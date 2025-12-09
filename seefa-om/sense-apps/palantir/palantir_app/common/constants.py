FIA = "FIA"
DDOS_PRODUCTS = [
    "DDoS Protection",
    "DDoS Protection Proactive",
    "DDoS Protections Reactive",
    "DDoS Protection Always On",
    "DDoS Protection - Always On",
]
UNSUPPORTED_DDOS_PRODUCTS = ["DDoS Protection Proactive", "DDoS Protections Reactive"]


DDOS_ALWAYS_ON_PROTECTION = ["PROTECTED ALWAYS ON L-TWC / L-BHN", "PROTECTED ALWAYS ON L-CHTR"]
DDOS_PROTECTION = ["PROTECTED DETECT AND MITIGATE L-TWC / L-BHN", "PROTECTED DETECT AND MITIGATE L-CHTR"]


MBPS_TO_BITS = 1000000
GBPS_TO_BITS = 1000000000
BANDWIDTH_VALUES = {
    "MBPS": MBPS_TO_BITS,
    "MBPS_100": 100 * MBPS_TO_BITS,
    "MBPS_1000": 1000 * MBPS_TO_BITS,
    "GBPS": GBPS_TO_BITS,
    "GBPS_10": 10 * GBPS_TO_BITS,
}

NETWORK_TO_GRANITE_MODEL_MAP = {
    "FSP 150-GE114Pro": "FSP 150-GE114PRO-C",
    "FSP150CC-GE114": "FSP 150-GE114PRO-C",
    "FSP150CC-XG116PRO": "FSP 150-XG116PRO",
    "ETX-203AX": "ETX203AX/2SFP/2UTP2SFP",
    "ETX-2i-10G-B-8SFPP": "ETX-2I-10G-B/8.5/8SFPP",
    "FSP150CC-XG116PRO (H)": "FSP 150-XG116PROH",
    "FSP150CC-XG120PRO": "FSP 150-XG120PRO",
    "ETX-220A": "ETX-220A",
    "ETX-2I-10G-LC": "ETX-2I-10G/4SFPP/4SFP4UTP",
    "ETX-2I-10G": "ETX-2I-10G/4SFPP/24SFP",
    "FSP 150-XG108": "FSP 150-XG108",
    "FSP150-XG118PRO (SH)": "FSP 150-XG118PRO (SH)",
}


# Granite values
ADVA_NETCONF_MODELS = (
    NETWORK_TO_GRANITE_MODEL_MAP["FSP150CC-XG116PRO"],
    NETWORK_TO_GRANITE_MODEL_MAP["FSP150CC-XG116PRO (H)"],
    NETWORK_TO_GRANITE_MODEL_MAP["FSP150CC-XG120PRO"],
    NETWORK_TO_GRANITE_MODEL_MAP["FSP150-XG118PRO (SH)"],
)


FIA_TOPOLOGY_INDEXES = {"z_side": {"topology_index": 0, "endpoint_index": -1, "address_index": 0}}

ELINE_TOPOLOGY_INDEXES = {
    "a_side": {"topology_index": 0, "endpoint_index": 0, "address_index": 0},
    "z_side": {"topology_index": 1, "endpoint_index": -1, "address_index": 1},
}

COMPLIANT = "compliant"

NEW_ORDER_TYPE = "NEW"
ADD_ORDER_TYPE = "ADD"
CHANGE_ORDER_TYPE = "CHANGE"
PARTIAL_DISCO_ORDER_TYPE = "PARTIAL DISCONNECT"
FULL_DISCO_ORDER_TYPE = "FULL DISCONNECT"
DOCSIS_NEW_ORDER_TYPE = "DOCSIS NEW"
DOCSIS_CHANGE_ORDER_TYPE = "DOCSIS CHANGE"
WIA_ORDER_TYPE = "WIA"
ASSTN_USED_STATUS = "Used"
ASST_PUT_NUMBER_TYPE = "EVC ID"
ASSOCIATION_STATUS_CHG_PRODUCTS = ("EPL", "EVPL", "CARRIER E-ACCESS")


DOCSIS_PREFIX = "DOCSIS "

FULL = "FULL"


