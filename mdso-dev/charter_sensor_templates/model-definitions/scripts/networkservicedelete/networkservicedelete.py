""" -*- coding: utf-8 -*-

NetworkServiceDelete Plans

Versions:
   0.1 Dec 03, 2018
       Initial check in of CircuitDataCollection plans

"""
import sys
sys.path.append('model-definitions')
from scripts.common_plan import CommonPlan


class Activate(CommonPlan):
    """this is the class that is called for the deletion of the
    Network Service.  The only input it requires is the circuit_id
    associated with the service.
    """

    def process_with_cleanup(self):
        self.circuit_id = self.properties["circuit_id"]
        self.label = self.resource["label"]

        # create circuit details collector resource for this network service update
        self.circuit_details_id = self.create_circuit_details_resource(self.circuit_id)
        circuit_details_collector = self.bpo.resources.get(self.circuit_details_id)
        self.circuit_details_res_id = circuit_details_collector["properties"]["circuit_details_id"]

        # create the service device validator resource to make sure all devices are present.
        self.create_service_device_validator_resource(self.circuit_details_res_id, self.circuit_id)

        # creating the Device Onboarders
        self.create_service_device_onboarder_resource(self.circuit_details_res_id, self.circuit_id)
        circuit_details = self.bpo.resources.get(self.circuit_details_res_id)

        network_services = self.get_associated_network_service_for_circuit_id(self.circuit_id, include_all=True)
        if network_services is None:
            raise Exception("Unable to get Network Service for " + self.circuit_id)

        for network_service in network_services:
            self.bpo.resources.delete(network_service["id"])

        # CLeaning up the device
        evc = circuit_details["properties"]["service"][0]["data"]["evc"][0]
        svlan = "0" if evc["sVlan"] in ["untagged", "Untagged"] else evc["sVlan"]
        pe_list = []
        agg_list = []
        mtu_list = []
        cpe_list = []

        spoke_list = self.create_device_dict_from_circuit_details(circuit_details)
        for spoke in spoke_list:
            for device, values in spoke.items():
                if values["Role"].upper() == "PE":
                    pe_list.append(values)
                elif values["Role"].upper() == "AGG":
                    agg_list.append(values)
                elif values["Role"].upper() == "CPE" or (
                    values["Role"].upper() == "MTU"
                    and (
                        str(values["Client Neighbor"].lower()) == "none"
                        and (
                            self.COMMON_TYPE_LOOKUP[values["Vendor"]].get("MTU_BW_INCLUSION")
                            and self.COMMON_TYPE_LOOKUP[values["Vendor"]]["MTU_BW_INCLUSION"]["MODEL"]
                            == values["Model"]
                        )
                    )
                ):
                    cpe_list.append(values)
                elif values["Role"] == "MTU":
                    mtu_list.append(values)
                else:
                    self.exit_error("Device %s has unsupported role %s " % (device, values["Role"]))

        self.delete_pe_context(circuit_details, pe_list, svlan)
        self.delete_agg_context(circuit_details, agg_list, svlan)
        self.delete_mtu_context(circuit_details, mtu_list, svlan)
        self.delete_cpe_context(circuit_details, cpe_list, svlan)

        return {}

    def process(self):
        result = {}
        try:
            result = self.process_with_cleanup()
        except RuntimeError:
            self.create_cleanup_resource()  # cleanup the unneeded info objects
            raise
        self.create_cleanup_resource()  # cleanup the unneeded info objects
        return result

    def create_circuit_details_resource(self, circuit_id):
        """
        Function to create circuit details collector resource
        """

        circuit_details_collector_product_id = self.get_built_in_product(self.BUILT_IN_CIRCUIT_DATA_COLLECTOR_TYPE)[
            "id"
        ]
        cdc_resource = {
            "label": self.bpo.resources.get(self.params["resourceId"])["label"] + "." + "circuit_details_collector",
            "productId": circuit_details_collector_product_id,
            "properties": {
                "circuit_id": circuit_id,
                "operation": "NETWORK_SERVICE_DELETION",
                "use_alternate_circuit_details_server": self.properties.get(
                    "use_alternate_circuit_details_server", False
                ),
            },
        }
        cdc_res_id = self.bpo.resources.create(self.params["resourceId"], cdc_resource)
        return cdc_res_id.resource_id

    def create_service_device_validator_resource(self, circuit_details_resource_id, circuit_id):
        """
        Function to create network service bandwidth
        update resource.
        """

        service_device_validator_product = self.get_built_in_product(self.BUILT_IN_SERVICE_DEVICE_VALIDATORY_TYPE)["id"]
        service_device_validator_res = {
            "label": self.label + "service_device_validator",
            "productId": service_device_validator_product,
            "properties": {
                "circuit_details_id": circuit_details_resource_id,
                "circuit_id": circuit_id,
                "operation": "NETWORK_SERVICE_DELETION",
            },
        }
        self.bpo.resources.create(self.params["resourceId"], service_device_validator_res)

    def create_service_device_onboarder_resource(self, circuit_details_resource_id, circuit_id):
        """
        Function to create network service bandwidth
        update resource.
        """

        for context in ["PE", "CPE"]:
            service_device_onboarder_product = self.get_built_in_product(self.BUILT_IN_SERVICE_DEVICE_ONBOARDER_TYPE)[
                "id"
            ]
            service_device_onboarder_res = {
                "label": self.label + "service_device_onboarder",
                "productId": service_device_onboarder_product,
                "properties": {
                    "circuit_details_id": circuit_details_resource_id,
                    "circuit_id": circuit_id,
                    "context": context,
                    "operation": "NETWORK_SERVICE_DELETION",
                },
            }
            self.bpo.resources.create(self.params["resourceId"], service_device_onboarder_res)

    def delete_pe_context(self, circuit_details, pe_list, svlan):
        """
        Method to delete all the pe device configuration, which was
        configured for the given circuit id through racutthrough.
        """
        service_type = circuit_details["properties"]["serviceType"]
        if not service_type == "ELINE":
            if "VOICE" in service_type:
                required_resource_type = self.PE_SPECIFIC_RESOURCE_TYPES[service_type]
            else:
                required_resource_type = "charter.resourceTypes.ServiceProvisioner_" + service_type.upper()
            pe_provisioner_obj = {
                "label": self.properties["circuit_id"] + "-" + service_type + "-Provisioner",
                "productId": self.get_built_in_product(required_resource_type)["id"],
                "properties": {
                    "circuit_details_id": self.circuit_details_res_id,
                    "stage": "PRODUCTION",
                    "context": "PE",
                    "operation": self.TERMINATE_OPERATION_STRING,
                    "circuit_id": self.circuit_id,
                },
            }
            self.bpo.resources.create(self.params["resourceId"], pe_provisioner_obj)
        else:
            # create mef segment for ELine service
            evc = circuit_details["properties"]["service"][0]["data"]["evc"][0]
            evc_id = int(evc.get("evcId")) if evc.get("evcId") else 0
            mgmt_ips = []
            endpoints = []
            network_function_resources = []
            for pe in pe_list:
                nf = self.get_network_function_by_host(pe["FQDN"])
                if not nf:
                    self.exit_error(
                        "No Network Function Resource was found on the server for the " "host {}".format(pe["FQDN"])
                    )
                port = pe["Client Interface"]
                pe_endpoint = {
                    "node_id": nf["id"],
                    "port_id": self.get_port_id_from_port_name_and_device_id_retry(port, nf["id"], pe["Role"]),
                    "description": pe["Client Interface Description"],
                    "svlan": int(svlan),
                }
                mgmt_ips.append(pe["Management IP"])
                network_function_resources.append(nf)
                endpoints.append(pe_endpoint)

            # Be careful about the spelling here. The name of the property
            # is spelled neighbour_ip. It's not the American spelling of neighbor.
            endpoints[0]["neighbour_ip"] = mgmt_ips[1]
            endpoints[1]["neighbour_ip"] = mgmt_ips[0]
            package_0 = network_function_resources[0]["resourceTypeId"].split(".")[0]
            package_1 = network_function_resources[1]["resourceTypeId"].split(".")[0]

            if package_0 == package_1:
                mef_plugin_product_id = self.get_mef_plugin_product(package_0)

                segment_properties = {
                    "operation": "TERMINATE",
                    "segment_info": {
                        "name": self.circuit_id,
                        "evcid": evc_id,
                        "type": evc["serviceType"],
                        "endpoints": endpoints,
                    },
                }
                self.create_and_delete_segment_resource(
                    self.resource["id"], mef_plugin_product_id, segment_properties, self.circuit_id
                )

            else:
                self.logger.info("deleting resource for two different packages %s" % str([package_0, package_1]))

                mef_plugin_product_id_0 = self.get_mef_plugin_product(package_0)
                self.logger.info("MEF plugin product- %s for package_0- %s" % (mef_plugin_product_id_0, package_0))
                segment_properties_0 = {
                    "operation": "TERMINATE",
                    "segment_info": {
                        "name": self.circuit_id,
                        "evcid": evc_id,
                        "type": evc["serviceType"],
                        "endpoints": [endpoints[0]],
                    },
                }
                self.logger.info("Segment properties- %s for package_0- %s" % (str(segment_properties_0), package_0))
                self.create_and_delete_segment_resource(
                    self.resource["id"], mef_plugin_product_id_0, segment_properties_0, self.circuit_id
                )

                mef_plugin_product_id_1 = self.get_mef_plugin_product(package_1)
                self.logger.info("MEF plugin product- %s for package_1- %s" % (mef_plugin_product_id_1, package_1))
                segment_properties_1 = {
                    "operation": "TERMINATE",
                    "segment_info": {
                        "name": self.circuit_id,
                        "evcid": evc_id,
                        "type": evc["serviceType"],
                        "endpoints": [endpoints[1]],
                    },
                }
                self.logger.info("Segment properties- %s for package_1- %s" % (str(segment_properties_1), package_1))
                self.create_and_delete_segment_resource(
                    self.resource["id"], mef_plugin_product_id_1, segment_properties_1, self.circuit_id
                )

    def delete_agg_context(self, circuit_details, agg_list, svlan):
        """
        Method to delete all the agg devices configuration, which was
        configured for the given circuit id through racutthrough.
        """

        evc = circuit_details["properties"]["service"][0]["data"]["evc"][0]
        for agg in agg_list:
            agg_device = self.get_network_function_for_spoke_device(agg)
            package = agg_device["resourceTypeId"].split(".")[0]
            client_port_id = self.get_port_id_from_port_name_and_device_id_retry(
                agg["Client Interface"], agg_device["id"], agg["Role"]
            )
            nw_port_id = self.get_port_id_from_port_name_and_device_id_retry(
                agg["Network Interface"], agg_device["id"], agg["Role"]
            )
            mef_plugin_product_id = self.get_mef_plugin_product(package)
            segment_properties = {
                "operation": "TERMINATE",
                "segment_info": {
                    "name": self.circuit_id,
                    "type": evc["serviceType"],
                    "endpoints": [
                        {
                            "node_id": agg_device["id"],
                            "port_id": client_port_id,
                            "svlan": int(svlan),
                        },
                        {
                            "node_id": agg_device["id"],
                            "port_id": nw_port_id,
                            "svlan": int(svlan),
                        },
                    ],
                },
            }
            self.create_and_delete_segment_resource(
                self.resource["id"], mef_plugin_product_id, segment_properties, self.circuit_id
            )

    def delete_mtu_context(self, circuit_details, mtu_list, svlan):
        """
        Method to delete all the mtu devices configuration, which was
        configured for the given circuit id through racutthrough.
        """

        evc = circuit_details["properties"]["service"][0]["data"]["evc"][0]
        for mtu in mtu_list:
            mtu_device = self.get_network_function_for_spoke_device(mtu)
            package = mtu_device["resourceTypeId"].split(".")[0]
            client_port_id = self.get_port_id_from_port_name_and_device_id_retry(
                mtu["Client Interface"], mtu_device["id"], mtu["Role"]
            )
            client_port_decr = mtu["Client Interface Description"]
            nw_port_id = self.get_port_id_from_port_name_and_device_id_retry(
                mtu["Network Interface"], mtu_device["id"], mtu["Role"]
            )
            mef_plugin_product_id = self.get_mef_plugin_product(package)
            segment_properties = {
                "operation": "TERMINATE",
                "segment_info": {
                    "name": self.circuit_id,
                    "type": evc["serviceType"],
                    "endpoints": [
                        {
                            "node_id": mtu_device["id"],
                            "port_id": client_port_id,
                            "svlan": int(svlan),
                            "description": client_port_decr,
                        },
                        {
                            "node_id": mtu_device["id"],
                            "port_id": nw_port_id,
                            "svlan": int(svlan),
                        },
                    ],
                },
            }
            self.create_and_delete_segment_resource(
                self.resource["id"], mef_plugin_product_id, segment_properties, self.circuit_id
            )

    def delete_cpe_context(self, circuit_details, cpe_list, svlan):
        """
        Method to delete all the cpe device configuration, which was
        configured for the given circuit id through racutthrough.
        """
        evc = circuit_details["properties"]["service"][0]["data"]["evc"][0]
        for cpe in cpe_list:
            cpe_device = self.get_network_function_for_spoke_device(cpe)
            if cpe_device is not None:
                package = cpe_device["resourceTypeId"].split(".")[0]
                client_port = cpe["Client Interface"]
                network_port = cpe["Network Interface"]
                svlan = evc["sVlan"]
                cvlan = self.get_cvlans_for_uni_ep(circuit_details, cpe["Host Name"] + "-" + cpe["Client Interface"])
                port_id = self.get_port_id_from_port_name_and_device_id_retry(client_port, cpe_device["id"])

                product_id = self.get_mef_plugin_product(package)
                segment_properties = {
                    "operation": "TERMINATE",
                    "segment_info": {
                        "name": self.circuit_id,
                        "type": evc["serviceType"],
                        "endpoints": [
                            {
                                "node_id": cpe_device["id"],
                                "port_id": port_id,
                                "svlan": int(svlan),
                                "cvlan": cvlan,
                                "cosIdentifier": self.COS_LOOKUP["CPE"][evc["cosNames"][0]["name"]],
                            },
                            {
                                "node_id": cpe_device["id"],
                                "svlan": int(svlan),
                                "cvlan": cvlan,
                                "cosIdentifier": self.COS_LOOKUP["CPE"][evc["cosNames"][0]["name"]],
                                "port_id": self.get_port_id_from_port_name_and_device_id_retry(
                                    network_port, cpe_device["id"]
                                ),
                            },
                        ],
                    },
                }
                self.create_and_delete_segment_resource(
                    self.resource["id"], product_id, segment_properties, self.circuit_id
                )
                self.terminate_update_cpe(circuit_details, cpe)

    def terminate_update_cpe(self, circuit_details, device):
        """update the CPE port properties
        termination of the service on the CPE port
        """
        state = "OOS_AUMA"

        # FIRST DO THE UNI PORT
        interface = device["Client Interface"]
        reachable_via = self.get_node_reachability(circuit_details, device["Host Name"])
        # device_role = self.get_node_role(circuit_details, device["Host Name"])

        connection_param = "IP" if reachable_via == "IP" else "FQDN"

        if connection_param == "IP":
            host = self.get_node_management_ip(circuit_details, device["Host Name"])

        else:
            host = self.get_node_fqdn(circuit_details, device["Host Name"])

        nf = self.get_network_function_by_host(host)
        tpe_id = self.get_port_id_from_port_name_and_device_id_retry(interface, nf["id"])
        if tpe_id is None:
            interface = interface.replace("ETH-PORT", "ETH_PORT")
            tpe_id = self.get_port_id_from_port_name_and_device_id_retry(interface, nf["id"])
        if tpe_id is None:
            self.logger.warn("Unable to get TPE for host %s name %s" % (device["Host Name"], interface))
            return

        tpe = self.bpo.resources.get(tpe_id)

        # Only update the TPE if there is only 1 Active FRE on it
        fres = self.get_dependents_by_type_and_query(
            tpe["id"], resource_type=self.BUILT_IN_FRE_TYPE, recursive=True, query="properties.networkRole:IFRE"
        )
        active_ctp_count = 0
        for fre in fres:
            if fre["properties"]["data"]["attributes"]["adminState"] == "enabled":
                active_ctp_count += 1

        self.logger.debug("TPE %s has %s number of active CTPs." % (interface, str(active_ctp_count)))
        is_discovered = tpe["discovered"]
        if active_ctp_count == 0:
            if is_discovered is True:
                self.bpo.resources.patch(tpe["id"], {"discovered": False})

            props = tpe["properties"]
            props["data"]["attributes"]["state"] = state
            props["data"]["attributes"]["userLabel"] = ""

            if (
                props["data"]["attributes"]["layerTerminations"][0].get("additionalAttributes", {}).get("l2cpProfile")
                is not None
            ):
                props["data"]["attributes"]["layerTerminations"][0]["additionalAttributes"].pop("l2cpProfile")
            if (
                props["data"]["attributes"]["layerTerminations"][0].get("additionalAttributes", {}).get("egressMtu")
                is not None
            ):
                props["data"]["attributes"]["layerTerminations"][0]["additionalAttributes"].pop("egressMtu")

            self.logger.debug("Updating port %s with attributes: %s" % (interface, str(props["data"]["attributes"])))
            self.bpo.resources.patch(tpe["id"], {"properties": {"data": {"attributes": props["data"]["attributes"]}}})
            if is_discovered is True:
                self.bpo.resources.patch(tpe["id"], {"discovered": True})

            self.logger.debug(
                "Checking TPE differences for port %s with attributes: %s"
                % (interface, str(props["data"]["attributes"]))
            )
            try:
                self.await_differences_cleared_collect_timing(
                    "CPE TPE resource ", tpe["id"], interval=10.0, tmax=1200.0
                )
            except Exception as ex:
                self.exit_error(
                    "Unable to get differences cleared for port %s with attributes: %s due to error: %s"
                    % (interface, str(props["data"]["attributes"]), str(ex))
                )

            self.logger.debug(
                "Awaiting until TPE is active for port %s with attributes: %s"
                % (interface, str(props["data"]["attributes"]))
            )
            self.await_active_collect_timing([tpe["id"]], interval=1.0, tmax=30.0)

        # NOW FOR THE NNI PORT
        if self.COMMON_TYPE_LOOKUP[device["Vendor"]].get(device["Model"]) is None:
            self.logger.debug("No model that matches %s in the lookup." % device["Model"])
            return

    def create_cleanup_resource(self):
        cleanup_productId = self.get_built_in_product(self.BUILT_IN_NETWORK_SERVICE_CLEANER_TYPE)["id"]
        cleanup_resource = {
            "label": self.bpo.resources.get(self.params["resourceId"])["label"] + "." + "cleaner",
            "productId": cleanup_productId,
            "properties": {
                "resource_id": self.params["resourceId"],
            },
        }
        cleanup_res_id = self.bpo.resources.create(self.params["resourceId"], cleanup_resource)
        return cleanup_res_id


class Terminate(CommonPlan):
    """terminate call for network service update"""

    def process(self):
        dependencies = self.bpo.resources.get_dependencies(self.resource["id"])
        self.bpo.resources.delete_dependencies(self.resource["id"], None, dependencies)
