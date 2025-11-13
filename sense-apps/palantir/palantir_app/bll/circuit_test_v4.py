import ipaddress
import logging
import re
import socket
import time

import palantir_app

from common_sense.common.errors import abort
from common_sense.dll.hydra import HydraConnector
from common_sense.dll.snmp import snmp_get_wrapper
from palantir_app.bll import circuit_test
from palantir_app.bll.circuit_test_v3 import _ctbh_model
from palantir_app.bll.ipc import get_ip_from_tid
from palantir_app.common.endpoints import (
    GRANITE_ELEMENTS,
    GRANITE_CIRCUIT_SITES,
    DENODO_SPIRENT_PORT,
    DENODO_SPIRENT_VTA,
)
from palantir_app.common.utils import get_hydra_key
from palantir_app.dll.denodo import denodo_get
from palantir_app.dll.granite import call_granite_for_circuit_devices, granite_get
from palantir_app.dll.sense import sense_get

CPE = "CPE"
QFX = "QFX"
PE = "PE"

DEVICE_ROLE = {CPE: ["A", "Z"], QFX: ["Q"], PE: ["C"]}

BLANK_CPE = dict.fromkeys(
    [
        "Status",
        "Vendor",
        "Model",
        "Hostname",
        "IpAddress",
        "TestAccessPort",
        "Interface",
        "InterfaceInfo",
        "Description",
        "PortType",
        "VLANOperation",
        "ServiceVLANID",
        "CustomerVLANID",
        "EVCType",
    ]
)

logger = logging.getLogger(__name__)

SRVC_TYPE = ["EPL", "EVPL", "ETHERNET", "E-ACCESS F", "EPLAN", "NNI", "UNI", "DIA", "MSS DIA", "SECURE INT"]