DESIGN_COMPLIANCE_STAGE = "Order Design Compliance"
NETWORK_COMPLIANCE_STAGE = "Network Design Compliance"
NETWORK_ORDER_COMPLIANCE_STAGE = "Network Order Compliance"
PATH_STATUS_STAGE = "Path Status Update"
SITE_STATUS_STAGE = "Site Status Update"
IP_DISCONNECT_STAGE = "IP Disconnect Processes"
CPE_IP_RELEASE_STAGE = "CPE IP Release Process"
ISP_STAGE = "ISP Disconnect Process"
IP_UNSWIP_STAGE = "IP UnSWIP"
IP_RECLAIM_STAGE = "IP Reclaim"
INTERNAL_ENG_ID = "0058Z000009SI07QAG"

ISP_INFO = "ISP Information"
ISP_REQUIRED = "ispRequired"

SUPPORTED_ORDER_TYPES = (
    NEW_ORDER_TYPE,
    CHANGE_ORDER_TYPE,
    PARTIAL_DISCO_ORDER_TYPE,
    FULL_DISCO_ORDER_TYPE,
    DOCSIS_NEW_ORDER_TYPE,
    DOCSIS_CHANGE_ORDER_TYPE,
)


GRANITE_DISCONNECT_STATUS = ["Pending Decommission"]
GRANITE_STATUS_LIVE = "Live"
READY_TO_SET_LIVE_STATUSES = ["Designed", "Auto-Designed", "Auto-Provisioned"]
SURPRISE_STATUSES = ["Planned", "Auto-Planned", "Ordered", "Testing", "DO NOT USE", "Draft"]
SET_CONFIRMED_TRUE = "TRUE"


NETWORK_LINK = "NETWORK LINK"
NETWORK = "NETWORK"
STL_SVC_ELEMENT_TYPES = {
    "CUS-VOICE-HOSTED": [NETWORK, NETWORK_LINK],
    "COM-EPLAN": [NETWORK, NETWORK_LINK],
    "CAR-EPLAN": [NETWORK, NETWORK_LINK],
}
STL_PARENT_SVC_TYPES = {"COM-EPL, COM-EVPL"}


# engineering job
ENGINEERING_JOB_TYPES = {
    NEW_ORDER_TYPE: ["New"],
    CHANGE_ORDER_TYPE: [
        "Add",
        "Downgrade",
        "Express BW Upgrade",
        "Logical Change",
        "Upgrade",
        "Move",
        "Move - Hotcut/Relocation",
        "Move - New Build",
        "EE Conversion",
        "EVPN Conversion",
    ],
    FULL_DISCO_ORDER_TYPE: ["Full Disconnect", "Disconnect"],
    PARTIAL_DISCO_ORDER_TYPE: ["Partial Disconnect", "Disconnect"],
}


# translate order types received from request to generic standard
ORDER_TYPES = {
    NEW_ORDER_TYPE: ["NEW INSTALL", NEW_ORDER_TYPE],
    CHANGE_ORDER_TYPE: [
        "ADD",
        CHANGE_ORDER_TYPE,
        "CHANGE REQUEST",
        "CONVERSION NEW INSTALL",
        "MOVE",
        "PRICE CHANGE",
        "RENEWAL",
        "UPGRADE",
    ],
    PARTIAL_DISCO_ORDER_TYPE: [PARTIAL_DISCO_ORDER_TYPE],
    FULL_DISCO_ORDER_TYPE: [
        "DISCONNECT",
        FULL_DISCO_ORDER_TYPE,
        "DOUBLE FULL DISCONNECT",  # testing full disconnect with 2 ISP sites
    ],
}


REQUIRED_ORDER_DATA = {
    NEW_ORDER_TYPE: {
        FIA: {"product_name": "", "connector_type": "", "dia_svc_type": "", "uni_type": "", "ipv4": ""},
        "ELINE": {"product_name": "", "connector_type": "", "uni_type": ""},
        "VOICE": {"product_name": "", "connector_type": "", "uni_type": ""},
        "ELAN": {"product_name": "", "connector_type": "", "uni_type": ""},
        "CTBH": {"product_name": "", "connector_type": "", "uni_type": ""},
    },
    FULL_DISCO_ORDER_TYPE: {
        FIA: {"product_name": "", "site_order_data": ""},
        "ELINE": {"product_name": "", "site_order_data": ""},
    },
}


