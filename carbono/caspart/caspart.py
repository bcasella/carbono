#!/usr/bin/python
# coding: utf-8

# Author: MStech <http://www.mstech.com.br>
# Bruno Fernandes Casella <bruno.casella@mstech.com.br>
import re

from carbono.log import log
from carbono.caspart.utils_misc import *

class CasPart:

    def __init__(self, particoes = None):
        '''
        recebe um dicionario de particao e tamanho em MB
        eg.: {'/dev/sda1': 20480, '/dev/sda2': 1024}
        '''
        if particoes is not None:
            self.particoes = particoes
        else:
            log.error("Nao foi informada nenhuma particao a ser criada.")
        
    def verify_4k(self, hd = 'sda'):
        '''
        Verifica o tipo de tamanho fisico dos blocos da HD
        Se for 4096bytes, retorna True
        Caso contrario (512 bytes) retorna False
        '''
        f = open("/sys/block/{0}/queue/physical_block_size".format(hd))
        physical_block_size = f.readline()
        if physical_block_size == "4096":
            return True
        return False
        

    def fdisk_parser(self, hd='sda'):
        '''
            Pega informacoes da hd a partir do comando fdisk -l
        '''        
        
        info = {'sector_size_physical': 0, 'sector_size_logical': 0,
                       'cylinders_number': 0, 'sectors_per_track': 0,
                       'total_sectors': 0, 'disk_size':0}
                
        out,err,ret = run_simple_command_echo("fdisk -l /dev/{0}".format(hd))
        if ret is not 0:
            print "Erro ao pegar informacoes do hd"

        for linha in out.splitlines():
            if "Disk /dev/{0}".format(hd) in linha:

                #split the numbers of the line into a list
                #them get the last occurence, 
                #which is the size of the disk in bytes
                info['disk_size'] = re.findall('\d+',linha)[-1]
            elif "cylinders" in linha:

                #[heads (nao usado), sectors/track, cylinders, total sectors]
                lst_aux = re.split('[,]',linha)
                for str_aux in lst_aux:
                    if "sectors/track" in str_aux:
                        info['sectors_per_track'] = re.findall('\d+', str_aux)[-1]
                    elif "cylinders" in str_aux:
                        info['cylinders_number'] = re.findall('\d+', str_aux)[-1]
                    elif "total" in str_aux:
                        info['total_sectors'] = re.findall('\d+', str_aux)[-1]
            elif "Sector size" in linha:
                #[logical, physical]
                info['sector_size_logical'] = re.findall('\d+',linha)[0]
                #info['sector_size_physical'] = re.findall('\d+',linha)[-1]
        
        return info

    
    def get_hd_info(self, hd = 'sda'):
        
        hd_info_dic = {'sector_size_physical': 0, 'sector_size_logical': 0,
                       'cylinders_number': 0, 'sectors_per_track': 0,
                       'total_sectors': 0, 'disk_size':0, 'ptable_type': None}
        
        parser_info = self.fdisk_parser(hd)
        
        for aux in parser_info:   
            hd_info_dic[aux] = parser_info[aux]
        
        hd_info_dic['sector_size_physical'] = 4096 if self.verify_4k(hd) else 512
        hd_info_dic['ptable_type'] = 'gpt' if self.verify_gpt(hd) else 'mbr'
        
        return hd_info_dic
                
                       
    def verify_gpt(self, hd = 'sda'):
        '''
        Verifica se a tabela de particao é GPT
        '''
        out,err,ret = run_simple_command_echo("fdisk -l /dev/{0}".format(hd))
        if ret is not 0:
            print "Erro ao verificar tipo da tabela de particao. {0}".format(err)
        if "gpt" in out.lower():
            return True
        return False
