import logging

from pysnmp.hlapi import CommunityData, ContextData, ObjectIdentity, ObjectType, SnmpEngine, UdpTransportTarget, getCmd

from beorn_app import auth_config
from common_sense.common.errors import abort

logger = logging.getLogger(__name__)


def snmp_get(device_id: str, object_id: str, best_effort: bool = False, public: bool = False):
    logger.info(f"Device ID: '{device_id}' Object ID: '{object_id}'")
    snmp_str = auth_config.SNMP_PUBLIC_STRING if public else auth_config.SNMP_COMMUNITY_STRING
    if "." in object_id:
        iterator = getCmd(
            SnmpEngine(),
            CommunityData(snmp_str),
            UdpTransportTarget((device_id, 161)),
            ContextData(),
            ObjectType(ObjectIdentity(object_id)),
        )
    else:
        iterator = getCmd(
            SnmpEngine(),
            CommunityData(snmp_str),
            UdpTransportTarget((device_id, 161)),
            ContextData(),
            ObjectType(ObjectIdentity("SNMPv2-MIB", object_id, 0)),
        )
    try:
        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
    except Exception as error:
        if best_effort:
            logger.warning(f"Unexpected SNMP Error: {error}")
            return None
        abort(500, str(error))

    if errorIndication:  # SNMP engine errors
        if best_effort:
            logger.warning(f"SNMP Engine Error: {str(errorIndication)}")
            return None
        abort(406, str(errorIndication))
    elif errorStatus:  # SNMP agent errors
        error = f"{errorStatus.prettyPrint()} at {varBinds[int(errorIndex) - 1] if errorIndex else 'Unknown'}"
        logger.warning(f"SNMP Agent Error: {error}")
        if best_effort:
            return None
        abort(500, f"{errorStatus.prettyPrint()} at {varBinds[int(errorIndex) - 1] if errorIndex else 'Unknown'}")
    else:
        return str(varBinds[0][1])


def get_system_info(device_id: str):
    iterator = getCmd(
        SnmpEngine(),
        CommunityData(auth_config.SNMP_COMMUNITY_STRING),
        UdpTransportTarget((device_id, 161)),
        ContextData(),
        ObjectType(ObjectIdentity("SNMPv2-MIB", "sysName", 0)),
        ObjectType(ObjectIdentity("SNMPv2-MIB", "sysDescr", 0)),
        ObjectType(ObjectIdentity("SNMPv2-MIB", "sysUpTime", 0)),
        ObjectType(ObjectIdentity("SNMPv2-MIB", "sysLocation", 0)),
    )
    try:
        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
    except Exception as error:
        abort(500, str(error))

    if errorIndication:  # SNMP engine errors
        abort(406, str(errorIndication))
    elif errorStatus:  # SNMP agent errors
        abort(
            status_code=500,
            detail=f"{errorStatus.prettyPrint()} at {varBinds[int(errorIndex) - 1] if errorIndex else 'Unknown'}",
        )
    else:
        return (str(varBinds[0][1]), str(varBinds[1][1]), str(varBinds[2][1]), str(varBinds[3][1]))
