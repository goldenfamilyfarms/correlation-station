import logging

from common_sense.common.errors import abort
from arda_app.bll.circuit_design.common import add_vrfid_link
from arda_app.dll.granite import (
    assign_association,
    get_circuit_site_info,
    # get_network,
    get_network_association,
    get_network_elements,
    get_network_path,
    get_path_elements,
    get_shelf_udas,
    get_source_mep,
    put_granite,
    update_network_vlan,
    # assign_network_association,
    # create_vpls_network,
    # get_path_elements_l1,
)
from arda_app.common.cd_utils import granite_paths_url
from arda_app.dll.mdso import onboard_and_exe_cmd

# from arda_app.bll.assign.evc import assign_evc_2

logger = logging.getLogger(__name__)


def assign_vpls_main(payload: dict):
    """
    Main function to assign VPLS to provided cid

    Input:
      payload = {
          "cid": "91.L1XX.009706..CHTR",
          "product_name": "'EP-LAN (Fiber)'",
          "create_new_elan_instance": True,
          "customers_elan_name": "CHTRSE.VRFID.431111.NCDIT K12 RTP2",
          "granite_site_name": "PTBONC39-ITS-NC//1476 ANDREWS STORE RD"
      }

    Output:
        customers_elan_name = "CHTRSE.VRFID.431111.NCDIT K12 RTP2"
          or
        abort
    """
    if payload["create_new_elan_instance"] == "Yes":
        payload["create_new_elan_instance"] = True
    else:
        payload["create_new_elan_instance"] = False
    cid = payload["cid"]
    logger.info(f"Adding VPLS to {cid}")

    cne_instance = payload["create_new_elan_instance"]
    existing_vrfid = "" if payload.get("customers_elan_name") == "Null" else payload.get("customers_elan_name")
    # granite_sitename = body.get("granite_site_name", "")

    if existing_vrfid:
        vpls_inst = check_vpls(existing_vrfid, cne_instance)
    else:
        # TODO will place this code back once business logic is worked out
        # vpls_inst = get_sitename(cid, cne_instance, granite_sitename)
        msg = "Customer ELAN Name was not provided, which is currently unsupported"
        logger.error(msg)
        abort(500, msg)

    if vpls_inst:
        create_new_elan_instance = False
        status = vpls_inst[0].get("STATUS") or vpls_inst[0].get("status")
        network_id = vpls_inst[0].get("CIRC_PATH_INST_ID") or vpls_inst[0].get("pathInstanceId")
        network_name = vpls_inst[0].get("NETWORK_NAME") or vpls_inst[0].get("pathId")
        granite_vlan = vpls_inst[0].get("NETWORK_VLAN_ID", "")
        network_vlan_list = []

        if status == "Live":  # perform encapsulation check on network
            # get cids from existing live VPLS
            vpls_elements = get_network_elements(network_id)

            # filter for live cids
            equipment_list = live_vpls_check(vpls_elements)

            # if hub device is charter or vendor is cisco abort
            equipment_check(equipment_list)

            # MDSO call on port to get encapsulation on both circuits
            network_encap = get_network_info(equipment_list)

            for encap in network_encap:  # getting live network VPLS information
                description = encap["properties"]["config"]["description"]
                encap_type = encap["properties"]["config"]["type"]

                if encap_type != "vpls":  # if either encapsulation is not vpls abort
                    msg = f"{description} has an encapsulation of {encap_type} that is not equal to vpls"
                    logger.error(msg)
                    abort(500, msg)

                # adding try and except assigning 0 if not configured on network
                try:
                    network_vlan = str(encap["properties"]["vlans"][0]["vlanId"])
                except Exception:
                    network_vlan = "0"

                network_vlan_list.append(network_vlan)

        # if granite network VLAN is blank update with VLAN on network or 1200
        update_network_vlan(network_id, network_vlan_list, granite_vlan)

        # add VPLS to CID
        resp = add_network_link(cid, network_id)

        # add association to CID
        if isinstance(resp, dict):
            association = get_network_association(network_id)

            if isinstance(association, dict):
                if association.get("retString"):
                    logger.error("Missing association in granite for Network link")
                    abort(500, f"Missing association in granite for {network_name}")

            # adding path association to revision
            evcid = association[0]["associationValue"]
            association_name = association[0]["associationName"].replace("NETWORK", "PATH")
            range_name = association[0]["numberRangeName"]

            path_inst_id = resp["pathInstanceId"]

            # removing leading zero from evcid
            new_evc = str(int(evcid))

            assoc_result = assign_association(path_inst_id, new_evc, association_name, range_name)

            if not assoc_result:
                logger.error("Unable to add path association, Granite operation failed")
                abort(500, f"Unable to add path association {new_evc} to new revision in Granite for {cid}")

            evcid_update(cid, new_evc)

            add_vrfid_link(cid, path_inst_id)

            return {"customers_elan_name": network_name, "create_new_elan_instance": create_new_elan_instance}

        msg = f"Unable to add vpls network to {cid}"
        logger.error(msg)
        abort(500, msg)
    else:
        msg = f"Unable to find Customer ELAN Name: {existing_vrfid} in granite"
        logger.error(msg)
        abort(500, msg)
        # new VPLS creation
        # TODO this codelogic will get added back once business logic is figured out for new elan creation
        """
        create_new_elan_instance = True
        range_name = assign_evc_2(cid)
        resp = get_path_elements_l1(cid)

        if isinstance(resp, list):
            path_instid = resp[0]["CIRC_PATH_INST_ID"]
            evcid = resp[0]["EVC_ID"]
            site = resp[0]["PATH_Z_SITE"].split("/")[0]
            customer_name = site[9:]
            new_vrfid = f"CHTRSE.VRFID.{evcid}.{customer_name}"

            data = create_vpls_network(new_vrfid)

            evcid_update(cid, evcid)

            if isinstance(data, dict):
                network_id = data["ntwkInstanceId"]
                response = add_network_link(cid, network_id)  # then add to cid

                # will need to add association to new network
                network_add = assign_network_association(network_id, evcid, range_name)

                if isinstance(network_add, dict):

                    # add association to CID
                    if isinstance(response, dict):
                        add_vrfid_link(cid, path_instid)

                        return [new_vrfid, create_new_elan_instance]

                    msg = f"Unable to add vpls network to {cid}"
                    logger.error(msg)
                    abort(500, msg)

                msg = f"Unable to add association to network to {new_vrfid}"
                logger.error(msg)
                abort(500, msg)

            msg = "Unable to create new VPLS network in granite"
            logger.error(msg)
            abort(500, msg)

        msg = "Unable to get path elements from granite"
        logger.error(msg)
        abort(500, msg)
    """


