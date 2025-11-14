# Module: Makefile
#
# Copyright(c) 2017, Ciena All rights reserved.
#

HIDE ?= @
SRC_DIR := $(shell pwd)
VENV ?= env
REQ := requirements.txt
REQ_HOST := requirements-host.txt
PIP := $(VENV)/bin/pip
PYPI ?= 'https://artifactory.ciena.com/api/pypi/blueplanet-pypi/simple'

#
# Build rules
#

all: help

help:
	$(HIDE)echo "  help           Display this list"
	$(HIDE)echo "  prepare-venv    Setup virtual environment and install packages from $(REQ)"

prepare-venv:
	$(HIDE)virtualenv $(VENV)  --no-pip
	$(HIDE)$(VENV)/bin/easy_install pip==9.0.1
	$(HIDE)$(PIP) install -r $(REQ) 

clean:
	$(HIDE)find . -name \*.pyc -exec rm {} \;
	$(HIDE)rm -rf $(VENV) 
