#!/usr/bin/python
# coding: utf-8

# Author: MStech <http://www.mstech.com.br>
# Bruno Fernandes Casella <bruno.casella@mstech.com.br>

from shutil import copy2 as copyFile

from carbono.utils import *
from carbono.boot_manager.disk_utils import *
from carbono.boot_manager.utils_misc import *
from carbono.log import log

class Syslinux:

    def build_sislinux_menu(self,boot_folder,dev_boot_tuples = None):

        KERNEL_OPTIONS="ro quiet"#if trying to boot in a netbook, add boot=hdd
        cont = 0
        contador_win=0
        try:
            os.listdir("{0}/syslinux/".format(boot_folder))
            
        except:
            os.makedirs("{0}/syslinux/".format(boot_folder))
        FILE = "{0}/syslinux/syslinux.cfg".format(boot_folder)            
        try:            
            f = open(FILE,"w")            
        except:
            ret,err,out = run_simple_command_echo("touch {0}/syslinux/syslinux.cfg".format(boot_folder))
            f = open(FILE,"w")            

        menu_linux = []
        menu_windows = []
        menu_linux.append("UI menu.c32\n")
        menu_linux.append("PROMPT 1\n")
        menu_linux.append("TIMEOUT 100\n")         
        contador_label=0
        
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
                            boot_me = "/boot/"                
                            for aux in filenames:
                                if "init" in aux:
                                    initrd = aux
                                    if len(aux) < 12:
                                        var_temp=""
                                    else:
                                        var_temp = aux[11:] # take just the kernel version
                                elif (((var_temp is not None) and ("vmlinuz" in aux) and (var_temp in aux))
                                   or ("vmlinuz"==aux)):
                                    vmlinuz = aux
                                    cont+=1
                        if (filenames2 is not None) and (vmlinuz is None):
                            filenames2.sort()
                            boot_me = "/"                
                            for aux in filenames2:
                                if "init" in aux:
                                    initrd = aux
                                    if len(aux) < 12:
                                        var_temp=""
                                    else:
                                        var_temp = aux[11:] # take just the kernel version
                                elif (((var_temp is not None) and ("vmlinuz" in aux) and (var_temp in aux))
                                   or ("vmlinuz"==aux)):
                                    vmlinuz = aux#+"MAOEEE"
                                    cont+=1
                                    
                        if (vmlinuz is not None):
                            line = distro_name(directory)
                            if  line is None:
                                line = cont
                            temp = True
                            if (dev_boot_tuples is not None):
                                for i in dev_boot_tuples:
                                    if ((lin in i[0]) or (lin in i[1])):
                                        temp = False                        
                                        if (lin not in i[0]):
                                            contador_label+=1
                                            menu_linux.append("\nLABEL {0}\n".format(contador_label))
                                            menu_linux.append("MENU LABEL Linux {0} in {1}\n".format(line,lin))                       
                                            menu_linux.append("KERNEL {0}{1}\nAPPEND root={2} {3}\
                                                \n".format(boot_me,vmlinuz,i[1],KERNEL_OPTIONS))
                                            menu_linux.append("INITRD {0}{1}\n".format(boot_me,initrd))
                                            break
                                        else:
                                            dev_boot_tuples.pop(dev_boot_tuples.index(i))
                                            break
                                if not dev_boot_tuples:
                                    dev_boot_tuples = None
                            if temp:
                                #if temp_dev is None:
                                contador_label+=1                            
                                menu_linux.append("\nLABEL {0}\n".format(contador_label))
                                menu_linux.append("MENU LABEL Linux {0} in {1}\n".format(line,lin))                       
                                menu_linux.append("KERNEL {0}{1}\nAPPEND root={2} {3}\
                                      \n".format(boot_me,vmlinuz,lin,KERNEL_OPTIONS))
                                menu_linux.append("INITRD {0}{1}\n".format(boot_me,initrd))                          
                                #else:
                                #   menu_linux.append("kernel {0}/{1} root = {2} ro quiet splash\
                                #      \n".format(boot_me,vmlinuz,temp_dev))
                                #    temp_dev = None


                        else:
                            temp_dev = lin   
                        
                        umount_partition(directory)
                cont = 0
            #fim for
                if devices_windows is not None:
                    for win in devices_windows:
                        filenames = None

                        directory = mount_partition(win)
                        try:
                            filenames = os.listdir("{0}".format(directory))
                        except:
                            log.warning("Folder {0} didn't exist or it'a empty".format(directory))
                        if filenames is not None:
                            bootWin = False
                            for i in filenames:
                                if "windows" in i.lower():
                                    bootWin = True
                            if bootWin:
                                windev = int(win[8:])
                                contador_label+=1                            
                                menu_windows.append("\nLABEL {0}\n".format(contador_label))
                                menu_windows.append("MENU LABEL Windows\n") 
                                menu_windows.append("COM32 chain.c32\n")
                                menu_windows.append("APPEND hd{0} {1}\n".format(contador_win,windev))
                                contador_win+=1

        menu_windows.append("\nLABEL Reboot\n")
        menu_windows.append("MENU LABEL Reboot\n")
        menu_windows.append("COM32 reboot.c32\n")
        menu_windows.append("\nLABEL Shutdown\n")
        menu_windows.append("MENU LABEL Shutdown\n")
        menu_windows.append("COMBOOT poweroff.com\n")                        
        for i in menu_linux:
            f.write(i)
        for i in menu_windows:
            f.write(i)
        f.close()


    def install_syslinux(self, device, directory):
    
        boot_folder = directory+"boot"
        dev = device[:8]
        try:
            log.info("cp /usr/lib/syslinux/menu.c32 {0}/syslinux".format(boot_folder))
            copyFile("/usr/lib/syslinux/menu.c32", boot_folder+"/syslinux")
            log.info("cp /usr/lib/syslinux/chain.c32 {0}/syslinux".format(boot_folder))
            copyFile("/usr/lib/syslinux/chain.c32", boot_folder+"/syslinux")
            log.info("cp /usr/lib/syslinux/reboot.c32 {0}/syslinux".format(boot_folder))
            copyFile("/usr/lib/syslinux/reboot.c32", boot_folder+"/syslinux")
            log.info("cp /usr/lib/syslinux/poweroff.com {0}/syslinux".format(boot_folder))
            copyFile("/usr/lib/syslinux/poweroff.com", boot_folder+"/syslinux")

        except:
            log.error("Error copying files")
            return False
        try:
            aux = get_filesystem_type(device)
            if "fat" in aux:
               run_simple_command_echo("syslinux -d {0}/syslinux {1}".format(boot_folder,device),True)
            elif "ext" in aux:
                log.info("extlinux --install {0}/syslinux".format(boot_folder))                      
                run_simple_command_echo("extlinux --install {0}/syslinux".format(boot_folder),True)

            else:
                log.error("Filesystem not accepted.")
                return False

        except:
            log.error("installing syslinux in {0} failed".format(device))
            return False        
        try:
            run_simple_command_echo("dd if=/usr/lib/syslinux/mbr.bin of={0} \
                bs=440 conv=notrunc count=1".format(dev),True)
        except:
            log.error("dd failed")
            return False
            
        if not get_boot_flag(device):
            unset_all_boot_flags(device)
            if set_boot_flag(device):
                log.info("{0} has been set as bootable device".format(device))
        return True