def check_vpls(existing_vrfid, cne_instance, cust_name=False):
    """
    Check granite for an existing VRFID.
    If it exist it will compare the status to determine if it can be used.
    Will also return None if a new one needs to get created

    Input:
      existing_vrfid = "CHTRSE.VRFID.431111.NCDIT K12 RTP2",
      cne_instance = True / False,
      cust_name = "cust_name"

    Output:
      [{resp}] or None or abort
    """
    """
    if cust_name:
        resp = get_network_path(existing_vrfid)
    else:
        resp = get_network(existing_vrfid)
    """
    resp = get_network_path(existing_vrfid)

    if isinstance(resp, list):
        if len(resp) == 1:
            if cust_name:
                vrfid_status = resp[0].get("STATUS") or resp[0].get("status")

                if (cne_instance is False and vrfid_status != "Live") or (
                    cne_instance is True and vrfid_status == "Live"
                ):
                    logger.error("Existing VPLS has an unsupported status")
                    abort(500, f"Existing VPLS {existing_vrfid} has an unsupported status of {vrfid_status}")

            return resp
        elif len(resp) > 1:  # more than one resp
            msg = f"Multiple VPLS instances were found while searching customers ELAN name {existing_vrfid}"
            logger.error(msg)
            abort(500, msg)
    elif isinstance(resp, dict):  # no response from granite == 0
        if cne_instance:
            return  # create EVCID and then use evcid to create vrfid

        msg = f"No existing VPLS instances found in granite searching with Customer Elan name: {existing_vrfid}"
        logger.error(msg)
        abort(500, msg)

    msg = "Error while searching granite for existing VPLS"
    logger.error(msg)
    abort(500, msg)


