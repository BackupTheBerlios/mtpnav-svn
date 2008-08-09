#!/usr/bin/env python
# 
# Setup.py for MTPnavigator
#

from distutils.core import setup

setup(name = "MTPnavigator",
      version = "0.0.2a",
      description = "Manage your portable media player",
      author = "Jerome Chabod",
      author_email = "jerome.chabod@ifrance.com",
      url = "http://mtpnav.berlios.de",
      packages = ["mtpnavigator"],
      data_files=[("", ["mtpnavigator/MTPnavigator.xml"])]
      )

