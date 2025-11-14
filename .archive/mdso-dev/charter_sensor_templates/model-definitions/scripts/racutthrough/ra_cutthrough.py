""" -*- coding: utf-8 -*-

RA Cut Through Package

This package provides a way to execute commands directly to an RA REST interface
without having to go through the MDSO Market.  If there is no session or the session
is down to the RA, an exception will be responded.

To Use:
    Review the `execute_ra_command_file()`.  Here you can specify the command
    file and parameters.

    There are class variables that  will perform retries if there is a HTTP error
    response as a debounce:
        self.NumberOfRetries   # Number of time to retry (Default = 1)
        self.WaitSeconds       # Time between retries in seconds (Default = 5)

    Example to execute the show-device.json().
        self.execute_ra_command_file("AUSDTXIR2CW.ONE.TWCBIZ.COM", "show-device.json")

    Response:
        {
            'command': 'show-device.json',
            'result': {
                'swImage': 'JUNOS 16.1R6-S2.3',
                'swVersion': 'JUNOS 16.1R6-S2.3',
                'name': 'AUSDTXIR2CW',
                'resourceType': 'JuniperMX480',
                'serialNumber': 'JN111D794AFB',
                'swType': 'JUNOS',
                'type': 'JuniperMX480',
                'deviceVersion': 'JuniperMX480'
            },
            'parameters': {}
        }


Versions:
   0.1 Sept 17, 2018
       Initial check in of RaCutThrough plans

"""

import sys

sys.path.append("model-definitions")
import requests
import time
import json
import re
from scripts.common_plan import CommonPlan