def get_sitename(cid, cne_istance, granite_sitename=None):
    """
    Check granite for an existing VRFID using the granite sitename.
    If no results it will search granite with customer name with ending word removed each time

    Input:
      cid = "91.L1XX.009706..CHTR",
      create_new_elan_instance = False,
      granite_site_name = "PTBONC39-ITS-NC//1476 ANDREWS STORE RD"

    Output:
      [{result}] or None or abort
    """
    if granite_sitename:
        site = granite_sitename.split("/")[0].replace("_", "-")
    else:
        try:
            resp = get_circuit_site_info(cid)

            if isinstance(resp, list):
                site = resp[0]["Z_SITE_NAME"].split("/")[0].replace("_", "-")
        except (KeyError, IndexError):
            msg = f"Unable to get site information in granite for {cid}"
            logger.error(msg)
            abort(500, msg)

    site_name = site.split("-", 1)[1]
    site_list = site_name.split()

    while len(site_list) > 0:
        csite = " ".join(site_list)
        result = check_vpls(csite, cne_istance, cust_name=True)

        if isinstance(result, list):
            return result

        site_list.pop()
    else:
        if cne_istance:
            return

    msg = "Unable to find VPLS in granite while searching with customer sitename"
    logger.error(msg)
    abort(500, msg)


def live_vpls_check(vpls_elements):
    """
    Gets the first 2 Live elements from the VRFID.
    It will then get hub and port information appended to equipment list.

    Input:
      vpls_elements = [{}, {}, {}, {}]

    Output:
      equipment_list = [{},{}]
        or
      abort
    """
    live_paths = []

    for element in vpls_elements:
        if element["ELEMENT_STATUS"] == "Live" and len(live_paths) < 2:
            live_paths.append(element["ELEMENT_NAME"])

    equipment_list = []

    for paths in live_paths:
        # use path elements call on each cid to get hub(CW) and port info
        result = get_path_elements(paths)

        if isinstance(result, list):
            for x in result:
                tid = x["TID"]

                if x["PATH_CATEGORY"] == "ETHERNET TRANSPORT" and tid.endswith("CW"):
                    equipment_list.append(x)
                    break

    if not len(equipment_list) or len(equipment_list) < 2:
        msg = "Unable to find hub transport paths on one or more of the related network paths"
        logger.error(msg)
        abort(500, msg)

    return equipment_list


def equipment_check(equipment_list):
    """
    Checks the equipment network is not legacy Charter or the vendor is not a Cisco device.

    Input:
      equipment_list = [{},{}]

    Output:
      None or abort
    """
    for equip in equipment_list:
        vendor = equip["VENDOR"]
        tid = equip["TID"]
        equip_inst_id = equip["ELEMENT_REFERENCE"]

        equip_uda = get_shelf_udas(equip_inst_id)

        if isinstance(equip_uda, list):
            for uda in equip_uda:
                if uda.get("ATTR_NAME") == "NETWORK":
                    network = uda["ATTR_VALUE"]

                    if vendor == "CISCO" or "L-C" in network:
                        msg = f"Hub device {tid} has a vendor or network which is currently unsupported"
                        logger.error(msg)
                        abort(500, msg)

                    break


