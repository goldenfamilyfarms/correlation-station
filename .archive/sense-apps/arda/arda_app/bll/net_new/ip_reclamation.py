import logging

from arda_app.dll.ipc import delete_block, get_subnet_block_by_blockname, delete_device, get_subnet_block_by_ip
from arda_app.dll.granite import get_ip_subnets, get_path_elements, get_granite
from common_sense.common.errors import abort, error_formatter, get_standard_error_summary
from thefuzz import fuzz
from arda_app.bll.net_new.utils.shelf_utils import get_vgw_shelf_info

logger = logging.getLogger(__name__)


def vgw_ipv4_trns(ipv4):
    try:
        ip1, ip2 = ipv4.split("/")
        ip_list = ip1.split(".")
        if ip2 == "31":
            ip_list[3] = str(max(int(ip_list[3]) - 1, 0)).zfill(2)
        else:
            ip_list[3] = str(max(int(ip_list[3]) - 2, 0)).zfill(2)
        new_ipv4 = ".".join(ip_list) + "/" + ip2
        return new_ipv4
    except Exception as ex:
        logger.warn(f"Error transforming VGW IPV4 {ex}")
        return ipv4


def get_vgw_data(cid):
    vgw_ipv4 = None
    endpoint = f"/pathElements?CIRC_PATH_HUM_ID={cid}"
    granite_resp = get_granite(endpoint)
    if isinstance(granite_resp, dict):
        if granite_resp.get("retString") and "No records found" in granite_resp.get("retString"):
            abort(500, f"{cid} does not have an existing record in Granite")
    elif isinstance(granite_resp, list) and granite_resp:
        data = granite_resp[0]
        if data["SERVICE_TYPE"] in ["CUS-VOICE-PRI", "CUS-VOICE-SIP"]:
            vgw_data = get_vgw_shelf_info(cid)
            if vgw_data:
                vgw_ipv4 = vgw_data.get("IPV4_ADDRESS")
                vgw_ipv4 = vgw_ipv4_trns(vgw_ipv4)
            if vgw_ipv4 is None:
                abort(500, f"VGW Circuit {cid} did not have any IPv4 in Granite")
    return vgw_ipv4


def get_subnet_block_by_cid(cid):
    """Retrieves the subnet block from IPC using a circuit's IP subnets in Granite as the block_name"""
    vgw_ipv4 = get_vgw_data(cid)
    if not vgw_ipv4:
        subnets = get_ip_subnets(cid)
        ipv4_block = get_subnet_block_by_blockname(subnets["IPV4_ASSIGNED_SUBNETS"])
        ipv6_block = get_subnet_block_by_blockname(subnets["IPV6_ASSIGNED_SUBNETS"])
        ipv4_glue_block = get_subnet_block_by_blockname(subnets["IPV4_GLUE_SUBNET"])
        ipv6_glue_block = get_subnet_block_by_blockname(subnets["IPV6_GLUE_SUBNET"])
    else:
        ipv4_block = get_subnet_block_by_blockname(vgw_ipv4)
        ipv6_block, ipv4_glue_block, ipv6_glue_block = None, None, None
    return {"ipv4": ipv4_block, "ipv6": ipv6_block, "glue_subnets": {"ipv4": ipv4_glue_block, "ipv6": ipv6_glue_block}}


def verify_disconnect_info_for_ipc(cid, subnets_in_cid):
    path_elements_resp = get_path_elements(cid)[0]
    granite_customer_name = path_elements_resp["CUSTOMER_NAME"]
    granite_customer_acct = path_elements_resp["CUSTOMER_ID"]
    verification_results = {"status": "", "verified": [], "incorrect_information": [], "nonexistent": []}

    for block in subnets_in_cid:
        if block is None:
            continue
        subnet_block = get_subnet_block_by_blockname(block, get_message=True)
        if subnet_block is None or isinstance(subnet_block, str):
            verification_results = update_verification_results_nonexistent(verification_results, subnet_block, block)
        else:
            subnet_block_user_fields = subnet_block.get("userDefinedFields", [])
            for field in subnet_block_user_fields:
                verified_customer = is_customer_verified(field, cid, granite_customer_name, granite_customer_acct)
                if verified_customer == "irrelevant field":
                    continue
                elif verified_customer:
                    verification_results["verified"].append(block)
                else:
                    verification_results["incorrect_information"].append(
                        {"IP": block, "Customer Name": normalize_name(field)}
                    )

    if verification_results["incorrect_information"]:
        verification_results["status"] = get_incorrect_information_status(
            verification_results["verified"], verification_results["incorrect_information"], granite_customer_name
        )
    else:
        if verification_results["verified"]:
            verification_results["status"] = get_verified_ready_status(verification_results["nonexistent"])
        else:
            verification_results["status"] = get_ips_nonexistent_status(verification_results["nonexistent"])

    logger.info(f"IP Verification: {verification_results} CID: {cid}")
    return verification_results


