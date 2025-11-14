import sys
sys.path.append('model-definitions')
from scripts.common_plan import CommonPlan
import traceback
import requests as rqst
import meraki


class REQUEST:
    def __init__(self, req):
        self.parent = req

    def get(self, *args, **kwargs):
        return self.parent.get(*args, **kwargs)

    def put(self, *args, **kwargs):
        return self.parent.put(*args, **kwargs)

    def post(self, *args, **kwargs):
        return self.parent.post(*args, **kwargs)


requests = REQUEST(rqst)


class Activate(CommonPlan):
    def process(self):
        # load in all data that we need
        self.properties = self.resource["properties"]
        self.private_data = self.get_private_data()
        auditor = Acceptance(self)
        if auditor.org_id:
            auditor.runAcceptance()
        # report already recorded to resource

    def get_private_data(self):
        defaults = self.bpo.resources.get(
            self.get_resources_by_type_and_label("charter.resourceTypes.MNEData", "default", no_fail=True)[0]["id"],
            obfuscate=False,
        )
        return defaults["properties"]


class Acceptance:
    """
    Class holding logic for MNE ACCEPTANCE. (ensuring data from meraki portal matches what is in Salesforce)
    Methods have variable 'context' that is a string describing the component it is responsible for validating
    API calls should be validated with the validate_response method
    """

    def __init__(self, commonPlanObject):
        self.report = []  # list of strings describing all problems with
        self.expected_data = commonPlanObject.properties["expected_data"]
        self.netID = self.expected_data["nwid"]
        self.logger = commonPlanObject.logger
        self.bpo = commonPlanObject.bpo
        self.private_data = commonPlanObject.private_data
        self.exit_error = commonPlanObject.exit_error
        self.circuit_id = self.expected_data["cid"]
        self.report_rid = commonPlanObject.resource["id"]
        self.product_family = self.expected_data["product_family"]
        self.is_docsis = False  # will be changed later if 'docsis' is in network notes
        self.dashboardUrl = "https://api.meraki.com"
        self.apikey = self.private_data["apiKey"]
        self.baseURL = self.dashboardUrl + "/api/v1"
        self.org_id = ""
        self.remediation = []
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Cisco-Meraki-API-Key": self.apikey,
        }

        self.dashboard = meraki.DashboardAPI(self.apikey)

        self.get_org_and_net_info()
        # self.networkName = ''  # todo 2.7 netname = Device ID - Customer Street Address (elaborate?)

    def runAcceptance(self):
        """
        check that all firmware is up-to-date ( )
        check the network is correct
        confirm Remote IP's (2.14 - 2.15)
        confirm device name and address, cid (2.16 - 2.17)
        confirm connectivity (2.18)
        confirm all devices are filling all services requested and devices are configured properly
        confirm network SNMP settings (2.11 - 2.13)
        confirm firewall settings ()
        confirm CID in notes section
        :return: 'report' -> list of strings describing misconfigurations/errors, empty if none
        """
        try:
            # Commenting this out temporarily at customer request
            # self.check_firmware()
            self.check_network()
            self.check_device_configs()
            self.check_device_connectivity()
            self.check_org_snmp()
            self.check_network_snmp()
            # TODO: check firewall only if there "is" one?
            if self.expected_data["product_family"] == "MX":
                self.check_firewall_snmp()
        except Exception as e:
            self.logger.error(traceback.format_exc())
            self.report_error(
                "Cannot continue Acceptance check because of error: {}, aborting ...".format(str(e)), exit=True
            )
        self.record_report()
        self.record_remediation()
        return self.report

    def retrieve_network(self, nwid, ignore_error=True):
        # response = self.dashboard.networks.getNetwork(nwid)
        url = "{}/networks/{}".format(self.baseURL, nwid)
        response = requests.get(url=url, headers=self.headers)
        data = self.validate_api_response(response, context="Retrieving Network", ignore_error=ignore_error)
        self.logger.info(f"RETURNED FROM NW: {response.text}")
        if isinstance(data, int) or data == {}:
            return None
        else:
            return data

    def report_error(self, msg, exit=False):
        if msg is None or msg == "":
            return
        elif isinstance(msg, list):
            if len(msg) == 0:
                return
            self.report = self.report + [str(x) for x in msg]
        else:
            self.report.append(str(msg))
        if exit:
            self.record_report()
            self.exit_error(str(msg))

    def record_report(self):
        self.bpo.resources.patch_observed(self.report_rid, {"properties": {"report": self.report}})

    def record_remediation(self):
        self.bpo.resources.patch_observed(self.report_rid, {"properties": {"remediated_fields": self.remediation}})

    def get_org_and_net_info(self, retry=True):
        """
        Either set the net id and org id from the mdso resource, or use the granite UDA net id and query the org id
        """
        context = "Retrieving Meraki data"
        try:
            self.netID = self.expected_data["nwid"]
            attempt = [self.netID] if "_" in self.netID else [f"{prefix}_{self.netID}" for prefix in "LN"]
            for tmp_nid in attempt:
                network = self.retrieve_network(nwid=tmp_nid)
                if network:
                    self.netID = tmp_nid
                    url = f"{self.baseURL}/networks/{self.netID}"
                    response = requests.get(url, headers=self.headers)
                    data = response.json()
                    self.org_id = data.get("organizationId", "")
                    return True
            if not retry:
                if self.org_id == "":
                    self.org_id = self.getOrganizationId(self.expected_data['name'])
                    if not self.org_id:
                        message = "Incorrect Network ID provided and could not find the Org by name, exiting"
                        self.report_error(message, True)
                    nw_name = self.expected_data["CLLI"] + " - " + self.expected_data["address"]
                    self.logger.info(f"MATCHING ORG FOUND {self.org_id}, looking for: {nw_name}")
                    nwid = self.get_network_by_name(self.org_id, nw_name)
                    if nwid:
                        message = f"Matching network found different than provided NWID: {self.netID}, correct: {nwid['id']}"
                        self.logger.info(message)
                        self.netID = nwid['id']
                        self.remediation.append(message)
                        return True
                message = (
                    f"{context} - Incorrect Network ID. Provided: {self.netID} Tried: {tmp_nid} and {tmp_nid}"
                )
                self.report_error(message)
                self.record_report()
                return False
            self.headers['X-Cisco-Meraki-API-Key'] = self.private_data["apiKey2"]
            return self.get_org_and_net_info(False)

        except Exception as e:
            self.logger.error(traceback.format_exc())
            message = f"{context} - An Exception occurred: {e}"
            self.report_error(message, exit=True)

    def getOrganizationId(self, organizationName):
        """Returns the organization ID if it exists. Otherwise Return False"""
        organizations = self.dashboard.organizations.getOrganizations()
        for org in organizations:
            if org["name"].upper() == organizationName.upper():  # Check if name matches
                return org["id"]
        return False

    def get_network_by_name(self, org_id, net_name):
        existing_nets = self.dashboard.organizations.getOrganizationNetworks(org_id)
        for net in existing_nets:
            if net["name"].upper() == net_name.upper():
                self.logger.info(
                    f"We found a network with name: {net_name} in the organization"
                )
                return net
        return False

    def validate_api_response(self, response, context, ignore_error=True):
        """
        Validates that a response from the requests' library is valid.
        A request is invalid if the response code is not 2xx,
        or if the response is empty without the ignore_empty_response set to True
        :param response: requests library Response object
        :param ignore_empty_response: ignore errors raised if the response is empty json
        :param context: What the caller is doing to be provided as information in the event of an error
                        (ex: context='validating SNMP settings)
        :return: None
        """
        self.logger.info("Getting data for: {} from: Meraki Dashboard".format(context))
        try:
            data = response.json()
            return data
        except Exception:
            if ignore_error:
                return {}
            else:
                self.report_error(
                    "FAILED API CALL IN CONTEXT: {} -- {} Status code from Meraki Dashboard"
                    .format(context, response.status_code),
                    exit=True,
                )

    def check_firmware(self):
        """
        checks that the firmware is up-to-date by examining if:
         firmware['currentVersion'] is in firmware['availableVersions']
        """

        def firmware_prod_family(firmware_pf):
            if "appliance" in firmware_pf:
                return "MX"
            elif "wireless" in firmware_pf:
                return "MR"
            elif "camera" in firmware_pf:
                return "MV"
            elif "switch" in firmware_pf:
                return "MS"
            else:
                return "NA"

        context = "Firmware"
        # url = "{}/networks/{}/firmwareUpgrades".format(self.baseURL, self.netID)
        # response = requests.get(url=url, headers=self.headers)
        data = self.dashboard.networks.getNetworkFirmwareUpgrades(self.netID)
        products = data["products"]
        self.logger.info(f"GetNetworkFirmwareUpgrades Response: {data}")
        # get the data for the correct product family
        firmware_data = [
            prod_data
            for prod_key, prod_data in products.items()
            if firmware_prod_family(prod_key) == self.product_family
        ]
        if len(firmware_data) > 1:
            current = firmware_data[0]["currentVersion"]["firmware"]
            available = firmware_data[0]["availableVersions"]
            available = [x["firmware"] for x in available]
            if current not in available:
                message = "{} - Out of date firmware for {} - current version: {}, available:" " {}".format(
                    context, self.product_family, current, available
                )
                self.report_error(message)
        else:
            self.logger.info("No matching product family found in FW Upgrade Response")

    def check_network(self):
        """
        Checks Network settings
        https://developer.cisco.com/meraki/api-v1/#!get-device
        """
        # context = "Network"

        # get network data for network
        data = self.retrieve_network(nwid=self.netID)

        # todo???
        # check that the net name is what is expected (granite data implied, not directly in records)
        # if data['name'] != self.networkName:
        #     msg = '{} - Network name does not match what is expected. Expected: {}, observed:' \
        #           ' {}'.format(context,self.networkName, data['name'])
        #     self.report_error(msg)

        # if self.circuit_id not in data['notes']:
        #     msg = '{} - Network notes does not contain circuit id. Observed notes: {}'.format(context, data['notes'])
        #     self.report_error(msg)

        # todo, 2.17, write circuit info from notes?

        # todo, if the notes are not written above, are we getting this from salesforce
        if "notes" in data and data.get("notes", "") is not None and "DOCSIS" in data.get("notes", "").upper():
            self.is_docsis = True

    def validate_device_name_(self, device_name, clli, model_code):
        tmp_name = device_name.replace("-", "")
        n = len(clli) + 4
        tmp_name = tmp_name[:n]

        # is clli in name
        if clli in tmp_name:
            tmp_name = tmp_name.replace(clli, "")
        else:
            return False

        # is model type in device name
        if model_code in tmp_name:
            tmp_name = tmp_name.replace(model_code, "")
        elif model_code == "MX" and "MN" in tmp_name:
            # todo: MN for mx?
            tmp_name = tmp_name.replace("MN", "")
        else:
            return False

        # is the only thing left in the name the device index number
        if tmp_name.isnumeric():
            return True
        else:
            return False

    def validate_address_(self, device_address, expected_address):
        """
        validates that all major parts of the device address are in that expected address which may contain
        more information that device address like city state and zip
        """
        tmp_address_expected = expected_address.replace(",", "").upper()
        tmp_address_expected = tmp_address_expected.replace(".", "")
        tmp_address_expected.replace("-", "")

        tmp_device_address = device_address.replace(",", "").upper()
        tmp_device_address = tmp_device_address.replace(".", "")
        tmp_device_address.replace("-", "")

        tmp_address_expected = tmp_address_expected.split(" ")
        tmp_device_address = tmp_device_address.split(" ")

        # todo ensure this is okay
        return (
            all([da_ in tmp_address_expected for da_ in tmp_device_address])
            or all([oa_ in tmp_device_address for oa_ in tmp_address_expected])
        ) and (len(tmp_address_expected) > 1 and len(tmp_device_address) > 1)

    def check_device_configs(self):
        """
        checks status of devices in org. ensurese there is a 1-1 correlation between devices in the network and services
        ordered as shown in granite parent managed services.
        this also checks all mx devices and ensures all have a proper tid
        # todo: ensure that all devices are correct model
        Will also check notes section for CID in notes section ONLY if it's an MX
        :return: bool, pass or fail
        """
        context = "Device Configs"

        # url = "{}/networks/{}/devices".format(self.baseURL, self.netID)
        # response = requests.get(url=url, headers=self.headers)
        data = self.dashboard.networks.getNetworkDevices(self.netID)
        prod_family_devices = []

        # TODO ITERATIVE TID CHECK FOR VARIOUS DIFFERENT TYPES OF DEVICES:
        # CLLI + MN/MS/MR/[int] CAMERAS: TID CAN CHANGE/WILL NOT BE CONSISTENT. UNSURE WHAT DO

        for device in data:
            model_code = device["model"][:2]
            model_code = "MX" if model_code == "MN" else model_code

            if model_code != self.expected_data["product_family"]:
                continue
            else:
                prod_family_devices.append(device)

            name = device.get("name", "(unnammed) " + device["serial"])
            address = device.get("address", "NO ADDRESS")
            notes = device.get("notes", "NO NOTES")

            if model_code == "MX" and (self.expected_data["cid"] not in notes):
                self.dashboard.devices.updateDevice(device["serial"], notes=self.expected_data["cid"])
                self.remediation.append(
                    "{} - correct CID missing from notes section of the MX. Observed: {}".format(
                        context, notes)
                )
            # validate device name follows proper naming convention
            if not self.product_family != "MV":
                if not self.validate_device_name_(name, clli=self.expected_data["CLLI"], model_code=model_code):
                    self.report_error(
                        "{} - Device name does not follow [CLLI][model][int id] format. Expected: {}, Observed: "
                        "{}".format(context, self.expected_data["CLLI"] + model_code + "**", name)
                    )

            # validate the address
            if not self.validate_address_(device_address=address, expected_address=self.expected_data["address"]):
                self.report_error(
                    "{} - Device {} address does not match what is in granite record. address "
                    "from granite: {}, Observed: {}".format(
                        context, name, self.expected_data["address"], address if address != "" else None
                    )
                )

        # outside loop
        if len(prod_family_devices) < self.expected_data["quantity"]:
            message = "{} - fewer devices in network that expected. Expected {}, found: {}".format(
                context, self.expected_data["quantity"], len(prod_family_devices)
            )
            self.report_error(message)

    def check_device_connectivity(self):
        """
        Checks connectivity of device by seeing if its status is 'online'
        https://developer.cisco.com/meraki/api-v1/#!api-reference-early-access-api-platform-monitor-devices-
        """
        context = "Device connectivity"
        # url = "{}/organizations/{}/devices/statuses".format(self.baseURL, self.org_id)
        # response = requests.get(url=url, headers=self.headers)
        data = self.dashboard.organizations.getOrganizationDevicesStatuses(self.org_id, total_pages="all")
        try:
            for device in data:
                if device["networkId"] == self.netID:
                    if device["status"] != "online":
                        if device["name"]:
                            self.report_error(
                                '{} - Device: {} connectivity status is not "online". \
                                    Expected: "online", observed: "{}"'.format(
                                    context, device.get("name", "NAME NOT AVAILABLE"), device["status"]
                                )
                            )
        except KeyError as ke:
            self.report_error("{} - Response dict key: {} not found ".format(context, ke))

    def check_org_snmp(self):
        """
        2.11
        https://developer.cisco.com/meraki/api-v1/#!get-organization-snmp
        """
        context = "Organization SNMP"
        # url = "{}/organizations/{}/snmp".format(self.baseURL, self.org_id)
        # response = requests.get(url=url, headers=self.headers)
        data = self.dashboard.organizations.getOrganizationSnmp(self.org_id)
        try:
            if not data["v3Enabled"]:
                message = "{} - v3Enabled is set to: {}".format(context, data["v3Enabled"])
                set_v3 = True
                self.remediation.append(message)
            # todo: should data INCLUDE expected ips or exclusively BE expected?
            expected_ips = {"70.125.123.72", "98.6.16.112", "70.125.123.47"}
            excluded_ips = expected_ips - set(data["peerIps"])
            if not len(excluded_ips) == 0:
                message = "{} - missing ip(s): {}".format(context, excluded_ips)
                self.logger.info(f"updating Org SNMP with V3: {set_v3} and peer_ip's: {expected_ips}")
                self.dashboard.organizations.updateOrganizationSnmp(self.org_id, v3Enabled=set_v3, peerIps=list(expected_ips))
                self.remediation.append(message)
        except KeyError as ke:
            self.report_error("{} - Response dict key: {} not found ".format(context, ke))

    def check_network_snmp(self):
        """
        2.13
        https://developer.cisco.com/meraki/api-v1/#!get-network-snmp
        """
        context = "Network SNMP"
        # url = "{}/networks/{}/snmp".format(self.baseURL, self.netID)
        # response = requests.get(url=url, headers=self.headers)
        data = self.dashboard.networks.getNetworkSnmp(self.netID)
        try:
            if data["access"] == "users":
                users = data["users"][0]
                if not (len(users["username"]) > 0 and len(users["passphrase"]) > 0):
                    self.report_error("{} - Username or passphrase not populated".format(context))
            else:
                self.remediation.append("{} - Access not set to username/passphrase".format(context))
                self.dashboard.networks.updateNetworkSnmp(self.netID, access='users',
                                                          users=[{"username": "un1f13dMNE", "passphrase": "dmZadm1N"}])
        except KeyError as ke:
            self.report_error("{} - Response dict key: {} not found ".format(context, ke))

    def check_firewall_snmp(self):
        """
        2.15
        https://developer.cisco.com/meraki/api-v1/#!get-network-appliance-firewall-firewalled-services
        Checks for Spectrum SNMP Ip's being allowed through the FW
        """
        context = "Security and SD_WAN Firewall"
        # url = "{}/networks/{}/appliance/firewall/firewalledServices".format(self.baseURL, self.netID)
        # response = requests.get(url=url, headers=self.headers)
        data = self.dashboard.appliance.getNetworkApplianceFirewallFirewalledServices(self.netID)
        snmp_settings = [x for x in data if x["service"] == "SNMP"][0]
        try:
            if not snmp_settings["access"] in ["restricted", "allowed"]:
                self.report_error(
                    '{} - SNMP access is {}, expected: "restricted" or "allowed"'.format(
                        context, snmp_settings["access"]
                    )
                )

            expected_ips = {"70.125.123.72", "98.6.16.112", "70.125.123.47"}
            given_ips = set(snmp_settings["allowedIps"])
            if not expected_ips == given_ips:
                self.report_error(
                    "{} - SNMP allowed ips do not match. Expected: {}, Observed:"
                    " {}.".format(context, expected_ips, given_ips)
                )
        except KeyError as ke:
            self.report_error("{} - Response dict key: {} not found ".format(context, ke))


class Terminate(CommonPlan):
    def process(self):
        pass
