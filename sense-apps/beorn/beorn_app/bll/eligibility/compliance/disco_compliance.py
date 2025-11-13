from beorn_app.bll.eligibility.mdso_eligible import (
    JUNIPER_ACX_MODELS,
    JUNIPER_EX_MODELS,
    JUNIPER_MX_MODELS,
    JUNIPER_QFX_MODELS,
    RAD_220_MODELS,
    RAD_203_MODELS,
    RAD_2I_MODELS,
    ADVA_114_MODELS,
    ADVA_116_MODELS,
    ADVA_116H_MODELS,
    ADVA_118_MODELS,
    ADVA_120_MODELS,
    ADVA_108_MODELS,
    CISCO_9K_MODELS,
    CISCO_920_MODELS,
    CISCO_ME3400_MODELS,
)


class ELINE:
    VENDORS = ["JUNIPER", "RAD", "ADVA", "CISCO"]

    MODELS = [
        JUNIPER_MX_MODELS,
        JUNIPER_QFX_MODELS,
        JUNIPER_ACX_MODELS,
        JUNIPER_EX_MODELS,
        RAD_220_MODELS,
        RAD_203_MODELS,
        RAD_2I_MODELS,
        ADVA_114_MODELS,
        ADVA_116_MODELS,
        ADVA_116H_MODELS,
        ADVA_118_MODELS,
        ADVA_120_MODELS,
        ADVA_108_MODELS,
        CISCO_9K_MODELS,
        CISCO_920_MODELS,
        CISCO_ME3400_MODELS,
    ]

    PORT_ROLES = {
        "MX": ["INNI", "ENNI"],
        "QFX": ["INNI"],
        "ACX": ["INNI"],
        "EX": ["INNI", "UNI"],
        "220": ["UNI", "ENNI", "INNI"],
        "203": ["UNI", "INNI"],
        "2I": ["ENNI", "INNI", "UNI"],
        "114": ["UNI", "INNI"],
        "116": ["INNI", "ENNI", "UNI"],
        "116H": ["INNI", "ENNI", "UNI"],
        "118": ["INNI", "ENNI", "UNI"],
        "120": ["INNI", "ENNI", "UNI"],
        "108": ["INNI", "ENNI", "UNI"],
        "9K": ["ENNI"],
        "920": ["INNI", "UNI", "ENNI"],
        "ME3400": ["UNI", "INNI"],
    }


class FIA:
    VENDORS = ["JUNIPER", "RAD", "ADVA", "CISCO"]

    MODELS = [
        JUNIPER_MX_MODELS,
        JUNIPER_QFX_MODELS,
        JUNIPER_ACX_MODELS,
        JUNIPER_EX_MODELS,
        RAD_220_MODELS,
        RAD_203_MODELS,
        RAD_2I_MODELS,
        ADVA_114_MODELS,
        ADVA_116_MODELS,
        ADVA_116H_MODELS,
        ADVA_118_MODELS,
        ADVA_120_MODELS,
        ADVA_108_MODELS,
        CISCO_9K_MODELS,
        CISCO_920_MODELS,
        CISCO_ME3400_MODELS,
    ]

    PORT_ROLES = {
        "MX": ["INNI", "ENNI", "UNI"],
        "QFX": ["INNI"],
        "ACX": ["INNI"],
        "EX": ["INNI", "UNI"],
        "220": ["UNI", "ENNI", "INNI"],
        "203": ["UNI", "INNI"],
        "2I": ["ENNI", "INNI", "UNI"],
        "114": ["UNI", "INNI"],
        "116": ["INNI", "ENNI", "UNI"],
        "116H": ["INNI", "ENNI", "UNI"],
        "118": ["INNI", "ENNI", "UNI"],
        "120": ["INNI", "ENNI", "UNI"],
        "108": ["INNI", "ENNI", "UNI"],
        "9K": ["INNI", "UNI", "ENNI"],
        "920": ["INNI", "UNI", "ENNI"],
        "ME340": ["UNI", "INNI"],
    }


class VOICE:
    VENDORS = ["JUNIPER", "RAD", "ADVA", "CISCO"]

    MODELS = [
        JUNIPER_MX_MODELS,
        JUNIPER_QFX_MODELS,
        JUNIPER_ACX_MODELS,
        JUNIPER_EX_MODELS,
        RAD_220_MODELS,
        RAD_203_MODELS,
        RAD_2I_MODELS,
        ADVA_114_MODELS,
        ADVA_116_MODELS,
        ADVA_116H_MODELS,
        ADVA_118_MODELS,
        ADVA_120_MODELS,
        ADVA_108_MODELS,
        CISCO_9K_MODELS,
        CISCO_920_MODELS,
        CISCO_ME3400_MODELS,
    ]

    PORT_ROLES = {
        "MX": ["INNI", "ENNI", "UNI"],
        "QFX": ["INNI"],
        "ACX": ["INNI"],
        "EX": ["INNI", "UNI"],
        "220": ["UNI", "ENNI", "INNI"],
        "203": ["UNI", "INNI"],
        "2I": ["ENNI", "INNI", "UNI"],
        "114": ["UNI", "INNI"],
        "116": ["INNI", "ENNI", "UNI"],
        "116H": ["INNI", "ENNI", "UNI"],
        "118": ["INNI", "ENNI", "UNI"],
        "120": ["INNI", "ENNI", "UNI"],
        "108": ["INNI", "ENNI", "UNI"],
        "9K": ["INNI", "UNI", "ENNI"],
        "920": ["INNI", "UNI", "ENNI"],
        "ME3400": ["UNI", "INNI"],
    }


class ELAN:
    VENDORS = ["JUNIPER", "RAD", "ADVA", "CISCO"]

    MODELS = [
        JUNIPER_MX_MODELS,
        JUNIPER_QFX_MODELS,
        JUNIPER_ACX_MODELS,
        JUNIPER_EX_MODELS,
        RAD_220_MODELS,
        RAD_203_MODELS,
        RAD_2I_MODELS,
        ADVA_114_MODELS,
        ADVA_116_MODELS,
        ADVA_116H_MODELS,
        ADVA_118_MODELS,
        ADVA_120_MODELS,
        ADVA_108_MODELS,
        CISCO_9K_MODELS,
        CISCO_920_MODELS,
        CISCO_ME3400_MODELS,
    ]

    PORT_ROLES = {
        "MX": ["INNI", "ENNI"],
        "QFX": ["INNI"],
        "ACX": ["INNI"],
        "EX": ["INNI", "UNI"],
        "220": ["UNI", "INNI", "ENNI"],
        "203": ["UNI", "INNI"],
        "2I": ["ENNI", "INNI", "UNI"],
        "114": ["UNI", "INNI"],
        "116": ["INNI", "ENNI", "UNI"],
        "116H": ["INNI", "ENNI", "UNI"],
        "118": ["INNI", "ENNI", "UNI"],
        "120": ["INNI", "ENNI", "UNI"],
        "108": ["INNI", "ENNI", "UNI"],
        "9K": ["INNI", "ENNI"],
        "920": ["INNI", "UNI", "ENNI"],
        "ME3400": ["UNI", "INNI"],
    }
