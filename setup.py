#!/usr/bin/python
import os
from setuptools import setup
from carbono.config import get_version

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name = "carbono",
    version = get_version(),
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
