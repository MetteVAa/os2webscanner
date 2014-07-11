#!/usr/bin/env python

"""Start up and manage queue processors to ensure they stay running.

Starts up multiple instances of each processor.
Restarts processors if they die or if they get stuck processing a single
item for too long.
"""

import os
import sys
import subprocess
import time
import signal
from datetime import timedelta

base_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(base_dir + "/webscanner_site")
os.environ["DJANGO_SETTINGS_MODULE"] = "webscanner.settings"

from django.utils import timezone
from django.db import transaction, IntegrityError, DatabaseError

from os2webscanner.models import ConversionQueueItem, Scan

var_dir = os.path.join(base_dir, "var")
log_dir = os.path.join(var_dir, "logs")

if not os.path.exists(log_dir):
    os.makedirs(log_dir)

processes_per_type = 2
processing_timeout = timedelta(minutes=3)

process_types = ('html', 'libreoffice', 'ocr', 'pdf', 'zip', 'text')

process_map = {}
process_list = []

def stop_process(p):
    """Stop the process."""
    if not 'process_handle' in p:
        print "Process %s already stopped" % p['name']
        return

    phandle = p['process_handle']
    del p['process_handle']
    pid = phandle.pid
    # If running, stop it
    if phandle.poll() is None:
        print "Terminating process %s" % p['name']
        phandle.terminate()
        phandle.wait()
    # Remove pid from process map
    if pid in process_map:
        del process_map[pid]
    # Set any ongoing queue-items for this process id to failed
    ConversionQueueItem.objects.filter(
        status=ConversionQueueItem.PROCESSING,
        process_id=pid
    ).update(
        status=ConversionQueueItem.FAILED
    )

    # Close logfile and remove it
    if 'log_fh' in p:
        log_fh = p['log_fh']
        del p['log_fh']
        log_fh.close()


def start_process(p):
    """Start the process."""
    if 'process_handle' in p:
        raise BaseException(
            "Program %s is already running" % p['name']
        )

    print "Starting process %s, (%s)" % (
        p['name'], " ".join(p['program_args'])
    )

    log_file = os.path.join(log_dir, p['name'] + '.log')
    log_fh = open(log_file, 'a')

    process_handle = subprocess.Popen(
        p['program_args'],
        stdout=log_fh,
        stderr=log_fh
    )

    pid = process_handle.pid

    if process_handle.poll() is None:
        print "Process %s started successfully, pid = %s" % (
            p['name'], pid
        )
    else:
        print "Failed to start process %s, exiting" % p['name']
        exit_handler()

    p['log_fh'] = log_fh
    p['process_handle'] = process_handle
    p['pid'] = pid
    process_map[pid] = p


def restart_process(processdata):
    """Stop and start the process."""
    stop_process(processdata)
    start_process(processdata)


def exit_handler(signum=None, frame=None):
    """Handle process manager exit signals by stopping all processes."""
    for p in process_list:
        stop_process(p)
    sys.exit(1)


signal.signal(signal.SIGTERM | signal.SIGINT | signal.SIGQUIT, exit_handler)

for ptype in process_types:
    for i in range(processes_per_type):
        name = '%s%d' % (ptype, i)
        program = [
            'python',
            os.path.join(base_dir, 'scrapy-webscanner', 'process_queue.py'),
            ptype
        ]
        # Libreoffice takes the homedir name as second arg
        if "libreoffice" == ptype:
            program.append(name)
        p = {'program_args': program, 'name': name}
        process_map[name] = p
        process_list.append(p)

for p in process_list:
    start_process(p)

try:
    while True:
        for pdata in process_list:
            result = pdata['process_handle'].poll()
            if pdata['process_handle'].poll() is not None:
                print "Process %s has terminated, restarting it" % (
                    pdata['name']
                )
                restart_process(pdata)

        stuck_processes = ConversionQueueItem.objects.filter(
            status=ConversionQueueItem.PROCESSING,
            process_start_time__lt=(
                timezone.localtime(timezone.now()) - processing_timeout
            ),
        )

        for p in stuck_processes:
            pid = p.process_id
            if pid in process_map:
                print "Process with pid %s is stuck, restarting" % pid
                stuck_process = process_map[pid]
                restart_process(stuck_process)
            else:
                p.status = ConversionQueueItem.FAILED
                p.save()

        try:
            with transaction.atomic():
                # Get the first unprocessed item of the wanted type
                running_scans = Scan.objects.filter(
                    status=Scan.STARTED
                ).select_for_update(nowait=True)
                for scan in running_scans:
                    if not scan.pid:
                        continue
                    try:
                        os.kill(scan.pid, 0)
                    except OSError:
                        scan.status = Scan.FAILED
                        scan.save()
        except (DatabaseError, IntegrityError) as e:
            pass

        time.sleep(10)
except KeyboardInterrupt:
    pass
