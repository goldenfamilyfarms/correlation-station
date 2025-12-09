from common_sense.common.errors import abort
from pysnmp.hlapi import SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity, getCmd
from arda_app.common import auth_config

# host = "71.42.150.67"


def snmp_get(host, obj_identifier):
    if ".1.3." in obj_identifier:
        iterator = getCmd(
            SnmpEngine(),
            CommunityData(auth_config.SNMP_COMMUNITY_STRING),
            UdpTransportTarget((host, 161)),
            ContextData(),
            ObjectType(ObjectIdentity(obj_identifier)),
        )
    else:
        iterator = getCmd(
            SnmpEngine(),
            CommunityData(auth_config.SNMP_COMMUNITY_STRING),
            UdpTransportTarget((host, 161)),
            ContextData(),
            ObjectType(ObjectIdentity("SNMPv2-MIB", obj_identifier, 0)),
        )

    try:
        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
    except Exception as err:
        abort(500, err)

    if errorIndication:  # SNMP engine errors
        abort(500, errorIndication)
    elif errorStatus:  # SNMP agent errors
        abort(500, "%s at %s" % (errorStatus.prettyPrint(), varBinds[int(errorIndex) - 1] if errorIndex else "?"))
    else:
        varBind = varBinds[0]
        return [x.prettyPrint() for x in varBind][1]
