import sys
sys.path.append('model-definitions')
from scripts.deviceconfiguration.cli_cutthrough import CliCutthrough
from scripts.complete_and_terminate_plan import CompleteAndTerminatePlan
from collections import OrderedDict


class Activate(CompleteAndTerminatePlan, CliCutthrough):
    def process(self):
        props = self.resource["properties"]
        self.fqdn = props.get("fqdn")
        self.ipAddress = props["ipAddress"]
        self.configuration = props["configuration"]
        self.label = self.resource["label"]
        self.ignore_errors = bool(props.get("ignore_errors", False))
        self.banner = bool(props.get("banner", False))
        self.delimiter = props.get("additionalAttributes", {}).get("delimiter")
        self.config_mode = bool(props.get("additionalAttributes", {}).get("config_mode", False))
        operation = self.properties.get("operation")
        if operation is None or operation not in ["MANAGED_SERVICES_ACTIVATION", "CPE_ACTIVATION"]:
            for conf in self.configuration:
                if conf.split()[0] != "show":
                    self.exit_error("Show commands only permitted")
                # INFO: diff logic is needed for RAD devices since show are not being used
        nf = self.get_network_function_by_host(self.ipAddress)
        if nf is None:
            raise Exception("Please verify device {}. Network Function is not onboard".format(self.ipAddress))

        commands_sent = []
        fails = [
            "UNKNOWN COMMAND",
            "CLI ERROR: COMMAND NOT RECOGNIZED",
            "INVALID INPUT DETECTED AT",
            "ERROR: INVALID COMMAND OR INPUT PARAMETER",
            "ERROR: ",
        ]
        # fails = device errors
        kill = False
        status = "start"

        self.addparams = {"delimiter": self.delimiter, "config_mode": self.config_mode, "banner": self.banner}

        if self.banner is True:
            response = self.configdelivery(self.configuration, nf["providerResourceId"], self.ipAddress, self.addparams)
            response_code = response.status_code
            response = response.json()
            result = response.get("header", {}).get("reason") or response.get("result", "")
            commands_sent.append(OrderedDict([("command", self.configuration), ("result", result)]))

            if not self.ignore_errors:
                if response_code > 400:
                    kill = True
                else:
                    for fail in fails:
                        if fail in result.upper():
                            kill = True
                            break
            if kill:
                status = "partial with error"

            elif status == "start":
                status = "partial"

        else:
            for conf in self.configuration:
                response = self.configdelivery(conf, nf["providerResourceId"], self.ipAddress, self.addparams)
                response_code = response.status_code
                response = response.json()
                result = response.get("header", {}).get("reason") or response.get("result", "")
                commands_sent.append(OrderedDict([("command", conf), ("result", result)]))
                if not self.ignore_errors:
                    if response_code > 400:
                        kill = True
                    else:
                        for fail in fails:
                            if fail in result.upper():
                                kill = True
                                break
                if kill:
                    status = "partial with error"
                    break

                elif status == "start":
                    status = "partial"

        if not kill:
            status = "full"

        output = {"output": {"status": status, "command_results": commands_sent}}
        self.logger.info("Json Commands Sent: {}".format(output))
        return output


class Terminate(CompleteAndTerminatePlan):
    def process(self):
        pass
