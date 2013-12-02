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
import tempfile
import multiprocessing
import random
import errno
import os
import parted

from threading import Thread, Event
from os.path import realpath
from carbono.exception import *



class DiskInfo():

    def __init__(self):
        self.__DISK_DICT = {}
        self.__PARTITION_DICT = {}

      #  self.disk_info = {"/dev/sda":{"size":123123124,
      #                                "label":model:self.__DISK_DICT,
      #                                "partitions":[]}

    def __get_devices(self):
        ''' Filter = only partitions with a valid filesystem '''

        disk_dict = {}
        devices = parted.getAllDevices()
        for device in devices:
            dev_path = device.path
            dev_model = device.model
            dev_size = device.getSize('b')
            try:
                disk = parted.Disk(device)
            except:
                continue

            part_dict = {}
            for p in disk.partitions:
                if p.type not in (parted.PARTITION_NORMAL,
                                  parted.PARTITION_LOGICAL):
                    continue

                part_path = p.path
                part_size =1024*1024*int(p.getSize('b'))
                part_type = "unknown"
                if p.fileSystem:
                    part_type = p.fileSystem.type

                part_dict[part_path] = {"size": part_size,
                                        "type": part_type}

            disk_dict[dev_path] = {"model": dev_model,
                                   "size": dev_size,
                                   "partitions": part_dict}
        return disk_dict


    def __collect_information_about_devices(self):
        '''
        Pega informacoes sobre os discos e particoes,
        todas as telas que precisarem de informacoes sobre discos ou particoes
        pegam elas dos dicionarios aqui criados
        '''
        _dict = self.__get_devices()
        for disk in _dict:
            partitions = _dict[disk]["partitions"].keys()
            for part in partitions:
                self.__PARTITION_DICT[part] = {"type": _dict[disk]["partitions"][part]["type"],
                                             "size": _dict[disk]["partitions"][part]["size"]}
            self.__DISK_DICT[disk] = {"model": _dict[disk]["model"],
                                    "size": _dict[disk]["size"],
                                    "partitions": partitions}


    def formated_partitions(self):
        formated_partitions = []
        formated_partitions_dict = self.__DISK_DICT
        self.__collect_information_about_devices()

        device_info = {"size":None,"label":None,"partitions":None}
        for part in self.__PARTITION_DICT.keys():
            part_type = self.__PARTITION_DICT[part]['type']
            size_bytes = self.__PARTITION_DICT[part]['size']
            size_mb = int(long(size_bytes)/(1024*1024.0))
            part_dict = {}
            part_dict["type"] = part_type
            part_dict["path"] = part
            part_dict["size"] = size_mb
            formated_partitions.append(part_dict)

        formated_partitions.sort(reverse=False)
        temp_parts = []
        disk = formated_partitions[0]['path'][:8]
        for aux in range(0,len(formated_partitions)):
            temp_disk = formated_partitions[aux]['path'][:8]
            if temp_disk == disk:
                temp_parts.append(formated_partitions[aux])
            else:
                formated_partitions_dict[disk]["partitions"] = temp_parts
                temp_parts = []
                temp_parts.append(formated_partitions[aux])
                disk = temp_disk
        formated_partitions_dict[disk]["partitions"] = temp_parts
        return(formated_partitions_dict)



