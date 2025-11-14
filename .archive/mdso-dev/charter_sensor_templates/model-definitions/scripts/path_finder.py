import sys
sys.path.append('model-definitions')
from scripts.common_plan import CommonPlan


class Activate(CommonPlan):
    def process(self):
        self.properties = self.resource["properties"]
        node_name, port_name = self.get_node_port_name_from_uuid(self.properties["port_uuid"])
        if "topology_resource_id" in self.properties.keys():
            cd_resource = self.bpo.resources.get(self.properties["topology_resource_id"])
        else:
            try:
                ns_resources = self.get_dependents(
                    self.resource["id"], resource_type="charter.resourceTypes.NetworkService", recursive=True
                )
                if len(ns_resources) == 1:
                    ns_resource = ns_resources[0]
                    service_mapper_resource = self.get_dependencies(
                        ns_resource["id"], resource_type="charter.resourceTypes.ServiceMapper"
                    )
                    if service_mapper_resource:
                        service_mapper_resource = service_mapper_resource[0]
                elif len(ns_resources) == 0:
                    self.logger.info(
                        "no network service resources found, trying for cpe activation and independent service mapper"
                    )
                    # if no network service, try for cpe activation and service mapper
                    cpe_activator = self.get_associated_resource(self.resource_id, self.BUILT_IN_CPE_ACTIVATOR_TYPE)
                    service_mapper_resource = self.get_associated_resource(
                        self.resource["id"], self.BUILT_IN_SERVICE_MAPPER_TYPE
                    )
                    if cpe_activator and not service_mapper_resource:
                        self.logger.info("CPE Activation")
                        ns_resource = cpe_activator
                    elif service_mapper_resource:
                        ns_resource = service_mapper_resource
                        self.logger.info("using service mapper as network service")
                else:
                    raise Exception("Too many Network service found")
            except Exception as ex:
                self.logger.info(str(ex))
                raise Exception(
                    "Unable to find NetworkService, cpeActivate, or service mapper resource \
                        while creating path finder resource for %s"
                    % self.properties["port_uuid"]
                )
            try:
                if service_mapper_resource:
                    cd_resource = self.get_dependencies(
                        service_mapper_resource["id"], resource_type="charter.resourceTypes.CircuitDetails"
                    )[0]
                    service_type_supported_by_service_mapper = self.is_service_type_supported_by_service_mapper(
                        cd_resource
                    )
                else:
                    cd_resource = self.get_dependencies(
                        ns_resource["id"], resource_type="charter.resourceTypes.CircuitDetails"
                    )[0]
            except Exception as ex:
                self.logger.info(str(ex))
                raise Exception(
                    "Unable to find Required circuit details Service resource \
                        while creating path finder resource for %s"
                    % self.properties["port_uuid"]
                )

        required_spoke = {}
        spoke_list = self.create_device_dict_from_circuit_details(cd_resource)
        for spoke in spoke_list:
            if node_name in spoke.keys():
                if spoke[node_name]["Client Interface"] == port_name or spoke[node_name][
                    "Client Interface"
                ] == port_name.replace("ETH_PORT", "ETH-PORT"):
                    required_spoke = spoke
                    break

        if required_spoke == {}:
            raise Exception("No Path Found for uniId %s" % self.properties["port_uuid"])

        output_nodes = []
        if self.is_handoff_device(required_spoke[node_name]):
            device_obj = self.create_device_obj_non_pe(required_spoke[node_name], cd_resource)
            output_nodes.append(device_obj)
        else:
            for spoke in spoke_list:
                for k, v in spoke.items():
                    if not self.is_handoff_device(v):
                        if v["Role"] == "PE":
                            if service_mapper_resource and service_type_supported_by_service_mapper:
                                self.logger.info(
                                    f'Service Mapper for {cd_resource["properties"]["serviceType"]}, PE modeling handled in servicefiaprovisioner.py'
                                )
                                continue
                            elif required_spoke[node_name]["Role"] == "PE" and k == node_name:
                                device_obj = self.create_device_obj_pe(cd_resource)
                            else:
                                continue
                        else:
                            if v["Equipment Status"] == "LIVE" or v["Ip Reachable"] == "True":
                                device_obj = self.create_device_obj_non_pe(v, cd_resource)
                            else:
                                continue
                        if device_obj not in output_nodes:
                            output_nodes.append(device_obj)

        output = {"required_nodes": output_nodes}
        self.logger.info("Output: " + str(output))

        return output

    def is_service_type_supported_by_service_mapper(self, cd_resource) -> bool:
        return bool(cd_resource["properties"]["serviceType"] in ["VOICE", "FIA"])

    def create_device_obj_pe(self, circuit_details):
        device_list = []
        device_obj = {}
        ctr = 1

        if circuit_details["properties"]["serviceType"] not in ["ELINE", "CTBH 4G"]:
            raise Exception(
                "Path Finder called for PE Device while Service Type is %s "
                % circuit_details["properties"]["serviceType"]
            )

        spoke_list = self.create_device_dict_from_circuit_details(circuit_details)
        for spoke in spoke_list:
            for key, value in spoke.items():
                if value["Role"] == "PE":
                    nf = self.get_network_function_by_host_or_ip(value["FQDN"], value["Management IP"])
                    if nf is None:
                        raise Exception(
                            "Unable to find Network Function for FQDN %s, IP %s "
                            % (value["FQDN"], value["Management IP"])
                        )
                    ep_detail = {
                        "node_id": nf["id"],
                        "port_id": value["Client Interface"] if value["Vendor"].upper() in ["NOKIA", "ALCATEL"] else self.get_port_id_from_port_name_and_device_id_retry(
                            value["Client Interface"], nf["id"], value["Role"]
                        ),
                        "port_role": self.get_port_role(
                            circuit_details, value["Host Name"] + "-" + value["Client Interface"]
                        ),
                        "port_description": value["Client Interface Description"],
                        "management_ip": value["Management IP"],
                        "service_description": self.get_service_endpoint_description(
                            circuit_details, value["Host Name"]
                        ),
                    }
                    # do not add duplicate
                    if ep_detail not in device_list:
                        device_list.append(ep_detail)

        for device in device_list:
            key = "node_" + str(ctr)
            device_obj[key] = device
            ctr += 1

        self.logger.info("Device Obj for PE EP %s is " % str(device_obj))
        return device_obj

    def create_device_obj_non_pe(self, values, circuit_details):
        nf = self.get_network_function_by_host_or_ip(values["FQDN"], values["Management IP"])
        if nf is None:
            raise Exception(
                "Unable to find Network Function for FQDN %s, IP %s " % (values["FQDN"], values["Management IP"])
            )
        port_id_value = self.COMMON_TYPE_LOOKUP[values["Vendor"]]["PORT_ID_VALUE"]
        network_interface_id = None
        client_interface_id = None
        if values["Role"] == "CPE" or (values["Role"] == "MTU" and port_id_value == "PORT_RESOURCE_ID"):
            network_interface_id = self.get_port_id_from_port_name_and_device_id_retry(
                values["Network Interface"], nf["id"], values["Role"]
            )
            client_interface_id = self.get_port_id_from_port_name_and_device_id_retry(
                values["Client Interface"], nf["id"], values["Role"]
            )
        device_obj = {
            "node_1": {
                "node_id": nf["id"],
                "port_id": client_interface_id or values["Client Interface"],
                "port_description": values["Client Interface Description"],
                "service_description": self.get_service_endpoint_description(circuit_details, values["Host Name"]),
            },
            "node_2": {
                "node_id": nf["id"],
                "port_id": network_interface_id or values["Network Interface"],
                "port_description": values["Network Interface Description"],
                "service_description": self.get_service_endpoint_description(circuit_details, values["Host Name"]),
            },
        }

        self.logger.info("Return Device Obj %s" % str(device_obj))
        return device_obj

    def get_port_id_by_device_and_name(self, device, uniid):
        # take a uniid that is passed in and search for the port resource
        # break it apart into device identifier and port
        port_name = self.get_node_port_name_from_uuid(uniid)[1]

        # move port name "ethernet 3" -> "TPE_ETHERNET-3_PTP"
        if port_name.lower().startswith("ethernet "):
            port_name = "TPE_ETHERNET-{}_PTP".format(port_name.split(" ")[-1])
        elif port_name.lower().startswith("ethernet-"):
            port_name = "TPE_ETHERNET-{}_PTP".format(port_name.split("-")[-1])
        elif port_name.lower().startswith("access "):
            port_name = "TPE_{}_PTP".format(port_name.upper())
        elif port_name.lower().startswith("access-"):
            port_name = "TPE_{}_PTP".format(port_name.upper())
        elif port_name.lower().startswith("network-"):
            port_name = "TPE_{}_PTP".format(port_name.upper())

        port_resource = None

        ports = []
        ports = ports + self.get_resources_by_type_and_properties(
            "tosca.resourceTypes.TPE", {"device": device["providerResourceId"]}
        )
        ports = ports + self.get_resources_by_type_and_properties("tosca.resourceTypes.TPE", {"device": device["id"]})

        for port in ports:
            if port.get("providerResourceId", "").endswith(port_name) or port.get("providerResourceId", "").endswith(
                port_name.lower()
            ):
                port_resource = port
                break

        if port_resource is None:
            raise Exception("Port Resource not found for %s" % str(uniid))
        return port_resource["id"]

    def get_service_endpoint_description(self, circuit_details, node_name):
        """
        returns the service level description to be applied
        """

        index = 0
        for topology in circuit_details["properties"]["topology"]:
            node_list = []
            for node in topology["data"]["node"]:
                node_list.append(node["uuid"])
            if node_name in node_list:
                break
            index += 1

        if index > 1:
            self.exit_error("Unable to find node in topology in path finder")

        endpoints = circuit_details["properties"]["service"][0]["data"]["evc"][0]["endPoints"]
        try:
            service_description = endpoints[index]["userLabel"]
        except IndexError:
            self.exit_error("Unable to fetch service description while creating path finder resource")

        return service_description
