#!/usr/bin/python
# coding: utf-8

# Author: MStech <http://www.mstech.com.br>
# Bruno Fernandes Casella <bruno.casella@mstech.com.br>

import os
import parted
from carbono.device import Device
from carbono.disk import Disk
from carbono.utils import *
from carbono.boot_manager.utils_misc import *
from carbono.log import log

mounted_devices = []    
MOUNT_OPTIONS = ""

def list_devices(device):
    devices_linux = []
    devices_windows = []
    #device = device[:8]
    device="/dev/{0}".format(device)
    try:
        p = parted.Device(device)
        disk = parted.Disk(p)
        for i in disk.partitions:
            if "ext" in "{0}".format(i.fileSystem):
                devices_linux.append("{0}".format(i.path))
            elif ("ntfs" in "{0}".format(i.fileSystem)) or ("fat" in "{0}".format(i.fileSystem)):
                devices_windows.append("{0}".format(i.path))
        
        devices_linux.sort()
        bubble_sort(devices_linux)        

        return devices_linux, devices_windows
    except:
        return None,None

def get_filesystem_type(device):

    dev = device[:8]
    p = parted.Device(dev)
    t = parted.Disk(p)
    pt =  parted.Disk.getPrimaryPartitions(t)
    ptl = parted.Disk.getLogicalPartitions(t)
    for i in pt:
        #scan the primary partitions
        if device in i.path:
            if "ext" in "{0}".format(i.fileSystem):
                fileS = "ext"
            elif ("ntfs" in "{0}".format(i.fileSystem)):
                fileS = "win"                    
            elif ("fat" in "{0}".format(i.fileSystem)):
                fileS = "fat"
            elif "swap" in "{0}".format(i.fileSystem):
                fileS = "swap"
            else:
                fileS = "other"
            return fileS
    for i in ptl:
        #scan the logical partitions
        if device in i.path:
            if "ext" in "{0}".format(i.fileSystem):
                fileS = "ext"
            elif ("ntfs" in "{0}".format(i.fileSystem)):
                fileS = "win"
            elif ("fat" in "{0}".format(i.fileSystem)):
                fileS = "fat"
            elif "swap" in "{0}".format(i.fileSystem):
                fileS = "swap"
            else:
                fileS = "other"
            return fileS
        #print "\nsda{0} --> {1} --> {2}\n".format(i.path,i.type,fileS)

    
def mount_device(device,folder):
    '''
    Mount devices (as /dev, /sys)
    Usefull to mount chroot needed devices
    ''' 
    if folder is None:
        log.error("No folder as received as mounting point")
    if device is None:
        log.error("No device as received to mount")
    output,erro,ret = run_simple_command_echo("mount -o bind /{0} {1}{0}".format(device, folder),True)
    if ret is not 0:
        log.error("error output={0} command output={1}".format(erro,output))
        raise ErrorMountingFilesystem
    mounted_devices.insert(0,"{0}{1}".format(folder,device))    

def mount_partition(device, folder = None):
    ''' 
    Monta a particao recebida.(Ex.: /dev/sda1)
    Caso 'folder'  nao tenha um destino valido,
     a particao eh montada em uma pasta temporaria
    '''
    mount_device = None    
    if folder is None:
        tmpd = make_temp_dir()
    else:
        tmpd = folder

    if device is None:
        log.error("No device given")
        return False
        
    output,erro,ret =  run_simple_command_echo("mount {0} {1} {2}".format(MOUNT_OPTIONS, 
        device, tmpd),True)
        
    if "already" in erro:
        log.error("{0} is arealdy exclusively mounted.".format(mount_device))
        log.info("Trying to umount device above, and re-run")
        umount_real(mount_device)
        output,erro,ret =  run_simple_command_echo("mount {0} {1} {2}".format(MOUNT_OPTIONS, 
            mount_device, tmpd),True)
            
    if ret is not 0:
        log.error("{0}".format(erro))
        
        #raise ErrorMountingFilesystem
    if folder is not None:
        mounted_devices.insert(0, folder)
    else:
        mounted_devices.append(tmpd)
        return tmpd    

def umount_partition(directory):
    '''
    Desmonta a ultima particao montada
    ou a pasta/particao recebida 
    '''
    if directory is None:
        log.error("directory to umount not received")
        return None        
    run_simple_command_echo("sync")
    output,erro,ret = run_simple_command_echo("umount {0}".format(directory),True)
    
    if ret is 0:
        #pops the mounted folder from the list
        for i in mounted_devices:
            if directory in i:
                mounted_devices.pop(mounted_devices.index(i))
    else:
        log.error("error output={0} command output={1}".format(erro,output))
        
    return ret


def get_boot_flag(device):
    ''' return if the device given has the boot flag or not'''
    dev = device[:8]
    p = parted.Device(dev)
    t = parted.Disk(p)
    cont=0
    for i in t.partitions:
        if i.getFlag(parted.PARTITION_BOOT):
            cont+=1
        if device in i.path:
            aux = i.getFlag(parted.PARTITION_BOOT)
    if cont >1:
        return False
    else:
        return aux

def unset_boot_flag(device):
    ''' unset the boot flag in the given device'''
    dev = device[:8]
    p = parted.Device(dev)
    t = parted.Disk(p)
    
    for i in t.partitions:
        if device in i.path:
            aux = i.unsetFlag(parted.PARTITION_BOOT)
            break
    t.commit()
    return aux

def unset_all_boot_flags(device):
    ''' unset all the boot flags'''
    dev = device[:8]
    p = parted.Device(dev)
    t = parted.Disk(p)
    for i in t.partitions:
            i.unsetFlag(parted.PARTITION_BOOT)
    t.commit()
    
    
def set_boot_flag(device):
    ''' set the boot flag in the given device'''
    dev = device[:8]
    p = parted.Device(dev)
    t = parted.Disk(p)
    for i in t.partitions:
        if device in i.path:
            aux = i.setFlag(parted.PARTITION_BOOT)
            break
    t.commit()
    return aux

            
def umount_all_devices():
    for i in mounted_devices:
        ret = umount_partition(i)
        if ret is not 0:
            log.warning("umount device {0} failed".format(i))
                #raise ErrorUmountingFilesystem        

def umount_real(device):
    while True:
        output,err,ret = run_simple_command_echo("umount {0}".format(device))
        if ("not" in err) or ("busy" in err):
            break

def umount_all_devices_system():
    mount_cmd,err,ret = run_simple_command_echo("mount")
    for j in ["a","b","c","d"]:
        for i in range(1,20):
            if "/dev/sd{0}{1}".format(j,i) in mount_cmd:
                umount_real("/dev/sd{0}{1}".format(j,i))

def chroot(root):
    real_root = os.open("/", os.O_RDONLY)
    mount_device("dev",root)
    mount_device("sys",root)
    mount_device("proc",root)
    os.chdir(root)
    log.info("chroot {0}".format(root))
    os.chroot(root)
    return "/",real_root
    
def undo_chroot(real_root):
    log.info("Exiting chroot")
    os.fchdir(real_root)
    os.chroot(".")
    os.close(real_root)
    os.chdir("/")
