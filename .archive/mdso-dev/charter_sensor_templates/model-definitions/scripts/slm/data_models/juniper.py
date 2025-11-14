class Juniper:
    def __init__(self, probe=False):
        self.is_probe = probe

    def model_slm_config(self, slm_details, model_type):
        slm_details = self._normalize_slm_details(slm_details, model_type)
        slm_config_model = self._base_slm_model(slm_details)
        if self.is_probe:
            slm_config_model = self._add_probe_to_model(slm_config_model, slm_details)
        return slm_config_model

    def _normalize_slm_details(self, slm_details, model_type):
        normalized = {
            "maintenance_domain_level": slm_details["additional_data"]["maintenance_domain_level"],
            "maintenance_association": slm_details["maintenance_association"],
            "mep": slm_details["mep"],
            "cos": slm_details["additional_data"]["cos"],
            "cos_name": slm_details["additional_data"].get("cos_name"),
            "performance_tier": slm_details["additional_data"].get("performance_tier"),
            "vlan": slm_details["additional_data"]["vlan"],
        }

        details_are_from_network = self._are_details_from_existing_config(slm_details, model_type)
        if details_are_from_network:
            normalized = self._get_network_details(slm_details, normalized)
        else:
            normalized = self._get_designed_details(slm_details, normalized)

        return normalized

    def _are_details_from_existing_config(self, slm_details, model_type):
        return (
            model_type == "network_config"
            or model_type == "designed_config"
            and "existing_configuration_details" in slm_details
        )

    def _get_network_details(self, slm_details, normalized_details):
        normalized_details["maintenance_domain_name"] = slm_details["maintenance_domain"]
        normalized_details["continuity_check_interval"] = slm_details["additional_data"]["continuity_check"]["interval"]
        normalized_details["continuity_check_interface_status"] = slm_details["additional_data"]["continuity_check"][
            "interface_status_tlv"
        ]
        normalized_details["mep_direction"] = slm_details["additional_data"]["mep_direction"]
        normalized_details["mep_discovery"] = slm_details["additional_data"]["mep_discovery"]
        normalized_details["mep_lowest_priority_defect"] = slm_details["additional_data"]["mep_lowest_priority_defect"]
        if slm_details["additional_data"]["vlan"] is None:
            normalized_details["interface_name"] = None
        else:
            normalized_details[
                "interface_name"
            ] = f"{slm_details['device_details']['port']}.{slm_details['additional_data']['vlan']}"

        if self.is_probe:
            normalized_details = self._get_network_probe_details(slm_details, normalized_details)
        return normalized_details

    def _get_network_probe_details(self, slm_details, normalized_details):
        normalized_details["continuity_check_hold_interval"] = slm_details["additional_data"]["continuity_check"][
            "hold_interval"
        ]
        normalized_details["remote_mep"] = slm_details["remote_mep"]
        normalized_details["sla_iterator_profile_slm"] = slm_details["sla_iterator_profile_slm"]
        normalized_details["sla_iterator_profile_delay"] = slm_details["sla_iterator_profile_delay"]
        return normalized_details

    def _get_designed_details(self, slm_details, normalized_details):
        normalized_details["maintenance_domain_name"] = slm_details["maintenance_domain_name"]
        normalized_details["continuity_check_interval"] = "1s"
        normalized_details["continuity_check_interface_status"] = "interface-status-tlv"
        normalized_details["mep_direction"] = "up"
        normalized_details["mep_discovery"] = "auto-discovery"
        normalized_details["mep_lowest_priority_defect"] = "mac-rem-err-xcon"
        if slm_details["additional_data"]["vlan"] is None:
            normalized_details["interface_name"] = None
        else:
            normalized_details["interface_name"] = f"{slm_details['handoff_port']}.{slm_details['vlan']}"
        if self.is_probe:
            normalized_details = self._get_designed_probe_details(slm_details, normalized_details)
        return normalized_details

    def _get_designed_probe_details(self, slm_details, normalized_details):
        normalized_details["continuity_check_hold_interval"] = "1"
        normalized_details["remote_mep"] = "1"
        normalized_details[
            "sla_iterator_profile_slm"
        ] = f"ce-slm-{slm_details['cos_name']}-{slm_details['performance_tier']}"
        normalized_details[
            "sla_iterator_profile_delay"
        ] = f"ce-delay-{slm_details['cos_name']}-{slm_details['performance_tier']}"
        return normalized_details

    def _base_slm_model(self, slm_details):
        return {
            "maintenance-domain": {
                "name": slm_details["maintenance_domain_name"],
                "level": slm_details["maintenance_domain_level"],
            },
            "maintenance-association": {
                "name": slm_details["maintenance_association"],
                "primary-vid": slm_details["vlan"],
                "continuity-check": {
                    "interval": slm_details["continuity_check_interval"],
                    "interface-status-tlv": slm_details["continuity_check_interface_status"],
                },
                "mep": {
                    "name": slm_details["mep"],
                    "interface": {
                        "interface-name": slm_details["interface_name"],
                    },
                    "direction": slm_details["mep_direction"],
                    "priority": slm_details["cos"],
                    "auto-discovery": slm_details["mep_discovery"],
                    "lowest-priority-defect": slm_details["mep_lowest_priority_defect"],
                },
            },
        }

    def _add_probe_to_model(self, slm_config_model, slm_details):
        slm_config_model["maintenance-association"]["continuity-check"]["hold-interval"] = slm_details[
            "continuity_check_hold_interval"
        ]
        slm_config_model["maintenance-association"]["mep"]["remote-mep"] = {
            "name": slm_details["remote_mep"],
            "sla-iterator-profile": {
                "ce-slm": {"name": slm_details["sla_iterator_profile_slm"]},
                "ce-delay": {"name": slm_details["sla_iterator_profile_delay"]},
            },
        }
        return slm_config_model
