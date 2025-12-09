import logging
import re

from common_sense.common.errors import abort
from arda_app.dll.arin import whois_check, delete_arin_record, create_arin_record, whois_record
from arda_app.dll.granite import get_ip_subnets, get_path_elements
from thefuzz import fuzz
from time import sleep

logger = logging.getLogger(__name__)


def regex_info(info):
    new_info = info
    regex = [("&", "AND"), ("[_-]", " "), ("[\\/#,+()$~%.'\":*?<>}{]", "")]
    for old, new in regex:
        new_info = re.sub(old, new, new_info)
    return new_info, info == new_info


def check_cidr(ip, unswip=False):
    if ip:
        cidr = ip.split("/")[1]  # Looking for ipv4 with subnet /28-31 or ipv6 with /48, /64, /127
        if unswip:
            if int(cidr) <= 27:
                resp = f"IP un-SWIP operation aborted.  IPv4 block {ip} larger than /28."
                logger.info(resp)
                abort(500, resp)
            elif ":" in ip:
                if cidr not in ["48", "64", "127"]:
                    resp = (
                        f"IP un-SWIP operation aborted.  IPv6 address {ip} has a CIDR value other than /48, /64 or /127."
                    )
                    logger.info(resp)
                    abort(500, resp)
        if int(cidr) in range(28, 31) or cidr in ["48", "64", "127"]:
            return True
        else:
            return False
    else:
        return False


def ip_swip_main(ipv4_lan, ipv6_route, customer_info):
    # Part 1, cidr check
    logger.info("Intake validation completed successfully, beginning IP SWIP")
    assigned = []
    failed_assignment = []

    ips = [ip for ip in [ipv4_lan, ipv6_route] if check_cidr(ip)]

    if len(ips) < 1:
        resp = {"message": "IP SWIP operation failed.", "IPs that fall out of subnet range": f"{ips}"}
        logger.info(f"IP SWIP operation failed, returning payload: \n{resp}")
        abort(500, resp)

    # Part 2, loop through ip addresses and call whois on each ip then store in object
    whoIs = {}
    ip_info = {}

    for ip in ips:
        customer_id, handle, org = whois_record(ip)
        whoIs[ip] = [customer_id, handle, org]

    # Part 3, now we have the org status for both ipV4 and ipV6
    # We can run the delete on one or both
    if ipv4_lan not in ips:
        ipV4_Org = True
    else:
        ipV4_Org = whoIs[ipv4_lan][2]

    if ipv6_route not in ips:
        ipV6_Org = True
    else:
        ipV6_Org = whoIs[ipv6_route][2]

    # Execute delete arin record on the IP Addresses that are not Charter
    # Update with WHOIS call afterwards
    if not ipV4_Org:
        for x in range(4):
            logger.debug("Deleting IPV4 Record")
            if not delete_arin_record(whoIs[ipv4_lan][0], whoIs[ipv4_lan][1]):
                continue
            sleep(10)
            customer_id, handle, org = whois_record(ipv4_lan)
            if org:
                whoIs.update({ipv4_lan: [customer_id, handle, org]})
                ipV4_Org = org
                break
            if x != 3:
                sleep(30)

    if not ipV6_Org:
        for x in range(4):
            logger.debug("Deleting IPV6 Record")
            if not delete_arin_record(whoIs[ipv6_route][0], whoIs[ipv6_route][1]):
                continue
            sleep(10)
            customer_id, handle, org = whois_record(ipv6_route)
            if org:
                whoIs.update({ipv6_route: [customer_id, handle, org]})
                ipV6_Org = org
                break
            if x != 3:
                sleep(30)

    # Part 4 Create ARIN Records and record fallout
    if ipV4_Org and ipV6_Org:
        logger.debug("Creating ARIN Records...")
        for ip in ips:
            failed, ticket, error_code = create_arin_record(ip, customer_info, whoIs[ip][1])

            if failed:
                ip_info = {}
                ip_info["ip"] = ip
                ip_info["status"] = "failed"
                ip_info["error_code"] = error_code
                logger.info(f"ARIN record creation failed for {ip}, received error code {error_code}")
                failed_assignment.append(ip_info)
            elif ticket:
                ip_info = {}
                ip_info["ip"] = ip
                ip_info["ticket"] = ticket
                ip_info["status"] = "pending"
                logger.info(f"ARIN record creation pending, received ticket {ticket}")
                assigned.append(ip_info)
            else:
                ip_info = {}
                ip_info["ip"] = ip
                ip_info["status"] = "success"
                logger.info(f"ARIN record creation completed successfully for {ip}")
                assigned.append(ip_info)

    if len(failed_assignment) > 0:
        resp = {
            "message": "IP SWIP operation completed.",
            "IPs that have been reassigned": f"{assigned if len(assigned) > 0 else 0}",
            "IPs that failed assignment": f"{failed_assignment if len(failed_assignment) > 0 else 0}",
        }
        logger.info(f"IP SWIP operation completed successfully, returning payload: \n{resp}")
        return resp
    else:
        # Both IPs have been SWIPd
        resp = {"message": "IP SWIP operation completed", "IPs Assigned": f"{assigned}"}
        logger.info(f"IP SWIP operation completed, returning payload: \n{resp}")
        return resp


