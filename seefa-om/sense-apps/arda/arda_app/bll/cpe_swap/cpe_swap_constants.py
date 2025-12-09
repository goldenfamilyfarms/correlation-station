SUPPORTED_VENDORS = ["ADVA", "RAD", "CRADLEPOINT"]

SUPPORTED_MODELS = {
    "FSP 150-GE114PRO-C": ["1 Gbps", "ADVA"],
    "FSP 150-XG116PRO": ["10 Gbps", "ADVA"],
    "FSP 150-XG116PROH": ["10 Gbps", "ADVA"],
    "FSP 150-XG120PRO": ["10 Gbps", "ADVA"],
    "FSP 150-XG108": ["10 Gbps", "ADVA"],
    "ETX203AX/2SFP/2UTP2SFP": ["1 Gbps", "RAD"],
    "ETX-220A": ["10 Gbps", "RAD"],
    "ETX-2I-10G-B/8.5/8SFPP": ["10 Gbps", "RAD"],
    "ETX-2I-10G-B/19/8SFPP": ["10 Gbps", "RAD"],
    "ETX-2I-10G/4SFPP/4SFP4UTP": ["10 Gbps", "RAD"],
    "ETX-2I-10G/4SFPP/24SFP": ["10 Gbps", "RAD"],
    "ARC CBA850": ["10/100/1000 BASET", "CRADLEPOINT"],
    "E100 C4D/C7C": ["10/100/1000 BASET", "CRADLEPOINT"],
}

RAD_TO_10G_ADVA_HANDOFF_PAID_MATRIX = {
    "LC": [
        {"ADVA": "ETH_PORT-1-1-1-3", "RAD": "0/1"},
        {"ADVA": "ETH_PORT-1-1-1-4", "RAD": "0/2"},
        {"ADVA": "ETH_PORT-1-1-1-5", "RAD": "0/3"},
        {"ADVA": "ETH_PORT-1-1-1-6", "RAD": "0/4"},
    ],
    "RJ-45": [
        {"ADVA": "ETH_PORT-1-1-1-1", "RAD": "0/1"},
        {"ADVA": "ETH_PORT-1-1-1-2", "RAD": "0/2"},
        {"ADVA": "ETH_PORT-1-1-1-3", "RAD": "0/3"},
        {"ADVA": "ETH_PORT-1-1-1-4", "RAD": "0/4"},
    ],
}

RAD_TO_1G_ADVA_HANDOFF_PAID_MATRIX = {
    "LC": [{"ADVA": "ACCESS-1-1-1-3", "RAD": "ETH PORT 5"}, {"ADVA": "ACCESS-1-1-1-4", "RAD": "ETH PORT 6"}],
    "RJ-45": [
        {"ADVA": "ACCESS-1-1-1-3", "RAD": "ETH PORT 3"},
        {"ADVA": "ACCESS-1-1-1-4", "RAD": "ETH PORT 4"},
        {"ADVA": "ACCESS-1-1-1-5", "RAD": "ETH PORT 5"},
        {"ADVA": "ACCESS-1-1-1-6", "RAD": "ETH PORT 6"},
    ],
}
