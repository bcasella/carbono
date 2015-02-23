#!/usr/bin/python
# coding: utf-8
# Copyright (C) 2011 Lucas Alvares Gomes <lucasagomes@gmail.com>
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

import json
import errno

from carbono.utils import *
from carbono.exception import *


class Information:

    def __init__(self, target_path):
        self._doc = dict()
        self.target_path = adjust_path(target_path)
        self.file_path = self.target_path + "image.info"

    def set_partitions(self, plist):
        """ """
        img_parts = map(lambda x: x["number"], self._doc["partitions"])
        not_found = filter(lambda x: x not in img_parts, plist)

        # Check availability
        if not_found:
            parts = ' '.join(map(lambda x: str(x), not_found))
            raise PartitionNotFound("Partition(s) {0} not found".\
                                    format(not_found))

        self._partitions = list()
        for part in self._doc["partitions"]:
            if part["number"] in plist:
                self._partitions.append(part)

    def set_image_name(self, name):
        """ """
        self._doc.update({"name": name})

    def set_image_compressor_level(self, level):
        """ """
        self._doc.update({"compressor_level": level})

    def set_image_is_disk(self, is_disk):
        """ """
        self._doc.update({"is_disk": is_disk})

    def set_disk_size(self, size):
        """ """
        self._doc.update({"disk_size": size})

    def add_partition(self, number, type, volumes, size,
                      uuid=None, label=None):
        """ """
        part_dict = dict()
        part_dict.update({"number": number,
                          "type": type,
                          "size": size})

        if uuid is not None:
            part_dict.update({"uuid": uuid})
        if label is not None:
            part_dict.update({"label": label})
        if volumes > 1:
            part_dict.update({"volumes": volumes})

        if not self._doc.has_key("partitions"):
            self._doc.update({"partitions": list()})

        self._doc["partitions"].append(part_dict)

    def get_image_name(self):
        """ """
        return self._doc["name"]

    def get_disk_size(self):
        """ """
        if hasattr(self, _doc["disk_size"]):
            return self._doc["disk_size"]
        return None

    def get_image_compressor_level(self):
        """ """
        return self._doc["compressor_level"]

    def get_image_is_disk(self):
        """ """
        return self._doc["is_disk"]

    def get_partitions(self):
        """ """
        if hasattr(self, "_partitions"):
            partitions = self._partitions
        else:
            partitions = self._doc["partitions"]

        parts = list()
        for part in partitions:
            partition = type("Partition",
                             (object,),
                             part)
            parts.append(partition)
        return parts

    def save(self):
        with open(self.file_path, mode='w') as f:
            json.dump(self._doc, f, indent=4)

    def load(self):
        try:
            with open(self.file_path, 'r') as f:
                self._doc = json.load(f)
        except IOError, e:
            if e.errno == errno.ENOENT:
                raise ImageNotFound("Image not found")
