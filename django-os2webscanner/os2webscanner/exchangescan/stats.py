import time
import pika
import curses
import logging
import subprocess
import multiprocessing
import psutil
import settings

logger = logging.getLogger('Mailscan_exchange')
fh = logging.FileHandler('logfile.log')
fh.setLevel(logging.INFO)
logger.addHandler(fh)
logger.error('Stat start')


class amqp_listener(multiprocessing.Process):
    def __init__(self, stat_module):
        multiprocessing.Process.__init__(self)
        self.stat_module = stat_module


class Stats(multiprocessing.Process):
    def __init__(self, user_queue):
        psutil.cpu_percent(percpu=True)  # Initil dummy readout
        multiprocessing.Process.__init__(self)

        conn_params = pika.ConnectionParameters('localhost')
        connection = pika.BlockingConnection(conn_params)
        self.channel = connection.channel()
        self.amqp_messages = {}
        self.user_queue = user_queue
        self.scanners = []
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(False)
        self.screen.keypad(1)
        self.screen.nodelay(1)
        # Measure initial values while we have the chance
        self.start_time = time.time()
        self.total_users = self.user_queue.qsize()
        self.init_du = self.disk_usage()

    def amqp_update(self):
        for scanner in self.scanners:
            pid = str(scanner.pid)
            self.channel.queue_declare(queue=pid)
            method_frame, header_frame, body = self.channel.basic_get(pid)
            if method_frame:  # Ensures result is not None
                self.amqp_messages[pid] = body.decode()

    def number_of_threads(self):
        """ Number of threads
        :return: Tuple with Number of threads, and nuber of active threads
        """
        return (len(self.scanners), len(multiprocessing.active_children()))

    def add_scanner(self, scanner, amqp_name=None):
        """ Add a scanner to the internal list of scanners
        :param scanner: The scanner object to be added
        :return: The new number of threads
        """
        self.scanners.append(scanner)
        return self.number_of_threads()

    def disk_usage(self):
        """ Return the current disk usage
        :return: Disk usage in MB
        """
        error = True
        while error:
            try:
                du_output = subprocess.check_output(['du', '-s',
                                                     settings.export_path])
                error = False
            except subprocess.CalledProcessError:
                # Happens if du is called while folder is being marked done

                # logger.warn('du-error') Warning ends up in the terminal...
                # will need to investiate
                time.sleep(1)
        size = float(du_output.decode('utf-8').split('\t')[0]) / 1024
        return size

    def exported_users(self):
        """ Returns the number of exported users
        :return: Tuple with finished exports and total users
        """
        finished_users = (self.total_users - self.user_queue.qsize() -
                          self.number_of_threads()[1])
        return (finished_users, self.total_users)

    def amount_of_exported_data(self):
        """ Return the total amount of exported data (MB)
        :return: The total amount of exported data sinze start
        """
        return self.disk_usage() - self.init_du

    def memory_info(self):
        """ Returns the memory consumption (in MB) of all threads
        :return: List of memory consumptions
        """
        mem_list = []
        for scanner in self.scanners:
            pid = scanner.pid
            process = psutil.Process(pid)
            mem_info = process.memory_full_info()
            used_memory = mem_info.uss/1024**2
            mem_list.append(used_memory)
        return mem_list

    def status(self):
        template = ('Threads: {}. ' +
                    'Queue: {}. ' +
                    'Export: {:.3f}GB. ' +
                    'Time: {:.2f}min. ' +
                    'Speed: {:.2f}MB/s. ' +
                    'Memory consumption: {:.3f}GB. ' +
                    'Scanned users: {} / {}')
        memory = sum(self.memory_info()) / 1024
        processes = self.number_of_threads()[1]
        dt = (time.time() - self.start_time)
        users = self.exported_users()
        ret_str = template.format(processes,
                                  self.user_queue.qsize(),
                                  self.disk_usage() / 1024,
                                  dt / 60.0,
                                  self.amount_of_exported_data() / dt,
                                  memory,
                                  users[0], users[1])
        return ret_str

    def run(self):
        processes = self.number_of_threads()[1]
        while processes > 0:
            time.sleep(5)
            self.amqp_update()
            thread_info = self.number_of_threads()
            processes = thread_info[1]
            status = self.status()
            logger.info(status)
            # print(status)

            dt = int((time.time() - self.start_time))
            msg = 'Run-time: {}min {}s  '.format(int(dt / 60),
                                                 int(dt % 60))
            self.screen.addstr(2, 3, msg)

            users = self.exported_users()
            msg = 'Exported users: {}/{}  '.format(users[0], users[1])
            self.screen.addstr(3, 3, msg)

            total_export_size = self.amount_of_exported_data()
            msg = 'Total export: {:.2f}MB   '.format(total_export_size)
            self.screen.addstr(4, 3, msg)

            speed = total_export_size / dt
            msg = 'Avg eksport speed: {:.2f}MB/s   '.format(speed)
            self.screen.addstr(5, 3, msg)

            self.screen.addstr(6, 3, 'Memory usage:')
            mem_info = self.memory_info()
            for i in range(0, len(mem_info)):
                msg = 'Worker {}: {:.1f}MB    '.format(i, mem_info[i])
                self.screen.addstr(7 + i, 3, msg)
            msg = 'Total: {:.0f}MB    '.format(sum(mem_info))
            self.screen.addstr(8 + i, 3, msg)

            cpu_usage = psutil.cpu_percent(percpu=True)
            msg = 'CPU{} usage: {}%  '
            for i in range(0, len(cpu_usage)):
                self.screen.addstr(2 + i, 40, msg.format(i, cpu_usage[i]))

            i = i + 1
            msg = 'Total threads: {}. Active threads: {}  '
            self.screen.addstr(2 + i, 40,
                               msg.format(thread_info[0], thread_info[1]))

            i = i + 2
            self.screen.addstr(2 + i, 40, 'Scan status:')
            for key, value in self.amqp_messages.items():
                i = i + 1
                msg = 'ID {} scanning: {}'
                self.screen.addstr(2 + i, 40, msg.format(key, value))
                self.screen.clrtoeol()

            self.screen.refresh()