class DiskPartition():


    def __init__(self, partition = ""):

        self.__temp_folder = ""
        self.__partition = partition

    def __generate_temp_folder(self, destino = "/tmp/"):

        self.__temp_folder = adjust_path(tempfile.mkdtemp())

        return self.__temp_folder

    def __set_partition(self, partition):

        self.__partition = partition

    def get_partition(self):

        return self.__partition

    def umount_partition(self, device = None):
        disk_mounted = self.get_mounted_devices()
        disk_list = []
        result_disk_umounted = {}
        if self.__partition not in disk_mounted.keys():
            return "{0} is already umounted".format(self.__partition)
        else:
            disk_list = disk_mounted[self.__partition]
            for item in disk_list:
                cmd = "umount {0}".format(item)
                p = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE, shell=True)
                ret = os.waitpid(p.pid,0)[1]
                if not ret:
                    result_disk_umounted[item] = 0
                    print "A particao {0} foi desmontada do diretorio {1}".format(self.__partition, item)
                else:
                    result_disk_umounted[item] = -1
                    print "A particao {0} montada em {1} nao foi desmontada".format(self.__partition,item)
        return result_disk_umounted

    def umount_all_partitions(self):
        disk_mounted = self.get_mounted_devices()
        result_part_umounted = {}
        result_disk_umounted = {}
        disk_list = []
        for item in disk_mounted.keys():
            disk_list = disk_mounted[item]
            result_part_umounted = {}
            for part in  disk_list:
                cmd = "umount {0}".format(item)
                p = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE, shell=True)
                ret = os.waitpid(p.pid,0)[1]
                if not ret:
                    result_part_umounted[part] = 0
                else:
                    result_part_umounted[part] = -1
            result_disk_umounted[item] = result_part_umounted
        return result_disk_umounted


    def mount_partition(self,destino = None):

        mounted_folder = self.get_mount_point(self.__partition)

        if mounted_folder:
            return mounted_folder[0]

        mounted_folder = ""

        if destino is None:
            mounted_folder = adjust_path(tempfile.mkdtemp())
            cmd = "mount {0} {1}".format(self.__partition, mounted_folder)
            p = subprocess.Popen(cmd,stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            ret = os.waitpid(p.pid,0)[1]
            if not ret:
                return mounted_folder
            else:
                return False

        else:
            cmd = "mount {0} {1}".format(self.__partition, destino)
            p = subprocess.Popen(cmd,stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            ret = os.waitpid(p.pid,0)[1]
            if not ret:
                return destino
            else:
                return False

    def get_mount_point(self, device = None):
        if device is not None:
            mounted_dest = self.get_mounted_devices()
            if device not in mounted_dest.keys():
                return False
            else:
                return mounted_dest[device]
        else:
            return False

    def get_mounted_devices(self, device = None):
        disk_mounted = {}
        list_dest = []
        mount_command = subprocess.check_output(['mount','-l']).split('\n')
        for lines in mount_command:
            line = lines.split(' ')
            if line[0].startswith('/dev/sd'):
                if line[0] not in disk_mounted.keys():
                    list_dest = []
                    list_dest.append(line[2])
                    disk_mounted[line[0]] = list_dest
                    list_dest = []
                else:
                    list_dest = []
                    for element in xrange(len(disk_mounted[line[0]])):
                        list_dest.append(disk_mounted[line[0]][element])
                    list_dest.append(line[2])
                    disk_mounted[line[0]] = list_dest
                    list_dest = []
        return disk_mounted

class Timer(Thread):
    def __init__(self, callback, timeout=2):
        Thread.__init__(self)
        self.callback = callback
        self.timeout = timeout
        self.event = Event()

    def run(self):
        while not self.event.is_set():
            self.callback()
            self.event.wait(self.timeout)

    def stop(self):
        self.event.set()


class RunCmd:
    def __init__(self, cmd):
        self.cmd = cmd
        self.stdout = None
        self.stdin = None
        self.stderr = None

    def run(self):
        self.process = subprocess.Popen(self.cmd, shell=True,
                                        stdout=subprocess.PIPE,
                                        stdin=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
        self.stdout = self.process.stdout
        self.stdin = self.process.stdin
        self.stderr = self.process.stderr

    def wait(self):
        if hasattr(self, "process"):
            self.process.wait()
            return self.process.returncode

    def stop(self):
        if hasattr(self, "process"):
            try:
                self.process.kill()
            except OSError, e:
                if e.errno == errno.ESRCH:
                    pass


def run_simple_command(cmd):
    """  """
    p = subprocess.Popen(cmd, shell=True,
                         stdout=subprocess.PIPE,
                         stdin=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    p.wait()
    return p.returncode

def get_disk_size(path):
    devices = parted.getAllDevices()
    for device in devices:
        if (device.path == path):
            return device.getSize('b')
    return False

def random_string(length=5):
    return ''.join([random.choice(tempfile._RandomNameSequence.characters) \
                   for i in range(length)])

def adjust_path(path):
    """ """
    path = realpath(path)
    if not path[-1] == '/':
        path += '/'
    return path

def make_temp_dir():
    """ """
    return adjust_path(tempfile.mkdtemp())

def get_parent_path(path):
    num = -1
    while True:
        try:
            int(path[num])
            num -= 1
        except ValueError:
            return path[:num+1]

def singleton(cls):
    instance_list = list()
    def getinstance():
        if not len(instance_list):
            instance_list.append(cls())
        return instance_list[0]
    return getinstance

def available_processors():
    return multiprocessing.cpu_count()

def is_hyperthreading():
    with open("/proc/cpuinfo", "r") as f:
        for line in f.readlines():
            if line.startswith("flags"):
                if "ht" in line.split():
                    return True
                break
    return False

def available_memory(percent=100):
    free = 0
    with open("/proc/meminfo", 'r') as f:
        for line in f:
            if line.startswith("MemFree:"):
                free = int(line.split()[1]) * 1024
                break

    if percent < 100:
        free = (free * percent) / 100

    return free

def get_devices():
    disk_dict = {}
    devices = parted.getAllDevices()
    for device in devices:
        dev_path = device.path
        try:
            disk = parted.Disk(device)
        except:
            continue
        part_dict = {}
        for p in disk.partitions:
            part_path = p.path
            part_type = "unkown"
            if p.fileSystem:
                part_type = p.fileSystem.type
            if part_type == "fat32" or part_type == "fat16":
                part_dict[part_path] = {"type":part_type}
                disk_dict[dev_path] = {"partitions": part_dict}
    return disk_dict

CARBONO_FILES2 = ("initram.gz","vmlinuz","isolinux.cfg")

def mount_pen(device):
    tmpd = make_temp_dir()
    ret = run_simple_command("mount {0} {1}".format(device, tmpd))
    if ret is not 0:
        raise ErrorMountingFilesystem
    return tmpd

def find_carbono(path):
    dev_files = os.listdir(path)
    ret = True
    if filter(lambda x:not x in dev_files, CARBONO_FILES2):
        ret = False
    return ret


def mount_point(device):
    mounts = {}
    for line in subprocess.check_output(['mount', '-l']).split('\n'):
        parts = line.split(' ')
        if len(parts) > 2:
            mounts[parts[0]] = parts[2]
    try:
        if mounts[device]:
            return mounts[device]
        else:
            raise ErrorWithoutConnectedDevice("Sem Pen-Drive conectado")
    except:
        raise ErrorIdentifyDevice("Erro na identificação do Pendrive")

def get_upimage_device():
    devices = get_devices()
    for dev in devices:
        device = devices[dev]["partitions"].keys()
        if is_mounted(device[0]):
            mount_path = mount_point(device[0])
        else:
            mount_path = mount_pen(device[0])
        ret = find_carbono(mount_path)
        if ret:
            run_simple_command("umount {0}".format(mount_path))
            return device[0], mount_path
        else:
            if ret == 0:
                run_simple_command("umount {0}".format(mount_path))
    return -1,-1

def get_cdrom_device():
    device = None
    path = None
    try:
        device,path = get_upimage_device()
    except:
        pass
    if (device and path) == -1:
        with open("/proc/sys/dev/cdrom/info", 'r') as f:
            for line in f:
                if line.startswith("drive name:"):
                    try:
                        device = "/dev/" + line.split()[2]
                    except IndexError:
                        continue
    return device

def which(program):
    def is_exe(fpath):
        return os.path.exists(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    raise CommandNotFound("{0}: command not found".\
                          format(program))

def sync():
    run_simple_command("sync")

def is_mounted(device):
    with open("/etc/mtab", 'r') as f:
        for line in f:
            if line.find(device) > -1:
                return True
    return False

def check_if_root():
    if os.getuid() == 0:
        return True
    return False

def verify_4k(hd = "sda"):
    '''
    Retorna o tamanho fisico do setor
    '''
    try:
        f = open("/sys/block/{0}/queue/physical_block_size".format(hd))
        block = f.readline()
        if "4096" in block:
            return(4096)
        #se nao for 4K, considera-se 512
        return(512)
    except Exception as e:
        #nao tem HD (uma vm sem hd, por exemplo)
        return(512)

