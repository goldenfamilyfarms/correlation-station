#!/usr/bin/env python

#
# Copyright (C) 2006-2018 by Ciena, Inc.
#
# All rights reserved.
#
# PROPRIETARY NOTICE
#
# This Software consists of confidential information.
# Trade secret law and copyright law protect this Software.
# The above notice of copyright on this Software does not indicate
# any actual or intended publication of such Software.
#
#
import socket
import time
import sys
sys.path.append('model-definitions')
from scripts.complete_and_terminate_plan import CompleteAndTerminatePlan


class Activate(CompleteAndTerminatePlan):
    DEFAULT_PORTS = [22, 23, 80]

    def process(self):
        # EXTRACTING DATA FROM REQUESTED RESOURCE
        props = self.resource["properties"]
        device_ip = props["device_ip"]
        device_port = props.get("device_port")
        timeout = props["timeout"]
        return_delay = props["return_delay"]
        retry_time = props["retry_time"]
        min_retry_count = props["min_retry_count"]
        try_timeout = props["try_timeout"]
        command = props.get("command")

        # Verify network connectivity
        device_connected = False
        timeout_time = int(time.time()) + timeout

        retry_count = 0
        while int(time.time()) < timeout_time or retry_count < min_retry_count:
            self.logger.debug(
                f"Checking connectivity ({((timeout_time - int(time.time())) / retry_time)} retries remaining)"
            )
            device_connected = self.is_device_reachable(device_ip, device_port, try_timeout, command)
            if device_connected:
                self.logger.debug("Device: " + device_ip + " successfully connected")
                break
            else:
                self.logger.debug(f"Cannot connect to device. Retry in {retry_time} seconds")

            time.sleep(retry_time)
            retry_count += 1

        if not device_connected:
            raise Exception(f"Unable to connect to device at {device_ip}")

        time.sleep(return_delay)

    def is_device_reachable(self, access_ip, port, try_timeout, command):
        """
        Checks the device connection through the use of a socket connection to
        the specified port.

        @param access_ip: IP Address that will be used
        @param port: IP Address port to connect to
        @param try_timeout: Specific time in seconds to timeout the connection
        @param command: After connection is made the command to run (not implemented yet)

        @return: True if the device connected successfully
        """
        reachable = False
        s = None

        ports = []
        if port is None:
            ports = self.DEFAULT_PORTS
        else:
            ports = [port]

        for port in ports:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(try_timeout)
                s.connect((access_ip, port))
                reachable = True
                self.logger.debug("Device: " + access_ip + " successfully connected on port: " + str(port))
                break
            except Exception as e:
                self.logger.debug(f"Exception in connection to device: {str(e)} on port {port}")
                continue

        try:
            s.close()
        except Exception:
            pass

        return reachable
