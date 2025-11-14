"""-*- coding: utf-8 -*-

NetworkServiceCheck Plans

Versions:
   0.1 Jan 8, 2017
       Initial check in of NetworkServiceCheck plans

"""

import sys

sys.path.append("model-definitions")
from scripts.complete_and_terminate_plan import CompleteAndTerminatePlan
from scripts.networkservice.update_site_state import UpdateSiteState


class Activate(CompleteAndTerminatePlan):
    """this is the class that is called for the initial activation of the
    NetworkServiceCheck.  The only input it requires is the circuit_id associated
    with the service.
    """

    def process(self):
        circuit_id = self.properties["circuit_id"]
        stage = self.properties["provisioning_stage"]
        network_service_res_id = self.properties["resource_id"]

        if len(circuit_id.strip()) < 5:
            msg = self.error_formatter(
                self.INCORRECT_DATA_ERROR_TYPE,
                self.TOPOLOGIES_DATA_SUBCATEGORY,
                f"Invalid circuit id provided {circuit_id}",
            )
            self.categorized_error = msg
            raise Exception(msg)

        network_service_res = self.get_resource(network_service_res_id)
        network_services = self.get_associated_network_service_for_circuit_id(circuit_id, include_all=True)

        if network_services is None:
            msg = self.error_formatter(
                self.MISSING_DATA_ERROR_TYPE,
                self.TOPOLOGIES_DATA_SUBCATEGORY,
                f"Unable to get Network Service for {circuit_id}",
            )
            self.categorized_error = msg
            raise Exception(msg)
        elif stage == "PRE":
            self.logger.info("Performing pre-processing for network service.")
            # PROCESS FOR PRE_CHECK

            # CHECK IF NETWORK SERVICE ALREADY EXISTS FOR THIS CIRCUIT
            for resource in network_services:
                if resource["orchState"] == "active" and resource["desiredOrchState"] == "active":
                    msg = self.error_formatter(
                        self.INCORRECT_DATA_ERROR_TYPE,
                        self.TOPOLOGIES_DATA_SUBCATEGORY,
                        f"Network Service already provisioned for circuit id: {circuit_id}, id: {resource['id']}",
                    )
                    self.categorized_error = msg
                    raise Exception(msg)

            circuit_details_id = self.properties["circuit_details_id"]
            circuit_details = self.get_resource(circuit_details_id)

            if circuit_details is None:
                msg = self.error_formatter(
                    self.MISSING_DATA_ERROR_TYPE,
                    self.TOPOLOGIES_DATA_SUBCATEGORY,
                    f"No circuit details found for id: {circuit_id}",
                )
                self.categorized_error = msg
                raise Exception(msg)

            # Associate the CD to this NS Resource
            self.bpo.relationships.add_relationship(network_service_res_id, circuit_details_id)
            # TODO: Making a mess
            # Need to run the site_status now that NS is a thing
            self.patch_cpe_with_initial_state(circuit_details, network_service_res)

            # resyncs to all devices onboarded and the RA supports poll free
            self.resync_poll_free_network_functions(circuit_details)

            # REGISTER NETWORK SERVICE RESOURCE ID WITH LOG FILTER
            try:
                self.post_bpprov_filter(network_service_res_id)
            except Exception as e:
                self.logger.warning(f"Error creating log filter, check bplogfilter is deployed. Error: {e}")

            service_resource_type = self.BUILT_IN_MEF_TEST_SERVICE_TYPE

            # checking for first element of network_services because its impossible to reach here if the length isn't 1
            if network_service_res is not None and network_service_res["properties"]["stage"] == "PRODUCTION":
                service_resource_type = self.BUILT_IN_MEF_PRODUCTION_SERVICE_TYPE

            service_type = circuit_details["properties"]["serviceType"]

            if service_type == "FIA" or service_type == "VOICE":
                # For FIA, circuitName uniquely identify the service in network
                circuitName = circuit_details["properties"]["serviceName"]
                mef_service = self.get_resource_by_type_and_properties(
                    service_resource_type, {"evcId": circuitName}, no_fail=True
                )

                if mef_service is not None:
                    msg = self.error_formatter(
                        self.INCORRECT_DATA_ERROR_TYPE,
                        self.TOPOLOGIES_DATA_SUBCATEGORY,
                        f"MEF Service {mef_service['id']} already exists with Circuit Name {circuitName}",
                    )
                    self.categorized_error = msg
                    self.exit_error(msg)
            elif service_type == "ELAN":
                pass

        elif stage == "POST":
            if len(network_services) == 0:
                msg = self.error_formatter(
                    self.INCORRECT_DATA_ERROR_TYPE,
                    self.TOPOLOGIES_DATA_SUBCATEGORY,
                    f"No network service found for {circuit_id}",
                )
                self.categorized_error = msg
                raise Exception(msg)

            # PROCESS FOR POST CHECK
            self.post_provisioning_actions(network_service_res)

    def patch_cpe_with_initial_state(self, circuit_details: dict, parent_resource) -> None:
        """Patches the CPE Initial State to the Parent Resource for Select Workstreams

        :param circuit_details: _description_
        :type circuit_details: dict
        :param parent_resource: _description_
        :type parent_resource: Any | Any | None
        """
        # NOW UPDATE THE CIRCUIT DETAILS WITH THE CPE AND INITIAL STATE OF THE CPE
        site_status = []
        cpe_node_list = []
        for topology in circuit_details["properties"]["topology"]:
            for node in topology["data"]["node"]:
                for name in node["name"]:
                    if name["name"] == "Role" and name["value"] == "CPE":
                        cpe_node_list.append(node)

        cpe_updated_dict = {}
        for cpe_node in cpe_node_list:
            cpe_updated_dict[cpe_node["uuid"]] = {}
            for name in cpe_node["name"]:
                if name["name"] == "Customer Address":
                    cust_addr = name["value"]
                    cpe_updated_dict[cpe_node["uuid"]]["customeraddr"] = cust_addr
                if name["name"] == "Host Name":
                    host_name = name["value"]
                    cpe_updated_dict[cpe_node["uuid"]]["hostname"] = host_name

        for cpe in cpe_updated_dict:
            site_status.append(
                {
                    "site": cpe_updated_dict[cpe].get(
                        "customeraddr", str(self.get_customer_addresses(circuit_details)[0])
                    ),
                    "host": cpe_updated_dict[cpe]["hostname"],
                    "state": "NOT_STARTED",
                }
            )

        patch = {"properties": {"site_status": site_status}}

        self.patch_observed(parent_resource["id"], patch)

    def post_provisioning_actions(self, network_service):
        """perform for post provisioning activities"""
        self.logger.info(f"Performing post processing for network service: {network_service['label']}")

        update_site_state = UpdateSiteState(self)
        circuit_details = self.get_associated_circuit_details_for_network_service(network_service["id"])

        if circuit_details is None:
            msg = self.error_formatter(
                self.MISSING_DATA_ERROR_TYPE,
                self.TOPOLOGIES_DATA_SUBCATEGORY,
                f"Cannot find Circuit Details associated with ID: {network_service['properties']['circuit_id']}",
            )
            self.categorized_error = msg
            raise Exception(msg)

        associated_fres = self.get_dependencies(
            network_service["id"], resource_type=self.BUILT_IN_FRE_TYPE, recursive=True
        )
        self.logger.debug(f"Associated FREs with NetworkService: {associated_fres}")
        associated_tpes = self.get_dependencies(
            network_service["id"], resource_type=self.BUILT_IN_TPE_TYPE, recursive=True
        )
        self.logger.debug(f"Associated TPEs with NetworkService: {associated_tpes}")
        site_state_dict = {}

        for ss in update_site_state.get_site_status_from_network_service(network_service, circuit_details):
            site_state_dict[ss["host"]] = ss

        # BUILD A LOOKUP BETWEEN FRE AND DEVICES
        device_fre_states = {}

        for fre in associated_fres:
            for dep in self.get_dependencies(fre["id"], recursive=True):
                if ".NetworkFunction" in dep["resourceTypeId"]:
                    self.logger.debug(f"Found device {dep['properties']['ipAddress']} for FRE: {fre['label']}")
                    device_fre_states[dep["properties"]["ipAddress"]] = fre

        device_tpe_states = {}

        for tpe in associated_tpes:
            for dep in self.get_dependencies(tpe["id"], recursive=True):
                if ".NetworkFunction" in dep["resourceTypeId"]:
                    self.logger.debug(f"Found device {dep['properties']['ipAddress']} for TPE: {tpe['label']}")
                    device_tpe_states[dep["properties"]["ipAddress"]] = tpe

        """ NOT SURE IF WE NEED THIS AS THIS SHOULD BE IN GRANITE
        # UPDATE THE CPE PROVISIONING STATE
        self.logger.debug("Circuit Details Before: " + str(circuit_details['properties']))
        for side in [circuit_details['properties']['a_side'], circuit_details['properties']['z_side']]:
            self.logger.debug("CircuitDetauls Side: " + str(side))
            cpe = side.get('cpe', {})
            if cpe is not None and len(cpe.keys()) > 0:
                nf = self.get_network_fuction_by_host(cpe['hostname'])
                if nf is not None and device_fre_states.get(cpe['hostname']) is not None \
                and device_fre_states[cpe['hostname']]['orchState'].lower() == "active":
                    cpe['provisioned'] = True
                elif nf is not None:
                    cpe['provisioned'] = False
        self.logger.debug("Circuit Details After: " + str(circuit_details['properties']))
        self.bpo.resources.patch(circuit_details['id'], {"properties": circuit_details['properties']})
        """

        # NOW UPDATE THE RESOURCES
        self.logger.debug(f"Device FRE States: {device_fre_states}")
        self.logger.debug(f"Device TPE States: {device_tpe_states}")
        self.logger.debug(f"Site State Dict: {site_state_dict}")

        for device_name, site_res in site_state_dict.items():
            fqdn = self.get_node_fqdn(circuit_details, device_name)
            mgnt_ip = self.get_node_management_ip(circuit_details, device_name)
            vendor = self.get_node_vendor(circuit_details, device_name)
            RESOURCE_TYPE_TO_CHECK = self.COMMON_TYPE_LOOKUP[vendor]["RESOURCE_TYPE_TO_CHECK"]

            if RESOURCE_TYPE_TO_CHECK == "tosca.resourceTypes.TPE":
                if (
                    device_name not in device_tpe_states.keys()
                    and fqdn not in device_tpe_states.keys()
                    and mgnt_ip not in device_tpe_states.keys()
                ):
                    if site_res["state"] not in ["UNKNOWN", "NOT_STARTED", "TERMINATED"]:
                        site_res["state"] = "FAILED"
                        self.patch_observed(network_service["id"], {"properties": {"state": "FAILED"}})
                    else:
                        continue
                else:
                    tpe = device_tpe_states.get(device_name)

                    if tpe is None:
                        tpe = device_tpe_states.get(fqdn)

                    if tpe is None:
                        tpe = device_tpe_states.get(mgnt_ip)

                    if tpe["orchState"].lower() == "activating":
                        site_res["state"] = "ACTIVATING-CONFIGURING"
                    else:
                        site_res["state"] = tpe["orchState"].upper()
            elif RESOURCE_TYPE_TO_CHECK == "tosca.resourceTypes.FRE":
                if (
                    device_name not in device_fre_states.keys()
                    and fqdn not in device_fre_states.keys()
                    and mgnt_ip not in device_fre_states.keys()
                ):
                    if site_res["state"] not in ["UNKNOWN", "NOT_STARTED", "TERMINATED"]:
                        site_res["state"] = "FAILED"
                        self.patch_observed(network_service["id"], {"properties": {"state": "FAILED"}})
                    else:
                        continue
                else:
                    fre = device_fre_states.get(device_name)

                    if fre is None:
                        fre = device_fre_states.get(fqdn)

                    if fre is None:
                        fre = device_fre_states.get(mgnt_ip)

                    if fre["orchState"].lower() == "activating":
                        site_res["state"] = "ACTIVATING-CONFIGURING"
                    else:
                        site_res["state"] = fre["orchState"].upper()
            elif RESOURCE_TYPE_TO_CHECK is None:
                site_res["state"] = "ACTIVE"
                update_site_state.update_site_state_by_network_service(
                    network_service, site_res["host"], site_res["state"]
                )
                continue

            update_site_state.update_site_state_by_network_service(network_service, site_res["host"], site_res["state"])

        self.logger.debug("Site State updated dict: " + str(site_state_dict))
