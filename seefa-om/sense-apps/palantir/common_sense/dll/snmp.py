import logging

from pysnmp.hlapi import CommunityData, ContextData, ObjectIdentity, ObjectType, SnmpEngine, UdpTransportTarget, getCmd

logger = logging.getLogger(__name__)


def snmp_get(snmp_str: str, ip_address: str, object_id: str):
    logger.info(f"SNMP Target Address: '{ip_address}' Object ID: '{object_id}'")
    object_type = ObjectIdentity(object_id)
    if "." in object_id:
        object_type = ObjectIdentity("SNMPv2-MIB", object_id, 0)
    iterator = getCmd(
        SnmpEngine(),
        CommunityData(snmp_str),  # TODO: Is this a token?
        UdpTransportTarget((ip_address, 161)),
        ContextData(),
        ObjectType(object_type),
    )
    try:
        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
    except Exception as error:
        logger.warning(f"Unexpected SNMP Error: {error}")
        return None
    if errorIndication:  # SNMP engine errors
        logger.warning(f"SNMP Engine Error: {str(errorIndication)}")
        return None
    elif errorStatus:  # SNMP agent errors
        error = f"{errorStatus.prettyPrint()} at {varBinds[int(errorIndex) - 1] if errorIndex else 'Unknown'}"
        logger.warning(f"SNMP Agent Error: {error}")
        return None
    else:
        return str(varBinds[0][1])


def snmp_get_wrapper(snmp_str_list: list, ip_address: str, object_id: str):
    for index, snmp_str in enumerate(snmp_str_list):
        try:
            response = snmp_get(snmp_str, ip_address, object_id)
            if response:
                return response
        except Exception as e:
            logger.warning(f"Failed snmp get with token index '{index}' '{ip_address}' '{object_id}' - {e}")
    return False


def get_system_info(snmp_str: str, ip_address: str):
    iterator = getCmd(
        SnmpEngine(),
        CommunityData(snmp_str),
        UdpTransportTarget((ip_address, 161)),
        ContextData(),
        ObjectType(ObjectIdentity("SNMPv2-MIB", "sysName", 0)),
        ObjectType(ObjectIdentity("SNMPv2-MIB", "sysDescr", 0)),
        ObjectType(ObjectIdentity("SNMPv2-MIB", "sysUpTime", 0)),
        ObjectType(ObjectIdentity("SNMPv2-MIB", "sysLocation", 0)),
    )
    try:
        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
    except Exception as error:
        logger.warning(f"Unexpected SNMP Error: {error}")
        return None
    if errorIndication:  # SNMP engine errors
        logger.warning(f"SNMP Engine Error: {str(errorIndication)}")
        return None
    elif errorStatus:  # SNMP agent errors
        error = f"{errorStatus.prettyPrint()} at {varBinds[int(errorIndex) - 1] if errorIndex else 'Unknown'}"
        logger.warning(f"SNMP Agent Error: {error}")
        return None
    else:
        return (
            str(varBinds[0][1]),
            str(varBinds[1][1]),
            str(varBinds[2][1]),
            str(varBinds[3][1]),
        )
