from common_sense.common.errors import abort
from arda_app.dll.expo import get_order_processing, put_order_processing

STAGES = [
    "CID",
    "ISP",
    "Design",
    "ESP",
    "MS-CD",
    "NA",
    "MS-NA",
    "NC",
    "MS-NC",
    "SOVA",
    "BMS",
    "ARDA",
    "BEORN",
    "PALANTIR",
]

SUBSTAGES = {
    "Design": [
        "All",
        "Quick Connect",
        "Serviceable",
        "New with CJ",
        "Bandwidth Change",
        "Logical Change",
        "Disconnect",
        "Add",
    ],
    "MS-CD": ["All", "New Install"],
    "NA": ["All", "Enterprise", "Disconnect"],
    "MS-NA": ["All", "New Install", "MNE"],
    "NC": ["All", "Enterprise", "Disconnect", "Wireless Internet Access"],
    "MS-NC": ["All", "New Install", "MNE"],
}

ARDA = ["CID", "ISP", "Design", "BMS"]

BEORN = PALANTIR = ["ESP", "MS-CD", "NA", "MS-NA", "NC", "MS-NC"]


def get_expo_order_processing_main(user_stages):
    expo_resp = get_order_processing()
    if user_stages.lower() == "all":
        return expo_resp
    user_resp = {}
    if user_stages in ["ARDA", "BEORN", "PALANTIR"]:
        if user_stages == "ARDA":
            for stage in ARDA:
                for expo_stage in expo_resp:
                    if stage == expo_stage.get("stage"):
                        user_resp[stage] = expo_stage
        else:
            for stage in BEORN:
                for expo_stage in expo_resp:
                    if stage == expo_stage.get("stage"):
                        user_resp[stage] = expo_stage
    for stage in user_stages.split(","):
        stage = stage.strip()
        if stage in STAGES:
            for expo_stage in expo_resp:
                if stage == expo_stage.get("stage"):
                    user_resp[stage] = expo_stage
    return user_resp


def put_expo_order_processing_main(body):
    """Pause EXPO queues or triggers, or set order processing interval or delay

    ex_expo_all_payload = {
        "updated_by": "P8675309",
        "configData": [
            {
                "stage": "all",
                "orderProcessing": {
                    "interval": 60,
                    "delay": 0,
                    "status": "OFF",
                },
                "trigger": {
                    "status": "ON",
                },
            }
        ],
    }

    ex_expo_substage_payload = {
        "updated_by": "P8675309",
        "configData": [
            {
                "stage": "Design",
                "orderProcessing": {"interval": 60},
                "substages": {
                    {
                        "substage": "All",
                        "orderProcessing": {
                            "interval": 60,
                            "delay": 0,
                            "status": "OFF",
                        },
                        "trigger": {
                            "status": "ON",
                        },
                    }
                },
            }
        ],
    }
    """
    payload = {"updated_by": body["pid"], "configData": []}

    stage = body["stage"]
    substage = body.get("substage")

    if stage.lower() == "all":
        configData = build_configData(body)
        configData["stage"] = "all"
        payload["configData"].append(configData)
    elif stage in ["ARDA", "BEORN", "PALANTIR"]:
        if stage == "ARDA":
            for workstream in ARDA:
                body["stage"] = workstream
                configData = build_configData(body)
                configData["stage"] = workstream
                payload["configData"].append(configData)
        if stage in ["BEORN", "PALANTIR"]:
            for workstream in BEORN:
                body["stage"] = workstream
                configData = build_configData(body)
                configData["stage"] = workstream
                payload["configData"].append(configData)
    else:
        validate_stages(stage, substage)
        configData = build_configData(body)
        configData["stage"] = stage
        payload["configData"].append(configData)

    resp = put_order_processing(payload)
    return resp


def validate_stages(stage, substage=""):
    if stage not in STAGES:
        abort(500, f"Invalid stage: {stage}")
    if substage:
        if stage not in SUBSTAGES.keys():
            abort(500, f"Stage {stage} does not have a substage")
        if substage not in SUBSTAGES[stage]:
            abort(500, f"Stage {stage} does not have substage {substage}")


def build_configData(body):
    if body["stage"] in SUBSTAGES.keys() and not body.get("substage"):
        substage = "All"
    else:
        substage = body.get("substage")

    queue_status = body.get("queue_status")
    trigger_status = body.get("trigger_status")
    interval = body.get("interval_seconds")
    delay = body.get("delay_minutes")

    configData = {"stage": ""}

    if substage:
        configData["substages"] = {"substage": substage}
        if queue_status or interval or delay:
            configData["substages"]["orderProcessing"] = {}
            if queue_status:
                configData["substages"]["orderProcessing"]["status"] = queue_status
            if interval:
                configData["substages"]["orderProcessing"]["interval"] = interval
            if delay:
                configData["substages"]["orderProcessing"]["delay"] = delay
    elif queue_status or interval or delay:
        configData["orderProcessing"] = {}
        if queue_status:
            configData["orderProcessing"]["status"] = queue_status
        if interval:
            configData["orderProcessing"]["interval"] = interval
        if delay:
            configData["orderProcessing"]["delay"] = delay

    if substage and trigger_status:
        configData["substages"]["trigger"] = {"status": trigger_status}
    elif trigger_status:
        configData["trigger"] = {"status": trigger_status}

    return configData
