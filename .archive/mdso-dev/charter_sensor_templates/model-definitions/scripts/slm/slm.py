""" -*- coding: utf-8 -*-

SLM Plans

Versions:
   0.1 Aug 19, 2021
       Initial check in of SLM plans

"""
from scripts.common_plan import CommonPlan
from ra_plugins.ra_cutthrough import RaCutThrough


class Activate(CommonPlan):
    def process(self):
        props = self.resource["properties"]
        self.circuit_id = props["circuit_id"]
        self.circuit_details = props.get("circuitDetails")
        """
        solutioning:
        1- get current circuit details
        2- parse out endpoints/tids
        2.5- supported devices
        3- log into endpoints, resync device/session
        4- poll and parse
        """
        self.cutthrough = RaCutThrough()

        # step 1: get current circuit details
        self.new_circuit_details = self.circuit_details if self.circuit_details else self.get_new_circuit_details()
        self.logger.info("new circuit details = {}".format(self.new_circuit_details))
        slm_new_circuit_details = self.slm_device_validator(self.new_circuit_details)

        # step 2: parse out slm reflector and probe tids and ports
        # determine which side reflector is on based on device count
        z_side_device_count = self.device_count_per_side(1)
        # if z side only has 1 device: Z side MX/reflector, A side CPE/probe
        if z_side_device_count == 1:
            reflector = self.determine_slm_device_details(1, "reflector")
            probe = self.determine_slm_device_details(0, "probe")
        # otherwise more common topology applies: A side CPE/reflector, Z side CPE/probe
        else:
            reflector = self.determine_slm_device_details(0, "reflector")
            probe = self.determine_slm_device_details(1, "probe")
        self.logger.info("Reflector: {}\nProbe: {}".format(reflector, probe))

        # determine endpoint port roles
        roles = self.translate_granite_slm([reflector["uuid"], probe["uuid"]])
        self.logger.info("endpoint roles from granite: {}".format(str(roles)))

        # step 2.5: eligibility check
        reflector_eligible = self.check_device_eligibility(reflector, "reflector")
        probe_eligible = self.check_device_eligibility(probe, "probe")
        if reflector_eligible and probe_eligible:
            eligible = True
        else:
            eligible = False
            self.exit_error(
                "Device pairing not eligible. \
                Reflector: {} {}\nProbe: {} {}".format(
                    reflector["model"], reflector["tid"], probe["model"], probe["tid"]
                )
            )

        slm_devices = {reflector["tid"]: reflector, probe["tid"]: probe}

        # step 3: log into endpoints, resync device/session
        # onboard device/try to log in
        slm_configs, next_manet = {}, {}
        if eligible:
            for device in slm_devices:
                self.device_onboard(slm_new_circuit_details, slm_devices[device])
                if self.onboarded:
                    network_function = self.get_network_function_by_host_or_ip(
                        slm_devices[device]["fqdn"], slm_devices[device]["mgmt_ip"]
                    )
                    self.logger.info("Network Function = {}".format(network_function))
                    device_prid = network_function["providerResourceId"]
                    # issue racutthrough to get CFM configuration
                    vendor = slm_devices[device]["vendor"]
                    connection_type = self.get_network_function_connection_type(network_function)
                    cfm_config_data = self.cutthrough.execute_ra_command_file(
                        device_prid,
                        "get-cfm-configuration.json"
                        if connection_type == "cli"
                        else "get-cfm-configuration-netconf.json",
                    )
                    maintenance_domains = self.parse_for_maintenance_domain(cfm_config_data, vendor, connection_type)
                    self.logger.info("maintenance domains: {}".format(maintenance_domains))
                    if self.maintenance_association_command_required(vendor, connection_type):
                        maintenance_association_return = self.cutthrough.execute_ra_command_file(
                            device_prid, "list-oam-mas.json"
                        )
                        maintenance_domains = self.get_maintenance_association_info(
                            maintenance_association_return, maintenance_domains, vendor
                        )
                    next_manet[device] = self.get_next_available_manet(
                        maintenance_domains, network_function, roles, vendor
                    )
                    slm_configs[device] = {
                        "CFM_config": maintenance_domains,
                        "slmRole": slm_devices[device]["slm_role"],
                        "vendor": vendor,
                    }
                    self.logger.info("cfm configs = {}".format(slm_configs))
                else:
                    self.exit_error("onboarding failure on {}".format(slm_devices[device]))

        self.bpo.resources.patch_observed(
            self.resource["id"],
            data={"properties": {"slm_configuration": slm_configs, "next_available_MANETs": next_manet}},
        )

    def maintenance_association_command_required(self, vendor, connection_type):
        maintenance_association_vendors = ["RAD", "ADVA"]
        return True if vendor in maintenance_association_vendors and connection_type == "cli" else False

    def device_count_per_side(self, topology_index):
        device_count = 0
        for device in self.new_circuit_details["properties"]["topology"][topology_index]["data"]["node"]:
            device_count += 1
        return device_count

    def determine_slm_device_details(self, topology_index, slm_role):
        for device in self.new_circuit_details["properties"]["topology"][topology_index]["data"]["node"]:
            device_data = device["name"]
            device_info = {detail["name"]: detail["value"] for detail in device_data}
            if (
                device_info["Host Name"]
                == self.new_circuit_details["properties"]["service"][0]["data"]["evc"][0]["endPoints"][topology_index][
                    "uniId"
                ].split("-")[0]
            ):
                slm_device = self.add_slm_device_details(device_info)
                slm_device["slm_role"] = slm_role
                return slm_device

    def add_slm_device_details(self, device_info):
        return {
            "tid": device_info["Host Name"],
            "port": device_info["Client Interface"],
            "uuid": "{}-{}".format(
                device_info["Host Name"],
                device_info["Client Interface"],
            ),
            "model": device_info["Model"],
            "mgmt_ip": device_info["Management IP"],
            "fqdn": device_info["FQDN"],
            "role": device_info["Role"],
            "vendor": device_info["Vendor"],
        }

    def translate_device_model(self, slm_device):
        models_by_vendor = {"JUNIPER": ["MX"], "ADVA": ["114/", "114PRO", "116PRO"], "RAD": ["203", "220", "2I"]}
        for model in models_by_vendor[slm_device["vendor"]]:
            if model in slm_device["model"]:
                device_model = model.replace("/", "")

        return device_model

    def check_device_eligibility(self, slm_device, slm_role):
        eligible = False
        eligibile_devices = {
            "reflector": ["MX", "220", "203", "2I", "114", "114PRO", "116PRO"],
            "probe": ["220", "203", "2I", "114", "114PRO", "116"],
        }
        translated_model = self.translate_device_model(slm_device)
        self.logger.info("eligibile devices: {}".format(eligibile_devices))
        if translated_model in eligibile_devices[slm_role]:
            eligible = True
            self.logger.info("Eligible {}: {} {}".format(slm_role, slm_device["model"], slm_device["tid"]))

        return eligible

    def determine_maintenance_domain_name(self, network_function, roles):
        tid = str(network_function["label"].split(".")[0]).upper()
        for device in roles:
            if tid in device:
                maintenance_domain_name = roles[device]
                self.logger.info("DEVICE: {}\nMD NAME: {}".format(tid, maintenance_domain_name))
                return maintenance_domain_name

    @property
    def domain_levels(self):
        return {"UNI-UNI": "3", "UNI-ENNI": "2"}

    def check_domain_availability(self, cfm, maintenance_domain_name):
        cid_eligible = True
        # Check that domain does not exist with given standard maintenance_domain_name and level
        self.logger.info("maintenance domain name: {}, cfm: {}".format(maintenance_domain_name, cfm))
        for domain in cfm:
            if (
                maintenance_domain_name == domain["name"]
                and self.domain_levels[maintenance_domain_name] == domain["level"]
            ):
                for ma in domain["MAs"]:
                    self.logger.info("ma[name] = {}, self.circuit_id = {}".format(ma["name"], self.circuit_id))
                    if ma["name"] == self.circuit_id:
                        # domain exists already with given standard maintenance_domain_name and level, circuit is ineligible
                        cid_eligible = False
        self.logger.info("cid_eligible is: {}".format(cid_eligible))
        return cid_eligible

    def separate_maintenance_association_data(self, cfm, vendor):
        # break out list of maintenance associations from cfm data
        maintenance_associations = [maintenance_domain["maintenance-associations"] for maintenance_domain in cfm]
        # flatten list of maintenance associations
        maintenance_associations = [
            ma for maintenance_association in maintenance_associations for ma in maintenance_association
        ]
        if vendor == "ADVA":
            try:
                return sorted(
                    [
                        maintenance_association["id"].split("-")[2]
                        for maintenance_association in maintenance_associations
                    ]
                )
            except IndexError:
                return sorted([maintenance_association["id"] for maintenance_association in maintenance_associations])
        if vendor == "RAD":
            return sorted([maintenance_association["id"] for maintenance_association in maintenance_associations])

    def get_last_configured_maintenance_association(self, maintenance_associations):
        return 0 if len(maintenance_associations) == 0 else int(maintenance_associations[-1])

    def get_next_available_manet(self, cfm, network_function, roles, vendor):
        self.logger.info("finding next available MANET")
        maintenance_domain_name = self.determine_maintenance_domain_name(network_function, roles)
        if vendor == "JUNIPER":
            cid_eligible = self.check_domain_availability(cfm, maintenance_domain_name)
            if cid_eligible:
                manet = "CID eligible"
            else:
                manet = "CID in use for MANET. Ineligible."
        else:  # RAD and Adva logic
            self.logger.info("CFM: {}".format(cfm))
            maintenance_associations = self.separate_maintenance_association_data(cfm, vendor)
            last_configured_maintenance_association = self.get_last_configured_maintenance_association(
                maintenance_associations
            )
            manet = last_configured_maintenance_association + 1
            self.logger.info("next available manet: {}".format(manet))

        return manet

    # need to pass in correct domain level and name to compare this against.
    def translate_granite_slm(self, endpoint_ports):
        self.logger.info("new cd: {} \n endpoint_ports: {}".format(self.new_circuit_details, endpoint_ports))
        translation = {"UNI": "UNI-UNI", "ENNI": "UNI-ENNI", "INNI": "UNI-ENNI"}
        endpoint_roles = {}
        try:
            for topo in self.new_circuit_details["properties"]["topology"]:
                for node in topo["data"]["node"]:
                    for edgenode in node["ownedNodeEdgePoint"]:
                        if edgenode["uuid"] in endpoint_ports:
                            for element in edgenode["name"]:
                                if element["name"].upper() == "ROLE":
                                    endpoint_roles[edgenode["uuid"]] = translation[element["value"]]

            return endpoint_roles

        except Exception as e:
            self.exit_error("Failed during granite translation for: {}".format(e))

    def parse_for_maintenance_domain(self, command_output, vendor, connection_type):
        maintenance_domain_parser_by_vendor = {
            "JUNIPER": self.juniper_maintenance_domains,
            "RAD": self.rad_maintenance_domains,
            "ADVA": self.adva_maintenance_domains,
        }
        cfm_config_data = command_output.json()["result"]
        self.logger.info("Return from MD commands: {}".format(cfm_config_data))
        return maintenance_domain_parser_by_vendor[vendor](cfm_config_data, connection_type)

    def juniper_maintenance_domains(self, cfm_config_data, connection_type=None):
        maintenance_domain_list = []
        for maintenance_domain in cfm_config_data:
            maintenance_domains = {}
            maintenance_domains["name"] = maintenance_domain["name"]
            maintenance_domains["level"] = maintenance_domain["level"]
            maintenance_domains["maintenance-associations"] = maintenance_domain["maintenance-association"]
            maintenance_domain_list.append(maintenance_domains)
        if maintenance_domain_list:
            return maintenance_domain_list
        else:
            self.exit_error("no maintenance domains found on this device")

    def rad_maintenance_domains(self, cfm_config_data, connection_type=None):
        maintenance_domain_list = []
        for maintenance_domain in cfm_config_data:
            maintenance_domains = {"maintenance-associations": []}
            maintenance_domains["name"] = maintenance_domain["properties"]["name"]
            maintenance_domains["level"] = maintenance_domain["properties"]["md-level"]
            maintenance_domains["md-id"] = maintenance_domain["properties"]["md-id"]
            maintenance_domain_list.append(maintenance_domains)
        if maintenance_domain_list:
            return maintenance_domain_list
        else:
            self.exit_error("no maintenance domains found on this device")

    def adva_maintenance_domains(self, cfm_config_data, connection_type=None):
        maintenance_domain_list = []
        # netconf data shape
        if connection_type == "netconf":
            for maintenance_domain in cfm_config_data["data"]["maintenance-domain"]:
                maintenance_associations = []
                maintenance_domains = {
                    "name": maintenance_domain["name"],
                    "md-id": maintenance_domain["id"],
                    "level": maintenance_domain["md-level"],
                }
                if isinstance(maintenance_domain["maintenance-association"], list):
                    for maintenance_association in maintenance_domain["maintenance-association"]:
                        maintenance_associations.append(maintenance_association)
                        maintenance_domains["maintenance-associations"] = maintenance_associations
                if isinstance(maintenance_domain["maintenance-association"], dict):
                    maintenance_domains["maintenance-associations"] = [maintenance_domain["maintenance-association"]]
                maintenance_domain_list.append(maintenance_domains)
        # cli data shape
        if connection_type == "cli":
            for maintenance_domain in cfm_config_data["output"]:
                maintenance_domains = {
                    "maintenance-associations": [],
                    "name": maintenance_domain["mdName"],
                    "level": maintenance_domain["mdLevel"],
                    "md-id": maintenance_domain["mdId"],
                }
                maintenance_domain_list.append(maintenance_domains)
        if maintenance_domain_list:
            return maintenance_domain_list
        else:
            self.exit_error("no maintenance domains found on this device")

    def get_maintenance_association_info(self, maintenance_association_return, maintenance_domains, vendor):
        maintenance_association_data = {
            "RAD": self.rad_maintenance_associations,
            "ADVA": self.adva_maintenance_associations,
        }
        return maintenance_association_data[vendor](maintenance_association_return, maintenance_domains)

    def adva_maintenance_associations(self, maintenance_association_return, maintenance_domains):
        maintenance_association_return = maintenance_association_return.json()["result"]
        self.logger.info("adva maintenance association command return: {}".format(maintenance_association_return))
        for maintenance_domain in maintenance_domains:
            for maintenance_association in maintenance_association_return:
                maintenance_association_zip = zip(
                    maintenance_association["manetId"], maintenance_association["manetName"]
                )
                for maintenance_association_data in maintenance_association_zip:
                    if maintenance_domain["md-id"].split("-")[1] == maintenance_association_data[0].split("-")[1]:
                        maintenance_domain["maintenance-associations"].append(
                            {"id": maintenance_association_data[0], "name": maintenance_association_data[1]}
                        )
        return maintenance_domains

    def rad_maintenance_associations(self, maintenance_association_return, maintenance_domains):
        maintenance_association_return = maintenance_association_return.json()["result"]
        self.logger.info("rad maintenance association command return: {}".format(maintenance_association_return))
        for maintenance_domain in maintenance_domains:
            for maintenance_association in maintenance_association_return:
                if maintenance_association["properties"]["md-id"] == maintenance_domain["md-id"]:
                    maintenance_domain["maintenance-associations"].append(
                        {
                            "id": maintenance_association["properties"]["id"],
                            "name": maintenance_association["properties"]["name"],
                        }
                    )
        return maintenance_domains

    def device_onboard(self, circuit_details, device_details):
        # Onboards device
        operation = "SLM"
        product = "charter.resourceTypes.ServiceDeviceOnboarder"
        ser_product = self.get_built_in_product(product)
        product_name = "ServiceDeviceOnboarder"
        details = {
            "label": self.circuit_id + "." + product_name,
            "productId": ser_product["id"],
            "properties": {
                "circuit_details_id": circuit_details["id"],
                "circuit_id": self.circuit_id,
                "context": "ALL",
                "operation": operation,
            },
        }
        self.resource_create(details, product, product_name, device_details)

    def slm_device_validator(self, circuit_details):
        # Identifies devices to onboard.
        slm_devicevalidator_product = self.get_built_in_product(self.BUILT_IN_SERVICE_DEVICE_VALIDATORY_TYPE)

        slm_devicevalidator_details = {
            "label": circuit_details["id"] + ".slm_devicevalidator",
            "productId": slm_devicevalidator_product["id"],
            "properties": {
                "circuit_details_id": circuit_details["id"],
                "circuit_id": self.circuit_id,
                "operation": "SLM",
            },
        }
        self.bpo.resources.create(self.resource["id"], slm_devicevalidator_details)
        circuit_details = self.bpo.resources.get(circuit_details["id"])
        return circuit_details

    def resource_create(self, res_details, rtype, what, device_details):
        try:
            self.logger.info(what + " for circuit_id " + self.circuit_id)
            if rtype == "charter.resourceTypes.ServiceDeviceOnboarder":
                res_created = self.create_active_resource(rtype, self.resource_id, res_details, wait_active=False)
                self.await_termination(res_created.resource_id, rtype, False, tmax=345)
                Network_Function_Resource = self.get_network_function_by_host_or_ip(
                    device_details["fqdn"], device_details["mgmt_ip"]
                )
                self.logger.info("Onboard Network_Function_Resource: {}".format(Network_Function_Resource))
                if Network_Function_Resource["orchState"] != "active":
                    self.bpo.resources.patch_observed(self.resource["id"], data={"properties": {"eligible": False}})
                    self.bpo.resources.patch_observed(
                        self.resource["id"], data={"properties": {"failure_status": "Could not onboard the CPE"}}
                    )
                    self.onboarded = False
                    self.bpo.resources.delete(Network_Function_Resource["id"])
                else:
                    self.onboarded = True
            else:
                res_created = self.create_active_resource(rtype, self.resource_id, res_details, wait_active=False)
                self.await_termination(res_created.resource_id, rtype, False, tmax=345)

        except Exception as ex:
            self.exit_error("Exception - '%s' raised for product %s while SLM %s" % (str(ex), rtype, self.resource_id))

    def get_new_circuit_details(self):
        cd_collector_product = self.get_built_in_product(self.BUILT_IN_CIRCUIT_DATA_COLLECTOR_TYPE)
        cd_collector_details = {
            "label": self.circuit_id + "slm.cd_collector",
            "productId": cd_collector_product["id"],
            "properties": {
                "circuit_id": self.circuit_id,
                "use_alternate_circuit_details_server": self.properties.get(
                    "use_alternate_circuit_details_server", False
                ),
                "operation": "SLM",
            },
        }

        try:
            self.logger.info("Creating CircuitDetailsCollector for %s" % self.circuit_id)
            self.logger.info("Resources Coming from the Logger: {}".format(self.resource_id))
            cdc_res_created = self.bpo.resources.create(self.resource_id, cd_collector_details)
            circuit_details_id = cdc_res_created.resource["properties"]["circuit_details_id"]
            new_circuit_details = self.bpo.resources.get(circuit_details_id)

        except Exception as ex:
            self.exit_error("Exception %s raised when attempting to create CircuitDetailsCollector" % (str(ex)))

        return new_circuit_details


class Terminate(CommonPlan):
    def process(self):
        pass
