#!/usr/bin/python
# coding: utf-8
# Copyright (C) 2010 Lucas Alvares Gomes <lucasagomes@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import subprocess
import re
from carbono.filesystem.generic import Generic
from carbono.exception import *
from carbono.utils import *

class Ext(Generic):
    MOUNT_OPTIONS = "-t extfs"

    def get_used_size(self):
        """  """
        p = subprocess.Popen("{0} -h {1}".format(which("dumpe2fs"), self.path),
                             shell=True,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)

        lines = p.stdout.readlines()

        free_blocks = 0
        block_size = 0
        for l in lines:
            if l.startswith("Free blocks:"):
                free_blocks = int(l.split()[2])
            elif l.startswith("Block size:"):
                block_size = int(l.split()[2])

        sectors_unused = free_blocks * (block_size/float(512))
        sectors_unused = (self.geometry.end - \
                          self.geometry.start + 1) - \
                          sectors_unused
        bytes = long(sectors_unused * 512)

        return bytes

    def open_to_read(self):
        """ """
        #cmd = "{0} -q -c -s {1} -o -".format(which("partclone.extfs"), self.path)
        cmd = "{0} -c -s {1} -o -".format(which("partclone.extfs"), self.path)
        try:
            self.process = RunCmd(cmd)
            self.process.run()
            self._fd = self.process.stdout
            self.fderr = self.process.stderr
        except:
            raise ErrorOpenToRead("Cannot open {0} to read".format(self.path))

    def open_to_write(self, uuid=None):
        """ """
        #cmd = "{0} -q -r -o {1} -s - ".format(which("partclone.extfs"), self.path)
        cmd = "{0} -r -o {1} -s - ".format(which("partclone.extfs"), self.path)
        try:
            self.process = RunCmd(cmd)
            self.process.run()
            self._fd = self.process.stdin
            self.fderr = self.process.stderr
        except:
            raise ErrorOpenToWrite("Cannot open {0} to write".format(self.path))

    def uuid(self):
        """ """
        proc = subprocess.Popen(["blkid", self.path], stdout=subprocess.PIPE)
        output = proc.stdout.read()

        uuid = None

        if not len(output):
            return uuid

        try:
            uuid = re.search('(?<=UUID=")\w+-\w+-\w+-\w+-\w+', output).group(0)
        except AttributeError:
            pass

        return uuid

    def close(self):
        """  """
        os.system("pkill -9 partclone.extfs")
        if self._fd is None or \
           self._fd.closed:
            return

        self._fd.close()

    def check(self):
        ret = run_simple_command("{0} -f -y -v {1}".format(which("e2fsck"),
                                                           self.path))
        proc = subprocess.Popen([which("resize2fs"), "-f", self.path],
                                stdout=subprocess.PIPE)
        output = proc.stdout.read()
        output = output.strip()
        if ret in (0, 1, 2, 256):
            return True
        return False

    def format_filesystem(self):

        proc = subprocess.Popen([which("mkfs.ext3"), self.path],
                                stdout=subprocess.PIPE)
        output = proc.stdout.read()
        output = output.strip()
        if output == 0:
            return True
        return False


    def resize(self):

        if self.check():
            proc = subprocess.Popen([which("resize2fs"), self.path],
                                    stdout=subprocess.PIPE)
            proc.wait()
            output = proc.stdout.read()
            output = output.strip()
            if proc.returncode == 0:
                return True
        return False

    def read_label(self):
        proc = subprocess.Popen([which("e2label"), self.path],
                                stdout=subprocess.PIPE)
        output = proc.stdout.read()
        output = output.strip()
        if output:
            return output
        return None

    def write_label(self, label):
        ret = run_simple_command('{0} {1} "{2}"'.format(which("e2label"),
                                                      self.path,
                                                      label))
        if ret == 0:
            return True
        return False
