#!/usr/bin/env python

from setuptools import setup
import os
import json

# Allow to run setup.py from another directory.
os.chdir(os.path.dirname(os.path.abspath(__file__)))

with open("version.json") as f:
    data = json.load(f)

setup(name=data["name"], version=data["version"])
