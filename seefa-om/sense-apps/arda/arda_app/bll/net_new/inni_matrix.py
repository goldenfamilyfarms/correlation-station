import logging
from common_sense.common.errors import abort

logger = logging.getLogger(__name__)


def find_inni(a_state, z_state, a_network, z_network):
    supported_stated = [
        "AL",
        "CA",
        "CT",
        "FL",
        "GA",
        "HI",
        "IL",
        "IN",
        "KS",
        "KY",
        "LA",
        "MA",
        "ME",
        "MI",
        "MN",
        "MO",
        "NC",
        "NE",
        "NH",
        "NV",
        "NY",
        "NYC",
        "OH",
        "OR",
        "SC",
        "TN",
        "TX",
        "VA",
        "WA",
        "WI",
    ]

    if a_state not in supported_stated or z_state not in supported_stated:
        abort(500, f"Unsupported state given for INNI determination: {a_state, z_state}")

    charter_twc = {
        "NY/CT/MA": [
            {"NY/ME/NH/MA": "51.KGFD.000023..TWCC"},
            {"NYC": "51.KGFD.000023..TWCC"},
            {"OH/WI/KY": "70.KGFD.000088..TWCC"},
            {"NC/SC": "70.KGFD.000124..CHTR"},
            {"TX/KS/MO/NE": "21.KGFD.000103..TWCC"},
            {"CA/HI": "90.KGFD.000009..TWCC"},
        ],
        "NC/SC/VA": [
            {"NY/ME/NH/MA": "70.KGFD.000088..TWCC"},
            {"NYC": "70.KGFD.000088..TWCC"},
            {"OH/WI/KY": "40.KGFD.000152..CHTR"},
            {"NC/SC": "70.KGFD.000124..CHTR"},
            {"TX/KS/MO/NE": "21.KGFD.000103..TWCC"},
            {"CA/HI": "21.KGFD.000134..TWCC"},
        ],
        "TN/LA": [
            {"NY/ME/NH/MA": "40.KGFD.000152..CHTR"},
            {"NYC": "40.KGFD.000152..CHTR"},
            {"OH/WI/KY": "40.KGFD.000152..CHTR"},
            {"NC/SC": "40.KGFD.000152..CHTR"},
            {"TX/KS/MO/NE": "21.KGFD.000103..TWCC"},
            {"CA/HI": "90.KGFD.000009..TWCC"},
        ],
        "GA/AL": [
            {"NY/ME/NH/MA": "40.KGFD.000152..CHTR"},
            {"NYC": "40.KGFD.000152..CHTR"},
            {"OH/WI/KY": "40.KGFD.000152..CHTR"},
            {"NC/SC": "40.KGFD.000152..CHTR"},
            {"TX/KS/MO/NE": "40.KGFD.000152..CHTR"},
            {"CA/HI": "21.KGFD.000134..TWCC"},
        ],
        "TX": [
            {"NY/ME/NH/MA": "21.KGFD.000103..TWCC"},
            {"NYC": "21.KGFD.000103..TWCC"},
            {"OH/WI/KY": "21.KGFD.000103..TWCC"},
            {"NC/SC": "21.KGFD.000103..TWCC"},
            {"TX/KS/MO/NE": "21.KGFD.000103..TWCC"},
            {"CA/HI": "21.KGFD.000103..TWCC"},
        ],
        "MO/IL": [
            {"NY/ME/NH/MA": "31.KGFD.000052..TWCC"},
            {"NYC": "31.KGFD.000052..TWCC"},
            {"OH/WI/KY": "31.KGFD.000052..TWCC"},
            {"NC/SC": "40.KGFD.000152..CHTR"},
            {"TX/KS/MO/NE": "21.KGFD.000103..TWCC"},
            {"CA/HI": "90.KGFD.000009..TWCC"},
        ],
        "WI": [
            {"NY/ME/NH/MA": "26030.GE10L.BRFDWIFB4CW.BRFDWIFB3CW"},
            {"NYC": "26030.GE10L.BRFDWIFB4CW.BRFDWIFB3CW"},
            {"OH/WI/KY": "26030.GE10L.BRFDWIFB4CW.BRFDWIFB3CW"},
            {"NC/SC": "26030.GE10L.BRFDWIFB4CW.BRFDWIFB3CW"},
            {"TX/KS/MO/NE": "26030.GE10L.BRFDWIFB4CW.BRFDWIFB3CW"},
            {"CA/HI": "26030.GE10L.BRFDWIFB4CW.BRFDWIFB3CW"},
        ],
        "MI": [
            {"NY/ME/NH/MA": "31.KGFD.000052..TWCC"},
            {"NYC": "31.KGFD.000052..TWCC"},
            {"OH/WI/KY": "31.KGFD.000052..TWCC"},
            {"NC/SC": "31.KGFD.000052..TWCC"},
            {"TX/KS/MO/NE": "21.KGFD.000103..TWCC"},
            {"CA/HI": "90.KGFD.000009..TWCC"},
        ],
        "MN/NE": [
            {"NY/ME/NH/MA": "31.KGFD.000052..TWCC"},
            {"NYC": "31.KGFD.000052..TWCC"},
            {"OH/WI/KY": "31.KGFD.000052..TWCC"},
            {"NC/SC": "31.KGFD.000052..TWCC"},
            {"TX/KS/MO/NE": "21.KGFD.000103..TWCC"},
            {"CA/HI": "90.KGFD.000009..TWCC"},
        ],
        "CA": [
            {"NY/ME/NH/MA": "21.KGFD.000134..TWCC"},
            {"NYC": "90.KGFD.000009..TWCC"},
            {"OH/WI/KY": "21.KGFD.000134..TWCC"},
            {"NC/SC": "40.KGFD.000152..CHTR"},
            {"TX/KS/MO/NE": "21.KGFD.000103..TWCC"},
            {"CA/HI": "90.KGFD.000009..TWCC"},
        ],
        "OR/WA/NV": [
            {"NY/ME/NH/MA": "90.KGFD.000009..TWCC"},
            {"NYC": "21.KGFD.000134..TWCC"},
            {"OH/WI/KY": "90.KGFD.000009..TWCC"},
            {"NC/SC": "40.KGFD.000152..CHTR"},
            {"TX/KS/MO/NE": "21.KGFD.000103..TWCC"},
            {"CA/HI": "21.KGFD.000134..TWCC"},
        ],
    }

    charter_bhn = {
        "NY/CT/MA": [
            {"FL": "TYPE II"},
            {"AL": "20.KGFD.000015..TWCC"},
            {"IN": "31.KGFD.000052..TWCC"},
            {"MI": "24.KGFD.000001..TWCC"},
            {"CA": "TYPE II"},
        ],
        "NC/SC/VA": [
            {"FL": "TYPE II"},
            {"AL": "20.KGFD.000015..TWCC"},
            {"IN": "31.KGFD.000052..TWCC"},
            {"MI": "24.KGFD.000001..TWCC"},
            {"CA": "TYPE II"},
        ],
        "TN/LA": [
            {"FL": "TYPE II"},
            {"AL": "20.KGFD.000015..TWCC"},
            {"IN": "31.KGFD.000052..TWCC"},
            {"MI": "24.KGFD.000001..TWCC"},
            {"CA": "TYPE II"},
        ],
        "GA/AL": [
            {"FL": "TYPE II"},
            {"AL": "20.KGFD.000015..TWCC"},
            {"IN": "31.KGFD.000052..TWCC"},
            {"MI": "24.KGFD.000001..TWCC"},
            {"CA": "TYPE II"},
        ],
        "TX": [
            {"FL": "TYPE II"},
            {"AL": "20.KGFD.000015..TWCC"},
            {"IN": "31.KGFD.000052..TWCC"},
            {"MI": "24.KGFD.000001..TWCC"},
            {"CA": "TYPE II"},
        ],
        "MO/IL": [
            {"FL": "TYPE II"},
            {"AL": "20.KGFD.000015..TWCC"},
            {"IN": "31.KGFD.000052..TWCC"},
            {"MI": "24.KGFD.000001..TWCC"},
            {"CA": "TYPE II"},
        ],
        "WI": [
            {"FL": "TYPE II"},
            {"AL": "20.KGFD.000015..TWCC"},
            {"IN": "31.KGFD.000052..TWCC"},
            {"MI": "24.KGFD.000001..TWCC"},
            {"CA": "TYPE II"},
        ],
        "MI": [
            {"FL": "TYPE II"},
            {"AL": "20.KGFD.000015..TWCC"},
            {"IN": "24.KGFD.000001..TWCC"},
            {"MI": "24.KGFD.000001..TWCC"},
            {"CA": "TYPE II"},
        ],
        "MN/NE": [
            {"FL": "TYPE II"},
            {"AL": "20.KGFD.000015..TWCC"},
            {"IN": "31.KGFD.000052..TWCC"},
            {"MI": "24.KGFD.000001..TWCC"},
            {"CA": "TYPE II"},
        ],
        "CA": [
            {"FL": "TYPE II"},
            {"AL": "20.KGFD.000015..TWCC"},
            {"IN": "31.KGFD.000052..TWCC"},
            {"MI": "24.KGFD.000001..TWCC"},
            {"CA": "TYPE II"},
        ],
        "OR/WA/NV": [
            {"FL": "TYPE II"},
            {"AL": "20.KGFD.000015..TWCC"},
            {"IN": "31.KGFD.000052..TWCC"},
            {"MI": "24.KGFD.000001..TWCC"},
            {"CA": "TYPE II"},
        ],
    }

    networks = None
    if (a_network, z_network) in [("L-CHTR", "L-TWC"), ("L-TWC", "L-CHTR")]:
        networks = charter_twc
        if a_network == "L-TWC":
            a_state, z_state = z_state, a_state
    elif (a_network, z_network) in [("L-CHTR", "L-BHN"), ("L-BHN", "L-CHTR")]:
        networks = charter_bhn
        if a_network == "L-BHN":
            a_state, z_state = z_state, a_state
    else:
        abort(500, f"Unsupported network combo given for INNI determination: {a_network, z_network}")

    for key in networks:
        if a_state in key.split("/"):
            for region in networks[key]:
                for key in region:
                    if z_state in key.split("/"):
                        if region[key] == "TYPE II":
                            abort(500, "TYPE II determined by INNI matrix")
                        return region[key]
    return None
