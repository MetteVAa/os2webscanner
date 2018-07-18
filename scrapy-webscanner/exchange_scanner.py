#!/usr/bin/env python
# The contents of this file are subject to the Mozilla Public License
# Version 2.0 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
#    http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS"basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# OS2Webscanner was developed by Magenta in collaboration with OS2 the
# Danish community of open source municipalities (http://www.os2web.dk/).
#
# The code is currently governed by OS2 the Danish community of open
# source municipalities ( http://www.os2web.dk/ )
import os
import sys
import time
import logging
import django
from multiprocessing import Queue
from pathlib import Path

# Include the Django app
base_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(base_dir + "/webscanner_site")
os.environ["DJANGO_SETTINGS_MODULE"] = "webscanner.settings"
django.setup()

from mailscan.exchangescan.settings import NUMBER_OF_EMAIL_THREADS

from mailscan.exchangescan.exchange_server_scanner import ExchangeServerScanner

from os2webscanner.models.scan_model import Scan


logger = logging.Logger('Exchange_scanner')


class ExchangeScanner:
    """A scanner application which can be run."""

    def __init__(self):
        """
        Initialize the scanner application.
        Takes input, argv[1], which is directly related to the scan job id in the database.
        Updates the scan status and sets the pid.
        """
        self.scan_id = sys.argv[1]

        # Get scan object from DB
        self.scan_object = Scan.objects.get(pk=self.scan_id)
        self.scan_object.set_scan_status_start()
        from scanner.scanner.scanner import Scanner
        self.scanner = Scanner(self.scan_id)

    def read_users(self, user_queue, user_file):
        """ Small helper to read user-list from file
        :param user_queue: The common multiprocess queue
        :param user_file: Filename for user list
        """
        user_path = Path(user_file)
        with user_path.open('r') as f:
            users = f.read().split('\n')
        for user in users:
            if len(user.strip()) == 0:
                users.remove(user)
        for user in users:
            user_queue.put(user)

    def run(self):
        domains = self.scanner.get_domain_objects()
        for domain in domains:
            user_queue = Queue()
            self.read_users(user_queue, domain.exchangedomain.userlist)
            scanners = {}
            for i in range(0, NUMBER_OF_EMAIL_THREADS):
                scanners[i] = ExchangeServerScanner(user_queue, domain, self.scanner, None)
                # stats.add_scanner(scanners[i])
                scanners[i].start()
                time.sleep(1)


exchange_scanner = ExchangeScanner()
exchange_scanner.run()
