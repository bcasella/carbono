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

import math
import _ped
from parted import PARTITION_NORMAL

from carbono.device import Device
from carbono.disk import Disk
from carbono.mbr import Mbr
from carbono.disk_layout_manager import DiskLayoutManager
from carbono.information import Information
from carbono.image_reader import ImageReaderFactory
from carbono.compressor import Compressor
from carbono.buffer_manager import BufferManagerFactory
from carbono.exception import *
from carbono.utils import *
from carbono.config import *

from carbono.log import log
from partition_expander import PartitionExpander

class ImageRestorer:

    def __init__(self, image_folder, target_device,
                 status_callback, partitions=None,
                 expand=2):

        assert check_if_root(), "You need to run this application as root"

        self.image_path = adjust_path(image_folder)
        self.target_device = target_device
        self.notify_status = status_callback
        self.partitions = partitions
        self.expand = expand

        self.timer = Timer(self.notify_percent)
        self.total_blocks = 0
        self.processed_blocks = 0
        self.current_percent = -1
        self.active = False
        self.canceled = False

    def notify_percent(self):
        # Total blocks can be 0 when restoring only a swap partition
        # for example
        if self.total_blocks > 0:
            percent = (self.processed_blocks/float(self.total_blocks)) * 100
            if self.current_percent != percent:
                self.current_percent = percent
                self.notify_status("progress", {"percent":
                                    self.current_percent})

    def restore_image(self):
        """ """
        if is_mounted(self.target_device):
            raise DeviceIsMounted("Please umount first")

        self.active = True
        information = Information(self.image_path)
        information.load()
        if self.partitions:
            information.set_partitions(self.partitions)
        image_name = information.get_image_name()
        compressor_level = information.get_image_compressor_level()
        partitions = information.get_partitions()

        # Get total size
        total_bytes = 0
        for part in partitions:
            total_bytes += part.size

        self.total_blocks = long(math.ceil(total_bytes/float(BLOCK_SIZE)))

        device = Device(self.target_device)

        if device.is_disk() != \
           information.get_image_is_disk():
            log.error("Invalid target device %s" % device.path)
            raise ErrorRestoringImage("Invalid target device")

        try:
            disk = Disk(device)
        except _ped.DiskLabelException:
            try:
                device.fix_disk_label()
                disk = Disk(device)
            except:
                log.error("Unrecognized disk label")
                raise ErrorRestoringImage("Unrecognized disk label")

        if information.get_image_is_disk():
            #Get total disk target size
            disk_size = get_disk_size(self.target_device)
            if (total_bytes > disk_size):
                log.info("Total size of image is {0}".format(total_bytes))
                log.info("Total size of {0} is {1}".format(self.target_device,disk_size))
                log.error("The size of {0} is {1}, is not enough to apply the selected image".format(self.target_device, disk_size))
                disk_space_info = []
                disk_space_info.append(total_bytes)
                disk_space_info.append(disk_size)
                self.notify_status("no_enough_space", {"disk_minimum_size":disk_space_info})
                raise ErrorRestoringImage("No enough space on disk")
            log.info("Restoring MBR and Disk Layout")
            mbr = Mbr(self.image_path)
            mbr.restore_from_file(self.target_device)
            dlm = DiskLayoutManager(self.image_path)
            if self.expand != 2:
                dlm.restore_from_file(disk, True)
            else:
                dlm.restore_from_file(disk, False)
        else:
            parent_path = get_parent_path(self.target_device)
            parent_device = Device(parent_path)
            parent_disk = Disk(parent_device)
            partition = parent_disk.get_partition_by_path(
                                        self.target_device,
                                        part.type)
            part_size = partition.getSize('b')
            if (total_bytes > part_size):
                 part_space_info = []
                 part_space_info.append(total_bytes)
                 part_space_info.append(part_size)
                 log.error("The partition selected is smaller than the image")
                 self.notify_status("no_enough_space_part", {"disk_minimum_size":part_space_info})
                 raise ErrorRestoringImage("No enought space on partition")
        self.timer.start()
        for part in partitions:
            if not self.active: break
            
            if information.get_image_is_disk():
                partition = disk.get_partition_by_number(part.number,
                                                         part.type)
            else:
                parent_path = get_parent_path(self.target_device)
                parent_device = Device(parent_path)
                parent_disk = Disk(parent_device)
                partition = parent_disk.get_partition_by_path(
                                            self.target_device,
                                            part.type)

            log.info("Restoring partition {0}".format(partition.get_path()))

            if partition is None:
                raise ErrorRestoringImage("No valid partitions found")

            if hasattr(part, "uuid"):
                partition.filesystem.open_to_write(part.uuid)
            else:
                partition.filesystem.open_to_write()

            if hasattr(part, "label"):
                partition.filesystem.write_label(part.label)

            if partition.filesystem.is_swap():
                continue

            pattern = FILE_PATTERN.format(name=image_name,
                                          partition=part.number,
                                          volume="{volume}")
            volumes = 1
            if hasattr(part, "volumes"):
                volumes = part.volumes

            image_reader = ImageReaderFactory(self.image_path, pattern,
                                              volumes, compressor_level,
                                              self.notify_status)

            extract_callback = None
            if compressor_level:
                compressor = Compressor(compressor_level)
                extract_callback = compressor.extract

            self.buffer_manager = BufferManagerFactory(image_reader.read_block,
                                                       extract_callback)

            # open the file after instantiating BufferManager, cause of a
            # problem on multiprocessing module, FD_CLOEXE doesn't work
            # (I don't want to dup the file descriptor).
            image_reader.open()
            self.buffer_manager.start()

            buffer = self.buffer_manager.output_buffer
            while self.active:
                try:
                    data = buffer.get()
                except IOError, e:
                    if e.errno == errno.EINTR:
                        self.cancel()
                        break

                if data == EOF:
                    break

                try:
                    partition.filesystem.write_block(data)
                except ErrorWritingToDevice, e:
                    if not self.canceled:
                        self.stop()
                        raise e

                self.processed_blocks += 1

            self.buffer_manager.join()
            partition.filesystem.close()

        self.timer.stop()
        log.info(self.expand)

        if self.expand != 2:
            if information.get_image_is_disk():
                self.expand_last_partition(self.expand)

        if self.canceled:
            self.notify_status("canceled", {"operation": 
                                            "Restore image"})
        else:
            self._finish()
        log.info("Restoration finished")
        log.info("Iniciando gtk grubinstall")
        cmd = "{0}".format(which("grubinstall"))
        try:
            self.process = RunCmd(cmd)
            self.process.run()
        except Exception as e:
            log.error("Erro ao iniciar grubinstall. {0}".format(e))

    def expand_last_partition(self,opt_expand):
        # After all data is copied to the disk
        # we instance class again to reload
        
        sync()
        device = Device(self.target_device)
        disk = Disk(device)
        partition = disk.get_last_partition()
        if partition is not None:
            if partition.type == PARTITION_NORMAL:
                expander = PartitionExpander(device.path)
                log.info("Checking and try expand {0}".format(partition.get_path()))
                new_size = expander.try_expand()
                log.info("The new_size of the disk will be {0}".format(new_size))
                if new_size!= -1:

                    if opt_expand == 0:
                        log.info("Expanding {0} filesystem".format(partition.get_path()))
                        self.notify_status("expand", {"device":
                                               partition.get_path()})
                        returncode = partition.filesystem.resize()
                        if returncode == True:
                            log.info("Resize in {0} was made with sucess".format(partition.get_path()))
                        else:
                            log.info("Resize in {0} failed".format(partition.get_path()))
                            self.notify_status("expand_last_partition_error", {"last_partition":partition.get_path()})
                            self.canceled = True
                    else:
                        if opt_expand == 1:
                            log.info("Formating {0} filesystem".format(partition.get_path()))
                            self.notify_status("format", {"device":
                                                   partition.get_path()})
                            partition.filesystem.format_filesystem()
    def stop(self):
        # When restoring only a swap partition, buffer_manager
        # isnt necessary
        if self.active and hasattr(self, "buffer_manager"):
            self.buffer_manager.stop()
        self.active = False
        self.timer.stop()
        log.info("Restore image stopped")

    def _finish(self):
        self.stop()
        self.notify_status("finish")

    def cancel(self):
        if not self.canceled:
            self.canceled = True
            self.stop()