FIBER_INTERNET_ACCESS = "Fiber Internet Access"
CARRIER_FIA = "Carrier Fiber Internet Access"
EPL_FIBER = "EPL (Fiber)"
EVPL_FIBER = "EVPL (Fiber)"
CARRIER_EACCESS_FIBER = "Carrier E-Access (Fiber)"
CARRIER_TRANSPORT_EPL = "Carrier Transport EPL"
PRI_TRUNK_FIBER = "PRI Trunk (Fiber)"
PRI_TRUNK_FIBER_ANALOG = "PRI Trunk(Fiber) Analog"
SIP_TRUNK_FIBER = "SIP - Trunk (Fiber)"
SIP_TRUNK_FIBER_ANALOG = "SIP Trunk(Fiber) Analog"
HOSTED_VOICE_FIBER = "Hosted Voice - (Fiber)"
EPLAN_FIBER = "EP-LAN (Fiber)"
EVPLAN = "EVP-LAN"
WIA_PRIMARY = "Wireless Internet Access-Primary"
CTBH = "Carrier CTBH"


SALESFORCE_PRODUCT_NAMES = {
    (FIA, FIBER_INTERNET_ACCESS, CARRIER_FIA, "CAR-DIA", "COM-DIA"): FIA,
    (
        EPL_FIBER,
        "EPL (Type II)",
        EVPL_FIBER,
        "EVPL (Type II)",
        CARRIER_EACCESS_FIBER,
        "Carrier E-Access (Type II)",
        "COM-EPL",
        "COM-EVPL",
        "CAR-E-ACCESS FIBER/FIBER EPL",
        "CAR-E-ACCESS FIBER/FIBER EVPL",
    ): "ELINE",
    (
        PRI_TRUNK_FIBER,
        PRI_TRUNK_FIBER_ANALOG,
        "CUS-VOICE-PRI",
        SIP_TRUNK_FIBER,
        SIP_TRUNK_FIBER_ANALOG,
        "CUS-VOICE-SIP",
        HOSTED_VOICE_FIBER,
        "CUS-VOICE-HOSTED",
    ): "VOICE",
    ("Hosted Voice - Trunk (DOCSIS)", "Hosted Voice - (DOCSIS)", "SIP - Trunk (DOCSIS)", "PRI Trunk (DOCSIS)"): "DOCSIS",
    ("COM-EPLAN", "CAR-EPLAN", "EP-LAN (Fiber)", "EVP-LAN"): "ELAN",
    ("Carrier CTBH", "CTBH 4G", "CAR-CTBH 4G"): "CTBH",
}


FIA_PRODUCTS = (FIBER_INTERNET_ACCESS, CARRIER_FIA, "CAR-DIA", "COM-DIA", FIA, "Dedicated Internet Service")

FIBER_VOICE_DISCONNECT_PRODUCTS = (
    PRI_TRUNK_FIBER,
    PRI_TRUNK_FIBER_ANALOG,
    "CUS-VOICE-PRI",
    "SIP Trunk (Fiber)",
    SIP_TRUNK_FIBER,
    SIP_TRUNK_FIBER_ANALOG,
    "CUS-VOICE-SIP",
)


DOCSIS_VOICE_DISCONNECT_PRODUCTS = ("SIP - Trunk (DOCSIS)", "PRI Trunk (DOCSIS)", "COAX VOICE-PRI", "COAX VOICE-SIP")


VOICE_DISCONNECT_PRODUCTS = list(FIBER_VOICE_DISCONNECT_PRODUCTS + DOCSIS_VOICE_DISCONNECT_PRODUCTS)


DISCONNECT_IP_PRODUCTS = list(FIA_PRODUCTS + FIBER_VOICE_DISCONNECT_PRODUCTS)


ELIGIBILITY_ENDPOINT_BASE = "beorn/v1/eligibility"


SUPPORTED_PRODUCTS = [
    # FIA
    FIBER_INTERNET_ACCESS,
    CARRIER_FIA,
    "CAR-DIA",
    "COM-DIA",
    # ELINE
    "EPL (Fiber)",
    "EPL (Type II)",
    "EVPL (Fiber)",
    "EVPL (Type II)",
    CARRIER_EACCESS_FIBER,
    "Carrier E-Access (Type II)",
    "COM-EPL",
    "COM-EVPL",
    "CAR-E-ACCESS FIBER/FIBER EPL",
    "CAR-E-ACCESS FIBER/FIBER EVPL",
    # VOICE
    PRI_TRUNK_FIBER,
    PRI_TRUNK_FIBER_ANALOG,
    "CUS-VOICE-PRI",
    SIP_TRUNK_FIBER,
    SIP_TRUNK_FIBER_ANALOG,
    "CUS-VOICE-SIP",
    HOSTED_VOICE_FIBER,
    "CUS-VOICE-HOSTED",
    # RPHY
    "FC + Remote PHY",
    # CTBH
    "CTBH 4G",
    "Carrier CTBH",
]

