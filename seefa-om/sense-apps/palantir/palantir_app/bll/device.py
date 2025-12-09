import ipaddress
import logging
import platform
import socket
import subprocess  # noqa: S404
import re

from copy import deepcopy

from common_sense.common.errors import abort
from palantir_app.bll.ipc import get_ip_from_tid
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

    def __init__(self, device_attributes: dict, cid: str = "") -> None:
        """Initialize device"""
        self._var_init(device_attributes, cid)
        self._prerequisite_validation_process()
        self._set_prequisite_is_err_state()

    def _var_init(self, device_attributes: dict, cid: str):
        """Initialize device from granite device_list output"""
        self.cid = cid
        self.ip = device_attributes["ip"]
        if self.ip and self.ip != "DHCP":
            self.ip = self.ip.split("/")[0]
        self.tid = device_attributes["tid"]
        self.fqdn = device_attributes["fqdn"]
        self.vendor = device_attributes["vendor"]  # use Granite value until SNMP confirms
        self.is_cpe = True if re.match(".{9}[WXYZ]W", self.tid.upper()) else False
        self.model = None  # will update using SNMP response
        self.tacacs_remediation_required = False
        self.ise_success = False
        # l2circuit validation attributes
        self.port = device_attributes["port"]
        self.vlan = device_attributes["vlan"]
        self.chan_name = device_attributes["channel"]
        self.eq_type = device_attributes["category"]
        self.leg_name = device_attributes["leg"]
        # gather IPs to ping test
        self.ips_by_source = {
            "ipc": get_ip_from_tid(self.tid, self.vendor),
            "dns": self._get_dns_ip(self.fqdn),
            "granite": self.ip,
        }
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
        self.msg = {
            "hostname": {},  # granite TID comparison against device TID via SNMP
            "ip": {},  # designated usable IP determined by pingability and hostname match
            "fqdn": {},  # DNS IP from FQDN matches usable IP
            "tacacs": {},  # login via TACACS creds
            "ise": {},  # onboard device to ISE
            "granite": {},  # track database reconciliation efforts
            "reachable": "",  # preferred method of accessing device - FQDN if resolves else usable IP
        }

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
        pingable_ips = self._get_pingable_ips()
        if pingable_ips:
            # validate host name using pingable IPs; first validated results in usable IP
            self.usable_ip = self._get_validated_hostname_ip(pingable_ips)
        else:
            # unable to send SNMP request for host name without pingable IP
            self.usable_ip = None
            self.msg["hostname"].update({"status": "failed", "message": "no usable ip", "data": {}})
            self.msg["ip"].update({"status": "failed", "message": "no pingable ip found", "data": self.ips_by_source})
        # determine if we need to update Granite to align with IPC
        self.granite_remediation_required = self._is_granite_remediation_required()
        self._validate_fqdn_resolves()
        self._set_reachable()

    def _get_dns_ip(self, host):
        try:
            return socket.gethostbyname(host)
        except socket.gaierror:
            logger.info(f"DNS Call - Unable to resolve {self.fqdn}")
            return
        except TypeError:
            logger.info(f"DNS Call - Unable to resolve {self.fqdn}")
            return
        except UnicodeError:
            logger.info(f"DNS Call - FQDN Malformed {self.fqdn}")
            abort(502, f"DNS Call - FQDN Malformed({self.fqdn})")

    def _get_pingable_ips(self):
        """get all pingable IPs from available IP data"""
        # THe IPs are tried in order of importance so IPC, IPC(DNS), Granite
        logger.debug(f"{self.cid} IPs from all sources: {self.ips_by_source}")
        # Granite data can be None so we need to filter out the None values
        untestable_ip_types = [None, "DHCP", ""]
        ping_test_ips = {}
        for source, ip in self.ips_by_source.items():
            if ip not in untestable_ip_types:
                ping_test_ips[ip] = {"source": source, "validated": False}

        logger.info(f"{self.cid} IPs to ping test: {ping_test_ips}")

        for ip in ping_test_ips:
            if self._is_ip_pinging(ip):
                ping_test_ips[ip]["validated"] = True

        if any(ping_test_ips[ip]["validated"] for ip in ping_test_ips):
            # something is pingy, yay!
            self.prerequisite_validated.update({"ping": True})
            pingable_ips = deepcopy(ping_test_ips)
            for ip, pingable in ping_test_ips.items():
                if not pingable["validated"]:
                    pingable_ips.pop(ip, None)
            logger.debug(f"{self.cid} IPs pinging: {pingable_ips}")
            return pingable_ips
        else:
            # If we get here we have no pingable IPs and cannot proceed past prerequisite validations
            logger.info(f"PING_CHECK - Unable to verify IP for {self.tid}")

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
        snmp_error = False
        for ip in pingable_ips:
            validated, found_tid = self._is_validated_hostname(ip, pingable_ips[ip]["source"])
            if validated:
                self.msg["hostname"].update({"status": "validated", "message": "device name matches design"})
                self.msg["ip"].update(
                    {"status": "validated", "message": f"usable: {ip} source: {pingable_ips[ip]['source']}"}
                )
                self.prerequisite_validated.update({"hostname": True})
                logger.debug(f"{self.cid} {self.tid} determined usable IP: {ip}")
                return ip  # first one to validate hostname wins
            if not found_tid:
                snmp_error_ip = ip
                snmp_error = True
        if snmp_error:
            self.msg["hostname"].update(
                {
                    "status": "failed",
                    "message": "snmp error",
                    "data": {"ip": snmp_error_ip, "source": pingable_ips[snmp_error_ip]["source"]},
                }
            )
        else:
            # IP pings but SNMP and Granite TID does not align
            logger.info(f"HOSTNAME_VALIDATION - SNMP Call Could not find {self.tid} on device")
            self.msg["hostname"].update(
                {
                    "status": "failed",
                    "message": "device name mismatch",
                    "data": {"ip": ip, "granite": self.tid, "snmp": found_tid},
                }
            )

    def _is_validated_hostname(self, ip: str, source: str):
        """Validate hostname (TID) using SNMP"""
        found_tid = self._get_device_hostname_by_snmp(ip, source)
        logger.info(f"SNMP TID VALIDATION - FOUND TID... {found_tid}")
        if found_tid and self.tid.upper() in found_tid.upper():
            return True, found_tid
        else:
            return False, found_tid

    def _get_device_hostname_by_snmp(self, ip: str, source: str) -> str:
        beorn_response = beorn_get("/v1/device/system_info", params={"device_id": ip})
        if beorn_response.keys() != {"error"}:
            self.prerequisite_validated.pop("snmp", None)  # this has served its purpose now
            return beorn_response.get("name")
        else:
            logger.info(f"SNMP IS DISABLED on {ip} found in {source}")
            return ""

    def _is_granite_remediation_required(self):
        if not self.usable_ip:
            # none of the IPs were valid, not sure what to update to
            # we'll fail in the prereq process for being unable to validate hostname without a usable IP
            return False
        # we only update CPE IPs
        if not self.is_cpe:
            self.msg.pop("granite", None)  # no need to reconcile databases
            return False
        if not self.ip:  # no IP found in Granite
            return True
        # IP in Granite is either DHCP or differs from the validated hostname IP
        if self.ip == "DHCP" or self.ip.split("/")[0] != self.usable_ip:
            self.msg["granite"].update(
                {
                    "status": "reconciliation required",
                    "message": "database disagreement",
                    "data": {"found": self.ips_by_source, "usable": self.usable_ip},
                }
            )
            return True
        self.msg.pop("granite", None)  # no need to reconcile databases
        return False

    def _validate_fqdn_resolves(self):
        """Informational for API response, does not trigger fallout"""
        if self.ips_by_source["dns"] == self.usable_ip:
            self.msg["fqdn"].update({"status": "validated", "message": "fqdn resolves to usable ip"})
        else:
            self.msg["fqdn"].update(
                {
                    "status": "failed",
                    "message": "not resolvable",
                    "data": {"fqdn": self.fqdn, "dns": self.ips_by_source["dns"], "usable": self.usable_ip},
                }
            )

    def _set_reachable(self):
        """Define reachable host name in order of preference: FQDN (resolvable), IP (usable)"""
        if self.msg["fqdn"].get("status") == "validated":
            self.msg["reachable"] = self.fqdn
        elif self.usable_ip:
            self.msg["reachable"] = self.usable_ip
        else:
            logger.warning("device is not reachable")

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
                self.msg["tacacs"].update(
                    {
                        "status": "failed",
                        "message": "authentication error",
                        "data": {
                            "ip": self.usable_ip,
                            "vendor": self.vendor,
                            "model": self.model,
                            "role": self.eq_type,
                            "response": status,
                        },
                    }
                )
                if self.vendor in ["ADVA", "RAD"]:  # supported for remediation
                    if self.vendor == "ADVA":
                        # for now we are unable to remediate Adva netconf devices
                        # do not set tacacs remediation required to True to prevent automated remediation effort
                        # fallout will then be triggered by self.validated["tacacs"] False value
                        return
                    self.tacacs_remediation_required = True
            elif status == "Success":
                self.msg["tacacs"].update({"status": "validated", "message": "logged in successfully"})
                self.validated.update({"tacacs": True})
            elif "Failed" in status:
                self.msg["tacacs"].update(
                    {
                        "status": "failed",
                        "message": "unexpected error",
                        "data": {
                            "ip": self.usable_ip,
                            "vendor": self.vendor,
                            "model": self.model,
                            "role": self.eq_type,
                            "response": status,
                        },
                    }
                )
        except Exception as e:
            logger.error(f"TACACS - Exception: {e}")
            self.msg["tacacs"].update(
                {
                    "status": "failed",
                    "message": "unhandled error",
                    "data": {
                        "ip": self.usable_ip,
                        "vendor": self.vendor,
                        "model": self.model,
                        "role": self.eq_type,
                        "response": str(e),
                    },
                }
            )

    def remediate_tacacs(self):
        logger.info("---------------STARTING TACACS REMEDIATION---------------")
        remediation_response = remediate_tacacs_connection(self.usable_ip, self.tid, self.vendor, use_local_creds=True)
        if "Success" in remediation_response.keys():
            self.msg["tacacs"].update({"status": "validated", "message": "tacacs config applied"})
            # the metadata is now stale, remove it
            self.msg["tacacs"].pop("data", None)
        else:
            logger.info(f"TACACS REMEDIATION - Failed for {self.tid}({self.usable_ip})")
            self.msg["tacacs"].update(
                {
                    "status": "failed",
                    "message": "unable to update config",
                    "data": {
                        "ip": self.usable_ip,
                        "vendor": self.vendor,
                        "model": self.model,
                        "role": self.eq_type,
                        "response": remediation_response,
                    },
                }
            )
            self.tacacs_remediation_required = True

    def ise_check(self):
        ise_response, onboarded = onboard_device_in_ise(self.tid, self.usable_ip)
        if (
            isinstance(ise_response, dict) and "Onboarding Not Attempted" in ise_response["message"]
        ):  # core is assumed to be onboarded
            self.msg["ise"].update({"status": "validated", "message": "bypassed onboarding for core device"})
            logger.info("Core device, ISE onboarding not performed")
            self.ise_success = True
        elif onboarded:
            self.msg["ise"].update({"status": "validated", "message": "onboarded device"})
            self.ise_success = True
        else:
            if "NDG cannot be found" in ise_response or not ise_response:
                self.msg["ise"].update(
                    {
                        "status": "failed",
                        "message": "unable to onboard",
                        "data": {"ip": self.usable_ip, "response": ise_response},
                    }
                )
            elif "Device Name Already Exist" in ise_response:
                self.msg["ise"].update({"status": "pending", "message": "device already exists"})
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
            self.msg["ise"].update({"status": "validated", "message": "secret validated on existing entry"})
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
            self.msg["ise"].update(
                {
                    "status": "failed",
                    "message": "unable to find device id",
                    "data": {"ip": self.usable_ip, "tid": self.tid},
                }
            )
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
            self.msg["ise"].update({"status": "validated", "message": "secret updated on existing entry"})
            self.ise_success = True
        else:
            self.msg["ise"].update(
                {
                    "status": "failed",
                    "message": "unable to update shared secret",
                    "data": {"ip": self.usable_ip, "tid": self.tid},
                }
            )
            self.tacacs_remediation_required = True

    def remediate_boundary(self):
        # This is going to be best effort align Granite with IPC data
        if self.granite_remediation_required:
            self.update_granite_ip()

    def update_granite_ip(self):
        if not self.usable_ip:
            logger.debug("you shouldn't be here")
            return
        cidr = _init_export_child_block(self.usable_ip)
        ipaddr_with_cidr = self.usable_ip + "/" + cidr
        # Call Granite to update Shelf with new IP Addr
        logger.info("GRANITE IP UPDATE - Updating Granite Shelf...")
        shelf = update_granite_shelf(self.tid, ipaddr_with_cidr, cid=self.cid)
        if shelf:
            logger.info("GRANITE IP UPDATE - Updated Successfully.")
            self.msg["granite"].update({"status": "validated", "message": "updated design ip to usable ip"})
        else:
            logger.info("GRANITE IP UPDATE - Failed")
            self.msg["granite"].update(
                {
                    "status": "failed",
                    "message": "unable to reconcile databases",
                    "data": {"granite": self.ips_by_source["granite"], "usable": self.usable_ip},
                }
            )

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
