#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Setup.py for MTPnavigator
#
import os

from distutils.core import setup



setup(name = "MTPnavigator",
    version = "0.1.a3",
    description = "Manage your portable media player",
    author = "Jérôme Chabod",
    author_email = "jerome.chabod@ifrance.com",
    url = "http://mtpnav.berlios.de",
    packages = ["mtpnavigator"],
    scripts = ["bin/mtpnavigator"],
    package_dir={'mtpnavigator': 'mtpnavigator'},
    data_files=[('share/mtpnavigator', ['data/MTPnavigator.xml']),
                ('share/applications', ['data/mtpnavigator.desktop'])],
    requires=["PyMTP(>=0.0.4)"]
)

