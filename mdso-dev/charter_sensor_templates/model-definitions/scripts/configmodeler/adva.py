import sys

sys.path.append("model-definitions")
from ra_plugins.ra_cutthrough import RaCutThrough
from scripts.configmodeler.base import ConfigBase

ONE_GB = 1000000000
ONE_MB = 1000000
ONE_KB = 1000
EXTRA_SOAM_BW = 128000
MAX_CIR_ONEGIG_ADVA = 999000000
MAX_CIR_TENGIG_ADVA = 9999000000


class Adva(ConfigBase):
    def __init__(self, plan, circuit_id: str, device: str, location: str, circuit_details_id: str):
        self.plan = plan
        self.circuit_id = circuit_id
        self.cutthrough = RaCutThrough()
        self.circuit_details = self.bpo.resources.get(circuit_details_id)
        self.service_type = self.circuit_details["properties"]["serviceType"]
        super().__init__(self.service_type)
        self.netconf_devicelist = ["FSP 150-XG116PRO", "FSP 150-XG116PROH", "FSP 150-XG118PRO (SH)", "FSP 150-XG120PRO"]
        self.device = self._get_device_details(device_tid=device.upper(), location=location)
        self.logger.info(f"self.device = {self.device}")
        self.device_port_role = self.device["Client Interface Description"].split(":")[1]
        self.logger.info(f"self.device_port_role = {self.device_port_role}")
        self.device_model = self.device["Model"]
        self.device_model_dir_name = self.get_device_model_dir_name(self.device_model)
        self.nf_resource = self.get_network_function_by_host_or_ip(self.device["FQDN"], self.device["Management IP"], require_active=True)
        if not self.nf_resource:
            self.exit_error("Cannot Model without NF Resource")
        self.ce_vlans = self.get_ce_vlans()
        self.ms_vlan = self.circuit_details["properties"]["service"][0]["data"]["evc"][0].get("msVlan", "")
        self.logger.info(f"self.ce_vlans = {self.ce_vlans}")
        self.pbit = str(
            {
                "SERVICEPORT_UNCLASSIFIED_COS": 0,
                "SERVICEPORT_BRONZE_COS": 1,
                "SERVICEPORT_SILVER_COS": 3,
                "SERVICEPORT_GOLD_COS": 5,
                "PBIT-0": 0,
                "PBIT-1": 1,
                "PBIT-3": 3,
                "PBIT-5": 5,
                "UNCLASSIFIED": 0,
                "BRONZE": 1,
                "SILVER": 3,
                "GOLD": 5,
            }[self.circuit_details["properties"]["service"][0]["data"]["evc"][0]["cosNames"][0].get("name", None)]
        )

        # Refrence to NF and PRID
        if not self.nf_resource:
            msg = self.error_formatter(
                self.PROCESS_ERROR_TYPE,
                self.RESOURCE_GET_SUBCATEGORY,
                f"Cannot generate Adva config model without active network function for device: {self.device['FQDN']}."
            )
            self.categorized_error = msg
            self.exit_error(msg)

        self.device_prid = self.nf_resource["providerResourceId"]
        self.client_interface = self.device["Client Interface"]
        self.network_interface = self.device["Network Interface"]

        self.logger.info(f"self.client_interface stripped = {self.client_interface[6:]}")

        self.flow_label = self.get_flow_label(self.client_interface.lower())

        self.svlan = self.circuit_details["properties"]["service"][0]["data"]["evc"][0]["endPoints"][0].get("sVlan")
        if self.svlan == "Untagged":
            msg = self.error_formatter(
                self.PROCESS_ERROR_TYPE,
                self.RESOURCE_GET_SUBCATEGORY,
                f"Cannot generate ADVA config model with an Untagged svlan: {self.device['FQDN']}."
            )
            self.categorized_error = msg
            self.exit_error(msg)
        self.port_relationships_a = f"TPE_{self.client_interface}_{self.svlan}"
        self.port_relationships_z = f"TPE_{self.network_interface}_{self.svlan}"

        self.bw = self.circuit_details["properties"]["service"][0]["data"]["evc"][0].get("evc-ingress-bwp", None)

    def _generate_base_model(self):
        """
        Generates the base model for ADVA devices
        Parameters:
            None
        Returns:
            self.base_model (dict): The base model for ADVA devices
        """
        self.logger.info("=== Generating ADVA Base Model ===")
        if (not self.ce_vlans) and ("GE114PRO" in self.device_model.upper()):
            self.ce_vlans = ["0:4095"]
        # Random logic found for extra EVPL toggles
        if self.ce_vlans or "GE114PRO" in self.device_model.upper():
            self.port_type = "EVPL"
        else:
            self.port_type = self.device["Network Interface Description"].split(":")[1]

        flow_label_network_side = str(self.network_interface.lower())

        ingress_cir = self.get_cir_for_adva()

        if self.device_model in self.netconf_devicelist:
            return self.generate_pro_base_model()
        else:
            fre_label = f"{self.device['Host Name']}::FRE_{self.flow_label}"
            vlan_action = self.get_endpoint_vlan_action().lower()

            fre = {
                "label": fre_label.upper(),
                "ms_vlan": self.ms_vlan,
                "properties": {
                    "included": [
                        {
                            "type": "endPoints",
                            "id": self.port_relationships_a,
                            "attributes": {
                                "role": "a",
                                "additionalAttributes": {
                                    "deviceType": self.device_model,
                                    "egressAction": {
                                        "label": self.circuit_details["properties"]["service"][0]["data"]["evc"][0][
                                            "endPoints"
                                        ][0].get("sVlan", None),
                                        "value": "push",
                                    },
                                    "egressAction.label": self.circuit_details["properties"]["service"][0]["data"][
                                        "evc"
                                    ][0]["endPoints"][0].get("sVlan", None),
                                    "egressAction.value": "push",
                                    "epAccessA2NFlowCir": ingress_cir,
                                    "epAccessA2NFlowCbs": self.get_cbs_for_adva(),
                                    "epAccessA2NFlowEbs": self.get_ebs_for_adva(),
                                    "epAccessFlowIVlan": "256-0",
                                    "epAccessA2NFlowSOAMEir": 0,
                                    "epAccessA2NFlowSOAMCir": 128000,
                                    "epAccessFlowDefaultCos": 0,
                                    "epAccessFlowInnerTagPrioSwap": "disabled",
                                    "PolicerType": "single-rate-three-color-marker",
                                    "policerName": self.flow_label.replace("flow", "a2n_policer") + "-0",
                                    "serviceName": self.circuit_details["properties"]["serviceName"],
                                    "portId": self.client_interface.lower(),
                                    "epAccessFlowCVlanTagControl": "push",
                                    "epAccessFlowOuterTagPrioSwap": "disabled",
                                    "flowType": "regular-evc",
                                    "epAccessFlowSVlanTagControl": "none",
                                    "epAccessFlowN2ARateLimiting": "enabled" if self.port_type == "EPL" else "disabled",
                                    "egressCosPbit": self.pbit if self.port_type == "EVPL" else str(0),
                                    "epAccessFlowPBBFramesControl": "disabled",
                                    "epAccessFlowFramesSupport": "enabled" if self.port_type == "EVPL" else "disabled",
                                    "epAccessA2NFlowEir": (448000 if ingress_cir == 999000000 or ingress_cir == 9999000000 else 0),
                                    "epAccessFlowIVlanControl": "none",
                                    "epAccessFlowAccessInterface": self.client_interface.lower(),
                                    "epAccessFlowA2NShapingType": "flow-based",
                                    "epAccessFlowCVlanTag": str(
                                        self.circuit_details["properties"]["service"][0]["data"]["evc"][0]["endPoints"][
                                            0
                                        ].get("sVlan", None)
                                        + "-"
                                        + str(self.pbit)
                                    ),
                                    "epAccessFlowMultiCos": "disabled",
                                    "egressAction.etherType": "8a88",
                                    "epAccessFlowCVlanTagMatchRecievedPrio": "disabled",
                                    "epAccessFlowVlanMemberList": self.ce_vlans,
                                },
                                "directionality": "a2n",
                            },
                        },
                        {
                            "type": "endPoints",
                            "id": self.port_relationships_z,
                            "attributes": {
                                "role": "z",
                                "additionalAttributes": {
                                    "epAccessN2AFlowCir": 0,
                                    "epAccessN2AFlowCbs": 0,
                                    "epAccessFlowIVlan": "256-0",
                                    "epAccessFlowDefaultCos": 0,
                                    "epAccessFlowInnerTagPrioSwap": "disabled",
                                    "PolicerType": "two-rate-three-color-marker",
                                    "policerName": flow_label_network_side.replace("flow", "n2a_policer") + "-0",
                                    "portId": self.network_interface.lower(),
                                    "epAccessFlowCVlanTagControl": vlan_action,
                                    "epAccessFlowOuterTagPrioSwap": "disabled",
                                    "epAccessFlowNetworkInterface": self.network_interface.lower(),
                                    "ingressAction": {
                                        "label": str(
                                            self.circuit_details["properties"]["service"][0]["data"]["evc"][0][
                                                "endPoints"
                                            ][0].get("sVlan", None)
                                        ),
                                        "value": "pop",
                                    },
                                    "ingressAction.label": str(
                                        self.circuit_details["properties"]["service"][0]["data"]["evc"][0]["endPoints"][
                                            0
                                        ].get("sVlan", None)
                                    ),
                                    "ingressCosPbit": self.pbit,
                                    "serviceName": self.circuit_details["properties"]["serviceName"],
                                    "flowType": "port-based" if self.port_type == "EPL" else "default-evc",
                                    "epAccessFlowSVlanTagControl": "pop",
                                    "epAccessFlowN2ARateLimiting": "enabled" if self.port_type == "EPL" else "disabled",
                                    "epAccessFlowPBBFramesControl": "enabled",
                                    "epAccessFlowFramesSupport": "enabled" if self.port_type == "EVPL" else "disabled",
                                    "epAccessN2AFlowEir": 1000000000,
                                    "epAccessN2AFlowEbs": self.get_ebs_for_adva(),
                                    "epAccessN2AFlowSOAMEir": 0,
                                    "epAccessN2AFlowSOAMCir": 128000,
                                    "epAccessFlowIVlanControl": "none",
                                    "epAccessFlowA2NShapingType": "flow-based",
                                    "epAccessFlowCVlanTag": str(
                                        self.circuit_details["properties"]["service"][0]["data"]["evc"][0]["endPoints"][
                                            0
                                        ].get("sVlan", None)
                                        + "-"
                                        + self.pbit
                                    ),
                                    "epAccessFlowMultiCos": "disabled",
                                    "ingressAction.value": "pop",
                                    "ingressAction.etherType": "8a88",
                                    "epAccessFlowCVlanTagMatchRecievedPrio": "disabled",
                                    "epAccessFlowVlanMemberList": self.ce_vlans,
                                },
                                "directionality": "n2a",
                            },
                        },
                    ],
                    "data": {
                        "attributes": {
                            "topologySources": ["discovered"],
                            "serviceClass": "EVC",
                            "directionality": "bidirectional",
                            "networkRole": "IFRE",
                            "adminState": "enabled",
                            "layerRate": "ETHERNET",
                            "active": True,
                            "nativeName": self.flow_label,
                        },
                        "id": self.flow_label,
                    },
                    "layerRate": "ETHERNET",
                    "networkRole": "IFRE",
                },
            }

            client_tpe = {
                "label": self.device["Host Name"] + "::TPE_" + self.client_interface + "_PTP",
                "properties": {
                    "data": {
                        "id": "TPE_" + self.client_interface + "_PTP",
                        "type": "tpes",
                        "attributes": {
                            "state": "IS",
                            "locations": [{"port": self.client_interface.upper()}],
                            "userLabel": self.device["Client Interface Description"],
                            "nativeName": self.client_interface.lower(),
                            "serviceType": "epl",
                            "displayAlias": self.device["Client Interface Description"],
                            "structureType": "PTP",
                            "stackDirection": "bidirectional",
                        },
                    },
                    "state": "IS",
                    "structureType": "PTP",
                },
            }

            # Convert the included list to a dict for unique keys
            fre = self.convert_fre_included_list_to_dict(fre)

            self.base_model = {
                "FRE": fre,
                "Client TPE": client_tpe,
            }

            return self.base_model

    def generate_pro_base_model(self):
        """
        Generates the PRO version of the model
        Needs
            FRE - mp_flow(Label irrelevant but circuitName mandatory)
            Client PTP - handoff port physical properties
            Client TPE - flowpoint for handoff port
            Network TPE - flowpoint for network port
        """
        client_flowpoint = self.client_interface.replace("ETH-PORT", "fp")
        network_flowpoint = self.network_interface.replace("ETH-PORT", "fp")
        self.vlan_values = self.get_vlan_values_for_adva_pro_model()
        self.logger.info(f"{self.vlan_values=}")

        eir = None
        if self.device["Role"] in ["MTU", "AGG"]:
            cir = None
            eir = self.get_cir_for_adva()
        else:
            cir = self.get_cir_for_adva()
            if cir == 999000000 or cir == 9999000000:
                eir = 448000
                self.logger.info(f"{self.vlan_values=}")

        cbs = self.get_cbs_for_adva()
        ebs = self.get_ebs_for_adva()

        fre = {
            "label": f"FRE_{self.flow_label}",
            "ms_vlan": self.ms_vlan,
            "orchState": "active",
            "properties": {
                "data": {
                    "id": self.flow_label,
                    "type": "fres",
                    "attributes": {
                        "active": True,
                        "layerRate": "ETHERNET",
                        "adminState": "enabled",
                        "nativeName": self.flow_label,
                        "networkRole": "IFRE",
                        "serviceClass": "EVC",
                        "directionality": "bidirectional",
                        "topologySources": ["discovered"],
                        "additionalAttributes": {"circuitName": self.circuit_id},
                    },
                },
                "included": [
                    {
                        "id": client_flowpoint,
                        "type": "endPoints",
                        "attributes": {
                            "role": "a",
                            "directionality": "bidirectional",
                            "additionalAttributes": {},
                        },
                    },
                    {
                        "id": network_flowpoint,
                        "type": "endPoints",
                        "attributes": {
                            "role": "z",
                            "directionality": "bidirectional",
                            "additionalAttributes": {},
                        },
                    },
                ],
            },
        }

        client_ptp = {
            "label": "TPE_" + self.network_interface + "_PTP",
            "properties": {
                "data": {
                    "id": "TPE_" + self.network_interface + "_PTP",
                    "type": "tpes",
                    "attributes": {
                        "state": "IS",
                        "locations": [{"port": self.network_interface.upper()}],
                        "userLabel": self.device["Client Interface Description"],
                        "nativeName": self.network_interface.lower(),
                        "serviceType": "epl",
                        "displayAlias": self.device["Client Interface Description"],
                        "structureType": "PTP",
                        "stackDirection": "bidirectional",
                    },
                },
                "state": "IS",
                "structureType": "PTP",
            },
        }

        client_tpe = {
            "label": f"TPE_{client_flowpoint.upper()}_CTP",
            "orchState": "active",
            "properties": {
                "data": {
                    "id": client_flowpoint,
                    "type": "tpes",
                    "attributes": {
                        "state": "IS",
                        "userLabel": self.circuit_id,
                        "nativeName": self.flow_label,
                        "displayAlias": self.circuit_id,
                        "structureType": "CTPServerToClient",
                        "layerTerminations": [
                            {
                                "active": True,
                                "layerRate": "ETHERNET",
                                "structureType": "exposed lone cp",
                                "terminationState": "layer termination cannot terminate",
                                "additionalAttributes": {"multiCos": False},
                            }
                        ],
                        "additionalAttributes": {
                            "c_tag_pbit": 0,
                            "queueProfile": {
                                "cir": cir if cir else 0,
                                "eir": eir if eir else 0,
                                "shaper_id": "1",
                                "buffer_size": cbs,
                                "shaper_name": self.client_interface.replace("ETH-PORT", "fp_policer") + "-0",
                            },
                            "vlan_members": self.vlan_values["vlan_members_client"],
                            "policerProfile": {
                                "cbs": cbs if cbs else 1,
                                "cir": cir if cir else 0,
                                "ebs": ebs if ebs else 1,
                                "eir": eir if eir else 0,
                                "max_cir": 1000000000 if not eir else 0,
                                "max_eir": 0 if not eir else 1000000000,
                                "policer_id": "1",
                                "policer_name": self.client_interface.replace("ETH-PORT", "fp_policer") + "-0",
                            },
                            "broadcast_rate_limit": 64000,
                            "multicast_rate_limit": 64000,
                            "default_member_control": False,
                            "broadcast_rate_limit_control": False,
                            "multicast_rate_limit_control": False,
                        },
                        "flexibleEncapsulation": {
                            "match": {"untagged": "true"},
                            "localTrafficDefaultEncaps": {
                                "outerTag": {"vlanId": 1, "tagType": "none"},
                                "secondTag": {"tagType": "none"},
                            },
                        },
                    },
                }
            },
        }

        network_tpe = {
            "label": f"TPE_{network_flowpoint.upper()}_CTP",
            "orchState": "active",
            "properties": {
                "data": {
                    "id": network_flowpoint,
                    "type": "tpes",
                    "attributes": {
                        "state": "IS",
                        "userLabel": self.circuit_id,
                        "nativeName": network_flowpoint,
                        "displayAlias": self.circuit_id,
                        "structureType": "CTPServerToClient",
                        "layerTerminations": [
                            {
                                "active": True,
                                "layerRate": "ETHERNET",
                                "structureType": "exposed lone cp",
                                "terminationState": "layer termination cannot terminate",
                                "additionalAttributes": {"multiCos": False},
                            }
                        ],
                        "additionalAttributes": {
                            "c_tag_pbit": int(self.pbit),
                            "queueProfile": {
                                "cir": cir if cir else 0,
                                "eir": eir if eir else 0,
                                "shaper_id": "1",
                                "buffer_size": cbs,
                                "shaper_name": self.network_interface.replace("ETH-PORT", "fp_policer") + "-0",
                            },
                            "vlan_members": self.vlan_values["vlan_members_network"],
                            "policerProfile": {
                                "cbs": cbs if cbs else 1,
                                "cir": cir if cir else 0,
                                "ebs": ebs if ebs else 1,
                                "eir": eir if eir else 0,
                                "max_cir": 1000000000 if not eir else 0,
                                "max_eir": 0 if not eir else 1000000000,
                                "policer_id": "1",
                                "policer_name": self.network_interface.replace("ETH-PORT", "fp_policer") + "-0",
                            },
                            "broadcast_rate_limit": 64000,
                            "multicast_rate_limit": 64000,
                            "default_member_control": False,
                            "broadcast_rate_limit_control": False,
                            "multicast_rate_limit_control": False,
                        },
                        "flexibleEncapsulation": {
                            "match": {"untagged": "false"},
                            "localTrafficDefaultEncaps": {
                                "outerTag": {"vlanId": int(f"{self.vlan_values['vlan_id']}"), "tagType": "push"},
                                "secondTag": {"tagType": "none"},
                            },
                        },
                    },
                }
            },
        }

        # Convert the included list to a dict for unique keys
        fre = self.convert_fre_included_list_to_dict(fre, pro=True)

        self.base_model = {
            "FRE": fre,
            "Client PTP": client_ptp,
            "Client TPE": client_tpe,
            "Network TPE": network_tpe,
        }

        return self.base_model

    def get_vlan_values_for_adva_pro_model(self):
        """Adjusts model vlan_values if UNI"""
        vlan_values = {
            "vlan_members_client": [self.svlan],
            "vlan_members_network": [self.svlan],
            "vlan_id": "1",
        }
        if self.device_port_role == "EP-UNI":
            vlan_values = {
                "vlan_members_client": ["0:4095"],
                "vlan_members_network": [],
                "vlan_id": self.svlan,
            }
        if self.device_port_role == "EVP-UNI":
            vlan_values = {
                "vlan_members_client": [self.svlan],
                "vlan_members_network": [],
                "vlan_id": self.svlan,
            }
        return vlan_values

    def generate_design_model(self):
        """
        Main function to generate the service design model
        Parameters:
            None
        Returns:
            self.service_modeler() (function): The service design model for ADVA devices(calls service specif modeler)
        """
        self.logger.info(f"Adding {self.service_type} config details to base model")
        base_model = self._generate_base_model()
        self.logger.info(f"DESIGN MODEL:\n{base_model}")
        return self.service_modeler()

    def generate_network_model(self):
        """
        Generates the network model for ADVA devices
        Parameters:
            None
        Returns:
            network_model (dict): The live network model for ADVA devices
        """
        self.logger.info("=== Generating ADVA Network Model ===")

        # Netconf devices
        if self.device_model in self.netconf_devicelist:
            client_flowpoint, network_flowpoint, fre = self.gather_network_fre(self.device_prid, self.circuit_id)
            tpes = self.gather_network_tpes(
                client_flowpoint, network_flowpoint, self.device_prid
            )
            fre = self.convert_fre_included_list_to_dict(fre, pro=True)
            fre["ms_vlan"] = (
                self.get_managed_service_management_vlan(self.get_all_vlans_from_port_flowpoints_netconf())
                if self.ms_vlan
                else ""
            )
            network_model = {
                "FRE": fre,
                "Client TPE": tpes["client_tpe"],
                "Network TPE": tpes["network_tpe"],
            }

        # Non-Netconf devices
        else:
            fre = self.find_fre()

            client_tpe = self.cutthrough.execute_ra_command_file(
                self.device_prid,
                "tpe_get.json",
                parameters={"id": f"TPE_{self.client_interface}_PTP"},
                headers=None,
            ).json()["result"]

            if not fre.get("FRE_ERROR"):
                # Convert the included list to a dict for unique keys
                fre = self.convert_fre_included_list_to_dict(fre)
                if fre != {}:
                    fre["label"] = fre["label"].upper()
            # todo testing if I can add ms_vlan
            fre["ms_vlan"] = (
                self.get_managed_service_management_vlan(self.get_all_client_port_vlans()) if self.ms_vlan else ""
            )
            self.logger.info(f"self.ce_vlans = {self.ce_vlans}")
            self.logger.info(f"fre['ms_vlan'] = {fre['ms_vlan']}")

            network_model = {"FRE": fre, "Client TPE": client_tpe}

        if fre.get("FRE_ERROR"):
            network_model["FRE_ERROR"] = fre.get("FRE_ERROR")
            network_model["FRE"] = {}

        # Extra for Netconf devices
        if self.device_model in self.netconf_devicelist:
            network_model["Client PTP"] = tpes["client_ptp"]
        self.logger.info(f"NETWORK MODEL: {network_model}")
        return network_model

    def _model_fia_config(self):
        """
        Generates the service design model for FIA services
        Parameters:
            None
        Returns:
            self.base_model (dict): The service design model with additional FIA model
        """
        self.logger.info("=== Generating ADVA FIA Specific Model ===")
        fia_model = {}
        self.base_model.update(fia_model)

        return self.base_model

    def _model_voice_config(self):
        self.logger.info("=== Generating ADVA VOICE Specific Model ===")
        voice_model = {}
        self.base_model.update(voice_model)

        return self.base_model

    def _model_eline_config(self):
        """
        Generates the service design model for ELINE services
        Parameters:
            None
        Returns:
            self.base_model (dict): The service design model with additional ELINE model
        """
        self.logger.info("=== Generating ADVA ELINE Specific Model ===")
        eline_model = {}
        self.base_model.update(eline_model)

        return self.base_model

    def _model_ctbh_4g_config(self):
        """
        Generates the service design model for CTBH 4G services
        Parameters:
            None
        Returns:
            self.base_model (dict): The service design model with additional ELINE model
        """
        self.logger.info("=== Generating ADVA CTBH 4G Specific Model ===")
        eline_model = {}
        self.base_model.update(eline_model)

        return self.base_model

    def _model_elan_config(self) -> dict:
        """
        Generates the service design model for ELAN services
        Parameters:
            None
        Returns:
            self.base_model (dict): The service design model with additional ELINE model
        """
        self.logger.info("=== Generating ADVA ELINE Specific Model ===")
        elan_model = {}
        self.base_model.update(elan_model)

        return self.base_model

    def _model_nni_config(self):
        """
        Generates the service design model for NNI services
        Parameters:
            None
        Returns:
            self.base_model (dict): The service design model with additional NNI model
        """
        self.logger.info("=== Generating ADVA NNI Specific Model ===")
        nni_model = {}
        self.base_model.update(nni_model)

    def _model_static_config(self):
        """
        Houses all static config details for ADVA devices
        Parameters:
            None
        Returns:
            None
        """
        self.logger.info("Placeholder for static config details")

    def gather_network_fre(self, device_prid: str, circuit_id: str):
        """Parses the ra cutthrough fre_list.json result and gathers the
        fre which is the mp-flow and then gets the client and network flowpoint id's
        for the adva116 and 120pro's only

        :param device_prid: device providerResourceId
        :type device_prid: str
        :param circuit_id:
        :type circuit_id: str
        :return: fre: dict, client_flowpoint: str and network_flowpint: str
        :example: fp-1-1-1-6-1, fp-1-1-1-8-1 and fre: dict
        """

        fre_list = self.cutthrough.execute_ra_command_file(
            device_prid,
            f"ge/{self.device_model_dir_name}/fre_list.json",
            parameters={"id": ""},
            headers=None,
        ).json()
        fre = {}
        client_flowpoint = ""
        network_flowpoint = ""
        for item in fre_list["result"]:
            if circuit_id in item["properties"]["data"]["attributes"]["additionalAttributes"]["circuitName"]:
                end_points = item["properties"]["data"]["relationships"]["endPoints"]["data"]
                fre = item
                client_flowpoint = end_points[0].get("id")
                network_flowpoint = end_points[1].get("id")
                # 8 and 26 represent the standard uplinks for 116 and 120pros
                if len(client_flowpoint) > 4 and client_flowpoint.split("-")[4] in ["8", "26"]:
                    client_flowpoint = end_points[1].get("id")
                    network_flowpoint = end_points[0].get("id")
                    self.logger.info("client and network end_points adjusted")
        if not fre:
            flowpoint_ids = self.alternative_way_to_find_flowpoints(
                self.client_interface,
                self.network_interface,
                device_prid,
            )
            client_flowpoint = flowpoint_ids["client_flowpoint_id"]
            network_flowpoint = flowpoint_ids["network_flowpoint_id"]
        self.logger.info(f"test_client: {client_flowpoint} test_network: {network_flowpoint}")

        return client_flowpoint, network_flowpoint, fre

    def alternative_way_to_find_flowpoints(self, client_port_id: str, network_port_id: str, device_prid: str) -> dict:
        """gets the flowpoint_ids for both device client and network port.
        This is for the 116 and 120pro models.

        :param client_port_id: The device handoff port Example ETH_PORT-1-1-1-6
        :type client_port_id: str
        :param network_port_id: The uplink port Example ETH_PORT-1-1-1-8
        :type network_port_id: str
        :return: Example fp-1-1-1-3-2 and fp-1-1-1-8-2
        :rtype: str
        """
        client_port_number = client_port_id.split("-")[-1]
        network_port_number = network_port_id.split("-")[-1]
        flow_items = self.cutthrough.execute_ra_command_file(
            device_prid,
            f"ge/{self.device_model_dir_name}/netconf_find_flowpoints.json",
            parameters={
                "client_port": client_port_number,
                "network_port": network_port_number,
            },
            headers=None,
        ).json()["result"]["data"]["sub-network"]["network-element"]["shelf"]["slot"]["card"]["ethernet-card"][
            "ethernet-port"
        ]
        flowpoint_ids = {}
        self.logger.info(f"racutthrough results for flow_items: {flow_items}")
        flowpoint_ids["client_flowpoint_id"] = self.find_flowpoint_id_for_a_port(flow_items, client_port_id)
        flowpoint_ids["network_flowpoint_id"] = self.find_flowpoint_id_for_a_port(flow_items, network_port_id)

        return flowpoint_ids

    def find_flowpoint_id_for_a_port(self, flow_items: dict, device_port_id: str):
        """Parses the flow_items dictionary and gathers the flowpoint_id that is associated to a single port.
        Used for the 116 and 120pro models. The is a helper method for alternative_way_to_find_flowpoints().

        :param flow_items: is the result of an racutthrough command netconf_find_flowpoints.json
        :type flow_items: dict
        :param device_port_id: ETH_PORT-1-1-1-6
        :type device_port_id: str
        :return: flowpoint_id Example fp-1-1-1-6-1
        :rtype: str
        """

        device_port_number = device_port_id.split("-")[-1]
        port_flowpoint_id = None
        for item in flow_items:
            if item.get("port-id") == device_port_number and item.get("flowpoint"):
                port_flowpoint = item["flowpoint"]
                if type(port_flowpoint) is list:
                    for flow in port_flowpoint:
                        if self.circuit_id in flow["alias"]:
                            port_flowpoint_id = f"fp-1-1-1-{device_port_number}-{flow['flowpoint-id']}"
                else:
                    if self.circuit_id in port_flowpoint["alias"]:
                        port_flowpoint_id = f"fp-1-1-1-{device_port_number}-{item['flowpoint']['flowpoint-id']}"
        return port_flowpoint_id

    def gather_network_tpes(self, client_flowpoint: str, network_flowpoint: str, device_prid: str) -> dict:
        """Parses the ra cutthrough tpe_list.json results for the client and network tpe's
        for the adva116 and 120pro's only.

        :param client_flowpoint: Example: fp-1-1-1-6-1
        :type client_flowpoint: str
        :param network_flowpoint: Example: fp-1-1-1-8-1
        :type network_flowpoint: str
        :param device_prid: _description_
        :type device_prid: str
        :return: client_ptp, client_tpe and network_tpe
        :rtype: dictionaries
        """

        tpe_list = self.cutthrough.execute_ra_command_file(
            device_prid,
            f"ge/{self.device_model_dir_name}/tpe_list.json",
            parameters={"id": ""},
            headers=None,
        ).json()

        tpes = {
            "client_ptp": {},
            "client_tpe": {},
            "network_tpe": {}
        }
        for item in tpe_list["result"]:
            client_port_number = self.client_interface.split("-")[-1]
            if item["properties"]["data"]["attributes"]["nativeName"] == f"eth_port-1-1-1-{client_port_number}":
                tpes["client_ptp"] = item
            if client_flowpoint:
                if item["label"] == f"TPE_{client_flowpoint}_CTP".upper():
                    tpes["client_tpe"] = item
            if network_flowpoint:
                if item["label"] == f"TPE_{network_flowpoint}_CTP".upper():
                    tpes["network_tpe"] = item
        return tpes

    def get_cir_for_adva(self):
        """
        acts as a step function and generates
        cir values as required by adva devices
        """

        client_port = self.client_interface.lower()
        reqd_bw = self.convert_bw_value_to_bytes()
        self.logger.info("The req bw is: %s" % (reqd_bw))

        if self.device_model in self.netconf_devicelist:
            cir = self.get_cir_value_for_netconf_pro_devices(reqd_bw)
        elif "XG108" in self.device_model:
            cir = self.get_cir_value_for_xg108_device(client_port, reqd_bw)
        else:
            if reqd_bw % 64000 != 0:
                multiplier = reqd_bw // 64000 + 1
                reqd_bw = int(64000 * multiplier)
            cir = MAX_CIR_ONEGIG_ADVA if int(reqd_bw) == ONE_GB else int(reqd_bw)
        self.logger.info("The %s cir is: %s" % (self.device_model, cir))
        return cir

    def get_cir_value_for_netconf_pro_devices(self, reqd_bw):
        if reqd_bw == ONE_GB * 10:
            return int(MAX_CIR_TENGIG_ADVA)
        elif reqd_bw == ONE_GB:
            return int(MAX_CIR_ONEGIG_ADVA + EXTRA_SOAM_BW)
        return int(reqd_bw + EXTRA_SOAM_BW)

    def get_cir_value_for_xg108_device(self, client_port, reqd_bw):
        ONE_GIG_PORTS = [3, 4, 5, 6]
        TEN_GIG_PORTS = [7, 8]
        if int(client_port.split("-")[-1]) in ONE_GIG_PORTS and reqd_bw == ONE_GB:
            return int(MAX_CIR_ONEGIG_ADVA)
        elif int(client_port.split("-")[-1]) in TEN_GIG_PORTS and reqd_bw == ONE_GB * 10:
            return int(MAX_CIR_TENGIG_ADVA)
        return int(reqd_bw)

    def get_cbs_for_adva(self):
        """
        Device model specific bandwidth to CBS conversion
        Parameters:
            bw (str): Bandwidth in the format of "1g", "100m", "10000k"
        Returns:
            cbs (int): Committed Burst Size in bytes
        """

        bw_in_mb = self.convert_bw_value_to_bytes()
        cbs = 512

        if bw_in_mb == ONE_GB * 10:
            cbs = 2048
        elif bw_in_mb == ONE_GB:
            cbs = 1024
        else:
            if int(bw_in_mb) > ONE_GB + 1:
                cbs = 2048
            elif int(bw_in_mb) > ONE_MB * 201:
                cbs = 1024
        return cbs

    def get_ebs_for_adva(self):
        bw_in_mb = self.convert_bw_value_to_bytes()

        if bw_in_mb == ONE_GB * 10:
            ebs = 512
        elif bw_in_mb == ONE_GB:
            ebs = 512
        else:
            ebs = 0

        return ebs

    def convert_bw_value_to_bytes(self):
        bytes_value = {"g": ONE_GB, "m": ONE_MB, "k": ONE_KB}
        return int(self.bw[:-1]) * (bytes_value[self.bw[-1:]])

    def get_flow_label(self, client_port):
        """
        Creates a flow label for the client port based on Circuit Details
        Houses no network checks
        Parameters:
            client_port (str): Client port name
        Returns:
            flow_label (str): Flow label for the client port
        """
        if self.device_model in self.netconf_devicelist:
            flow_label = "mp_flow-1-1"
        else:
            flow_label = client_port.replace("access", "flow") + "-1"
        return flow_label

    def find_fre(self):
        """
        Finds the FRE for the circuit
        Parameters:
            None
        Returns:
            fre (dict): The FRE for the circuit
        """

        flow_list = self.cutthrough.execute_ra_command_file(
            self.device_prid,
            "list_flows.json",
            parameters={"id": ""},
            headers=None,
        ).json()["result"]

        flow_label = self.get_flow_list_label(flow_list)

        if isinstance(flow_label, dict):
            return flow_label

        fre = self.cutthrough.execute_ra_command_file(
            self.device_prid,
            "fre_get.json",
            parameters={"id": flow_label},
            headers=None,
        ).json()["result"]

        if not fre:
            return {}
        return fre

    def get_flow_list_label(self, flow_list):
        for fre in flow_list:
            if self.circuit_id in fre["properties"]["epAccessFlowEVCName"]:
                if self.client_interface.lower().strip("access") in fre["label"]:
                    return fre["label"]
                else:
                    return {"FRE_ERROR": "Flow found on wrong port.(Found on port %s)" % fre["label"].split("-")[-2]}

    def get_endpoint_vlan_action(self):
        """returns the individual adva device sVlanOperation value"""
        endpoints = self.circuit_details["properties"]["service"][0]["data"]["evc"][0]["endPoints"]
        if self.circuit_details["properties"]["serviceType"] == "ELINE":
            for endpoint in endpoints:
                if self.device["Host Name"] in endpoint["uniId"]:
                    return endpoint.get("sVlanOperation", "None")
        else:
            return endpoints[-1].get("sVlanOperation", "None")

    # new methods below for managed service

    def get_managed_service_management_vlan(self, flow_vlan_list):
        return "88" if "88" in flow_vlan_list else ""

    def get_all_vlans_from_port_flowpoints_netconf(self):
        vlan_member_list = []
        for vlan in self.get_all_client_port_flowpoints_netconf():
            vlan_member_list.append(vlan.get("ingress-vlan-member-list", "")[:-2])
        return vlan_member_list

    def get_all_client_port_flowpoints_netconf(self):
        try:
            port_flowpoints = self.cutthrough.execute_ra_command_file(
                self.device_prid,
                "netconf_find_flowpoints.json",
                parameters={"client_port": self.client_interface[-1:]},
                headers=None,
            ).json()["result"]["data"]["sub-network"]["network-element"]["shelf"]["slot"]["card"]["ethernet-card"][
                "ethernet-port"
            ]["flowpoint"]
            self.logger.info(f"get_all_client_port_flowpoints_netconf: {port_flowpoints}")
            return port_flowpoints
        except Exception as e:
            self.logger.info(f"Failed to get trunk port vlans via netconf: {self.device['Host Name']} with error {e}")
            return []

    def get_all_client_port_vlans(self):
        vlans = []
        flow_ids = self.get_handoff_port_flow_ids(self.get_all_device_flow_ids())
        vlans = self.get_all_trunk_port_vlans(flow_ids)
        if vlans:
            return vlans["vlans"]
        return vlans

    def get_all_trunk_port_vlans(self, flow_ids) -> list:
        try:
            response = self.cutthrough.execute_ra_command_file(
                self.device_prid,
                "get-all-trunk-port-vlans.json",
                parameters={"flow_ids": flow_ids},
                headers=None,
            ).json()["result"][0]
            self.logger.info(f"get all trunk port vlans: {response}")
            return response
        except Exception as e:
            self.logger.info(f"Failed to get trunk port vlans: {self.device['Host Name']} with error {e}")
            return []

    def get_handoff_port_flow_ids(self, device_values) -> list:
        return [flow for flow in device_values.get("flows", "") if self.client_interface[6:] in flow]

    def get_all_device_flow_ids(self) -> list:
        try:
            device_values = self.cutthrough.execute_ra_command_file(
                self.device_prid,
                "get-all-device-flow-ids.json",
                parameters={},
                headers=None,
            ).json()["result"][0]
            self.logger.info(f"get_all_device_flow_ids: {device_values}")
            return device_values
        except Exception as e:
            self.logger.info(f"Failed to get flow_ids: {self.device['Host Name']} with error {e}")
            return []
