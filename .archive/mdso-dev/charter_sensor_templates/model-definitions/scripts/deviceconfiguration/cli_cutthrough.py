from plansdk.apis.plan import Plan
import requests
import time
import json
import logging


class CliCutthrough(Plan):
    logger = logging.getLogger(__name__)

    def run(self):
        raise Exception("This should never be called directly")

    # Use this function if RA does not support latest RACTL
    def executeCommandCisco(self, devicepid, command):
        url = "http://bpocore/racisco/api/v1/devices/{}/execute".format(devicepid)
        data = {
            "command": "cutthrough-cli.json",
            "parameters": {
                "commands": "{}".format(command),
            },
        }
        self.logger.info("data=" + str(data))
        response = requests.post(url, data=json.dumps(data), verify=False, headers={"Content-Type": "application/json"})
        self.logger.info("response: status_code={}, reason={}".format(response.status_code, response.reason))
        jsonResult = response.json()["result"]
        self.logger.info("jsonResult=" + str(jsonResult))
        return jsonResult

    def getRaUrlForSession(self, sessionid):
        rpurl = "http://blueplanet:80/ractrl/api/v1/sessions/{}".format(sessionid)
        response = requests.get(rpurl, headers={"Content-Type": "application/json"})
        self.logger.info(
            "response: status_code={}, reason={} json={}".format(response.status_code, response.reason, response.json())
        )
        if response.status_code == 404:
            result = None
            try:
                result = response.json()
            except Exception:
                # 404 raised when ractrl not reachable
                # Next status code check will raise appropriate error
                pass
            if result and "userMessage" in result:
                self.logger.info("RA_NOT_FOUND")
                raise Exception("RA_NOT_FOUND")
        if response.status_code != 200:
            self.logger.info("RACTRL_UNREACHABLE")
            raise Exception("RACTRL_UNREACHABLE")
        # ssessionData = response.json()
        ra_url = "http://blueplanet:80/ractrl/api/v1/devices/" + str(sessionid)
        return ra_url

    def commandExecutor(self, sessionid, command, addparams={}, alternate_return=False):
        self.logger.info("commandExecutor sessionid {}, command {}".format(sessionid, command))
        nfUrl = self.getRaUrlForSession(sessionid)
        headers = {"Content-Type": "application/json"}
        executeUrl = nfUrl + "/execute"
        self.logger.info("url=" + executeUrl)
        if addparams.get("banner"):
            data = {"parameters": addparams, "command": "set-banner.json"}
            data["parameters"]["commands"] = command

        else:
            data = {
                "command": "cutthrough-cli.json",
                "parameters": {
                    "commands": "{}".format(command),
                },
            }

        response = requests.post(executeUrl, data=json.dumps(data), verify=False, headers=headers)
        self.logger.info("status code: " + str(response.status_code))
        self.logger.info("Response: " + str(response.json()))

        if not alternate_return:
            return response.json()
        else:
            return response

    def configdelivery(self, config, device_resource_id, device_ip, addparams={}):
        # Send Down Commands
        self.logger.info("ATTEMPTING TO SEND COMMAND: " + str(config))
        try:
            out = self.commandExecutor(device_resource_id, config, addparams, alternate_return=True)
            self.logger.info(out)
            if out.status_code > 400:
                raise Exception
        except Exception:
            connected = self.connectivity_check(str(device_ip), device_ip)
            if not connected:
                sesssion_restart_response = self.reconnect(device_resource_id)
                connected = self.connectivity_check(str(device_ip), device_ip)
                if connected:
                    try:
                        out = self.commandExecutor(device_resource_id, config, addparams, alternate_return=True)
                        self.logger.info(out)
                    except Exception as e:
                        raise Exception("Error making URL call. Error: {}".format(e))
                else:
                    raise Exception(
                        "Error making URL call. \
                        Code: %s, Response: %s"
                        % (str(sesssion_restart_response), str(sesssion_restart_response.reason))
                    )

        time.sleep(0.1)

        return out

    def reconnect(self, device_resource_id):
        sesssion_restart_response = requests.post(
            "http://blueplanet:80/ractrl/api/v1/sessions/{}/restart".format(device_resource_id),
            data=None,
            headers={"Content-Type": "application/json"},
        )
        time.sleep(30)
        return sesssion_restart_response

    def connectivity_check(self, device_fqdn, device_ip):
        connection_product = self.get_built_in_product(self.BUILT_IN_CONNECTIVITY_CHECK_TYPE)
        connection_details = {
            "label": device_fqdn.split(".")[0] + ".connection_check",
            "productId": connection_product["id"],
            "properties": {
                "device_ip": device_ip,
                "device_port": 22,
                "timeout": 90,
                "method": "SSH",
                "return_delay": 5,
            },
        }

        self.bpo.resources.create(self.resource["id"], connection_details, wait_active=False)
        connect_res = self.get_dependencies(self.resource["id"], resource_type="tosca.resourceTypes.ConnectivityCheck")[
            0
        ]
        try:
            self.bpo.resources.await_termination(connect_res["id"], connection_product, False, max=601)
            return True
        except Exception:
            return False