def update_verification_results_nonexistent(verification_results, subnet_block, block):
    if subnet_block is None:
        verification_results["nonexistent"].append(block)
        return verification_results
    if "IP Block not found" in subnet_block:
        verification_results["nonexistent"].append(block)
        return verification_results
    else:
        msg = error_formatter("Crosswalk", "IPC", "Get IP Block by Blockname", subnet_block)
        abort(500, message=msg, summary=get_standard_error_summary(msg))


def is_customer_verified(field, cid, granite_customer_name, granite_customer_acct):
    logger.debug(f"{field = }")
    normalized_customer_name = normalize_name(granite_customer_name)
    if "Company_Name=" in field:
        normalized_field = normalize_name(field)
        name_match_similarity_percentage = fuzz.partial_ratio(normalized_field, normalized_customer_name)
        if customer_name_matches(
            normalized_field, normalized_customer_name, name_match_similarity_percentage
        ) or customer_id_matches(field, cid, granite_customer_acct):
            return True
        else:
            return False
    elif "Notes=" in field and normalized_customer_name in normalize_name(field):
        return True
    else:
        return "irrelevant field"


def normalize_name(name: str):
    # Removes non-alphanumeric characters except spaces from input string and returns the string in upper case
    name = name.replace("Company_Name=", "") if "Company_Name=" in name else name
    name = "".join(filter(lambda x: x.isalnum() or x.isspace(), name)).upper()
    return name


def customer_name_matches(normalized_field: str, normalized_customer_name: str, name_match_similarity_percentage: int):
    return normalized_field == normalized_customer_name or name_match_similarity_percentage >= 80


def customer_id_matches(field, cid, customer_acct_from_granite):
    return customer_acct_from_granite in field or cid in field


def get_incorrect_information_status(verified, incorrect_information, granite_customer_name):
    if not verified:  # the customer name didn't match on any blocks
        customer_names = [name["Customer Name"] for name in incorrect_information]
        abort(
            500,
            f"The customer name listed in Granite ({granite_customer_name}) did not match the customer name(s)"
            f"{customer_names} listed for the circuit's subnet blocks in IPControl.  "
            f"IPControl data: {incorrect_information}",
        )
    else:  # the customer name matched on some but not all blocks
        # we will delete the matching blocks & also return the failed ones
        return "ready_and_incorrect"


def get_verified_ready_status(nonexistent):
    if nonexistent:  # customer name matched but blocks are gone already
        return "ready_and_nonexistent"
    else:
        return "ready"  # customer name matched, ready to delete


def get_ips_nonexistent_status(nonexistent):
    if nonexistent:
        return "all_blocks_nonexistent"
    else:
        abort(500, "This circuit does not contain any IPs ")


def get_status_messages(verified_status, subnets_with_mismatched_names, subnets_with_nonexistent_blocks):
    process_complete_msg, mismatch_msg, nonexistent_msg = "", "", ""

    if verified_status == "all_blocks_nonexistent":
        # The work's already been done for us :)
        process_complete_msg = "All of the subnet blocks for the circuit's IPs have already been removed."
    if verified_status == "ready_and_incorrect":
        mismatch_msg = f" |  IPs without matching Granite/IPControl customer names: {subnets_with_mismatched_names}"
    if verified_status == "ready_and_nonexistent":
        nonexistent_msg = f" |  IPs with nonexistent subnet blocks in IPControl: {subnets_with_nonexistent_blocks}"
    return process_complete_msg, mismatch_msg, nonexistent_msg


def reclaim_mgmt_ip_main(tid, mgmt_ip):
    """A part of the IP reclamation process that reclaims a CPE's management IPs for future use if it's static.
    If it's not static, it can be left alone.

    :param tid: TID/hostname whose management IP will hopefully be reclaimed
    :type tid: str
    :param mgmt_ip: management IP provided from granite_data in Palantir
    :type mgmt_ip: str
    :return: A response for whether or not it was able to be deleted.
    :rtype: dict
    """
    reclaim_resp = delete_device(mgmt_ip)
    logger.info(f"IP response: {reclaim_resp}")
    if "successfully deleted" in reclaim_resp.get("message"):
        return {"message": f"Successfully reclaimed IP: {mgmt_ip}"}
    else:
        abort(
            500,
            f"Unexpected response from IPC after trying to reclaim mgmt IP {mgmt_ip} for {tid}. "
            f"Response: {reclaim_resp}",
        )


