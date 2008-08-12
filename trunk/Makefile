#
#    MTP navigator - Easily manage your MTP based portable media player
#    Copyright (c) 2008 Jérôme Chabod
#
#    MTP navigator is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#    
#    MTP navigator is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#    
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##########################################################################

DESTDIR ?= /
PREFIX ?= /usr

# default editor of user has not set "EDITOR" env variable
EDITOR ?= vim

##########################################################################

all: help

help:
	@echo 'make test:       run gpodder in local directory'
	@echo 'make release:    create source tarball in dist/'
	@echo 'make install:    install into $(PREFIX)'
	@echo 'make clean:      clean installation'
	@echo 'make glade2xml:  convert glade file to an xml file interpretabel by gtk.Builder'

##########################################################################

test: glade2xml
	python bin/mtpnavigator --local --debug

release: glade2xml
	python setup.py sdist

install: glade2xml
	python setup.py install --root=$(DESTDIR) --prefix=$(PREFIX)

clean: 
	python setup.py clean
	
glade2xml: data/MTPnavigator.glade
	gtk-builder-convert data/MTPnavigator.glade data/MTPnavigator.xml   
 
##########################################################################

.PHONY: all test release install clean glade2xml help

##########################################################################


