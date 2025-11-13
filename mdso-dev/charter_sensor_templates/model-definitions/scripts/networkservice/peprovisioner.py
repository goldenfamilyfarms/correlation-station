""" -*- coding: utf-8 -*-

PeProvision Base Plan

To be inherited by other plans that do service provisioning on the PE.  This package
will provision the Logical TPE (VLAN/CTP) on the PE Router before any specific
service provisioning is required (like FIA or ELAN)

Versions:
   0.1 Dec 20, 2018
       Initial check in of PeProvisioner

"""
import sys
sys.path.append('model-definitions')
from scripts.common_plan import CommonPlan
import re
import json


class PeProvisioner(CommonPlan):
    """
    this is the class used for initial activation of service fia service provisioner
    """

    COS_FC_LOOKUP = {
        "PE": {
            "SERVICEPORT_UNCLASSIFIED_COS": "BE-CS-B",
            "SERVICEPORT_BRONZE_COS": "BE-CS-B",
            "SERVICEPORT_SILVER_COS": "CS-S",
            "SERVICEPORT_GOLD_COS": "CS-G",
        }
    }
    EDNA_COS_FC_LOOKUP = {
        "PE": {
            "TP_SERVICEPORT_UNCLASSIFIED_COS": "BE-CS-B",
            "TP_SERVICEPORT_BRONZE_COS": "BE-CS-B",
            "TP_SERVICEPORT_SILVER_COS": "CS-S",
            "TP_SERVICEPORT_GOLD_COS": "CS-G",
        }
    }
    EDNA_FW_obj = [
        {"name": "TF_FIA-Filter_4", "direction": "ingress", "type": "inet"},
        {"name": "TF_FIA-Filter_6", "direction": "ingress", "type": "inet6"},
    ]

    @staticmethod
    def delete_pe_logical_ctp(plan, network_function, interface, svlan):
        """
        Method to delete the logical TPE on a device

        :param network_function: Network Function object or ID
        :param interface: Physical Interface name (ge-1/1/1)
        :param svlan: VLAN ID
        :type network_function: dict or str
        :type network_function: dict or str
        :type network_function: dict or str
        """
        if isinstance(network_function, str):
            network_function = plan.bpo.resources.get(network_function)

        device_prid = network_function["providerResourceId"]
        plan.execute_ra_command_file(
            device_prid,
            "delete-logical-tpe.json",
            parameters={"interface": interface, "unit": 0 if svlan.lower() == "untagged" else svlan, "commit": True},
            headers=None,
        )

    def create_pe_tpe(self, properties):
        # Getting required domain
        device_pid = self.bpo.resources.get(properties["pe_device_rid"])["productId"]
        self.domain_id = self.bpo.market.get("/products/%s" % device_pid)["domainId"]
        # Update PTP TPE from disable to active state
        # this seems to only add phys int
        self.update_ptp_tpe(properties["port_id"], properties["interface_userLabel"])

        # create TPE for FIA service
        pe_tpe_res = self.create_tpe(properties)
        # we create TPE CTP but logical interface won't exists as TPE resource due to
        # the fact that RA doesn't list CTP logical interface, therefore it will try to
        # delete it on the next polling cycle.
        # we must set discovered to true for cleanup purpose otherwise it will be linger.
        # setting discovered true will terminate the resource next polling cycle until then
        # this resource will lingers.
        self.logger.info("Patch logical TPE resource to 'discovered: True' ")
        self.bpo.resources.patch(pe_tpe_res.resource_id, {"discovered": True})

        return pe_tpe_res.resource_id

    def create_tpe(self, properties, tpe_properties=None):
        """
        creates the TPE resource for service
        """
        tpe_pid = self.bpo.products.get_by_domain_and_type(self.domain_id, "tosca.resourceTypes.TPE")[0]["id"]
        if not tpe_properties:
            tpe_properties = self.get_tpe_properties(properties)
        # Define what unit we are provisioning on
        if properties.get("vlan") and properties["vlan"].lower() == "untagged":
            unit = "0"
        elif properties["type_2"]:
            unit = properties["unit"]
        else:
            unit = tpe_properties["data"]["attributes"]["locations"][0]["vlan"]
        tpe_label = (properties["port_name"].lower() + "." + unit)
        tpe_object = {
            "label": tpe_label,
            "resourceTypeId": "tosca.resourceTypes.TPE",
            "productId": tpe_pid,
            "properties": tpe_properties,
        }
        self.logger.info("**TPE OBJECT**: {}".format(json.dumps(tpe_object)))
        try:
            tpe = self.bpo.resources.create(self.params["resourceId"], tpe_object, wait_active=False)
        except Exception as ex:
            self.logger.info("Commit failed for: %s" % (str(ex)))

        return tpe

    def update_ptp_tpe(self, port_id, description):
        """
        updates the PE port description
        """

        ptp_resource = self.bpo.resources.get(port_id)
        interface_name = ptp_resource["properties"]["data"]["attributes"]["nativeName"]
        self.device_pr_id = ptp_resource["providerResourceId"].split("::")[0]

        if not description == "None":
            if ptp_resource["properties"]["data"]["attributes"]["userLabel"] == "":
                self.execute_ra_command_file(
                    self.device_pr_id,
                    "set-physical-interface-params-inner.json",
                    {"interface": interface_name.lower(), "param": "description", "description": description},
                )

    def get_tpe_properties(self, properties):
        """
        generate TPE object on PE port for FIA service
        """
        # Define what unit we are provisioning on
        if properties.get("vlan") and properties["vlan"].lower() == "untagged":
            unit = "0"
        elif properties["type_2"]:
            unit = properties["unit"]
        else:
            unit = properties["vlan"]
        tpe_properties = {
            "device": self.bpo.resources.get(properties["pe_device_rid"])["providerResourceId"],
            "data": {
                "attributes": {
                    "structureType": "CTPServerToClient",
                    "bwpPerUni": [],
                    "layerTerminations": [
                        {
                            "layerRate": "ETHERNET",
                            "structureType": "exposed lone cp",
                            "terminationState": "layer termination cannot terminate",
                            "active": True,
                            "mplsPackage": {
                                "bw": {
                                    "bwKbps": self.get_bw_in_kbps(properties["e_bwProfileFlowParameters"])
                                    if "e_bwProfileFlowParameters" in properties.keys()
                                    else self.get_bw_in_kbps(properties["in_bwProfileFlowParameters"])
                                }
                            },
                            "signalIndex": {"mappingTable": [{}]},
                        }
                    ],
                    "additionalAttributes": {},
                },
                "id": properties["port_name"].lower() + "." + unit,
                "relationships": {
                    "owningServerTpe": {"data": {"id": properties["port_id"], "type": "tpes"}},
                    "networkConstruct": {
                        "data": {"id": properties["network_construct_id"], "type": "networkConstructs"}
                    },
                },
                "type": "tpes",
            },
        }
        if str(properties["userLabel"].split(":")[-3]) == "VOICE":
            del tpe_properties["data"]["attributes"]["layerTerminations"][0]["mplsPackage"]["bw"]

        if "wanIpv6Address" in properties.keys():
            tpe_properties["data"]["attributes"]["additionalAttributes"]["ipv6Addresses"] = [
                properties["wanIpv6Address"].lower()
            ]

        if properties.get("fia_type") == "DIRECT":
            if "lanIpv4Addresses" in properties.keys():
                tpe_properties["data"]["attributes"]["additionalAttributes"]["ipv4Addresses"] = properties[
                    "lanIpv4Addresses"
                ]
        else:
            if "wanIpv4Address" in properties.keys():
                tpe_properties["data"]["attributes"]["additionalAttributes"]["ipv4Addresses"] = [
                    properties["wanIpv4Address"]
                ]

        # Determine if MX has been converted to EDNA, utilize appropriate apply-groups
        self.logger.info("=======PROPERTIES: %s" % properties)
        device_prid = self.bpo.resources.get(properties["pe_device_rid"])["providerResourceId"]
        is_edna = self.check_is_edna(device_prid)
        self.logger.info("IS_EDNA: %s" % is_edna)

        if "fia_type" in properties.keys():
            if properties["userLabel"].split(":")[-3] == "VOICE":
                tpe_properties["data"]["attributes"]["layerTerminations"][0]["signalIndex"]["mappingTable"][0]["cos"] = (
                    "SERVICEPORT_VOICE_COS" if not is_edna else "TP_SERVICEPORT_VOICE_COS"
                )
            else:
                tpe_properties["data"]["attributes"]["layerTerminations"][0]["signalIndex"]["mappingTable"][0]["cos"] = (
                    "SERVICEPORT_FIA_COS" if not is_edna else "TP_SERVICEPORT_FIA_COS"
                )
        else:
            if "port_role" in properties and properties["port_role"].upper() == "ENNI":
                tpe_properties["data"]["attributes"]["layerTerminations"][0]["signalIndex"]["mappingTable"][0][
                    "forwardingClass"
                ] = (
                    self.COS_FC_LOOKUP["PE"][properties["cos"]]
                    if not is_edna
                    else self.EDNA_COS_FC_LOOKUP["PE"][properties["cos"]]
                )
            else:
                tpe_properties["data"]["attributes"]["layerTerminations"][0]["signalIndex"]["mappingTable"][0][
                    "cos"
                ] = properties["cos"]
        if not properties["userLabel"] == "None":
            tpe_properties["data"]["attributes"]["userLabel"] = properties["userLabel"]

        if "fia_type" not in properties.keys():
            tpe_properties["data"]["attributes"]["encapsulation"] = {"encapsType": "vlan-vpls"}

        for bwfp in ["in_bwProfileFlowParameters", "e_bwProfileFlowParameters"]:
            if bwfp in properties.keys():
                bwfp_object = {
                    "ingressBwpPerUni"
                    if bwfp == "in_bwProfileFlowParameters"
                    else "egressBwpPerUni": {
                        "envelopeId": "layer2-policer:two-color" if "fia_type" in properties.keys() else "vpls",
                        "bwProfileFlowParameters": self.get_bandwidth_formatted(properties[bwfp], is_edna),
                    }
                }
                tpe_properties["data"]["attributes"]["bwpPerUni"].append(bwfp_object)

        if properties["type_2"]:
            tpe_properties["data"]["attributes"]["locations"] = [{"vlanlist": [properties["outer_vlan"], "type 2", properties["inner_vlan"]]}]
        if properties.get("vlan") and properties["vlan"].lower() != "untagged":
            tpe_properties["data"]["attributes"]["locations"] = [{"vlan": properties["vlan"]}]
        if properties["port_role"].upper() == "UNI":
            circuit_details = self.get_associated_circuit_details(self.params["resourceId"])
            node_name = str(
                self.bpo.resources.get(properties["pe_device_rid"])["properties"]["connection"]["hostname"].split(".")[
                    0
                ]
            )
            port_id = str(self.bpo.resources.get(properties["port_id"])["properties"]["data"]["id"])
            cvlan = self.get_cvlans_for_uni_ep(circuit_details, node_name + "-" + port_id)
            if cvlan:
                tpe_properties["data"]["attributes"]["locations"][0]["vlan"] = str(cvlan[0])
                tpe_properties["data"]["id"] = (
                    str(tpe_properties["data"]["id"].rsplit(".", 1)[0]) + "." + str(cvlan[0])
                )

        if "firewallFilters" in properties.keys():
            self.logger.info("Properties: {}".format(properties))
            for firewallFilter in properties["firewallFilters"]:
                firewallFilter["type"] = "inet" if firewallFilter["type"] == "ipv4" else "inet6"
                tpe_properties["data"]["attributes"]["additionalAttributes"]["filterProfile"] = (
                    self.EDNA_FW_obj if is_edna else properties["firewallFilters"]
                )

        if "ipv4ArpPolicer" in properties.keys():
            tpe_properties["data"]["attributes"]["additionalAttributes"]["ipv4ArpPolicer"] = properties[
                "ipv4ArpPolicer"
            ]
        return tpe_properties

    def get_bw_in_kbps(self, bw):
        """
        return bw in kbps
        """
        return str(
            int(re.findall(r"\d+", bw)[0]) * (1000000 if "g" in bw.lower() else 1000 if "m" in bw.lower() else 1)
        )

    def get_bandwidth_formatted(self, bw, edna=False):
        """
        return policer name as expected by the RA
        """
        rate = 1
        unit = "m"
        bw = str(bw).lower()
        response = re.search(r"[0-9]+", bw)
        if response:
            rate = int(response.group())

        if "g" in bw:
            unit = "g"
        elif "k" in bw:
            unit = "k"

        # Non-EDNA policer: 50m / EDNA policer: RL_50m
        policer_bw = "RL_" + str(rate) + str(unit) if edna else str(rate) + str(unit)
        # return str(rate) + str(unit)
        return policer_bw