def delete_ip_subnet_block_by_cid(cid, container=None):
    """
    Deletes a subnet block from IPC using a circuit's subnet addresses listed in Granite.
    NOTE: You must include the container name holding the block if the block name is not unique
    """
    vgw_ipv4 = get_vgw_data(cid)
    logger.info(f"VGW Info: {vgw_ipv4} CID: {cid}")

    if not vgw_ipv4:
        subnets_in_cid = list(get_ip_subnets(cid).values())
    else:
        subnets_in_cid = [vgw_ipv4]

    logger.info("Verifying customer name in Granite matches the customer name of the subnet block in IPControl")

    blocks_verified = verify_disconnect_info_for_ipc(cid, subnets_in_cid)
    # status will be one of "ready_and_incorrect", "ready_and_nonexistent", "ready", "all_blocks_nonexistent"
    verified_status = blocks_verified["status"]
    subnets_with_mismatched_names = blocks_verified["incorrect_information"]
    subnets_with_nonexistent_blocks = blocks_verified["nonexistent"]

    process_complete_msg, mismatch_msg, nonexistent_msg = get_status_messages(
        verified_status, subnets_with_mismatched_names, subnets_with_nonexistent_blocks
    )
    if process_complete_msg:
        return {"message": process_complete_msg}

    verified_subnets = blocks_verified.get("verified")  # only attempt to remove verified blocks
    missing_subnet_count, removed_subnets, failed_to_remove_subnets = delete_verified_blocks(
        verified_subnets, container, cid
    )
    if no_blocks_found_to_reclaim(missing_subnet_count, removed_subnets, failed_to_remove_subnets):
        abort(500, "This circuit did not contain any subnet blocks to reclaim.")
    elif is_partial_success(removed_subnets, failed_to_remove_subnets):
        return partial_success_message(removed_subnets, failed_to_remove_subnets, nonexistent_msg, mismatch_msg)
    elif is_success(failed_to_remove_subnets, removed_subnets):
        return success_message(removed_subnets, nonexistent_msg, mismatch_msg)
    else:
        return {"message": f"Failed to remove verified IP blocks from IPC for {cid}: {verified_subnets}"}


def delete_verified_blocks(verified_subnets, container, cid):
    missing_subnet_count = len([block for block in verified_subnets if block is None])
    removed_subnets = []
    failed_to_remove_subnets = []
    verified_existing_subnets = [block for block in verified_subnets if block is not None]
    logger.debug(f"{verified_existing_subnets = }")
    for block in verified_existing_subnets:
        ip_without_subnet = block.split("/")[0]  # the subnet's required for /deleteblock, so only removing it here.
        get_resp = get_subnet_block_by_ip(ip_without_subnet, status="Deployed", get_message=True)
        logger.info(f"Get Subnet Block: {get_resp} CID: {cid}")
        if get_resp is None:
            missing_subnet_count += 1
            continue
        if isinstance(get_resp, str):
            if "not found" in get_resp:
                missing_subnet_count += 1
            else:
                msg = error_formatter("Crosswalk", "IPC", "Get IP Block by IP", get_resp)
                abort(500, message=msg, summary=get_standard_error_summary(msg))
        else:
            delete_resp = delete_block(block, container, cid, return_resp=True)
            if delete_resp.get("message", "") == "success":
                removed_subnets.append(block)
            else:
                failed_to_remove_subnets.append({block: delete_resp})
    logger.debug(f"{missing_subnet_count = }\n{removed_subnets = }\n{failed_to_remove_subnets = }")
    return missing_subnet_count, removed_subnets, failed_to_remove_subnets


def no_blocks_found_to_reclaim(missing_subnet_count: int, removed_subnets: list, failed_to_remove_subnets: list):
    return missing_subnet_count > 0 and len(removed_subnets) == 0 and len(failed_to_remove_subnets) == 0


def is_partial_success(removed_subnets: list, failed_to_remove_subnets: list):
    return len(failed_to_remove_subnets) > 0 and len(removed_subnets) > 0


def partial_success_message(removed_subnets, failed_to_remove_subnets, nonexistent_msg, mismatch_msg):
    message = f"Partial success.  Subnet blocks reclaimed: {removed_subnets} | \
Subnets unable to be removed: {failed_to_remove_subnets}"
    if nonexistent_msg:
        message += nonexistent_msg
    if mismatch_msg:
        message += mismatch_msg
    return {"message": message}


def is_success(failed_to_remove_subnets: list, removed_subnets: list):
    return len(failed_to_remove_subnets) == 0 and len(removed_subnets) > 0


def success_message(removed_subnets, nonexistent_msg, mismatch_msg):
    message = f"Subnet blocks removed from IPControl: {removed_subnets} "
    if nonexistent_msg:
        message += nonexistent_msg
    if mismatch_msg:
        message += mismatch_msg
    return {"message": message}
