#!/usr/bin/python
# coding: utf-8

# Author: MStech <http://www.mstech.com.br>
# Bruno Fernandes Casella <bruno.casella@mstech.com.br>

from carbono.boot_manager.grub_legacy import GrubLegacy
from carbono.boot_manager.grub2 import Grub2
from carbono.boot_manager.syslinux import Syslinux
from carbono.boot_manager.disk_utils import *
from carbono.boot_manager.utils_misc import *
from carbono.log import log
#from shutil import move as moveFile
#from shutil import copy2 as copyFile

class BootManager:
    MOUNT_OPTIONS = ""
    GRUB2_OPTIONS = ""

    def __init__(self, source_device, boot_man="grub", make_config_file=False, chroot_option=False):
        self.device = source_device.strip()
        self.boot_manager = boot_man.lower()
        self.boot_manager = self.boot_manager.strip()
        self.chroot_option = chroot_option
        self.mounted_devices = []
        self.real_root = None
        self.dev_boot_tuples = None
        self.make_config_file = make_config_file
        
    def install_boot_manager(self, boot_only_dev=None, dev_boot_tuples=None):
        #dev_boot_tuples --> lista de duplas do tipo (particao_boot_sistema1, particao_sistema1)
        
        self.dev_boot_tuples = dev_boot_tuples
        directory = mount_partition(self.device)
        boot_folder = directory+"boot"
            
        if (boot_only_dev is not None) and (boot_only_dev):
            mount_partition(boot_only_dev,directory+"boot")
            
        if "grub2" in self.boot_manager:
            boot_opt = Grub2()
            if self.chroot_option:
                directory,self.real_root = chroot(directory)
            if self.make_config_file:
                #on live cd, this only works under chroot
                if not self.chroot_option:
                    directory,self.real_root = chroot(directory)                        
                if boot_opt.build_grub2_menu(directory):
                    log.warning("Grub2 config file generated")
            if boot_opt.install_grub2(self.device, directory):
                log.warning("Grub2 successfully installed")
            else:
                log.error("Installing Grub2 failed")
                
        elif "grub" in self.boot_manager:
            boot_opt=GrubLegacy()
            
            if self.chroot_option:
                directory,self.real_root = chroot(directory)         
                boot_folder="/boot"
            version=grub_version()
            if ("grub-legacy" in version) and version:
                if self.make_config_file:
                    boot_opt.build_grub_legacy_menu(boot_folder,dev_boot_tuples)            
                if boot_opt.install_grub_legacy(self.device, directory):
                    log.warning("Grub-Legacy successfully installed")
                else:
                    log.error("Installing Grub-Legacy failed")
            else:
                boot_opt = Grub2()
                log.error("Grub-legacy is not installed in {0}".format(self.device))
                log.warning("INSTALING GRUB2 INSTEAD")
                if self.make_config_file:
                    if boot_opt.build_grub2_menu(directory):
                        log.warning("Grub2 config file generated")
                if boot_opt.install_grub2(self.device, directory):
                    log.warning("Grub2 successfully installed")
                else:
                    log.error("Installing Grub2 failed")

        elif "syslinux" in self.boot_manager:
            boot_opt = Syslinux()
            if self.chroot_option:
                directory,self.real_root=chroot(directory) 
                boot_folder="/boot"
            if self.make_config_file:

                boot_opt.build_sislinux_menu(boot_folder,dev_boot_tuples)
            if boot_opt.install_syslinux(self.device,directory):
                log.warning("Syslinux successfully installed")
            else:
                log.error("Installing Syslinux failed")

        if self.chroot_option:
            try:
                undo_chroot(self.real_root)
            except:
                log.error("chroot exit failed")
        
        umount_all_devices()
        umount_all_devices_system()
