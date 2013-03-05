#!/usr/bin/python
# coding: utf-8

# Author: MStech <http://www.mstech.com.br>
# Bruno Fernandes Casella <bruno.casella@mstech.com.br>

import os
import subprocess
import shlex
import re
from carbono.log import log

def bubble_sort(list2):
    #swap_test = False
    for i in range(0, len(list2) - 1):
        swap_test = False
        for j in range(0, len(list2) - i - 1):
            if len(list2[j]) > len(list2[j + 1]):
                list2[j], list2[j + 1] = list2[j + 1], list2[j]  # swap
            swap_test = True
        if swap_test == False:
            break

def distro_name(directory):
    #Return the name of the linux distro, or "None" if it didn't find it
    try:
        expr = re.compile(r"\\+.+",re.DOTALL)
        files = os.listdir("{0}etc/".format(directory))
        tmp_filei = None
        tmp_filer = None
        for i in files:
            if "issue" in i:
                tmp_filei = "{0}/etc/issue".format(directory)
            elif "-release" in i:
                tmp_filer = "{0}/etc/{1}".format(directory,i)
        if tmp_filei is not None:
            FILE = tmp_filei
            fl = open(FILE,"r")
            line = fl.readline()
            line = expr.sub('',line)
        elif tmp_filer is not None:
            FILE = tmp_filer
            fl = open(FILE,"r")
            for l in fl:
                if "DISTRIB_DESCRIPTION" in l:
                    line = l[20:]
                    line = expr.sub('',line)
                    line = re.sub(r'"+','',line)
                    line = re.sub(r'\n+','',line)
        return line
    except:
        return None


def grub_version():
    try:
        version = os.popen("grub-install --version").read()
    except:
        log.error("Grub is not installed")
        return False
    if  "0.97" in version:
        return "grub-legacy"
    elif "1." in version:
        return "grub2"
    elif "GNU" in version:
        return "grub-legacy"        
        

def run_simple_command_echo(cmd, echo=False):
    ''' 
    run a given command
    returns the output, errors (if any) and returncode
    '''    
    if echo:
        log.info("{0}".format(cmd))
    p = subprocess.Popen(cmd, shell=True,
                         stdout=subprocess.PIPE,
                         stdin=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    p.wait()
    output, err = p.communicate()
    ret = p.returncode
    return output,err,ret
