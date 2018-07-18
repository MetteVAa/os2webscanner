import sys
import time
import shutil
import random
import logging
import multiprocessing
from pathlib import Path
from multiprocessing import Queue
from datetime import datetime, timedelta
from exchangelib import EWSDateTime, EWSDate, UTC
from exchangelib import FileAttachment, ItemAttachment
from exchangelib import IMPERSONATION, ServiceAccount, Account
from exchangelib.util import chunkify
from exchangelib.errors import ErrorNonExistentMailbox
from exchangelib.errors import ErrorInternalServerTransientError
from exchangelib.errors import ErrorCannotOpenFileAttachment
from exchangelib.errors import ErrorInternalServerError
from exchangelib.errors import ErrorInvalidOperation
from exchangelib.errors import ErrorTimeoutExpired
from stats import Stats
import settings
import password

exchangelogger = logging.getLogger('exchangelib')
exchangelogger.setLevel(logging.ERROR)

logger = logging.Logger('Mailscan_exchange')
fh = logging.FileHandler('logfile.log')
fh.setLevel(logging.INFO)
logger.addHandler(fh)
logger.error('Program start')


class ExportError(Exception):
    """ Exception to indicate that export failed for unspecified reasons """
    def __init__(self, *args, **kwargs):
        logger.error('Export Exception')
        Exception.__init__(self, *args, **kwargs)


