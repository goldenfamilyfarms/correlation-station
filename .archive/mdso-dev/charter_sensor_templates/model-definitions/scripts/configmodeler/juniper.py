import ipaddress
import re
import sys

from ra_plugins.ra_cutthrough import RaCutThrough

sys.path.append("model-definitions")
from scripts.configmodeler.base import ConfigBase

MS_APPLY_GROUPS = [
    "SERVICEPORT-MS",
    "SERVICEPORT-MS_NID",
    "SERVICEPORT-MS_MTU",
    "SERVICEPORT-MS_CES",
    "TP_SERVICEPORT-MS",
    "TP_SERVICEPORT-MS_NID",
    "TP_SERVICEPORT-MS_MTU",
    "TP_SERVICEPORT-MS_CES",
]


class Juniper(ConfigBase):
    def __init__(
        self,
        plan,
        circuit_id: str,
        device: str,
        location: str,
        circuit_details_id: str,
    ):
        self.plan = plan
        self.circuit_id = circuit_id
        self.cutthrough = RaCutThrough()
        self.circuit_details = self.circuit_details_vlan_change_if_untagged(self.bpo.resources.get(circuit_details_id))
        self.service_type = self.circuit_details["properties"]["serviceType"]
        super().__init__(self.service_type)
        self.device = self._get_device_details(device_tid=device.upper(), location=location)
        self.nf_resource = self.get_network_function_by_host_or_ip(
            self.device["FQDN"], self.device["Management IP"], require_active=True
        )
        if not self.nf_resource:
            msg = self.error_formatter(
                self.PROCESS_ERROR_TYPE,
                self.RESOURCE_GET_SUBCATEGORY,
                f"Cannot generate Juniper config model without active network function for device: {self.device['FQDN']}."
            )
            self.categorized_error = msg
            self.exit_error(msg)
        self.device_prid = self.nf_resource["providerResourceId"]
        # These are some cleaner CD paths for FIA and EVC
        if self.service_type == "FIA":
            self.cd_nested = self.circuit_details["properties"]["service"][0]["data"]["fia"][0]
        self.cd_evc = self.circuit_details["properties"]["service"][0]["data"]["evc"][0]
        # Shorthand paths for readability
        self.vlan = self.cd_evc["sVlan"]
        self.port = self.device["Client Interface"]

        if self.cd_evc.get("evcId") == "LOCALLY SWITCHED" and self.device.get("Role") == "PE":
            self.logger.info(f"self.topology_dictionary: {self.topology_dictionary}")
            self.locally_switched_ports = self.get_both_pe_ports_and_add_to_list()
            self.logger.info(f"self.locally_switched_ports: {self.locally_switched_ports}")
        # Use this to get the Role of the port from CD
        self.port_type = self.get_port_role(self.circuit_details, self.device["Host Name"] + "-" + self.port)

        # UNI Port Role Check
        self.is_uni_port = False
        self.port_with_vlan = self.port + "." + str(self.vlan)
        if self.port_type == "UNI":
            self.is_uni_port = True
            self.port_with_vlan = self.port + ".0"
        self.ce_vlans = self.get_ce_vlans()
        self.ms_vlan = self.circuit_details["properties"]["service"][0]["data"]["evc"][0].get("msVlan", "")

        # COS mapping for PE devices, this is seperate from the common_plan COS mapping
        self.COS_FC_LOOKUP = {
            "PE": {
                "SERVICEPORT_UNCLASSIFIED_COS": [
                    "SERVICEPORT_FC_BRONZE",
                    "BE-CS-B",
                    "SERVICEPORT_BRONZE_COS",
                ],
                "SERVICEPORT_FC_BRONZE": [
                    "SERVICEPORT_FC_BRONZE",
                    "BE-CS-B",
                    "SERVICEPORT_BRONZE_COS",
                ],
                "SERVICEPORT_BRONZE_COS": [
                    "SERVICEPORT_FC_BRONZE",
                    "BE-CS-B",
                    "SERVICEPORT_BRONZE_COS",
                ],
                "BRONZE": [
                    "SERVICEPORT_FC_BRONZE",
                    "BE-CS-B",
                    "SERVICEPORT_BRONZE_COS",
                ],
                "SERVICEPORT_SILVER_COS": [
                    "SERVICEPORT_FC_SILVER",
                    "CS-S",
                    "SERVICEPORT_SILVER_COS",
                ],
                "SERVICEPORT_FC_SILVER": [
                    "SERVICEPORT_FC_SILVER",
                    "CS-S",
                    "SERVICEPORT_SILVER_COS",
                ],
                "SILVER": [
                    "SERVICEPORT_FC_SILVER",
                    "CS-S",
                    "SERVICEPORT_SILVER_COS",
                ],
                "SERVICEPORT_GOLD_COS": [
                    "SERVICEPORT_FC_GOLD",
                    "CS-G",
                    "SERVICEPORT_GOLD_COS",
                ],
                "SERVICEPORT_FC_GOLD": [
                    "SERVICEPORT_FC_GOLD",
                    "CS-G",
                    "SERVICEPORT_GOLD_COS",
                ],
                "GOLD": [
                    "SERVICEPORT_FC_GOLD",
                    "CS-G",
                    "SERVICEPORT_GOLD_COS",
                ],
            }
        }
        self.EDNA_COS_FC_LOOKUP = {
            "PE": {
                "SERVICEPORT_UNCLASSIFIED_COS": [
                    "TP_SERVICEPORT_QF_BRONZE",
                    "QF_SPECTRUM-BRONZE",
                    "TP_SERVICEPORT_BRONZE_COS",
                ],
                "SERVICEPORT_FC_BRONZE": [
                    "TP_SERVICEPORT_QF_BRONZE",
                    "QF_SPECTRUM-BRONZE",
                    "TP_SERVICEPORT_BRONZE_COS",
                ],
                "SERVICEPORT_BRONZE_COS": [
                    "TP_SERVICEPORT_QF_BRONZE",
                    "QF_SPECTRUM-BRONZE",
                    "TP_SERVICEPORT_BRONZE_COS",
                ],
                "BRONZE": [
                    "TP_SERVICEPORT_QF_BRONZE",
                    "QF_SPECTRUM-BRONZE",
                    "TP_SERVICEPORT_BRONZE_COS",
                ],
                "SERVICEPORT_SILVER_COS": [
                    "TP_SERVICEPORT_QF_SILVER",
                    "QF_SPECTRUM-SILVER",
                    "TP_SERVICEPORT_SILVER_COS",
                ],
                "SERVICEPORT_FC_SILVER": [
                    "TP_SERVICEPORT_QF_SILVER",
                    "QF_SPECTRUM-SILVER",
                    "TP_SERVICEPORT_SILVER_COS",
                ],
                "SILVER": [
                    "TP_SERVICEPORT_QF_SILVER",
                    "QF_SPECTRUM-SILVER",
                    "TP_SERVICEPORT_SILVER_COS",
                ],
                "SERVICEPORT_GOLD_COS": [
                    "TP_SERVICEPORT_QF_GOLD",
                    "QF_SPECTRUM-GOLD",
                    "TP_SERVICEPORT_GOLD_COS",
                ],
                "SERVICEPORT_FC_GOLD": [
                    "TP_SERVICEPORT_QF_GOLD",
                    "QF_SPECTRUM-GOLD",
                    "TP_SERVICEPORT_GOLD_COS",
                ],
                "GOLD": [
                    "TP_SERVICEPORT_QF_GOLD",
                    "QF_SPECTRUM-GOLD",
                    "TP_SERVICEPORT_GOLD_COS",
                ],
            }
        }

        # This must be after the COS lookup tables are defined
        if self.device["Role"] == "PE":
            self.cos_list = self.get_cos()

    def _generate_base_model(self) -> dict:
        """
        Generates the base model for Juniper devices
        Parameters:
            None
        Returns:
            self.base_model (dict): The base model for Juniper devices
        """
        self.logger.info("=== Generating JUNIPER Base Model ===")
        self.base_model = {}

        return self.base_model

    def generate_design_model(self):
        self.logger.info(f"Adding {self.service_type} config details to base model")
        self._generate_base_model()
        return self.service_modeler()

    def generate_network_model(self):
        """
        Generates the network model for Juniper devices
        Parameters:
            None
        Returns:
            network_model (dict): The live network model for Juniper devices
        """
        self.logger.info("=== Generating JUNIPER Network Model ===")

        if self.service_type == "NNI":
            network_model = self.nni_network_config()

        if self.service_type in ["ELINE", "CTBH 4G"]:
            if self.device["Role"] == "PE":
                tpe, fre = self.pe_eline_network_config()
                network_model = {
                    "Client TPE": tpe,
                    "FRE": fre,
                }
            else:
                network_model = self.non_pe_network_config()

        if self.service_type == "FIA":
            if self.device["Role"] == "PE":
                tpe, fre = self.pe_fia_network_config()
                network_model = {
                    "Client TPE": tpe,
                    "FRE": fre,
                }
            else:
                network_model = self.non_pe_network_config()

        if self.service_type == "ELAN":
            if self.device["Role"] == "PE":
                tpe, fre = self.pe_elan_network_config()
                network_model = {
                    "Client TPE": tpe,
                    "FRE": fre,
                }
            else:
                network_model = self.non_pe_network_config()

        if self.service_type == "VOICE":
            if self.device["Role"] == "PE":
                tpe, fre = self.pe_voice_network_config()
                network_model = {"Client TPE": tpe, "FRE": fre, "ARP": self.check_if_ip_in_arp_table()}
            else:
                network_model = self.non_pe_network_config()
        if self.ms_vlan:
            network_model["FRE"]["ms_vlan"] = self.get_ms_vlan_for_network_model()
        return network_model

    def _model_ctbh_4g_config(self):
        self._model_eline_config()

        return self.base_model

    def _model_voice_config(self):
        self.logger.info("=== Generating JUNIPER VOICE Specific Model ===")
        self._model_fia_config()
        self.get_ms_vlan_for_design_model()

        return self.base_model

    def _model_nni_config(self):
        self.logger.info("=== Generating JUNIPER NNI Specific Model ===")

        nni_model = {
            "FRE": {"port_slotted": True},
            "Client TPE": {"description": self.device["Client Interface Description"]},
        }
        self.base_model.update(nni_model)
        return self.base_model

    def _model_fia_config(self):
        """
        Generates the service design model for FIA services
        Parameters:
            None
        Returns:
            self.base_model (dict): The service design model with additional FIA model
        """
        self.logger.info("=== Generating JUNIPER FIA Specific Model ===")

        if self.device["Role"] == "PE" or self.device["Role"] == "CPE":
            design_model_data = self.get_fia_service_object_from_details(self.device, self.circuit_details)

            fia_model = {
                "FRE": self.normalize_designed_model(design_model_data),
                "Client TPE": {"userLabel": self.circuit_id, "apply-groups": "None"},
            }
        else:
            fia_model = {
                "FRE": {
                    "VLAN": self.cd_evc["endPoints"][0]["sVlan"],
                    "Client Interface Description": self.device["Client Interface Description"],
                    "userLabel": self.cd_evc["endPoints"][0]["userLabel"],
                },
                "Client TPE": {},
            }
        self.base_model.update(fia_model)
        self.get_ms_vlan_for_design_model()
        return self.base_model

    def _model_eline_config(self):
        """
        Generates the service design model for ELINE services
        Parameters:
            None
        Returns:
            self.base_model (dict): The service design model with additional ELINE model
        """
        self.logger.info("=== Generating JUNIPER ELINE Specific Model ===")

        # Eline Specific values
        userlabel = self.circuit_id + ":TRANS:ELINE::"
        tpe_userlabel = self.device["Client Interface Description"]

        self.siteNetworkAccessId = self.cd_evc.get("evcId", "")
        remote_carrier_name = self.get_l2circuit_neighbor_ip(self.device, self.circuit_details) if self.siteNetworkAccessId else ""
        site_network_access_id = str(self.siteNetworkAccessId)
        if self.cd_evc.get("evcId") == "LOCALLY SWITCHED":
            remote_carrier_name = "LOCALLY SWITCHED"
            site_network_access_id = "LOCALLY SWITCHED"

        if self.device["Role"] == "PE" or self.device["Role"] == "CPE":
            eline_model = {
                "FRE": {
                    "included": [
                        {
                            "id": self.port_with_vlan,
                            "attributes": {
                                "additionalAttributes": {},
                                "directionality": "bidirectional",
                                "role": "symmetric",
                            },
                        }
                    ],
                    "device": self.device_prid,
                    "data": {
                        "attributes": {
                            "directionality": "bidirectional",
                            "layerRate": "ETHERNET",
                            "networkRole": "IFRE",
                            "siteNetworkAccesses": [
                                {
                                    "siteNetworkAccess": {
                                        "remoteCarrierName": remote_carrier_name,
                                        "siteNetworkAccessId": site_network_access_id,
                                    }
                                }
                            ],
                            "userLabel": userlabel,
                        },
                    },
                },
                "Client TPE": {
                    "device": self.device_prid,
                    "data": {
                        "id": self.port.lower(),
                        "attributes": {
                            "bwpPerUni": [
                                {
                                    "egressBwpPerUni": {
                                        "envelopeId": "ccc",
                                        "bwProfileFlowParameters": (
                                            self.cd_evc["evc-egress-bwp"]
                                            if "evc-egress-bwp" in self.cd_evc.keys()
                                            else self.cd_evc["evc-ingress-bwp"]
                                        ),
                                    }
                                }
                            ],
                            "userLabel": tpe_userlabel,
                            "layerTerminations": [
                                {
                                    "layerRate": "ETHERNET",
                                    "signalIndex": {"mappingTable": [{"cos": self.cos_list}]},
                                    "mplsPackage": {
                                        "bw": {
                                            "bwKbps": (
                                                self.get_bw_in_kbps(self.cd_evc["evc-egress-bwp"])
                                                if "evc-egress-bwp" in self.cd_evc.keys()
                                                else self.get_bw_in_kbps(self.cd_evc["evc-ingress-bwp"])
                                            )
                                        }
                                    },
                                }
                            ],
                            "locations": [{"vlan": self.vlan if not self.is_uni_port else "None"}],
                            "encapsulation": {"encapsType": "vlan-ccc" if not self.is_uni_port else "ethernet-ccc"},
                        },
                    },
                },
            }
        # If the juniper is a MTU or AGG device
        else:
            eline_model = {
                "FRE": {
                    "VLAN": self.cd_evc["endPoints"][0]["sVlan"],
                    "Client Interface Description": self.device["Client Interface Description"],
                    "userLabel": self.cd_evc["endPoints"][0]["userLabel"],
                },
                "Client TPE": {},
            }
        self.base_model.update(eline_model)
        self.get_ms_vlan_for_design_model()
        return self.base_model

    def nni_network_config(self):
        gathered_tpe = self.cutthrough.execute_ra_command_file(
            self.device_prid,
            command_file="get-tpe.json",
            parameters={"data.id": self.port.lower()},
            headers=None,
        ).json()["result"]

        interface_optic_levels = self.execute_ra_command_file(
            self.device_prid, "show-interface-dom.json", parameters={"name": self.port.lower()}, headers=None
        ).json()["result"]

        if "N/A" in interface_optic_levels["tx-signal-avg-optical-power"]:
            port_slotted = False
        else:
            port_slotted = True

        network_config = {
            "FRE": {"port_slotted": port_slotted},
            "Client TPE": {
                "description": gathered_tpe["properties"]["data"]["attributes"].get("userLabel", "None")
                if gathered_tpe
                else "None"
            },
        }

        return network_config

    def non_pe_network_config(self):
        network_config = self.get_network_config_data(
            self.circuit_details,
            self.service_type,
            self.device["Host Name"],
            self.device_prid,
        )
        self.logger.info(f"network_config: {network_config}")
        vlan_name = network_config["vlan_name"]
        device_model = self.device["Model"]
        self.logger.info(f"DEVICE MODEL: {device_model}")
        if "ACX" in device_model:
            # ACXs return a slightly different result
            network_model = {
                "Client TPE": {
                    "userLabel": (
                        network_config["interface_config"].get("description", "None")
                        if network_config.get("interface_config")
                        else None
                    ),
                    "apply-groups": None,
                },
                "FRE": {},
            }

            if network_config["vlan_config"]:
                network_model["FRE"]["vlan_name"] = vlan_name
                network_model["FRE"]["VLAN"] = network_config.get("vlan-id", "None")
                network_model["FRE"]["userLabel"] = network_config["vlan_config"][vlan_name].get("description", "None")

        else:
            network_model = {
                "Client TPE": {
                    "userLabel": (
                        network_config["interface_config"]["configuration"]["interfaces"][
                            self.device["Client Interface"].lower()
                        ].get("description", "None")
                        if network_config.get("interface_config")
                        else None
                    ),
                    "apply-groups": (
                        network_config["interface_config"]["configuration"]["interfaces"][
                            self.device["Client Interface"].lower()
                        ].get("apply-groups", "None")
                        if network_config.get("interface_config")
                        else None
                    ),
                },
                "FRE": {},
            }

            if network_config["vlan_config"]:
                network_model["FRE"]["vlan_name"] = vlan_name
                network_model["FRE"]["VLAN"] = (network_config["vlan_config"][vlan_name].get("vlan-id", "None"),)
                network_model["FRE"]["userLabel"] = network_config["vlan_config"][vlan_name].get("description", "None")

        return network_model

    def pe_eline_network_config(self):
        """
        Generates the network config for PE ELINE devices
        Parameters:
            None
        Returns:
            tpe (dict): The TPE config
            fre (dict): The FRE config
        """

        gathered_tpe = self.cutthrough.execute_ra_command_file(
            self.device_prid,
            command_file="get-tpe.json",
            parameters={"data.id": self.port.lower()},
            headers=None,
        ).json()["result"]

        # Try to gather all data with initial vlan determination
        interface_config = self.get_interface_config(
            self.device_prid, self.port.lower(), self.vlan if not self.is_uni_port else 0
        )
        cos_config = self.get_cos_config(self.device_prid, self.port.lower(), self.vlan if not self.is_uni_port else 0)
        l2_info = self.get_l2circuit_config(
            self.device_prid,
            self.device,
            self.circuit_details,
            self.port.lower(),
            self.vlan if not self.is_uni_port else 0,
        )

        # If not found for UNI ports try the svlan as it may exist but tagged
        if self.is_uni_port and not interface_config:
            interface_config = self.get_interface_config(self.device_prid, self.port.lower(), self.vlan)
            cos_config = self.get_cos_config(self.device_prid, self.port.lower(), self.vlan)
            l2_info = self.get_l2circuit_config(
                self.device_prid, self.device, self.circuit_details, self.port.lower(), self.vlan
            )

        cos = cos_config[self.port.lower()]["unit"].get("apply-groups", None) if cos_config else None

        self.logger.info(f"l2_info: {l2_info}")
        # If the juniper has a valid config
        if interface_config:
            self.logger.info(f"interface_config: {interface_config}")
            interface_config = interface_config["configuration"]["interfaces"][self.port.lower()]["unit"][0]
            remote_carrier_name = l2_info["properties"].get("neighbor", "None") if l2_info else "None"
            site_network_access_id = str(l2_info["properties"].get("virtual-circuit-id", "")) if l2_info else ""
            if self.cd_evc.get("evcId") == "LOCALLY SWITCHED":
                locally_switch_info = self.get_locally_switched_l2circuit_info()
                self.logger.info(f"locally switched info: {locally_switch_info}")
                locally_switched_values = self.get_locally_switched_values_for_network_model(locally_switch_info)
                self.logger.info(f"locally switched values: {locally_switched_values}")
                remote_carrier_name = locally_switched_values['remoteCarrierName']
                site_network_access_id = locally_switched_values['siteNetworkAccessId']

            fre = {
                "included": [
                    {
                        "id": self.port_with_vlan,
                        "attributes": {
                            "additionalAttributes": {},
                            "directionality": "bidirectional",
                            "role": "symmetric",
                        },
                    }
                ],
                "sub_interace UserLabel": interface_config.get("description", "None"),
                "device": self.device_prid,
                "data": {
                    "id": self.port.lower(),
                    "attributes": {
                        "directionality": "bidirectional",
                        "layerRate": "ETHERNET",
                        "networkRole": "IFRE",
                        "bwpPerUni": [
                            {
                                "egressBwpPerUni": {
                                    "envelopeId": "ccc",
                                    "bwProfileFlowParameters": (
                                        interface_config.get("bandwidth", "None") if interface_config else "None"
                                    ),
                                }
                            }
                        ],
                        "layerTerminations": [
                            {
                                "layerRate": "ETHERNET",
                                "signalIndex": {"mappingTable": [{"cos": cos if cos else "None"}]},
                            },
                        ],
                        "locations": [
                            {"vlan": interface_config.get("vlan-id", "None") if interface_config else "None"}
                        ],
                        "siteNetworkAccesses": [
                            {
                                "siteNetworkAccess": {
                                    "remoteCarrierName": remote_carrier_name,
                                    "siteNetworkAccessId": site_network_access_id,
                                }
                            }
                        ],
                        "userLabel": l2_info["properties"].get("description", "None") if l2_info else "None",
                    },
                },
            }
        else:
            fre = {}

        tpe = {
            "device": self.device_prid,
            "data": {
                "id": self.port.lower(),
                "attributes": {
                    "bwpPerUni": [
                        {
                            "egressBwpPerUni": {
                                "envelopeId": "ccc",
                                "bwProfileFlowParameters": (
                                    interface_config.get("bandwidth", "None") if interface_config else "None"
                                ),
                            }
                        }
                    ],
                    "userLabel": (
                        gathered_tpe["properties"]["data"]["attributes"].get("userLabel", "None")
                        if gathered_tpe
                        else "None"
                    ),
                    "layerTerminations": [
                        {
                            "layerRate": "ETHERNET",
                            "signalIndex": {"mappingTable": [{"cos": cos if cos else "None"}]},
                            "mplsPackage": {
                                "bw": {
                                    "bwKbps": self.get_bw_in_kbps(
                                        interface_config.get("bandwidth", None) if interface_config else None
                                    )
                                }
                            },
                        }
                    ],
                    "locations": [{"vlan": interface_config.get("vlan-id", "None") if interface_config else "None"}],
                    "encapsulation": {
                        "encapsType": interface_config.get("encapsulation", "None") if interface_config else "None",
                    },
                    "additionalAttributes": {
                        "apply-groups": gathered_tpe["properties"]["data"]["attributes"]["additionalAttributes"].get(
                            "apply-groups", "None"
                        )
                    },
                    "adminState": gathered_tpe["properties"]["data"]["attributes"]["layerTerminations"][0].get(
                        "adminState", "None"
                    ),
                    "operationalState": gathered_tpe["properties"]["data"]["attributes"]["layerTerminations"][0].get(
                        "operationalState", "None"
                    ),
                },
            },
        }

        return tpe, fre

    def _model_elan_config(self):
        description = self.cd_evc["endPoints"][0]["userLabel"]
        if self.device["Role"] == "PE":
            vrfId = self.circuit_details["properties"]["service"][0]["data"]["elan"][0]["vrfId"]
            asNumber = self.circuit_details["properties"]["service"][0]["data"]["elan"][0]["asNumber"]
            ri_vlan = self.cd_evc["vplsVlanId"]

            elan_model = {
                "FRE": {
                    "COS CONFIG": {
                        self.port.lower(): {
                            "name": self.port.lower(),
                            "unit": {"name": self.vlan, "apply-groups": self.cos_list},
                        }
                    },
                    "INTERFACE CONFIG": {
                        "configuration": {
                            "interfaces": {
                                self.port.lower(): {
                                    "name": self.port.lower(),
                                    "unit": [
                                        {
                                            "name": self.vlan,
                                            "family": {
                                                "vpls": {
                                                    "policer": {
                                                        "output": (
                                                            self.cd_evc["evc-egress-bwp"]
                                                            if "evc-egress-bwp" in self.cd_evc.keys()
                                                            else self.cd_evc["evc-ingress-bwp"]
                                                        )
                                                    }
                                                }
                                            },
                                            "vlan-id": self.vlan,
                                            "bandwidth": (
                                                self.cd_evc["evc-egress-bwp"]
                                                if "evc-egress-bwp" in self.cd_evc.keys()
                                                else self.cd_evc["evc-ingress-bwp"]
                                            ),
                                            "description": description,
                                            "encapsulation": "vlan-vpls",
                                        }
                                    ],
                                }
                            }
                        }
                    },
                    "ROUTING INSTANCE": {
                        "label": f"RI::{vrfId}.ELAN",
                        "properties": {
                            "name": f"{vrfId}.ELAN",
                            "vlans": [{"vlanId": int(ri_vlan) if ri_vlan not in ["", "null"] else "None"}],
                            "config": {
                                "type": "vpls",
                                "description": f"VC{vrfId}:TRANS:ELAN::",
                                "routeTarget": str(asNumber) + ":" + vrfId,
                                "additionalConfiguration": {"noTunnelServices": False, "interfaceMacLimit": "512"},
                            },
                            "interfaces": [{"config": {"interface": self.port_with_vlan.lower()}}],
                        },
                    },
                },
                "Client TPE": {
                    "data": {
                        "id": self.port.lower(),
                        "attributes": {
                            "bwpPerUni": [
                                {"egressBwpPerUni": {"envelopeId": "ccc", "bwProfileFlowParameters": "None"}}
                            ],
                            "locations": [{"vlan": "None"}],
                            "userLabel": self.device["Client Interface Description"],
                            "encapsulation": {"encapsType": "vlan-vpls"},
                            "layerTerminations": [
                                {
                                    "layerRate": "ETHERNET",
                                    "mplsPackage": {
                                        "bw": {
                                            "bwKbps": (
                                                self.get_bw_in_kbps(self.cd_evc["evc-egress-bwp"])
                                                if "evc-egress-bwp" in self.cd_evc.keys()
                                                else self.get_bw_in_kbps(self.cd_evc["evc-ingress-bwp"])
                                            )
                                        }
                                    },
                                    "signalIndex": {"mappingTable": [{"cos": self.cos_list}]},
                                }
                            ],
                        },
                    },
                },
            }

        else:
            elan_model = {
                "FRE": {
                    "VLAN": self.vlan,
                    "userLabel": description,
                    "vlan_name": f"ELAN{self.vlan}",
                },
                "Client TPE": {
                    "userLabel": self.device["Client Interface Description"],
                },
            }

        self.base_model.update(elan_model)
        self.get_ms_vlan_for_design_model()
        return self.base_model

    def pe_elan_network_config(self):
        """
        Generates the network config for PE ELAN devices
        Parameters:
            None
        Returns:
            tpe (dict): The TPE config
            fre (dict): The FRE config
        """
        vrfId = self.circuit_details["properties"]["service"][0]["data"]["elan"][0]["vrfId"]
        asNumber = self.circuit_details["properties"]["service"][0]["data"]["elan"][0]["asNumber"]
        gathered_tpe = self.cutthrough.execute_ra_command_file(
            self.device_prid,
            command_file="get-tpe.json",
            parameters={"data.id": self.port.lower()},
            headers=None,
        ).json()["result"]

        found_instance = self.get_routing_instance(vrfId, asNumber)

        instance_name = found_instance["properties"]["name"] if found_instance else None

        vpls_connected = self.is_vpls_connected(instance_name)

        interface_config = self.get_interface_config(self.device_prid, self.port.lower(), self.vlan)
        cos_config = self.get_cos_config(self.device_prid, self.port.lower(), self.vlan)

        cos = cos_config[self.port.lower()]["unit"].get("apply-groups", None) if cos_config else None

        fre = {
            "ROUTING INSTANCE": found_instance,
            "INTERFACE CONFIG": interface_config if interface_config else {},
            "COS CONFIG": cos_config if cos_config else {},
            "VPLS": {"Connection Active": vpls_connected},
        }

        if interface_config:
            interface_config = interface_config["configuration"]["interfaces"][self.port.lower()]["unit"][0]

        tpe = {
            "device": self.device_prid,
            "data": {
                "id": self.port.lower(),
                "attributes": {
                    "bwpPerUni": [
                        {
                            "egressBwpPerUni": {
                                "envelopeId": "ccc",
                                "bwProfileFlowParameters": (
                                    interface_config.get("bandwidth", "None") if interface_config else "None"
                                ),
                            }
                        }
                    ],
                    "userLabel": (
                        gathered_tpe["properties"]["data"]["attributes"].get("userLabel", "None")
                        if gathered_tpe
                        else "None"
                    ),
                    "layerTerminations": [
                        {
                            "layerRate": "ETHERNET",
                            "signalIndex": {"mappingTable": [{"cos": cos if cos else "None"}]},
                            "mplsPackage": {
                                "bw": {
                                    "bwKbps": (
                                        self.get_bw_in_kbps(interface_config.get("bandwidth", None))
                                        if interface_config
                                        else "None"
                                    )
                                }
                            },
                        }
                    ],
                    "locations": [{"vlan": interface_config.get("vlan-id", "None") if interface_config else "None"}],
                    "encapsulation": {
                        "encapsType": interface_config.get("encapsulation", "None") if interface_config else "None",
                    },
                    "additionalAttributes": {
                        "apply-groups": gathered_tpe["properties"]["data"]["attributes"]["additionalAttributes"].get(
                            "apply-groups", "None"
                        )
                    },
                    "adminState": gathered_tpe["properties"]["data"]["attributes"]["layerTerminations"][0].get(
                        "adminState", "None"
                    ),
                    "operationalState": gathered_tpe["properties"]["data"]["attributes"]["layerTerminations"][0].get(
                        "operationalState", "None"
                    ),
                },
            },
        }

        return tpe, fre

    def get_routing_instance(self, vrfId, asNumber):
        routing_info = self.cutthrough.execute_ra_command_file(
            self.device_prid,
            command_file="get-routinginstances-full.json",
            parameters={"data.id": self.port.lower()},
            headers=None,
        ).json()["result"]
        # Only return if correct "<asNumber>:<vrfId>" is found and interface is correct

        found_instance = []
        correct_instance = []

        for instance in routing_info:
            if instance["properties"]["config"].get("routeTarget") == str(asNumber) + ":" + vrfId:
                found_instance.append(instance)

        if found_instance:
            for instance in found_instance:
                for interface in instance["properties"]["interfaces"]:
                    if interface["config"]["interface"] == self.port_with_vlan.lower():
                        correct_instance.append(instance)

        self.logger.info(f"Found RI's on Interface: {correct_instance}")

        if correct_instance:
            if len(correct_instance) > 1:
                return {}
            elif len(correct_instance) == 1:
                return correct_instance[0]
        else:
            return {}

    def is_vpls_connected(self, instance_name: str):
        if instance_name:
            vpls_info = self.cutthrough.execute_ra_command_file(
                self.device_prid,
                command_file="show-vpls-instance.json",
                parameters={"name": instance_name},
                headers=None,
            ).json()["result"]
            vpls_connected = False
            if isinstance(vpls_info["vpls-connection-information"]["instance"], dict):
                if vpls_info["vpls-connection-information"]["instance"].get("instance-display-error"):
                    vpls_connected = False
                else:
                    connections = (
                        vpls_info["vpls-connection-information"]
                        .get("instance", dict())
                        .get("reference-site", dict())
                        .get("connection", dict())
                    )
                    if isinstance(connections, list):
                        for instance in connections:
                            status = instance.get("local-interface", dict()).get("interface-status", "Down")
                            if status == "Up":
                                vpls_connected = True
                    else:
                        if connections.get("local-interface", dict()).get("interface-status", "Down") == "Up":
                            vpls_connected = True

            if isinstance(vpls_info["vpls-connection-information"]["instance"], list):
                for connection in vpls_info["vpls-connection-information"]["instance"]:
                    if connection["local-interface"]["interface-status"] == "Up":
                        vpls_connected = True
        else:
            vpls_connected = False
        return vpls_connected

    def check__values_for_nonetypes(self, data_dict: dict, expected_none_count: int = 0):
        """
        Checks the tpe dict for all tracked variables if all are none return a blank dict to match other vendors
        Args:
            tpe (dict): The tpe dict to check
        Returns:
            tpe (dict): The tpe dict with none types removed
        """
        count = 0
        flat_dict = self.flatten_complex_dict(data_dict)
        for each in flat_dict.values():
            if each in [None, "None"]:
                count += 1

        if count >= expected_none_count:
            return {}
        else:
            return data_dict

    def pe_fia_network_config(self):
        """
        Generates the network config for PE FIA devices
        Parameters:
            None
        Returns:
            tpe (dict): The TPE config
            fre (dict): The FRE config
        """
        network_config_data = self.get_network_config_data(
            self.circuit_details,
            self.service_type,
            self.device["Host Name"],
            self.device_prid,
        )

        try:
            network_config_data_sub = network_config_data["subinterface_config"]["configuration"]["interfaces"][
                self.port.lower()
            ]["unit"][0]
        except TypeError as error:
            self.logger.info("No subinterface config found. Error: {}".format(error))
            network_config_data_sub = None
            layer2 = None
            ipv6 = None
            ipv4 = None

        if network_config_data_sub:
            layer2 = network_config_data_sub.get("layer2-policer", "None")
            ipv6 = network_config_data_sub["family"].get("inet6", "None")
            ipv4 = network_config_data_sub["family"].get("inet", "None")

        tpe = self.cutthrough.execute_ra_command_file(
            self.device_prid,
            "get-tpe.json",
            parameters={"data.id": self.port.lower()},
            headers=None,
        ).json()["result"]

        if layer2:
            e_bandwidth = network_config_data_sub["layer2-policer"].get("output-policer", "None")
            i_bandwidth = network_config_data_sub["layer2-policer"].get("input-policer", "None")
        else:
            e_bandwidth = "None"
            i_bandwidth = "None"
        if "RL" in e_bandwidth:
            e_bandwidth = e_bandwidth.split("_")[1]
        if "RL" in i_bandwidth:
            i_bandwidth = i_bandwidth.split("_")[1]

        get_ipv4_data = self.get_ipv4_next_hop_data(network_config_data, self.device_prid, self.get_ipv4())
        fre = {
            "userLabel": network_config_data_sub.get("description", "None") if network_config_data_sub else "None",
            "e_bwProfileFlowParameters": e_bandwidth,
            "in_bwProfileFlowParameters": i_bandwidth,
            "bandwidth_description": (
                network_config_data_sub.get("bandwidth", "None") if network_config_data_sub else "None"
            ),
            "vlan": network_config_data_sub.get("vlan-id", "None") if network_config_data_sub else "None",
            "ipv6": (
                network_config_data_sub.get("family", dict())
                .get("inet6", dict())
                .get("address", dict())
                .get("name", "None")
                .upper()
                if ipv6
                else "None"
            ),
            "ipv4": get_ipv4_data.get("name", "None") if isinstance(get_ipv4_data, dict) and ipv4 else "None",
            "nextipv6hop": self.get_ipv6_next_hop_data(network_config_data["next_hop_ipv6"]),
            "nextipv4hop": get_ipv4_data.get("next-hop", "None") if ipv4 else "None",
        }

        return tpe, fre

    def get_ipv4(self):
        """Gets lanIpv4Addresses from circuit details"""
        return self.circuit_details["properties"]["service"][0]["data"]["fia"][0]["endPoints"][0]["lanIpv4Addresses"][0]

    def get_cos(self):
        """
        Gets the COS from circuit details
        Parameters:
            None
        Returns:
            cos (str): The COS identifier
        """
        # Does is EDNA check for the standards
        is_edna = self.check_is_edna(self.device_prid)

        # Uses is_edna to determine which COS lookup to use
        cos_list = (
            self.COS_FC_LOOKUP["PE"].get(self.cd_evc["cosNames"][0]["name"].upper(), None)
            if not is_edna
            else self.EDNA_COS_FC_LOOKUP["PE"].get(self.cd_evc["cosNames"][0]["name"].upper(), None)
        )
        # Checks device to see if the GRP standard COS is present
        # RA command will return true|false if the GRP standard is present
        is_grp_present = self.cutthrough.execute_ra_command_file(
            self.device_prid,
            "get-config-groups.json",
            parameters={"group": cos_list[0]},
            headers=None,
        )
        # If the devices has the GRP naming it will be used
        if is_grp_present.json()["result"]:
            cos_list = cos_list[0]
        # If the device does not have the GRP naming convention,
        # and the port type is INNI, and the customer handoff device is a juniper
        elif self.port_type.upper() == "INNI":
            cos_list = cos_list[2]
        # Otherwise; (UNI/ENNI/INNI(w/ non juniper customer handoff device))
        else:
            cos_list = cos_list[1]

        return cos_list

    def get_bw_in_kbps(self, bw):
        """
        Converts a bandwidth string to kbps
        Parameters:
            bw (str): The bandwidth string ex. 100M, 1G
        Returns:
            str: The bandwidth in kbps ex. 100000, 1000000
        """

        if bw is None:
            return "None"
        else:
            return str(
                int(re.findall(r"\d+", bw)[0]) * (1000000 if "g" in bw.lower() else 1000 if "m" in bw.lower() else 1)
            )

    def increment_ip_address(self, cidr):
        """
        Increments the IP address by 1 with no network checks
        Parameters:
            cidr (str): The IP address in CIDR notation
        Returns:
            str: The incremented IP address in CIDR notation
        """

        ip, mask = cidr.split("/")

        incremented_ip = ipaddress.ip_address(ip) + 1
        incremented_cidr = str(incremented_ip) + "/" + mask

        return incremented_cidr

    def circuit_details_vlan_change_if_untagged(self, circuit_details):
        """This will check if sVlan is Untagged and change value to 0 in circuit_details"""
        if circuit_details["properties"]["service"][0]["data"]["evc"][0].get("sVlan", None) == "Untagged":
            circuit_details["properties"]["service"][0]["data"]["evc"][0]["sVlan"] = "0"
        return circuit_details

    def pe_voice_network_config(self):
        """
        Generates the network config for PE VOICE devices
        Parameters:
            None
        Returns:
            tpe (dict): The TPE config
            fre (dict): The FRE config
        """
        network_config_data = self.get_network_config_data(
            self.circuit_details,
            self.service_type,
            self.device["Host Name"],
            self.device_prid,
        )

        try:
            network_config_data_sub = network_config_data["subinterface_config"]["configuration"]["interfaces"][
                self.port.lower()
            ]["unit"][0]
        except TypeError as error:
            self.logger.info("No subinterface config found. Error: {}".format(error))
            network_config_data_sub = None
            layer2 = None
            ipv6 = None
            ipv4 = None
        if network_config_data_sub:
            layer2 = network_config_data_sub.get("layer2-policer", None)
            ipv6 = network_config_data_sub["family"].get("inet6", None)
            ipv4 = network_config_data_sub["family"].get("inet", None)

        tpe = self.cutthrough.execute_ra_command_file(
            self.device_prid,
            "get-tpe.json",
            parameters={"data.id": self.port.lower()},
            headers=None,
        ).json()["result"]

        if layer2:
            e_bandwidth = network_config_data_sub["layer2-policer"].get("output-policer", "None")
            i_bandwidth = network_config_data_sub["layer2-policer"].get("input-policer", "None")
        else:
            e_bandwidth = "None"
            i_bandwidth = "None"

        if "RL" in e_bandwidth:
            e_bandwidth = e_bandwidth.split("_")[1]

        get_ipv4_data = self.get_ipv4_next_hop_data(network_config_data, self.device_prid, self.get_ipv4())
        fre = {
            "userLabel": network_config_data_sub.get("description", "None") if network_config_data_sub else "None",
            "e_bwProfileFlowParameters": e_bandwidth,
            "in_bwProfileFlowParameters": i_bandwidth,
            "bandwidth_description": (
                network_config_data_sub.get("bandwidth", "None") if network_config_data_sub else "None"
            ),
            "vlan": network_config_data_sub.get("vlan-id", "None") if network_config_data_sub else "None",
            "ipv6": (
                network_config_data_sub["family"]["inet6"].get("address", {}).get("name", "None") if ipv6 else "None"
            ),
            "ipv4": get_ipv4_data.get("name", "None") if ipv4 else "None",
            "nextipv6hop": self.get_ipv6_next_hop_data(network_config_data["next_hop_ipv6"]),
            "nextipv4hop": get_ipv4_data.get("next-hop", "None") if ipv4 else "None",
        }

        return tpe, fre

    def normalize_designed_model(self, designed_model):
        """
        This method normalizes the MDSO designed model to currently supported attributes for comparison
        Parameters:
            designed_model (dict): MDSO designed model
        Returns:
            normalized_designed_model (dict): Normalized designed model
        """
        output_policer = designed_model["properties"]["e_bwProfileFlowParameters"]
        if "RL" in output_policer:
            output_policer = output_policer.split("_")[1]

        normalized_model = {
            "userLabel": self.circuit_id,
            "e_bwProfileFlowParameters": output_policer,
            "in_bwProfileFlowParameters": designed_model["properties"].get("in_bwProfileFlowParameters", "None"),
            "bandwidth_description": designed_model["properties"][
                "e_bwProfileFlowParameters"
            ],  # This should match on device to e_bwProfileFlowParameters
            "vlan": designed_model["properties"]["vlan"],
            "ipv6": designed_model["properties"].get("wanIpv6Address", "None"),
            "ipv4": designed_model["properties"]["lanIpv4Addresses"][0],
            "port_name": designed_model["properties"]["port_name"],
            "nextipv4hop": designed_model["properties"].get("nextIpv4Hop"),
        }
        return normalized_model

    # === Voice Specific Methods ===

    def check_if_ip_in_arp_table(self) -> bool:
        ip = self.calculate_ipv4_for_voice_device()
        arp_response = self.get_voice_arp_table()
        self.logger.info(f"ARP Response: {arp_response}")
        voice_ip_in_arp_table = self.iterate_arp_table_for_ip(arp_response, ip)
        self.logger.info(f"IP: {ip} \n ARP Response: {arp_response} \n Voice IP in ARP Table: {voice_ip_in_arp_table}")
        return voice_ip_in_arp_table

    def calculate_ipv4_for_voice_device(self) -> str:
        ip_block = self.get_ipv4()
        return ip_block[:-3].rstrip(ip_block[:-3].split(".")[3]) + str(int(ip_block[:-3].split(".")[3]) + 1)

    def get_voice_arp_table(self) -> dict:
        port_vlan = f"|{self.port.lower()}.{self.vlan}"
        try:
            arp_response = self.execute_ra_command_file(
                self.device_prid,
                "get-arp-query.json",
                parameters={"uniqueid": port_vlan},
                headers=None,
            ).json()["result"]
        except Exception:
            arp_response = {}
        return arp_response

    def iterate_arp_table_for_ip(self, arp_response, ip) -> bool:
        if arp_response.get("properties", dict()).get("result"):
            if isinstance(arp_response["properties"]["result"], list):
                return bool([arp for arp in arp_response["properties"]["result"] if ip in arp["ip-address"]])
            return bool(arp_response["properties"]["result"]["ip-address"] == ip)
        return False

    def get_ms_vlan_for_design_model(self):
        if self.base_model.get("FRE") and self.ms_vlan:
            self.base_model["FRE"].update({"ms_vlan": self.ms_vlan})

    def get_ms_vlan_for_network_model(self):
        if self.ms_vlan:
            response = self.get_interface_values_from_network_device_with_ra_commands()
            return self.get_ms_vlan_if_found_in_response(response)

    def get_interface_values_from_network_device_with_ra_commands(self):
        self.logger.info(f'self.port_type: {self.port_type}, self.device["Model"]: {self.device["Model"]}')
        if "MX" in self.device["Model"]:
            return self.get_network_pe_apply_groups()
        else:
            return self.get_interface_config(self.device_prid, self.port.lower(), "0")

    def get_ms_vlan_if_found_in_response(self, response):
        ms_vlan = ""
        if not response or not response.get("configuration"):
            return ms_vlan
        configuration = response["configuration"]
        if configuration:
            if "MX" in self.device["Model"]:
                device_apply_groups = configuration["interfaces"]["interface"]["apply-groups"]
                ms_vlan = "88" if any(apply_group in device_apply_groups for apply_group in MS_APPLY_GROUPS) else ""
            else:
                vlan_members = configuration["interfaces"][self.port.lower()]["unit"][0]["family"][
                    "ethernet-switching"
                ]["vlan"]["members"]
                ms_vlan = "88" if "MGMT88" in vlan_members else ""
        return ms_vlan

    def get_network_pe_apply_groups(self) -> dict:
        try:
            network_apply_groups = self.cutthrough.execute_ra_command_file(
                self.device_prid,
                "get-apply-groups-inner.json",
                parameters={"interface": self.port.lower()},
                headers=None,
            ).json()["result"]["data"]
        except Exception as e:
            self.logger.info(f"Failed to gather network values {self.device['Host Name']} with error {e}")
        return network_apply_groups

    def get_locally_switched_l2circuit_info(self):
        try:
            locally_switch_info = self.cutthrough.execute_ra_command_file(
                self.device_prid,
                "get-l2-circuits-in-cmd.json",
                parameters={},
                headers=None,
            ).json()["result"]["configuration"]["protocols"]["l2circuit"]["local-switching"]
        except Exception as e:
            self.logger.info(f"Failed to gather network l2circuit connection values {self.device['Host Name']} with error {e}")
        return locally_switch_info

    def get_both_pe_ports_and_add_to_list(self):
        locally_switched_ports = []
        for device in self.topology_dictionary:
            for value in device.values():
                if value['Role'] == "PE":
                    locally_switched_ports.append(f'{value["Client Interface"]}.{self.vlan}'.lower())
        return locally_switched_ports

    def get_locally_switched_values_for_network_model(self, locally_switch_info):
        l2flow = {
            "remoteCarrierName": "NOT LOCALLY SWITCHED",
            "siteNetworkAccessId": "NOT LOCALLY SWITCHED"
        }
        for l2_circuit in locally_switch_info['interface']:
            if self.local_switch_value_locations(0, l2_circuit) and self.local_switch_value_locations(1, l2_circuit):
                l2flow = {
                    "remoteCarrierName": "LOCALLY SWITCHED",
                    "siteNetworkAccessId": "LOCALLY SWITCHED"
                }
        return l2flow

    def local_switch_value_locations(self, index, l2_circuit):
        return self.locally_switched_ports[index] in l2_circuit['name'] or self.locally_switched_ports[index] in l2_circuit['end-interface']['interface']
