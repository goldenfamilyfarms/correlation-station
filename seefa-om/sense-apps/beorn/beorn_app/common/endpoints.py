import beorn_app

# Granite/Gatekeeper
PATH = (
    "/granite/ise" if beorn_app.app_config.USAGE_DESIGNATION == "PRODUCTION" else "/gateKeeper/resources/GKRestService"
)
GRANITE_ELEMENTS = f"{PATH}/pathElements"
GRANITE_JSON_PATH = f"{PATH}/json/processPath"
GRANITE_PATHS = f"{PATH}/paths"
GRANITE_UDA = f"{PATH}/circuitUDAs"
GRANITE_EQUIPMENTS = f"{PATH}/equipments"
GRANITE_SHELF_UDA = f"{PATH}/shelfUDAs"
ELAN_SLM = f"{PATH}/elanPaths"

# Granite/Denodo
DENODO_ENV = "app_dev" if beorn_app.app_config.USAGE_DESIGNATION == "STAGE" else "app_int"
DENODO_UDA = "/server/atom/dv_circ_path_attr_settings/views/dv_circ_path_attr_settings"
DENODO_CIRCUIT_DEVICES = "/denodo/app_int/dv_mdso_model_v4/views/dv_mdso_model_v4"
DENODO_SPIRENT_VTA = "/prod/denodo/app_int/dv_spirent_vta_lookup/views/dv_spirent_vta_lookup"
DICE_CIRCUIT_TOPOLOGY = f"/denodo/{DENODO_ENV}/dice/views/dv_dice_topology_v5"
DENODO_MDSO_MODEL_V3 = "/denodo/app_int/dv_mdso_model_v3/views/dv_mdso_model_v3?"

# ESET
ESET_VENDOR_MODEL = "eset_db/vendor_model_mapping"

# Crosswalk/IPC
CROSSWALK_ENV = "/qa" if beorn_app.app_config.USAGE_DESIGNATION == "STAGE" else "/prod"
CROSSWALK_DEVICE = f"/{CROSSWALK_ENV}/crosswalk/dms/api/v1/ddi/device"