class ExchangeMailboxScan(object):
    """ Library to export a users mailbox from Exchange to a filesystem """
    def __init__(self, user, start_date=None):
        credentials = ServiceAccount(username="mailscan",
                                     password=password.password)
        username = user + settings.mail_ending
        self.start_date = start_date
        if self.start_date is None:
            self.export_path = Path(settings.export_path + username)
        else:
            self.export_path = Path(settings.export_path + username + '_' +
                                    str(self.start_date))
        self.current_path = None
        try:
            self.account = Account(primary_smtp_address=username,
                                   credentials=credentials, autodiscover=True,
                                   access_type=IMPERSONATION)
            self.account.root.refresh()
            logger.info('{}: Init complete'.format(username))
        except ErrorNonExistentMailbox:
            logger.error('No such user: {}'.format(username))
            self.account = None

    def total_mails(self):
        """ Return the total amounts of content for the user
        this includes mails and calendar items """
        total_count = 0
        if self.account is not None:
            for folder in self.account.root.walk():
                total_count += folder.total_count
        return total_count

    def export_item_body(self, item):
        """ Export the actual message body to a txt file
        :param item: The exchange item to be exported
        :return: List of inline attachments that should be ignored
        """
        subject = item.subject
        if subject is None:
            subject = ''
        name = ('body_' + str(item.datetime_created) + '_' +
                str(random.random()) + '_' +
                subject.replace('/', '_')[-60:] + '.txt')
        path = self.current_path.joinpath(name)
        msg_body = str(item.body)
        with path.open('w') as f:
            f.write(msg_body)

        # Make a list inline images, mostly used for logos in footers:
        footer_images = []
        cid_pos = 0
        end_pos = 0
        while cid_pos > -1:
            cid_pos = msg_body.find('cid:', end_pos)
            if cid_pos > 0:
                end_pos = msg_body.find('"', cid_pos)
                cid_string = msg_body[cid_pos:end_pos]
                # Format for cid-string: cid:image001.jpg@01D1189A.A75327D0
                img_name = cid_string[4:cid_string.find('@')]
                footer_images.append(img_name)
        return footer_images

    def export_attachments(self, item, skip_list):
        """ Export all attachments to the users folder
        :param item: The exchange item to export attachments from
        :skip_list: List of attachments that should not be exported
        :return: Number of attachments in item (including skipped...)
        """
        i = 0
        for attachment in item.attachments:
            if attachment.name is None:
                # If we have no name, we assume that we no real atachment
                i += 1  # Make end-assertion happy
                continue
            if attachment.name in skip_list:
                logger.debug('Skippig {}: '.format(attachment.name))
                i += 1  # Make end-assertion happy
                continue
            if isinstance(attachment, FileAttachment):
                i = i + 1
                name = (str(item.datetime_created) + '_' +
                        str(random.random()) + '_' +
                        attachment.name.replace('/', '_')[-60:])
                path = self.current_path.joinpath(name)
                try:
                    with path.open('wb') as f:
                        f.write(attachment.content)
                except TypeError:
                    logger.error('Type Error')  # Happens for empty attachments
                except ErrorCannotOpenFileAttachment:
                    # Not sure when this happens
                    msg = 'ErrorCannotOpenFileAttachment {}'
                    logger.error(msg.format(self.current_path))
            elif isinstance(attachment, ItemAttachment):
                i = i + 1
                try:
                    # Pick last 60 chars of name to prevens too-long filenames
                    name = (str(item.datetime_created) + '_' +
                            str(random.random()) + '_' +
                            attachment.name.replace('/', '_')[-60:])
                    path = self.current_path.joinpath(name + '.txt')
                    with path.open('w') as f:
                        f.write(name)
                        if attachment.item.subject:
                            f.write(attachment.item.subject)
                        if attachment.item.body:
                            f.write(attachment.item.body)
                except AttributeError:
                    msg = 'AttributeError {}'
                    logger.error(msg.format(self.current_path))

            else:
                raise(Exception('Unknown attachment'))
        assert(i == len(item.attachments))
        return len(item.attachments)

    def list_non_empty_folders(self):
        """ Returns a list of all non-empty folders
        :return: A python list with all folders"""
        folder_list = []
        if self.account is not None:
            for folder in self.account.root.walk():
                if folder.total_count > 0:
                    folder_list.append(folder)
        return folder_list

    def _export_folder_subset(self, folder, start_dt=None, end_dt=None):
        """ Export a time-subset of an exchange folder
        :param folder: The exchange folder to export
        :start_dt: The start date to export from, default 1900-01-01
        :end_dt: The end date to export to, default 2100-01-01
        :return: Number of attachments in folder
        """
        try:
            attachments = 0
            if start_dt is None:
                start_dt = EWSDate(1900, 1, 1)
            if end_dt is None:
                end_dt = EWSDate(2100, 1, 1)
            items = folder.all()
            start_dt = UTC.localize(EWSDateTime(start_dt.year, start_dt.month,
                                                start_dt.day, 0, 0))
            end_dt = UTC.localize(EWSDateTime(end_dt.year, end_dt.month,
                                              end_dt.day, 0, 0))
            items = items.filter(datetime_received__range=(start_dt, end_dt))
            for chunk in chunkify(items, 10):
                for item in chunk:
                    skip_list = self.export_item_body(item)
                    attachments += self.export_attachments(item, skip_list)

        except ErrorInternalServerError:
            # Possibly happens on p7m files?
            msg = '{}: ErrorInternalServerError, giving up sub-folder'
            msg += ' Attachment value: {}'
            logger.warning(msg.format(self.export_path, attachments))
        except ErrorInvalidOperation:
            msg = '{}: ErrorInvalidOperation, giving up sub-folder'
            msg += ' Attachment value: {}'
            logger.warning(msg.format(self.export_path, attachments))
        except ErrorTimeoutExpired:
            attachments = -1
            time.sleep(30)
            logger.warning('{}: ErrorTimeoutExpired'.format(self.export_path))
        except ErrorInternalServerTransientError:
            attachments = -1
            time.sleep(30)
            warning = '{}, {}: ErrorInternalServerTransientError'
            logger.warning(warning.format(self.export_path, folder))
        return attachments

    def _attempt_export(self, folder, start_dt=None, end_dt=None):
        """ Attempt to export a folder, will re-try a number of time
        to increase tolerance to temporary errors on the server
        :param folder: The folder to scan
        :param start_dt: The start time of the export
        :param end_dt: The end time of the export
        :return: Number of exported attachments
        """
        logger.debug('Export {} from {} to {}'.format(self.current_path,
                                                      start_dt,
                                                      end_dt))
        subset_attach = -1
        attempts = 0
        while subset_attach < 0 and attempts < 5:
            attempts += 1
            subset_attach = self._export_folder_subset(folder, start_dt,
                                                       end_dt)
        if subset_attach == -1:
            raise ExportError('Unable to export folder')
        return subset_attach

    def export_folder(self, folder):
        """ Export a given folder
        :param folder: The folder to export
        :return: The number of exported attachments
        """
        folder_name = folder.name.replace(' ', '_').replace('/', '_')
        self.current_path = self.export_path.joinpath(folder_name)
        if self.export_path.joinpath(folder_name + '_done').exists():
            logger.info('Already done: {}'.format(self.current_path))
            return folder.total_count  # Already scanned
        if self.current_path.exists():
            logger.info('Clean up: {}'.format(self.current_path))
            shutil.rmtree(str(self.current_path))
        self.current_path.mkdir()

        attachments = 0
        if self.start_date is None:
            start_dt = EWSDate(2010, 1, 1)
            # First, export everything before 2010
            attachments += self._attempt_export(folder, end_dt=start_dt)
        else:
            start_dt = self.start_date
            end_dt = start_dt + timedelta(days=10)
            while end_dt < EWSDate(2022, 1, 1):
                attachments += self._attempt_export(folder, start_dt=start_dt,
                                                    end_dt=end_dt)
                start_dt = end_dt
                end_dt = start_dt + timedelta(days=10)
            # Finally, export everything later than 2022
            attachments += self._attempt_export(folder, start_dt=end_dt)
        try:
            self.current_path.rename(str(self.current_path) + '_done')
        except FileNotFoundError:
            # This can happen if a user mistakenly is scanned twice at
            # the same time
            # For now we will log and do no more. The offending folder
            # will still contain the export, but will lose the information
            # that it is already scanned and thus will be re-scanned on
            # next run.
            logger.error('Rename error from {}'.format(self.current_path))
        return attachments

    def check_mailbox(self, total_count=None):
        """ Run an export of the mailbox
        :param total_count: The total amount of mail for progress report
        :param start_dt: Only export from this time.
        :return: Returns true if the account exists
        """
        if self.account is None:
            return False
        attachments = 0
        total_scanned = 0
        if not self.export_path.exists():
            self.export_path.mkdir()
        folders = self.list_non_empty_folders()
        for folder in folders:
            info_string = '{}: Exporting: {} ({} items)'
            logger.info(info_string.format(self.export_path,
                                           folder,
                                           folder.total_count))
            attachments += self.export_folder(folder)
            total_scanned += folder.total_count
            logger.info("Exported {}: {} / {}".format(self.export_path,
                                                      total_scanned,
                                                      total_count))
        return True


