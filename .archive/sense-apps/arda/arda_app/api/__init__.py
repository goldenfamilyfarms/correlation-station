# Flake8: noqa: E402

from ._routers import (
    v1_cid_router,
    v4_cid_router,
    v5_cid_router,
    v1_isp_router,
    v3_isp_router,
    v1_design_router,
    v1_design_new_router,
    v1_design_mac_router,
    v2_remedy_router,
    v1_tools_router,
    atlas_router,
    v1_internal_router,
)

# CID
from .related_sitename import v1_cid_router as related_sitename_router
from .customer import v4_cid_router as customer_router
from .site import v5_cid_router as site_router
from .circuitpath import v4_cid_router as circuitpath_router

# ISP
from .isp_update_related_circuits import v1_isp_router as isp_update_related_circuits_router
from .optic_check import v1_isp_router as optic_check_router
from .pick_sova_wo import v1_isp_router as pick_sova_wo_check_router
from .transport_path import v3_isp_router as transport_path_router

# from .ispgroup import v1_isp_router as ispgroup_router

# Design
from .circuit_design import v1_design_router as circuit_design_router
from .build_circuit_design import v1_design_router as build_circuit_design_router
from .service_product_eligibility import v1_design_router as service_product_eligibility_router
from .supported_product import v1_design_router as supported_product_router
from .exit_criteria import v1_design_router as exit_criteria_router
from .update_path_status import v1_design_router as update_path_status_router
from .overlay_design import v1_design_router as overlay_design_router
from .meraki_services import v1_design_router as meraki_services_router

# Design New
from .vlan_reservation import v1_design_new_router as vlan_reservation_router
from .ip_reservation import v1_design_new_router as ip_reservation_router
from .ip_swip import v1_design_new_router as ip_swip_router
from .serviceable_shelf import v1_design_new_router as serviceable_shelf_router
from .create_shelf import v1_design_new_router as create_shelf_router
from .create_mtu_transport import v1_design_new_router as create_mtu_transport_router
from .qc_transport_path import v1_design_new_router as qc_transport_path_router
from .assign_handoffs_and_uplinks import v1_design_new_router as assign_handoffs_and_uplinks_router
from .assign_parent_paths import v1_design_new_router as assign_parent_paths_router
from .assign_enni import v1_design_new_router as assign_enni_router
from .assign_evc import v1_design_new_router as assign_evc_router
from .assign_gsip import v1_design_new_router as assign_gsip_router
from .elan_add_vpls import v1_design_new_router as elan_add_vpls_router
from .type_2_hub_work import v1_design_new_router as type_2_hub_work_router
from .type_2_outer_vlan_request import v1_design_new_router as type_2_outer_vlan_request_router
from .light_test_check import v1_design_new_router as light_test_check_router

# Design MAC
from .bandwidth_change import v1_design_mac_router as bandwidth_change_router
from .logical_change import v1_design_mac_router as logical_change_router
from .disconnect import v1_design_mac_router as disconnect_router
from .blacklist_check import v1_design_mac_router as blacklist_check_router
from .design_validation import v1_design_mac_router as design_validation_router

# Remedy
from .remedyticket import v2_remedy_router as remedyticket_router

# Tools
from .adva_rad_by_year import v1_tools_router as adva_rad_by_year_router
from .check_ip_on_network import v1_tools_router as check_ip_on_network_router
from .cpe_swap import v1_tools_router as cpe_swap_router
from .create_bom import v1_tools_router as create_bom_router
from .device import v1_tools_router as device_router
from .ipc_reset import v1_tools_router as ipc_reclaim
from .ipc_container import v1_tools_router as ipc_container_router
from .ip_reclamation import v1_tools_router as ip_reclamation_router
from .ip_reservation_gather import v1_tools_router as ip_reservation_gather_router
from .reclaim_cpe_mgmt_ip import v1_tools_router as reclaim_cpe_mgmt_ip_router
from .expo_order_processing import v1_tools_router as expo_order_processing_router
from .mock import v1_tools_router as mock_router

# Internal
from .health import v1_internal_router as health_router

# Atlas
from .atlas.snmp import atlas_router as snmp_get_router
from .atlas.accessibility import atlas_router as accessibility_router
from .atlas.juniper import juniper_router
from .atlas.juniper.interface_config import juniper_router as interface_config_router

atlas_router.include_router(juniper_router)

__all__ = [
    "v1_cid_router",
    "v4_cid_router",
    "v5_cid_router",
    "v1_isp_router",
    "v3_isp_router",
    "v1_design_router",
    "v1_design_new_router",
    "v1_design_mac_router",
    "v2_remedy_router",
    "v1_tools_router",
    "v1_internal_router",
    # CID
    "related_sitename_router",
    "customer_router",
    "site_router",
    "circuitpath_router",
    # ISP
    "isp_update_related_circuits_router",
    "optic_check_router",
    "pick_sova_wo_check_router",
    "transport_path_router",
    # Design
    "circuit_design_router",
    "build_circuit_design_router",
    "service_product_eligibility_router",
    "supported_product_router",
    "exit_criteria_router",
    "update_path_status_router",
    "overlay_design_router",
    "meraki_services_router",
    # Design New
    "vlan_reservation_router",
    "ip_reservation_router",
    "ip_swip_router",
    "serviceable_shelf_router",
    "create_shelf_router",
    "create_mtu_transport_router",
    "qc_transport_path_router",
    "assign_handoffs_and_uplinks_router",
    "assign_parent_paths_router",
    "assign_enni_router",
    "assign_evc_router",
    "assign_gsip_router",
    "elan_add_vpls_router",
    "type_2_hub_work_router",
    "type_2_outer_vlan_request_router",
    "light_test_check_router",
    # Design MAC
    "bandwidth_change_router",
    "logical_change_router",
    "disconnect_router",
    "blacklist_check_router",
    "design_validation_router",
    # Remedy
    "remedyticket_router",
    # Tools
    "adva_rad_by_year_router",
    "check_ip_on_network_router",
    "cpe_swap_router",
    "create_bom_router",
    "device_router",
    "ipc_reclaim",
    "ipc_container_router",
    "ip_reclamation_router",
    "ip_reservation_gather_router",
    "reclaim_cpe_mgmt_ip_router",
    "expo_order_processing_router",
    "mock_router",
    # Atlas
    "atlas_router",
    "snmp_get_router",
    "accessibility_router",
    "interface_config_router",
    # Internal
    "health_router",
]
