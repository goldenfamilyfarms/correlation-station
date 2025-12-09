import logging
from re import findall

from fastapi import Depends
from arda_app.bll.circuit_design.bandwidth_change.bw_change_main import bandwidth_change_main
from arda_app.data.mock_circuits.mc_circuit_design import test_case_responses
from arda_app.bll.circuit_design.exit_criteria import create_base_exit_criteria, create_exit_criteria
from arda_app.bll.disconnect import disconnect
from arda_app.bll.logical_change import logical_change_main
from arda_app.bll.models.payloads import (
    BandwidthChangePayloadModel,
    CircuitDesignPayloadModel,
    DisconnectPayloadModel,
    LogicalChangePayloadModel,
)
from arda_app.bll.utils import retaining_ip_addresses
from common_sense.common.errors import abort
from arda_app.common.http_auth import verify_password
from arda_app.common.utils import validate_required_parameters
from arda_app.common.build_circuit_design_template import build_circuit_design_main
from arda_app.bll.circuit_design.common import (
    add_job_validation,
    colo_site_check,
    epl_circuit_check,
    bw_check,
    entrance_criteria_check,
)

from arda_app.api._routers import v1_design_router

logger = logging.getLogger(__name__)


@v1_design_router.post("/circuit_design", summary="SEnSE Circuit Design")
def circuit_design(payload: CircuitDesignPayloadModel, authenticated: bool = Depends(verify_password)):
    """
    Checks eligibility of service and product ordered and runs Design automation process if successful
    """
    payload_dict = payload.model_dump(exclude_none=True)
    logger.info(f"v1/circuit_design payload: {payload_dict}")

    # TEST CASES for regression testing
    test_resp = test_case_responses(payload_dict)

    if test_resp:
        return test_resp

    entrance_criteria_check(payload_dict)

    z_side = True if payload_dict["z_side_info"]["service_type"] == "add" else False
    a_side = (
        True if (payload_dict.get("a_side_info") and payload_dict["a_side_info"]["service_type"] == "add") else False
    )

    if a_side or z_side:
        payload_dict = add_job_validation(payload_dict, z_side, a_side)

    engineering_job_type = (
        payload_dict["z_side_info"]["engineering_job_type"].lower()
        if payload_dict["z_side_info"].get("engineering_job_type")
        else ""
    )

    # Determine which direction the payload_dict will be sent
    if payload_dict.get("z_side_info"):
        z_side_service_type = payload_dict["z_side_info"].get("service_type")
        zcid = payload_dict["z_side_info"].get("cid")

        if z_side_service_type not in ["disconnect", "change_logical", "bw_change"]:
            colo_site_check(zcid)

        # if len(path_regex_match(zcid)) != 1:
        #     abort(
        #        500,
        #        f"Unable to determine CID from: {zcid}",
        #    )

        resp: dict = {}
        if z_side_service_type == "change_logical":
            lc_payload_dict = {
                "service_type": z_side_service_type,
                "product_name": payload_dict["z_side_info"].get("product_name"),
                "cid": zcid,
                "engineering_id": payload_dict["z_side_info"].get("engineering_id"),
                "engineering_name": payload_dict["z_side_info"].get("engineering_name"),
                "class_of_service_needed": payload_dict["z_side_info"].get("class_of_service_needed"),
                "class_of_service_type": payload_dict["z_side_info"].get("class_of_service_type"),
                "change_reason": payload_dict["z_side_info"].get("change_reason"),
                "third_party_provided_circuit": payload_dict["z_side_info"].get("third_party_provided_circuit"),
                "spectrum_primary_enni": payload_dict["z_side_info"].get("spectrum_primary_enni"),
                "spectrum_secondary_enni": payload_dict["z_side_info"].get("spectrum_secondary_enni"),
                "primary_vlan": payload_dict["z_side_info"].get("primary_vlan"),
            }

            resp = logical_change_main(LogicalChangePayloadModel(**lc_payload_dict))

            exit_criteria_payload_dict = {
                "cid": zcid,
                "circ_path_inst_id": resp["circ_path_inst_id"],
                "engineering_job_type": resp.get("engineering_job_type", "none").lower(),
                "product_name": payload_dict["z_side_info"].get("product_name"),
                "cpe_model_number": "NA",
                "maintenance_window_needed": resp["maintenance_window_needed"],
                "hub_work_required": "No",
                "cpe_installer_needed": "No",
            }
            required_exit_values = list(exit_criteria_payload_dict)
            validate_required_parameters(required_exit_values, exit_criteria_payload_dict)
            ec_resp = create_base_exit_criteria(exit_criteria_payload_dict)
            ec_resp["orchestration"] = z_side_service_type

            return create_exit_criteria(exit_criteria_payload_dict, ec_resp)
        elif z_side_service_type == "disconnect":
            side = list(payload_dict.keys())[0]
            return disconnect_processing(payload_dict, side)
        elif z_side_service_type == "bw_change":
            if payload_dict["z_side_info"].get("pid"):
                logger.error("PRISM ID not allowed in bw_change payload_dict.")
                abort(500, "PRISM ID not allowed in bw_change payload_dict.")

            bw_change_payload_dict = {
                "service_type": z_side_service_type,
                "product_name": payload_dict["z_side_info"].get("product_name"),
                "engineering_id": payload_dict["z_side_info"].get("engineering_id"),
                "cid": zcid,
                "bw_speed": payload_dict["z_side_info"].get("bw_speed"),
                "bw_unit": payload_dict["z_side_info"].get("bw_unit"),
                "change_reason": payload_dict["z_side_info"].get("change_reason"),
                "engineering_name": payload_dict["z_side_info"].get("engineering_name"),
                "engineering_job_type": engineering_job_type if engineering_job_type else "",
                "spectrum_primary_enni": payload_dict["z_side_info"].get("spectrum_primary_enni", ""),
                "spectrum_secondary_enni": payload_dict["z_side_info"].get("spectrum_secondary_enni", ""),
                "primary_vlan": payload_dict["z_side_info"].get("primary_vlan", ""),
                "secondary_vlan": payload_dict["z_side_info"].get("secondary_vlan", ""),
                "type_2": payload_dict["z_side_info"].get("third_party_provided_circuit", ""),
            }

            if payload_dict["z_side_info"].get("retain_ip_addresses"):
                bw_change_payload_dict["retain_ip_addresses"] = payload_dict["z_side_info"]["retain_ip_addresses"]

            if payload_dict["z_side_info"].get("primary_fia_service_type"):
                bw_change_payload_dict["primary_fia_service_type"] = payload_dict["z_side_info"][
                    "primary_fia_service_type"
                ]

            if payload_dict["z_side_info"].get("usable_ip_addresses_requested"):
                bw_change_payload_dict["usable_ip_addresses_requested"] = payload_dict["z_side_info"][
                    "usable_ip_addresses_requested"
                ]

            if payload_dict["z_side_info"].get("ip_address"):
                bw_change_payload_dict["ip_address"] = payload_dict["z_side_info"]["ip_address"]

            if payload_dict["z_side_info"].get("connector_type"):
                bw_change_payload_dict["connector_type"] = payload_dict["z_side_info"]["connector_type"]

            if payload_dict["z_side_info"].get("uni_type"):
                bw_change_payload_dict["uni_type"] = payload_dict["z_side_info"]["uni_type"]

            resp = bandwidth_change_main(BandwidthChangePayloadModel(**bw_change_payload_dict))

            if payload_dict["z_side_info"]["engineering_job_type"] == "Express BW Upgrade":
                exit_criteria_payload_dict = {
                    "cid": zcid,
                    "circ_path_inst_id": resp["circ_path_inst_id"],
                    "engineering_job_type": engineering_job_type if engineering_job_type else "none",
                    "product_name": payload_dict["z_side_info"].get("product_name"),
                    "cpe_model_number": "NA",
                    "maintenance_window_needed": "No",
                    "hub_work_required": "No",
                    "cpe_installer_needed": "No",
                }
            else:
                exit_criteria_payload_dict = {
                    "cid": zcid,
                    "circ_path_inst_id": resp["circ_path_inst_id"],
                    "engineering_job_type": engineering_job_type if engineering_job_type else "none",
                    "product_name": payload_dict["z_side_info"].get("product_name"),
                    "cpe_model_number": "NA",
                    "maintenance_window_needed": resp["mw_needed"],
                    "hub_work_required": ("Yes" if resp["hub_work_required"] is True else "No"),
                    "cpe_installer_needed": ("Yes" if resp["cpe_installer"] is True else "No"),
                }

                if resp.get("circuit_design_notes"):
                    exit_criteria_payload_dict["circuit_design_notes"] = resp["circuit_design_notes"]

            required_exit_values = list(exit_criteria_payload_dict)
            validate_required_parameters(required_exit_values, exit_criteria_payload_dict)
            ec_resp = create_base_exit_criteria(exit_criteria_payload_dict)
            ec_resp["orchestration"] = z_side_service_type

            return create_exit_criteria(exit_criteria_payload_dict, ec_resp)

        # This is not a (change_logical, disconnect, bw_change) will flow to Build Ciruit Design
        if z_side_service_type in ("net_new_cj", "net_new_qc", "net_new_serviceable", "net_new_no_cj"):
            # whitelist for bw_check
            if payload_dict["z_side_info"].get("product_name") in (
                "Carrier E-Access (Fiber)",
                "Carrier Fiber Internet Access",
                "EP-LAN (Fiber)",
                "EPL (Fiber)",
                "Fiber Internet Access",
            ):
                # checking bandwidth to ensure granite and salesforce match
                bw_speed = payload_dict["z_side_info"].get("bw_speed")
                bw_unit = payload_dict["z_side_info"].get("bw_unit")

                bw_check(zcid, bw_speed, bw_unit)

            # Check for EPL circuits to ensure we have a proper circuit before design
            if payload_dict["z_side_info"].get("product_name") == "EPL (Fiber)":
                epl_circuit_check(payload_dict)

            # Grabbing z side payload first
            payload_list = [{"z_side_info": payload_dict.get("z_side_info")}]

            # Adding a side if it exist
            if payload_dict.get("a_side_info"):
                payload_list.append({"a_side_info": payload_dict.get("a_side_info")})

            exit_dict = {}

            # Will loop through each side of payload z side then a side(if exist)
            for side_info in payload_list:
                side_name = list(side_info.keys())[0]

                resp = build_circuit_design_main(side_info)

                if isinstance(resp, list):
                    circ_path_inst_id = next(
                        (
                            item.get("circ_path_inst_id")
                            for item in resp
                            if isinstance(item, dict) and item.get("circ_path_inst_id")
                        ),
                        "Missing path instance id",
                    )

                    transport_upgrade = any(
                        item.get("transport_upgrade", False) for item in resp if isinstance(item, dict)
                    )

                    cpe_model_number = next(
                        (
                            item.get("cpe_model_number")
                            for item in resp
                            if isinstance(item, dict) and item.get("cpe_model_number")
                        ),
                        "NA",
                    )
                else:
                    circ_path_inst_id = resp.get("circ_path_inst_id")
                    transport_upgrade = resp.get("transport_upgrade", False)
                    cpe_model_number = resp.get("cpe_model_number", "NA")

                exit_criteria_payload_dict = {
                    "cid": zcid,
                    "circ_path_inst_id": circ_path_inst_id,
                    "engineering_job_type": engineering_job_type if engineering_job_type else "new",
                    "product_name": payload_dict[side_name].get("product_name"),
                    "cpe_model_number": cpe_model_number,
                    "maintenance_window_needed": "Yes - Hub Impacted - Inflight Customer Only Impacted"
                    if z_side_service_type == "net_new_serviceable" and transport_upgrade
                    else "No",
                    "hub_work_required": "Yes"
                    if z_side_service_type == "net_new_cj"
                    or (z_side_service_type == "net_new_serviceable" and transport_upgrade)
                    else "No",
                    "cpe_installer_needed": "Yes",
                }
                # if payload contains request to retain IP addresses
                retain_ips = (
                    payload_dict[side_name].get("retain_ip_addresses")
                    if payload_dict[side_name].get("retain_ip_addresses")
                    else ""
                )
                retain_ip_decision = r"([Y|y][E|e][S|s])"
                if findall(retain_ip_decision, retain_ips):
                    exit_criteria_payload_dict = retaining_ip_addresses(
                        payload_dict.get(side_name), exit_criteria_payload_dict
                    )
                # check if product is ELAN and add additional exit fields
                if payload_dict[side_name].get("product_name") == "EP-LAN (Fiber)":
                    customer_elan = resp[-3].get("customers_elan_name", "NA")
                    create_new_elan_instance = resp[-3].get("create_new_elan_instance", "NA")

                    exit_criteria_payload_dict["create_new_elan_instance"] = "Yes" if create_new_elan_instance else "No"
                    exit_criteria_payload_dict["customer_elan_name"] = customer_elan

                cpe_gear = payload_dict[side_name].get("cpe_gear")
                if cpe_gear:
                    # RAD-ETX203AX (1G) will get converted to ETX203AX
                    # will use this value to compare to model we get back from device topology
                    cpe_gear = cpe_gear.split("-", 1)[-1].split()[0]
                    pm = payload_dict[side_name].get("project_manager_email")
                    sdm = payload_dict[side_name].get("service_delivery_manager_email")
                    cc = payload_dict[side_name].get("construction_coordinator_email")
                    pid = payload_dict[side_name].get("pid")
                    epr = payload_dict[side_name].get("engineering_name")

                    if cpe_gear not in cpe_model_number:
                        exit_criteria_payload_dict["email_recipients"] = f"{pm}, {sdm}, {cc}"
                        exit_criteria_payload_dict["email_bcc"] = "DL-SENOE-SEEFA-CD-Wave-Change@charter.com"
                        exit_criteria_payload_dict["email_subject"] = f"PRISM ID {pid} - {epr} - CPE Change"
                        exit_criteria_payload_dict["email_body"] = (
                            f"Circuit Design has changed the CPE to be installed at the customer site from a "
                            f"'{cpe_gear}' to a '{cpe_model_number}'. Please update the team that is "
                            "responsible for building this project"
                        )
                        exit_criteria_payload_dict["email_from"] = "DL-SEE&O-ECD-Prism-Design-Update@charter.com"

                required_exit_values = list(exit_criteria_payload_dict)
                validate_required_parameters(required_exit_values, exit_criteria_payload_dict)
                ec_resp = create_base_exit_criteria(exit_criteria_payload_dict)
                ec_resp["orchestration"] = z_side_service_type

                # Checking if product is EPL and will add to exict dict per side
                if payload_dict[side_name].get("product_name") == "EPL (Fiber)":
                    exit_dict[side_name] = create_exit_criteria(exit_criteria_payload_dict, ec_resp)
                else:
                    return create_exit_criteria(exit_criteria_payload_dict, ec_resp)

            return exit_dict

        abort(500, f"Build Circuit Design Error: service_type of {z_side_service_type} is unsupported")

    abort(500, "z_side_info field missing from payload_dict")


