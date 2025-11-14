import re
import json
import time
import pyzipcode
import meraki
import datetime
import random
import functools
import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError


class DashboardAttributeErrorHandlingWrapper:
    """
    This class will replace the attributes in meraki.DashboardAPI so that we can apply
    custom error handling to them. The main issue that pushed for this implementation was the
    "502 Bag Gateway" error that is often raised by all endpoints ond only requires a retry to get around.
    Future error handling logic that we want applied to all API calls can be fitted into this class as well.
    """
    def __init__(self, original_attr, attr_name, logger, backoff_seconds=2, n_retries=3):
        self.attr_name = attr_name
        self.backoff_seconds = backoff_seconds
        self.retries = n_retries
        self.actual_instance = original_attr
        self.logger = logger
        self.logger.info(f'===== initialized wrapper for {self.attr_name}')

    def __getattr__(self, name):
        attr = getattr(self.actual_instance, name)
        if not callable(attr):
            # directly return attributes that are not callable
            return attr

        @functools.wraps(attr)
        def wrapper(*args, **kwargs):
            """
            This wraps all callable methods of the object
            """
            self.logger.info(f"===== {self.attr_name}.{name} called")
            self.logger.info(f"===== ARGS: {json.dumps(args, indent=4)}")
            self.logger.info(f"===== KWARGS: {json.dumps(kwargs, indent=4)}")
            for attempt_no in range(self.retries):
                try:
                    return attr(*args, **kwargs)
                except meraki.exceptions.APIError as api_error:
                    """
                    API errors usually come back as meraki.exceptions.APIError but we only care about retrying
                    specific errors. If the conditions for the errors we are looking for are not met, we re-raise
                    the error and let the caller handle it
                    """
                    self.logger.error(
                        f"===== Error occurred while calling {self.attr_name}.{name}"
                        f" on attempt {attempt_no+1}:\n{api_error.args}"
                    )
                    if attempt_no + 1 == self.retries:
                        # raise this error if we are out of retries
                        self.logger.error(f"===== Out of retries for calling {name}")
                        raise api_error
                    elif "502 Bad Gateway" in str(api_error.args):
                        # 502 Bad Gateway, {'errors': ['Internal server error']}
                        self.logger.error("===== Handling 502 bad gateway error, retrying")
                        # wait before we try again
                        time.sleep(self.backoff_seconds)
                        continue
                    else:
                        # raise this error if it was not explicitly checked for
                        self.logger.error("===== Error is unknown, raising to caller")
                        raise api_error
        return wrapper