SERVICE_TYPES = {
    FIA: SUPPORTED_PRODUCTS[:4],
    "ELINE": SUPPORTED_PRODUCTS[4:14],
    "VOICE-PRI": SUPPORTED_PRODUCTS[14:17],
    "VOICE-SIP": SUPPORTED_PRODUCTS[17:20],
    "VOICE-HOST": SUPPORTED_PRODUCTS[20:22],
    "VIDEO-FC P": SUPPORTED_PRODUCTS[22],
}

UNSUPPORTED_ACCEPTANCE_SERVICE_TYPES = {"COM-VIDEO OVER IP", "CUS-VIDEO-FC PLUS-RPHY", "COM-VIDEO SBB"}

DEVICE_STATUS_CHECK_SERVICES = ["ELINE"]
DEVICE_STATUS_CHECK_VENDORS = ["JUNIPER"]

STATE_ABBREVIATIONS = [
    "AI",
    "AK",
    "AL",
    "AR",
    "AZ",
    "CA",
    "CO",
    "CT",
    "DC",
    "DE",
    "FL",
    "GA",
    "HI",
    "IA",
    "ID",
    "IL",
    "IN",
    "KS",
    "KY",
    "LA",
    "MA",
    "MD",
    "ME",
    "MH",
    "MI",
    "MN",
    "MO",
    "MS",
    "MT",
    "NC",
    "ND",
    "NE",
    "NH",
    "NJ",
    "NM",
    "NV",
    "NY",
    "OH",
    "OK",
    "OR",
    "PA",
    "PR",
    "PW",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UM",
    "UT",
    "VA",
    "VI",
    "VT",
    "WA",
    "WI",
    "WV",
    "WY",
]

ISE_INELIGIBLE_VENDORS = ["JUNIPER"]
ISE_ELIGIBLE_DEVICES = ["MTU", "LOCAL"]


DISCO_FAILURES_WITH_PORT = ("service", "port")

ISE_STATES_EAST = ("CT", "FL", "IN", "KY", "ME", "MA", "MI", "NH", "NJ", "NY", "OH", "PA", "RI", "VT", "WV", "TN")
ISE_STATES_WEST = (
    "AZ",
    "CA",
    "CO",
    "HI",
    "ID",
    "IL",
    "IA",
    "KS",
    "KY",
    "MN",
    "MO",
    "MT",
    "NE",
    "NV",
    "ND",
    "OR",
    "SD",
    "UT",
    "WA",
    "WI",
    "WY",
)
ISE_STATES_SOUTH = ("AL", "GA", "LA", "MD", "MS", "NM", "NC", "OK", "SC", "TN", "TX", "VA", "WV")

ISE_STATE_LOCATIONS = {
    "Midwest": ["MI", "OH", "PA", "WV", "KY", "WI", "NE", "MO", "IL", "IA", "KS", "KY", "MN", "IN", "WV"],
    "Northeast": ["CT", "ME", "MA", "NH", "NJ", "NY", "RI", "VT", "DE"],
    "Pacwest": ["AZ", "CA", "CO", "HI", "ID", "MT", "NV", "ND", "OR", "SD", "UT", "WA", "WY"],
    "Southeast": ["TN", "AL", "FL", "GA", "NC", "SC", "TN", "LA", "MD", "MS", "VA"],
    "Southwest": ["NM", "OK", "TX"],
}

PASS_THROUGH = "passthrough"  # noqa: S105

PROCESSING_STATUSES = ("requested", "activating")

WIA_MODEL_TO_MEDIA_TYPE_MAP = {"E100": "LTE", "CBA850": "LTE", "CB850": "LTE", "W1850": "5G", "W1855": "5G"}

SEEFA_DL = "DL-SENOE-Automation-and-Orchestration-All@charter.com"


ELIGIBLE_SLM_SERVICES = ("EPLAN", "EPL", "EVPL", "E-ACCESS F", "CAR-CTBH 4G", "CTBH 4G")
