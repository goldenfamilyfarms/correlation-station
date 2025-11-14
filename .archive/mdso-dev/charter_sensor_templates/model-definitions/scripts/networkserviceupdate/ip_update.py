""" -*- coding: utf-8 -*-

IPUpdate Plans

Versions:
   0.1 Dec 03, 2018
       Initial check in of CircuitDataCollection plans

"""

import time
import sys

sys.path.append("model-definitions")
from scripts.common_plan import CommonPlan


class Activate(CommonPlan):
    """this is the class that is called for the initial updation of the
    Network Service IP. The only input it requires is the circuit_id
    associated with the service.
    """

    def process(self):
        self.circuit_id = self.properties["circuit_id"]
        self.circuit_res_id = self.properties["circuit_details_resource_id"]
        # self.changes = self.get_circuit_changes(self.circuit_id)
        circuit_details = self.get_resource(self.circuit_res_id)
        evc = circuit_details["properties"]["service"][0]["data"]["evc"][0]
        svlan = "0" if evc["sVlan"] in ["untagged", "Untagged"] else evc["sVlan"]
        service_type = circuit_details["properties"]["serviceType"]

        if not service_type == "FIA":
            return {}
        else:
            try:
                pe_list = []
                spoke_list = self.create_device_dict_from_circuit_details(circuit_details)

                for spoke in spoke_list:
                    for _, values in spoke.items():
                        if values["Role"].upper() == "PE":
                            pe_list.append(values)

                for pe in pe_list:
                    pe_device = self.get_network_function_for_spoke_device(pe)
                    interface_name = pe["Client Interface"]
                    device_pid = pe_device["productId"]
                    device_prid = pe_device["providerResourceId"]
                    self.domain_id = self.bpo.market.get(f"/products/{device_pid}")["domainId"]
                    fia_obj_properties = self.get_fia_service_object_from_details(pe, circuit_details)["properties"]

                    ipv4_res = self.bpo.resources.get_by_provider_resource_id(
                        self.domain_id, f"{device_prid}::RIB::GlobalRouter"
                    )
                    ipv6_res = self.bpo.resources.get_by_provider_resource_id(
                        self.domain_id, f"{device_prid}::RIB::inet6.0"
                    )

                    # Don't need to create any FIA FRE for FIA DIRECT
                    if fia_obj_properties["fia_type"] == "DIRECT":
                        if "lanIpv6Addresses" in fia_obj_properties.keys():
                            if ipv6_res is None:
                                self.create_fia_static_fre(fia_obj_properties, "ipv6")
                            else:
                                self.update_fia_static_fre(ipv6_res, fia_obj_properties, "ipv6")

                        if "lanIpv4Addresses" in fia_obj_properties.keys():
                            int_details = self.execute_ra_command_file(
                                device_prid,
                                "get-logical-tpe.json",
                                parameters={"interface": interface_name.lower(), "unit": svlan},
                                headers=None,
                            )
                            ips_on_interface = int_details.json()["result"]["ipv4Addresses"]
                            required_ips = []

                            for ip in fia_obj_properties["lanIpv4Addresses"]:
                                if ip not in ips_on_interface:
                                    required_ips.append(ip)

                            if not required_ips == []:
                                try:
                                    self.execute_ra_command_file(
                                        device_prid,
                                        "update-logical-tpe.json",
                                        parameters={
                                            "interface": interface_name.lower(),
                                            "unit": svlan,
                                            "ipv4Addresses": required_ips,
                                            "commit": True,
                                        },
                                        headers=None,
                                    )
                                except Exception as ex:
                                    self.logger.info(f"Unable to add Ipv4 addresses on interface {required_ips}")
                                    self.logger.info(str(ex))
                                    msg = self.error_formatter(
                                        self.SYSTEM_ERROR_TYPE,
                                        self.RESOURCE_GET_SUBCATEGORY,
                                        str(ex),
                                    )
                                    self.categorized_error = msg
                                    self.exit_error(msg)

                    # Find if routing FREs already exist and update them, create if they do not exist
                    if fia_obj_properties["fia_type"] == "STATIC":
                        if "lanIpv4Addresses" in fia_obj_properties.keys():
                            if ipv4_res is None:
                                self.create_fia_static_fre(fia_obj_properties, "ipv4")
                            else:
                                fre_res = self.refresh_resource_differences(ipv4_res, device_prid, "ipv4")
                                self.update_fia_static_fre(fre_res, fia_obj_properties, "ipv4")

                        if "lanIpv6Addresses" in fia_obj_properties.keys():
                            if ipv6_res is None:
                                self.create_fia_static_fre(fia_obj_properties, "ipv6")
                            else:
                                fre_res = self.refresh_resource_differences(ipv6_res, device_prid, "ipv6")
                                self.update_fia_static_fre(fre_res, fia_obj_properties, "ipv6")

            except Exception as e:
                msg = self.error_formatter(
                    self.SYSTEM_ERROR_TYPE,
                    self.RESOURCE_GET_SUBCATEGORY,
                    str(e),
                )
                self.categorized_error = msg
                self.exit_error()

    def refresh_resource_differences(self, fre_res, device_prid, route_type):
        self.logger.info("refresh_resource_differences")

        # refresh and merge differences if exists before acting on data
        is_discovered = True

        if fre_res["discovered"] is False:
            is_discovered = False
            self.bpo.resources.patch(fre_res["id"], {"discovered": True})
            self.logger.info(is_discovered)

        self.ip_update_resource_resync(fre_res["id"])

        if not is_discovered:
            self.bpo.resources.patch(fre_res["id"], {"discovered": False})
            self.logger.info(is_discovered)

        if route_type == "ipv4":
            fre_res = self.bpo.resources.get_by_provider_resource_id(
                self.domain_id, f"{device_prid}::RIB::GlobalRouter"
            )
        else:
            fre_res = self.bpo.resources.get_by_provider_resource_id(self.domain_id, f"{device_prid}::RIB::inet6.0")

        return fre_res

    def ip_update_resource_resync(self, res_id):
        """
        resync resource, updating marketplace
        """
        rstatus = self.bpo.market.post(f"/resources/{res_id}/resync")
        self.logger.debug(f"resource resync status:{rstatus}")

        # wait till settle
        time.sleep(5)

    def get_product_id_by_type_domain(self, resource_type, domain_id):
        """
        returns the product id based on resource type and
        domain (this needs to be moved to common.py)
        """
        product_list = self.bpo.market.get_products_by_resource_type(resource_type)

        if len(product_list) == 0:
            msg = self.error_formatter(
                self.INCORRECT_DATA_ERROR_TYPE,
                self.TOPOLOGIES_DATA_SUBCATEGORY,
                f"Unable to Find any products for type {resource_type}, make sure the products are on-boarded",
                system=self.CIRCUIT_DETAILS_DATABASE,
            )
            self.categorized_error = msg
            raise Exception(msg)

        for product in product_list:
            if product["domainId"] == domain_id:
                required_pid = product["id"]

        if not required_pid:
            msg = self.error_formatter(
                self.MISSING_DATA_ERROR_TYPE,
                self.TOPOLOGIES_DATA_SUBCATEGORY,
                f"unable to find product for {resource_type} in domain {domain_id}",
                system=self.CIRCUIT_DETAILS_DATABASE,
            )
            self.categorized_error = msg
            raise Exception(msg)

        return required_pid

    def create_fia_static_fre(self, properties, route_type):
        """
        creates the FRE object for FIA-STATIC
        """
        fre_pid = self.get_product_id_by_type_domain("tosca.resourceTypes.FRE", self.domain_id)
        fre_properties = self.create_fre_properties(properties, route_type)
        fre_label = "RIB::" + ("GlobalRouter" if route_type == "ipv4" else "inet6.0")
        fre_object = {
            "label": fre_label,
            "resourceTypeId": "tosca.resourceTypes.FRE",
            "productId": fre_pid,
            "properties": fre_properties,
        }

        self.bpo.resources.create(self.params["resourceId"], fre_object)

    def create_fre_properties(self, properties, route_type):
        """
        generate FRE object for FIA service
        """
        fre_properties = {
            "device": self.bpo.resources.get(properties["pe_device_rid"])["providerResourceId"],
            "data": {
                "id": "RIB::" + ("GlobalRouter" if route_type == "ipv4" else "inet6.0"),
                "type": "fres",
                "attributes": {
                    "serviceClass": "IP",
                    "networkRole": "IFRE",
                    "adminState": "enabled",
                    "active": True,
                    "routingInstance": {
                        "name": "GlobalRouter" if route_type == "ipv4" else "inet6.0",
                        "ribList": [
                            {
                                "name": "GlobalRouter" if route_type == "ipv4" else "inet6.0",
                                "addressFamily": route_type,
                                "routeList": [],
                            }
                        ],
                    },
                },
            },
        }

        looper = properties["lanIpv4Addresses"] if route_type == "ipv4" else properties["lanIpv6Addresses"]

        for ip in looper:
            route_list_element = {
                "match": {
                    "routeType": {
                        route_type: {"destIpv4Address" if route_type == "ipv4" else "destIpv6Address": ip.lower()}
                    }
                },
                "nexthop": {
                    "nexthopType": {
                        "nexthopBase": {
                            "ipv4AddressNexthop" if route_type == "ipv4" else "ipv6AddressNexthop": (
                                properties["nextIpv4Hop"] if route_type == "ipv4" else properties["nextIpv6Hop"].lower()
                            )
                        }
                    }
                },
            }
            fre_properties["data"]["attributes"]["routingInstance"]["ribList"][0]["routeList"].append(
                route_list_element
            )

        return fre_properties

    def is_update_fia_static_fre_success(self, route_type, fre_resid, ipaddresses):
        success = True
        new_fre_res = self.bpo.resources.get(fre_resid)
        route_list = new_fre_res["properties"]["data"]["attributes"]["routingInstance"]["ribList"][0]["routeList"]
        match = 0

        for ip in ipaddresses:
            for route in route_list:
                existing_dest_ip = (
                    route["match"]["routeType"]["ipv4"]["destIpv4Address"]
                    if route_type == "ipv4"
                    else route["match"]["routeType"]["ipv6"]["destIpv6Address"]
                )

                if ip.lower() == existing_dest_ip.lower():
                    match += 1

        if match != len(ipaddresses):
            success = False

        return success

    def update_fia_static_fre(self, fre_res, properties, route_type):
        """
        generate FRE object for FIA service
        """
        self.logger.info("----update_fia_static_fre start----")

        try:
            is_discovered = False
            is_update = False
            ipaddresses = properties["lanIpv4Addresses"] if route_type == "ipv4" else properties["lanIpv6Addresses"]
            route_list = fre_res["properties"]["data"]["attributes"]["routingInstance"]["ribList"][0]["routeList"]

            # cases:
            if ipaddresses:
                # 1. adding IP addresses that is not already avail on the device
                # 2. replace also not implemented unless we decided that it's what we want
                new_ipaddresses = ipaddresses[:]

                for ip in ipaddresses:
                    for route in route_list:
                        existing_dest_ip = (
                            route["match"]["routeType"]["ipv4"]["destIpv4Address"]
                            if route_type == "ipv4"
                            else route["match"]["routeType"]["ipv6"]["destIpv6Address"]
                        )

                        if ip.lower() == existing_dest_ip.lower():
                            new_ipaddresses.remove(ip)

                for ip in new_ipaddresses:
                    route_list_object = {
                        "match": {
                            "routeType": {
                                route_type: {
                                    "destIpv4Address" if route_type == "ipv4" else "destIpv6Address": ip.lower()
                                }
                            }
                        },
                        "nexthop": {
                            "nexthopType": {
                                "nexthopBase": {
                                    "ipv4AddressNexthop" if route_type == "ipv4" else "ipv6AddressNexthop": (
                                        properties["nextIpv4Hop"]
                                        if route_type == "ipv4"
                                        else properties["nextIpv6Hop"].lower()
                                    )
                                }
                            }
                        },
                    }

                    fre_res["properties"]["data"]["attributes"]["routingInstance"]["ribList"][0]["routeList"].append(
                        route_list_object
                    )
                    is_update = True
            else:
                # 2. empty list,
                # the behavior is noop right now, unless we decided to delete the route, which might not
                # be the behavior that we want.
                is_update = False

            if is_update:
                self.logger.info(f"changed, update on {route_type} id {fre_res['id']}")
                patch = {"properties": fre_res["properties"]}

                if fre_res["discovered"] is True:
                    is_discovered = True
                    self.bpo.resources.patch(fre_res["id"], {"discovered": False})

                self.bpo.resources.patch(fre_res["id"], patch)

                if is_discovered is True:
                    self.bpo.resources.patch(fre_res["id"], {"discovered": True})

                # resyncing before checking the data
                self.ip_update_resource_resync(fre_res["id"])

                if not self.is_update_fia_static_fre_success(route_type, fre_res["id"], ipaddresses):
                    msg = self.error_formatter(
                        self.MISSING_DATA_ERROR_TYPE,
                        self.TOPOLOGIES_DATA_SUBCATEGORY,
                        f"update failed on fia static fre type {route_type} id {fre_res['id']}",
                        system=self.CIRCUIT_DETAILS_DATABASE,
                    )
                    self.categorized_error = msg
                    raise Exception(msg)
            else:
                self.logger.info(f"nothing changed, no update on {route_type} id {fre_res['id']}")
        except Exception as err:
            self.logger.info(f"Error is {err}")

            if is_discovered is True:
                self.bpo.resources.patch(fre_res["id"], {"discovered": True})

        self.logger.info("----update_fia_static_fre end----")
