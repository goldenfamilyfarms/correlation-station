import logging

from fastapi import Query

from common_sense.common.errors import abort
from arda_app.dll.mdso import check_onboard, onboard_and_exe_cmd
from arda_app.api._routers import v1_tools_router

logger = logging.getLogger(__name__)


@v1_tools_router.get("/device", summary="Device-level CRUD operations")
def device(
    host: str = Query(..., examples="NYCLNYRG0QW", alias="hostname"),
    cmd: str = Query(
        ...,
        description="Command to execute",
        enum=[
            "agg_vlans",
            "check_onboard",
            "show_interfaces",
            "show_route",
            "show_version",
            "show_isis",
            "show_routing_options",
            "show_chassis",
            "show_l2circuit_status",
            "show_arp_irb",
            "show_vlan_brief",
            "show_interface_description",
            "show_running_config_interface",
        ],
    ),
    param: str = Query(None, description="Optional argument (e.g., 'ge-0/0/0')", examples="ge-0/0/0", alias="args"),
    attempt_onboarding: bool = Query(False, description="Onboard device in MDSO"),
):
    """
    Accept a specific device command, return device response to command
    """

    if cmd in "check_onboard":
        logger.info(
            f"Executing MDSO {cmd} command against {host} \
            with param {param}"
        )
        return check_onboard(host)
    elif cmd in [
        "show_version",
        "show_interfaces",
        "show_route",
        "agg_vlans",
        "show_isis",
        "show_routing_options",
        "show_chassis",
        "show_l2circuit_status",
        "show_arp_irb",
        "show_vlan_brief",
        "show_interface_description",
        "show_running_config_interface",
    ]:
        logger.info(
            f"Executing MDSO onboard and executing command {cmd} for {host} \
                with param {param}"
        )
        return onboard_and_exe_cmd(command=cmd, hostname=host, parameter=param, attempt_onboarding=attempt_onboarding)
    else:
        logger.error(f"Unsupported command {cmd} requested for {host}")
        abort(500, f"Unsupported command {cmd} requested for {host}")
