import logging

from common_sense.common.errors import abort

logger = logging.getLogger(__name__)


def get_bh_path(area):
    return f"/Commercial/LBHN/{area}/Customer"


Birmingham = get_bh_path("Birmingham")
Bakersfield = get_bh_path("Bakersfield")
CentralFL = get_bh_path("CentralFL")
Detroit = get_bh_path("Detroit")
Indianapolis = get_bh_path("Indianapolis")
TampaBay = get_bh_path("TampaBay")

# outlier containers
# Cantonment = get_bh_path('Cantonment')
# Defuniak = get_bh_path('Defuniak')
# Elmore = get_bh_path('Elmore')
# Eufaula = get_bh_path('Eufaula')
# Greenville = get_bh_path('Greenville')

bh_map = {
    "AL": {
        "BRHN": Birmingham,
        "BRHO": Birmingham,
        "BRHP": Birmingham,
        "BSMR": Birmingham,
        "CLIO": Birmingham,
        "EUFL": Birmingham,
        "GENV": Birmingham,
        "GNVL": Birmingham,
        "MLBK": Birmingham,
        "SLCM": Birmingham,
        "TLLS": Birmingham,
        "WTMP": Birmingham,
    },
    "CA": {
        "BKFD": Bakersfield,
        "BKFE": Bakersfield,
        "BKFI": Bakersfield,
        "DELN": Bakersfield,
        "LAMT": Bakersfield,
        "TAFT": Bakersfield,
        "THCH": Bakersfield,
        "WASC": Bakersfield,
    },
    "FL": {
        "BLTW": Birmingham,
        "CHTH": Birmingham,
        "CNTM": Birmingham,
        "CNTR": Birmingham,
        "DFSP": Birmingham,
        "GCVL": Birmingham,
        "HRFR": Birmingham,
        "ALSP": CentralFL,
        "APPK": CentralFL,
        "BLVW": CentralFL,
        "CLMT": CentralFL,
        "COCO": CentralFL,
        "CPCN": CentralFL,
        "DELD": CentralFL,
        "DLND": CentralFL,
        "DLTN": CentralFL,
        "DYBH": CentralFL,
        "EDWR": CentralFL,
        "KSSN": CentralFL,
        "MLBH": CentralFL,
        "MLBR": CentralFL,
        "MLBS": CentralFL,
        "MRIS": CentralFL,
        "NSBH": CentralFL,
        "OCAM": CentralFL,
        "OCOE": CentralFL,
        "ORBH": CentralFL,
        "ORLE": CentralFL,
        "ORLH": CentralFL,
        "ORLJ": CentralFL,
        "ORLN": CentralFL,
        "ORLR": CentralFL,
        "OVID": CentralFL,
        "PLBY": CentralFL,
        "PLCS": CentralFL,
        "PTOR": CentralFL,
        "SNFR": CentralFL,
        "STBH": CentralFL,
        "STCD": CentralFL,
        "TTVL": CentralFL,
        "WLWD": CentralFL,
        "WNGR": CentralFL,
        "WNPK": CentralFL,
        "WNSP": CentralFL,
        "ABDL": TampaBay,
        "BKVL": TampaBay,
        "BRND": TampaBay,
        "BRTN": TampaBay,
        "BRTO": TampaBay,
        "CLWS": TampaBay,
        "CLWT": TampaBay,
        "CTSG": TampaBay,
        "DNDN": TampaBay,
        "DOVR": TampaBay,
        "DVPT": TampaBay,
        "ELFS": TampaBay,
        "ELTN": TampaBay,
        "HDSN": TampaBay,
        "HNCY": TampaBay,
        "INVR": TampaBay,
        "LCNT": TampaBay,
        "LKLE": TampaBay,
        "LKLF": TampaBay,
        "LRGO": TampaBay,
        "LUTZ": TampaBay,
        "NPRC": TampaBay,
        "PLHR": TampaBay,
        "PRSH": TampaBay,
        "PTCY": TampaBay,
        "RSKN": TampaBay,
        "SEML": TampaBay,
        "SFHR": TampaBay,
        "SHHC": TampaBay,
        "SNAN": TampaBay,
        "SPBG": TampaBay,
        "SPBK": TampaBay,
        "SRSV": TampaBay,
        "TAMP": TampaBay,
        "TAMQ": TampaBay,
        "TAMR": TampaBay,
        "TAMV": TampaBay,
        "TAMW": TampaBay,
        "TRSP": TampaBay,
        "TWCN": TampaBay,
        "WIMM": TampaBay,
        "WKWC": TampaBay,
        "WLCH": TampaBay,
        "WNHN": TampaBay,
    },
    "SC": {
        # "Greenville": Greenville  # NO INFO
    },
    "IN": {
        "AVON": Indianapolis,
        "CRMM": Indianapolis,
        "FTVL": Indianapolis,
        "IPLB": Indianapolis,
        "IPLT": Indianapolis,
        "IPLZ": Indianapolis,
        "MARN": Indianapolis,
        "ZIVL": Indianapolis,
    },
    "MI": {"FMHL": Detroit, "LIVN": Detroit, "SFLD": Detroit},
}


def get_path_from_hubname(hub):
    try:
        hub = hub.split(" ")[1][:4]
        hub_map = {
            "BHAM": Birmingham,
            "BKFD": Bakersfield,
            "DETR": Detroit,
            "INDP": Indianapolis,
            "ORLD": CentralFL,
            "TAMP": TampaBay,
        }
        ipc_path = hub_map.get(hub)
    except Exception as e:
        logger.info(f"BH get hub error: {e}")
        return None
    return ipc_path


def map_ipc_container_for_bh(z_clli, mx, hub=None):
    # get state from mx variable
    state = mx[4:6]

    # get area codes from z_clli and mx variables
    area_from_z = z_clli[:4]
    area_from_mx = mx[:4]

    # find State in data
    ipc_path = bh_map.get(state)
    if ipc_path:
        # find path in data by area_from_z or area_from_mx
        ipc_path = ipc_path.get(area_from_z) or ipc_path.get(area_from_mx)

    if ipc_path is None and hub:
        # find path from hub name
        ipc_path = get_path_from_hubname(hub)

    if ipc_path is None:
        abort(500, "Area does not have an associated mapping folder for ipc that is currently supported")
    return ipc_path
