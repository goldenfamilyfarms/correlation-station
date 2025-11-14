import logging


logger = logging.getLogger(__name__)


def device_overview(path_elements: list) -> tuple:
    """Iterate over a path's elements and return a list of distinct TIDs plus bools of device types\n
    :param path_elements: standard /pathElements response (list of dicts)
    :return: distinct_tids: ['FLRSMONO1CW', 'HZWDMOGX1ZW', 'FLRSMONO0QW']\n
        has_cw, has_qw, has_aw, has_zw: bools
    """
    distinct_tids = set()
    has_cw = has_qw = has_aw = has_zw = False

    for elem in path_elements:
        if elem.get("TID") and elem["TID"] not in distinct_tids:
            device_type = elem["TID"][-2:]
            if device_type in ["CW", "QW", "AW", "ZW"]:
                distinct_tids.add(elem["TID"])
                if device_type == "CW":
                    has_cw = True
                elif device_type == "QW":
                    has_qw = True
                elif device_type == "AW":
                    has_aw = True
                elif device_type == "ZW":
                    has_zw = True
            else:
                logger.info(
                    f"BW Upgrade - unexpected device TID in path: {path_elements[0]['PATH_NAME']} - {elem['TID']}"
                )

    return list(distinct_tids), has_cw, has_qw, has_aw, has_zw


def device_details(path_elements: list, distinct_tids: list) -> dict:
    """Build dictionary of distinct CW, QW, AW, ZW devices in the path\n
    :param path_elements: standard /pathElements response (list of dicts)
    :param distinct_tids: ['FLRSMONO1CW', 'HZWDMOGX1ZW', 'FLRSMONO0QW']
    :return: {
            "CW": {
                "downstream_port": "AE17",
                "model": "MX960",
                "parent_transport_path": "",
                "parent_transport_path_inst_id": "",
                "tid": "FLRSMONO1CW",
                "vendor": "JUNIPER",
            },
            "QW": {
                "downstream_port": "GE-0/0/92",
                "model": "QFX5100-96S",
                "parent_transport_path": "31001.GE40L.FLRSMONO1CW.FLRSMONO0QW",
                "parent_transport_path_inst_id": "1165644",
                "tid": "FLRSMONO0QW",
                "vendor": "JUNIPER",
            },
            "ZW": {
                "downstream_port": "ACCESS-1-1-1-3",
                "model": "FSP 150-GE114PRO-C",
                "parent_transport_path": "31001.GE1.FLRSMONO0QW.HZWDMOGX1ZW",
                "parent_transport_path_inst_id": "2883252",
                "tid": "HZWDMOGX1ZW",
                "vendor": "ADVA",
                },
            }
    """
    devices = {}

    for elem in path_elements:
        device_info = {
            "tid": "",
            "downstream_port": "",
            "vendor": "",
            "model": "",
            "parent_transport_path": "",
            "parent_transport_path_inst_id": "",
        }

        if elem.get("TID") and elem.get("PORT_ACCESS_ID") and elem["TID"] in distinct_tids:
            tid = elem["TID"]
            port = elem["PORT_ACCESS_ID"]
            device_type = tid[-2:]

            if device_type == "ZW" and elem["LVL"] == "1":
                device_info["tid"] = tid
                device_info["downstream_port"] = port
                device_info["vendor"] = elem["VENDOR"]
                device_info["model"] = elem["MODEL"]
                for elem in path_elements:
                    if elem["PATH_NAME"].endswith(tid):
                        device_info["parent_transport_path"] = elem["PATH_NAME"]
                        device_info["parent_transport_path_inst_id"] = elem["CIRC_PATH_INST_ID"]
                        break
            else:
                device_info["tid"] = tid
                device_info["vendor"] = elem["VENDOR"]
                device_info["model"] = elem["MODEL"]
                if device_type != "CW":
                    device_info["parent_transport_path"] = elem["PATH_NAME"]
                    device_info["parent_transport_path_inst_id"] = elem["CIRC_PATH_INST_ID"]

                if device_type == "CW" and elem.get("LEG_NAME") and "AE" in elem["LEG_NAME"]:
                    device_info["downstream_port"] = elem["LEG_NAME"].split("/")[0]
                elif device_type in ["AW", "QW"]:
                    for elem in path_elements:
                        if (
                            elem["PATH_NAME"].split(".")[-2] == tid
                            and elem.get("PORT_ACCESS_ID")
                            and device_info["model"] == elem.get("MODEL")
                        ):
                            device_info["downstream_port"] = elem["PORT_ACCESS_ID"]
                            break
                else:
                    device_info["downstream_port"] = port

            if device_type not in devices.keys():
                devices[device_type] = device_info

    return devices
