"""-*- coding: utf-8 -*-

smokeTest.py
Versions:
    7/29/2025

"""


from scripts.circuitDetailsHandler import CircuitDetailsHandler
from ra_plugins.ra_cutthrough import RaCutThrough
from scripts.configmodeler.utils import NetworkCheckUtils
from scripts.serviceMapper.common import Common, Device
from scripts.common_plan import CommonPlan


class Activate(CommonPlan):

    def process(self):
        self.initialize()
        topology_devices = [node for node in self.circuit_details["properties"]["topology"][0]["data"]["node"]]
        if self.service_type == "ELINE":
            topology_devices.extend(node for node in self.circuit_details["properties"]["topology"][1]["data"]["node"])
        for device_data in topology_devices:
            device = Device(device_data)
            self.reset_device(device)
        self.test_standalone_config_delivery()
        self.test_network_service()
        self.test_network_service_update()
        self.test_service_mapper()
        self.test_port_activation()
        self.test_turnup_locate_ip()

    def initialize(self):
        self.utils = NetworkCheckUtils()
        self.resource_id = self.resource["id"]
        self.circuit_id = "71.L1XX.011899..CHTR"
        self.cutthrough = RaCutThrough()
        self.set_circuit_details()
        self.service_type = self.circuit_details["properties"]["serviceType"]
        self.bw = self.circuit_details["properties"]["service"][0]["data"]["evc"][0].get("evc-ingress-bwp", None)
        self.svlan = self.circuit_details["properties"]["service"][0]["data"]["evc"][0].get("sVlan", "")
        self.lan_ipv6 = self.circuit_details["properties"]["service"][0]["data"]["fia"][0]["endPoints"][0].get("lanIpv6Addresses", "")
        self.logger.info(f"self.lan_ipv6: {self.lan_ipv6}")
        self.logger.info(f"self.bw: {self.bw}")
        self.circuit_details_id = self.circuit_details["id"]
        self.delete_existing_product_resources_and_dependencies(
            self.BUILT_IN_NETWORK_SERVICE_TYPE, self.circuit_id, self.resource_id
        )
        self.service_type = self.circuit_details["properties"]["serviceType"].upper()

    def set_circuit_details(self):
        # Generate initial circuit details
        circuit_details_handler = self.create_circuit_details_handler(self.circuit_id, operation="SMOKE_TEST")
        # handle onboarding
        circuit_details_handler.device_onboarding_process()
        # set initial circuit details id
        self.circuit_details_id = circuit_details_handler.circuit_details_id
        # grab updated circuit details
        self.circuit_details = circuit_details_handler.circuit_details

    def create_circuit_details_handler(self, cid, operation: str = "OperationNotSet"):
        return CircuitDetailsHandler(plan=self, circuit_id=cid, operation=operation)

    def loggers_test(self, device: Device):
        self.logger.info(f"device.fqdn: {device.fqdn}")
        self.logger.info(f"device.vendor: {device.vendor}")

    def reset_device(self, device: Device):
        if device.vendor == "JUNIPER":
            self.reset_juniper(device)
        if device.vendor == "ADVA":
            self.reset_adva(device)
        if device.vendor == "RAD":
            self.reset_rad(device)

    def reset_juniper(self, device: Device):
        parameters = {}
        if device.vendor == "JUNIPER" and device.role == "PE":
            parameters["port"] = device.handoff_port.lower()
            parameters["unit"] = self.svlan
            parameters["lan_ipv6"] = self.lan_ipv6[0] if self.lan_ipv6 else ""
        if device.vendor == "JUNIPER" and device.role == "AGG":
            parameters["port"] = device.handoff_port.lower()
            parameters["service_type"] = self.service_type
            parameters["vlan"] = self.svlan
        command = "regression-delete-service"
        self.ra_cutthrough_command(device, parameters, command)

    def reset_adva(self, device: Device):
        parameters = {}
        if device.vendor == "ADVA" and device.role == "MTU":
            return
        if device.vendor == "ADVA" and device.role == "CPE":
            parameters["port"] = device.handoff_port[-1]
        command = "regression-delete-service"
        self.ra_cutthrough_command(device, parameters, command)

    def reset_rad(self, device: Device):
        parameters = {}
        command = ""
        if device.vendor == "RAD" and device.role == "MTU":
            parameters["cid"] = self.circuit_id
            command = "smoketest-delete-service"
        elif device.vendor == "RAD" and device.role == "CPE":
            parameters["port"] = device.handoff_port[-1]
            parameters["cid"] = self.circuit_id
            parameters["bw"] = self.bw
            command = "regression-delete-service"
        if command:
            self.ra_cutthrough_command(device, parameters, command)

    def ra_cutthrough_command(self, device: Device, parameters, command):
        keyname = "devices_reset_status"
        nf_resource = self.get_network_function_by_host_or_ip(device.fqdn, device.management_ip, require_active=True)
        if not nf_resource:
            self.patch_result_to_resource(keyname, {device.tid: "No provider resource id found"})
            return
        device_prid = nf_resource["providerResourceId"]
        self.logger.debug(f"Smoke Test Reset paramaters: {parameters}")
        if parameters:
            try:
                self.execute_ra_command_file(
                    device_prid,
                    f"{command}.json",
                    parameters,
                )
            except Exception as e:
                self.logger.info(f"Failed to reset device {device.tid} with error {e}")
                self.patch_result_to_resource(keyname, {device.tid: "Had issue while resetting device"})
                return
            self.patch_result_to_resource(keyname, {device.tid: "Reset Complete"})
        else:
            self.patch_result_to_resource(keyname, {device.tid: "Not started"})

    def test_network_service(self):
        product = "Provisioning"
        keyname = "product_test_status"
        product_id = self.get_products_by_type_and_domain(f"charter.resourceTypes.{product}", "built-in")[0]['id']
        self.logger.info("The CID I will send is: {}".format(self.circuit_id))
        props = {
            "circuit_id": self.circuit_id,
            "use_alternate_circuit_details_server": self.resource['properties']['use_alternate_circuit_details_server'],
            "operation_type": "CREATE"
        }
        net_serv_body = {
            "productId": product_id,
            "label": self.circuit_id,
            "properties": props}
        msg, _ = self.create_active_product_resource(product, net_serv_body)
        test = {"test1": msg}
        self.patch_result_to_resource(keyname, test)

    def test_network_service_update(self):
        product = "Provisioning"
        keyname = "product_test_status"
        product_id = self.get_products_by_type_and_domain(f"charter.resourceTypes.{product}", "built-in")[0]['id']
        self.logger.info("The CID I will send is: {}".format(self.circuit_id))
        props = {
            "circuit_id": self.circuit_id,
            "use_alternate_circuit_details_server": self.resource['properties']['use_alternate_circuit_details_server'],
            "operation_type": "UPDATE",
            "bandwidthValue": "50m",
            "bandwidth": True
        }
        net_serv_body = {
            "productId": product_id,
            "label": self.circuit_id,
            "properties": props}
        msg, _ = self.create_active_product_resource(product, net_serv_body)
        test = {"test2": msg}
        self.patch_result_to_resource(keyname, test)

    def test_service_mapper(self):
        product = "Compliance"
        keyname = "product_test_status"
        product_id = self.get_products_by_type_and_domain(f"charter.resourceTypes.{product}", "built-in")[0]['id']
        self.logger.info("The CID I will send is: {}".format(self.circuit_id))
        props = {
            "circuit_id": self.circuit_id,
            "use_alternate_circuit_details_server": self.resource['properties']['use_alternate_circuit_details_server'],
            "order_type": "NEW"
        }
        net_serv_body = {
            "productId": product_id,
            "label": self.circuit_id,
            "properties": props}
        msg, _ = self.create_active_product_resource(product, net_serv_body)
        test = {"test3": msg}
        self.patch_result_to_resource(keyname, test)

    def test_port_activation(self):
        product = "PortActivation"
        keyname = "product_test_status"
        self.delete_existing_product_resources_and_dependencies(f"charter.resourceTypes.{product}", "LNCSNYCD1QW_GE-0/0/61", self.resource_id)
        product_id = self.get_products_by_type_and_domain(f"charter.resourceTypes.{product}", "built-in")[0]['id']
        props = {
            "vendor": "JUNIPER",
            "portname": "ge-0/0/61",
            "deviceName": "LNCSNYCD1QW.CHTRSE.COM",
            "terminationTime": 5
        }
        net_serv_body = {
            "productId": product_id,
            "label": "LNCSNYCD1QW_GE-0/0/61",
            "properties": props}
        self.create_active_product_resource(product, net_serv_body)
        product_resource_id = self.get_product_resource_id(product)
        self.logger.info(f"product_resource_id: {product_resource_id}")
        response = self.bpo.resources.exec_operation(product_resource_id, "getPortStatus", {}, timeout=300.0, interval=5.0)
        self.logger.info(f"response1 value: {response}")
        msg = {"port_activation": response['outputs']}
        test = {"test4": msg}
        self.patch_result_to_resource(keyname, test)

    def test_turnup_locate_ip(self):
        product = "turnupLocateIP"
        keyname = "product_test_status"
        product_id = self.bpo.market.get_products_by_resource_type(f'charter.resourceTypes.{product}')[0]['id']
        self.logger.info(f"product_id value: {product_id}")

        props = {
            "pe_router_vendor": "JUNIPER",
            "pe_router_FQDN": "LNCSNYCD1CW.CHTRSE.COM",
            "upstream_device_vendor": "RAD",
            "upstream_device_FQDN": "LNCSNYCD2AW.CML.CHTRSE.COM",
            "upstream_port": "ETH PORT 0/6",
        }
        net_serv_body = {
            "productId": product_id,
            "label": "LNCSNYCD6ZW",
            "properties": props}
        msg, net_serv_response = self.create_active_product_resource(product, net_serv_body)
        self.logger.info(f"net_serv_response value: {net_serv_response}")
        self.logger.info(f"response value: {msg}")
        test = {"test5": msg}
        self.patch_result_to_resource(keyname, test)

    def test_standalone_config_delivery(self):
        product = "standaloneConfigDelivery"
        keyname = "product_test_status"
        product_id = self.bpo.market.get_products_by_resource_type(f'charter.resourceTypes.{product}')[0]['id']
        self.logger.info(f"product_id value: {product_id}")

        props = {
            "pe_router_vendor": "JUNIPER",
            "pe_router_FQDN": "LNCSNYCD1CW.CHTRSE.COM",
            "upstream_device_vendor": "RAD",
            "upstream_device_FQDN": "LNCSNYCD2AW.CML.CHTRSE.COM",
            "upstream_port": "ETH PORT 0/6",
            "target_vendor": "ADVA",
            "target_model": "114PRO",
            "target_device": "LNCSNYCD6ZW.CML.CHTRSE.COM",
            "cpe_config": [
                "home",
                "network-element ne-1",
                "configure nte nte114pro-1-1-1",
                "configure access-port access-1-1-1-6",
                "alias \"MDSO_SCOD_SUCCESS\"",
                "home",
                "configure user-security",
                "access-order remote",
                "home",
                "admin database",
                "backup-db",
                ""
            ]
        }
        net_serv_body = {
            "productId": product_id,
            "label": "LNCSNYCD2AW_LNCSNYCD6ZW",
            "properties": props}
        msg, net_serv_response = self.create_active_product_resource(product, net_serv_body)
        self.logger.info(f"net_serv_response value: {net_serv_response}")
        self.logger.info(f"response value: {msg}")
        test = {"test6": msg}
        self.patch_result_to_resource(keyname, test)

    def create_active_product_resource(self, product, net_serv_body):
        product_label = self.product_label()[product]
        try:
            net_serv_response = self.bpo.resources.create(parent_resource_id=self.resource_id, data=net_serv_body, wait_time=300)
            self.logger.info(f"=&=$=%=&=$=%=&=$=% {product_label}_RESPONSE %=$=&=%=$=&=%=$=&=%=$=&=")
            self.logger.info(f'response: {net_serv_response}')
            msg = {f'{product_label}': "Completed"}
        except Exception as e:
            self.logger.info(f'{product_label} exception: {e}')
            net_serv_response = {}
            msg = {f"{product_label}": "Failure in the Smoke Test Process"}

        return msg, net_serv_response

    def product_label(self):
        return {
            "NetworkService": "network_service",
            "NetworkServiceUpdate": "network_service_update",
            "ServiceMapper": "service_mapper",
            "PortActivation": "port_activation",
            "standaloneConfigDelivery": "standalone_config_delivery",
            "turnupLocateIP": "turnup_locate_ip",
            "Provisioning": "provisioning",
            "Compliance": "compliance"
        }

    def get_product_resource_id(self, product):
        dependencies = self.bpo.resources.get_dependencies(self.resource_id)
        self.logger.info(f'dependencies: {dependencies}')
        for item in dependencies:
            if item['resourceTypeId'] == f'charter.resourceTypes.{product}':
                return item['id']

    def patch_result_to_resource(self, keyname, msg: dict):
        properties = self.resource["properties"]
        if not properties.get("smoke_test_progress"):
            properties["smoke_test_progress"] = {}
        if not properties["smoke_test_progress"].get(keyname):
            properties["smoke_test_progress"][keyname] = {}
        try:
            self.bpo.resources.patch_observed(
                self.resource_id, data={"properties": {"smoke_test_progress": {keyname: msg}}}
            )
        except Exception as e:
            self.logger.error("Exception", e)

    def delete_existing_product_resources_and_dependencies(self, resource_type, label, resource_id):
        """Looks for existing product resources that match the label and deletes all including
        dependencies while leaving the current product resource and dependencies untouched

        :param resource_type: Example: self.BUILT_IN_DISCONNECT_MAPPER_TYPE
        :type resource_type: str
        :param label: The label of the resource item
        :type label: str
        :param resource_id: The id of the current resource
        :type resource_id: str
        """
        product_resources = self.get_resources_by_type_and_label(resource_type, label, no_fail=True)
        self.logger.info(f"mickey product_resources {product_resources}")
        if product_resources:
            for product_resource in product_resources:
                if product_resource["id"] != resource_id:
                    resource_dependents = self.get_dependencies(product_resource["id"])
                    for resource_dependent in resource_dependents:
                        self.logger.info(f"existing resource_dependent id found: {resource_dependent['id']}")
                        self.bpo.resources.patch(
                            resource_dependent["id"],
                            {"desiredOrchState": "terminated", "orchState": "terminated"},
                        )
                    self.logger.info(f"existing product_resource_id found : {product_resource['id']}")
                    self.bpo.resources.patch(
                        product_resource["id"],
                        {"desiredOrchState": "terminated", "orchState": "terminated"},
                    )


class Terminate(Common):
    def process(self):
        resource_dependents = self.get_dependencies(self.resource["id"])
        for resource_dependent in resource_dependents:
            self.logger.info("existing resource_dependent id found: {}".format(resource_dependent["id"]))
            self.bpo.resources.patch(
                resource_dependent["id"],
                {"desiredOrchState": "terminated", "orchState": "terminated"},
            )
