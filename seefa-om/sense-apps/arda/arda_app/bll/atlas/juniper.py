import re

# import atlas_app
from arda_app.common import auth_config
from common_sense.common.errors import abort
from jnpr.junos import Device
from lxml import etree
import xmltodict


def is_valid_interface(interface):
    regex = r"((?:ge|xe|et)\-\d{1,2}\/\d{1,2}\/\d{1,2})|ae\d+"
    return True if re.match(regex, interface) else False


def is_valid_ip_address(ip_address, cidr):
    ip_regex = r"((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"
    if 0 <= int(cidr) <= 32:
        if re.match(ip_regex, ip_address):
            return True
        else:
            return False
    else:
        return False


def create_connection(host):
    return Device(host=host, user=auth_config.TACACS_USER, password=auth_config.TACACS_PASS, gather_facts=False)


def check_optic(host, interface):
    # Separate interface into it's logical parts
    optic_size, int_raw = interface.split("-")
    fpc, pic, port = int_raw.split("/")

    # Get the Optic information from the network
    network_data = _show_chassis_pic(host, fpc, pic)
    ports = (
        network_data.get("fpc-information", {})
        .get("fpc", {})
        .get("pic-detail", {})
        .get("port-information", {})
        .get("port", {})
    )
    if not ports:
        return abort(500, "An error occurred while retrieving data from the network.")
    else:
        return [x for x in ports if x.get("port-number") == port]


def _show_chassis_pic(host, fpc, pic):
    try:
        conn = create_connection(host)
        conn.open()
    except Exception as err:
        abort(500, err)

    cnf = conn.rpc.get_pic_detail(fpc_slot=fpc, pic_slot=pic)
    cnf_xml = etree.tostring(cnf)
    conn.close()

    return xmltodict.parse(cnf_xml)


def show_chassis_hardware(host):
    try:
        conn = create_connection(host)
        conn.open()
    except Exception as err:
        abort(500, err)

    cnf = conn.rpc.get_chassis_inventory()
    cnf_xml = etree.tostring(cnf)
    conn.close()

    return xmltodict.parse(cnf_xml)


def show_interface_descriptions(host, interface=False):
    try:
        conn = create_connection(host)
        conn.open()
    except Exception as err:
        abort(500, err)

    cnf = conn.rpc.get_interface_information(descriptions=True, interface_name=interface)
    cnf_xml = etree.tostring(cnf)
    conn.close()

    return xmltodict.parse(cnf_xml)


def show_interface_details(host, interface):
    try:
        conn = create_connection(host)
        conn.open()
    except Exception as err:
        abort(500, err)

    cnf = conn.rpc.get_interface_information(interface_name=interface)
    cnf_xml = etree.tostring(cnf)
    conn.close()

    return xmltodict.parse(cnf_xml)


def show_interface_config(host, interface, timeout=30):
    try:
        conn = create_connection(host)
        conn.open()
    except Exception as err:
        abort(500, err)

    cnf = conn.rpc.get_config(
        filter_xml="<interfaces><interface><name>{}</name></interface></interfaces>".format(interface)
    )
    cnf_xml = etree.tostring(cnf)
    conn.close()

    return xmltodict.parse(cnf_xml)


def show_route(host, destination, cidr=None):
    destination = f"{destination}/{cidr}" if cidr else destination

    try:
        conn = create_connection(host)
        conn.open()
    except Exception as err:
        abort(500, err)

    cnf = conn.rpc.get_route_information(destination=destination)
    cnf_xml = etree.tostring(cnf)
    conn.close()

    return xmltodict.parse(cnf_xml)