class MerakiDashboard:
    def __init__(
        self,
        apiKey,
        logger,
        exit_error,
        bpo=None,
        rid=None,
        serial_db_auth=None
    ):
        logger.info("===== initializing meraki dashboard")
        self.rid = rid
        self.bpo = bpo
        self.logger = logger
        self.exit_error_passed = exit_error
        self.issues = []
        self.current_device = ""
        self.current_device_model = ""
        self.default_qnr_camera_profile_id = None
        self.missing_licenses = []
        self.record_to_resource = False
        self.ignore_warnings = True
        self.dashboard = meraki.DashboardAPI(apiKey, output_log=False)
        self.api_key = apiKey
        self.wrap_meraki_library_attributes()

        if serial_db_auth:
            self.serial_db_auth = HTTPBasicAuth(serial_db_auth["username"], serial_db_auth["password"])
        else:
            self.serial_db_auth = None

    def wrap_meraki_library_attributes(self):
        """
        this will wrap the attributes of self.dashboard used for making API calls. Please review the doc string
        for DashboardAttributeErrorHandlingWrapper above for any questions about why this is implemented
        """
        attributes = [
            'administered',
            'organizations',
            'networks',
            'devices',
            'appliance',
            'camera',
            'cellularGateway',
            'insight',
            'licensing',
            'sensor',
            'sm',
            'switch',
            'wireless'
        ]
        for attribute in attributes:
            self.logger.info(f"wrapping meraki dashboard library attribute {attribute}")
            wrapper = DashboardAttributeErrorHandlingWrapper(
                original_attr=self.dashboard.__getattribute__(attribute),
                attr_name=attribute,
                logger=self.logger
            )
            self.dashboard.__setattr__(attribute, wrapper)

    def log_issue(self, external_message, internal_message, api_response="", code=2000, details="", category=0):
        """
        :param external_message: string describing the issue encountered, includes information that can vary such as
        port number or vlan id
        :param internal_message: Used for reporting. does not include variables so that messages can be aggregated
        :param api_response: (optional) api error response from meraki api
        :param details: non-important details that may be helpful for debugging later
        :param category: see `broad_categories`
        :param code: Error code.
         Default (not provided): 2000
         Things that will not cause a failed status: 1xxx
         Non-critical issues that cause a failed status but do not result in halting automation: 2xxx
         Critical issue that does result in halting automation: 3xxx
        """
        broad_categories = {
            0: "Not Provided",
            1: "Design Configuration",
            2: "API / Network Error",
            3: "User Error",
            4: "Missing Licenses",
            5: "Logical Errors"
        }
        if category not in broad_categories.keys():
            category = 0
        record = {
            "current_device": self.current_device,
            "current_device_model": self.current_device_model,
            "external_message": external_message,
            "internal_message": internal_message,
            "api_response": str(api_response),
            "code": code,
            "details": details.replace("|", ";"),  # replace pipe to avoid issues with splunk
            "subcategory": broad_categories[category]
        }
        self.issues.append(record)
        if code // 1000 == 3:
            self.finish()

    def finish(self):
        self.logger.info("FINISHING RESOURCE")
        if len(self.missing_licenses) > 0:
            self.log_issue(
                external_message=f"Could not find licenses for {self.missing_licenses}",
                internal_message="Some requested licenses are missing",
                api_response="",
                code=1001,
                details="",
                category=4
            )
        status = "Success"
        codes = [x["code"] // 1000 for x in self.issues]
        messages = [x["external_message"] for x in self.issues]
        messages = "; ".join(messages)
        if len(self.issues) > 0:
            if 2 in codes or 3 in codes:
                status = "Failed"
        update_payload = {
            "properties": {
                "configurations": {
                    "issues": self.issues,
                    "status": status
                }
            }
        }
        self.logger.info(f"updating the resource info with: {update_payload}")
        self.bpo.resources.patch_observed(self.rid, update_payload)
        if status == "Failed":
            self.exit_error_passed(messages)

    def clean_string(self, s, default=""):
        if not s or s == "":
            return default
        else:
            s = s.lower().replace(" ", "").replace("\n", "").replace("\t", "")
            s = "any" if s == "all" else s
            return s

    def replace_escape_chars(self, s):
        s = s.strip().replace(" ", ",").replace("\n", ",").replace("\t", ",")
        s = re.sub(r'\\(n|t)', ',', s)
        return s

    def get_template_and_inventory_orgs(self, mne_data):
        """
        Gets the organization id of org used to store licenses, and randomly select a template org id to use
        as the clone org for new organizations.
        :param mne_data: MNEData resource info
        :return:
        """
        try:
            inventory_org = mne_data["properties"]["SecurityAppliances"]["InventoryOrgId"]
            template_orgs = mne_data["properties"]["SecurityAppliances"]["TemplateOrgIds"]
            template = random.choice(template_orgs)
            self.logger.info(f"choosing template org {inventory_org}")
            self.logger.info(f"inventory org {template}")
            return {
                "inventory": inventory_org,
                "template": template
            }
        except Exception as e:
            self.log_issue(
                external_message="Failed to get the license inventory and template org ids",
                internal_message="Failed to get the license inventory and template org ids",
                api_response=e.args,
                code=3018,
                category=5
            )

    def get_timezone(self, code):
        """
        :param code: either a state code or zipcode
        :type code: str
        :return: timezone
        """
        offset_to_tz = {
            -5: "America/New_York",
            -6: "America/Chicago",
            -7: "America/Denver",
            -8: "America/Los_Angeles",
        }
        if code.isnumeric():
            try:
                zcdb = pyzipcode.ZipCodeDatabase()
                if zcdb[code].state == "AZ":
                    return "US/Arizona"
                else:
                    return offset_to_tz[zcdb[code].timezone]
            except Exception as e:
                self.log_issue(
                    external_message=f"Failed to retrieve timezone for {code}. defaulting to America/Los_Angeles",
                    internal_message="Failed to retrieve timezone",
                    api_response=e.args,
                    code=2078,
                    details=f"code={code}",
                    category=1
                )
                return "America/Los_Angeles"  # Default value if not a valid State
        else:
            # then code should be a state
            timezones = {
                "EST": [
                    "CT",
                    "DE",
                    "FL",
                    "GA",
                    "KY",
                    "ME",
                    "MD",
                    "MA",
                    "MI",
                    "NH",
                    "NJ",
                    "NY",
                    "NC",
                    "OH",
                    "PA",
                    "RI",
                    "SC",
                    "VT",
                    "VA",
                    "WV",
                ],
                "CST": [
                    "AL",
                    "AR",
                    "IL",
                    "IA",
                    "LA",
                    "MN",
                    "MS",
                    "MO",
                    "OK",
                    "TN",
                    "TX",
                    "WI",
                ],
                "SST": ["AZ"],
                "MST": ["CO", "KS", "MT", "NE", "NM", "ND", "SD", "UT", "WY"],
                "PST": ["CA", "ID", "NV", "OR", "WA"],
                "HST": ["AK", "HI"],
            }
            cityTimezone = {
                "EST": "America/New_York",
                "CST": "America/Chicago",
                "SST": "US/Arizona",
                "MST": "America/Denver",
                "PST": "America/Los_Angeles",
                "HST": "Pacific/Honolulu",
            }
            for timezone, states in timezones.items():
                if code in states:
                    return cityTimezone[timezone]
            self.log_issue(
                external_message=f"Failed to retrieve timezone for {code}. defaulting to America/Los_Angeles",
                internal_message="Failed to retrieve timezone",
                api_response="",
                code=2077,
                details=f"code={code}",
                category=1
            )
            return "America/Los_Angeles"  # Default value if not a valid State

    def log_missing_license(self, device_name):
        self.missing_licenses.append(device_name)

    def create_vlans(self, nw_id, vlans=None):
        for vlan in vlans:
            self.logger.info("configuring VLAN\n")
            self.logger.info(json.dumps(vlan, indent=4))
            if vlan.get("dnsNameservers", False):
                self.logger.info(f'Updating dnsNameservers. Before: {vlan["dnsNameservers"]}')
                vlan["dnsNameservers"] = vlan["dnsNameservers"].replace(" ", "").replace(",\n", "\n").replace(",", "\n")
                self.logger.info(f'After: {vlan["dnsNameservers"]}')
            existing_vlans = self.getNetworkVlans(nw_id)
            self.logger.info(f"vlan {vlan['id']}")
            # is there another vlan with this mx ip?
            if vlan["applianceIp"] not in [x["applianceIp"] for x in existing_vlans]:
                # if not, just create the new one
                if vlan["id"] not in [x["id"] for x in existing_vlans]:
                    self.createNetworkApplianceVlan(nw_id, vlan)
                time.sleep(1)
                success = self.update_vlan(nw_id, vlan=vlan)
                if not success:
                    # if we fail to update the vlan, we want to enable DHCP so other things dont fail
                    self.logger.info(f"fall back update for vlan: {vlan['id']}")
                    defaults = {
                        "id": vlan["id"],
                        "dhcpHandling": "Run a DHCP server"
                    }
                    success = self.update_vlan(nw_id, vlan=defaults)
                    if not success:
                        self.logger.info("failed to update defaults")
            else:
                # if so, is it actually the same vlan
                contested_existing_vlan = [
                    x for x in existing_vlans if x["applianceIp"] == vlan["applianceIp"]
                ][0]
                self.logger.info(
                    f"vlan {contested_existing_vlan['id']} is contesting with subnet {contested_existing_vlan['subnet']}"
                )
                if contested_existing_vlan["id"] == vlan["id"]:
                    # if so just update it
                    success = self.update_vlan(nw_id, vlan=vlan)
                    if not success:
                        # if we fail to update the vlan, we want to enable DHCP so other things dont fail
                        self.logger.info(f"fall back update for existing vlan: {vlan['id']}")
                        defaults = {
                            "id": vlan["id"],
                            "dhcpHandling": "Run a DHCP server"
                        }
                        self.update_vlan(nw_id, vlan=defaults)
                else:
                    # otherwise, see if the existing vlan is expected to be provisioned:
                    if contested_existing_vlan["id"] != 1:
                        self.log_issue(
                            external_message=f"vlan {contested_existing_vlan['id']} is preventing {vlan['id']} from being created due to overlapping subnet {contested_existing_vlan['subnet']}",
                            internal_message="vlan cannot be created due to another contesting vlan",
                            api_response="",
                            code=2076,
                            details=f"nw_id={nw_id}| contested_existing_vlan={contested_existing_vlan}| vlan={vlan}",
                            category=1
                        )
                        continue
                    # otherwise, give the contesting a temp ip
                    vl = {
                        "applianceIp": "0.0.0.1",
                        "subnet": "0.0.0.0/24",
                        "id": 1,
                    }
                    self.update_vlan(nw_id=nw_id, vlan=vl)
                    time.sleep(1)

                    # create new one
                    self.createNetworkApplianceVlan(nw_id, vlan=vlan)
                    time.sleep(1)
                    success = self.update_vlan(nw_id, vlan=vlan)
                    if not success:
                        # if we fail to update the vlan, we want to enable DHCP so other things dont fail
                        self.logger.info(f"fall back update for vlan: {vlan['id']}")
                        defaults = {
                            "id": vlan["id"],
                            "dhcpHandling": "Run a DHCP server"
                        }
                        self.update_vlan(nw_id, vlan=defaults)

                    # delete old
                    time.sleep(1)
                    self.delete_vlan(nw_id, contested_existing_vlan["id"])

    def getOrganizationId(self, organizationName):
        """Returns the organization ID if it exists. Otherwise Return False"""
        organizations = self.getOrganizations()
        for org in organizations:
            if org["name"].upper() == organizationName.upper():  # Check if name matches
                return org["id"]
        return False

    def get_organization_by_id(self, orgid):
        try:
            response = self.dashboard.organizations.getOrganization(
                organizationId=orgid
            )
        except meraki.exceptions.APIError:
            return False
        return response

    def getOrganizations(self):
        error_message = "Failed to connect to the meraki dashboard"
        n = 2000  # number of orgs we want to get at a time
        all_orgs = []
        url = f"https://api.meraki.com/api/v1/organizations?perPage={n}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        }
        payload = {"startingAfter": 0}
        while True:
            try:
                response = requests.get(url=url, headers=headers, data=payload)
                response.raise_for_status()  # raise HTTPError if non 200 status
                orgs = response.json()
                all_orgs.extend(orgs)
                if len(orgs) != n:
                    break
                last_org = orgs[-1]  # Grab the last entry in the returned org list
                last_org_id = last_org['id']
                last_org_name = last_org['name']
                self.logger.info(f'last org id: {last_org_id} and name is {last_org_name}')
                payload["startingAfter"] = f"{last_org_id}"
            except HTTPError:
                try:
                    # fallback, attempt to get the orgs we can with the dashboard
                    response = self.dashboard.organizations.getOrganizations()
                    return response
                except meraki.APIError as e:
                    self.log_issue(
                        external_message=error_message,
                        internal_message=error_message,
                        api_response=e.args,
                        code=3001,
                        details="",
                        category=2
                    )
                    return None
        return all_orgs

    def cloneOrganization(self, srcOrgId, name):
        """Create a new organization by cloning *Spectrum Clone"""
        try:
            response = self.dashboard.organizations.cloneOrganization(organizationId=srcOrgId, name=name)
            return response["id"]
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to clone organization",
                internal_message="Failed to clone organization",
                api_response=e.args,
                code=3002,
                details=f"srcOrgId={srcOrgId} | name={name}",
                category=2
            )

    @staticmethod
    def valid_exp_date(t, n_days=90):
        """
        Determines if a time (t) is further out in the future than n_days
        t = null means no exp date means return true
        :param t: string in format 'y-m-dTh:m:s9Z'
        :return: bool
        """
        if t is None:
            return True
        else:
            today = datetime.datetime.today()
            d, t = t.split("T")
            date = d.split("-")
            time24 = t.split(':')
            time24[2] = time24[2].split(".")[0]
            _time = datetime.datetime(
                int(date[0]),
                int(date[1]),
                int(date[2]),
            )
            return _time - today > datetime.timedelta(days=n_days)

    def get_license_ids(self, org_id, license_types):
        def get_missing_count(what_we_have):
            missing = {}
            for lic_type, needed_n in license_types.items():
                if lic_type not in what_we_have:
                    missing[lic_type] = needed_n
                else:
                    missing[lic_type] = needed_n - len(what_we_have[lic_type])
            s = "Unable to find the following licenses: "
            first = True
            for k, v in missing.items():
                if v > 0:
                    if first:
                        s = s + f"{k}({v})"
                        first = False
                    else:
                        s = s + f", {k}({v})"
            return s

        def get_licenses_page(startingAfter=None, state="unusedActive"):
            try:
                response = self.dashboard.organizations.getOrganizationLicenses(
                    org_id, startingAfter=startingAfter, state=state
                )
            except meraki.exceptions.APIError:
                return []
            return response

        def consolidate(new_licenses, existing_licenses={}):
            for lic in new_licenses:
                lt = lic["licenseType"].upper()
                lid = lic["id"]
                if MerakiDashboard.valid_exp_date(t=lic["expirationDate"]):
                    if lt not in existing_licenses:
                        existing_licenses[lt] = [lid]
                    else:
                        existing_licenses[lt].append(lid)
                else:
                    self.logger.info(f"{lt} license {lid} is expiring too soon")
            return existing_licenses

        if isinstance(license_types, dict):
            needed_licenses = license_types
        else:
            needed_licenses = {x: license_types.count(x) for x in set(license_types)}
        self.logger.info(
            f"licenses requested from meraki:\n{json.dumps(needed_licenses, indent=2)}"
        )
        licenses = {}
        last = None
        go_again = True
        states = ["unusedActive", "unused"]
        state_index = 0
        while go_again:
            self.logger.info(
                f"found:\n{json.dumps({x: len(v) for x, v in licenses.items()}, indent=4)}"
            )
            go_again = False
            new_licenses = get_licenses_page(last, state=states[state_index])
            if len(new_licenses) == 0:
                if states[state_index] != states[-1]:
                    state_index += 1
                    last = None
                    go_again = True
                    continue
                else:
                    self.log_issue(
                        external_message=f"{get_missing_count(licenses)}. Please check Meraki Dashboard",
                        internal_message="failed to find some licenses",
                        api_response="",
                        code=1003,
                        details="",
                        category=4
                    )
                    break
            licenses = consolidate(
                new_licenses=new_licenses,
                existing_licenses=licenses
            )
            for k, v in needed_licenses.items():
                if k not in licenses:
                    self.logger.info(
                        f"Requesting another batch of licenses. No {k} found, needed: {v}"
                    )
                    last = new_licenses[-1]["id"]
                    go_again = True
                    break
                elif v > len(licenses[k]):
                    self.logger.info(
                        f"Requesting another batch of licenses. insufficient {k}. "
                        f"Found: {len(licenses[k])}, needed: {v}"
                    )
                    last = new_licenses[-1]["id"]
                    go_again = True
                    break
            if go_again:
                if len(new_licenses) != 1000:
                    if states[state_index] != states[-1]:
                        state_index += 1
                        last = None
                        go_again = True
                        continue
                    else:
                        self.log_issue(
                            external_message=f"{get_missing_count(licenses)}. Please check Meraki Dashboard",
                            internal_message="failed to find some licenses",
                            api_response="",
                            code=1003,
                            details="",
                            category=4
                        )
                        break
        found_lics_for_log = {k: len(v) for k, v in licenses.items()}
        self.logger.info(f"found licenses:\n{json.dumps(found_lics_for_log, indent=2)}")
        self.logger.info(f"needed licenses:\n{json.dumps(needed_licenses, indent=2)}")

        returning_licenses = []
        for k, v in needed_licenses.items():
            # if any of the first 2 conditions are met, then we already know about it and passed the warning above
            if k not in licenses:
                continue
            elif v > len(licenses[k]):
                returning_licenses.extend(licenses[k])
            else:
                returning_licenses.extend(licenses[k][:v])
        return returning_licenses

    def get_licenses_from_inventory(self, org_id, params=None):
        if isinstance(params, dict):
            params = json.dumps(params)
        else:
            params = {}
        try:
            response = self.dashboard.organizations.getOrganizationLicenses(organizationId=org_id, **params)
            return response
        except (meraki.exceptions.APIError, AssertionError) as e:
            message = "Issue occurred getting licenses from inventory"
            self.log_issue(
                external_message=message,
                internal_message=message,
                api_response=e.args,
                code=2001,
                details=f"org_id={org_id}, params={str(params)}",
                category=4
            )
            return None

    def move_organization_licenses(self, orgId, licenseIds, inventory_org, n_tries=3, wait_interval=10):
        if len(licenseIds) == 0:
            return False
        if isinstance(licenseIds, str):
            licenseIds = [licenseIds]
        if not isinstance(licenseIds, list):
            self.log_issue(
                external_message="Issue moving licenses",
                internal_message="Issue moving licenses",
                api_response="",
                code=2079,
                details=f"orgId={orgId} | licenseIds={licenseIds}",
                category=6
            )
            return False
        self.logger.info(
            "Licenses: {} will be moved to the organization: {} ".format(
                licenseIds, orgId
            )
        )
        error_message = None
        for i in range(n_tries):
            try:
                time.sleep(wait_interval)
                self.dashboard.organizations.moveOrganizationLicenses(
                    organizationId=inventory_org,
                    destOrganizationId=orgId,
                    licenseIds=licenseIds
                )
                return True
            except (meraki.exceptions.APIError, AssertionError) as e:
                error_message = str(e.args)
                self.logger.info(
                    f"organization cannot be found yet. "
                    f"error {error_message} was received calling move license endpoint on attempt {i+1} of {n_tries}"
                    f" waiting {wait_interval} seconds before trying again"
                    f"\n-------------------------------------------------"
                )
        # if none of the attempts were successful, throw an error
        self.log_issue(
            external_message="Failed to move license(s)",
            internal_message="Failed to move license(s)",
            api_response=error_message,
            code=2002,
            details=f"org_id={orgId}, license_ids={str(licenseIds)}",
            category=2
        )
        return False

    def license_type(self, device_type, fail_if_not_found=False):
        lic_map = {
            "MR": "ENT",
            "MS120-24P": "MS120-24P",
            "MS120-8": "MS120-8",
            "MS120-8FP": "MS120-8FP",
            "MS125-48": "MS125-48",
            "MS125-48-HW": "MS125-48",
            "MS125-48FP": "MS125-48FP",
            "MS125-48FP-HW": "MS125-48FP",
            "MS125-48LP": "MS125-48LP",
            "MS210-24P": "MS210-24P",
            "MS210-48FP": "MS210-48FP",
            "MS210-48LP": "MS210-48LP",
            "MS210-48P": "MS210-48P",
            "MS225-24P": "MS225-24P",
            "MS225-48FP": "MS225-48FP",
            "MS225-48P": "MS225-48P",
            "MS250-24P": "MS225-24P",
            "MS250-48FP": "MS250-48FP",
            "MS250-48P": "MS250-48P",
            "MS350-24X": "MS350-24X",
            "MS350-48": "MS350-48",
            "MS350-48FP": "MS350-48FP",
            "MS390-24 SERIES": "MS390-24E",
            "MS390-48 SERIES": "MS390-48E",
            "MS410-16": "MS410-16",
            "MS425-16": "MS425-16",
            "MS425-16-HW": "MS425-16",
            "MS425-32": "MS425-32",
            "MS425-32-HW": "MS425-32",
            "MV": "MV",
            "MX105": "MX105-SEC",
            "MX250": "MX250-SEC",
            "MX450": "MX450-SEC",
            "MX68": "MX68-SEC",
            "MX85": "MX85-SEC",
            "MX95": "MX95-SEC",
            "Z3-HW": "Z3-ENT",
            "Z3C-HW": "Z3C-ENT",
            "VMX-S": "VMX-S-ENT",
            "VMX-M": "VMX-M-ENT",
            "VMX-L": "VMX-L-ENT",

            # new devices added March - 2025
            "MS130-8P": "MS130-CMPT",
            "MS130-24P": "MS130-24",
            "MS130-48P": "MS130-48",
            "MS130-24X": "MS130-24",
            "MS130-48X": "MS130-48",
            "MS130-8X": "MS130-CMPT",
            "MS130R-8P": "MS130-CMPT",
            "C9300-24P-M": "C9300-24E",
            "C9300-48P-M": "C9300-48E",
            "C9300-48S-M": "C9300-48E",
            "C9300L-48P-4X-M": "C9300-",
            "C9300L-24P-4X-M": "C9300-",
            "C9300L-48UXG-4X-M": "C930",
            "C9300X-12Y-M": "C9300-24E",
            "C9300X-24Y-M": "C9300-24",
        }
        query = device_type.upper()
        if "MV" in query:
            query = "MV"
        if "MR" in query:
            query = "MR"

        if query not in lic_map and fail_if_not_found:
            self.log_issue(
                external_message=f"Failed determine license type for: {device_type}",
                internal_message="Failed determine license type",
                api_response="",
                code=2003,
                details=f"device_type={str(device_type)}",
                category=1
            )
            return ""
        else:
            return lic_map[query]

    def create_webhooks(self, org_id, nwid):
        def _create_webhook_receiver(nwid):
            webhook_receiver_base = 'https://webhooks.uaa.chtrse.com/uaa-sbwl/webhook-listener/'
            response = self.dashboard.networks.createNetworkWebhooksHttpServer(
                nwid,
                f'uaa-{nwid}',
                f'{webhook_receiver_base}{org_id}',
                sharedSecret=org_id,
                payloadTemplate={'payloadTemplateId': 'wpt_00001', 'name': 'Meraki (included)'}
            )
            return response

        def _updateNetworkAlertSettings(nwid, webhook_id):
            response = self.dashboard.networks.getNetworkAlertsSettings(nwid)
            response['defaultDestinations']["httpServerIds"].append(webhook_id)
            self.dashboard.networks.updateNetworkAlertsSettings(
                nwid, defaultDestinations=response['defaultDestinations']
            )

        def _get_webhook_receivers(nwid):
            return self.dashboard.networks.getNetworkWebhooksHttpServers(nwid)

        try:
            self.logger.info("checking net {} for receiver".format(nwid))
            rcvr_name = f"uaa-{nwid}"
            receivers = _get_webhook_receivers(nwid)
            uaa_receiver_exists = any([x["name"] == rcvr_name for x in receivers])
            if not uaa_receiver_exists:
                self.logger.info(f"creating webhook receiver {rcvr_name}")
                webhook = _create_webhook_receiver(nwid=nwid)
                _updateNetworkAlertSettings(nwid, webhook['id'])
            else:
                self.logger.info("webhook receiver already exists")
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to create webhook receiver",
                internal_message="Failed to create webhook receiver",
                api_response=e.args,
                code=2110,
                details="",
                category=2
            )

    def get_existing_traffic_shaping_rules(self, nwid):
        try:
            response = self.dashboard.appliance.getNetworkApplianceTrafficShapingRules(nwid)
            rules = response['rules']
            return rules
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to get traffic shaping rules",
                internal_message="Failed to get traffic shaping rules",
                api_response=e.args,
                code=2110,
                details="",
                category=2
            )
            return []

    def update_traffic_shaping_rules(self, nwid):
        # Hard-coded expected payload
        default_rule = {
            "definitions": [
                {
                    "type": "ipRange",
                    "value": "66.81.240.0/20"
                },
                {
                    "type": "ipRange",
                    "value": "80.81.128.0/20"
                },
                {
                    "type": "ipRange",
                    "value": "103.44.68.0/22"
                },
                {
                    "type": "ipRange",
                    "value": "104.245.56.0/21"
                },
                {
                    "type": "ipRange",
                    "value": "185.23.248.0/22"
                },
                {
                    "type": "ipRange",
                    "value": "192.209.24.0/21"
                },
                {
                    "type": "ipRange",
                    "value": "199.68.212.0/22"
                },
                {
                    "type": "ipRange",
                    "value": "199.255.120.0/22"
                },
                {
                    "type": "ipRange",
                    "value": "208.87.40.0/22"
                },
                {
                    "type": "applicationCategory",
                    "value": {
                        "id": "meraki:layer7/category/16",
                        "name": "VoIP & video conferencing"
                    }
                }
            ],
            "perClientBandwidthLimits": {
                "settings": "ignore"
            },
            "dscpTagValue": 46,
            "priority": "high"
        }
        existing_rules = self.get_existing_traffic_shaping_rules(nwid)
        self.logger.info(f"existing traffic shaping rules: {existing_rules}")
        self.logger.info(f"default traffic shaping rules: {default_rule}")
        all_rules = existing_rules + [default_rule]
        new_rule_groups = []
        for rule_group in all_rules:
            if rule_group not in new_rule_groups:
                new_rule_groups.append(rule_group)
        rules = {
            "defaultRulesEnabled": True,
            "rules": new_rule_groups
        }
        try:
            self.dashboard.appliance.updateNetworkApplianceTrafficShapingRules(
                nwid,
                **rules
            )
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to update traffic shaping rules",
                internal_message="Failed to update traffic shaping rules",
                api_response=e.args,
                code=2109,
                details="",
                category=2
            )

    def getNetworkId(self, orgId, netName):
        """Verifies whether the network already exists or not"""
        networks = self.getNetworks(orgId)
        if "'" in netName:
            netName = netName.replace("'", "")
        if '"' in netName:
            netName = netName.replace('"', "")
        for network in networks:
            if network["name"].upper() == netName.upper():
                nw_id = network["id"]
                self.logger.info("Network {} exists with ID {}.".format(netName, nw_id))
                return nw_id
            continue
        return False

    def waitForNetwork(self, orgId, net_id, polls=7, dt=3):
        """Assumes call to create network was made, waits until net can be returned"""
        for i in range(polls):
            nets = self.getNetworks(orgId)
            if net_id in [n["id"] for n in nets]:
                return [n for n in nets if n["id"] == net_id][0]
            else:
                time.sleep(dt)
        return False

    def getNetworks(self, orgId):
        self.logger.info(f"Querying networks within organization: {orgId}")
        try:
            response = self.dashboard.organizations.getOrganizationNetworks(
                organizationId=orgId,
            )
            return response
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to find organization networks",
                internal_message="Failed to find organization networks",
                api_response=e.args,
                code=3004,
                details=f"orgId={orgId}",
                category=2
            )

    def getNetInfo(self, nwid):
        try:
            response = self.dashboard.networks.getNetwork(
                networkId=nwid,
            )
            return response
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to get network info",
                internal_message="Failed to get network info",
                api_response=e.args,
                code=2004,
                details=f"nwid={nwid}",
                category=2
            )
            return False

    def get_network_by_name(self, org_id, net_name):
        existing_nets = self.getNetworks(orgId=org_id)
        for net in existing_nets:
            if net["name"].upper() == net_name.upper():
                self.logger.info(
                    f"We found a network with name: {net_name} in the organization"
                )
                return net
        return False

    def createNetwork(self, orgId, networkName, timeZone, notes, is_vmx=False, template_id=None):
        """
        :return: nwid
        """
        network_id = ""
        productTypes = ["appliance", "switch", "wireless", "cellularGateway", "camera"]
        if is_vmx:
            productTypes = ["appliance"]
        payload = {
            "name": networkName,
            "timeZone": timeZone,
            "notes": notes,
            "productTypes": productTypes,
        }
        try:
            response = self.dashboard.organizations.createOrganizationNetwork(
                organizationId=orgId,
                **payload
            )
            network_id = response["id"]
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to create network",
                internal_message="Failed to create network",
                api_response=e.args,
                code=3005,
                details=f"orgId={orgId}",
                category=2
            )

        if template_id:
            self.bind_template(
                nwid=network_id,
                template_id=template_id
            )

        return network_id

    def bind_template(self, nwid, template_id):
        """
        we prefer to have auto bind set to True but this may cause issues.
        So if that fails, we will bind without it
        """
        try:
            self.dashboard.networks.bindNetwork(
                networkId=nwid,
                configTemplateId=template_id,
                autoBind=True
            )
        except (meraki.exceptions.APIError, AssertionError):
            self.logger.info("FAILED TO BIND TEMPLATE WITH AUTO-BIND, TRYING WITHOUT")
            try:
                self.dashboard.networks.bindNetwork(
                    networkId=nwid,
                    configTemplateId=template_id,
                    autoBind=False
                )
            except (meraki.exceptions.APIError, AssertionError) as e2:
                self.log_issue(
                    external_message="Failed to Bind newly created network to template",
                    internal_message="Failed to Bind newly created network to template",
                    api_response=e2.args,
                    code=2005,
                    details=f"nwid={nwid} | template_id={template_id}",
                    category=2
                )

    def siteToSiteVPN(self, nwid, vpn):
        try:
            self.dashboard.appliance.updateNetworkApplianceVpnSiteToSiteVpn(
                networkId=nwid,
                **vpn
            )
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to create site to site vpn",
                internal_message="Failed to create site to site vpn",
                api_response=e.args,
                code=2006,
                details=f"nwid={nwid} | vpn={vpn}",
                category=1
            )
            return False

    def vpn_peers(self, org_id, peers):
        try:
            response = self.dashboard.appliance.updateOrganizationApplianceVpnThirdPartyVPNPeers(
                organizationId=org_id,
                **peers
            )
            return response
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to update vpn 3rd party VPN peers",
                internal_message="Failed to update vpn 3rd party VPN peers",
                api_response=e.args,
                code=2007,
                details=f"org_id={org_id} | peers={peers}",
                category=1
            )

    def applianceVlans(self, nw_id, enable):
        try:
            self.dashboard.appliance.updateNetworkApplianceVlansSettings(
                networkId=nw_id,
                vlansEnabled=enable
            )
            return True
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to enable appliance VLANS",
                internal_message="Failed to enable appliance VLANS",
                api_response=e.args,
                code=2008,
                details=f"nw_id={nw_id} | enable={enable}",
                category=2
            )
            return False

    def delete_vlan(self, nw_id, vlid):
        try:
            self.dashboard.appliance.deleteNetworkApplianceVlan(
                networkId=nw_id,
                vlanId=vlid
            )
            return True
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message=f"Failed to delete default VLAN {vlid}",
                internal_message="Failed to delete default VLAN",
                api_response=e.args,
                code=2009,
                details=f"nw_id={nw_id} | vlid={vlid}",
                category=2
            )
            return False

    def createNetworkApplianceVlan(self, nw_id, vlan):
        self.logger.info(f"CREATING VLAN: {vlan['id']}")
        try:
            self.dashboard.appliance.createNetworkApplianceVlan(
                networkId=nw_id,
                **vlan
            )
            return True
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message=f"Failed to create appliance vlan {vlan['id']}",
                internal_message="Failed to create appliance vlan",
                api_response=e.args,
                code=2010,
                details=f"nw_id={nw_id} | vlan={vlan}",
                category=1
            )
            return False

    def update_vlan(self, nw_id, vlan):
        self.logger.info(f"UPDATING VLAN: {vlan['id']}")
        vlid = vlan["id"]
        try:
            self.dashboard.appliance.updateNetworkApplianceVlan(
                networkId=nw_id,
                vlanId=vlid,
                **vlan
            )
            return True
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message=f"Failed to update appliance vlan {vlan['id']}",
                internal_message="Failed to update appliance vlan",
                api_response=e.args,
                code=2011,
                details=f"nw_id={nw_id} | vlan={vlan}",
                category=1
            )
            return False

    def update_firmware(self, nw_id, new_device_types=["appliance", "switch", "wireless"]):
        try:
            self.logger.info("FIRMWARE")
            self.logger.info(f"Updating firmware for {new_device_types}")
            net_info = self.getNetInfo(nw_id)
            if not net_info:
                self.log_issue(
                    external_message="Error occurred getting information about network, Cannot update firmware",
                    internal_message="Error occurred getting information about network, Cannot update firmware",
                    api_response="",
                    code=2080,
                    details=f"nw_id={nw_id} | new_device_types={new_device_types} | ",
                    category=2
                )
                return False

            product_types = net_info["productTypes"]
            product_types = {"appliance", "switch", "wireless"}.intersection(
                set(product_types)
            )
            product_types = product_types.intersection(set(new_device_types))

            pl = self.dashboard.networks.getNetworkFirmwareUpgrades(
                networkId=nw_id,
            )

            self.logger.info(f"firmware response:\n{pl}")
            updates = {}

            # determine if there are any out of date
            for prod_type, product in pl["products"].items():
                self.logger.info(f"Checking {prod_type}")
                if prod_type not in product_types or product["nextUpgrade"]["time"] != "":
                    continue

                current_id = int(product["currentVersion"]["id"])
                stable = {
                    int(x["id"]): x
                    for x in product["availableVersions"]
                    if x["releaseType"] == "stable"
                }
                acceptable = [
                    int(x["id"])
                    for x in product["availableVersions"]
                    if x["releaseType"] in ["stable", "beta"]
                ]
                self.logger.info(
                    f"current: {current_id} | stable: {stable} | currently acceptable: {acceptable}"
                )
                if current_id not in acceptable:
                    if len(stable) > 0:
                        available = max(stable.keys())
                        if current_id >= available:
                            continue
                        self.logger.info(
                            f"Upgrading {prod_type} from {current_id} to {available}"
                        )
                        updates[prod_type] = stable[available]
                    else:
                        self.log_issue(
                            external_message=f"Network firmware for {prod_type} appears to be out of date but no stable"
                                             f" replacement version can be found",
                            internal_message="No stable firmware version found",
                            api_response="",
                            code=2012,
                            details=f"nw_id={nw_id} | prod_type={prod_type} | firmware_upgrades={pl}",
                            category=5
                        )
                        continue
                else:
                    self.logger.info(
                        f"Firmware for {prod_type} is already up to date {current_id}"
                    )

            # send updates if any
            if updates:
                payload = {
                    "upgradeWindow": {"dayOfWeek": "sun", "hourOfDay": "4:00"},
                    "products": {},
                }
                for pt, vers in updates.items():
                    payload["products"][pt] = {
                        "nextUpgrade": {"toVersion": vers},
                        "participateInNextBetaRelease": False,
                    }
                self.logger.info(
                    f"Sending firmware upgrades:\n{json.dumps(payload, indent=2)}"
                )
                self.dashboard.networks.updateNetworkFirmwareUpgrades(
                    networkId=nw_id,
                    **payload
                )
            else:
                self.logger.info("No firmware updates available")
            return True

        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to update firmware",
                internal_message="Failed to update firmware",
                api_response=e.args,
                code=2013,
                details=f"nw_id={nw_id}  | firmware_upgrades_available={pl} | firmware_upgrades_sent={payload}",
                category=1
            )
            return False

    def vlanExists(self, nw_id, vl_id):
        netAppVlans = self.getNetworkVlans(nw_id)
        if not netAppVlans:
            return False
        self.logger.debug("NetAppVlans {}".format(netAppVlans))
        ids = [x["id"] for x in netAppVlans]
        self.logger.debug(f"NetAppVlans ids {ids}")
        return any([str(x) == str(vl_id) for x in ids])

    def getNetworkVlans(self, nw_id):
        try:
            response = self.dashboard.appliance.getNetworkApplianceVlans(
                networkId=nw_id,
            )
            return response
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to get appliance VLANS",
                internal_message="Failed to get appliance VLANS",
                api_response=e.args,
                code=2014,
                details=f"nw_id={nw_id}",
                category=2
            )
            return []

    def updateNetworkAlertSettings(self, nw_id):
        payload = {
            "alerts": [
                {
                    "type": "applianceDown",
                    "enabled": True,
                    "alertDestinations": {
                        "emails": [],
                        "snmp": True,
                        "allAdmins": False,
                        "httpServerIds": [],
                    },
                    "filters": {"timeout": 10},
                },
                {
                    "type": "failoverEvent",
                    "enabled": True,
                    "alertDestinations": {
                        "emails": [],
                        "snmp": True,
                        "allAdmins": False,
                        "httpServerIds": [],
                    },
                    "filters": {},
                },
                {
                    "type": "dhcpNoLeases",
                    "enabled": False,
                    "alertDestinations": {
                        "emails": [],
                        "snmp": False,
                        "allAdmins": False,
                        "httpServerIds": [],
                    },
                    "filters": {},
                },
                {
                    "type": "vrrp",
                    "enabled": True,
                    "alertDestinations": {
                        "emails": [],
                        "snmp": True,
                        "allAdmins": False,
                        "httpServerIds": [],
                    },
                    "filters": {},
                },
                {
                    "type": "cellularGatewayDown",
                    "enabled": True,
                    "alertDestinations": {
                        "emails": [],
                        "snmp": True,
                        "allAdmins": False,
                        "httpServerIds": [],
                    },
                    "filters": {"timeout": 10},
                },
                {
                    "type": "powerSupplyDown",
                    "enabled": True,
                    "alertDestinations": {
                        "emails": [],
                        "snmp": True,
                        "allAdmins": False,
                        "httpServerIds": [],
                    },
                    "filters": {},
                },
                {
                    "type": "rpsBackup",
                    "enabled": True,
                    "alertDestinations": {
                        "emails": [],
                        "snmp": True,
                        "allAdmins": False,
                        "httpServerIds": [],
                    },
                    "filters": {},
                },
                {
                    "type": "udldError",
                    "enabled": True,
                    "alertDestinations": {
                        "emails": [],
                        "snmp": True,
                        "allAdmins": False,
                        "httpServerIds": [],
                    },
                    "filters": {},
                },
                {
                    "type": "switchDown",
                    "enabled": True,
                    "alertDestinations": {
                        "emails": [],
                        "snmp": True,
                        "allAdmins": False,
                        "httpServerIds": [],
                    },
                    "filters": {"timeout": 10},
                },
                {
                    "type": "gatewayDown",
                    "enabled": True,
                    "alertDestinations": {
                        "emails": [],
                        "snmp": True,
                        "allAdmins": False,
                        "httpServerIds": [],
                    },
                    "filters": {"timeout": 10},
                },
                {
                    "type": "gatewayToRepeater",
                    "enabled": True,
                    "alertDestinations": {
                        "emails": [],
                        "snmp": True,
                        "allAdmins": False,
                        "httpServerIds": [],
                    },
                    "filters": {},
                },
                {
                    "type": "repeaterDown",
                    "enabled": True,
                    "alertDestinations": {
                        "emails": [],
                        "snmp": True,
                        "allAdmins": False,
                        "httpServerIds": [],
                    },
                    "filters": {"timeout": 10},
                },
                {
                    "type": "cameraDown",
                    "enabled": True,
                    "alertDestinations": {
                        "emails": [],
                        "snmp": True,
                        "allAdmins": False,
                        "httpServerIds": [],
                    },
                    "filters": {"timeout": 10},
                },
            ]
        }

        try:
            self.dashboard.networks.updateNetworkAlertsSettings(
                networkId=nw_id,
                **payload
            )
            return True
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to update network alert settings",
                internal_message="Failed to update network alert settings",
                api_response=e.args,
                code=2015,
                details=f"nw_id={nw_id}",
                category=2
            )
            return False

    def logging_settings(self, nwid, lic_types_str):
        try:
            self.logger.info(f"determining roles for {lic_types_str}")
            roles = []
            if "MX" in lic_types_str.upper():
                self.logger.info("adding MX roles")
                roles.extend(
                    [
                        'Appliance event log',
                        'URLs',
                        'Security events',
                        'Wireless event log',
                        'Air Marshal events',
                        'Switch event log'
                    ]
                )
            if "ENT" in lic_types_str.upper():
                self.logger.info("adding MR roles")
                roles.extend(
                    [
                        'Wireless event log',
                        "URLs"
                    ]
                )
            if "MS" in lic_types_str.upper():
                self.logger.info("adding MS roles")
                roles.extend(['Switch event log'])

            roles = list(set(roles))
            if len(roles) == 0:
                self.logger.info("no roles to push")
                return

            servers = [
                {
                    'host': '198.24.118.153',
                    'port': 514,
                    'roles': roles
                }
            ]
            response = self.dashboard.networks.updateNetworkSyslogServers(
                networkId=nwid,
                servers=servers
            )
            return response
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to set network SysLogging",
                internal_message="Failed to set network SysLogging",
                api_response=e.args,
                code=2016,
                details=f"nwid={nwid} | lic_types_str={lic_types_str} | servers={servers}",
                category=2
            )
            return False

    def getOrganizationSamlRoles(self, orgid):
        try:
            response = self.dashboard.organizations.getOrganizationSamlRoles(
                organizationId=orgid,
            )
            return response
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to get exiting organization SAML roles",
                internal_message="Failed to get exiting organization SAML roles",
                api_response=e.args,
                code=2017,
                details=f"orgid={orgid}",
                category=2
            )
            return False

    def updateOrganizationSamlRoles(self, org_id, acctNumber_str):
        # these 2 roles come from the clone by default
        default_acc_no1 = "07633567"
        default_acc_no2 = "25635500"
        did_write_full = False
        did_write_read_only = False
        samlRoles = self.getOrganizationSamlRoles(org_id)
        for account in samlRoles:
            saml_role = account["role"]
            saml_id = account["id"]
            access = account["orgAccess"]
            self.logger.info(f"looking at role: {saml_role}, id: {saml_id}")
            if saml_role.startswith("ACCT"):
                # we want to only update an account role if it is the default one that came with the clone org,
                # or if it is in a generic form. eg: acct-xxx_full
                last_part = saml_role.split("_")
                if len(last_part) < 2:
                    continue
                last_part = last_part[1]
                if acctNumber_str in saml_role:
                    # don't create the same role 2x
                    if last_part.lower() == "full":
                        did_write_full = True
                    else:
                        did_write_read_only = True
                    continue
                if (default_acc_no1 in saml_role or default_acc_no2 in saml_role) or all(
                        [not x.isnumeric() for x in saml_role]):
                    # in this case, the role we are looking at is generic, or it is the default account number
                    self.logger.info(f"{saml_role} passes conditions to update role")
                    try:
                        self.dashboard.organizations.updateOrganizationSamlRole(
                            organizationId=org_id,
                            samlRoleId=saml_id,
                            orgAccess=access,
                            role=f"{acctNumber_str}_{last_part}"
                        )
                        if last_part.lower() == "full":
                            did_write_full = True
                        else:
                            did_write_read_only = True
                    except (meraki.exceptions.APIError, AssertionError) as e:
                        self.log_issue(
                            external_message=f"Failed to update SAML role: {last_part}",
                            internal_message="Failed to update SAML role",
                            api_response=e.args,
                            code=2018,
                            details=f"org_id={org_id} | role_id={saml_id} | orgaccess={access} | role={f'{acctNumber_str}_{last_part}'}",
                            category=5
                        )
                else:
                    self.logger.info(f"{saml_role} failed conditions to update role")
        try:
            # Add additional roles that are needed and could not be updated from existing roles
            if not did_write_full:
                self.dashboard.organizations.createOrganizationSamlRole(
                    organizationId=org_id,
                    orgAccess="full",
                    role=f"{acctNumber_str}_Full"
                )

            if not did_write_read_only:
                self.dashboard.organizations.createOrganizationSamlRole(
                    organizationId=org_id,
                    orgAccess="read-only",
                    role=f"{acctNumber_str}_Read-only"
                )
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message=f"Failed to update SAML role: {last_part}",
                internal_message="Failed to update SAML role",
                api_response=e.args,
                code=2019,
                details=f"org_id={org_id} | did_write_full={did_write_full} | did_write_read_only={did_write_read_only} | acctNumber_str={acctNumber_str}",
                category=5
            )

    def updateNetworkApplianceTrafficShaping(self, nw_id, bandwidth):
        """
        Update the traffic shaping settings for an MX network
        Does limit up and limit down separate for wan1 and wan2 (if available)
        incase any of those fields fail
        https://jira.charter.com/browse/SECSO-2654
        """
        limits = bandwidth["bandwidthLimits"]
        for wan_n in ["wan1", "wan2"]:
            if wan_n in limits:
                for bandwidth_direction in ["limitUp", "limitDown"]:
                    try:
                        pl = {
                            "bandwidthLimits": {
                                wan_n: {bandwidth_direction: limits[wan_n][bandwidth_direction]}
                            }
                        }
                        self.dashboard.appliance.updateNetworkApplianceTrafficShapingUplinkBandwidth(
                            networkId=nw_id,
                            **pl
                        )
                        time.sleep(0.5)
                    except (meraki.exceptions.APIError, AssertionError) as e:
                        self.log_issue(
                            external_message="Failed to update network appliance traffic shaping",
                            internal_message="Failed to update network appliance traffic shaping",
                            api_response=e.args,
                            code=2020,
                            details=f"nw_id={nw_id} | wan_n={wan_n} | bandwidth_direction={bandwidth_direction} | bandwidth={bandwidth}",
                            category=1
                        )

    def updateNetworkApplianceSecurityIntrusion(self, nw_id, rules=None):
        try:
            payload = (
                {"mode": "prevention", "idsRulesets": "balanced"}
                if rules is None
                else rules
            )
            payload = {k: v.lower() for k, v in payload.items()}
            self.dashboard.appliance.updateNetworkApplianceSecurityIntrusion(
                networkId=nw_id,
                **payload
            )
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to apply Appliance Security Intrusion settings",
                internal_message="Failed to apply Appliance Security Intrusion settings",
                api_response=e.args,
                code=2021,
                details=f"nw_id={nw_id} | rules={rules} | payload={payload}",
                category=2
            )

    def updateNetworkApplianceSecurityMalware(self, nw_id):
        try:
            self.dashboard.appliance.updateNetworkApplianceSecurityMalware(
                networkId=nw_id,
                mode="enabled"
            )
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to apply Appliance Security Malware settings",
                internal_message="Failed to apply Appliance Security Malware settings",
                api_response=e.args,
                code=2022,
                details=f"nw_id={nw_id}",
                category=2
            )

    def create_content_filtering_payload(self, site_details, source="mne"):
        """
        creates payloads for content filtering
        if source == staff
        :param site_details: site details straight from design portal
        :param source: one of "mne" "guest" or "staff" (staff will be used for group policy content filtering)
        :return: content filtering payload
        """
        try:
            if source in ["guest", "staff"]:
                wl_key = f"policy_web_filter_{source}_url_whitelist"
                bl_key = f"policy_web_filter_{source}_url_blacklist"
                categories_key = f"policy_web_filter_{source}_category_blocking"
                threat_categories_key = f"policy_web_filter_{source}_threat_categories"
            else:
                wl_key = "policy_web_filter_url_whitelist"
                bl_key = "policy_web_filter_url_blacklist"
                categories_key = "policy_web_filter_category_blocking"
                threat_categories_key = "policy_web_filter_threat_categories"

            categories = f"{site_details[categories_key]}, {site_details[threat_categories_key]}"
            categories = categories.replace(" ", "").split(",")

            if source == "staff":
                payload = {"blockedUrlCategories": {"categories": categories, "settings": "override"}}
            else:
                payload = {"blockedUrlCategories": categories}

            wl = site_details[wl_key]
            bl = site_details[bl_key]

            if wl not in [None, ""]:
                wl = (
                    wl.replace(", ", ",")
                    .replace(" ,", ",")
                    .replace(" ", ",")
                    .replace("\n", ",")
                    .replace(" ", "")
                    .split(",")
                )
                if source == "staff":
                    payload["allowedUrlPatterns"] = {"patterns": wl, "settings": "override"}
                else:
                    payload["allowedUrlPatterns"] = wl
            if bl not in [None, ""]:
                bl = (
                    bl.replace(", ", ",")
                    .replace(" ,", ",")
                    .replace(" ", ",")
                    .replace("\n", ",")
                    .replace(" ", "")
                    .split(",")
                )
                if source == "staff":
                    payload["blockedUrlPatterns"] = {"patterns": bl, "settings": "override"}
                else:
                    payload["blockedUrlPatterns"] = bl
            return payload
        except Exception as e:
            self.log_issue(
                external_message=f"Failed to parse {source} content filtering payload",
                internal_message="Failed to parse content filtering payload",
                api_response=e.args,
                code=2023,
                details=f"site_details={site_details} | source={source}",
                category=1
            )
            return None

    def get_content_filtering_ids(self, nw_id, category_list, context=""):
        try:
            meraki_categories = self.dashboard.appliance.getNetworkApplianceContentFilteringCategories(networkId=nw_id)
            meraki_categories = meraki_categories["categories"]
            meraki_categories = {
                mc["name"].upper().replace(" ", ""): mc["id"] for mc in meraki_categories
            }
            categories = []
            invalid = []
            for c in category_list:
                content_category = c.upper().replace(" ", "")
                if c in ["", None]:
                    continue
                if content_category in meraki_categories.keys():
                    categories.append(content_category)
                else:
                    invalid.append(content_category)
            if len(invalid) > 0:
                self.log_issue(
                    external_message=f"Some {context} content filtering categories are invalid and have been skipped",
                    internal_message="Some content filtering categories are invalid and have been skipped",
                    api_response="",
                    code=2024,
                    details=f"nw_id={nw_id} | context={context} | invalid={invalid}",
                    category=1
                )
            category_ids = [
                meraki_categories[sc.upper().replace(" ", "")] for sc in categories
            ]
            return category_ids
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to apply content filtering categories",
                internal_message="Failed to apply content filtering categories",
                api_response=e.args,
                code=2025,
                details=f"nw_id={nw_id} | context={context}",
                category=2
            )
            return []

    def create_staff_group_policy(self, nwid, content_filters):
        try:
            # first get existing policies to make sure the staff group policy has already been created
            exiting_policies = self.dashboard.networks.getNetworkGroupPolicies(
                networkId=nwid,
            )
            exiting_policy_names = [x["name"].lower() for x in exiting_policies]
            if "staff" in exiting_policy_names:
                return True

            content_filters["blockedUrlCategories"]["categories"] = self.get_content_filtering_ids(
                nw_id=nwid,
                category_list=content_filters["blockedUrlCategories"]["categories"],
                context="Staff group policy"
            )
            payload = {
                "name": "Staff",
                "contentFiltering": content_filters
            }
            response = self.dashboard.networks.createNetworkGroupPolicy(
                networkId=nwid,
                **payload
            )
        except (meraki.exceptions.APIError, AssertionError, KeyError) as e:
            self.log_issue(
                external_message="Failed to create group policy",
                internal_message="Failed to create group policy",
                api_response=e.args,
                code=2026,
                details=f"nwid={nwid} | payload={payload}",
                category=2
            )
            return False

        try:
            # this block covers calls to update the vlan with the group policy
            # get VLANS, find the right one, then apply the group policy id to it
            vlans = self.dashboard.appliance.getNetworkApplianceVlans(nwid)
            vlans = {x["name"]: x["id"] for x in vlans}
            vid = 0  # for logging
            for k, v in vlans.items():
                vid = v
                # todo this logic is temporary, eventually we will want a better way to determine exactly which
                #  vlan to select but doing a name search should cover 99% of cases, otherwise we will tell the user
                #  it cannot be found and they will have to add it manually
                if "staff" in k.lower():
                    self.logger.info(f"Changing the group policy id for vlan {v}")
                    self.dashboard.appliance.updateNetworkApplianceVlan(
                        networkId=nwid,
                        vlanId=v,
                        groupPolicyId=response["groupPolicyId"]
                    )
                    return True
        except (meraki.exceptions.APIError, AssertionError, KeyError) as e:
            self.log_issue(
                external_message="Failed to add staff group policy to staff VLAN",
                internal_message="Failed to add staff group policy to staff VLAN",
                api_response=e.args,
                code=2027,
                details=f"nwid={nwid} | vlanId={vid} | groupPolicyId={response['groupPolicyId']}",
                category=2
            )
            return False

    def updateNetworkApplianceContentFiltering(self, nw_id, content_filters):
        try:
            self.logger.info(f"provided Categories: {content_filters}")
            if len(content_filters) == 0:
                return
            content_filters["blockedUrlCategories"] = self.get_content_filtering_ids(
                nw_id=nw_id,
                category_list=content_filters["blockedUrlCategories"],
                context="Security and SD-WAN"
            )
            self.logger.info("ids: {}".format(content_filters["blockedUrlCategories"]))
            self.dashboard.appliance.updateNetworkApplianceContentFiltering(
                networkId=nw_id,
                **content_filters
            )
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to update content filtering categories",
                internal_message="Failed to update content filtering categories",
                api_response=e.args,
                code=2028,
                details=f"nwid={nw_id} | content_filters={content_filters}",
                category=1
            )

    def updateNetworkSnmpSettings(self, nw_id):
        """Update the SNMP settings for a network"""
        try:
            self.dashboard.networks.updateNetworkSnmp(
                networkId=nw_id,
                access="users",
                users=[{"username": "un1f13dMNE", "passphrase": "dmZadm1N"}]
            )
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to update network SNMP settings",
                internal_message="Failed to update network SNMP settings",
                api_response=e.args,
                code=2029,
                details=f"nwid={nw_id}",
                category=2
            )

    def updateOrganizationSNMP(self, org_id):
        try:
            data = {
                "organizationId": org_id,
                "v2cEnabled": False,
                "v3Enabled": True,
                "v3AuthMode": "SHA",
                "v3PrivMode": "AES128",
                "peerIps": ["70.125.123.72", "98.6.16.112", "70.125.123.47"],
                "v3User": "o/GFDceaDb",
                "hostname": "snmp.meraki.com",
                "port": 16100,
            }
            self.dashboard.organizations.updateOrganizationSnmp(
                **data
            )

        except meraki.exceptions.APIError as e:
            self.log_issue(
                external_message="Failed to update organization SNMP",
                internal_message="Failed to update organization SNMP",
                api_response=e.args,
                code=2030,
                details=f"org_id={org_id}",
                category=2
            )

    def update_vpn_peers(self, organizationID, peers: list):
        try:
            existing_peers = self.dashboard.appliance.getOrganizationApplianceVpnThirdPartyVPNPeers(
                organizationId=organizationID,
            )
            existing_peers = existing_peers["peers"]
            existing_peers = {x["name"]: x for x in existing_peers}
            self.logger.info("Successfully retrieved current peers")

            # update existing peers with new peers
            peers = {x["name"]: x for x in peers}
            existing_peers.update(peers)
            peers = list(existing_peers.values())

            # send the news peers with the updated peers to meraki
            self.dashboard.appliance.updateOrganizationApplianceVpnThirdPartyVPNPeers(
                organizationId=organizationID,
                peers=peers
            )
            self.logger.info("Successfully Updated 3party vpn peers")

        except meraki.exceptions.APIError as e:
            self.log_issue(
                external_message="Failed to updated 3party vpn peers",
                internal_message="Failed to updated 3party vpn peers",
                api_response=e.args,
                code=2031,
                details=f"organizationID={organizationID} | peers={peers}",
                category=1
            )
            self.logger.info("Failed to updated 3party vpn peers")

    def disable_auto_vpn(self, nwid):
        try:
            self.dashboard.appliance.updateNetworkApplianceTrafficShapingUplinkSelection(
                networkId=nwid,
                activeActiveAutoVpnEnabled=False
            )
            self.logger.info("Successfully disabled active_active")
        except meraki.exceptions.APIError as e:
            self.log_issue(
                external_message="Failed to Disable Active Active Auto VPN",
                internal_message="Failed to Disable Active Active Auto VPN",
                api_response=e.args,
                code=2032,
                details=f"nwid={nwid}",
                category=2
            )

    def firewall_service(self, nwid):
        try:
            self.dashboard.appliance.updateNetworkApplianceFirewallFirewalledService(
                networkId=nwid,
                service="SNMP",
                access="restricted",
                allowedIps=["70.125.123.72", "98.6.16.112", "70.125.123.47"]
            )
            self.logger.info("SUCCESS firewall_service")
        except meraki.exceptions.APIError as e:
            self.log_issue(
                external_message="Failed to update Firewall Services SNMP",
                internal_message="Failed to update Firewall Services SNMP",
                api_response=e.args,
                code=2033,
                details=f"nwid={nwid}",
                category=2
            )

    def apply_L3_rules(self, nwid, l3_rules):
        vlans = self.getNetworkVlans(nwid)
        vlans = {x["name"]: x["id"] for x in vlans}
        payload = {"rules": []}
        for rule in l3_rules["rules"]:
            if rule["destCidr"] in vlans:
                rule["destCidr"] = "VLAN({}).*".format(vlans[rule["destCidr"]])
            if rule["srcCidr"] in vlans:
                rule["srcCidr"] = "VLAN({}).*".format(vlans[rule["srcCidr"]])
            if isinstance(rule["protocol"], str):
                rule["protocol"] = rule["protocol"].replace("v4", "").replace("v6", "6").lower()
            for key in ["srcCidr", "destCidr"]:
                rule[key] = self.replace_escape_chars(rule[key])
            payload["rules"].append(rule)

        payload = l3_rules
        self.logger.info("L3 RULES")
        self.logger.info(json.dumps(payload, indent=4))
        try:
            self.dashboard.appliance.updateNetworkApplianceFirewallL3FirewallRules(
                networkId=nwid,
                **payload
            )
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to update L3 firewall rules",
                internal_message="Failed to update L3 firewall rules",
                api_response=e.args,
                code=2034,
                details=f"nwid={nwid} | payload={payload}",
                category=1
            )

    def apply_L7_rules(self, nwid, l7_rules):
        try:
            applications = self.dashboard.appliance.getNetworkApplianceFirewallL7FirewallRulesApplicationCategories(
                networkId=nwid
            )
            applications = applications["applicationCategories"]
            all_ids = []  # list of all application and applicationCategories with ids
            for application_category in applications:
                application_category_entry = {
                    "id": application_category["id"],
                    "name": f"All {application_category['name']}",
                }
                all_ids.append(application_category_entry)
                all_ids.extend(application_category["applications"])
            name_to_id = {x["name"]: x["id"] for x in all_ids}
            special_types = [
                "HTTP hostname",
                "Port",
                "Remote IP range",
                "Remote IP range & port",
            ]
            new_rules = []
            country_rules = [x for x in l7_rules["rules"] if x["type"] == "Countries"]
            rules = [x for x in l7_rules["rules"] if x["type"] != "Countries"]

            # non-country rules
            for x in rules:
                new_rule = {
                    "policy": "deny",
                }
                if x["type"] not in special_types:
                    # type either needs to be set to 'application' or 'applicationCategory'
                    name = x["value"]
                    _id = name_to_id.get(name)
                    if _id is None:
                        self.log_issue(
                            external_message=f"Failed to find meraki id for L7 rule value '{name}'",
                            internal_message="Failed to find meraki id for L7 rule value",
                            api_response="",
                            code=2035,
                            details=f"nwid={nwid} | name={name}",
                            category=1
                        )
                        continue
                    _type = "application"
                    if "category" in _id:
                        _type = "applicationCategory"
                    new_rule["type"] = _type
                    new_rule["value"] = {"name": name, "id": _id}
                else:
                    # if special, we need to rename the type
                    if x["type"] == "HTTP hostname":
                        new_rule["type"] = "host"
                        new_rule["value"] = x["value"]
                    elif x["type"] == "Port":
                        new_rule["type"] = "port"
                        new_rule["value"] = x["value"]
                    elif x["type"] in ["Remote IP range", "Remote IP range & port"]:
                        new_rule["type"] = "ipRange"
                        new_rule["value"] = x["value"]
                new_rules.append(new_rule)

            # country rules
            if len(country_rules) > 0:
                country_codes = []
                bad_countries = []
                for country_rule in country_rules:
                    country_code = self.country_map(country_rule["value"].upper())
                    if country_code:
                        country_codes.append(country_code)
                    else:
                        # account for instances where one entry is actually the list as a string we are trying to parse
                        if "," in country_rule["value"]:
                            countries_list_as_str = country_rule["value"].upper()
                            countries = [x.upper().strip() for x in countries_list_as_str.split(",")]
                            for c in countries:
                                country_code = self.country_map(c)
                                if country_code:
                                    country_codes.append(country_code)
                                else:
                                    bad_countries.append(c)
                        else:
                            bad_countries.append(country_rule["value"].upper())
                if len(bad_countries) > 0:
                    self.log_issue(
                        external_message=f"Could not find the ISO 3166 code for some countries blocked under L7 rules {bad_countries}",
                        internal_message="Could not find the ISO 3166 code for some countries blocked under L7 rules",
                        api_response="",
                        code=2036,
                        details=f"nwid={nwid} | bad_countries={bad_countries}",
                        category=1
                    )
                meraki_country_rules = {
                    "policy": "deny",
                    "type": "blockedCountries",
                    "value": country_codes,
                }
                new_rules.append(meraki_country_rules)
            payload = {"rules": new_rules}
            self.dashboard.appliance.updateNetworkApplianceFirewallL7FirewallRules(
                networkId=nwid,
                **payload
            )
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to update L7 Rules",
                internal_message="Failed to update L7 Rules",
                api_response=e.args,
                code=2037,
                details=f"nwid={nwid} | payload={payload}",
                category=1
            )

    def apply_1to1_nat_rules(self, nwid, rules):
        try:
            self.dashboard.appliance.updateNetworkApplianceFirewallOneToOneNatRules(
                networkId=nwid,
                rules=rules["rules"]
            )
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to update 1-1 firewall NAT rules",
                internal_message="Failed to update 1-1 firewall NAT rules",
                api_response=e.args,
                code=2038,
                details=f"nwid={nwid} | rules={rules}",
                category=1
            )

    def apply_1to_many_nat_rules(self, nwid, rules):
        self.logger.warning("1-many nat rules: {}".format(json.dumps(rules)))
        try:
            self.dashboard.appliance.updateNetworkApplianceFirewallOneToManyNatRules(
                networkId=nwid,
                rules=rules["rules"]
            )
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to update 1-MANY firewall NAT rules",
                internal_message="Failed to update 1-MANY firewall NAT rules",
                api_response=e.args,
                code=2039,
                details=f"nwid={nwid} | rules={rules}",
                category=1
            )

    def apply_pf_nat_rules(self, nwid, rules):
        try:
            updated_rules = []
            self.logger.info(f"provided pf rules are: {rules}")
            for r in rules:
                ex_ports = r["external_port"].replace(" ", "")
                int_ports = r["internal_port"].replace(" ", "")

                allowed_ips = []
                if r["allowed_ips"].lower() == "any":
                    allowed_ips = ["any"]
                else:
                    allowed_ips = r["allowed_ips"].replaoce(" ", ",").replace("\n", ",").split(",")

                updated_rules.append(
                    {
                        "lanIp": r["internal_ip"],
                        "allowedIps": allowed_ips,
                        "protocol": r["protocol"],
                        "publicPort": ex_ports,
                        "localPort": int_ports,
                        "name": r["description"],
                        "uplink": r["uplink"].lower().replace(" ", ""),  # << this needs clean string
                    }
                )
                if not updated_rules["name"]:
                    del updated_rules["name"]
            self.logger.info(f"sending updated port forwarding rules: {updated_rules}")
            self.dashboard.appliance.updateNetworkApplianceFirewallPortForwardingRules(
                networkId=nwid,
                rules=updated_rules
            )
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to update firewall port forwarding rules",
                internal_message="Failed to update firewall port forwarding rules",
                api_response=e.args,
                code=2041,
                details=f"nwid={nwid}",
                category=1
            )
        except Exception as e:
            self.log_issue(
                external_message="Failed to update firewall port forwarding rules",
                internal_message="An unknown issue occured trying to update firewall port forwarding rules",
                api_response=e.args,
                code=2041,
                details=f"nwid={nwid}",
                category=1
            )

    def apply_static_routing(self, nwid, static_routes):
        try:
            self.logger.info(f"Static Routes \n{json.dumps(static_routes, indent=4)}")
        except Exception:
            # static route is not a list
            self.log_issue(
                external_message="Static route is not in json format",
                internal_message="Static route is not in json format",
                api_response="",
                code=2042,
                details=f"nwid={nwid} | static_routes={static_routes}",
                category=1
            )
            self.logger.info(static_routes)
            return

        for r in static_routes:
            try:
                self.dashboard.appliance.createNetworkApplianceStaticRoute(
                    networkId=nwid,
                    **r
                )
            except meraki.exceptions.APIError as e:
                self.log_issue(
                    external_message="Failed to create static route",
                    internal_message="Failed to create static route",
                    api_response=e.args,
                    code=2043,
                    details=f"nwid={nwid} | failed_route={r} | all_static_routes={static_routes}",
                    category=1
                )
                continue

    def claimNetworkDevice(self, nw_id, serial):
        """Claim devices into a network"""
        try:
            self.dashboard.networks.claimNetworkDevices(
                networkId=nw_id,
                serials=[serial]
            )
            return True, ""
        except (meraki.exceptions.APIError, AssertionError) as e:
            external = f"No device with serial {serial} found"
            internal = "No device with serial found"
            code = 2044
            if "already claimed" in e.args[0]:
                external = f"Device {serial} has already been claimed in a different network"
                internal = "Device has already been claimed"
                code = 2045

            self.log_issue(
                external_message=external,
                internal_message=internal,
                api_response=e.args,
                code=code,
                details=f"nw_id={nw_id} | serial={serial}",
                category=3
            )
            return False, e.args[0]

    def claim_vmx(self, nwid, size):
        """
        claims a VMX devices in an appliance network
        :return:
        """
        try:
            response = self.dashboard.networks.vmxNetworkDevicesClaim(
                networkId=nwid,
                size=size,
            )
            return response
        except meraki.exceptions.APIError as e:
            self.log_issue(
                external_message="Failed to claim VMX device to network",
                internal_message="Failed to claim VMX device to network",
                api_response=e.args,
                code=2046,
                details=f"nwid={nwid} | size={size}",
                category=1
            )
            return False

    def get_org_devices(self, org_id):
        try:
            response = self.dashboard.organizations.getOrganizationDevices(
                organizationId=org_id,
            )
            return response
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to get organization devices",
                internal_message="Failed to get organization devices",
                api_response=e.args,
                code=2047,
                details=f"org_id={org_id}",
                category=2
            )
            return []

    def get_network_devices(self, nwid):
        try:
            response = self.dashboard.networks.getNetworkDevices(
                networkId=nwid,
            )
            return response
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to get network devices",
                internal_message="Failed to get network devices",
                api_response=e.args,
                code=2048,
                details=f"nwid={nwid}",
                category=2
            )
            return []

    def updateOrganizationLicenses(self, org_id, serial, licenseId):
        """Assign license to this serial number"""
        try:
            self.dashboard.organizations.updateOrganizationLicense(
                organizationId=org_id,
                licenseId=licenseId,
                deviceSerial=serial
            )
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message=f"Failed to assign license to device {serial}",
                internal_message="Failed to assign license to device",
                api_response=e.args,
                code=2049,
                details=f"org_id={org_id} | serial={serial} | licenseId={licenseId}",
                category=2
            )

    def update_ha_appliance(self, nwid, spare_serial, vip1, vip2=False):
        try:
            vip2_condition = {}
            if vip2:
                vip2_condition["virtualIp2"] = vip2
            self.dashboard.appliance.updateNetworkApplianceWarmSpare(
                networkId=nwid,
                virtualIp1=vip1,
                enabled=True,
                spareSerial=spare_serial,
                uplinkMode="virtual",
                **vip2_condition
            )
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to set appliance high availability settings",
                internal_message="Failed to set appliance high availability settings",
                api_response=e.args,
                code=2050,
                details=f"nwid={nwid} | spare_serial={spare_serial} | vip1={vip1} | vip2={vip2}",
                category=2
            )

    def failover_fallback(self, nwid):
        try:
            self.dashboard.appliance.updateNetworkApplianceTrafficShapingUplinkSelection(
                networkId=nwid,
                failoverAndFailback={'immediate': {'enabled': True}}
            )
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to set fail-over and fallback settings",
                internal_message="Failed to set fail-over and fallback settings",
                api_response=e.args,
                code=2051,
                details=f"nwid={nwid}",
                category=2
            )

    def updateNetworkAppliancePorts(self, nw_id, ports):
        """
        Updates the ports on MX device
        """
        self.logger.info(f"MX ports: {ports}")
        failed_ports = []
        messages = []
        for k, v in ports.items():
            success, message = self.updateNetworkAppliancePort(nw_id=nw_id, port_no=k, port_pl=v)
            if not success:
                failed_ports.append(k)
                messages.append(message)
        if len(failed_ports) > 0:
            external = f"Failed to update some appliance port(s): {failed_ports}"
            internal = "Failed to update some appliance ports"
            if len(failed_ports) == len(ports.items()):
                external = "Failed to update all appliance ports"
                internal = "Failed to update all appliance ports"
            self.log_issue(
                external_message=external,
                internal_message=internal,
                api_response=str(messages),
                code=2052,
                details=f"nw_id={nw_id} | failed_ports={failed_ports} | all_ports={ports}",
                category=1
            )

    def updateNetworkAppliancePort(self, nw_id, port_no, port_pl):
        """
        Updates single port on MX device
        """
        try:
            self.dashboard.appliance.updateNetworkAppliancePort(
                networkId=nw_id,
                portId=port_no,
                **port_pl
            )
            return True, None
        except (meraki.exceptions.APIError, AssertionError) as e:
            # no error log needed here, handled by caller
            return False, e.args

    def updatePort(self, serial, port, payload):
        try:
            self.dashboard.switch.updateDeviceSwitchPort(
                serial=serial,
                portId=port,
                **payload
            )
        except (meraki.exceptions.APIError, AssertionError) as e:
            return False, e.args
        return True, None

    def updateSwitchPorts(self, serial, port_data: dict):
        failed_ports = []
        messages = []
        for p_id, p_data in port_data.items():
            success, message = self.updatePort(serial, p_id, p_data)
            if not success:
                messages.append(message)
                failed_ports.append(p_id)
            time.sleep(0.1)
        if len(failed_ports) > 0:
            external = f"Failed to update some switch port(s): {failed_ports}"
            internal = "Failed to update some switch ports"
            if len(failed_ports) == len(port_data.items()):
                external = "Failed to update all switch ports"
                internal = "Failed to update all switch ports"
            self.log_issue(
                external_message=external,
                internal_message=internal,
                api_response=str(messages),
                code=2053,
                details=f"serial={serial} | failed_ports={failed_ports} | all_ports={port_data}",
                category=1
            )

    def set_switch_settings(self, nw_id, mgmt_vlan=88):
        try:
            self.dashboard.switch.updateNetworkSwitchSettings(
                networkId=nw_id,
                vlan=mgmt_vlan
            )
            self.logger.info("Successfully updated switch vlan to 88")
        except meraki.exceptions.APIError as e:
            self.log_issue(
                external_message="Failed to set switch settings",
                internal_message="Failed to set switch settings",
                api_response=e.args,
                code=2054,
                details=f"nw_id={nw_id}",
                category=2
            )

    def update_device_location(self, serial, notes, tags):
        device_info = {}
        if notes not in ["", None]:
            device_info["notes"] = notes
        if tags not in ["", None]:
            if isinstance(tags, str):
                device_info["tags"] = tags.strip().split(" ")
            else:
                device_info["tags"] = tags

        if "notes" not in device_info and "tags" not in device_info:
            return True, None
        else:
            try:
                self.logger.info(f"Sending {device_info} to {serial}")
                self.dashboard.devices.updateDevice(
                    serial=serial,
                    **device_info
                )
                return True, None
            except (meraki.exceptions.APIError, AssertionError) as e:
                return False, f"{serial} - {e.args}"

    def updateDeviceName(self, org_id, nw_id, serial, hostname, address, notes):
        params = '\n'.join([str(x) for x in [org_id, nw_id, serial, hostname, address, notes]])
        self.logger.info(f"UPDATE DEVICE PARAMS: {params}")

        def getNameOfDevices():
            try:
                # Return array with name of devices or an empty list if no devices in the organization.
                devices = self.dashboard.organizations.getOrganizationDevices(organizationId=org_id)
                return [x["name"] for x in devices]
            except (meraki.exceptions.APIError, AssertionError) as e:
                self.log_issue(
                    external_message="Failed to get organization devices",
                    internal_message="Failed to get organization devices",
                    api_response=e.args,
                    code=2055,
                    details=f"org_id={org_id}",
                    category=2
                )
                return []

        device_names = getNameOfDevices()
        if hostname not in device_names:
            try:
                payload = {
                    "name": hostname,
                    "serial": serial,
                    "address": address,
                    "notes": notes,
                    "moveMapMarker": True,
                }
                self.dashboard.devices.updateDevice(
                    **payload
                )
            except (meraki.exceptions.APIError, AssertionError) as e:
                self.log_issue(
                    external_message=f"Failed to set name '{hostname}' to device {serial}",
                    internal_message="Failed to set device info",
                    api_response=e.args,
                    code=2056,
                    details=f"org_id={org_id} | nw_id={nw_id} | serial={serial} | hostname={hostname} | address={address} | notes={notes}",
                    category=2
                )
        else:
            self.log_issue(
                external_message=f"There is already a device claimed in network with name: {hostname}",
                internal_message="There is already a device claimed in network with provided hostname",
                api_response="",
                code=2057,
                details=f"org_id={org_id} | nw_id={nw_id} | serial={serial} | hostname={hostname} | address={address} | notes={notes}",
                category=3
            )

    def get_ssids(self, nw_id):
        try:
            response = self.dashboard.wireless.getNetworkWirelessSsids(
                networkId=nw_id
            )
            return response
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to get existing wireless ssids",
                internal_message="Failed to get existing wireless ssids",
                api_response=e.args,
                code=2058,
                details=f"nw_id={nw_id}",
                category=2
            )
            return []

    def createSSIDs(self, nw_id, ssids, service_type=""):
        self.logger.info("Creating SSIDS")
        splash_page_urls = {}  # maps ssid_name -> custom splash_url
        if len(ssids) == 0:
            return True
        elif "id" in ssids[0]:
            try:
                parsed_ssids = []
                for dp_ssid in ssids:
                    if dp_ssid.get("custom_splash_url", False):
                        splash_page_urls[dp_ssid["ssid"].strip()] = dp_ssid["custom_splash_url"]
                    meraki_ssid = {
                        "wireless_clients_blocked_from_lan": dp_ssid["wireless_clients_blocked_from_lan"],
                        "schedule": dp_ssid["schedule"],
                        "enabled": dp_ssid["status"].lower() == "enabled",
                        "name": dp_ssid["ssid"].strip(),
                        "encryptionMode": "wpa",
                        "ipAssignmentMode": dp_ssid["addressing_mode"].lower(),
                        "splashPage": "None",
                        "visible": str(dp_ssid["hide_ssid"]).lower() != "enabled",
                        "useVlanTagging": str(dp_ssid["vlan_tagging"]).lower() == "enabled",
                    }

                    if dp_ssid.get("wpa_encryption_mode") and dp_ssid["network_access"].lower() != "open":
                        if "and" in dp_ssid["wpa_encryption_mode"]:
                            if dp_ssid["wpa_encryption_mode"].upper() == "WPA2 AND WPA3":
                                meraki_ssid["wpaEncryptionMode"] = 'WPA3 Transition Mode'
                            else:
                                meraki_ssid["wpaEncryptionMode"] = dp_ssid["wpa_encryption_mode"]
                        else:
                            meraki_ssid["wpaEncryptionMode"] = dp_ssid["wpa_encryption_mode"] + " only"

                    if dp_ssid["network_access"].lower() == "open":
                        meraki_ssid["authMode"] = "open"

                    elif dp_ssid["network_access"].lower() == "enterprise":
                        meraki_ssid["authMode"] = "8021x-meraki"

                    elif "with radius" in dp_ssid["network_access"]:
                        meraki_ssid["radiusServers"] = []

                    if "psk" in dp_ssid["network_access"].lower():
                        if not dp_ssid.get("psk"):
                            self.log_issue(
                                external_message="SSID with 'PSK' Network needs a valid PSK",
                                internal_message="SSID with 'PSK' Network needs a valid PSK",
                                api_response="",
                                code=2059,
                                details=f"nw_id={nw_id} | dp_ssid={dp_ssid} | service_type={service_type}",
                                category=1
                            )
                            continue
                        meraki_ssid["psk"] = dp_ssid["psk"]
                        meraki_ssid["authMode"] = "psk"
                        meraki_ssid["encryptionMode"] = "wpa"

                    if dp_ssid["per_client_bw_limit_down"]:
                        meraki_ssid["perClientBandwidthLimitDown"] = int(dp_ssid["per_client_bw_limit_down"])
                    if dp_ssid["per_client_bw_limit_up"]:
                        meraki_ssid["perClientBandwidthLimitUp"] = int(dp_ssid["per_client_bw_limit_up"])
                    if meraki_ssid["useVlanTagging"]:
                        meraki_ssid["vlanId"] = dp_ssid["vlan"]
                    ipAssignmentMode = dp_ssid["addressing_mode"].lower()
                    if "nat" in ipAssignmentMode:
                        meraki_ssid["ipAssignmentMode"] = "NAT mode"
                    elif "bridge" in ipAssignmentMode:
                        meraki_ssid["lanIsolationEnabled"] = str(dp_ssid["layer_2_isolation"]).lower() == "enabled"
                        meraki_ssid["ipAssignmentMode"] = "Bridge mode"
                        meraki_ssid["useVlanTagging"] = dp_ssid["vlan_tagging"].lower() == "enabled"
                        if dp_ssid["vlan"] not in [None, ""]:
                            meraki_ssid["defaultVlanId"] = int(dp_ssid["vlan"])
                    elif "layer 3" in ipAssignmentMode and "concentrator" in ipAssignmentMode:
                        meraki_ssid["ipAssignmentMode"] = "Layer 3 roaming with a concentrator"
                    elif "layer 3" in ipAssignmentMode:
                        meraki_ssid["ipAssignmentMode"] = "Layer 3 roaming"
                        meraki_ssid["useVlanTagging"] = dp_ssid["vlan_tagging"].lower() == "enabled"
                        if dp_ssid["vlan"] not in [None, ""]:
                            meraki_ssid["defaultVlanId"] = int(dp_ssid["vlan"])
                    elif "vpn" in ipAssignmentMode:
                        meraki_ssid["ipAssignmentMode"] = "VPN"
                    else:
                        raise Exception("unknown ipAssignmentMode")

                    # for mne pr
                    if "per room" in service_type.lower():
                        if dp_ssid.get("guest_ssid"):
                            self.logger.info(f"SSID {dp_ssid['ssid']} is Guest")
                            # Static information for mne per room
                            # this will not change between orders
                            meraki_ssid.update(
                                {
                                    "radiusAccountingEnabled": True,
                                    "splashPage": "Password-protected with custom RADIUS",
                                    "walledGardenEnabled": True,
                                    "walledGardenRanges": [
                                        "*.guestinternet.com",
                                        "*.11os.com",
                                        "*.spreedly.com"
                                    ],
                                    "radiusServers": [
                                        {
                                            "host": "rad.11os.com",
                                            "port": 1812,
                                            "secret": "ElevenRules"
                                        }
                                    ],
                                    "radiusAccountingServers": [
                                        {
                                            "host": "rad.11os.com",
                                            "port": 1813,
                                            "secret": "ElevenRules"
                                        }
                                    ]
                                }
                            )
                        else:
                            self.logger.info(f"SSID {dp_ssid['ssid']} is NOT Guest")

                    parsed_ssids.append(meraki_ssid)
                ssids = parsed_ssids
            except Exception as e:
                self.log_issue(
                    external_message="Failed to parse SSIDS from Design Portal",
                    internal_message="Failed to parse SSIDS from Design Portal",
                    api_response=e.args,
                    code=2060,
                    details=f"nw_id={nw_id} | ssids={ssids} | already_parsed={[x['name'] for x in parsed_ssids]}",
                    category=5
                )
                return False

        existing_ssids = self.get_ssids(nw_id=nw_id)
        existing_ssids = {x["name"]: x["number"] for x in existing_ssids}
        numbers = list(reversed(range(15)))  # 15 slots for ssids in meraki

        # assign the "number" id to each ssid and keep existing ssids having the same number
        for i in range(len(ssids)):
            if ssids[i]["name"].strip() in existing_ssids:
                number = existing_ssids[ssids[i]["name"].strip()]
                ssids[i]["number"] = number
                numbers.remove(number)
        # give numbers to all new ones
        for i in range(len(ssids)):
            if "number" not in ssids[i]:
                ssids[i]["number"] = numbers.pop()

        for ssid in ssids:
            self.logger.info(f"adding ssid: {ssid['name']} with number {ssid['number']}")
            schedule = ssid.get("schedule")
            access = not ssid.get("wireless_clients_blocked_from_lan")
            for x in ["wireless_clients_blocked_from_lan", "schedule"]:
                if x in ssid:
                    del ssid[x]
            try:
                ssid.update(
                    {
                        "name": ssid["name"].strip(),
                        "networkId": nw_id
                    }
                )
                self.dashboard.wireless.updateNetworkWirelessSsid(**ssid)
                if ssid["name"] in splash_page_urls:
                    self.dashboard.wireless.updateNetworkWirelessSsidSplashSettings(
                        networkId=nw_id,
                        number=ssid["number"],
                        splashUrl=splash_page_urls[ssid["name"]],
                        useSplashUrl=True
                    )
            except Exception as e:
                fail_message = f"Failed adding {ssid['name']}"
                if len(e.args) == 1:
                    fail_message = f"Failed adding {ssid['name']}: {e.args[0]}"
                self.log_issue(
                    external_message=fail_message,
                    internal_message="Failed to add SSID",
                    api_response=e.args,
                    code=2061,
                    details=f"nw_id={nw_id} | ssid={ssid}",
                    category=1
                )

            try:
                self.logger.info(f"setting lan access for {ssid['name']} to {access}")
                self.dashboard.wireless.updateNetworkWirelessSsidFirewallL3FirewallRules(
                    networkId=nw_id,
                    number=ssid["number"],
                    allowLanAccess=access
                )
            except meraki.exceptions.APIError as e:
                set_to = "enabled" if ssid.get("wireless_clients_blocked_from_lan") else "disabled"
                self.log_issue(
                    external_message=f"Failed to set lan access to '{set_to}' for {ssid['name']}",
                    internal_message="Failed to set lan access for SSID",
                    api_response=e.args,
                    code=2062,
                    details=f"nw_id={nw_id} | ssid={ssid} | set_to={set_to}",
                    category=2
                )
            # check the schedule
            if schedule and schedule.lower() != "always available":
                times = self.get_wifi_schedules(schedule.lower())["ranges"]
                if times:
                    try:
                        self.dashboard.wireless.updateNetworkWirelessSsidSchedules(
                            networkId=nw_id,
                            number=ssid["number"],
                            enabled=True,
                            ranges=times
                        )
                    except meraki.exceptions.APIError as e:
                        self.log_issue(
                            external_message=f"Failed to update schedule for {ssid['name']}",
                            internal_message="Failed to update schedule for SSID",
                            api_response=e.args,
                            code=2063,
                            details=f"nw_id={nw_id} | ssid={ssid} | times={times}",
                            category=5
                        )
                else:
                    self.logger.info(f"no schedule for {ssid['name']} -- {ssid['number']}")
        return True

    def get_wifi_schedules(self, schedule):
        schedules = {
            "available 8-5 daily": {
                "enabled": True,
                "ranges": [
                    {
                        "startDay": "Sunday",
                        "startTime": "00:00:00",
                        "endDay": "Sunday",
                        "endTime": "08:00:00",
                    },
                    {
                        "startDay": "Sunday",
                        "startTime": "17:00:00",
                        "endDay": "Monday",
                        "endTime": "08:00:00",
                    },
                    {
                        "startDay": "Monday",
                        "startTime": "17:00:00",
                        "endDay": "Tuesday",
                        "endTime": "08:00:00",
                    },
                    {
                        "startDay": "Tuesday",
                        "startTime": "17:00:00",
                        "endDay": "Wednesday",
                        "endTime": "08:00:00",
                    },
                    {
                        "startDay": "Wednesday",
                        "startTime": "17:00:00",
                        "endDay": "Thursday",
                        "endTime": "08:00:00",
                    },
                    {
                        "startDay": "Thursday",
                        "startTime": "17:00:00",
                        "endDay": "Friday",
                        "endTime": "08:00:00",
                    },
                    {
                        "startDay": "Friday",
                        "startTime": "17:00:00",
                        "endDay": "Saturday",
                        "endTime": "08:00:00",
                    },
                    {
                        "startDay": "Saturday",
                        "startTime": "17:00:00",
                        "endDay": "Saturday",
                        "endTime": "23:59:59",
                    }
                ]
            },
            "available 8-5 daily except weekends": {
                "enabled": True,
                "ranges": [
                    {
                        "startDay": "Sunday",
                        "startTime": "00:00:00",
                        "endDay": "Monday",
                        "endTime": "08:00:00"
                    },
                    {
                        "startDay": "Monday",
                        "startTime": "17:00:00",
                        "endDay": "Tuesday",
                        "endTime": "08:00:00"
                    },
                    {
                        "startDay": "Tuesday",
                        "startTime": "17:00:00",
                        "endDay": "Wednesday",
                        "endTime": "08:00:00"
                    },
                    {
                        "startDay": "Wednesday",
                        "startTime": "17:00:00",
                        "endDay": "Thursday",
                        "endTime": "08:00:00"
                    },
                    {
                        "startDay": "Thursday",
                        "startTime": "17:00:00",
                        "endDay": "Friday",
                        "endTime": "08:00:00"
                    },
                    {
                        "startDay": "Friday",
                        "startTime": "17:00:00",
                        "endDay": "Saturday",
                        "endTime": "23:59:59"
                    }
                ]
            },
        }
        return schedules.get(schedule)

    def create_default_camera_profile(self, nwid):
        try:
            self.dashboard.camera.createNetworkCameraQualityRetentionProfile(
                networkId=nwid,
                name="Default"
            )
            return True
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to create default quality and retention profile",
                internal_message="Failed to create default quality and retention profile",
                api_response=e.args,
                code=2064,
                details=f"nwid={nwid}",
                category=2
            )
            return False

    def get_default_quality_and_retention_profile_id(self, nwid, log_fail=False):
        try:
            profiles = self.dashboard.camera.getNetworkCameraQualityRetentionProfiles(
                networkId=nwid
            )
            default = [p for p in profiles if p["name"] == "Default"]
            assert len(default) > 0
            return default[0]["id"]
        except (meraki.exceptions.APIError, AssertionError) as e:
            if log_fail:
                self.log_issue(
                    external_message="Failed to get default camera profile",
                    internal_message="Failed to get default camera profile",
                    api_response=e.args,
                    code=2065,
                    details=f"nwid={nwid}",
                    category=2
                )
            return None

    def setCameraSettings(self, serial, data, nwid):
        def resolution_map(res):
            if res is None:
                self.log_issue(
                    external_message="Camera resolution must be set in Design Portal if it is not bound to a profile",
                    internal_message="Camera resolution must be set in Design Portal if it is not bound to a profile",
                    api_response="",
                    code=2075,
                    details=f"nwid={nwid} | serial={serial} | nwid={data} | res={res}",
                    category=1
                )
                return None
            res = res.upper()
            resolutions = {
                '2880X2880': "2880x2880",
                '720P': "1280x720",
                '4MP': "2688x1512",
                '2112X2112': "2112x2112",
                '1080X1080': "1080x1080",
                '4K': "3840x2160",
                '1080P': "1920x1080"
            }
            if res not in resolutions:
                self.log_issue(
                    external_message=f"Failed to map camera resolution {res}",
                    internal_message="Failed to map camera resolution",
                    api_response="",
                    code=2066,
                    details=f"nwid={nwid} | serial={serial} | nwid={data} | res={res}",
                    category=1
                )
                return None
            else:
                return resolutions[res]

        try:
            payload = {}
            if data["mnc_default_video_settings"]:
                if self.default_qnr_camera_profile_id is None:
                    # we do not know the profile id, see it exists already
                    self.logger.info("searching for default camera q&r profile")
                    self.default_qnr_camera_profile_id = self.get_default_quality_and_retention_profile_id(nwid=nwid)
                    if self.default_qnr_camera_profile_id is None:
                        # could not find it, create it
                        self.logger.info("Could not find existing default camera q&r profile, creating one")
                        successfully_created_profile = self.create_default_camera_profile(nwid=nwid)
                        if successfully_created_profile:
                            time.sleep(3)
                            self.logger.info("getting id for q&r profile we just created")
                            self.default_qnr_camera_profile_id = self.get_default_quality_and_retention_profile_id(
                                nwid=nwid, log_fail=True)
                if self.default_qnr_camera_profile_id is None:
                    # something wrong happened when trying to create / get default profile
                    # and all errors should already be logged
                    return
                # add id to the payload
                payload["profileId"] = self.default_qnr_camera_profile_id

            else:  # not using the defualt settings
                if data.get("mnc_video_quality"):
                    payload["quality"] = data["mnc_video_quality"].lower().capitalize()
                else:
                    payload["quality"] = "Standard"
                resolution = resolution_map(data["mnc_video_resolution"])
                if not resolution:
                    # we should not assume a resolution like do with quality,
                    # doing so will probably cause a 400 response
                    # error logging for this contingency is handled by mapper
                    return
            self.dashboard.camera.updateDeviceCameraQualityAndRetention(
                serial=serial,
                **payload
            )
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to set quality and retention settings",
                internal_message="Failed to set quality and retention settings",
                api_response=e.args,
                code=2067,
                details=f"nwid={nwid} | serial={serial} | nwid={data} | res={payload}",
                category=1
            )

    def get_existing_sensor_profiles(self, nwid):
        try:
            return self.dashboard.sensor.getNetworkSensorAlertsProfiles(networkId=nwid)
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to get existing sensor profiles",
                internal_message="Failed to get existing sensor profiles",
                api_response=e.args,
                code=2068,
                details=f"nwid={nwid}",
                category=2
            )
            return []

    def sensor_profiles(self, profiles, nwid):
        if len(profiles) == 0:
            self.logger.info("no profiles to configure")
            return
        existing_profiles = self.get_existing_sensor_profiles(nwid)
        existing_profiles = {x["name"]: x["profileId"] for x in existing_profiles}
        self.logger.info(f"existing sensor profiles {existing_profiles}")
        for profile in profiles:
            self.create_sensor_profile(nwid=nwid, data=profile, existing_profiles=existing_profiles)

    def add_sensor_serials(self, dp_sensor_profiles, profile_serials, nwid):
        if len(dp_sensor_profiles) == 0:
            return
        existing_profiles = self.get_existing_sensor_profiles(nwid)
        existing_profiles = {x["name"]: x["profileId"] for x in existing_profiles}
        for dp_profile_name, serials in profile_serials.items():
            # profile should have been created already but if not, create it
            if dp_profile_name not in existing_profiles:
                self.logger.info(f"cannot find existing profile for {dp_profile_name}")
                profile = [p for p in dp_sensor_profiles if p["name"] == dp_profile_name][0]
                self.create_sensor_profile(nwid=nwid, data=profile, existing_profiles=existing_profiles)
                time.sleep(3)
                existing_profiles = self.get_existing_sensor_profiles(nwid)
                existing_profiles = {x["name"]: x["profileId"] for x in existing_profiles}
                if dp_profile_name not in existing_profiles:
                    self.log_issue(
                        external_message=f"issue occurred trying to add sensor profile: {dp_profile_name}",
                        internal_message="issue occurred trying to add sensor profile",
                        api_response="",
                        code=2069,
                        details=f"nwid={nwid} | existing_profiles={existing_profiles} | dp_profile_name={dp_profile_name} | profile={profile}",
                        category=1
                    )
                    continue
            # add serials to profile
            try:
                self.dashboard.sensor.updateNetworkSensorAlertsProfile(
                    networkId=nwid, id=existing_profiles.get(dp_profile_name), serials=serials
                )
            except (meraki.exceptions.APIError, AssertionError) as e:
                self.log_issue(
                    external_message=f"Failed to add serials to sensor profile: {dp_profile_name} | {e}",
                    internal_message="Failed to add serials to sensor profile",
                    api_response=e.args,
                    code=2070,
                    details=f"nwid={nwid} | existing_profiles={existing_profiles} | dp_profile_name={dp_profile_name}",
                    category=2
                )

    def create_sensor_profile(self, nwid, data, existing_profiles):
        def duration_map(duration):
            if duration is None:
                self.log_issue(
                    external_message=f"failed to determine duration: '{duration}' for profile {data['name']}",
                    internal_message="failed to determine sensor profile duration time",
                    api_response="",
                    code=2071,
                    details=f"nwid={nwid} | existing_profiles={existing_profiles} | duration={duration}",
                    category=1
                )
                return 0
            duration = duration.lower()
            if duration == "any amount of time":
                return 0
            duration_new = duration.split(" ")
            if len(duration_new) != 2:
                self.log_issue(
                    external_message=f"failed to determine duration: '{duration}' for profile {data['name']}",
                    internal_message="failed to determine sensor profile duration time",
                    api_response="",
                    code=2071,
                    details=f"nwid={nwid} | existing_profiles={existing_profiles} | duration={duration}",
                    category=1
                )
                return 0
            t, unit = duration_new
            if not t.isdigit():
                self.log_issue(
                    external_message=f"failed to determine duration: '{duration}' for profile {data['name']}",
                    internal_message="failed to determine sensor profile duration time",
                    api_response="",
                    code=2071,
                    details=f"nwid={nwid} | existing_profiles={existing_profiles} | duration={duration} | unit={unit}",
                    category=1
                )
                return 0
            if "second" in unit:
                return int(t)
            elif "minute" in unit:
                return int(t) * 60
            elif "hour" in unit:
                return int(t) * 60 * 60
            else:
                self.log_issue(
                    external_message=f"failed to determine duration: '{duration}' for profile {data['name']}",
                    internal_message="failed to determine sensor profile duration time",
                    api_response="",
                    code=2071,
                    details=f"nwid={nwid} | existing_profiles={existing_profiles} | duration={duration} | unit={unit}",
                    category=1
                )
                return 0
        try:
            self.logger.info(f"creating sensor profile: {data['name']}")
            payload = {
                "name": data["name"],
                "conditions": [],
                "recipients": {}
            }

            # temp
            if data.get("temperature_above_enabled"):
                payload["conditions"].append(
                    {
                        "metric": "temperature",
                        "threshold": {
                            "temperature": {
                                "celsius" if data["temperature_above_unit"] == "°C" else "fahrenheit": data[
                                    "temperature_above_value"]
                            }
                        },
                        "duration": duration_map(data["temperature_above_time"]),
                        "direction": "above"
                    }
                )
            if data.get("temperature_below_enabled"):
                payload["conditions"].append(
                    {
                        "metric": "temperature",
                        "threshold": {
                            "temperature": {
                                "celsius" if data["temperature_below_unit"] == "°C" else "fahrenheit": data[
                                    "temperature_below_value"]

                            }
                        },
                        "duration": duration_map(data["temperature_below_time"]),
                        "direction": "below"
                    }
                )
            if data.get("temperature_equal_to_or_below_enabled"):
                payload["conditions"].append(
                    {
                        "metric": "temperature",
                        "threshold": {
                            "temperature": {
                                "quality": data["temperature_equal_to_or_below_value"].lower()
                            }
                        },
                        "duration": duration_map(data["temperature_equal_to_or_below_time"]),
                        "direction": "below"
                    }
                )

            # humidity
            if data.get("humidity_above_enabled"):
                payload["conditions"].append(
                    {
                        "metric": "humidity",
                        "threshold": {
                            "humidity": {
                                "relativePercentage": data["humidity_above_value"]

                            }
                        },
                        "duration": duration_map(data["humidity_above_time"]),
                        "direction": "above"
                    }
                )
            if data.get("humidity_below_enabled"):
                payload["conditions"].append(
                    {
                        "metric": "humidity",
                        "threshold": {
                            "humidity": {
                                "relativePercentage": data["humidity_below_value"]
                            }
                        },
                        "duration": duration_map(data["humidity_below_time"]),
                        "direction": "below"
                    }
                )
            if data.get("humidity_equal_to_or_below_enabled"):
                payload["conditions"].append(
                    {
                        "metric": "humidity",
                        "threshold": {
                            "humidity": {
                                "quality": data["humidity_equal_to_or_below_value"].lower()
                            }
                        },
                        "duration": duration_map(data["humidity_equal_to_or_below_time"]),
                        "direction": "below"
                    }
                )

            # water
            if data.get("water_detection") and data["water_detection"] == "Enabled":
                payload["conditions"].append(
                    {
                        "metric": "water",
                        "threshold": {
                            "water": {
                                "present": True
                            }
                        }
                    }
                )

            # door
            if data.get("door_open") and data["door_open"] == "Enabled":
                payload["conditions"].append(
                    {
                        "metric": "door",
                        "threshold": {
                            "door": {
                                "open": True
                            }
                        },
                        "duration": 60
                    },
                )

            # recipients
            if data["alert_profile_recipient_email"]:
                emails = data["alert_profile_recipient_email"]
                emails = emails.replace(" ", ",")
                emails = emails.replace("\n", ",")
                emails = emails.split(",")
                emails = [e for e in emails if e not in [None, ""]]
                payload["recipients"]["emails"] = emails
            if data["alert_profile_recipient_sms"]:
                sms = data["alert_profile_recipient_sms"]
                sms = sms.replace(" ", ",")
                sms = sms.replace("\n", ",")
                sms = sms.split(",")
                sms = [s for s in sms if s not in [None, ""]]
                payload["recipients"]["smsNumbers"] = sms

            if data["name"] in existing_profiles:
                self.dashboard.sensor.updateNetworkSensorAlertsProfile(
                    networkId=nwid,
                    id=existing_profiles[data["name"]],
                    **payload
                )
                self.logger.info(f"updated sensor profile: {data['name']}")

            else:
                self.dashboard.sensor.createNetworkSensorAlertsProfile(
                    networkId=nwid,
                    **payload
                )
                self.logger.info(f"Created sensor profile: {data['name']}")

        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message=f"failed to add Sensor profile with name {data.get('name')} | {e}",
                internal_message="failed to add Sensor profile",
                api_response=e.args,
                code=2072,
                details=f"nwid={nwid} | existing_profiles={existing_profiles} | payload={payload}",
                category=1
            )

    def get_org_templates(self, orgid):
        try:
            response = self.dashboard.organizations.getOrganizationConfigTemplates(
                organizationId=orgid
            )
            return response
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed to get existing Organization templates",
                internal_message="Failed to get existing Organization templates",
                api_response=e.args,
                code=2073,
                details=f"orgid={orgid}",
                category=2
            )
            return []

    def create_org_template(self, orgid, template_data):
        try:
            response = self.dashboard.organizations.createOrganizationConfigTemplate(
                organizationId=orgid,
                **template_data
            )
            return response
        except (meraki.exceptions.APIError, AssertionError) as e:
            self.log_issue(
                external_message="Failed creating Organization template",
                internal_message="Failed creating Organization template",
                api_response=e.args,
                code=2074,
                details=f"orgid={orgid} | template_data={template_data}",
                category=2
            )
            return None

    def country_map(self, name):
        """
        maps an uppercase country name to its ISO 3166 alpha-2 code
        :return: (str) ISO 3166 alpha-2 country code
        """
        counties = {
            "AFGHANISTAN": "AF",
            "ALBANIA": "AL",
            "ALGERIA": "DZ",
            "AMERICAN SAMOA": "AS",
            "ANDORRA": "AD",
            "ANGOLA": "AO",
            "ANGUILLA": "AI",
            "ANTARCTICA": "AQ",
            "ANTIGUA AND BARBUDA": "AG",
            "ARGENTINA": "AR",
            "ARMENIA": "AM",
            "ARUBA": "AW",
            "AUSTRALIA": "AU",
            "AUSTRIA": "AT",
            "AZERBAIJAN": "AZ",
            "BAHAMAS": "BS",
            "BAHRAIN": "BH",
            "BANGLADESH": "BD",
            "BARBADOS": "BB",
            "BELARUS": "BY",
            "BELGIUM": "BE",
            "BELIZE": "BZ",
            "BENIN": "BJ",
            "BERMUDA": "BM",
            "BHUTAN": "BT",
            "BOLIVIA": "BO",
            "BOSNIA AND HERZEGOVINA": "BA",
            "BOTSWANA": "BW",
            "BRAZIL": "BR",
            "BRITISH INDIAN OCEAN TERRITORY": "IO",
            "BRITISH VIRGIN ISLANDS": "VG",
            "BRUNEI": "BN",
            "BULGARIA": "BG",
            "BURKINA FASO": "BF",
            "BURUNDI": "BI",
            "CAMBODIA": "KH",
            "CAMEROON": "CM",
            "CANADA": "CA",
            "CAPE VERDE": "CV",
            "CAYMAN ISLANDS": "KY",
            "CENTRAL AFRICAN REPUBLIC": "CF",
            "CHAD": "TD",
            "CHILE": "CL",
            "CHINA": "CN",
            "CHRISTMAS ISLAND": "CX",
            "COCOS ISLANDS": "CC",
            "COLOMBIA": "CO",
            "COMOROS": "KM",
            "COOK ISLANDS": "CK",
            "COSTA RICA": "CR",
            "CROATIA": "HR",
            "CUBA": "CU",
            "CURACAO": "CW",
            "CYPRUS": "CY",
            "CZECH REPUBLIC": "CZ",
            "DEMOCRATIC REPUBLIC OF THE CONGO": "CD",
            "DENMARK": "DK",
            "DJIBOUTI": "DJ",
            "DOMINICA": "DM",
            "DOMINICAN REPUBLIC": "DO",
            "EAST TIMOR": "TL",
            "ECUADOR": "EC",
            "EGYPT": "EG",
            "EL SALVADOR": "SV",
            "EQUATORIAL GUINEA": "GQ",
            "ERITREA": "ER",
            "ESTONIA": "EE",
            "ETHIOPIA": "ET",
            "FALKLAND ISLANDS": "FK",
            "FAROE ISLANDS": "FO",
            "FIJI": "FJ",
            "FINLAND": "FI",
            "FRANCE": "FR",
            "FRENCH POLYNESIA": "PF",
            "GABON": "GA",
            "GAMBIA": "GM",
            "GEORGIA": "GE",
            "GERMANY": "DE",
            "GHANA": "GH",
            "GIBRALTAR": "GI",
            "GREECE": "GR",
            "GREENLAND": "GL",
            "GRENADA": "GD",
            "GUAM": "GU",
            "GUATEMALA": "GT",
            "GUERNSEY": "GG",
            "GUINEA": "GN",
            "GUINEA-BISSAU": "GW",
            "GUYANA": "GY",
            "HAITI": "HT",
            "HONDURAS": "HN",
            "HONG KONG": "HK",
            "HUNGARY": "HU",
            "ICELAND": "IS",
            "INDIA": "IN",
            "INDONESIA": "ID",
            "IRAN": "IR",
            "IRAQ": "IQ",
            "IRELAND": "IE",
            "ISLE OF MAN": "IM",
            "ISRAEL": "IL",
            "ITALY": "IT",
            "IVORY COAST": "CI",
            "JAMAICA": "JM",
            "JAPAN": "JP",
            "JERSEY": "JE",
            "JORDAN": "JO",
            "KAZAKHSTAN": "KZ",
            "KENYA": "KE",
            "KIRIBATI": "KI",
            "KOSOVO": "XK",
            "KUWAIT": "KW",
            "KYRGYZSTAN": "KG",
            "LAOS": "LA",
            "LATVIA": "LV",
            "LEBANON": "LB",
            "LESOTHO": "LS",
            "LIBERIA": "LR",
            "LIBYA": "LY",
            "LIECHTENSTEIN": "LI",
            "LITHUANIA": "LT",
            "LUXEMBOURG": "LU",
            "MACAU": "MO",
            "MACEDONIA": "MK",
            "MADAGASCAR": "MG",
            "MALAWI": "MW",
            "MALAYSIA": "MY",
            "MALDIVES": "MV",
            "MALI": "ML",
            "MALTA": "MT",
            "MARSHALL ISLANDS": "MH",
            "MAURITANIA": "MR",
            "MAURITIUS": "MU",
            "MAYOTTE": "YT",
            "MEXICO": "MX",
            "MICRONESIA": "FM",
            "MOLDOVA": "MD",
            "MONACO": "MC",
            "MONGOLIA": "MN",
            "MONTENEGRO": "ME",
            "MONTSERRAT": "MS",
            "MOROCCO": "MA",
            "MOZAMBIQUE": "MZ",
            "MYANMAR": "MM",
            "NAMIBIA": "NA",
            "NAURU": "NR",
            "NEPAL": "NP",
            "NETHERLANDS": "NL",
            "NETHERLANDS ANTILLES": "AN",
            "NEW CALEDONIA": "NC",
            "NEW ZEALAND": "NZ",
            "NICARAGUA": "NI",
            "NIGER": "NE",
            "NIGERIA": "NG",
            "NIUE": "NU",
            "NORTH KOREA": "KP",
            "NORTHERN MARIANA ISLANDS": "MP",
            "NORWAY": "NO",
            "OMAN": "OM",
            "PAKISTAN": "PK",
            "PALAU": "PW",
            "PALESTINE": "PS",
            "PANAMA": "PA",
            "PAPUA NEW GUINEA": "PG",
            "PARAGUAY": "PY",
            "PERU": "PE",
            "PHILIPPINES": "PH",
            "PITCAIRN": "PN",
            "POLAND": "PL",
            "PORTUGAL": "PT",
            "PUERTO RICO": "PR",
            "QATAR": "QA",
            "REPUBLIC OF THE CONGO": "CG",
            "REUNION": "RE",
            "ROMANIA": "RO",
            "RUSSIA": "RU",
            "RWANDA": "RW",
            "SAINT BARTHELEMY": "BL",
            "SAINT HELENA": "SH",
            "SAINT KITTS AND NEVIS": "KN",
            "SAINT LUCIA": "LC",
            "SAINT MARTIN": "MF",
            "SAINT PIERRE AND MIQUELON": "PM",
            "SAINT VINCENT AND THE GRENADINES": "VC",
            "SAMOA": "WS",
            "SAN MARINO": "SM",
            "SAO TOME AND PRINCIPE": "ST",
            "SAUDI ARABIA": "SA",
            "SENEGAL": "SN",
            "SERBIA": "RS",
            "SEYCHELLES": "SC",
            "SIERRA LEONE": "SL",
            "SINGAPORE": "SG",
            "SINT MAARTEN": "SX",
            "SLOVAKIA": "SK",
            "SLOVENIA": "SI",
            "SOLOMON ISLANDS": "SB",
            "SOMALIA": "SO",
            "SOUTH AFRICA": "ZA",
            "SOUTH KOREA": "KR",
            "SOUTH SUDAN": "SS",
            "SPAIN": "ES",
            "SRI LANKA": "LK",
            "SUDAN": "SD",
            "SURINAME": "SR",
            "SVALBARD AND JAN MAYEN": "SJ",
            "SWAZILAND": "SZ",
            "SWEDEN": "SE",
            "SWITZERLAND": "CH",
            "SYRIA": "SY",
            "TAIWAN": "TW",
            "TAJIKISTAN": "TJ",
            "TANZANIA": "TZ",
            "THAILAND": "TH",
            "TOGO": "TG",
            "TOKELAU": "TK",
            "TONGA": "TO",
            "TRINIDAD AND TOBAGO": "TT",
            "TUNISIA": "TN",
            "TURKEY": "TR",
            "TURKMENISTAN": "TM",
            "TURKS AND CAICOS ISLANDS": "TC",
            "TUVALU": "TV",
            "U.S. VIRGIN ISLANDS": "VI",
            "UGANDA": "UG",
            "UKRAINE": "UA",
            "UNITED ARAB EMIRATES": "AE",
            "UNITED KINGDOM": "GB",
            "UNITED STATES": "US",
            "URUGUAY": "UY",
            "UZBEKISTAN": "UZ",
            "VANUATU": "VU",
            "VATICAN": "VA",
            "VENEZUELA": "VE",
            "VIETNAM": "VN",
            "WALLIS AND FUTUNA": "WF",
            "WESTERN SAHARA": "EH",
            "YEMEN": "YE",
            "ZAMBIA": "ZM",
            "ZIMBABWE": "ZW",
        }
        return counties.get(name, None)
