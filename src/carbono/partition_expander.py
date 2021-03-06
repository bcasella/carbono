#!/usr/bin/python
# coding: utf-8

# Author: MStech <http://www.mstech.com.br>
# Lucas Alvares Gomes <lucas.gomes@mstech.com.br>

import os
import subprocess
import logging
import parted
import time
from carbono.log import log

class PartitionExpander:

    def __init__(self, path):
        self.path = path

    def try_expand(self):
        """ """
        device = parted.Device(self.path)
        disk = parted.Disk(device)

        try:
            last_partition = disk.partitions[-1]
        except IndexError:
            log.error("The disk has no partitions")
            return -1

        # A partição deve ser primária e conter NTFS como sistema
        # de arquivos

        if last_partition.type != parted.PARTITION_NORMAL:
            log.error("The partition must be primary")
            return -1

        if last_partition.fileSystem is None:
            log.error("The partition hasn't filesystem")
            return -1

        #if last_partition.fileSystem is not None:
        #    if last_partition.fileSystem.type != "ntfs":
	    #        log.error("We only support ntfs filesystem for now")
	    #        return -1

        # Recria a última partição do disco utilizando
        # todo o espaço que desalocado
        start = last_partition.geometry.start
        fs = last_partition.fileSystem
        ped = last_partition.getPedPartition()

        disk.removePartition(last_partition)

        new_geometry = None
        if (len(disk.getFreeSpaceRegions()) == 1):
            new_geometry = disk.getFreeSpaceRegions()[0]
            new_geometry.start = start
        else:
            new_geometry = None
            for region in disk.getFreeSpaceRegions():
                if region.start == start:
                    new_geometry = region
                if (start > region.start and start < region.end):
                    new_geometry = region
                    new_geometry.start = start
        constraint = parted.Constraint(exactGeom=new_geometry)
        new_partition = parted.Partition(disk = disk,
                                         type = parted.PARTITION_NORMAL,
                                         fs = fs,
                                         geometry = new_geometry,
                                         PedPartition = ped)

        disk.addPartition(partition=new_partition, constraint=constraint)
        try:
            disk.commit()
        except:
            try:
                disk.commitToDevice()
                disk.commitToOS()
            except Exception as e:
                log.error("PartitionExpander : {0}".format(e))


        # Após criar a tabela de partição temos que fazer
        # com o kernel releia essa tabela. Será preciso
        # fazer isso para dar continuidade ao processo
        attempt = 0
        while True:
            p = subprocess.Popen("sfdisk -R %s" % device.path,
                                 shell = True,
                                 stderr = subprocess.PIPE,
                                 )

            if not len(p.stderr.readlines()):
                break

            if attempt >= 5:
                return -1

            attempt += 1
            time.sleep(2)

        # Apos o kernel re-ler a nova tabela de partição
        # temos que esperar o dispositivo ficar pronto
        attempt = 0
        while True:

            if os.path.exists(new_partition.path):
                break

            if attempt >= 5:
                return -1

            attempt += 1
            time.sleep(2)

        # Agora da um resize no sistema de arquivos
        # Pegar o tamanho total do dispositivo da partição a ser redimensionada
        size = new_partition.geometry.length * device.sectorSize

        return size
