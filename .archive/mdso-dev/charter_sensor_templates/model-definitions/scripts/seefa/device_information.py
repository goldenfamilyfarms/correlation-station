""" -*- coding: utf-8 -*-

SEEFA Device Information

Versions:
   0.1 May 27, 2022
       Initial check in of SEEFA Device Information plans

"""
import re
import textfsm

import sys
sys.path.append('model-definitions')
from scripts.common_plan import CommonPlan
from scripts.smartconnect.connection import Connection
from scripts.smartconnect.mdso_internal_utils import MDSOInternalSmartConnect
from scripts.smartconnect.render_io import RenderInput, RenderOutput


class Activate(CommonPlan):
    """
    Use Smart Connect to connect to device, send rendered command, receive rendered output
    Update resource properties with response from device to be used by SEEFA workstreams
    """

    def process(self):
        self.properties = self.resource["properties"]
        self.vendor = self.properties["vendor"]
        self.host_id = self.properties["host_id"]
        self.model = self.properties.get("model", "")
        self.command_name = self.properties["command"]
        mdso_internal = MDSOInternalSmartConnect(self)
        self.connection_type = mdso_internal.get_connection_type(self.vendor, self.model)
        self.device_response = {}
        try:
            self.connection = Connection(
                self,
                self.host_id,
                self.vendor,
                mdso_internal.get_credentials(self.vendor, self.connection_type),
                self.model,
            )
            self.input_handler = RenderInput(self.vendor)
            self.output_handler = RenderOutput(self.vendor, self.connection_type)
            rendered_command = self.input_handler.render_command_template(
                self.get_command_template_name(),
                self.properties.get("parameters", dict()),
            )
            self.command = self.input_handler.normalize_rendered_command_template(
                rendered_command, self.connection_type
            )
            self.logger.info("Normalized command payload: {}".format(self.command))
            if self.connection.is_connected:
                # send command(s), get device response
                multiple_command_process = self.get_multiple_command_process()
                if multiple_command_process:
                    self.device_response = multiple_command_process()
                else:
                    device_response = self.get_device_response(self.command)
                    # format device response
                    self.device_response = self.output_handler.format_device_response(
                        device_response, self.command_name
                    )
                    specialized_output_formatting = self.select_specialized_formatter()
                    if specialized_output_formatting:
                        self.device_response = specialized_output_formatting(self.device_response)
            else:
                self.device_response = {"Error": "Unable to establish SSH connection to {}".format(self.host_id)}
        finally:
            try:
                self.connection.close()
            except Exception:
                pass

        self.bpo.resources.patch_observed(
            self.resource["id"],
            data={
                "properties": {
                    "result": self.device_response,
                }
            },
        )

    def get_command_template_name(self):
        return (
            self.command_name + ".tmpl"
            if self.vendor == "JUNIPER" or "116PRO" in self.model
            else self.command_name + ".j2"
        )

    def get_device_response(self, command, ready_to_close=True):
        if isinstance(command, list):
            device_response = self.connection.send_commands(command, ready_to_close)
        else:
            device_response = self.connection.send_command(command, ready_to_close)
        if not device_response:
            device_response = ["Error: Unable to retreive data from device"]
            self.logger.error("Device response:\n{}".format(device_response))
        return device_response

    def rad_list_ports_process(self):
        # send initial port summary command
        port_summary = self.get_device_response(self.command, ready_to_close=False)
        # format port summary output to be iterated over by more detailed commands
        port_summary = self.output_handler.cli_formatter(port_summary, self.command_name)
        self.logger.info("Port summary output: {}".format(port_summary))
        data = {"ports": []}
        for port in port_summary:
            data["ports"].append(
                {
                    "name": port["name"],
                    "operational_state": port["operational_state"],
                    "rate": port["rate"],
                    "admin_state": port["admin_state"],
                    "type": port["type"],
                    "id": port["id"],
                    "details": self.get_rad_port_details_total(port),
                }
            )
        self.connection.close()
        return data

    def get_rad_port_details_total(self, port):
        # port info for each port in summary
        info_command = self.input_handler.render_command_template(
            "seefa-cd-get-port-info.j2", {"type": port["type"], "id": port["id"]}
        )
        info_command = self.input_handler.normalize_rendered_command_template(info_command, self.connection_type)
        port_info = self.get_device_response(info_command, ready_to_close=False)
        formatted_port_info = self.output_handler.cli_formatter(port_info, "seefa-cd-get-port-info")
        # add port info to details, creates initial details dict
        details = self.update_rad_port_info(formatted_port_info)
        # port status for each port in summary
        status_command = self.input_handler.render_command_template(
            "seefa-cd-get-port-status.j2", {"type": port["type"], "id": port["id"]}
        )
        status_command = self.input_handler.normalize_rendered_command_template(status_command, self.connection_type)
        port_status = self.get_device_response(status_command, ready_to_close=False)
        formatted_port_status = self.output_handler.cli_formatter(port_status, "seefa-cd-get-port-status")
        # add port status to details dict created by update rad port info
        details = self.update_rad_port_status(details, formatted_port_status)
        return details

    def update_rad_port_info(self, formatted_port_info):
        self.logger.info("Formatted Port Info\n{}".format(formatted_port_info))
        # TODO coordinate in arda to fix naming schema what even
        if self.is_empty(formatted_port_info):
            details = {
                "name": "",
                "mac_egressMtu": "",
                "mac_l2cp": "",
            }
        else:
            details = {
                "name": formatted_port_info[0]["name"],
                "mac_egressMtu": formatted_port_info[0]["mtu"],
                "mac_l2cp": formatted_port_info[0]["l2cp"],
            }
        return details

    def update_rad_port_status(self, details, formatted_port_status):
        self.logger.info("Formatted Port Status\n{}".format(formatted_port_status))
        # TODO coordinate in arda to fix naming schema what even
        port_status_details = (
            "admin",
            "oper",
            "connector",
            "phy_Equipped",
            "auto_negotiation",
            "rate",
            "duplex",
            "mac",
            "phy_ConnectorInterface",
            "phy_Manufacturer",
            "phy_PartNumber",
            "opt_Range",
            "opt_Wavelength",
            "phy_FiberType",
        )
        if self.is_empty(formatted_port_status):
            for detail in port_status_details:
                details[detail] = ""
        else:
            for detail in port_status_details:
                details[detail] = formatted_port_status[0][detail]
        return details

    def get_multiple_command_process(self):
        multiple_command_processes = {"seefa-cd-list-ports": {"RAD": self.rad_list_ports_process}}
        return multiple_command_processes.get(self.command_name, dict()).get(self.vendor)

    def select_specialized_formatter(self):
        formatters = {
            "seefa-cd-get-vlan-identifier-full": {"JUNIPER": self.format_juniper_vlans},
            "seefa-cd-show-version": {
                "JUNIPER": self.format_juniper_version,
            },
            "seefa-cd-show-isis": {
                "CISCO": self.format_cisco_isis,
            },
        }
        return formatters.get(self.command_name, dict()).get(self.vendor)

    def format_juniper_vlans(self, device_response):
        vlans = {}
        try:
            vlan_data = device_response["data"]["configuration"]["vlans"]["vlan"]
            if isinstance(vlan_data, dict):
                vlans[vlan_data["name"]] = vlan_data
            else:
                for vlan in vlan_data:
                    vlans[vlan["name"]] = vlan
        except (KeyError, TypeError):
            self.logger.debug("Does not contain VLAN data")
        return vlans

    def format_juniper_version(self, device_response):
        # see below for required data model comprised of network function resource properties
        # deviceVersion = device.get('properties')['deviceVersion']
        # resourceType = device.get('properties')['resourceType']
        # swVersion = device.get('properties')['swVersion']
        # return {'deviceVersion': deviceVersion, 'resourceType': resourceType, 'swVersion': swVersion}
        pass

    def format_cisco_isis(self, device_response):
        device_response = "\n".join(map(str, device_response))
        with open(self.fsm_directory + "/{}.fsm".format(self.command)) as template:
            fsm = textfsm.TextFSM(template)
            device_response = re.sub(r"\(Not configured, protocol disabled\)", "", device_response)
            device_response = re.sub(r"\s+Routing\sfor\sarea\saddress\(es\):\n\s+\d+.\d+", "", device_response)
        return [dict(zip(fsm.header, row)) for row in device_response]


class Terminate(CommonPlan):
    def process(self):
        pass
