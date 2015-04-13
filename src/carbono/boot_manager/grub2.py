#!/usr/bin/python
# coding: utf-8

# Author: MStech <http://www.mstech.com.br>
# Bruno Fernandes Casella <bruno.casella@mstech.com.br>

from carbono.utils import *
from carbono.boot_manager.utils_misc import *
from carbono.boot_manager.disk_utils import *
from carbono.log import log

class Grub2:

    def build_grub2_menu(self, directory, arq=None):

        boot_folder = directory+"boot"
        if arq is None:
            arq = "grub.cfg"
        output,erro,ret = run_simple_command_echo("grub-mkconfig -o \
          {0}/grub/{1}".format(boot_folder,arq),True)
        if ret is not 0:
            log.error("Generating Grub2 config file failed")
            log.error("error output={0} command output={1}".format(erro,output))
            return False
        else:
            return True
        
    def install_grub2(self, device, directory):

        boot_folder = directory+"boot"
        dev = device[:8]
       
        output,erro,ret = run_simple_command_echo("grub-install \
          --root-directory={0} {1}".format(directory, dev),True)
        if ret is not 0:
            log.error("error output={0} command output={1}".format(erro,output))
            return False
        else:
            return True