def verify_disconnect_info_for_unswip(cid, list_of_subnets_in_cid):
    """
    Takes a CID and a list of the circuit's subnets that require unSWIP-ing (retrieved from Granite) to
    verify that the circuit's customer name is the same as what is shown for the subnet's customer name in ARIN.

    :param: cid
    :type: string
    :param: list_of_subnets_in_cid
    :type: list (of strings)
    :rtype: dict
    """
    subnet_dict = {
        "verification_status": "",
        "verified": [],
        "incorrect_information": [],
        "already_owned_by_charter": [],
    }

    customer_name_from_granite = get_path_elements(cid)[0]["CUSTOMER_NAME"]

    # NOTE: whois_check returns resp.json()["net"] instead of just resp.json()
    for subnet in list_of_subnets_in_cid:
        # subnets can be blank/null in granite, like IPv4_glue_subnet, and won't have a record to check
        if subnet is not None:
            whois_record_for_subnet = whois_check(subnet)
            customer_ref = whois_record_for_subnet.get("customerRef")
            # If customerRef doesn't exist, there's no name to retrieve.  There will usually be an orgRef in its place.
            customer_name_from_arin = customer_ref.get("@name") if customer_ref else None
            logger.info(
                f"Comparing customer names.  Granite: {customer_name_from_granite} vs ARIN: {customer_name_from_arin}"
            )

            if customer_name_from_arin:
                # Compares both strings to see how close they match and returns an int based on closeness %
                name_match_similarity_percentage = fuzz.token_set_ratio(
                    customer_name_from_arin, customer_name_from_granite
                )
                if (
                    customer_name_from_arin.upper() == customer_name_from_granite.upper()
                    or name_match_similarity_percentage >= 95
                ):
                    # These will be unSWIP'd
                    subnet_dict["verified"].append(subnet)
                else:
                    # The customer name in Granite didn't match the name listed in ARIN
                    subnet_dict["incorrect_information"].append({"IP": subnet, "Name": customer_name_from_arin})

            elif not customer_name_from_arin:
                orgref_name = whois_record_for_subnet.get("orgRef").get("@name")
                logger.info(f"Customer name not found in ARIN.  Using orgRef name instead: {orgref_name}")
                if "Charter Communications" in orgref_name:
                    # If the orgRef is Charter Communications Inc, it shouldn't need to be unSWIP'd
                    subnet_dict["already_owned_by_charter"].append(subnet)
                else:
                    # The customer name in Granite didn't match the name listed in ARIN
                    subnet_dict["incorrect_information"].append({"IP": subnet, "Name": orgref_name})

    if subnet_dict["incorrect_information"]:
        # If a customer name mismatch was found
        if not subnet_dict["verified"]:
            # None of the records match
            resp = (
                f"The customer name listed in Granite ({customer_name_from_granite}) did not match the customer"
                f" name(s) listed for the circuit's IPs in ARIN.  ARIN data: {subnet_dict['incorrect_information']}"
            )
            logger.error(resp)
            abort(500, resp)

        elif subnet_dict["verified"]:
            # If there is a mismatch between customer name in ARIN and Granite BUT some of the records match:
            #   unSWIP the matching ones & also return the failed ones
            subnet_dict["verification_status"] = "ready_and_incorrect"

    # Everything's either verified or listed under Charter
    elif not subnet_dict["incorrect_information"]:
        if not subnet_dict["verified"]:
            if subnet_dict["already_owned_by_charter"]:
                # If the only records found have all been returned to Charter already
                subnet_dict["verification_status"] = "all_charter_owned"
            else:
                resp = "This circuit does not contain any IPs"
                logger.error(resp)
                abort(500, resp)
        else:
            if subnet_dict["already_owned_by_charter"]:
                subnet_dict["verification_status"] = "ready_and_owned"
            else:
                # Good to go!
                subnet_dict["verification_status"] = "ready"

    logger.info(f"Verification verdict: {subnet_dict}")
    return subnet_dict


