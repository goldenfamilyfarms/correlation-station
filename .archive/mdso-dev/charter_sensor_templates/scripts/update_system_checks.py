#!/usr/bin/env python
#
# Copyright (C) 2006-2017 by Ciena, Corp.
#
# All rights reserved.
#
# PROPRIETARY NOTICE
#
# This Software consists of confidential information.
# Trade secret law and copyright law protect this Software.
# The above notice of copyright on this Software does not indicate
# any actual or intended publication of such Software.
import os
import sys
import logging
import json
import re
import time
import subprocess
from logging.handlers import RotatingFileHandler
from subprocess import check_output
from lib.basebp import BaseBP
from lib.single_processor_instance import SingleProcessInstance

#
# Add local python path
#
sys.path.append(os.path.abspath(os.path.dirname(sys.argv[0])) + "/lib")

#
# GLOBAL VARS
#
APPLICATION_NAME = "system_check"
VERSION = "17.10.01"
BASE_DIR = "/tmp"

if os.path.exists("/bp2"):
    BASE_DIR = "/bp2"
elif os.path.exists("/opt/ciena/bp2"):
    BASE_DIR = "/opt/ciena/bp2"

APP_DIR = os.path.join(BASE_DIR, APPLICATION_NAME + "_" + VERSION + "_0")
LOG_DIR = os.path.join(APP_DIR, "log")
DATA_DIR = os.path.join(APP_DIR, "data")
#
# App Variables
#
NAGIOS_CHECK_RT = "nagios.resourceTypes.NagiosTest"
KAFKA_LAG_TEST_NAME = "KAFKA_LAG_CHECK"

#
# Initialized Variables
#
logger = logging.getLogger(__name__)


class UpdateSystemChecks:
    def __init__(self):
        # Set up logging directory
        self.start_time = int(time.time())

        log_file_name = os.path.join(LOG_DIR, APPLICATION_NAME + ".log")

        for dir in [APP_DIR, LOG_DIR, DATA_DIR]:
            if not os.path.exists(dir):
                os.makedirs(dir)

        #
        # Logging specifics
        #
        logging.basicConfig(
            format="%(asctime)s [%(levelname)s] %(thread)d %(module)s.%(funcName)s() %(message)s",
            level=logging.DEBUG,
            filename=log_file_name,
        )
        handler = RotatingFileHandler(log_file_name, maxBytes=500000, backupCount=5)
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(handler)

        #
        # check is another instance of same program running
        #
        pid_file_name = "/var/tmp/" + os.path.basename(sys.argv[0]) + ".pid"
        single_process_instance = SingleProcessInstance(pid_file_name)

        if single_process_instance.alreadyrunning():
            self.logger.warning("Another instance of this program is already running")
            sys.exit("Another instance of this program is already running")

        self.logger.info("==================> First log in process...")

        #
        # Initialize BPO Plan
        #
        self.bpo_plan = BaseBP()

        #
        # Go through the on-boarded tests
        #
        for test_resource in self.get_test_check_resources(self.bpo_plan):
            resource_props = test_resource["properties"]
            test_file = resource_props.get("test_file")

            if test_file is None:
                continue

            try:
                if os.path.exists(test_file) is False:
                    self.logger.warning("Test file '%s' does not exists" % test_file)
                    self.update_test_check_resources(
                        test_resource,
                        {
                            "results_status": "UNKNOWN",
                            "results_message": "Test file '%s' does not exists" % test_file,
                            "results": {},
                        },
                    )
                    continue

                self.logger.info("Executing test file: " + test_file)

                info_to_pass = {
                    "resourceId": test_resource["id"],
                    "testName": resource_props["test_name"],
                    "logDirectory": LOG_DIR,
                }
                # output,error = subprocess.Popen(["sudo", test_file, json.dumps(info_to_pass)]).communicate()
                output, error = subprocess.Popen(
                    ["sudo", test_file, json.dumps(info_to_pass)], stdout=subprocess.PIPE, stderr=subprocess.PIPE
                ).communicate()
                # result = subprocess.check_output(["sudo %s %s" % (test_file, json.dumps(json.dumps(info_to_pass)))])
                self.logger.debug("Output from testing: " + output)
                self.update_test_check_resources(test_resource, json.loads(output))

            except Exception as e:
                self.logger.exception(e)

        self.logger.info("Completed test, time: %s secs" % str(time.time() - self.start_time))

    #
    # Public Methods
    #
    def get_container_ip(self, name_regex):
        """
        Inspect file /etc/hosts and return ip addresses for host matching regex
        """
        ips = []

        hosts = check_output(["cat", "/etc/hosts"]).split("\n")

        for host in hosts:
            m = re.search("^(\d+.\d+.\d+.\d+)(\s+\S+\s+|\s+)(%s)$" % name_regex, host)

            if m:
                ips.append(m.group(1))

        if not ips:
            raise RuntimeError("Could not locate %s in /etc/hosts" % name_regex)

        self.logger.info("Found %s hosts %s in /etc/hosts" % (name_regex, ips))

        return ips

    def update_test_check_resources(self, resource, test):
        """creates the trace resource"""
        self.logger.debug("Test resource passed: " + json.dumps(test, indent=2))
        inputs = {
            "results": {
                "status": test["results_status"],
                "results": test["results"],
                "results_message": test["results_message"],
            }
        }
        self.logger.info("%s Test Results: %s" % (resource["label"], json.dumps(inputs, indent=2)))
        self.bpo_plan.exec_operation(resource["id"], "update_results", inputs)

    def get_test_check_resources(self, plan):
        """return the scheduler trace resource"""
        resources = []
        try:
            for resource in plan.get_resources_by_type(NAGIOS_CHECK_RT):
                if resource["orchState"] == "active":
                    resources.append(resource)

        except Exception as ex:
            logger.exception(ex)

        return resources


if __name__ == "__main__":
    usc = UpdateSystemChecks()