class RaCutThrough(CommonPlan):
    BUILT_IN_NETWORK_FUNCTION_TYPE = "tosca.resourceTypes.NetworkFunction"
    SESSION_URL = "http://blueplanet:80/ractrl/api/v1/sessions/{}"
    URL_MAIN_REGEX = "([^\n\r]+/v[0-9]/)[^\n\r]+/(bpo_[^/]+)"
    RA_PRID_REGEX = "[^:]+::([^/n/r]+)"
    RA_RESOURCE_TYPE_COMMAND = "execute-resource-type-command.json"
    NumberOfRetries = 1
    WaitSeconds = 5
    UrlLookup = {}

    def get_ra_resources_by_type(self, device, rtype):
        """executes the LIST command for the resource type

        :param device: Device IP, ID or provierResourceId
        :param rtype: resource type
        :type device: str or dict
        :type type: str

        :return: response of command
        :rtype: tuple (status_code, reason, json())
        """
        return self.execute_ra_command_file(
            device, self.RA_RESOURCE_TYPE_COMMAND, {"resourceType": rtype, "command": "LIST"}
        )

    def get_ra_resource_by_id_and_type(self, device, prid, rtype):
        """executes a GET command to get a specific resource from a device

        If the resource is not found (404), None is returned.

        :param device: Device IP, ID or provierResourceId
        :param prid: Provider resource ID of the resource either from BPO or the RA
        :param rtype: resource type
        :type device: str or dict
        :type prid: Either the BPO PRID ("bpo_..::TPE_1" or just the specific name "TPE_1")
        :type type: str

        :return: response of command
        :rtype: tuple (status_code, reason, json())
        """
        data = self.__get_base_ra_data(prid, rtype)
        data["command"] = "GET"

        return self.execute_ra_command_file(device, self.RA_RESOURCE_TYPE_COMMAND, data)

    def update_ra_resource(self, device, prid, rtype, data):
        """executes the LIST command for the resource type

        :param device: Device IP, ID or provierResourceId
        :param prid: Provider resource ID of the resource either from BPO or the RA
        :param rtype: resource type
        :param data: data to update, needs to be full resource
        :type device: str or dict
        :type prid: Either the BPO PRID ("bpo_..::TPE_1" or just the specific name "TPE_1")
        :type type: str
        :type data: object

        :return: response of command
        :rtype: tuple (status_code, reason, json())
        """
        data = data.update(self.__get_base_ra_data(prid, rtype))
        data["command"] = "PUT"

        return self.execute_ra_command_file(device, self.RA_RESOURCE_TYPE_COMMAND, data)

    def create_ra_resource(self, device, rtype, data):
        """executes the LIST command for the resource type

        :param device: Device IP, ID or provierResourceId
        :param rtype: resource type
        :param data: data to update, needs to be full resource
        :type device: str or dict
        :type type: str
        :type data: object

        :return: response of command
        :rtype: tuple (status_code, reason, json())
        """
        data["resourceType"] = rtype
        data["command"] = "POST"

        return self.execute_ra_command_file(device, self.RA_RESOURCE_TYPE_COMMAND, data)

    def delete_ra_resource(self, device, prid, rtype):
        """executes a DELETE command to get a specific resource from a device

        If the resource is not found (404), None is returned.

        :param device: Device IP, ID or provierResourceId
        :param prid: Provider resource ID of the resource either from BPO or the RA
        :param rtype: resource type
        :type device: str or dict
        :type prid: Either the BPO PRID ("bpo_..::TPE_1" or just the specific name "TPE_1")
        :type type: str

        :return: response of command
        :rtype: tuple (status_code, reason, json())
        """
        data = self.__get_base_ra_data(prid, rtype)
        data["command"] = "DELETE"

        return self.execute_ra_command_file(device, self.RA_RESOURCE_TYPE_COMMAND, data)

    """
    def get_ra_resource_by_id_and_type(self, device, prid, rtype):
        ''' executes a GET command to get a specific resource from a device

        If the resource is not found (404), None is returned.

        :param device: Device IP, ID or provierResourceId
        :param prid: Provider resource ID of the resource either from BPO or the RA
        :param rtype: resource type
        :type device: str or dict
        :type prid: Either the BPO PRID ("bpo_..::TPE_1" or just the specific name "TPE_1")
        :type type: str

        :return: response of command
        :rtype: tuple (status_code, reason, json())
        '''
        if prid.startswith("bpo_"):
            search = re.search(self.RA_PRID_REGEX, prid)
            prid = search.group(1)
        ra_url = self.get_ra_domain_url_for_device(device)

        ra_url += "/resources/%s?resourceTypeId=%s" % (prid, rtype)
        self.logger.debug("RA Command: " + ra_url)

        response = None
        try:
            headers = {'Content-Type': 'application/json',
                       'Tenant-Id': self.params['bpTenantId']}
            response = self.__ra_get_with_retry(ra_url, headers=headers)
        except Exception as ex:
            self.logger.exception(ex)

        self.logger.debug("Returning response: " + str(response))
        return response
    """

    def execute_ra_command_file(self, device, command_file, parameters=None, headers=None):
        """executes the GET command file on the RA based on device

        The Device name, provideResourceId, IP, ID or object could be passed

        :param device: Device IP, ID or provierResourceId
        :param command_file: File on the RA to call
        :type device: str or dict
        :type command_file: str

        :return: response of command
        :rtype: tuple (status_code, reason, json())
        """
        if parameters is None:
            parameters = {}

        if not isinstance(device, dict) and device.startswith("bpo_"):
            ra_url = self.get_ra_device_url_for_session_id(device)
        else:
            ra_url = self.get_ra_device_url_for_device(device)

        ra_url += "/execute"
        self.logger.debug("RA Cuthrough url: " + ra_url)
        data = {"command": command_file, "parameters": parameters}

        return self.__ra_post_with_retry(ra_url, data=data, headers=headers)

    def get_session_id_for_device(self, device):
        """Returns the session id for the device

        :param device_id: Device
        :type device_id: str

        :return: session id for device
        :rtype: str
        """
        self.logger.debug("Device to get session id: %s" % (str(device)))
        if isinstance(device, dict):
            return device["providerResourceId"]
        else:
            if device in self.UrlLookup.keys():
                return self.UrlLookup[device]

            if self.is_string_uuid(device):
                device = self.bpo.resources.get(device)
            else:
                device = self.get_network_function_by_host(device)

        if isinstance(device, dict) is False or "providerResourceId" not in device.keys():
            raise Exception("Unable to find device resource for " + str(device))

        self.logger.debug("Session ID returned: " + device["providerResourceId"])
        return device["providerResourceId"]

    def get_ra_domain_url_for_device(self, device):
        """Returns the URL for the RA based on the device

        The Device name, IP, ID or object could be passed

        Exceptions when there is an error connecting the RACTL or if
        the session is not established.

        :param device_id: Device
        :type device_id: str

        :return: url for device
        :rtype: str
        """
        if not isinstance(device, dict) and device.startswith("bpo_"):
            ra_url = self.get_ra_device_url_for_session_id(device)
        else:
            ra_url = self.get_ra_device_url_for_device(device)

        search = re.search(self.URL_MAIN_REGEX, ra_url)
        device_rpid = search.group(2)
        return search.group(1) + "domains/" + device_rpid.split("_")[1]

    def get_ra_device_url_for_device(self, device):
        """Returns the URL for the RA based on the device

        The Device name, IP, ID or object could be passed

        Exceptions when there is an error connecting the RACTL or if
        the session is not established.

        :param device_id: Device
        :type device_id: str

        :return: url for device
        :rtype: str
        """
        if not isinstance(device, dict) and device in self.UrlLookup.keys():
            return self.UrlLookup[device]

        url = self.get_ra_device_url_for_session_id(self.get_session_id_for_device(device))

        if isinstance(device, dict):
            self.UrlLookup[device["providerResourceId"]] = url
            self.UrlLookup[device["label"]] = url
            self.UrlLookup[device["id"]] = url
            if "ipAddress" in device["properties"].keys():
                self.UrlLookup[device["properties"]["ipAddress"]] = url
        else:
            self.UrlLookup[device] = url

        return url

    def get_ra_url_for_session_id(self, session_id):
        """Returns the URL for the RA based in the session ID of the device

        Exceptions when there is an error connecting the RACTL or if
        the session is not established.

        :param session_id: Session ID of the device
        :type session_id: string

        :return: url for device
        :rtype: str
        """
        if session_id in self.UrlLookup.keys():
            return self.UrlLookup[session_id]

        response = self.__ra_get_with_retry(
            self.SESSION_URL.format(session_id), headers={"Content-Type": "application/json"}
        )
        if response is None:
            raise Exception("Unknown error occurred when attempting to get URL for session")

        # session_data = response.json()

        ra_url = "http://blueplanet:80/ractrl/api/v1/devices/" + str(session_id)

        return ra_url

    def __ra_get_with_retry(self, command, headers={}, ignore_status_codes=[]):
        """Performs the retry mechanism for the URL command.

        Uses the self.NumberOfRetries and self.WaitSeconds for the retry
        mechanisms.  If it is an error response, an Exception will be raised

        :param command: HTTP Command
        :param headers: HTTP Headers
        :param ignore_status_codes: List of integers that it will return
        :type command: string
        :type headers: dict
        :type ignore_status_codes: list of ints

        :return: response of command
        :rtype: tuple (status_code, reason, json())
        """
        if headers is None:
            headers = {"Content-Type": "application/json"}

        response = None
        latest_response_code = None
        try_index = 0

        while try_index == 0 or try_index <= self.NumberOfRetries:
            try_index += 1
            response = requests.get(command, headers=headers)
            self.logger.debug(
                "Response: try_number={}, status_code={}, reason={}, json={}".format(
                    str(try_index), response.status_code, response.reason, response.json()
                )
            )
            latest_response_code = response.status_code
            if (
                latest_response_code < 300
                or latest_response_code in ignore_status_codes
                or try_index > self.NumberOfRetries
            ):
                break
            self.logger.warn("Failure in executing command to RA, trying again in %s seconds." % str(self.WaitSeconds))
            time.sleep(self.WaitSeconds)

        if latest_response_code >= 300 and latest_response_code not in ignore_status_codes:
            raise Exception(
                "Error making URL call.  Code: %s, Response: %s" % (str(latest_response_code), response.reason)
            )

        return response

    def __ra_post_with_retry(self, url, data, headers=None, ignore_status_codes=[]):
        """Performs the retry mechanism for the URL command.

        Uses the self.NumberOfRetries and self.WaitSeconds for the retry
        mechanisms.  If it is an error response, an Exception will be raised

        :param command: HTTP Command
        :param parameters: Data Parameters for the POST call
        :param headers: HTTP Headers
        :param ignore_status_codes: List of integers that it will return
        :type command: string
        :type parameters: dict
        :type headers: dict
        :type ignore_status_codes: list of ints

        :return: response of command
        :rtype: tuple (status_code, reason, json())
        """
        if headers is None:
            headers = {"Content-Type": "application/json"}

        if data is None:
            data = {}

        response = None
        latest_response_code = None
        try_index = 0

        while try_index == 0 or try_index <= self.NumberOfRetries:
            try_index += 1
            response = requests.post(url, data=json.dumps(data), verify=False, headers=headers)
            self.logger.debug(
                "Response: try_number={}, status_code={}, reason={}, json={}".format(
                    str(try_index), response.status_code, response.reason, response.json()
                )
            )
            latest_response_code = response.status_code
            if (
                latest_response_code < 300
                or latest_response_code in ignore_status_codes
                or try_index > self.NumberOfRetries
            ):
                break
            self.logger.warn("Failure in executing command to RA, trying again in %s seconds." % str(self.WaitSeconds))
            time.sleep(self.WaitSeconds)

        if latest_response_code >= 300 and latest_response_code not in ignore_status_codes:
            reason = response.reason if response else "No response when attempting RA Post with retry"
            msg = self.error_formatter(
                self.SYSTEM_ERROR_TYPE,
                "RA Post",
                f"command: {data.get('command')} code: {str(latest_response_code)} response: {reason}",
            )
            raise Exception(msg)

        return response

    def is_string_uuid(self, string):
        """returns true if the input string is a Blue Planet UUID

        This can be used when a string input can be the label of the UUID
        of an object/resource.

        :param string: Arbitrary String
        :type string: str

        :return: True if the input string is a UUID
        :rtype: boolean
        """
        UUID_PATTERN = re.compile(r"^[\da-f]{8}-([\da-f]{4}-){3}[\da-f]{12}$", re.IGNORECASE)

        if UUID_PATTERN.match(string):
            return True
        else:
            return False

    def get_network_function_by_host(self, hostname):
        """returns the NetworkFunction that has the hostname

        If none are found, None is returned.

        :param hostname: IP or routeable name
        :type hostname: str

        :return: NetworkFunction
        :rtype: dict
        """
        self.logger.debug("Getting NetworkFunction for Host %s" % (hostname))

        return_value = None
        response = self.bpo.market.get(
            "/resources?resourceTypeId={}&limit=100000".format(self.BUILT_IN_NETWORK_FUNCTION_TYPE), return_full=True
        )
        if response["status_code"] > 210:
            self.logger.error("Unable to get NetworkFunction for " + hostname)
            raise Exception(
                "Error %s when attempting to get Network Functions from server" % str(response["status_code"])
            )
        else:
            for network_function in response["body"]["items"]:
                if hostname in self.get_host_from_network_function(network_function):
                    return_value = network_function
                    break

        self.logger.debug("Returning NetworkFunction %s for Host %s" % (str(return_value), hostname))
        return return_value

    def get_host_from_network_function(self, nf):
        """returns the NetworkFunction that has the hostname

        If none are found, None is returned.

        :param nf: Network Function
        :type nf: str

        :return: Hostname/IP address
        :rtype: list of str
        """
        return_value = []
        if "ipAddress" in nf["properties"].keys():
            return_value.append(nf["properties"]["ipAddress"])

        if "connection" in nf["properties"].keys() and "hostname" in nf["properties"]["connection"].keys():
            return_value.append(nf["properties"]["connection"]["hostname"])

        self.logger.debug("Returning host for NF: " + str(return_value))
        return return_value

    def __get_base_ra_data(self, prid, rtype):
        """returns an object with the ID keys set"""
        data = {}
        if prid.startswith("bpo_"):
            search = re.search(self.RA_PRID_REGEX, prid)
            prid = search.group(1)

        data["resourceType"] = rtype
        data["id"] = prid
        data["name"] = prid
        data["data"]["id"] = prid
        data["data"]["name"] = prid

        return data


