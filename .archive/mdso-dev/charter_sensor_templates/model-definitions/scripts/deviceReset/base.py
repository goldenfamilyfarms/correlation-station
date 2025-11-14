class NotImplementedError(Exception):
    pass


RESET_COMPLETE = "Reset Complete"
EXCEPTION_RAISED = "Exception raised "


class ResetBase:
    def __init__(self, device_values):
        self.device_values = device_values
        self.nf_resource = self.get_network_function_by_host_or_ip(self.device_values.fqdn, self.device_values.management_ip, require_active=True)

    def __getattr__(self, attr):
        if hasattr(self.plan, attr):
            return getattr(self.plan, attr)
        raise AttributeError("'{}' object has no attribute '{}'".format(self.__class__.__name__, attr))

    def ra_cutthrough_command(self, parameters, command):
        keyname = "devices_reset_status"
        if not self.nf_resource:
            self.patch_result_to_resource(keyname, {self.device_values.tid: "No provider resource id found"})
            return
        device_prid = self.nf_resource["providerResourceId"]
        self.logger.debug(f"Remediation paramaters: {parameters}")
        response = {}
        if parameters:
            try:
                response = self.execute_ra_command_file(
                    device_prid,
                    f"{command}.json",
                    parameters,
                ).json()["result"]
            except Exception as e:
                self.logger.info(f"Exception happened {self.device_values.tid} with error {e}")
                self._device_exception_handler(keyname, e)
                return response
            self.patch_result_to_resource(keyname, {self.device_values.tid: RESET_COMPLETE})
        else:
            self.patch_result_to_resource(keyname, {self.device_values.tid: "Not started"})
        return response

    def _device_exception_handler(self, keyname, e):
        if self.device_values.vendor == "JUNIPER":
            self._juniper_exception_handler(keyname, e)
        elif self.device_values.vendor == "RAD":
            self._rad_exception_handler(keyname, e)
        elif self.device_values.vendor == "ADVA":
            self._adva_exception_handler(keyname, e)
        elif self.device_values.vendor == "CISCO":
            self._cisco_exception_handler(keyname, e)
        elif self.device_values.vendor == "NOKIA":
            self._nokia_exception_handler(keyname, e)
        else:
            self.patch_result_to_resource(keyname, {self.device_values.tid: "may be non supported device"})

    def _juniper_exception_handler(self, keyname, result):
        reason = str(result)
        if reason and "statement not found: unit" in reason:
            self.logger.info(f"juniper_exception_handler: {self.device_values.tid} with error reason: {reason}")
            return self.patch_result_to_resource(keyname, {self.device_values.tid: RESET_COMPLETE})
        else:
            return self.patch_result_to_resource(keyname, {self.device_values.tid: EXCEPTION_RAISED})

    def _rad_exception_handler(self, keyname, result):
        reason = str(result)
        if reason and "cli error: Entry instance doesn't exist" in reason:
            self.logger.info(f"rad_exception_handler: {self.device_values.tid} with error reason: {reason}")
            return self.patch_result_to_resource(keyname, {self.device_values.tid: RESET_COMPLETE})
        else:
            return self.patch_result_to_resource(keyname, {self.device_values.tid: EXCEPTION_RAISED})

    def _adva_exception_handler(self, keyname, result):
        reason = str(result)
        if reason and "System is busy" in reason:
            self.logger.info(f"adva_exception_handler: {self.device_values.tid} with error reason: {reason}")
            return self.patch_result_to_resource(keyname, {self.device_values.tid: "System is busy"})
        else:
            return self.patch_result_to_resource(keyname, {self.device_values.tid: EXCEPTION_RAISED})

    def _cisco_exception_handler(self, keyname, result):
        reason = str(result)
        self.logger.info(f"cisco_exception_handler: {self.device_values.tid} with error reason: {reason}")
        return self.patch_result_to_resource(keyname, {self.device_values.tid: "Currently not supported"})

    def _nokia_exception_handler(self, keyname, result):
        reason = str(result)
        if reason and "MINOR: CLI Association doesn't exist" in reason:
            self.logger.info(f"nokia_exception_handler: {self.device_values.tid} with error reason: {reason}")
            return self.patch_result_to_resource(keyname, {self.device_values.tid: RESET_COMPLETE})
        else:
            return self.patch_result_to_resource(keyname, {self.device_values.tid: EXCEPTION_RAISED})

    def patch_result_to_resource(self, keyname, msg: dict):
        properties = self.resource["properties"]
        if not properties.get("device_reset_progress"):
            properties["device_reset_progress"] = {}
        if not properties["device_reset_progress"].get(keyname):
            properties["device_reset_progress"][keyname] = {}
        try:
            self.bpo.resources.patch_observed(
                self.resource_id, data={"properties": {"device_reset_progress": {keyname: msg}}}
            )
        except Exception as e:
            self.logger.error("Exception", e)
