from arda_app.common import app_config

# Granite/Gatekeeper
GRANITE_COMMON_PATH = (
    "/granite/ise" if app_config.USAGE_DESIGNATION == "PRODUCTION" else "/gateKeeper/resources/GKRestService"
)

# Helios (data lake)
CARS_ISP_GROUPS = "/prod/dsl/helios/cat_aodevs_est/sch_src_aodevs_est/vw_isp_groups"

# Crosswalk/IPC
ENV = "/qa" if app_config.USAGE_DESIGNATION == "STAGE" else "/prod"

CROSSWALK_DEVICE = f"{ENV}/crosswalk/dms/api/v1/ddi/device"
CROSSWALK_IPADDRESS = f"{ENV}/crosswalk/ipms/api/v1/device/ipAddress"
CROSSWALK_IPBLOCK_V1 = f"{ENV}/crosswalk/ipms/api/v1/ipBlock"
CROSSWALK_IPBLOCK_V1_DELETE = f"{ENV}/crosswalk/ipms/api/v1/ipblock"
CROSSWALK_IPBLOCK_V2 = f"{ENV}/crosswalk/ipms/api/v2/ipBlock"
CROSSWALK_IPBLOCK_V3 = f"{ENV}/crosswalk/ipms/api/v3/ipBlock"
CROSSWALK_IPBLOCK_V4 = f"{ENV}/crosswalk/ipms/api/v4/ipBlock"
CROSSWALK_DHCP = f"{ENV}/crosswalk/ddms/api/v1/dhcpClientClass"
CROSSWALK_ACCOUNT = f"{ENV}/crosswalk/eos/api/v1/account"
CROSSWALK_ENGINEERING = "https://api.crosswalk.chtrse.com/prod/crosswalk/eos/api/v1/engineering"  # only prod
