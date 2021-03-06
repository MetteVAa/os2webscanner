# -*- coding: UTF-8 -*-
# encoding: utf-8
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
import logging
import tempfile
from subprocess import call, CalledProcessError

from django.conf import settings
from django.db import models

from os2webscanner.aescipher import decrypt
from .domain_model import Domain

# Get an instance of a logger
logger = logging.getLogger(__name__)


class FileDomain(Domain):

    """Represents a file domain to be scanned."""

    mountpath = models.CharField(max_length=2048, verbose_name='Folder sti', null=True)

    # Run error messages
    MOUNT_FAILED = (
        "Scanneren kunne ikke startes," +
        " fordi netværksdrev ikke kunne monteres"
    )

    @property
    def root_url(self):
        """Return the root url of the domain."""
        url = self.url.replace('*.', '')
        return url

    def check_mountpoint(self):
        """Checks if networkdrive is already mounted."""

        if not self.mountpath or not os.path.isdir(self.mountpath):
            self.set_mount_path()

        response = call('mountpoint ' + self.mountpath, shell=True)
        return response

    def set_mount_path(self):
        if not os.path.isdir(settings.NETWORKDRIVE_TMP_PREFIX):
            os.makedirs(settings.NETWORKDRIVE_TMP_PREFIX)

        tempdir = tempfile.mkdtemp(dir=settings.NETWORKDRIVE_TMP_PREFIX)
        self.mountpath = tempdir
        self.save()

    def smbmount(self):
        """Mounts networkdrive if not already mounted."""

        if self.check_mountpoint() is 0:
            return True

        # Make only one scanner able to scan mounted file directory.
        # Scrapy locks the files while reading, so to scan jobs running at the same time is not possible.

        command = 'sudo mount -t cifs ' + self.root_url + ' ' + self.mountpath + ' -o iocharset=utf8'

        if settings.PRODUCTION_MODE:
            # Mount as apache user (www-data). It will always have uid 33
            command += ',uid=33,gid=33'
        if self.authentication.username != '':
            command += ',username=' + self.authentication.username
        if len(self.authentication.ciphertext) > 0:
            password = decrypt(bytes(self.authentication.iv), bytes(self.authentication.ciphertext))
            command += ',password=' + password
        if self.authentication.domain != '':
            command += ',domain=' + self.authentication.domain

        logger.debug('Mount command: {0}'.format(command))
        response = call(command, shell=True)

        if response is not 0:
            logger.error('Mount failed: {0}'.format(response))
            return False

        return True

    def smbunmount(self):
        """Unmounts networkdrive if mounted."""
        if self.check_mountpoint() is 0:
            call('sudo umount -l ' + self.mount_path, shell=True)
            call('sudo umount -f ' + self.mount_path, shell=True)

    def __str__(self):
        """Return the URL for the domain."""
        return self.url

    class Meta:
        db_table = 'os2webscanner_filedomain'
