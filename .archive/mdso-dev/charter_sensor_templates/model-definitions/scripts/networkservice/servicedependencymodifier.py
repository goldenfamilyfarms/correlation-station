""" -*- coding: utf-8 -*-

ServiceDependencyModifier Plans

Versions:
   0.1 Feb 16, 2018
       Initial check in of ServiceDependencyModifier plans

"""
import sys
sys.path.append('model-definitions')
from scripts.complete_and_terminate_plan import CompleteAndTerminatePlan
import time


class Activate(CompleteAndTerminatePlan):
    """this is the class that is called for the initial activation of the
    ServiceProvisioner.
    """

    def process(self):
        action = self.properties.get("action", "ACTIVATE")
        operation = self.properties["operation"]
        # Get the network service, if this is a test, no need to update anything.
        self.service_mapper = None
        network_service = self.get_associated_network_service_for_resource(self.resource_id)
        if network_service and network_service["orchState"] == "failed":
            network_service = None
            self.logger.info("Found a Failed Network Service, skipping the Association")
        if network_service:
            self.service_mapper = self.get_dependencies(network_service["id"], self.BUILT_IN_SERVICE_MAPPER_TYPE)
            if self.service_mapper:
                self.service_mapper = self.service_mapper[0]
        else:
            # TODO is there a reason to use get dependencies instead of this if there's a network service?
            self.service_mapper = self.get_associated_resource(self.resource["id"], self.BUILT_IN_SERVICE_MAPPER_TYPE)
        if network_service is not None and network_service["properties"]["stage"] == "TEST":
            self.logger.info("Network service is built with test mode, so skipping processing.")
            return

        # IF TERMINATE CALLED DO THAT LAST
        if action == "TERMINATE":
            self.terminate()
            return

        # DO ACTIVATE
        circuit_details_id = self.properties["circuit_details_id"]

        # Get the circuit details and network service
        circuit_details = self.get_resource(circuit_details_id)

        # IS THE SERVICE FULLY PROVISIONED
        aff_devices = self.get_affected_devices_from_circuit(self.resource["id"], circuit_details, operation)
        for device in aff_devices:
            is_complete = True
            if self.is_node_provisioned(circuit_details, device) == "False":
                is_complete = False

            # UPDATE THE PORTS
            device_properties = {
                "Role": self.get_node_role(circuit_details, device).upper(),
                "Client Neighbor": self.get_node_client_neighbor(circuit_details, device),
            }
            if device_properties["Role"] == "PE":
                if operation == "SERVICE_MAPPER":
                    pass
                else:
                    self.update_pe(circuit_details, device, is_complete, operation)

            elif self.is_handoff_device(device_properties):
                self.log(is_complete)
                self.update_cpe(circuit_details, device, is_complete, operation)
            else:
                self.update_agg_mtu(circuit_details, device, is_complete)

    def update_pe(self, circuit_details, device, is_active, operation):
        """update the PE port properties
        create/update of the service on the PE port
        """

        # WHen we move Juniper to Plugin, this should be take care of in plugin
        if is_active is False:
            return
        neighbor = self.get_node_client_neighbor(circuit_details, device)
        if not neighbor == "None":
            neighbor_role = self.get_node_role(circuit_details, neighbor)
            if neighbor_role == "CPE" and self.is_node_provisioned(circuit_details, neighbor) == "False":
                # Dont bring the PE client port up in this case
                return

        # fIX ME
        # NEED TO USE CUT THROUGH HERE
        # CPE ACTIVATION WOULD FAIL HERE/RESYNC PTP
        # SERVICE ACTIVATE WONT HAVE ANY ISSUES
        if operation == "CPE_ACTIVATION":
            fqdn = self.get_node_fqdn(circuit_details, device)
            network_function = self.get_network_function_by_host(fqdn)
            interface_name = self.get_node_client_interface(circuit_details, device)
            interface_res_id = self.get_port_id_from_port_name_and_device_id_retry(
                interface_name, network_function["id"]
            )

            interface_res = self.get_resource(interface_res_id)
            apply_groups = (
                interface_res["properties"]["data"]["attributes"].get("additionalAttributes", {}).get("apply-groups")
            )
            if apply_groups:
                if "DISABLEIF" in apply_groups:
                    apply_groups.remove("DISABLEIF")

                patch = {"properties": interface_res["properties"]}
                self.bpo.resources.patch(interface_res_id, {"discovered": False})
                self.bpo.resources.patch(interface_res_id, patch)
                self.bpo.resources.patch(interface_res_id, {"discovered": True})

    def update_cpe(self, circuit_details, device, is_active, operation):
        """update the CPE port properties
        create/update of the service on the CPE port
        """
        state = "IS"
        if is_active is False and not self.service_mapper:
            state = "OOS_AUMA"

        self.logger.info(state)

        device_state = self.get_node_bpo_state(circuit_details, device)
        if not device_state == self.BPO_STATES["AVAILABLE"]["state"]:
            return
        device_vendor = self.get_node_vendor(circuit_details, device)
        device_model = self.get_node_property(circuit_details, device, "Model")
        service_type = circuit_details["properties"]["serviceType"]
        netconf_devicelist = ["FSP 150-XG116PRO", "FSP 150-XG116PROH", "FSP 150-XG118PRO (SH)"]

        # FIRST DO THE UNI PORT
        interface = self.get_node_property(circuit_details, device, "Client Interface")
        interface_role = self.get_port_role(circuit_details, device + "-" + interface)
        if interface_role == "ENNI":
            return
        network_service = self.get_associated_network_service_for_resource(self.params["resourceId"])
        if self.service_mapper and not network_service:
            network_service = self.service_mapper
        self.get_node_reachability(circuit_details, device)
        device_role = self.get_node_role(circuit_details, device)
        is_cpe_activate = False
        if not network_service or (network_service["orchState"] == "active" and device_role == "CPE"):
            is_cpe_activate = True
        self.logger.info("CPE Activate: {}".format(is_cpe_activate))
        mgmt_ip = self.get_node_management_ip(circuit_details, device)
        fqdn = self.get_node_fqdn(circuit_details, device)
        nf = self.get_network_function_by_host_or_ip(fqdn, mgmt_ip)
        tpe_id = self.get_port_id_from_port_name_and_device_id_retry(interface, nf["id"])
        if tpe_id is None:
            interface = interface.replace("ETH-PORT", "ETH_PORT")
            tpe_id = self.get_port_id_from_port_name_and_device_id_retry(interface, nf["id"])
        if tpe_id is None:
            msg = "Unable to get TPE for host %s name %s" % (fqdn, interface)
            # DAVID: host is not defined
            self.categorized_error = self.ERROR_CATEGORY["MDSO"].format(msg) if self.ERROR_CATEGORY.get("MDSO") else ""
            self.exit_error(msg)

        tpe = self.bpo.resources.get(tpe_id)
        discovered_tpe = self.bpo.resources.get(tpe_id)
        self.logger.info("Discovered TPE for device {}:\n{}".format(device, discovered_tpe))

        # Only update the TPE if there is only 1 Active FRE on it
        index = 0
        while index < 4:
            fres = self.get_dependents(
                tpe["id"], resource_type=self.BUILT_IN_FRE_TYPE, recursive=True, exception_on_failure=False
            )
            if len(fres) > 0:
                break
            self.logger.debug("No dependent on TPE %s, checking again in 10secs" % (interface))
            time.sleep(10)
            index += 1

        self.logger.debug("TPE %s has %s number of FREs." % (interface, str(len(fres))))
        active_ctp_count = 0
        for fre in fres:
            if (
                fre["properties"]["data"]["attributes"].get("networkRole", "") == "IFRE"
                and fre["properties"]["data"]["attributes"]["adminState"] == "enabled"
            ):
                active_ctp_count += 1

        self.logger.debug("TPE %s has %s number of active CTPs." % (interface, str(active_ctp_count)))
        is_discovered = tpe["discovered"]
        self.logger.info("Is TPE discovered? {}".format(is_discovered))
        if active_ctp_count > 1:
            self.logger.debug(
                "TPE %s has more than 1 active CTPs. Skipping the physical port configuration" % interface
            )

        if active_ctp_count == 1:
            if is_discovered is True and not operation == "SERVICE_MAPPER":
                self.bpo.resources.patch(tpe["id"], {"discovered": False})

            props = tpe["properties"]
            props["data"]["attributes"]["state"] = state
            props["data"]["attributes"]["userLabel"] = self.get_node_client_interface_description(
                circuit_details, device
            )
            if "mtu" in props["data"]["attributes"].keys():
                props["data"]["attributes"]["mtu"] = self.COMMON_TYPE_LOOKUP[device_vendor]["MTU"]
            else:
                if device_vendor == "RAD":
                    props["data"]["attributes"]["layerTerminations"][0]["additionalAttributes"]["egressMtu"] = str(
                        self.COMMON_TYPE_LOOKUP[device_vendor]["MTU"]
                    )

                else:
                    props["data"]["attributes"]["layerTerminations"][0]["additionalAttributes"]["egressMtu"] = int(
                        self.COMMON_TYPE_LOOKUP[device_vendor]["MTU"]
                    )

            if self.COMMON_TYPE_LOOKUP[device_vendor].get("UNI_L2CP_PROFILE") is not None:
                props["data"]["attributes"]["layerTerminations"][0]["additionalAttributes"][
                    "l2cpProfile"
                ] = self.COMMON_TYPE_LOOKUP[device_vendor].get("UNI_L2CP_PROFILE")

            self.logger.debug("Updating port %s with attributes: %s" % (interface, str(props["data"]["attributes"])))
            if operation == "SERVICE_MAPPER":
                tpe["properties"] = props

                if device_model in netconf_devicelist:
                    # adva 116pro specific
                    self.resource_compare_tpe_pro(discovered_tpe, tpe, self.service_mapper["id"], device, service_type)
                else:
                    self.resource_remodeling_tpe(discovered_tpe, tpe, self.service_mapper["id"], device, circuit_details)
            else:
                self.bpo.resources.patch(
                    tpe["id"], {"properties": {"data": {"attributes": props["data"]["attributes"]}}}
                )
            if is_discovered is True:
                self.bpo.resources.patch(tpe["id"], {"discovered": True})

            self.logger.debug(
                "Checking TPE differences for port %s with attributes: %s"
                % (interface, str(props["data"]["attributes"]))
            )
            try:
                self.await_differences_cleared_collect_timing("CPE TPE resource ", tpe["id"], interval=10.0, tmax=60.0)
            except Exception as ex:
                msg = "Unable to get differences cleared for port %s with attributes: %s due to error: %s" % (
                    interface,
                    str(props["data"]["attributes"]),
                    str(ex),
                )
                self.categorized_error = (
                    self.ERROR_CATEGORY["MDSO"].format(msg) if self.ERROR_CATEGORY.get("MDSO") else ""
                )
                self.exit_error(msg)

            self.logger.debug(
                "Awaiting until TPE is active for port %s with attributes: %s"
                % (interface, str(props["data"]["attributes"]))
            )
            self.await_active_collect_timing([tpe["id"]], interval=1.0, tmax=30.0)

        # NOW FOR THE NNI PORT
        if self.COMMON_TYPE_LOOKUP[device_vendor].get(device_model) is None:
            self.logger.debug("No model that matches %s in the lookup." % device_model)
            return

    def update_agg_mtu(self, circuit_details, device, is_active):
        """
        Discussed with charter, they say we do not have to update agg and mtu tpes at present
        When there is a requirement we will make the necessary changes.
        """
        pass

    def update_fres(self, circuit_details_id):
        """Updated the FREs to clear differences"""
        network_service = self.get_associated_network_service_for_resource(circuit_details_id)
        fres = self.get_dependents_by_type_and_query(
            network_service["id"],
            resource_type=self.BUILT_IN_FRE_TYPE,
            recursive=True,
            query="properties.networkRole:IFRE,discovered:false",
        )

        for fre in fres:
            self.bpo.resources.patch(fre["id"], {"discovered": True})
            self.await_differences_cleared_collect_timing(fre["label"], fre["id"])
            self.bpo.resources.patch(fre["id"], {"discovered": False})

    def terminate(self):
        # since this is now a soft terminate
        # we dont need to do anything.
        pass

    def terminate_update_pe(self, circuit_details, device):
        """update the PE port properties
        termination of the service on the PE port
        """
        # NOT NEEDED RIGHT NOW