class ExchangeServerScan(multiprocessing.Process):
    """ Helper class to allow parallel processing of export
    This classes inherits from multiprocessing and helps to
    run a number of exporters in parallel """
    def __init__(self, user_queue, start_date=None):
        multiprocessing.Process.__init__(self)
        self.user_queue = user_queue
        self.scanner = None
        self.user_name = None
        self.start_date = start_date

    def run(self):
        while not self.user_queue.empty():
            try:
                self.user_name = self.user_queue.get()
                logger.info('Scaning {}'.format(self.user_name))
                try:
                    self.scanner = ExchangeMailboxScan(self.user_name,
                                                       self.start_date)
                except NameError:  # No start_time given
                    self.scanner = ExchangeMailboxScan(self.user_name)
                total_count = self.scanner.total_mails()
                self.scanner.check_mailbox(total_count)
                logger.info('Done with {}'.format(self.user_name))
            except MemoryError:
                msg = 'We had a memory-error from {}'
                logger.error(msg.format(self.user_name))
                self.user_queue.put(self.user_name)
            except ExportError:
                msg = 'Could not export all of {}'
                logger.error(msg.format(self.user_name))
                self.user_queue.put(self.user_name)


def read_users(user_queue, user_file):
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


if __name__ == '__main__':
    number_of_threads = int(sys.argv[1])
    try:
        start_arg = datetime.strptime(sys.argv[2], '%Y-%m-%d')
        start_date = EWSDate.from_date(start_arg)
    except IndexError:
        start_date = None  # Scan from beginning of time

    # Populate user queue
    user_queue = Queue()
    read_users(user_queue, settings.user_path)

    stats = Stats(user_queue)

    scanners = {}
    for i in range(0, number_of_threads):
        scanners[i] = ExchangeServerScan(user_queue, start_date)
        stats.add_scanner(scanners[i])
        scanners[i].start()
        time.sleep(1)

    stats.run()

    while stats.is_alive():
        time.sleep(5)