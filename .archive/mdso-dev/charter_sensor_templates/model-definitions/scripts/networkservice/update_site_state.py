""" -*- coding: utf-8 -*-

UpdateSiteState Plans

Versions:
   0.1 Jan 03, 2018
       Initial check in of CreateFre plans

"""


class UpdateSiteState:
    """this will create a TPE for the two devices links"""

    def __init__(self, common_plan):
        self.plan = common_plan

    def update_site_state_by_circuit_id(self, circuit, site, state):
        """this will update the site state of the NetworkService

        :param circuit: Charter circuit name
        :param site: Site name, can be host name or site name
        :param state: State of the site
        :type circuit: str
        :type site: str
        :type state: state

        :return: None
        """
        network_service = self.get_associated_network_service_for_circuit_id(circuit)
        self.update_site_state_by_network_service(network_service, site, state)

    def update_site_state_by_network_service(self, network_service, site, state):
        """this will update the site state of the NetworkService

        :param network_service: NetworkService ID or Resource
        :param site: Site name, can be host name or site name
        :param state: State of the site
        :type circuit: str
        :type site: str
        :type state: state

        :return: None
        """
        if isinstance(network_service, str):
            network_service = self.bpo.resources.get(network_service)

        if network_service is None:
            raise Exception("None passed in for NetworkService")

        site_status = network_service["properties"].get("site_status", [])
        new_status = []
        for site_state in site_status:
            if site == site_state["host"] or site == site_state["site"]:
                site_state["state"] = state

            new_status.append(site_state)

        if len(new_status) == 0:
            self.plan.logger.debug("No status to update")
            return

        patch = {"properties": {"site_status": new_status}}

        self.plan.logger.debug("Updating ID %s with status: %s" % (network_service["id"], str(patch)))
        self.plan.bpo.resources.patch_observed(network_service["id"], patch)

    def get_site_status_from_network_service(self, network_service, circuit_details=None):
        """returns the properties.site_state of the network_service

        If it does not exist, it build the initial one

        :param network_service: Network Service resource
        :param circuit_details: Circuit Details resource
        :type network_service: charter.resourceTypes.NetworkService
        :type circuit_details: charter.resourceTypes.CircuitDetails

        :return: properties.site_state in NetworkService
        :rtype: dict
        """
        unique_list = []
        site_status = network_service["properties"].get("site_status", None)
        if site_status is None:
            site_status = []
            if circuit_details is None:
                circuit_details = self.plan.get_associated_circuit_details(network_service["properties"]["circuit_id"])

            for spoke in self.plan.create_device_dict_from_circuit_details(circuit_details):
                for device in list(spoke.values()):
                    if device["Role"] == "CPE" and device["Host Name"] not in unique_list:
                        site_status.append(
                            {"site": device.get("Customer Address"), "host": device["Host Name"], "state": "UNKNOWN"}
                        )
                        unique_list.append(device["Host Name"])

        return site_status
