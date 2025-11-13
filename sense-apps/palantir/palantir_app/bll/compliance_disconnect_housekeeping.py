import logging

from common_sense.common.errors import abort
from common_sense.common.network_devices import VOICE_GATEWAY_MODELS
from palantir_app.bll.compliance_disconnect import Initialize
from palantir_app.bll.remedy import create_remedy_disconnect_ticket
from palantir_app.common.compliance_utils import ComplianceStages, get_pri_trunks
from palantir_app.common.constants import (
    CPE_IP_RELEASE_STAGE,
    FULL,
    GRANITE_DISCONNECT_STATUS,
    IP_RECLAIM_STAGE,
    IP_DISCONNECT_STAGE,
    IP_UNSWIP_STAGE,
    ISP_INFO,
    ISP_STAGE,
    PATH_STATUS_STAGE,
    SITE_STATUS_STAGE,
    FIBER_VOICE_DISCONNECT_PRODUCTS,
    VOICE_DISCONNECT_PRODUCTS,
)
from palantir_app.dll import granite
from palantir_app.dll.ipc import get_device_by_hostname
from palantir_app.dll.sense import post_sense
from palantir_app.common.endpoints import GRANITE_ELEMENTS

logger = logging.getLogger(__name__)


class DisconnectHousekeeping:
    def __init__(self, cid, product_name, endpoint_data=None):
        self.cid = cid
        self.product_name = product_name
        if not endpoint_data:
            # we must query design database for endpoint data
            endpoint_data = self._get_endpoint_data()
        self.endpoint_data = endpoint_data
        self.disconnect_sides = self._get_disconnect_type_and_endpoint_device_per_side()
        self.designed_elements = None
        self.disconnect_design_data = None
        self.designed_path = None
        self.circuit_path_deleted = False
        self.path_decommed = False

    def _get_endpoint_data(self):
        disconnect = Initialize(self.cid, request=None, order_type=None)
        endpoint_data = disconnect.get_endpoint_data_from_design()
        return endpoint_data

    def _get_disconnect_type_and_endpoint_device_per_side(self):
        disconnect_sides = {
            "z": {
                "z_side_disconnect": self.endpoint_data["z_side_disconnect"],
                "z_side_endpoint": self.endpoint_data["z_side_endpoint"],
            }
        }
        if self.endpoint_data.get("a_side_disconnect"):
            disconnect_sides["a"] = {}
            disconnect_sides["a"]["a_side_disconnect"] = self.endpoint_data["a_side_disconnect"]
            disconnect_sides["a"]["a_side_endpoint"] = self.endpoint_data["a_side_endpoint"]
        return disconnect_sides

    def _set_designed_elements(self):
        self.designed_elements = granite.granite_get(GRANITE_ELEMENTS, params={"CIRC_PATH_HUM_ID": self.cid})

    def _get_model_from_designed_elements_by_tid(self, tid):
        for element in self.designed_elements:
            if element.get("TID") == tid:
                return element.get("MODEL")
        return None

    def reclaim_cpe_mgmt_ip(self, compliance_status=None):
        msg = ""
        if not compliance_status:
            compliance_status = {}
        if not self.designed_elements:
            self._set_designed_elements()
        for side in self.disconnect_sides:
            disconnect_type = self.disconnect_sides[side][f"{side}_side_disconnect"]
            if disconnect_type != FULL:
                continue
            granite_tid = self.disconnect_sides[side].get(f"{side}_side_endpoint")
            granite_mgmt_ip = self._get_granite_cpe_mgmt_ip(granite_tid)
            granite_model = self._get_model_from_designed_elements_by_tid(granite_tid)
            if granite_mgmt_ip == "DHCP" or granite_model in ["ETX203AX/2SFP/2UTP2SFP", "FSP 150CC-GE114/114S"]:
                msg = "DHCP Management IP in Granite, no release process required."
                return {CPE_IP_RELEASE_STAGE: msg}
            if "not found" in granite_mgmt_ip:
                compliance_status.update({CPE_IP_RELEASE_STAGE: granite_mgmt_ip})
                abort(502, compliance_status)

            ipc_entry = get_device_by_hostname(granite_tid)
            if isinstance(ipc_entry, str):  # no device found, carry on as there is nothing to reclaim
                compliance_status.update({CPE_IP_RELEASE_STAGE: ipc_entry})
                return compliance_status

            ipc_hostname = ipc_entry.get("hostName")
            ipc_ip_address = self._get_ipc_cpe_mgmt_ip(ipc_entry["interfaces"])
            if "DHCP" in ipc_ip_address:
                msg = "DHCP Management IP in IPC, no release process required."
                return {CPE_IP_RELEASE_STAGE: msg}

            database_disagreement = self._validate_device_tid_and_ip(
                ipc_hostname, granite_tid, ipc_ip_address, granite_mgmt_ip
            )
            if database_disagreement:
                compliance_status.update({CPE_IP_RELEASE_STAGE: database_disagreement})
                abort(502, compliance_status)

            if ipc_entry.get("addressType") == "Static":
                msg += self._reclaim_device_from_ipc(granite_tid, granite_mgmt_ip, compliance_status)

        return {CPE_IP_RELEASE_STAGE: msg}

    def _get_granite_cpe_mgmt_ip(self, tid: str) -> str:
        """Retrieves management IP from the CPE(s) on a circuit.
        :param tid: CPE TID
        :type tid: str
        :param granite_elements: Payload from get granite paths call
        :type granite_elements: list
        :return: management IP from any CPEs on the circuit
        :rtype: str
        """
        for element in self.designed_elements:
            if element.get("TID") == tid:
                return element["IPV4_ADDRESS"].split("/")[0]
        return f"CPE management IP not found for {tid}."

    def _get_ipc_cpe_mgmt_ip(self, interfaces):
        for entry in interfaces:
            if "DHCP" in entry.get("addressType", [""])[0]:
                return entry["addressType"][0]
            elif entry.get("ipAddress"):
                return entry["ipAddress"][0]

    def _validate_device_tid_and_ip(self, ipc_hostname, granite_tid, ipc_ip_address, granite_mgmt_ip):
        if ipc_hostname.upper() != granite_tid.upper() or ipc_ip_address != granite_mgmt_ip:
            return f"Data mismatch. IPC TID: {ipc_hostname}, IPC IP address: {ipc_ip_address}, \
Granite TID: {granite_tid}, Granite IP address: {granite_mgmt_ip}"

    def _reclaim_device_from_ipc(self, tid: str, mgmt_ip: str, compliance_status: dict) -> dict:
        msg = None
        endpoint = f"arda/v1/reclaim_cpe_mgmt_ip?tid={tid}?mgmt_ip={mgmt_ip}"
        reclaim = post_sense(endpoint)
        try:
            msg = reclaim.json().get("message")
        except Exception as ex:
            err_msg = f"Exception parsing response from Arda for {mgmt_ip}: {ex}  | Arda response: {reclaim.text}"
            compliance_status.update({CPE_IP_RELEASE_STAGE: err_msg})
            abort(502, compliance_status)
        if reclaim.status_code not in (200, 201):
            err_msg = f"Error reclaiming CPE MGMT IP for {mgmt_ip} in Arda.  Message: {msg}"
            compliance_status.update({CPE_IP_RELEASE_STAGE: err_msg})
            abort(502, compliance_status)
        return ComplianceStages.SUCCESS_STATUS + msg

    def isp_work_order_process(self, site_order_data, compliance_status=None):
        if not compliance_status:
            compliance_status = {}
        # future: get optic slotted status for full discos if we don't have record of the check from mdso
        isp_required_sites = self._get_isp_required_sites()
        if not isp_required_sites:
            compliance_status.update({ISP_INFO: ["Optic not slotted, no ticket created."]})
            return compliance_status

        self.endpoint_data["isp_required_sites"] = isp_required_sites
        if not self.designed_elements:
            self._set_designed_elements()
        if not self.disconnect_design_data:
            self._set_disconnect_design_data(compliance_status)
        self._add_hub_data(compliance_status)
        create_remedy_disconnect_ticket(
            self.cid, self.endpoint_data, self.disconnect_design_data, site_order_data, compliance_status
        )
        return compliance_status

    def _get_isp_required_sites(self):
        isp_required_sites = {}
        for side in self.disconnect_sides:
            if self._is_remedy_isp_required(side):
                isp_required_sites[side] = {}
                isp_required_sites[side]["address"] = self.endpoint_data[f"{side}_side_address"]
        return isp_required_sites

    def _is_remedy_isp_required(self, side):
        return (
            self.disconnect_sides[side][f"{side}_side_disconnect"] == "FULL"
            and self.endpoint_data.get(f"{side}_side_optic_slotted") is True
        )

    def _set_disconnect_design_data(self, compliance_status=None):
        if not compliance_status:
            compliance_status = {}
        disconnect_design_data = {}
        if not self.designed_path:
            self._set_designed_path()
        if not self.designed_elements:
            self._set_designed_elements()
        for side in self.disconnect_sides:
            site_name = self.designed_path[0][f"{side}SideSiteName"]
            disconnect_design_data[side] = {}
            disconnect_type = self.disconnect_sides[side][f"{side}_side_disconnect"]
            if disconnect_type == "FULL":
                tid = self.disconnect_sides[side].get(f"{side}_side_endpoint")
                # Get Shelf and Site data
                shelf_status_data = granite.get_shelf_status_data(tid, site_name)
                logger.info(shelf_status_data)
                transport_path_data = granite.get_transport_path(
                    self.designed_elements, self.designed_path[0]["pathInstanceId"]
                )
                disconnect_design_data[side]["shelf_id"] = shelf_status_data["EQUIP_INST_ID"]
                disconnect_design_data[side]["site_id"] = shelf_status_data["SITE_INST_ID"]
                disconnect_design_data[side]["equip_status"] = shelf_status_data["EQUIP_STATUS"]
                disconnect_design_data[side]["site_status"] = shelf_status_data["SITE_STATUS"]
                disconnect_design_data[side]["site_name"] = shelf_status_data["SITE_NAME"]
                disconnect_design_data[side]["transport_data"] = transport_path_data

        disconnect_design_data["cid"] = self.cid
        self.disconnect_design_data = disconnect_design_data

    def _set_designed_path(self):
        self.designed_path = granite.get_path_details_by_cid(self.cid)

    def _add_hub_data(self, compliance_status):
        for side in self.disconnect_sides:
            if self.disconnect_sides[side][f"{side}_side_disconnect"] != "FULL":
                continue
            tid = self.disconnect_sides[side].get(f"{side}_side_endpoint")
            hub_data = self._get_hub_data(tid)
            if not hub_data:
                compliance_status.update({ISP_STAGE: f"Unable to get hub data for {tid}"})
                abort(502, compliance_status)
            self.disconnect_design_data[side]["element_data"] = self._get_element_data(tid, hub_data)

    def _get_element_data(self, tid, hub_data):
        upstream_handoff = self._get_upstream_handoff(tid)
        element_data = {
            "customer_name": self.designed_elements[0]["CUSTOMER_NAME"],
            "hub_clli": hub_data["clli"],
            "hub_site": hub_data["site_name"],
            "port_access_id": upstream_handoff.split(":")[1],
            "upstream_device": upstream_handoff.split(":")[0],
            "upstream_handoff": upstream_handoff,
        }
        return element_data

    def _get_upstream_handoff(self, disconnect_tid):
        for element in self.designed_elements:
            if disconnect_tid in element["PATH_NAME"] and element["TID"] != disconnect_tid:
                return f"{element['TID']}:{element['PORT_ACCESS_ID']}"

    def _get_hub_data(self, disconnect_tid):
        for element in self.designed_elements:
            if disconnect_tid in element["PATH_NAME"] and element["TID"] == disconnect_tid:
                return {"clli": element["A_CLLI"], "site_name": element["A_SITE_NAME"]}

    def set_path_to_decom(self, compliance_status=None):
        if not compliance_status:
            compliance_status = {}
        if not self.disconnect_design_data:
            self._set_disconnect_design_data(compliance_status)

        # validate pending decom status
        for side in self.disconnect_sides:
            disconnect_type = self.disconnect_sides[side][f"{side}_side_disconnect"]
            statuses = self._get_statuses(disconnect_type, side)
            pending_decom_error = self._validate_pending_decom(statuses, side.upper(), disconnect_type)
            if pending_decom_error:
                compliance_status.update({PATH_STATUS_STAGE: pending_decom_error})
                abort(502, compliance_status)

        pending_decom_data = [path for path in self.designed_path if path["status"] in GRANITE_DISCONNECT_STATUS]

        if len(pending_decom_data) != len(self.designed_path):
            err_msg = f"Path Status not allowed for disconnect for CID {self.cid}"
            compliance_status.update({PATH_STATUS_STAGE: err_msg})
            abort(502, compliance_status)

        if "PRI" in self.product_name:
            self._set_001_path_to_decom(self.cid, compliance_status)

        path_delete_error = granite.delete_path(self.designed_path, self.cid, "Decommissioned")
        if path_delete_error:
            compliance_status.update({PATH_STATUS_STAGE: path_delete_error})
            abort(502, compliance_status)

        if self.product_name in VOICE_DISCONNECT_PRODUCTS:
            self._del_vgw_elements(compliance_status)

        self.set_path_decommed()
        compliance_status.update({PATH_STATUS_STAGE: ComplianceStages.SUCCESS_STATUS})
        return compliance_status

    def _get_statuses(self, disconnect_type, side):
        statuses = []
        if disconnect_type == "PARTIAL":
            statuses.append(self.designed_path[0]["status"])
        else:
            if not self.path_decommed:  # if the path is already gone the status is moot
                statuses.append(self.designed_path[0]["status"])
            statuses.append(self.disconnect_design_data[side]["equip_status"])
            statuses.append(self.disconnect_design_data[side]["site_status"])
            if self.disconnect_design_data[side].get("transport_data"):
                statuses.append(self.disconnect_design_data[side]["transport_data"][0]["status"])
        return statuses

    def _validate_pending_decom(self, statuses: list, side: str, disconnect_type: str):
        for status in statuses:
            if status != "Pending Decommission":
                return f"Elements not in Pending Decommission status for {side}-side {disconnect_type} Disco"

    def _set_001_path_to_decom(self, cid, compliance_status=None):
        pri_trunks = get_pri_trunks(cid, live_only=False)
        # Call normal paths to get full detailed status of each trunk.
        for trunk in pri_trunks:
            pri_path = granite.get_path_details_by_cid(trunk[0])
            latest_revision = granite.get_latest_revision([rev[-1] for rev in pri_trunks])
            path_data = [x for x in pri_path if x["pathRev"] == latest_revision]
            if len(path_data) != 1:
                compliance_status.update(
                    {PATH_STATUS_STAGE: f"Multiple Paths for ({latest_revision}) Revision Found for Trunk Path"}
                )
                abort(502, compliance_status)
            if path_data[0]["status"] not in GRANITE_DISCONNECT_STATUS:
                compliance_status.update({PATH_STATUS_STAGE: "Path not in Pending Decommission status"})
                abort(502, compliance_status)
            path_delete_error = granite.delete_path(path_data, cid, "Decommissioned", skip_associations=True)
            if path_delete_error:
                compliance_status.update({PATH_STATUS_STAGE: path_delete_error})
                abort(502, compliance_status)

    def _del_vgw_elements(self, compliance_status):
        vgw_data = self._get_vgw_element()
        for element_reference in vgw_data:
            shelf_delete_error = granite.delete_shelf(element_reference)
            if shelf_delete_error:
                compliance_status.update({PATH_STATUS_STAGE: shelf_delete_error})
                abort(502, compliance_status)

    def _get_vgw_element(self):
        del_vgw_key = {}
        vgw_elements = [x for x in self.designed_elements if x["MODEL"] in VOICE_GATEWAY_MODELS]
        for vgw_element in vgw_elements:
            if vgw_element["ELEMENT_REFERENCE"] in del_vgw_key:
                if del_vgw_key[vgw_element["ELEMENT_REFERENCE"]]["pathRev"] > int(vgw_element["PATH_REV"]):
                    del_vgw_key[vgw_element["ELEMENT_REFERENCE"]]["pathRev"] = int(vgw_element["PATH_REV"])
                    del_vgw_key[vgw_element["ELEMENT_REFERENCE"]]["pathInstanceId"] = int(
                        vgw_element["CIRC_PATH_INST_ID"]
                    )
            else:
                del_vgw_key[vgw_element["ELEMENT_REFERENCE"]] = {}
                del_vgw_key[vgw_element["ELEMENT_REFERENCE"]]["pathRev"] = int(vgw_element["PATH_REV"])
                del_vgw_key[vgw_element["ELEMENT_REFERENCE"]]["pathInstanceId"] = int(vgw_element["CIRC_PATH_INST_ID"])

        return del_vgw_key

    def set_path_decommed(self):
        self.path_decommed = True

    def set_site_to_decom(self, compliance_status=None):
        if not compliance_status:
            compliance_status = {}
        if not self.disconnect_design_data:
            self._set_disconnect_design_data()
        if not self.path_decommed:
            compliance_status = self.set_path_to_decom()
            logger.info(self.disconnect_sides)
        for side in self.disconnect_sides:
            disconnect_type = self.disconnect_sides[side][f"{side}_side_disconnect"]
            if disconnect_type != FULL:
                continue
            statuses = self._get_statuses(disconnect_type, side)
            # validate pending decom status
            pending_decom_error = self._validate_pending_decom(statuses, side.upper(), disconnect_type)
            if pending_decom_error:
                compliance_status.update({SITE_STATUS_STAGE: pending_decom_error})
                abort(502, compliance_status)
            # delete transport path
            path_delete_error = granite.delete_path(
                self.disconnect_design_data[side]["transport_data"], self.cid, "Decommissioned", skip_associations=True
            )
            if path_delete_error:
                compliance_status.update({SITE_STATUS_STAGE: path_delete_error})
                abort(502, compliance_status)
            # delete shelf
            shelf_delete_error = granite.delete_shelf(self.disconnect_design_data[side]["shelf_id"])
            if shelf_delete_error:
                compliance_status.update({SITE_STATUS_STAGE: shelf_delete_error})
                abort(502, compliance_status)
            # delete site
            site_delete_error = granite.delete_site(self.disconnect_design_data[side]["site_id"])
            if site_delete_error:
                compliance_status.update({SITE_STATUS_STAGE: site_delete_error})
                abort(502, compliance_status)

        compliance_status.update({SITE_STATUS_STAGE: ComplianceStages.SUCCESS_STATUS})
        return compliance_status

    def no_guardrails_set_site_to_decom(self, site_id):
        compliance_status = {}
        # delete site
        site_delete_error = granite.delete_site(site_id)
        if site_delete_error:
            compliance_status.update({PATH_STATUS_STAGE: site_delete_error})
            abort(502, compliance_status)

        compliance_status.update({SITE_STATUS_STAGE: ComplianceStages.SUCCESS_STATUS})
        return compliance_status