def ip_unswip_main(cid):
    """Gathers IP information to delete an organization's ARIN records"""
    # Part 1, cidr check
    logger.info("Intake validation completed successfully, beginning IP unSWIP")
    failed_assignment = []
    subnets_with_mismatched_names = ""
    subnets_already_owned_by_charter = ""
    list_of_subnets_in_cid = ipv4_lan, ipv6_route, ipv4_glue, ipv6_glue = list(get_ip_subnets(cid).values())

    logger.info("Verifying customer name in Granite matches the names for each IP's ARIN record")
    records_verified = verify_disconnect_info_for_unswip(cid, list_of_subnets_in_cid)
    verified_status = records_verified.get("verification_status")

    if verified_status == "all_charter_owned":
        # The work's already been done for us :)
        message = "All of the ARIN records for the circuit's IPs have already been returned to Charter"
        logger.info(message)
        return {"message": message}

    elif "ready" in verified_status:
        # if the status is anything other than "all"
        list_of_subnets_in_cid = records_verified.get("verified")
        if verified_status == "ready_and_incorrect":
            # List the incorrectly named subnets at the end and only proceed with the verified subnets
            subnets_with_mismatched_names = records_verified.get("incorrect_information")
        elif verified_status == "ready_and_owned":
            # List the subnets already returned to Charter at the end and only proceed with the verified subnets
            subnets_already_owned_by_charter = records_verified.get("already_owned_by_charter")

    if ipv4_lan is None and ipv6_route is None:
        resp = f"IP un-SWIP operation failed.  No IPv4 or IPv6 subnets were found in Granite for {cid}."
        logger.info(resp)
        abort(500, resp)

    ips = [ip for ip in list_of_subnets_in_cid if check_cidr(ip, unswip=True)]

    if len(ips) < 1:
        resp = f"IP un-SWIP operation failed.  IPs that fall out of subnet range: {ips}"
        logger.info(resp)
        abort(500, resp)

    # Part 2, loop through ip addresses and call whois on each ip then store in object
    whoIs = {}
    for ip in ips:
        try:
            customer_id, handle, org = whois_record(ip)
            whoIs[ip] = [customer_id, handle, org]
        except Exception:  # Whois found nothing
            logger.exception(f"Exception during WHOIS record lookup for {ip}")
            ip_info = {}
            ip_info["ip"] = ip
            ip_info["status"] = "No WHOIS record"
            failed_assignment.append(ip_info)

    logger.info(f"WHOIS record information: {whoIs}")

    # Part 3, now we have the org status for both ipV4 and ipV6
    # We can run the delete on one or both
    if ipv4_lan not in ips:
        ipV4_Org = True
    else:
        ipV4_Org = whoIs[ipv4_lan][2]

    if ipv6_route not in ips:
        ipV6_Org = True
    else:
        ipV6_Org = whoIs[ipv6_route][2]

    if ipv4_glue not in ips:
        glue_ipV4_Org = True
    else:
        glue_ipV4_Org = whoIs[ipv4_glue][2]

    if ipv6_glue not in ips:
        glue_ipV6_Org = True
    else:
        glue_ipV6_Org = whoIs[ipv6_glue][2]

    # Execute delete arin record on the IP Addresses that
    # are not Charter until both deleted statuses return true
    # then will break out of inner while loop
    # If only one IP Address is not Charter then delete_arin_record
    # will run only for that IP Address
    deletedIpv4 = False
    deletedIpv6 = False
    deletedIpv4_glue = False
    deletedIpv6_glue = False

    for _ in range(3):
        if not ipV4_Org or not ipV6_Org or not glue_ipV4_Org or not glue_ipV6_Org:
            for _ in range(3):
                if not deletedIpv4 or not deletedIpv6 or not deletedIpv4_glue or not deletedIpv6_glue:
                    if ipV4_Org:
                        deletedIpv4 = True
                    else:
                        logger.debug("Deleting IPV4 Record")
                        deletedIpv4 = delete_arin_record(whoIs[ipv4_lan][0], whoIs[ipv4_lan][1])

                    if ipV6_Org:
                        deletedIpv6 = True
                    else:
                        logger.debug("Deleting IPV6 Record")
                        deletedIpv6 = delete_arin_record(whoIs[ipv6_route][0], whoIs[ipv6_route][1])

                    if glue_ipV4_Org:
                        deletedIpv4_glue = True
                    else:
                        logger.debug("Deleting IPV4 Glue Subnet Record")
                        deletedIpv4_glue = delete_arin_record(whoIs[ipv4_glue][0], whoIs[ipv4_glue][1])

                    if glue_ipV6_Org:
                        deletedIpv6_glue = True
                    else:
                        logger.debug("Deleting IPV6 Glue Subnet Record")
                        deletedIpv6_glue = delete_arin_record(whoIs[ipv6_glue][0], whoIs[ipv6_glue][1])
                    sleep(30)

                # After deleted status returns true then run whois until true
                if ipV4_Org:
                    pass
                else:
                    customer_id, handle, org = whois_record(ipv4_lan)
                    whoIs.update({ipv4_lan: [customer_id, handle, org]})
                    ipV4_Org = whoIs[ipv4_lan][2]

                if ipV6_Org:
                    pass
                else:
                    customer_id, handle, org = whois_record(ipv6_route)
                    whoIs.update({ipv6_route: [customer_id, handle, org]})
                    ipV6_Org = whoIs[ipv6_route][2]

                if glue_ipV4_Org:
                    pass
                else:
                    customer_id, handle, org = whois_record(ipv4_glue)
                    whoIs.update({ipv4_glue: [customer_id, handle, org]})
                    glue_ipV4_Org = whoIs[ipv4_glue][2]

                if glue_ipV6_Org:
                    pass
                else:
                    customer_id, handle, org = whois_record(ipv6_glue)
                    whoIs.update({ipv6_glue: [customer_id, handle, org]})
                    glue_ipV6_Org = whoIs[ipv6_glue][2]

            sleep(30)

    # The IPs have been un-SWIP'd
    unswipd_ips = [ip for ip in list_of_subnets_in_cid if ip is not None]
    logger.info(f"Un-SWIP successful.  The ARIN records for these IPs have been removed: {unswipd_ips}")

    message = f"IPs removed from ARIN: {unswipd_ips}"

    if subnets_with_mismatched_names:
        message = (
            f"Partial success.  IPs removed from ARIN: {unswipd_ips}  |  IPs without matching Granite/ARIN "
            f"customer names: {subnets_with_mismatched_names}"
        )
        return {"message": message}

    elif subnets_already_owned_by_charter:
        message += f"  |  IPs already returned to Charter in ARIN: {subnets_already_owned_by_charter}"
        return {"message": message}

    else:
        return {"message": message}
