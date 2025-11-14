from scripts.common_plan import CommonPlan
import requests as rqst
import traceback
from datetime import datetime
import ipaddress
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
        auditor = Compliance(self)
        if auditor.org_id:
            auditor.runCompliance()
        # report already recorded to resource

    def get_private_data(self):
        defaults = self.bpo.resources.get(
            self.get_resources_by_type_and_label("charter.resourceTypes.MNEData", "default", no_fail=True)[0]["id"],
            obfuscate=False,
        )
        return defaults["properties"]


class Compliance:
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
        self.dashboardUrl = "https://n109.meraki.com"
        self.apikey = self.private_data["apiKey"]
        self.baseURL = self.dashboardUrl + "/api/v1"
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Cisco-Meraki-API-Key": self.private_data["apiKey"],
        }
        self.org_id = ""
        self.dashboard = meraki.DashboardAPI(self.apikey)
        self.get_org_and_net_info()

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

    def runCompliance(self):
        """
        Compliance requires: Account Number, Device TID/ID and IP from MP.
        Steps:
        1- Verify Org SAML Admin roles include customer account number from Granite
        Ex: ACT-12345678_Full and Read-Only
        2- Verify TID(s) and public IPs of devices in granite vs MP
        3- Set Circuit to Live in Granite.
        TODO: Bulk Updates vs ones that do not allow it in Granite (Finished Internet/BYON/DOCSIS/HSD),
        set whole ckt live.
        """
        try:
            self.check_account_roles()
            prod_fam_devices = self.check_devices()
            if "public_ip_block" in self.expected_data.keys():
                self.check_public_ips(prod_fam_devices)
            self.check_licenses()
            self.record_report()

        except Exception as e:
            self.logger.error(traceback.format_exc())
            self.report_error(
                "Cannot continue compliance check because of error: {}, aborting ...".format(str(e)), exit=True
            )
        return self.report

    def check_account_roles(self):
        """
        :Get Organization SAML roles and check against Granite Account #
        :If not found, create FUll and R/O account
        :If Generic account is found, return fail.
        :return: bool, pass or fail.
        """
        context = "Check SAML Admin roles"
        # url = "{}/organizations/{}/samlRoles".format(self.baseURL, self.org_id)
        # response = requests.get(url=url, headers=self.headers)
        data = self.dashboard.organizations.getOrganizationSamlRoles(self.org_id)
        account = self.expected_data["account_number"].upper()
        self.logger.info(f"\nDATA: {data}\n")
        generics = []
        for suffix in ["_FULL", "_READ-ONLY"]:
            found_account = False
            for role in data:
                if "ACCT-XXXXXXXXX" in role["role"].upper():
                    self.logger.info(f"Generic ACCT found: {role['role'].upper()}")
                    generics.append(role["role"])
                elif role["role"].upper() == account + suffix:
                    found_account = True if not found_account else found_account
            # IF duplicates are not found AND proper saml acct for ACCT provided is not found, create.
            if not found_account:
                self.logger.info(f"Adding missing SAML role: {account + suffix}")
                try:
                    add_response = self.dashboard.organizations.createOrganizationSamlRole(self.org_id, account + suffix, suffix[1:].lower())
                    self.logger.info(f"Add response:{add_response}\n ")
                except Exception as e:
                    self.report_error("{} - Unable to add SAML Role {} Missing from org:{}".format(context, account + suffix, e))
        if generics:
            generics = set(generics)
            self.report_error("{} - Generic Accounts found: {}".format(context, generics))

    def check_public_ips(self, prod_tids):
        """
        :Get all device information in Network and check for IP information.
        :return: bool, pass or fail
        """
        # url = "{}/organizations/{}/devices/uplinks/addresses/byDevice".format(self.baseURL, self.org_id)
        # response = requests.get(url=url, headers=self.headers)
        # data = self.validate_api_response(response, context=context)
        data = self.dashboard.organizations.getOrganizationDevicesUplinksAddressesByDevice(self.org_id, total_pages="all")
        provided_ip = self.expected_data.get("public_ip_block")  # Use .get() to avoid KeyError
        data = [device for device in data if device["network"]["id"] == self.netID and device["name"].strip() in prod_tids]
        uplink_addresses = [port["addresses"][0]["public"]["address"] for device in data for port in device["uplinks"] if port["addresses"]]

        # If no public IPs are observed, report an error
        if not uplink_addresses:
            self.report_error(f"WAN/Public IP Error - No Public IP observed from Meraki Portal. Expected: {provided_ip}")
            return False

        # If public IP wasn't provided due to missing data, allow pass
        if not provided_ip:
            return True

        if any(ip in self.validate_ip(provided_ip) for ip in uplink_addresses):
            return True
        else:
            self.report_error(
                f"WAN/Public IP error - WAN IP Mismatch. Expected: {provided_ip}, Observed: {uplink_addresses}"
            )
        return False

    def validate_ip(self, expected):
        return [str(host) for host in ipaddress.ip_network(expected).hosts()]

    def check_devices(self, name_only=True):
        """
        :Get all device information in Network and check for IP information.
        :return: bool, pass or fail
        """
        # url = "{}/networks/{}/devices".format(self.baseURL, self.netID)
        # response = requests.get(url=url, headers=self.headers)
        # data = self.validate_api_response(response, context=context)
        data = self.dashboard.networks.getNetworkDevices(self.netID)
        self.logger.info(f"Devices_response: {data}")
        prod_family_devices = []

        for device in data:
            model_code = device["model"][:2]
            model_code = "MX" if model_code == "MN" else model_code
            name = device.get("name", "(unnammed) " + device["serial"])
            name = name.strip() if name else name

            if model_code != self.expected_data["product_family"]:
                continue
            else:
                if name_only:
                    prod_family_devices.append(name)
                else:
                    prod_family_devices.append({"name": name, "serial": device["serial"]})

            # validate device name follows proper naming convention
            if self.product_family == "MX":
                if not self.validate_device_name_(name, clli=self.expected_data["CLLI"]):
                    self.report_error(
                        "{} - CLLI {} Not found within Device Name {}. ".format("TID/Device ID error", self.expected_data["CLLI"], name))
        return prod_family_devices

    def check_licenses(self):
        """
        :Method will update parent resource with TIDs with licenses assigned that are expiring in 40 days.
        """
        # url = "{}/organizations/{}/inventory/devices?networkId={}".format(self.baseURL, self.org_id, self.netID)
        # response = requests.get(url=url, headers=self.headers)
        # data = self.validate_api_response(response, context=context)
        data = self.dashboard.organizations.getOrganizationInventoryDevices(self.org_id, total_pages='all')
        expiring_serials = []
        self.logger.info(f"LICENSE CHECK RESPONSE: {data}")
        for device in data:
            if device.get("licenseExpirationDate"):
                if (datetime.strptime(device["licenseExpirationDate"][:10], "20%y-%m-%d") - datetime.now()).days < 40:
                    expiring_serials.append(device["serial"])
        # expiring_serials = [device["deviceSerial"] for device in data if isinstance(device.get("totalDurationInDays"),
        #   int) and device.get("totalDurationInDays") < 1096]
        prod_devices_with_serial = self.check_devices(False)
        for device in prod_devices_with_serial:
            if device["serial"] in expiring_serials:
                self.report_error(
                    "{} - Device found provisioned with license expiring within 40 days. TID: {},"
                    " Serial:{}".format("License issue in network", device["name"], device["serial"])
                )

    def retrieve_network(self, nwid, ignore_error=True):
        url = "{}/networks/{}".format(self.baseURL, nwid)
        response = requests.get(url=url, headers=self.headers)
        data = self.validate_api_response(response, context="Retrieving Network", ignore_error=ignore_error)
        if isinstance(data, int) or data == {}:
            return None
        else:
            return data

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
                    data = self.validate_api_response(response, context, ignore_error=True)
                    if isinstance(data, dict) and "organizationId" in data:
                        self.org_id = data["organizationId"]
                        return True
                    else:
                        self.logger.error(f"Unexpected response format. Expected dictionary, got: {type(data)} | Value: {data}")
                        continue
                        # Continue to next loop. 2nd attempt failing after 1st succeeds would imply current meraki issue
            if not retry:
                message = (
                    f"{context} - Incorrect Network ID. Provided: {self.netID} Tried: L_{self.netID}"
                    f" and N_{self.netID}"
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
        self.logger.info("Getting data for: {} from: {}".format(context, response.url))
        if int(response.status_code) // 100 != 2:
            if not ignore_error:
                self.report_error(
                    "FAILED API CALL IN CONTEXT: {} -- {} Status code from "
                    "{}".format(context, response.status_code, response.url),
                    exit=True,
                )
            else:
                return response.status_code
        else:
            try:
                data = response.json()
                return data
            except Exception:
                if ignore_error:
                    return {}
                else:
                    self.report_error(
                        "FAILED API CALL IN CONTEXT: {} -- {} Status code from "
                        "{}".format(context, response.status_code, response.url),
                        exit=True,
                    )

    def validate_device_name_(self, device_name, clli):
        """
        Validate if the device name contains the expected CLLI (location identifier)
        :param device_name: Device name to validate
        :param clli: CLLI code from expected data
        :return: bool, True if valid, False if invalid
        """
        return clli in device_name.replace("-", "")


class Terminate(CommonPlan):
    def process(self):
        pass
