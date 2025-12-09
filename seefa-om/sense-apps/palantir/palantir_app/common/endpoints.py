import palantir_app


ENV = "/qa" if palantir_app.app_config.USAGE_DESIGNATION == "STAGE" else "/prod"


# Granite/Gatekeeper
PATH = (
    "/granite/ise"
    if palantir_app.app_config.USAGE_DESIGNATION == "PRODUCTION"
    else "/gateKeeper/resources/GKRestService"
)
GRANITE_AMOS = f"{PATH}/amos"
GRANITE_CARDS = f"{PATH}/cards"
GRANITE_ELEMENTS = f"{PATH}/pathElements"
GRANITE_NETWORKS = f"{PATH}/networks"
GRANITE_EQUIPMENTS = f"{PATH}/equipments"
GRANITE_MS = f"{PATH}/parentManagedServices"
GRANITE_PATHS = f"{PATH}/paths"
GRANITE_PATHS_FROM_SITE = f"{PATH}/pathsFromSite"
GRANITE_PORTS = f"{PATH}/ports"
GRANITE_SHELVES = f"{PATH}/shelves"
GRANITE_CIRCUIT_SITES = f"{PATH}/circuitSites"
GRANITE_SITES = f"{PATH}/sites"
GRANITE_UDA = f"{PATH}/circuitUDAs"
GRANITE_PATH_RELATIONSHIPS = f"{PATH}/pathRelationship"
GRANITE_ASSOCIATIONS_GET = f"{PATH}/pathAssociations"
GRANITE_ASSOCIATIONS_REMOVE = f"{PATH}/removePathAssociation"
GRANITE_ASSOCIATIONS_NUMBER_PUT = f"{PATH}/numbers"
GRANITE_PATH_CHAN_AVAILABILITY = f"{PATH}/pathChanAvailability"
SHELF_UDAS = f"{PATH}/shelfUDAs"
SHELF_UPDATE = f"{PATH}/shelves"
ELAN_SLM = f"{PATH}/elanPaths"

# Granite/Denodo
DENODO_CIRCUIT_DEVICES = "/denodo/app_int/dv_mdso_model_v4/views/dv_mdso_model_v4"
DENODO_CEDR_DV = "/denodo/app_int/bv_cedr_device_by_"
DENODO_VIEWS = "/denodo/orcas/dv_mdso_model_v3/views/dv_mdso_model_v3"
DENODO_SEEK_TID = "/denodo/app_dev/bv_seek_tid_lookup/views/bv_seek_tid_lookup"
DENODO_SPIRENT_PORT = "/denodo/app_int/dv_spirent_test_port_lookup/views/dv_spirent_test_port_lookup/"
DENODO_SPIRENT_VTA = "/denodo/app_int/dv_spirent_vta_lookup/views/dv_spirent_vta_lookup"

# Crosswalk/IPC
CROSSWALK_DEVICE = "/crosswalk/dms/api/v1/ddi/device"
CROSSWALK_IPADDRESS = "/crosswalk/ipms/api/v1/device/ipAddress"
CROSSWALK_IPBLOCK = "/crosswalk/ipms/api/v1/ipBlock"
CROSSWALK_DHCP = "/crosswalk/ddms/api/v1/dhcpClientClass"

# ISE
ISE_NETWORK_DEVICE = "/ers/config/networkdevice"