def disconnect_processing(payload_dict: dict, side: str):
    disco_payload_dict = {
        "service_type": "disconnect",
        "product_name": payload_dict[side].get("product_name"),
        "cid": payload_dict[side].get("cid"),
        "service_location_address": payload_dict[side].get("service_location_address"),
        "product_family": payload_dict[side].get("product_family"),
        "engineering_name": payload_dict[side].get("engineering_name"),
    }

    resp = disconnect(DisconnectPayloadModel(**disco_payload_dict))

    exit_criteria_payload_dict = {
        "cid": payload_dict[side].get("cid"),
        "circ_path_inst_id": resp["circ_path_inst_id"],
        "engineering_job_type": resp.get("engineering_job_type", "none").lower(),
        "product_name": payload_dict[side].get("product_name"),
        "cpe_model_number": resp.get("cpe_model", "none").upper(),
        "blacklist": resp["blacklist"],
        "network": resp["networkcheck"],
        "hub_work_required": resp["hub_work_required"],
        "cpe_installer_needed": resp["cpe_installer_needed"],
    }

    if resp.get("cosc_blacklist_ticket"):
        exit_criteria_payload_dict["cosc_blacklist_ticket"] = resp["cosc_blacklist_ticket"]

    required_exit_values = list(exit_criteria_payload_dict.keys())
    validate_required_parameters(required_exit_values, exit_criteria_payload_dict)
    ec_resp = create_base_exit_criteria(exit_criteria_payload_dict)
    ec_resp["orchestration"] = "disconnect"
    response = create_exit_criteria(exit_criteria_payload_dict, ec_resp)
    return response
