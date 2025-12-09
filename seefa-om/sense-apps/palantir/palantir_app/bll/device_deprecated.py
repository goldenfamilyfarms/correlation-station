import ipaddress
import logging
import platform
import socket
import subprocess  # noqa: S404
import re

from copy import deepcopy

from common_sense.common.errors import abort
from palantir_app.bll.ipc import get_ip_from_tid_deprecated
from palantir_app.bll.ise import (
    determine_ise_secret,
    onboard_device_in_ise,
    id_lookup_cluster,
    get_ise_record_by_id_cluster_specified,
    update_shared_secret,
)
from palantir_app.common.endpoints import CROSSWALK_IPBLOCK
from palantir_app.dll.granite import get_device_vendor_model_site_category, update_granite_shelf
from palantir_app.dll.ipc import ipc_get
from palantir_app.dll.sense import beorn_get
from palantir_app.dll.tacacs import get_tacacs_status, remediate_tacacs_connection


logger = logging.getLogger(__name__)


class Device:
    """Create a readable dataclass for each device"""

    def __init__(self, device_attributes: list, cid: str = "") -> None:
        """Initialize device"""
        self._var_init(device_attributes, cid)
        self._prerequisite_validation_process()
        self._set_prequisite_is_err_state()

    def _var_init(self, device_attributes: list, cid: str):
        """Initialize device from granite device_list output"""
        self.cid = cid
        self.ip = device_attributes[0]
        self.tid = device_attributes[1][0:11]
        self.fqdn = device_attributes[2]
        self.vendor = device_attributes[5]  # use Granite value until SNMP confirms
        self.is_cpe = True if re.match(".{9}[WXYZ]W", self.tid.upper()) else False
        self.model = None
        self.tacacs_remediation_required = False
        self.ise_success = False
        # l2circuit validation attributes
        self.port = device_attributes[3]
        self.vlan = device_attributes[4]
        self.chan_name = device_attributes[6]
        self.eq_type = device_attributes[7]
        self.leg_name = device_attributes[8]
        # process reporting attributes
        # initial validations must pass before secondary validations can be performed
        self.prerequisite_validated = {
            "ping": False,  # no IPs associated with device ping
            "hostname": False,  # hostname mismatch
            "snmp": False,  # snmp not enabled, so we can't validate hostname
        }
        # validation states, to be updated throughout process as each criteria is validated
        self.validated = {
            "tacacs": False  # unable to log in using TACACS creds
        }
        self.msg = {}

    def set_is_err_state(self):
        logger.debug(f"{self.cid} Validated: {self.validated}")
        self.is_err_state = False if all(self.validated.values()) else True

    def _prerequisite_validation_process(self):
        """
        Gather device properties to perform validations against. Confirm property viability.
        Failure to gather minimum required viable properties results in fast fail.
        Process:
            IP Gathering (IPC, DNS, Granite)
            Ping Check (IPC, DNS, Granite)
            Hostname Validation (SNMP)
            Granite Remediation Check (CPE Only *Does not report*)
            FQDN Resolves
        """
        # gather IPs to ping test
        self.ipc_ip = self._get_ipc_ip()
        self.dns_ip = self._get_dns_ip(self.fqdn)
        pingable_ips = self._get_pingable_ips()
        if pingable_ips:
            # validate host name using pingable IPs; first validated results in usable IP
            self.usable_ip = self._get_validated_hostname_ip(pingable_ips)
        else:
            self.usable_ip = None
            # unable to send SNMP request for host name without pingable IP
            self.msg.update({"HOSTNAME_VALIDATION": "PING CHECK FAILED"})
        # determine if we need to update Granite to align with IPC
        self.granite_remediation_required = self._is_granite_remediation_required()
        self._validate_fqdn_resolves()

    def _get_ipc_ip(self):
        """Returns an IP from IP Control for a given TID"""
        ipc_response = get_ip_from_tid_deprecated(self.tid, self.vendor, verbose=True)
        if ipc_response:
            if "ERROR" in ipc_response:
                self.msg.update({"CROSSWALK_IPC_CALL": "NOT FOUND"})
            else:
                self.msg.update({"CROSSWALK_IPC_CALL": "SUCCESS"})
        return ipc_response

    def _get_dns_ip(self, host):
        try:
            return socket.gethostbyname(host)
        except socket.gaierror:
            logger.info(f"DNS Call - Unable to resolve {self.fqdn}")
            return None
        except TypeError:
            logger.info(f"DNS Call - Unable to resolve {self.fqdn}")
            return None
        except UnicodeError:
            logger.info(f"DNS Call - FQDN Malformed {self.fqdn}")
            abort(502, f"DNS Call - FQDN Malformed({self.fqdn})")

    def _get_pingable_ips(self):
        """get all pingable IPs from available IP data"""

        # Using the dictionary we will remove any duplicate keys so each unique IP is tried once.
        # THe IPs are tried in order of importance so IPC, IPC(DNS), Granite
        ips = {self.ipc_ip: False, self.dns_ip: False}
        if self.ip and self.ip != "DHCP":
            ips.update({self.ip.split("/")[0]: False})
        logger.debug(f"{self.cid} IPs from all sources: {ips.keys()}")

        # Granite data can be None so we need to filter out the None values
        validated_ips = {k: v for k, v in ips.items() if k is not None}

        logger.info(f"{self.cid} IPs to ping test: {validated_ips}")

        for ip in validated_ips:
            if self._is_ip_pinging(ip):
                validated_ips[ip] = True

        if any(validated_ips.values()):
            # something is pingy, yay!
            self.prerequisite_validated.update({"ping": True})
            pingable_ips = deepcopy(validated_ips)
            for ip, pingable in validated_ips.items():
                if not pingable:
                    pingable_ips.pop(ip, None)
            logger.debug(f"{self.cid} IPs pinging: {pingable_ips}")
            return pingable_ips
        else:
            # If we get here we have no pingable IPs and cannot proceed past prerequisite validations
            logger.info(f"PING_CHECK - Unable to verify IP for {self.tid}")
            self._update_ip_ping_status(success=False)
            return None

    def _is_ip_pinging(self, ip):
        if self._is_ip_valid(ip):
            param = "-n" if platform.system().lower() == "windows" else "-c"
            command = ["ping", param, "1", ip]
            return subprocess.call(command) == 0  # noqa: S603

    def _is_ip_valid(self, ipaddr):
        """Returns True if IP address is valid"""
        try:
            ipaddress.ip_address(ipaddr)
            return True
        except ValueError:
            return False

    def _get_validated_hostname_ip(self, pingable_ips):
        for ip, pingable in pingable_ips.items():
            if self._is_validated_hostname(ip):
                self.msg.update({"HOSTNAME_VALIDATION": "SUCCESS"})
                self.prerequisite_validated.update({"hostname": True})
                self._update_ip_ping_status(ip, pingable)  # at this point pingable should always be True
                logger.debug(f"{self.cid} determined usable IP: {ip}")
                return ip  # first one to validate hostname wins
        # IP pings but SNMP not enabled prevents hostname validation
        logger.info(f"HOSTNAME_VALIDATION - SNMP Call Could not find {self.tid} on device")
        self.msg.update({"HOSTNAME_VALIDATION": "FAILED SNMP VALIDATION"})
        return None

    def _is_validated_hostname(self, ip: str):
        """Validate hostname (TID) using SNMP"""
        found_tid = self._get_device_hostname_by_snmp(ip)
        logger.info(f"SNMP TID VALIDATION - FOUND TID... {found_tid}")
        if found_tid and self.tid.upper() in found_tid.upper():
            return True
        else:
            return False

    def _get_device_hostname_by_snmp(self, ip: str = "") -> str:
        beorn_response = beorn_get("/v1/device/system_info", params={"device_id": ip})
        if beorn_response.keys() != {"error"}:
            self.msg.pop("SNMP_DISABLED", None)
            self.prerequisite_validated.pop("snmp", None)  # this has served its purpose now
            return beorn_response.get("name")
        else:
            logger.info(f"SNMP IS DISABLED on {ip}")
            self.msg.update({"SNMP_DISABLED": "FAILED"})
            return ""

    def _update_ip_ping_status(self, ipaddr=None, success: bool = False) -> dict:
        reference_dict = {
            "IPC API": self.ipc_ip,
            "IPC DNS": self.dns_ip,
            "GRANITE": self.ip.split("/")[0] if self.ip else None,
        }
        status = "SUCCESS" if success else "FAILED"
        if ipaddr:
            for label, ip in reference_dict.items():
                if ipaddr == ip:
                    self.msg.update({"PING_CHECK": {"STATUS": status, "IP": ipaddr, "SOURCE": label}})
                    break
        else:
            self.msg.update({"PING_CHECK": {"STATUS": status, "IP": "N/A", "SOURCE": "N/A"}})

    def _is_granite_remediation_required(self):
        # we only update CPE IPs
        if not self.is_cpe:
            return False
        if not self.ip:  # no IP found in Granite
            return True
        # IP in Granite is either DHCP or differs from the validated hostname IP
        if self.ip == "DHCP" or self.ip.split("/")[0] != self.usable_ip:
            return True
        return False

    def _validate_fqdn_resolves(self):
        """Informational for API response, does not trigger fallout"""
        if self.dns_ip == self.usable_ip:
            self.msg.update({"FQDN_RESOLVES": True})
        else:
            self.msg.update({"FQDN_RESOLVES": False})

    def _set_prequisite_is_err_state(self):
        logger.debug(f"{self.cid} Prequisite Validated: {self.prerequisite_validated}")
        self.is_err_state = False if all(self.prerequisite_validated.values()) else True

    def determine_vendor_and_model(self):
        """Uses Beorn SNMP to determine vendor and model of device"""
        device_vendor_model = self._get_vendor_and_model_by_ip(self.usable_ip, self.tid)
        self.vendor = device_vendor_model["vendor"]
        self.model = device_vendor_model["model"]

    def _get_vendor_and_model_by_ip(self, ipaddr: str, tid: str) -> dict:
        """This function will return the vendor and model of the device based on the IP address."""
        beorn_response = beorn_get("/v1/device", params={"ip": ipaddr})
        if beorn_response.keys() != {"error"}:
            vendor = beorn_response["vendor"]
            model = beorn_response["model"]
        else:
            device_info = get_device_vendor_model_site_category(tid)
            vendor = device_info["vendor"]
            model = device_info["model"]
        return {"vendor": vendor, "model": model}

    def determine_tacacs(self):
        try:
            status = get_tacacs_status(self.usable_ip)
            if "Auth" in status:
                self.msg.update({"TACACS": "AUTH FAILED - REMEDIATION REQUIRED"})
                if self.vendor in ["ADVA", "RAD"]:
                    if self.vendor == "ADVA":
                        # for now we are unable to remediate Adva netconf devices
                        # do not set tacacs remediation required to True to prevent automated remediation effort
                        # fallout will then be triggered by self.validated["tacacs"] False value
                        return
                    self.tacacs_remediation_required = True
            elif status == "Success":
                self.msg.update({"TACACS": "SUCCESS"})
                self.validated.update({"tacacs": True})
            elif "Failed" in status:
                self.msg.update({"TACACS": "FAILED ERROR"})
        except Exception as e:
            logger.error(f"TACACS - Exception: {e}")
            self.msg.update({"TACACS": f"EXCEPTION ERROR {e}"})

    def remediate_tacacs(self):
        logger.info("---------------STARTING TACACS REMEDIATION---------------")
        remediation_response = remediate_tacacs_connection(self.usable_ip, self.tid, self.vendor, use_local_creds=True)
        if "Success" in remediation_response.keys():
            self.msg.update({"TACACS_REMEDIATION": "SUCCESS (CONFIG ACCEPTED)"})
        else:
            logger.info(f"TACACS REMEDIATION - Failed for {self.tid}({self.usable_ip})")
            self.msg.update({"TACACS_REMEDIATION": "FAILED TO REMEDIATE"})
            self.tacacs_remediation_required = True

    def ise_check(self):
        ise_response, onboarded = onboard_device_in_ise(self.tid, self.usable_ip)
        if (
            isinstance(ise_response, dict) and "Onboarding Not Attempted" in ise_response["message"]
        ):  # core is assumed to be onboarded
            logger.info("Core device, ISE onboarding not performed")
        elif onboarded:
            self.msg.update({"ISE": "SUCCESS"})
            self.ise_success = True
        else:
            if "NDG cannot be found" in ise_response or not ise_response:
                self.msg.update({"ISE": "DEVICE NOT FOUND"})
            elif "Device Name Already Exist" in ise_response:
                self.msg.update({"ISE": "DEVICE ALREADY EXISTS"})
                self._process_ise_secret()

    def _process_ise_secret(self):
        logger.debug("Time to check the secrets")
        ise_id, cluster = self._get_device_ise_id_and_region()
        if not ise_id:
            return
        ise_device = self._get_ise_device(ise_id, cluster)
        if not ise_device:
            return
        sense_shared_secret = determine_ise_secret(self.vendor)
        validated_secret = self._compare_secrets(ise_device, sense_shared_secret)
        if validated_secret:
            logger.debug("Secrets match!")
            self.msg.update({"ISE": "SUCCESS"})
            self.ise_success = True
            return
        self._update_ise_secret(ise_id, sense_shared_secret)

    def _get_device_ise_id_and_region(self):
        logger.debug(f"Finding ISE ID for device {self.usable_ip}")
        _, ise_results = id_lookup_cluster(lookup_type="ipaddress", device_id=self.usable_ip)
        region = ise_results["region"]
        populated_cluster = ise_results.get(f"{region}_result")
        if populated_cluster:
            return populated_cluster[0]["id"], region
        else:
            # no device found
            self.msg.update({"ISE": "UNABLE TO FIND DEVICE ID"})
            return "", ""

    def _get_ise_device(self, ise_id, cluster):
        logger.debug(f"Getting the device by ISE ID in cluster {cluster}")
        response = get_ise_record_by_id_cluster_specified(ise_id, cluster)
        logger.debug(f"{response = }")
        for device in response:
            if device["name"] == self.tid:
                return device

    def _compare_secrets(self, ise_device, sense_shared_secret):
        # validate secret from ISE against secret we use
        if not ise_device.get("tacacsSettings"):
            return False  # can't be right if it doesn't exist!
        return ise_device["tacacsSettings"]["sharedSecret"] == sense_shared_secret

    def _update_ise_secret(self, ise_id, sense_shared_secret):
        logger.debug("We need to update this ancient secret.")
        state = self.tid[4:6]
        updated_secret = update_shared_secret(ise_id, sense_shared_secret, self.usable_ip, state)
        if updated_secret:
            self.msg.update({"ISE": "SUCCESS"})
            self.ise_success = True
        else:
            self.msg.update({"ISE": "DEVICE ALREADY EXISTS WITH INCORRECT SECRET"})

    def remediate_boundary(self):
        # This is going to be best effort align Granite with IPC data
        if self.granite_remediation_required:
            self.update_granite_ip(self.usable_ip)

    def update_granite_ip(self, ip):
        cidr = _init_export_child_block(ip)
        ipaddr_with_cidr = ip + "/" + cidr
        # Call Granite to update Shelf with new IP Addr
        logger.info("GRANITE IP UPDATE - Updating Granite Shelf...")
        if self.cid:
            shelf = update_granite_shelf(self.tid, ipaddr_with_cidr, self.cid)
        else:
            shelf = update_granite_shelf(self.tid, ipaddr_with_cidr)
        if shelf:
            logger.info("GRANITE IP UPDATE - Updated Successfully.")
            self.msg.update({"GRANITE_IP_UPDATE": "SUCCESS"})
        else:
            logger.info("GRANITE IP UPDATE - Failed")
            self.msg.update({"GRANITE_IP_UPDATE": "FAILED"})

    def __repr__(self) -> str:
        return f"Device(TID:{self.tid}, GRANITE_IP:{self.ip}, GRANITE_FQDN:{self.fqdn})"

    def __str__(self) -> str:
        return f"Device(TID:{self.tid}, GRANITE_IP:{self.ip}, GRANITE_FQDN:{self.fqdn})"


def _init_export_child_block(ipaddr):
    """
    uses ip address from ip control then looks for child block/CIDR to attach to
    update_granite_shelf
    """
    params = {"ipAddress": ipaddr}
    data = ipc_get(CROSSWALK_IPBLOCK, params)
    logger.debug(f"{data = }")
    block = data[0]["childBlock"]["blockSize"]
    logger.debug(f"child block found - {block}")
    return block
