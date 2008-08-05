#!/usr/bin/env python
# 
# Setup.py for MTPnavigator
#

from distutils.core import setup

setup(name = "MTPnavigator",
      version = "0.0.4",
      description = "Manage your portable media player",
      author = "Jérôme Chabod",
      author_email = "jerome.chabod@ifrance.com",
      url = "http://mtpnav.berlios.de",
      packages = ["mtpnavigator"]
      package_data={"mtpnavigator": ["MTPnavigator.xml"]}
      )

