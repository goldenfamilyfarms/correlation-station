""" -*- coding: utf-8 -*-

NetworkServiceUpdate Plans

Versions:
   0.1 Dec 03, 2018
       Initial check in of CircuitDataCollection plans

"""
import sys
sys.path.append('model-definitions')
from scripts.common_plan import CommonPlan


class Activate(CommonPlan):
    """this is the class that is called for the initial updation of the
    Network Service.  The only input it requires is the circuit_id
    associated with the service.
    """

    def process_with_cleanup(self):
        self.circuit_id = self.properties["circuit_id"]
        self.label = self.resource["label"]
        self.devices_to_update_list = ["PE", "CPE"]
        network_update_res_id = self.resource["id"]

        # validate the network service update request is correct
        self.validate_update_request()

        # reference circuit details collector resource for this network service update
        self.circuit_details_res_id = self.resource["properties"]["circuit_details_id"]

        # Associate the CD to this NSU Resource
        self.bpo.relationships.add_relationship(network_update_res_id, self.circuit_details_res_id)

        # resyncs to all devices onboarded and the RA supports poll free
        circuit_details_res = self.bpo.resources.get(self.circuit_details_res_id)
        self.resync_poll_free_network_functions(circuit_details_res)

        # create the service device validator resource to make sure all devices are present.
        self.create_service_device_validator_resource(self.circuit_details_res_id, self.circuit_id)

        # creating the Device Onboarders for both PE and CPE context
        self.create_service_device_onboarder_resource(self.circuit_details_res_id, self.circuit_id)

        # create bandwidth update resource if bw update is requested.
        if self.properties["bandwidth"] is True:
            # creating the Device Profile configurators for PE & CPE context.
            self.create_service_device_profile_configurator_resource(self.circuit_details_res_id, self.circuit_id)
            self.create_network_service_bandwidth_update_resource()

        if self.properties["description"] is True:
            self.create_network_service_description_update_resource()

        if self.properties["serviceStatedisable"] is True:
            self.create_network_service_state_toggle_resource("disable")

        if self.properties["serviceStateenable"] is True:
            self.create_network_service_state_toggle_resource("enable")

        if self.properties["ip"] is True:
            self.create_network_service_ip_update_resource()

        return {}

    def process(self):
        self.operation = self.properties.get("operation", "NETWORK_SERVICE_UPDATE")

        result = {}
        try:
            result = self.process_with_cleanup()
        except RuntimeError:
            self.create_cleanup_resource()  # cleanup the unneeded info objects
            raise
        self.create_cleanup_resource()  # cleanup the unneeded info objects
        return result

    def validate_update_request(self):
        """
        Function to validate a network service update
        request
        """

        ctr = 0
        true_items = []
        for k, v in self.properties.items():
            # do not count use_alternate_circuit_details_server as it is not a property of circuit being updated
            if k == "use_alternate_circuit_details_server":
                continue
            if v is True:
                ctr += 1
                true_items.append(k)

        if ctr != 1:
            msg = "Expected only one property to be true but found %s which are %s " % (ctr, str(true_items))
            self.categorized_error = (
                self.ERROR_CATEGORY["MDSO"].format(msg) if self.ERROR_CATEGORY.get("MDSO") else ""
            )
            self.exit_error(msg)

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
                "network_service_resource_id": self.params["resourceId"],
                "circuit_id": circuit_id,
                "resource_name": "circuit_details_collector",
                "use_alternate_circuit_details_server": self.properties.get(
                    "use_alternate_circuit_details_server", False
                ),
                # "use_alternate_circuit_details_server": True,
                "operation": "NETWORK_SERVICE_UPDATE",
            },
        }

        cdc_res_id = self.bpo.resources.create(self.params["resourceId"], cdc_resource)
        return cdc_res_id.resource_id

    def create_network_service_bandwidth_update_resource(self):
        """
        Function to create network service bandwidth
        update resource.
        """

        bw_update_product = self.get_built_in_product(self.BUILT_IN_BW_UPDATE_TYPE)["id"]
        bw_update_res = {
            "label": self.label + "BW_UPDATE",
            "productId": bw_update_product,
            "properties": {
                "resource_name": "network_service_bandwidth_update",
                "circuit_id": self.circuit_id,
                "circuit_details_resource_id": self.circuit_details_res_id,
            },
        }

        try:
            if self.properties["bandwidthValue"]:
                bw_update_res["properties"]["bandwidthValue"] = self.properties["bandwidthValue"]
        except Exception:
            self.logger.exception(
                "Failed to assign bandwidthValue in create_network_service_bandwidth_update_resource"
            )

        self.bpo.resources.create(self.params["resourceId"], bw_update_res)

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
                "resource_name": "service_device_validator",
                "circuit_details_id": circuit_details_resource_id,
                "circuit_id": circuit_id,
                "operation": "NETWORK_SERVICE_UPDATE",
            },
        }

        self.bpo.resources.create(self.params["resourceId"], service_device_validator_res)

    def create_service_device_onboarder_resource(self, circuit_details_resource_id, circuit_id):
        """
        Function to create network service bandwidth
        update resource.
        """

        for context in self.devices_to_update_list:
            service_device_onboarder_product = self.get_built_in_product(self.BUILT_IN_SERVICE_DEVICE_ONBOARDER_TYPE)[
                "id"
            ]
            service_device_onboarder_res = {
                "label": self.label + "service_device_onboarder",
                "productId": service_device_onboarder_product,
                "properties": {
                    "resource_name": "service_device_onboarder",
                    "circuit_details_id": circuit_details_resource_id,
                    "circuit_id": circuit_id,
                    "context": context,
                    "operation": "NETWORK_SERVICE_UPDATE",
                },
            }
            self.bpo.resources.create(self.params["resourceId"], service_device_onboarder_res)

    def create_service_device_profile_configurator_resource(self, circuit_details_resource_id, circuit_id):
        """
        Function to create network service bandwidth
        update resource.
        """
        operation = "NETWORK_SERVICE_UPDATE"
        for context in self.devices_to_update_list:
            service_device_profile_bw_product = self.get_built_in_product(
                self.BUILT_IN_SERVICE_DEVICE_PROFILE_CONFIGURATOR
            )["id"]
            service_device_profile_bw_res = {
                "label": self.label + "service_device_profile_bw",
                "productId": service_device_profile_bw_product,
                "properties": {
                    "resource_name": "service_device_profile_configurator",
                    "circuit_details_id": circuit_details_resource_id,
                    "circuit_id": circuit_id,
                    "context": context,
                    "operation": operation,
                },
            }
            self.bpo.resources.create(self.params["resourceId"], service_device_profile_bw_res)

    def create_network_service_description_update_resource(self):
        """
        Function to create network service description
        update resource.
        """

        descr_update_product = self.get_built_in_product(self.BUILT_IN_DESCRIPTION_UPDATE_TYPE)["id"]
        descr_update_res = {
            "label": self.label + "-" + "DESCRIPTION_UPDATE",
            "productId": descr_update_product,
            "properties": {"circuit_id": self.circuit_id, "circuit_details_resource_id": self.circuit_details_res_id},
        }

        self.logger.info(f"descr_update_res: {descr_update_res}")
        self.bpo.resources.create(self.params["resourceId"], descr_update_res)

    def create_network_service_state_toggle_resource(self, state):
        """
        Function to create network service bandwidth
        update resource.
        """

        state_toggle_product = self.get_built_in_product(self.BUILT_IN_NETWORK_SERVICE_STATE_TOGGLE_TYPE)["id"]
        state_toggle_res = {
            "resource_name": "network_service_state_toggle",
            "label": self.label + "-" + "STATE_TOGGLE",
            "productId": state_toggle_product,
            "properties": {
                "circuit_id": self.circuit_id,
                "circuit_details_resource_id": self.circuit_details_res_id,
                "required_state": state,
            },
        }
        self.bpo.resources.create(self.params["resourceId"], state_toggle_res)

    def create_network_service_ip_update_resource(self):
        """
        Function to create Network Service IP
        Update Resource
        """

        ip_update_product = self.get_built_in_product(self.BUILT_IN_IP_UPDATE_TYPE)["id"]
        ip_update_res = {
            "resource_name": "network_service_ip_update",
            "label": self.label + "-" + "IP_UPDATE",
            "productId": ip_update_product,
            "properties": {"circuit_id": self.circuit_id, "circuit_details_resource_id": self.circuit_details_res_id},
        }
        self.bpo.resources.create(self.params["resourceId"], ip_update_res)

    def create_cleanup_resource(self):
        cleanup_productId = self.get_built_in_product(self.BUILT_IN_NETWORK_SERVICE_CLEANER_TYPE)["id"]
        cleanup_resource = {
            "resource_name": "cleanup_resource",
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
