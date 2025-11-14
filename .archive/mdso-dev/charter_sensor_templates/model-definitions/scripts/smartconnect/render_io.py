""" -*- coding: utf-8 -*-

Smart Connect Utilities

Versions:
   0.1 May 27, 2022
       Initial check in of Smart Connect plans

"""
import re
import textfsm
import xmltodict

from jinja2 import Environment, FileSystemLoader

import sys
sys.path.append('model-definitions')
from scripts.smartconnect.common_plan import SmartConnectCommon


class RenderInput(SmartConnectCommon):
    """
    Functionalities to render command template with provided variables
    Make command(s) ready to be sent to device
    """

    def __init__(self, vendor):
        """
        template: str, command template file name
        vendor: str, device vendor
        parameters: dict, command parameters mapped to variables in command template file
        connection_type: str, 'cli' or 'netconf'
        """
        self.command_directory = self.get_file_path("commands", vendor)

    def render_command_template(self, template, parameters=None):
        """generate command using template file and command parameters"""
        if parameters is None:
            parameters = {}
        file_loader = FileSystemLoader(self.command_directory)
        env = Environment(loader=file_loader)
        env.trim_blocks = True
        env.lstrip_blocks = True
        env.rstrip_blocks = True
        template = env.get_template(template)
        rendered_command_template = template.render(parameters)
        self.logger.info("Rendered command template:\n{}".format(rendered_command_template))
        return [rendered_command_template]

    def normalize_rendered_command_template(self, rendered_command_template, connection_type):
        # if there are multiple commands within the template, return list of commands for send_commands to iterate over
        # if only 1 command within template, return str for send_command or bytes for send_command netconf
        normalized_command_payload = (
            rendered_command_template[0].strip().split("\n") if connection_type == "cli" else rendered_command_template
        )
        if len(normalized_command_payload) > 1:
            return normalized_command_payload
        else:
            return normalized_command_payload[0] if connection_type == "cli" else normalized_command_payload[0].encode()


class RenderOutput(SmartConnectCommon):
    """Functionalities to render output from device into formatted data model"""

    def __init__(self, vendor, connection_type):
        self.vendor = vendor
        self.connection_type = connection_type
        if self.connection_type == "cli":
            self.fsm_directory = self.get_file_path("fsms", self.vendor)

    def format_device_response(self, device_response, template_name=None):
        if self.connection_type == "cli":
            return self.cli_formatter(device_response, template_name)
        if self.connection_type == "netconf":
            return self.netconf_formatter(device_response)

    def cli_formatter(self, device_response, template_name):
        device_response = "\n".join(map(str, device_response))
        with open(self.fsm_directory + "/{}.fsm".format(template_name)) as template:
            fsm = textfsm.TextFSM(template)
            parsed_response = fsm.ParseText(device_response)
        return [dict(zip(fsm.header, row)) for row in parsed_response]

    def netconf_formatter(self, device_response):
        device_response = "\n".join(map(str, device_response))
        if self.vendor == "JUNIPER":
            # Only return the rpc reply no fluff
            trimmed_response = re.search(r"(<rpc.+)", device_response, re.DOTALL)
            # Make valid xml file
            trimmed_response = re.sub(r"(]]>]]>)", "", trimmed_response.group(), re.MULTILINE)
            # Cleaning reponse up removing unecessary things
            trimmed_response = re.sub(r"(xmlns.+?(?=>|\s))", "", trimmed_response)
            parsed_response = xmltodict.parse(str(trimmed_response))
            # Shorten reponse to make retrieval easier
            # Removes rpc-reply and replaces with nested data to match arda expected data
            formatted_response = {key: parsed_response[key] for key in parsed_response if key != "rpc-reply"}
            formatted_response.update(parsed_response["rpc-reply"])
            return formatted_response
        if self.vendor == "ADVA":
            # TODO get this sorted once adva netconf is a real thing
            return device_response
