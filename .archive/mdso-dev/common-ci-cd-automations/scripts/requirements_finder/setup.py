#!/usr/bin/env python

###############################################################################
# Copyright (C) 2019 by CIENA, Inc.                                           #
# All rights reserved.                                                        #
# PROPRIETARY NOTICE                                                          #
# This Software consists of confidential information.                         #
# Trade secret law and copyright law protect this Software.                   #
# The above notice of copyright on this Software does not indicate            #
# any actual or intended publication of such Software.                        #
###############################################################################


###############################################################################
#  _                            _                                             #
# (_)_ __ ___  _ __   ___  _ __| |_ ___                                       #
# | | '_ ` _ \| '_ \ / _ \| '__| __/ __|                                      #
# | | | | | | | |_) | (_) | |  | |_\__ \                                      #
# |_|_| |_| |_| .__/ \___/|_|   \__|___/                                      #
#             |_|                                                             #
###############################################################################
from setuptools import setup


setup(
    name='pypi_req_finder',
    version='0.0.7',
    url='https://git.blueplanet.com/BluePlanet/DevTools/common-ci-cd-automations',
    license='CIENA',
    author='Michelle Nagamori-Trew',
    author_email='cnagamor@ciena.com',
    description='Find all python packages required for a repo',
    long_description='Gather all python packaged required for repo to build pypi',
    install_requires=[
        'toml',
        'argparse'
    ],
    packages=['pypi_req_finder', ],
    entry_points={
        'console_scripts': [
            'pypi_req_finder = pypi_req_finder.requirements_finder:main'
        ],
    },

    include_package_data=True
)
