#!/usr/bin/python
# coding: utf-8

# Author: MStech <http://www.mstech.com.br>
# Bruno Fernandes Casella <bruno.casella@mstech.com.br>

from carbono.utils import *
from carbono.boot_manager.utils_misc import *
from carbono.boot_manager.disk_utils import  *
from carbono.log import log

class GrubLegacy:

    def build_grub_legacy_menu(self,boot_folder, dev_boot_tuples=None):
    
        '''
        search for linux kernels in all devices. search windows boot files.
        built the menu.lst in the target device, also copy grub-legacy files there.
        '''
        cont = 0
        menu_linux = []
        menu_windows = []
        FILE = "{0}/grub/menu.lst".format(boot_folder)        
        try:
            f = open(FILE,"w")
        except:
            os.makedirs("{0}/grub/".format(boot_folder))
            ret,err,out = run_simple_command_echo("touch {0}/grub/menu.lst".format(boot_folder))
            f = open(FILE,"w")
        menu_linux.append("#AUTOMAGIC GENERATED\n")
        menu_linux.append("default saved\n")
        menu_linux.append("timeout 10\n")
        menu_linux.append("password --md5 $1$7QG0J0$l2j8MS763EKQ3u.sDdh8Z0\n")     
            
        dev = os.listdir("/dev")

        for i in dev:
            if ("sd" in i) and (len(i)==3):        
                devices_linux,devices_windows = list_devices(i)
                if devices_linux is not None:
                    for lin in devices_linux:
                        directory = mount_partition(lin)
                        boot_directory = directory+"/boot"
                        try:
                            filenames = os.listdir("{0}".format(boot_directory))
                        except:
                            filenames=None
                        try: 
                            filenames2 = os.listdir("{0}".format(directory))
                        except:
                            filenames2 = None
                        var_temp = None
                        vmlinuz = None
                        if filenames is not None:
                            filenames.sort()
                            boot_me = "/boot"                
                            for aux in filenames:
                                if "init" in aux:
                                    initrd = aux
                                    if len(aux) < 12:
                                        var_temp=""
                                    else:
                                        var_temp = aux[11:] # take just the kernel version
                                elif ((var_temp is not None) and ("vmlinuz" in aux) and (var_temp in aux)) or ("vmlinuz"==aux):
                                    vmlinuz = aux
                                    cont+=1
                        if (filenames2 is not None) and (vmlinuz is None):
                            filenames2.sort()
                            boot_me = ""                
                            for aux in filenames2:
                                if "init" in aux:
                                    initrd = aux
                                    if len(aux) < 12:
                                        var_temp=""
                                    else:
                                        var_temp = aux[11:] # take just the kernel version
                                elif ((var_temp is not None) and ("vmlinuz" in aux) and (var_temp in aux)) or ("vmlinuz"==aux):
                                    vmlinuz = aux#+"MAOEEE"
                                    cont+=1

                        if (vmlinuz is not None):
                            line = distro_name(directory)
                            if  line is None:
                                line = cont
                            menu_linux.append("\ntitle Linux {0} in {1}\n".format(line,lin))
                            menu_linux.append("root (hd0,{0})\n".format(int(lin[8:])-1))
                            temp = False
                            
                            if (dev_boot_tuples is not None):
                                for i in dev_boot_tuples:
                                    if lin in i[0]:
                                        temp = True
                                        menu_linux.append("kernel {0}/{1} root={2} ro quiet splash\
                                            \n".format(boot_me,vmlinuz,i[1]))
                                        dev_boot_tuples.pop(dev_boot_tuples.index(i))
                                if not dev_boot_tuples:
                                    dev_boot_tuples = None
                            if not temp:
                                #if temp_dev is None:
                                menu_linux.append("kernel {0}/{1} root={2} ro quiet splash\
                                      \n".format(boot_me,vmlinuz,lin))
                                #else:
                                #   menu_linux.append("kernel {0}/{1} root = {2} ro quiet splash\
                                #      \n".format(boot_me,vmlinuz,temp_dev))
                                #    temp_dev = None
                            menu_linux.append("initrd {0}/{1}\n".format(boot_me,initrd))
                            menu_linux.append("quiet\n")
                            menu_linux.append("savedefault\n")
                        else:
                            temp_dev = lin   
                        
                        umount_partition(directory)
                    cont = 0
                    for win in devices_windows:
                        cont+= 1
                        filenames = None
                        directory = mount_partition(win)
                        try:
                            filenames = os.listdir("{0}".format(directory))
                        except:
                            log.info("Folder {0} didn't exist or it'a empty".format(directory))

                        if filenames is not None:
                            bootWin = False
                            for i in filenames:
                                if "boot" in i.lower():
                                    bootWin = True
                            if bootWin:
                                windev = int(win[8:])
                                
                                menu_windows.append("\ntitle Windows {0}\n".format(cont))
                                '''
                                the two line below should exist if windows is on sdb
                                '''
                                if "1" not in win:
                                    #if windows is not in the firs filesystem
                                    menu_windows.append("map (hd0) (hd{0})\n".format(windev))
                                    menu_windows.append("map (hd{0}) (hd0)\n".format(windev)) 
                                menu_windows.append("rootnoverify (hd0,{0})\n".format(windev-1))
                                menu_windows.append("makeactive\n")
                                menu_windows.append("chainloader +1\n")

        for i in menu_linux:
            f.write(i)
        for i in menu_windows:
            f.write(i)
        f.close()
        
    def install_grub_legacy(self, device, directory):
        '''
        install grub-legacy in sdX, giving de mounted device as the root device
        '''
        boot_folder = directory+"boot"
        dev = device[:8]
        try:
            output,erro,ret = run_simple_command_echo("grub-install \
              --root-directory={0} {1}".format(directory, dev),True)
        except:
            run_simple_command_echo("grep -v rootfs /proc/mounts > /etc/mtab")
            output,erro,ret = run_simple_command_echo("grub-install \
              --root-directory={0} {1}".format(directory, dev),True)
        if ret is not 0:
            log.error("Grub installation failed. [grub-install \
              --root-directory={0} {1}]".format(directory, dev))
            log.error("error output={0} command output={1}".format(erro,output))
            return False
        else:
            return True        
        