class DisconnectServiceIPs:
    def ip_release_process(self, cid, product_name, compliance_status=None):
        if not compliance_status:
            compliance_status = {}

        ip_release_status = {IP_RECLAIM_STAGE: ComplianceStages.NOT_PERFORMED_STATUS}

        reclaim_endpoint = f"arda/v1/ip_reclamation?cid={cid}"
        reclaimed, reclaim_msg = self.release_ips(cid, reclaim_endpoint)
        logger.debug(f"{cid} IP Reclamation: {reclaim_msg}")
        ip_release_status[IP_RECLAIM_STAGE] = reclaim_msg
        if not reclaimed:
            compliance_status.update({IP_DISCONNECT_STAGE: ip_release_status})
            abort(502, compliance_status)

        if product_name not in FIBER_VOICE_DISCONNECT_PRODUCTS:
            ip_release_status[IP_UNSWIP_STAGE] = ComplianceStages.READY_STATUS
            unswip_endpoint = f"arda/v1/ip_swip/unswip?cid={cid}"
            unswipped, unswip_msg = self.release_ips(cid, unswip_endpoint)
            logger.debug(f"{cid} IP unSWIP: {unswip_msg}")
            ip_release_status[IP_UNSWIP_STAGE] = unswip_msg
            if not unswipped:
                compliance_status.update({IP_DISCONNECT_STAGE: ip_release_status})
                abort(502, compliance_status)

        compliance_status.update({IP_DISCONNECT_STAGE: ip_release_status})
        logger.debug(compliance_status)
        return compliance_status

    def release_ips(self, cid, endpoint):
        msg = None
        response = post_sense(endpoint)
        try:
            msg = response.json().get("message")
        except Exception as excp:
            return False, f"Exception parsing response from {endpoint} : {excp} {response.text}"
        if response.status_code not in (200, 201):
            return False, f"Error calling {endpoint} for cid {cid} , Message : {msg}"
        return True, f"{ComplianceStages.SUCCESS_STATUS}. Additional info: {str(msg)}"