def get_network_info(equipment_list):
    """
    Gets the network encapsulation of both hub devices using the port access id or the leg name.

    Input:
      equipment_list = [{}, {}]

    Output:
      network_encap = [{{}, {}}, {{}, {}}] nested dictionary
        or
      abort
    """
    network_encap = []

    for port in equipment_list:
        tid = port["TID"]
        vlan = port["CHAN_NAME"].replace("VLAN", "")

        if (port["LEG_NAME"] != "1") and ("/" in port["LEG_NAME"]):
            port_id = port["LEG_NAME"].split("/")[0]

            if len(port_id) > 4:
                port_id = port_id.replace("LAG", "").replace(" ", "")
        else:
            port_id = port["PORT_ACCESS_ID"]

        paid = f"{port_id}.{vlan}".lower()

        device_config = onboard_and_exe_cmd(
            command="show_routing_instances", hostname=tid, timeout=120, attempt_onboarding=False
        )

        try:
            network_data = device_config["result"]
        except (KeyError, TypeError):
            msg = f"Error when retrieving data from MDSO for {tid}"
            logger.error(msg)
            abort(500, msg)

        if isinstance(network_data, list):
            for network in network_data:
                net_interfaces = network["properties"]["interfaces"]

                for interface in net_interfaces:
                    if paid == interface["config"]["interface"]:
                        network_encap.append(network)
                        break
        else:
            msg = f"Unable to find VPLS information on {tid} for {paid}. Please investigate"
            logger.error(msg)
            abort(500, msg)

    return network_encap


def add_network_link(cid, network_id):
    """
    Adding vpls network to path

    Input:
      cid = "21.L1XX.123456..CHTR"
      network_id = "234567"

    Output:
      None or abort
    """
    logger.info("Adding vpls network to path")
    url = granite_paths_url()

    payload = {
        "PATH_NAME": cid,
        "PATH_REVISION": "1",
        "LEG_NAME": "1",
        "ADD_ELEMENT": "true",
        "PATH_ELEM_SEQUENCE": "1",
        "PATH_ELEMENT_TYPE": "NETWORK_LINK",
        "PARENT_NETWORK_INST_ID": network_id,
    }

    try:
        resp = put_granite(url, payload)
    except Exception as e:
        logger.exception(
            f"Exception while parsing revision create response from Granite paths API "
            f"\nURL: {url} \nPayload: {payload} \nResponse: \n{e}"
        )
        abort(500, "Unable to add vpls network to path. Exception while processing Granite response", url=url)

    return resp


def evcid_update(cid, evcid):
    """
    Checks granite for the next available source mep ID.
    Then adds the EVCID and sorce and destination mep id to CID.

    Input:
      cid = "21.L1XX.123456..CHTR"
      evcid = "234567"

    Output:
      None or Abort
    """
    # Update CID Path with EVC ID
    logger.info(f"Assigning EVCID for {cid}")

    # Setting dest mep blank just incase this is the first source mep id ::10
    dest_mep_id = ""

    result = get_source_mep(evcid)

    if isinstance(result, list):
        so_mep_id = result[0]["NEXT_SOURCE_MEP_ID"]

        mep_id = so_mep_id.rsplit(":")[-1]

        if int(mep_id) >= 100:
            msg = f"Source MEP ID: {so_mep_id} is over 99. Please investigate"
            logger.error(msg)
            abort(500, msg)
        elif mep_id != "10":
            dest_mep_id = f"{evcid}::10"

        put_granite_url = granite_paths_url()

        payload = {
            "PATH_NAME": cid,
            "PATH_REVISION": "1",
            "UDA": {
                "ADDITIONAL ETHERNET INFO": {"EVC ID": evcid},
                "CIRCUIT SOAM PM": {"DESTINATION MEP ID": dest_mep_id, "SOURCE MEP ID": so_mep_id},
            },
        }

        put_granite(put_granite_url, payload)
    else:
        msg = "Error while getting source mep id from granite"
        logger.error(msg)
        abort(500, msg)
