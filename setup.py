#!/usr/bin/python
import os
from setuptools import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

VERSION_ID = "2.2.1"
BUILD_ID = "{0}-SNAPSHOT".format(VERSION_ID)
if 'BUILD_NUMBER' in os.environ:
    BUILD_ID = "{0}.{1}".format(VERSION_ID, os.environ['BUILD_NUMBER'])

setup(
    name = "carbono",
    version = BUILD_ID,
    author = "Bruno Casella",
    author_email = "bruno.casella@gmail.com",
    description = ("A hard disk imaging and recovery application"),
    license = "GPL",
    keywords = "network_manager dbus",
    url = "http://umago.info/carbono",
    packages = ["carbono","carbono.buffer_manager",
                  "carbono.filesystem", "carbono.ui",
                  "carbono.image_reader"],
    scripts = ["scripts/carbono"],
)
