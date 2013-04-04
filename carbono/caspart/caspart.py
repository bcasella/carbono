#!/usr/bin/python
# coding: utf-8

# Author: MStech <http://www.mstech.com.br>
# Bruno Fernandes Casella <bruno.casella@mstech.com.br>
import re
import parted

from _ped import partition_flag_get_by_name

from carbono.device import Device
from carbono.disk import Disk
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
        
    def _wait_devices(self, disk):
        """Wait OS create all device nodes"""
        for p in disk.partitions:
            while not os.path.exists(p.path):
                time.sleep(1)

    def verify_4k(self, hd = 'sda'):
        '''
        Verifica o tipo de tamanho fisico dos blocos da HD
        Se for 4096bytes, retorna True
        Caso contrario (512 bytes) retorna False
        '''
        f = open("/sys/block/{0}/queue/physical_block_size".format(hd))
        physical_block_size = f.readline()
        if "4096" in physical_block_size:
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

    def calculates_startofpart(self, end, size, disk='sda'):
        '''
        Given the end of the last partition and the size in GB of the current
        one, calculates where this one should start, returning a sector that
        don't give an cilinder conflict - where the end of last partition and
        the start of the new one is in the same cilinder - and also does not
        get an wrong sector - where it could place a start/and of a part in the
        middle of a 4096b sector.
        '''
        print "to aqui"
        hd_info_dict = self.get_hd_info(disk)
        cylinder_end = end/int(hd_info_dict['sectors_per_track'])
        cylinder_start = cylinder_end + 1
        sector_start = cylinder_start * int(hd_info_dict['sectors_per_track'])
        if self.verify_4k(disk):
            print sector_start
            sector_start *= 512
            
            print "why the luck{0}".format(sector_start % 4096)
            print (sector_start % 4096) / 4096
            if (sector_start % 4096):
                #sector_start += (sector_start % 4096)*4096 - (sector_start % 4096)
                sector_start += ((sector_start % 4096)/4096 +1) * 4096 - (sector_start % 4096) 
            sector_start /= 512
        return sector_start
        
        
        
    def calculates_endofpart(self, start, size_in_gb, disk='sda'):
        '''
        Given the size of the partition, gives where it should end
        It doesn't get a conflictant sector, just as the function above
        '''
        #hd_info_dict = get_hd_info(disk)
        print disk
        size = int(size_in_gb) * 1024 * 1024 *1024 #bytes
        if not self.verify_4k(disk):
            print "not 4k"
            #print start
            print size
            end = int(start)*512 + size
            if (end % 512):  #if end is not divisable by 512b, its wrong (?)
                #then, goes to the end of the next sector
                end += (end % 512)*512 - (end % 512)
                print end
            return end / 512            
        else: #4096b
            print "4k"
            end = int(start)*512 + size
            if (end % 4096):  #if end is not divisable by 4k, its wrong
                #then, goes to the end of that sector
                end += (end % 4096)*4096 - (end % 4096)
            return end / 512
        
    def partionate_disk(self, part_list = [['sda1','ntfs','30',''], 
                                           ['sda2','ext3','20','boot']]):
        '''
        particiona o disco
        '''
        for part in part_list:
            #get the hd using the 3 first letters of the 1st elem. of the dict.
            disk = "{0}".format(part[0][:3])
            break
        disk_path = "/dev/{0}".format(disk)
        device = Device(disk_path)            
        disk_obj = Disk(device)        
        start = end = 0
        layout = list() #objs of parted.partition will be added in the list
        disk_obj.unsetFlag(parted.DISK_CYLINDER_ALIGNMENT)
        for part in part_list:
            #got through all elements of the received dict
            
            if part[0][3:] == '1':
                #if is the 1st partition, then it should start at sector 2048
                start = 2048
                end = self.calculates_endofpart(start, part[2], disk)
            else:
                #starting from 2nd partition, we will make the calculus to where
                # it will start/end using the last partition ending
                start = self.calculates_startofpart(end, part[2], disk)
                
                end = self.calculates_endofpart(start, part[2], disk)
            #length = int(part[2]) * 1024 * 1024 *1024  / device.sectorSize
            length = end - start           
            #end = start + length - 1
            print "AQUI {0} {1} {2}".format(start,end,length)
            
            geometry = parted.geometry.Geometry(device = disk_obj.device,
                                                    start = start,
                                                    #length = length)
                                                    end = end)
            print "pqp"
            part_fs = None
            fs = part[1]
            print geometry
            if fs is not None:
                part_fs = parted.filesystem.FileSystem(type = fs,
                                                    geometry = geometry)
            print part_fs                                       
            partition = parted.partition.Partition(disk=disk_obj,
                                                   type=0,
                                                   geometry=geometry,
                                                   fs=part_fs)            
            #TODO swap e etc ?
            #partition.setFlag(partition_flag_get_by_name(p.flags))
            print partition
            print disk_obj.partitionAlignment
            layout.append(partition)
            
        disk_obj.deleteAllPartitions()
        
        #last_partition = len(layout)
        print layout
        constraint = parted.Constraint(device=disk_obj.device)
        for cont, partition in enumerate(layout, 1):
            disk_obj.addPartition(partition, constraint)
            #could use 'cont' to know if is the last part, 
            #and expand it to end of the hard drive

        #commit to device, OS and wait until OS create all devices nodes
        disk_obj.commitToDevice()
        disk_obj.commitToOS()
        self._wait_devices(disk_obj)
