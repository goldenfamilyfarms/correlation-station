""" -*- coding: utf-8 -*-

SEEFA TACACS Remediation

Versions:
    0.1 February 23, 2023
        Inital functionality to Check ISE
"""
import codecs
import json

import sys
sys.path.append('model-definitions')
from scripts.smartconnect.mdso_internal_utils import MDSOInternalSmartConnect
from scripts.common_plan import CommonPlan
from scripts.smartconnect.connection import Connection
from scripts.smartconnect.render_io import RenderInput


class Activate(CommonPlan):
    """
    Uses Smart Connect to connect to devices and check ISE
    Reports back with update status
    """

    def process(self):
        self.properties = self.resource["properties"]
        self.vendor = self.properties["vendor"]
        self.fqdn = self.properties["fqdn"]
        self.region = self.properties["region"]
        self.state = self.properties["state"]
        self.use_local_creds = self.properties["local_creds"]
        self.connection_type = "cli"
        self.device_response = {}

        if self.use_local_creds:
            creds = self.get_local_creds()
        else:
            mdso_internal = MDSOInternalSmartConnect(self)
            creds = mdso_internal.get_credentials(self.vendor, self.connection_type)

        self.logger.info(f"Connecting to {self.fqdn} with {creds}")

        try:
            self.connection = Connection(
                plan=self,
                host_id=self.fqdn,
                vendor=self.vendor,
                credentials=creds,
            )

            if self.connection.is_connected:
                self.input_handler = RenderInput("ise_files")
                rendered_command = self.input_handler.render_command_template(
                    f"{self.vendor}_{self.region}.j2", {"state": self.state.lower()}
                )

                self.command = self.input_handler.normalize_rendered_command_template(
                    rendered_command, self.connection_type
                )

                self.device_response = self.get_device_response(self.command)

                if not self.device_response:
                    self.device_response = {"Error": "Unable to push CONFIG"}
                else:
                    self.device_response = {"Success": "CONFIG Remediated"}

        except Exception as e:
            self.logger.error(f"Unable to make a connection to {self.fqdn}: {e} ")
            self.device_response = {"Error": f"Unable to make a connection to {self.fqdn}: {e} "}

        finally:
            try:
                self.logger.info("Closing connection")
                self.connection.close()
            except Exception:
                pass
        if not self.device_response:
            self.device_response = {"Error": "Unable to Connect to device"}

        self.bpo.resources.patch_observed(
            self.resource["id"],
            data={
                "properties": {
                    "status": self.device_response,
                }
            },
        )

    def get_local_creds(self):
        """
        Get unobfuscated credentials for local login
        """
        creds = b"eyJ1c2VybmFtZSI6ICJjb21tX2VuZ2luZWVyIiwgInBhc3N3b3JkIjogImNvbW0jRW5nUFdEIn0=\n"
        string_creds = creds.decode("utf-8")
        return self.unhash_dict(string_creds)

    def get_device_response(self, command, ready_to_close=True):
        if isinstance(command, list):
            device_response = self.connection.send_commands(command, ready_to_close)
        else:
            device_response = self.connection.send_command(command, ready_to_close)
        if not device_response:
            device_response = ["Error: Unable to retreive data from device"]
            self.logger.error("Device response:\n{}".format(device_response))
        return device_response

    def unhash_dict(self, hash_):
        """
        Decrypt python dictionary from base64.
        Takes a base64 hashed string and decodes it to the original object.
        Parameters
            hash_(str): Base64 encoded string.
        Returns
            (dict): Decoded dictionary object.
        """
        return json.loads(codecs.decode(hash_.encode(), "base64"))


class Terminate(CommonPlan):
    def process(self):
        pass
