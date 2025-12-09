import logging
import re
import subprocess  # noqa: S404
from enum import Flag, auto

from common_sense.common.errors import abort
from palantir_app.common.validators import ipv4_check

logger = logging.getLogger(__name__)


class SystemCommandStatus(Flag):
    """Support enum class to SystemCommand"""

    unexpected_argument = auto()
    malformed_argument = auto()
    missing_argument = auto()
    argument_failed_validation = auto()
    timeout_waiting = auto()
    opsystem_returned_error = auto()
    opsystem_status_empty = auto()
    success = command_result_success = auto()


class SystemCommand:
    """Utility to accommodate os command line system calls"""

    def __init__(self):
        self.ping_cmd = ("ping", "-c1", "-t1")
        self.host_cmd = ["host", "W1"]
        self.nslookup_cmd = ["nslookup"]
        self.lochosts_cmd = ["grep", "-i", "-w"]
        self.lochosts_file = "/etc/hosts"
        self.export_cedr = ["cedr-export", "-v"]

        self.system_status = None
        self.opsystem_code = None
        self.command_status = SystemCommandStatus.success

    def get_fqdn_from_ip(self, ip_tid):
        if ip_tid is None:
            self.system_status = SystemCommandStatus.missing_argument
            logger.debug("THE IP-TID ARGUMENT IS MISSING FROM THIS CALL - {}".format(str(ip_tid)))

            return None

        if len(ip_tid) != 2:
            self.system_status = SystemCommandStatus.missing_argument
            logger.debug("IP and TID ELEMENTS ARE RERQUIRED IN ARGUMENT - {}".format(str(ip_tid)))
            return None

        ip = ip_tid[0]
        tid = ip_tid[1]

        if ip is None:
            self.system_status = SystemCommandStatus.missing_argument
            logger.debug("IP ELEMENT IS NULL - {} from {}".format(ip, str(ip_tid)))
            return None

        if tid is None:
            self.system_status = SystemCommandStatus.missing_argument
            logger.debug("TID ELEMENT IS NULL - {} from {}".format(ip, str(ip_tid)))
            return None

        ip = str(ip_tid[0])
        tid = str(ip_tid[1])

        try:
            ipv4_check(ip)

        except Exception as e:
            logger.debug("Exception on IPv4 FORMAT VALIDATION : {} ".format(str(e)))
            self.system_status = SystemCommandStatus.success
            return None

        fqdn = self.do_nslookup(ip, tid)

        if fqdn is None:
            fqdn = self.do_localhost_lookup(ip, tid)

        if fqdn is not None:
            logger.debug("FOUND AN FQDN {} for {}:{}".format(tid, ip, fqdn))

        return fqdn

    def do_nslookup(self, ip, tid):
        fqdn = None

        try:
            x = self.nslookup_cmd
            command = x.copy()
            command.append(ip)
            logger.debug("Trying IP {} and TID {} using {}".format(ip, tid, str(command)))
            command_proc = subprocess.run(  # noqa: S603
                args=command,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stdin=subprocess.PIPE,
                timeout=5,
                check=True,
            )

            command_proc.check_returncode()

            stdout_lines = command_proc.stdout.decode("utf-8").split("\n")

            # Looking for matching ( e.g. for ip = 10.10.10.10 and tid = AMDAOH031ZW )
            # 10.10.10.10.in-addr.arpa	name = AMDAOH031ZW.mw.twcbiz.com.

            criteria = r"^.*name.*=\s+{}.*\.com".format(tid)

            if stdout_lines is not None:
                for line in stdout_lines:
                    if re.match(criteria, line):
                        logger.debug("Found regex match {} after nslookup result {}".format(criteria, line))
                        fqdn = re.sub("^.*name.*=", "", line)
                        fqdn = re.sub("\\.$", "", fqdn)
                        fqdn = str(fqdn).strip().upper()
                        break

        except subprocess.TimeoutExpired as e:
            logger.debug("nslookup check TimedOut for {}:{} - {}".format(tid, ip, str(e)))
            return fqdn

        except subprocess.CalledProcessError as e:
            logger.debug("nslookup check failed for {}:{} - {}".format(tid, ip, str(e)))

        return fqdn

    def do_localhost_lookup(self, ip, tid):
        fqdn = None

        try:
            x = self.lochosts_cmd
            command = x.copy()
            command.append('"{}"'.format(str(ip)))
            command.append(str(self.lochosts_file))
            logger.debug("Trying IP {} and TID {} using {}".format(ip, tid, str(command)))
            command_proc = subprocess.run(  # noqa: S603
                args=command,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stdin=subprocess.PIPE,
                timeout=5,
                check=True,
            )

            command_proc.check_returncode()
            stdout_lines = command_proc.stdout.decode("utf-8").split("\n")

            # Looking for matching ( e.g. for ip = 10.4.120.10 and tid = GRLDTXDW0QW )
            # 10.4.120.10    GRLDTXDW0QW.sw.twcbiz.com

            criteria = r"^{}\s*{}\..*$".format(ip, tid)

            if stdout_lines is not None:
                for line in stdout_lines:
                    if re.match(criteria, line):
                        logger.debug("Found regex match {} after local hosts {}".format(criteria, line))
                        fqdn = re.sub(ip, "", line)
                        fqdn = str(fqdn).strip().upper()
                        break

            else:
                return fqdn

        except subprocess.TimeoutExpired as e:
            logger.debug("Local host file check failed TimedOut for {}:{} - {}".format(tid, ip, str(e)))

            return fqdn

        except subprocess.CalledProcessError as e:
            logger.debug("Local host file check failed for {}:{} - {}".format(tid, ip, str(e)))

        return fqdn


def fping_os_cmd():
    with open("/etc/os-release") as f:
        os_output = f.read().lower()
    return "/usr/sbin/fping" if re.search("centos", os_output) else "/usr/bin/fping"


def fping_ip(block_name: str, compliance_status: dict):
    """uses fping to check the status of IPs within the designated block and returns the number of
    IPs marked as alive; if any, fall out."""
    logger.info(f"Beginning fping verification for {block_name}")
    cidr_notation_delimiter = "/"
    if cidr_notation_delimiter not in block_name:
        msg = f"CIDR missing from IP block {block_name}, unable to complete fping check"
        compliance_status.update({"IP Release Process": msg})
        abort(502, compliance_status)
    cmd = [fping_os_cmd(), "-ags", f"{block_name}"]
    gateway, output = None, None
    try:
        res = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)  # noqa: S603
        gateway, output = res.communicate()
    except Exception as e:  # Need blanket exception to catch all cases of failure
        logger.exception("Error running fping to check for alive IPs")
        err_msg = f"Error running fping to check for alive IPs: {e}"
        compliance_status.update({"IP Release Process": err_msg})
        abort(502, compliance_status)

    str_output = str(output)
    logger.info(f"Fping executed successfully: \n{str_output}")
    spl_output = str_output.split()
    alive_index = spl_output.index(r"alive\n")
    logger.info(f"Validating alive IPs from result of {alive_index}")
    try:
        num_alive = int(spl_output[(alive_index - 1)])
    except ValueError:
        msg = f"Unexpected response from fping. Command:{cmd} Response: {str_output}"
        compliance_status.update({"IP Release Process": msg})
        abort(502, compliance_status)

    if num_alive > 0:
        err_msg = f"fping found at least 1 IP in {block_name} marked alive"
        compliance_status.update({"IP Release Process": err_msg})
        abort(502, compliance_status)

    logger.info(f"Fping completed successfully for {block_name}")