class ServiceTopology:
    def circuit_test_model(self, cid: str) -> dict:
        # Obtain devices from CID
        retries = 5  # 1sec, 4sec, 7sec, 11sec, 18sec
        add_sleep_time = 3
        sleep_time = 1
        while retries > 0:
            retries = retries - 1
            elements = circuit_test.device_inventory_call(cid)
            if elements and (isinstance(elements, list) or isinstance(elements, dict)):
                break
            logger.warning(f"Invalid Result. Retries Left: {retries}")
            time.sleep(sleep_time)
            temp = max(sleep_time, add_sleep_time)
            sleep_time = sleep_time + add_sleep_time
            add_sleep_time = temp
        else:
            logger.error("Time out waiting for success of _device_inventory_call", exc_info=True)
            return {}

        if not elements:
            abort(404, "no record found")
        logger.debug(f"elements - {elements}")

        if "CTBH" in elements[0].get("service_type", ""):
            logger.error(f"Service Type '{elements[0].get('service_type', '')}' is not supported.")
            return _ctbh_model(cid, elements)

        active_element = self.active_element(elements, detect_active_element=True)

        return self.process_circuit_test_model(cid, active_element)

    def process_circuit_test_model(self, cid: str, element: dict) -> dict:
        devices = element["data"]
        if len(devices) == 0:
            abort(404, "no record found")
        # Check for supported topologies
        service_type = element["service_type"]
        if service_type not in SRVC_TYPE:
            abort(501, "Topology {} unsupported".format(service_type))

        logger.debug(f"service_type - {service_type}")

        data = element.get("data", {})

        # Identify ASide and ZSide devices
        a_side_cloud_index = self.find_cloud(element, 0, True)
        logger.info(a_side_cloud_index)
        a_side_devices = data[:a_side_cloud_index]
        logger.debug(f"== A side devices: {a_side_devices} ==")

        z_side_cloud_index = self.find_cloud(element, len(data) - 1, False)
        logger.info(z_side_cloud_index)
        z_side_devices = list(reversed(data[z_side_cloud_index + 1 :]))
        logger.debug(f"== Z side devices: {z_side_devices} ==")

        statuses = self.devices_statuses(cid)
        cid_info = self.get_additional_cid_info(cid)
        region_and_market = self.get_region_and_market(cid_info)
        # Identify CPE and PE devices
        a_pe, a_cpe, a_pe_details, a_vta_details, a_qfx_details = self.process_side(
            cid, a_side_devices, statuses, is_zside=False
        )
        ip_address = a_cpe.get("management_ip", False)
        if not ip_address or ip_address.upper() in ["DHCP", "TRUE", "FALSE"]:
            ip_address = self.get_cpe_ip_address(a_cpe.get("tid", ""))
        if not ip_address and cid and a_cpe.get("tid"):
            ip_finder_endpoint = f"beorn/v1/cpe/ip_finder?cid={cid}&tid={a_cpe.get('tid', '')}"
            response = sense_get(ip_finder_endpoint, best_effort=True, return_response=True)
            if response.status_code // 100 == 2:
                response = response.json()
                ip_address = response.get("CPE_IP", "")
        if not ip_address or not isinstance(ip_address, str):
            abort(502, "No management IP given for CPE: {}".format(a_cpe["tid"]))
        a_cpe["management_ip"] = ip_address.split("/")[0]

        z_pe, z_cpe, z_pe_details, z_vta_details, z_qfx_details = self.process_side(
            cid, z_side_devices, statuses, is_zside=True
        )
        ip_address = z_cpe.get("management_ip", False)
        if not ip_address or ip_address.upper() in ["DHCP", "TRUE", "FALSE"]:
            ip_address = self.get_cpe_ip_address(z_cpe.get("tid", ""))
        if not ip_address and cid and z_cpe.get("tid"):
            ip_finder_endpoint = f"beorn/v1/cpe/ip_finder?cid={cid}&tid={z_cpe.get('tid', '')}"
            response = sense_get(ip_finder_endpoint, best_effort=True, return_response=True)
            logger.info(response)
            if response.status_code // 100 == 2:
                response = response.json()
                ip_address = response.get("CPE_IP", "")
        if not ip_address or not isinstance(ip_address, str):
            abort(502, "No management IP given for CPE: {}".format(z_cpe["tid"]))
        z_cpe["management_ip"] = ip_address.split("/")[0]

        a_side_transformed = self._extract_side(
            a_side_devices, a_pe, a_cpe, a_pe_details, a_vta_details, region_and_market, a_qfx_details, is_zside=False
        )
        z_side_transformed = self._extract_side(
            z_side_devices, z_pe, z_cpe, z_pe_details, z_vta_details, region_and_market, z_qfx_details, is_zside=False
        )
        # Circuit with no PEs
        nid_detected = (not a_pe) and (not z_pe)

        # ELAN circuit requirements
        elan = False
        elan_types = ["EPLAN", "NNI", "UNI"]
        if service_type in elan_types:
            elan = True
        if elan:
            self._check_test_device(z_pe, z_pe_details)

        return self._data_transformation(element, a_side_transformed, z_side_transformed, nid_detected)

    def process_side(
        self, cid: str, side_devices: dict, statuses, is_zside=False
    ) -> tuple[dict, dict, dict, list, dict]:
        side = self._get_cpe_pe(cid, side_devices)
        cpe = side["cpe"]
        if cpe:
            cpe.update({"status": self.path_status(cpe, statuses)})
        pe = side["pe"]

        # Obtain PE details
        pe_details = {}
        if pe:
            pe.update({"status": self.path_status(pe, statuses)})
            pe_details = self._get_pe_details(pe)

        qfx = side.get("qfx", {})
        qfx_details = {}
        if qfx:
            qfx.update({"status": self.path_status(qfx, statuses)})
            a_qfx_details = self._get_pe_details(qfx)

        # Search for VTA and test port details
        vta_type = "vw-vta-y1564-l"
        vta_details = self._get_vta_and_port_info(pe, pe_details, vta_type)
        if not is_zside and not vta_details.get("vta_rid") and qfx.get("tid"):
            vta_details = self._get_vta_and_port_info(qfx, a_qfx_details, vta_type)
        return pe, cpe, pe_details, vta_details, qfx_details

    def _data_transformation(self, element, a_side_transformed: dict, z_side_transformed: dict, NID) -> dict:
        """create the data object to return"""
        record = element
        # Circuit info
        data = {
            "CustomerName": record.get("customer_id"),
            "CircuitID": record.get("cid"),
            "Bandwidth": record.get("bandwidth"),
            "ServiceLevel": record.get("cos"),
            "CustomerType": record.get("customer_type"),
            "ServiceType": record.get("service_type"),
            "Status": record.get("status"),
            "VCID": record.get("evc_id"),
            "ASide": a_side_transformed,
            "ZSide": z_side_transformed,
        }
        if not NID:
            data["UnitType"] = None
        return data

    def _extract_side(
        self, devices, pe, cpe, pe_details, vta_details, region_and_market, qfx_details=None, is_zside=True
    ) -> dict:
        if qfx_details is None:
            qfx_details = []
        extracted_cpe = self.extract_cpe(cpe)
        extracted_pe = self.extract_pe(devices, pe, cpe, pe_details, vta_details, is_zside=is_zside)
        if (
            (not extracted_pe.get("wbox") or not extracted_pe.get("wbox") == [{}])
            and qfx_details
            and isinstance(qfx_details, list)
        ):
            wbox = self.extract_wbox(qfx_details[0], vta_details)
            extracted_wbox = [wbox] if (isinstance(wbox, dict) and wbox) else []
            logger.info(f"Extracted WBOX - {extracted_wbox}")
            if extracted_wbox and isinstance(extracted_wbox, list) and extracted_wbox[0]:
                extracted_pe["WBox"] = extracted_wbox
        region = region_and_market.get("z_site_region" if is_zside else "a_site_region")
        market = region_and_market.get("z_site_market" if is_zside else "a_site_market")
        address = None if not cpe else cpe.get("full_address")
        return self._side_transformation(extracted_pe, extracted_cpe, region, market, address)

    def _side_transformation(
        self, extracted_pe: dict, extracted_cpe: dict = BLANK_CPE, region=None, market=None, address=None
    ) -> dict:
        side = {"CustomerAddr": address, "Market": market, "Region": region, "CPE": extracted_cpe}
        if extracted_pe:
            side["PE"] = extracted_pe
        side["CPE"] = extracted_cpe
        return side

    def active_element(self, elements: dict, detect_active_element=False) -> dict:
        element_index = 0
        if detect_active_element:
            active_index = self.active_element_index(elements)
            logger.info("Detected active element index ")
            if active_index:
                element_index = active_index
        element = elements[element_index]
        return element

    def active_element_index(self, elements: dict) -> int:
        for index, element in enumerate(elements):
            if element.get("service_type") not in SRVC_TYPE:
                continue
            if self.element_active(element):
                return index
        return 0

    def element_active(self, element: dict) -> bool:
        """Detects which element of a multi element topology is active out in the wild"""
        cpe_role_list = ["A", "Z"]
        device_check = []
        for entry in list(reversed(element["data"])):
            if entry["device_role"] in cpe_role_list:
                device_check.append(entry)
                logger.debug(f"Topology Device Role [A, Z] Data:{entry}")
                break
        for entry in element["data"]:
            if entry["device_role"] in cpe_role_list:
                device_check.append(entry)
                logger.debug(f"Topology Device Role [A, Z] Data:{entry}")
                break
        if not device_check:
            return False
        for device in device_check:
            ip_address = device.get("management_ip", "")
            if not ip_address or isinstance(ip_address, bool) or ip_address.upper() in ["DHCP", "TRUE", "FALSE"]:
                ip_address = self.get_cpe_ip_address(device.get("tid"))
            ip_address = ip_address.split("/")[0]
            device_info = snmp_get_wrapper(
                [palantir_app.auth_config.SNMP_COMMUNITY_STRING, palantir_app.auth_config.SNMP_PUBLIC_STRING],
                ip_address,
                "sysDescr",
            )
            if device_info and isinstance(device_info, dict) and device_info.get("model"):
                return True
        return False

    def _get_ip_from_ipc(self, tid: str) -> str:
        hostname = tid.split(".")[0]
        ip = get_ip_from_tid(hostname)
        logger.info(f"Ip from tid '{ip}'")
        if ip:
            return ip
        return ""

    def get_cpe_ip_address(self, tid: str) -> str:
        logger.info(f"Device tid: '{tid}'")
        try:
            ip = socket.gethostbyname(tid)
            ipaddress.ip_address(ip)
            if ip:
                return ip
        except ValueError as error:
            # IPControl can take 12-24 hours to update tid to ip mapping
            # TODO: Check that hostname in fqdn matches the tid used in the ip lookup.
            logger.warning(f"Failed to get ipaddress with tid '{tid}' Error - {error}")
            hostname = tid.split(".")[0]
            ip = get_ip_from_tid(hostname)
            logger.info(f"Ip from tid '{ip}'")
            if ip is not None:
                return ip
        except socket.gaierror as error:
            logger.warning(f"Unable to retrieve ip from tid '{tid}' Error - {error}")
            hostname = tid.split(".")[0]
            ip = get_ip_from_tid(hostname)
            logger.info(f"Ip from tid '{ip}'")
            if ip is not None:
                return ip
        except Exception:
            logger.error(f"Unknown Exception while SNMP tid '{tid}'")
            return ""
        return ""

    def devices_statuses(self, cid: str) -> dict:
        granite_resp = call_granite_for_circuit_devices(cid, GRANITE_ELEMENTS)
        logger.debug(f"GRANITE_PathElement_RESPONSE: {granite_resp}")
        return granite_resp

    def get_additional_cid_info(self, cid: str) -> dict:
        endpoint = f"{GRANITE_CIRCUIT_SITES}?CIRCUIT_NAME={cid}&WILD_CARD_FLAG=1&PATH_CLASS=P"
        granite_resp = granite_get(endpoint, operation="general")
        logger.debug(f"GRANITE_PathElement_RESPONSE: {granite_resp}")
        return granite_resp

    def _tid_data_search(self, tid):
        """get tid information"""
        return denodo_get(f"{DENODO_SPIRENT_VTA}?pe_tid={tid}", operation="spirent")["elements"]

    def _port_access_search(self, tid, test_circ_inst):
        """get port access id"""
        endpoint = f"{DENODO_SPIRENT_PORT}?pe_tid={tid}&test_circ_inst={test_circ_inst}"
        return denodo_get(endpoint, operation="spirent")["elements"]

    def get_region_and_market(self, data: dict):
        mapped = ["a_site_market", "a_site_region", "z_site_market", "z_site_region"]
        return {k: data[0].get(k.upper()) for k in mapped}

    def path_status(self, device: dict, data: dict) -> dict:
        path_inst_id = str(device.get("path_inst_id", ""))
        for x in data:
            if x["CIRC_PATH_INST_ID"] == path_inst_id:
                return x["PATH_STATUS"]
        return {}

    # Borrowed from Circuit Topology
    def find_cloud(self, element, starting_index: int, ascending=True) -> int:
        """Find the index of the next cloud element starting at the starting index"""
        if ascending:
            iterator = IndexIterator(starting_index, len(element.get("data")) - 1)
        if not ascending:
            iterator = IndexIterator(0, starting_index, ascending=False)
        for i in iter(iterator):
            device = element.get("data")[i]
            topology = device.get("topology", "")
            if not topology:
                continue
            # The part after the or is a detection method for if the cloud element has been incorrectly marked.
            elif "CLOUD" in topology.upper():
                return i
        # Attempt to detect a cloud in data if one was not marked. This occurs with "path_name": "CHTRSE.EDNA.MPLS"
        for i in iter(iterator):
            device = element.get("data")[i]
            topology = device.get("topology", "")
            if not topology:
                continue
            elif (
                topology.upper() == "POINT TO POINT"
                and not device.get("model")
                and not device.get("tid")
                and not device.get("chan_name")
            ):
                return i
        found_pe = False
        logger.warning("Unable to find cloud. Fallback to treat device after PE as Cloud.")
        for i in iter(iterator):  # Treat the first device after a PE as a cloud
            device = element.get("data")[i]
            if self.device_role(device, normalize=True) == PE and not found_pe:
                found_pe = device.get("tid")
                continue
            if found_pe and device.get("tid") != found_pe:
                return i
        logger.warning("Unable to find any indication of side index. Using outer bounds.")
        return 0 if not ascending else len(element.get("data")) - 1  # Treat the outer bounds of the list as cloud

    def device_role(self, device: dict, normalize=False):
        device_role = device.get("device_role", "")
        if not device_role:
            tid = device.get("tid", "")
            if not tid or len(tid) < 4:
                return
            device_role = tid[-2]
        if device_role and isinstance(device_role, str):
            device_role = device_role.upper()
        for k, v in DEVICE_ROLE.items():
            if device_role in v:
                return k if normalize else device_role
        return

    def _get_cpe_pe(self, cid: str, device_list: dict) -> dict:
        """retrieve the CPE and PE from a device list"""
        cpe = {}
        qfx = {}
        pe = {}
        cpe_found = False
        path_search = ["TRANSPORT", "EPL", "EVPL"]
        if device_list:
            for device in device_list:
                device_role = device.get("device_role")
                if not device_role:
                    try:
                        tid = device.get("tid", "").split("-")[0]
                        device_role = tid[-1]
                    except AttributeError:
                        pass
                if not cpe_found:
                    if device_role in ["A", "Z", "2"]:
                        cpe = device
                        if ("HANDOFF" in device["path_type"]) or (device["path_name"] == cid):
                            cpe = device
                            cpe_found = True
                if not pe:
                    if device_role == "C":
                        pe = device
                        if any(x for x in path_search if x in device["path_type"]):
                            pe = device
                            break
                if not qfx:  # Only used for e access fiber vta fallback.
                    if device_role in ["Q"]:
                        qfx = device
                if cpe and pe:
                    break
        return {"cpe": cpe, "qfx": qfx, "pe": pe}

    def _get_pe_details(self, pe: dict):
        """get target details on a valid PE"""
        hostname = pe.get("tid")
        if not hostname:
            return None, None
        tid_data = self._tid_data_search(hostname)

        """Add Circuit OAM TESTING for Y.1564 on eligible circuits. This is required for E ACCESS Fiber circuit testing
        (DICE ELINE Service Activation Test in Visionworks)."""
        circ_path_inst_id_list = [k.get("test_circ_inst") for k in tid_data]
        env = palantir_app.app_config.USAGE_DESIGNATION
        hc = HydraConnector(
            palantir_app.url_config.HYDRA_BASE_URL, get_hydra_key(), environment="dev" if env == "STAGE" else "prd"
        )
        logger.debug(f"list - {circ_path_inst_id_list}")
        if circ_path_inst_id_list:
            circ_path_inst_id_list_str = ", ".join([str(k) for k in circ_path_inst_id_list])
            dv_circ_path_attr_settings = hc.dv_circ_path_attr_settings(
                filter=f"(circ_path_inst_id in ({circ_path_inst_id_list_str})and val_attr_inst_id=3821)"
            )
            logger.debug(f"return - {dv_circ_path_attr_settings}")
            for k in dv_circ_path_attr_settings.get("elements", {}):
                if k.get("attr_value") in ["Y.1564"]:
                    for i, data in enumerate(tid_data):
                        if k.get("circ_path_inst_id") == data.get("test_circ_inst"):
                            tid_data[i].update({"Circuit_OAM_TESTING": k.get("attr_value")})
                            break

        logger.debug(f"tid_data - {tid_data}")
        keys = [
            "test_circ_inst",
            "test_tid",
            "test_fqdn",
            "test_circ_status",
            "test_equip_status",
            "test_equip_vendor",
            "test_equip_model",
            "Circuit_OAM_TESTING",
        ]
        data = []
        if not tid_data:
            return [dict.fromkeys(keys)]

        # Search each PE record with a Live status and fqdn is not NULL
        # and equipment model includes "NFX" per Spirent requirements
        # then adds each id to the tid_nfx_list
        tid_nfx_list = []
        for id, device in enumerate(tid_data):
            # conditions for a valid test circuit
            if device.get("test_circ_status", "").upper() != "LIVE":
                continue
            logger.debug(f"Test Circuit Status for PE {hostname}-{device['test_circ_inst']} is inactive")
            if device.get("test_equip_status", "").upper() != "LIVE":
                continue
            logger.debug(f"Test Equipment Status for PE {hostname}-{device['test_circ_inst']} is inactive")
            if device.get("test_fqdn", "") is None:
                continue
            logger.debug(f"Test fqdn for PE {hostname} is not found.")
            if device.get("test_equip_model", "").upper().find("NFX") == -1:
                continue
            logger.debug(f"Test Equipment Model for PE {hostname} is invalid.")
            tid_nfx_list.append(id)
        logger.debug(f"FOUND! {len(tid_nfx_list)} device(s)")
        if not tid_nfx_list:
            return [dict.fromkeys(keys)]
        # Mine data from each PE record
        for entry in tid_nfx_list:
            nfx = {}
            for key in keys:
                if key not in tid_data[entry].keys():
                    nfx[key] = None
                elif key not in ("test_fqdn", "test_circ_inst", "test_equip_model", "test_equip_status"):
                    nfx[key] = tid_data[entry].get(key, None)
                elif tid_data[entry][key]:
                    nfx[key] = tid_data[entry].get(key, None)
                else:
                    return abort(502, "Unable to determine {} for PE {}".format(key, hostname))
            data.append(nfx)
        return data

    def _get_vta_and_port_info(self, pe, pe_details, vta_type) -> dict:
        """obtain vta mac address and test port info"""
        vta_details = {"vta_rid": None, "vta_mac_address": None, "port_access_id": None}
        if not pe_details:
            return vta_details
        for entry in pe_details:
            try:
                test_tid = entry.get("test_tid")
            except TypeError:
                test_tid = None
            # Search for MDSO resource info for VTA device
            vta_info = {"vta_rid": None, "vta_mac_address": None}
            if not test_tid:
                return vta_details
            # Retrieve the test port info
            test_port = None
            if entry.get("test_equip_model", "") != "VISIONWORKS VTP 1G":
                test_port = self._port_access_search(pe.get("tid"), entry.get("test_circ_inst"))
            vta_details["vta_rid"] = vta_info["vta_rid"]
            vta_details["vta_mac_address"] = vta_info["vta_mac_address"]
            if test_port:
                vta_details["port_access_id"] = test_port[0]["pe_port_access_id"]
            if vta_details["vta_mac_address"] is not None or entry.get("Circuit_OAM_TESTING") == "Y.1564":
                break
        return vta_details

    def extract_pe(self, side_devices, side_pe, side_cpe, pe_details, vta_details, is_zside=False):
        ip_address = side_pe.get("management_ip", "").split("/")[0]
        if not ip_address or ip_address.upper() in ["DHCP", "TRUE", "FALSE"]:
            ip_address = self.get_cpe_ip_address(side_pe.get("tid"))
        leg_name = side_pe.get("leg_name", "")
        if leg_name and "AE" in leg_name:
            try:
                leg_name = leg_name.split("/")[0]
                leg_name = leg_name.lower()
            except Exception as e:
                logger.error(f"Failed to extract agg port - {leg_name} - {e}")
        else:
            leg_name = ""
        pe = {
            "Status": side_pe.get("status", None),
            "Vendor": side_pe.get("vendor"),
            "Model": side_pe.get("model"),
            "Hostname": side_pe.get("tid"),
            "IpAddress": ip_address,
            "VLANOperation": side_pe.get("vlan_operation"),
            "ServiceVLANID": side_pe.get("svlan"),
            "TestAccessPort": (
                leg_name
                if leg_name
                else (
                    vta_details.get("port_access_id")
                    if not vta_details.get("port_access_id")
                    else str(vta_details.get("port_access_id", "")).lower()
                )
            ),
            "Interface": (
                side_pe.get("port_access_id")
                if not side_pe.get("port_access_id")
                else side_pe.get("port_access_id", "").lower()
            ),
            "InterfaceInfo": None,
            "Description": None,
            "EVCType": None,
        }
        if side_pe.get("svlan"):
            if is_zside:
                # Service is outer vlan; customer is inner vlan
                # Case where Type II ('CUST-OFFNET') circuit:
                for device in list(reversed(side_devices)):
                    if device["chan_name"] and "IV-" in device["chan_name"] and "OV-" in device["chan_name"]:
                        side_pe["svlan"] = device["chan_name"]
            # Handle case where delimiter '//' separates a combined service/customer VLAN id
            if "//" in side_pe["svlan"]:
                vlan_id, side_pe["cevlan"] = side_pe["svlan"].split("//")
                if is_zside:
                    if "OV-" in vlan_id:
                        vlan_id = vlan_id[(vlan_id.find("OV-") + 3) :]
                    if "IV-" in side_pe["cevlan"]:
                        side_pe["cevlan"] = side_pe["cevlan"][(side_pe["cevlan"].find("IV-") + 3) :]
            else:
                # Remove all alpha characters, leave digits alone
                vlan_id = re.sub("[^0-9]", "", side_pe.get("svlan"))
            pe["ServiceVLANID"] = vlan_id
            if is_zside:
                pe["CustomerVLANID"] = side_pe.get("cevlan")
        else:
            # If PE service vlan is null, use the CPE service vlan id
            logger.debug(" == # If PE service vlan is null, use the CPE service vlan id == ")
            if side_cpe:
                if side_cpe.get("svlan"):
                    pe["ServiceVLANID"] = side_cpe.get("svlan")
        pe["CustomerVLANID"] = side_pe.get("cevlan")
        # If PE customer vlan is null, use the CPE customer vlan id
        if not side_pe.get("cevlan") and side_cpe and side_cpe.get("cevlan"):
            pe["CustomerVLANID"] = side_cpe.get("cevlan")
        pe["WBox"] = []
        if pe_details:
            wbox = self.extract_wbox(pe_details[0], vta_details)
            if wbox:
                pe["WBox"] = [wbox]
        return pe

    def extract_cpe(self, side_cpe: dict) -> dict:
        if not isinstance(side_cpe, dict) or not side_cpe.get("tid"):
            logger.warning(f"No cpe - '{side_cpe}'")
            return BLANK_CPE
        cpe = {
            "Status": side_cpe.get("status", None),
            "Vendor": side_cpe.get("vendor"),
            "Model": side_cpe.get("model"),
            "Hostname": side_cpe.get("tid"),
            "TestAccessPort": None,
            "InterfaceInfo": None,
            "Description": None,
            "PortType": None,
            "Interface": (
                side_cpe.get("port_access_id")
                if not side_cpe.get("port_access_id")
                else str(side_cpe.get("port_access_id", "")).lower()
            ),
            "VLANOperation": side_cpe.get("vlan_operation"),
            "ServiceVLANID": side_cpe.get("svlan"),
            "EVCType": None,
        }
        ip_address = side_cpe.get("management_ip", "")
        if not ip_address or ip_address.upper() in ["DHCP", "TRUE", "FALSE"]:
            ip_address = self.get_cpe_ip_address(side_cpe.get("tid"))
        if not ip_address:
            abort(502, "No management IP given for CPE: {}".format(side_cpe.get("tid")))
        cpe["IpAddress"] = ip_address.split("/")[0]
        if side_cpe["svlan"]:
            # Handle case where delimiter '//' separates a combined service/customer VLAN id
            if "//" in side_cpe["svlan"]:
                vlan_id = side_cpe.get("svlan", "").split("//")[0]
                side_cpe["cevlan"] = side_cpe.get("svlan", "").split("//")[1]
            else:
                # Remove all alpha characters, leave digits alone
                vlan_id = re.sub("[^0-9]", "", side_cpe["svlan"])
            cpe["ServiceVLANID"] = vlan_id
        cpe["CustomerVLANID"] = side_cpe["cevlan"]
        return cpe

    def extract_wbox(self, device_details: dict, vta_details) -> dict:
        logger.debug(f"Extracting wbox - {device_details} - {vta_details}")
        if device_details.get("test_equip_vendor") == "JUNIPER":
            if "VTP" not in device_details["test_equip_model"]:
                wbox = {
                    "Name": device_details["test_tid"],
                    "Vendor": device_details["test_equip_vendor"],
                    "Model": device_details["test_equip_model"],
                }
                vta = []
                if vta_details["vta_mac_address"]:
                    vta = [{"Vendor": None, "Model": None, "MacAddress": vta_details.get("vta_mac_address")}]
                wbox.update({"VTA": vta})
                logger.debug(f"wbox - {wbox}")
                return wbox
        return {}

    def _check_test_device(self, pe, pe_details):
        """check test device"""
        if not pe_details:
            abort(502, "Unable to find any PE")
        # Focus on NFX's for now
        if pe_details[0]["test_equip_model"] is None:
            return
        elif "NFX" not in pe_details[0]["test_equip_model"]:
            logger.debug("== check_test_device call ==")
            logger.debug("No valid test device (NFX) at this location - {}".format(pe["tid"]))
        elif pe_details[0]["test_circ_status"] != "Live":
            abort(502, "Test circuit status is {}, instead of Live".format(pe_details[0]["test_circ_status"]))
        elif pe_details[0]["test_equip_status"] != "Live":
            abort(
                502,
                "NFX {} equipment status is {}".format(pe_details[0]["test_fqdn"], pe_details[0]["test_equip_status"]),
            )


# Borrowed from Circuit Topology No Changes
class IndexIterator:
    def __init__(self, lower_bound: int, upper_bound: int, ascending=True):
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound
        self.increment = 1 if ascending else -1

    def __iter__(self):
        self.index = self.lower_bound if self.increment > 0 else self.upper_bound
        return self

    def __next__(self):
        if (self.index < self.lower_bound and self.increment < 0) or (
            self.upper_bound < self.index and 0 < self.increment
        ):
            raise StopIteration
        i = self.index
        self.index += self.increment
        return i

    def contains(self, index: int):
        return self.lower_bound <= index <= self.upper_bound