class Test(RaCutThrough):
    EnableEnterExitLog = False

    def process(self):
        # "device": "5b96c4e8-ea8c-4c18-924b-fdc0b968b93c",
        # AUSDTXIR2CW.ONE.TWCBIZ.COM
        # "session_id": "bpo_5ad7abd7-a6dc-40cf-9cdf-b9192c64dc81_5b96c4e8-ea8c-4c18-924b-fdc0b968b93c"
        session_id = self.properties.get("session_id")
        device = self.properties.get("device")
        resource_type = self.properties.get("resource_type")
        provider_resource_id = self.properties.get("provider_resource_id")

        if session_id is not None:
            self.logger.info(
                "RA Command Response: " + str(self.execute_ra_command_file(session_id, "show-device.json").json())
            )

        if device is not None:
            if resource_type:
                self.logger.info(
                    "#######>> RA Command Response 1: "
                    + str(self.get_ra_resources_by_type(device, resource_type).json())
                )
                self.logger.info(
                    "#######>> RA Command Response 2: "
                    + str(self.get_ra_resource_by_id_and_type(device, provider_resource_id, resource_type).json())
                )
            else:
                self.logger.info(
                    "#######>> RA Command Response 1: "
                    + str(self.execute_ra_command_file(device, "show-device.json").json())
                )
                self.logger.info(
                    "#######>> RA Command Response 2: "
                    + str(self.execute_ra_command_file(device, "show-device.json").json())
                )
