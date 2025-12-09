from arda_app.common import auth_config
from ncclient import manager
import xmltodict


def create_connection(host):
    return manager.connect(
        host=host,
        port="830",
        timeout=60,
        username=auth_config.TACACS_USER,
        password=auth_config.TACACS_PASS,
        hostkey_verify=False,
    )


def show_full_running_config(host):
    with create_connection(host) as conn:
        data_raw = conn.get_config(source="running").data_xml
        return xmltodict.parse(data_raw)


def show_port_details(host: str, interface):
    with create_connection(host) as conn:
        data_raw = conn.get_config(source="running", filter=("subtree", _access_port_filter(interface))).data_xml
        return xmltodict.parse(data_raw)


def show_ipv4_config(host):
    with create_connection(host) as conn:
        data_raw = conn.get_config(source="running", filter=("subtree", _ipv4_filter())).data_xml
        return xmltodict.parse(data_raw)


def show_system(host):
    with create_connection(host) as conn:
        data_raw = conn.get_config(source="running", filter=("subtree", _system_filter())).data_xml
        return xmltodict.parse(data_raw)


def _access_port_filter(interface):
    interface = interface.split("-")
    interface.pop(0)
    filter = f"""<sub-network xmlns="http://www.advaoptical.com/ns/yang/fsp150cm-entity">
                    <network-element><ne-id>{interface[0]}</ne-id><ne-name/>
                        <shelf><shelf-id>{interface[1]}</shelf-id>
                            <slot><slot-id>{interface[2]}</slot-id>
                                <card><ethernet-card>
                                        <ethernet-port xmlns="http://www.advaoptical.com/ns/yang/fsp150cm-facility">
                                            <port-id>{interface[3]}</port-id>
                                            <port-type/>
                                            <admin-state/>
                                            <flow />
                                        </ethernet-port>
                                    </ethernet-card>
                                </card>
                            </slot>
                        </shelf>
                    </network-element>
                </sub-network>"""
    return filter


def _ipv4_filter():
    return """<sub-network xmlns="http://www.advaoptical.com/ns/yang/fsp150cm-entity">
                <system xmlns="http://www.advaoptical.com/ns/yang/fsp150cm-system">
                    <ip xmlns="http://www.advaoptical.com/ns/yang/fsp150cm-ip"><ipv4-routes /></ip>
                </system>
                </sub-network>"""


def _system_filter():
    return """<sub-network xmlns="http://www.advaoptical.com/ns/yang/fsp150cm-entity">
                <system xmlns="http://www.advaoptical.com/ns/yang/fsp150cm-system"></system>
                </sub-network>"""
