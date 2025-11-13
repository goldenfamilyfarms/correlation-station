""" -*- coding: utf-8 -*-

BandwidthUpdate Plans

Versions:
   0.1 Dec 03, 2018
       Initial check in of CircuitDataCollection plans

"""
import re
import sys
sys.path.append('model-definitions')
from scripts.common_plan import CommonPlan


class Activate(CommonPlan):
    """this is the class that is called for the initial updation of the
    Network Service bandwidth.  The only input it requires is the circuit_id
    associated with the service.
    """

    def process(self):
        self.operation = self.properties["operation"]
        self.circuit_id = self.properties["circuit_id"]
        self.circuit_res_id = self.properties["circuit_details_resource_id"]
        circuit_details = self.get_resource(self.circuit_res_id)
        self.logger.info("circuit_details: {}".format(circuit_details))

        pe_list = []
        agg_list = []
        mtu_list = []
        cpe_list = []

        # get all the spokes in network service
        spoke_list = self.create_device_dict_from_circuit_details(circuit_details)

        if self.operation == "SERVICE_MAPPER":
            # dictionary of to be updated devices passed from network service update on behalf of service mapper
            # this is an optional attribute that is used for service mapper
            self.devices_to_be_updated = self.properties["devices_to_be_updated"]["bandwidth_update"]
            self.logger.info("devices_to_be_updated: {}".format(self.devices_to_be_updated))

            # service mapper removing all device that need not to be updated
            self.service_mapper_spoke_list_adjustment(self.devices_to_be_updated, spoke_list, circuit_details)

        self.logger.info("spoke_list after adjustment: {}".format(spoke_list))

        for spoke in spoke_list:
            for device, values in spoke.items():
                self.logger.debug("device {},values {}".format(device, values))
                if values["Role"].upper() == "PE":
                    pe_list.append(values)
                elif values["Role"].upper() == "AGG":
                    agg_list.append(values)
                elif values["Role"].upper() == "CPE" or (
                    values["Role"].upper() == "MTU"
                    and (
                        str(values["Client Neighbor"].lower()) == "none"
                        or (
                            self.COMMON_TYPE_LOOKUP[values["Vendor"]].get("MTU_BW_INCLUSION")
                            and values["Model"]
                            in self.COMMON_TYPE_LOOKUP[values["Vendor"]]["MTU_BW_INCLUSION"]["MODEL"]
                        )
                    )
                ):
                    cpe_list.append(values)
                elif values["Role"].upper() == "MTU":
                    mtu_list.append(values)
                else:
                    msg = "Device %s has unsupported role %s " % (device, values["Role"])
                    self.categorized_error = (
                        self.ERROR_CATEGORY["MDSO"].format(msg) if self.ERROR_CATEGORY.get("MDSO") else ""
                    )
                    self.exit_error(msg)

        if self.operation != "SERVICE_MAPPER":
            for pe in pe_list:
                try:
                    self.update_pe_bw(circuit_details, pe)
                except Exception as ex:
                    self.logger.info(str(ex))
                    msg = "Error while trying to update bw on Pe device %s" % pe["Host Name"]
                    self.categorized_error = (
                        self.ERROR_CATEGORY["MDSO"].format(msg) if self.ERROR_CATEGORY.get("MDSO") else ""
                    )
                    self.exit_error(msg)

        self.logger.info("cpe_list contains: {}".format(cpe_list))

        for cpe in cpe_list:
            try:
                context = cpe["Role"]
                node_vendor = cpe["Vendor"]
                device_role = cpe["Role"]
                node_model = cpe["Model"]

                # check if we need to skip applying policer to particular device role
                self.logger.debug("Checking update BW skip policer:")
                self.logger.debug(
                    "context:{}|node_vendor:{}|device_role:{}|node_model:{}".format(
                        context, node_vendor, device_role, node_model
                    )
                )
                if self.is_skip_bw_policer(context, node_vendor, device_role, node_model):
                    self.logger.debug(
                        "skip update vendor {}, role {}, model {}".format(node_vendor, device_role, node_model)
                    )
                    continue
                self.update_cpe_bw(circuit_details, cpe)
            except Exception as ex:
                self.logger.info(str(ex))
                msg = "Error while trying to update bw on Cpe device %s" % cpe["Host Name"]
                self.categorized_error = (
                    self.ERROR_CATEGORY["MDSO"].format(msg) if self.ERROR_CATEGORY.get("MDSO") else ""
                )
                self.exit_error(msg)

    def update_pe_bw(self, circuit_details, pe):
        """
        Creates plugin resource for eline service
        Creates serviceprovisioner_FIA/ELAN resource for FIA/ELAN service
        """
        try:
            service_type = circuit_details["properties"]["serviceType"]
            self.logger.info("Updating Device %s for service type %s" % (pe["Host Name"], service_type))

            if service_type == "ELINE":
                # Creating mef legato segment for bandwidth update
                self.create_mef_segment_for_bw_update(circuit_details, pe)

            else:
                properties = {
                    "circuit_details_id": self.circuit_res_id,
                    "circuit_id": self.circuit_id,
                    "context": "PE",
                    "stage": "PRODUCTION",
                    "operation": self.UPDATE_OPERATION_STRING,
                    "update_property": "bandwidth",
                }
                try:
                    properties["bandwidthValue"] = self.properties["bandwidthValue"]
                except Exception:
                    pass
                pe_update_obj = {
                    "label": self.properties["circuit_id"] + "-" + service_type + "-Provisioner",
                    "productId": self.get_built_in_product(self.PE_SPECIFIC_RESOURCE_TYPES.get(service_type))["id"],
                    "properties": properties,
                }
                self.logger.info("pe bandwidth update object %s" % str(pe_update_obj))
                self.bpo.resources.create(self.resource_id, pe_update_obj)

        except Exception as err:
            msg = "Error- %s raised while updating pe- %s bandwidth update" % (str(err), pe["Host Name"])
            self.categorized_error = self.ERROR_CATEGORY["MDSO"].format(msg) if self.ERROR_CATEGORY.get("MDSO") else ""
            self.exit_error(msg)

    def update_cpe_bw(self, circuit_details, cpe):
        """
        Method to Update Bandwidth on CPE
        devices
        """
        try:
            self.create_mef_segment_for_bw_update(circuit_details, cpe)

        except Exception as err:
            msg = "Error- %s raised while updating cpe- %s bandwidth update" % (str(err), cpe["Host Name"])
            self.categorized_error = self.ERROR_CATEGORY["MDSO"].format(msg) if self.ERROR_CATEGORY.get("MDSO") else ""
            self.exit_error(msg)

    def create_mef_segment_for_bw_update(self, circuit_details, device_info):
        """
        Creates mef segment resource for bandwidth update
        :param circuit_details: circuit details resource
        :param device_info: device info of pe/cpe devices from the spoke list
        :return: None
        """
        self.logger.info("Updating %s Device %s" % (device_info["Role"], device_info["Host Name"]))

        # Fetching device params required for PE/CPE update
        nf = self.get_network_function_by_host(device_info["FQDN"])

        if nf is None and not device_info["Management IP"].upper() == "DHCP":
            nf = self.get_network_function_by_host(device_info["Management IP"])

        if nf is None:
            msg = "Unable to find Network Function with FQDN %s or IP %s: " % (
                str(device_info["FQDN"]),
                str(device_info["Management IP"]),
            )
            self.categorized_error = self.ERROR_CATEGORY["MDSO"].format(msg) if self.ERROR_CATEGORY.get("MDSO") else ""
            self.exit_error(msg)

        # Get MEF Plugin Product
        package = nf["resourceTypeId"].split(".")[0]
        product_id = self.get_mef_plugin_product(package)
        self.logger.info("product_id for package: %s is %s" % (package, product_id))
        segment_properties = self.get_bw_update_properties(circuit_details, device_info, nf)
        self.logger.info(
            "segment properties for update operation of %s device is %s"
            % (device_info["Host Name"], str(segment_properties))
        )

        # Creating MEF Segment to update bandwidth on PE/CPE DEVICE
        self.create_and_delete_segment_resource(self.resource["id"], product_id, segment_properties, self.circuit_id)

    def get_bw_update_properties(self, circuit_details, device_info, nf):
        """
        Forms the bandwidth update properties for mef segment creation
        :param circuit_details: circuit details resource
        :param device_info: device info of pe/cpe devices from the spoke list
        :return: None
        """
        # Fetching device params required for device update
        client_interface = device_info["Client Interface"]
        client_port_res = self.get_port_id_from_port_name_and_device_id_retry(
            client_interface, nf["id"], device_info["Role"], 12
        )
        if client_port_res is None and device_info["Role"] == "CPE":
            client_interface = client_interface.replace("ETH-PORT", "ETH_PORT")
            client_port_res = self.get_port_id_from_port_name_and_device_id_retry(client_interface, nf["id"], "CPE")

        if client_port_res is None:
            msg = "Unable to find port %s on node %s" % (client_interface, device_info["Host Name"])
            self.categorized_error = self.ERROR_CATEGORY["MDSO"].format(msg) if self.ERROR_CATEGORY.get("MDSO") else ""
            self.exit_error(msg)

        port_uuid = device_info["Host Name"] + "-" + client_interface

        port_role = self.get_port_role(circuit_details, port_uuid)

        # Fetching service level properties for BW update
        evc = circuit_details["properties"]["service"][0]["data"]["evc"][0]
        svlan = "0" if evc["sVlan"] in ["untagged", "Untagged"] else evc["sVlan"]
        client_port_name = str(self.bpo.resources.get(client_port_res)["properties"]["data"]["id"])
        cvlan = self.get_cvlans_for_uni_ep(circuit_details, device_info["Host Name"] + "-" + client_port_name)
        try:
            egress_bw = self.properties["bandwidthValue"]
            ingress_bw = self.properties["bandwidthValue"]
        except Exception:
            egress_bw = evc.get("evc-egress-bwp")
            ingress_bw = evc.get("evc-ingress-bwp")

        service_type = circuit_details["properties"]["serviceType"]

        # Generate MEF Segment Properties
        segment_properties = {
            "operation": "UPDATE",
            "update_properties": [{"bandwidth": True}],
            "segment_info": {
                "type": service_type,
                "ingress_bandwidth": ingress_bw,
                "egress_bandwidth": egress_bw,
                "name": self.circuit_id,
                "endpoints": [
                    {
                        "node_id": nf["id"],
                        "port_id": client_port_res,
                        "svlan": int(svlan),
                        "cvlan": cvlan,
                        "port_role": port_role,
                    }
                ],
            },
        }

        if device_info["Role"] == "CPE" or (
            device_info["Role"].upper() == "MTU"
            and (
                str(device_info["Client Neighbor"].lower()) == "none"
                or (
                    self.COMMON_TYPE_LOOKUP[device_info["Vendor"]].get("MTU_BW_INCLUSION")
                    and device_info["Model"]
                    in self.COMMON_TYPE_LOOKUP[device_info["Vendor"]]["MTU_BW_INCLUSION"]["MODEL"]
                )
            )
        ):
            network_interface = device_info["Network Interface"]
            network_port_res = self.get_port_id_from_port_name_and_device_id_retry(
                network_interface, nf["id"], device_info["Role"]
            )
            cosname = self.COS_LOOKUP["CPE"][evc["cosNames"][0]["name"]]

            segment_properties["segment_info"]["endpoints"][0].update({"cosIdentifier": cosname})
            segment_properties["segment_info"]["endpoints"].append(
                {"node_id": nf["id"], "port_id": network_port_res, "svlan": int(svlan)}
            )

        return segment_properties

    def get_bw_in_kbps(self, bw):
        """
        return bw in kbps
        """
        return str(
            int(re.findall(r"\d+", bw)[0]) * (1000000 if "g" in bw.lower() else 1000 if "m" in bw.lower() else 1)
        )

    def get_bandwidth_formatted(self, bw):
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

        return str(rate) + str(unit)

    def service_mapper_spoke_list_adjustment(self, devices_to_be_updated, spoke_list, circuit_details):
        """alters the spoke_list when operation == "SERVICE_MAPPER.

        Reason:
        by default bandwidth update provisions all cpe's but for the use of service mapper
        only one cpe may be necessary so this method adjusts spoke_list as needed.

        Keyword arguments:
        devices_to_be_updated -- List of device tids that need update.

        spoke_list --

        circuit_details --

        """
        one_sided_services = (
            "FIA",
            "VOICE",
        )

        if circuit_details["properties"]["serviceType"] in one_sided_services:
            pass
        else:
            # self.spoke_list = spoke_list
            a_side = list(spoke_list[0].keys())
            z_side = list(spoke_list[1].keys())
            self.logger.info("a_side: {}".format(a_side))
            self.logger.info("z_side: {}".format(z_side))

            # empty list of device to be deleted from bandwidth update cpe_list
            cpe_to_be_excluded = []

            if len(self.devices_to_be_updated) == 1:
                for device in devices_to_be_updated:
                    if device in a_side:
                        del spoke_list[1]
                    else:
                        del spoke_list[0]
                # print(spoke_list)

                # for loop to determine what device to add to the cpe_to_be_excluded dynamic list
                for device in spoke_list[0].keys():
                    for tid in devices_to_be_updated:
                        if device != tid:
                            cpe_to_be_excluded.append(device)
                            self.logger.info("device to exclude: {}".format(device))

                # for loop to delete the key value contained in the cpe_to_be_excluded list from the spoke_list.
                # reason for doing this is that by default
                # this product will updated all cpe's regardless of it needing to be fixed.
                for device in cpe_to_be_excluded:
                    del spoke_list[0][device]
            else:
                pass
