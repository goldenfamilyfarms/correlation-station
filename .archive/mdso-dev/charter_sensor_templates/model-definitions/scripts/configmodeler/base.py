class NotImplementedError(Exception):
    pass


class ConfigBase:
    def __init__(self, service_type):
        SERVICE_SPECIFIC_MODELERS = {
            "FIA": self._model_fia_config,
            "ELINE": self._model_eline_config,
            "ELAN": self._model_elan_config,
            "VOICE": self._model_voice_config,
            "NNI": self._model_nni_config,
            "CTBH 4G": self._model_ctbh_4g_config,
        }
        self.service_modeler = SERVICE_SPECIFIC_MODELERS[service_type]
        self.topology_dictionary = self.create_device_dict_from_circuit_details(self.circuit_details)

    def generate_design_model(self):
        raise NotImplementedError(f"Design modeling not implemented for {self.vendor} {self.service_type}")

    def generate_network_model(self):
        raise NotImplementedError(f"Network modeling not implemented {self.vendor} {self.service_type}")

    def _generate_base_model(self):
        """
        service agnostic base config model
        """
        raise NotImplementedError(f"Base config modeling not implemented for {self.vendor}")

    def _model_nni_config(self):
        raise NotImplementedError(f"NNI modeling not implemented for {self.vendor}")

    def _model_ctbh_4g_config(self):
        raise NotImplementedError(f"CTBH 4G modeling not implemented for {self.vendor}")

    def _model_fia_config(self):
        raise NotImplementedError(f"FIA modeling not implemented for {self.vendor}")

    def _model_eline_config(self):
        raise NotImplementedError(f"ELINE modeling not implemented for {self.vendor}")

    def _model_elan_config(self):
        raise NotImplementedError(f"ELAN modeling not implemented for {self.vendor}")

    def _model_voice_config(self):
        raise NotImplementedError(f"VOICE modeling not implemented for {self.vendor}")

    def _model_slm_config(self):
        raise NotImplementedError(f"SLM modeling not implemented for {self.vendor}")

    def _get_device_details(self, device_tid: str, location: str) -> dict:
        for devices in self.topology_dictionary:
            for tid, device_details in devices.items():
                if tid == device_tid and location in device_details['location']:
                    return device_details
        return {}

    def __getattr__(self, attr):
        if hasattr(self.plan, attr):
            return getattr(self.plan, attr)
        raise AttributeError("'{}' object has no attribute '{}'".format(self.__class__.__name__, attr))

    def convert_fre_included_list_to_dict(self, fre, pro=False):
        if fre.get("properties", {}).get("included"):
            if pro:
                fre["properties"]["included"] = {item["id"]: item for item in fre["properties"]["included"]}
            else:
                fre["properties"]["included"] = {
                    item["id"].split("_")[1]: item for item in fre["properties"]["included"]
                }
        else:
            fre = {}
        return fre

    def get_ce_vlans(self):
        endpoints = self.circuit_details["properties"]["service"][0]["data"]["evc"][0]["endPoints"]
        ce_vlans = []
        for endpoint in endpoints:
            if self.device["Host Name"] in endpoint["uniId"]:
                ce_vlans = endpoint.get("ceVlans", [])
                break
        return ce_vlans
