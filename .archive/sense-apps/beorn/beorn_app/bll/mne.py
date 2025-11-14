import logging
import re
import ipaddress
from flask_restx import fields

logger = logging.getLogger(__name__)


def expected_payloads(api):
    models = {
        "claim_device": claim_device_expected_payload(api),
        "net_id_put": api.model(
            "mne_netid_fields",
            {
                "cid": fields.String(example="00.L1XX.000000..TWCC"),
                "network_id": fields.String(example="L_000000000000000000"),
            },
        ),
        "mne_pr": api.model(
            "mne_pr",
            {
                "orgID": fields.String(example="000000"),
                "networkID": fields.String(example="L_00000"),
                "orgName": fields.String(example="Customer Name"),
                "networkName": fields.String(example="clli - location"),
                "devices": fields.Nested(
                    api.model(
                        "mne_pr_fields",
                        {
                            "AAAA-AAAA-AAAA": fields.Nested(
                                api.model("", {"location": fields.String(example="room number")})
                            )
                        },
                    )
                ),
            },
        ),
        "template": api.model(
            "template",
            {
                "orgID": fields.String(example="000000"),
                "orgName": fields.String(example="Customer Name"),
                "template_name": fields.String(example="template_name"),
            },
        ),
    }
    return models


def claim_device_expected_payload(api):
    """
    Creates the expected payload template for MNE claim device endpoint
    :param api: api
    :return: api.model
    """

    def empty_field(name):
        return fields.Nested(api.model(name, {}))

    payload = api.model(
        "pl",
        {
            "address": fields.String(example="123 Abc St City ST 12345"),
            "clli": fields.String(example="ABCDEFGH"),
            "account_id": fields.String(example="ACCT-1234567"),
            "customer_name": fields.String(example="CUSTOMER NAME"),
            "dp_orders": fields.List(empty_field("")),
            "dp_site_detail": fields.List(empty_field("")),
            "dp_devices": fields.List(empty_field("")),
            "dp_network_static_routes": fields.List(empty_field("")),
            "dp_policy_amps": fields.List(empty_field("")),
            "dp_policy_firewall_layer_three_firewall_policies": fields.List(empty_field("")),
            "dp_policy_firewall_layer_seven_firewall_policies": fields.List(empty_field("")),
            "dp_policy_nat_one_to_many_nats": fields.List(empty_field("")),
            "dp_policy_nat_one_to_one_nats": fields.List(empty_field("")),
            "dp_policy_nat_port_forwardings": fields.List(empty_field("")),
            "dp_users_meraki_cloud_authentications": fields.List(empty_field("")),
            "dp_users_radius": fields.List(empty_field("")),
            "dp_vpn_client_vpns": fields.List(empty_field("")),
            "dp_vpn_site_to_site_ipsecs": fields.List(empty_field("")),
            "dp_wifi_settings": fields.List(empty_field("")),
        },
    )
    return payload


def response_models(api):
    models = {}
    models["bad_request"] = api.model("bad_request", {"message": fields.String(example="Brief failure description")})

    models["server_error"] = api.model(
        "app_error", {"message": fields.String(example="MDSO failed to process the request")}
    )

    models["mne_get_ok"] = api.model(
        "Successfully retrieved data",
        {
            "mne_resource_id": fields.String(example="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"),
            "operation_ids": fields.List(cls_or_instance=fields.String(example="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")),
            "network_id": fields.String(example="L_000000000000000000"),
            "organization_id": fields.String(example="000000000000000000"),
        },
    )

    models["claim_ok"] = api.model(
        "Claim device success",
        {
            "operationId": fields.String(example="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"),
            "resourceId": fields.String(example="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"),
        },
    )

    models["netid_get_ok"] = api.model(
        "Network Id successfully retrieved", {"network_id": fields.String(example="L_000000000000000000")}
    )

    models["netid_put_ok"] = api.model(
        "Network Id successfully updated in granite",
        {
            "pathId": fields.String(example="51.L1XX.000000..TWCC"),
            "pathRev": fields.String(example="1"),
            "status": fields.String(example="Designed"),
            "pathInstanceId": fields.String(example="1204107"),
            "retString": fields.String(example="Path Updated"),
        },
    )
    return models


def base_claim_device_payload():
    """
    Basic template of payload sent to MDSO for mne claim device
    """
    return {"properties": {"devices": [], "configurations": {}}}


def get_org_and_net_name(street, clli, customer):
    if isinstance(street, dict):
        street = street["street"]
    return {"orgName": customer, "networkName": clli + " - " + street}


def clean_string(s, default="", change_all=True):
    if not s or s == "":
        return default
    else:
        s = s.lower().replace(" ", "").replace("\n", "").replace("\t", "")
        s = "icmp-ping" if s == "icmpping" else s
        if change_all and s == "all":
            s = "any"
        return s


def ip_range(ip_range_input, _list=False, expand_ranges=True, expand_cidrs=False):
    # first determine that this is not none
    if ip_range_input is None:
        return [] if _list else ""

    # else operate on this as a string
    if isinstance(ip_range_input, list):
        ip_range_input = ",".join(ip_range_input).lower().replace(" ", ",").replace("all", "any")

    ip_range_input = ip_range_input.lower()
    ip_range_input = re.sub(" *- *", "-", ip_range_input)
    ip_range_input = re.sub(" */ *", "/", ip_range_input)
    ip_range_input = re.sub(" ", ",", ip_range_input)
    ip_range_input = re.sub(",+", ",", ip_range_input)

    # special cases
    if ip_range_input == "any":
        return ["any"] if _list else "any"
    if ip_range_input == "all":
        return ["any"] if _list else "any"
    if ip_range_input == "":
        return [] if _list else ""
    if ip_range_input == "none" or ip_range_input == "null":
        return ["none"] if _list else "none"

    ip_range_input = ip_range_input.split(",")
    ip_ranges = [x for x in ip_range_input if "-" in x]
    single_ips = [x for x in ip_range_input if "-" not in x]

    ip_list = []
    if expand_ranges:
        for ips in ip_ranges:
            ip1 = ips.split("-")[0]
            ip2 = ips.split("-")[1]
            a, b = sorted([ipaddress.ip_address(ip1), ipaddress.ip_address(ip2)])
            while a < b:
                ip_list.append(str(a))
                a = a + 1
            ip_list.append((str(b)))
    else:
        ip_list.extend(ip_ranges)

    if expand_cidrs:
        for si in single_ips:
            if "/" in si:
                ip_list.extend([str(x) for x in ipaddress.ip_network(si, strict=False)])
            else:
                ip_list.append(si)
    else:
        ip_list.extend(single_ips)
    return ip_list if _list else ",".join(ip_list)


def parse_mx(all_data: dict, dp_device: dict) -> dict:
    # this will be unique to mx
    # https: // developer.cisco.com / meraki / api - v1 /  # !update-network-appliance-port
    # interfaces for this device only that will map the interface_id with the port number
    interfaces = [x for x in all_data["dp_device_interfaces"] if x["device_id"] == dp_device["id"]]
    interfaces = {x["id"]: x["interface"].replace("port", "") for x in interfaces}
    lan_ports = [x for x in all_data["dp_network_lan_ports"] if x["device_id"] == dp_device["id"]]
    ports = {}
    for port in lan_ports:
        port_no = interfaces[port["device_interface_id"]]
        v = [x for x in all_data["dp_network_lan_vlans"] if x["id"] == port["native_vlan_id"]]
        if len(v) == 1:
            v = v[0]
        else:
            continue
        ports[port_no] = {"enabled": True, "type": clean_string(port["type"]), "vlan": v["vlan"]}

        if port["type"].lower() == "trunk":
            if len(port["allowed_vlans"]) > 0:
                if len(port["allowed_vlans"]) == 1 and port["allowed_vlans"][0]["vlan_name"] == "All VLANs":
                    # first, check if allowing all vlans
                    ports[port_no]["allowedVlans"] = "all"
                else:
                    # if not allowing all vlans, create a comma seperated list string of allowed vlans
                    allowed_vlans = [str(x["vlan"]) for x in port["allowed_vlans"]]
                    ports[port_no]["allowedVlans"] = ",".join(allowed_vlans)
        else:
            ports[port_no]["accessPolicy"] = "open"

    device_info = {"appliancePorts": ports, "is_ha": dp_device.get("mne_high_availability", False)}
    return device_info


def parse_ms(all_data: dict, dp_device: dict) -> dict:
    device_switch_ports = [x for x in all_data["dp_switch_ports"] if x["device_id"] == dp_device["id"]]
    interfaces = [x for x in all_data["dp_device_interfaces"] if x["device_id"] == dp_device["id"]]
    interface_id_to_port = {x["id"]: x["interface"].replace("port", "") for x in interfaces}
    meraki_ports = {}
    for x in device_switch_ports:
        port_info = {
            "enabled": True,
            "poeEnabled": x["poe"],
            "type": clean_string(x["type"]),
            "vlan": int(x["native_vlan"] if x["native_vlan"] is not None else 88),
            "allowedVlans": clean_string(x["allowed_vlan"], change_all=False),
            "rstpEnabled": x["spanning_tree"],
            "linkNegotiation": "Auto negotiate",
        }
        if port_info["type"] == "access":
            port_info["vlan"] = int(x["vlan"] if x["vlan"] is not None else 1)
            port_info["voiceVlan"] = int(x["voice_vlan"] if x["voice_vlan"] is not None else 1)
        meraki_ports[interface_id_to_port[x["device_interface_id"]]] = port_info
    device_info = {"switchPorts": meraki_ports}
    return device_info


def parse_mv(dp_device: dict):
    mv_fields = ["mnc_default_video_settings", "mnc_video_resolution", "mnc_video_quality"]
    mv_settings = {}
    for f in mv_fields:
        mv_settings[f] = dp_device.get(f, None)
    return mv_settings


def parse_payload(data: dict):
    """
    Translates a payload from design portal that defines a
    device should be provisioned by MDSO
    :param data: dictionary payload sent from DP
    :return: new_pl: dictionary payload for MDSO or None type if errors occurred
    """
    try:
        site_details = data["dp_site_detail"]
        devices = data["dp_devices"]
        clli = data["clli"]
        new_pl = base_claim_device_payload()
        org_and_net = {
            "orgName": data["dp_site_detail"]["organization_name"],
            "networkName": data["dp_site_detail"]["network_name"],
        }
        new_pl["properties"]["configurations"]["org_id"] = data["dp_site_detail"]["organization_id"]
        new_pl["properties"]["configurations"]["dp_site_detail"] = data["dp_site_detail"]
        new_pl["properties"].update(org_and_net)
        new_pl["label"] = clli
        new_pl["properties"]["configurations"]["service_type"] = data.get("service_type")

        for dev in devices:
            d = {
                "serial": dev["serial"],
                "model": dev["model"],
                "hostname": dev["hostname"],
                "address": data["address"],
                "notes": dev["mne_cid"],
                "license_type": dev["license_type"],
                "device_info": {},
            }

            if "mx" in d["model"].lower():
                d["device_info"] = parse_mx(all_data=data, dp_device=dev)
            elif "ms" in d["model"].lower():
                d["device_info"] = parse_ms(all_data=data, dp_device=dev)
            elif "mv" in d["model"].lower():
                d["device_info"] = parse_mv(dp_device=dev)
            elif "mr" in d["model"].lower():
                # routers may not need any device specific info
                pass
            else:
                # all other devices such as IOT
                continue
            new_pl["properties"]["devices"].append(d)
        # end for loop --------------------------------------

        # wireless ssids
        # https://developer.cisco.com/meraki/api-v1/update-network-wireless-ssid/
        wifi_settings = data["dp_wifi_settings"]
        new_pl["properties"]["configurations"]["ssids"] = wifi_settings

        # https://developer.cisco.com/meraki/api-v1/#!update-network-appliance-traffic-shaping-uplink-bandwidth
        bandwidth = {"bandwidthLimits": {}}
        if len(data["dp_network_wans"]) > 0 and None not in [
            data["dp_network_wans"][0]["bw_up"],
            data["dp_network_wans"][0]["bw_down"],
        ]:
            bandwidth["bandwidthLimits"]["wan1"] = {
                "limitUp": data["dp_network_wans"][0]["bw_up"] * 1000,
                "limitDown": data["dp_network_wans"][0]["bw_down"] * 1000,
            }

        if len(data["dp_network_wans"]) > 1 and None not in [
            data["dp_network_wans"][1]["bw_up"],
            data["dp_network_wans"][1]["bw_down"],
        ]:
            bandwidth["bandwidthLimits"]["wan2"] = {
                "limitUp": data["dp_network_wans"][1]["bw_up"] * 1000,
                "limitDown": data["dp_network_wans"][1]["bw_down"] * 1000,
            }
        new_pl["properties"]["configurations"]["bandwidth"] = bandwidth

        virtual_ips = {}  # serial to vip
        dev_id_to_serial = {x["id"]: x["serial"] for x in devices if x["serial"]}
        if len(data["dp_network_wans"]) > 0:
            for wan in data["dp_network_wans"]:
                if "virtual_ip" in wan and wan["virtual_ip"]:
                    dev_id = wan["device_id"]
                    if dev_id in dev_id_to_serial:
                        virtual_ips[dev_id_to_serial[dev_id]] = virtual_ips.get(dev_id_to_serial[dev_id], []) + [
                            wan["virtual_ip"]
                        ]
        new_pl["properties"]["configurations"]["virtual_ip"] = virtual_ips

        # https://developer.cisco.com/meraki/api-v1/#!add-a-vlan
        # reserved DHCP ranges
        reserved_ranges = {}
        for lan_res in data["dp_network_lan_reservations"]:
            vlid = lan_res["vlan_id"]
            _ip = lan_res["ip"].replace(" ", "")
            _ip = _ip.split("-")
            if len(_ip) == 2:
                if vlid not in reserved_ranges:
                    reserved_ranges[vlid] = []
                reserved_ranges[vlid].append(
                    {
                        "start": _ip[0],
                        "end": _ip[1],
                        "comment": clean_string(lan_res["description"], default="reserved ip range"),
                    }
                )

        # dict map of dhcp reservations for a mac addresses {vlid: {mac: {ip: "", name: ""}}}
        fixed_ips_by_vlid = {}
        for reservation in data["dp_network_mac_reservations"]:
            if reservation["vlan_id"] not in fixed_ips_by_vlid:
                fixed_ips_by_vlid[reservation["vlan_id"]] = {}
            fixed_ips_by_vlid[reservation["vlan_id"]][reservation["mac"]] = {
                "ip": reservation["ip"],
                "name": reservation["description"],
            }

        new_pl["properties"]["configurations"]["VLANS"] = []
        vlans = data["dp_network_lan_vlans"]
        # https://developer.cisco.com/meraki/api-v1/update-network-appliance-vlan/
        for v in vlans:
            vl = {"id": v["vlan"], "name": v["vlan_name"].replace("/", "-")}

            # basic vlan settings
            if v["subnet"]:
                vl["subnet"] = v["subnet"]
            if v["ip"]:
                vl["applianceIp"] = v["ip"]
            if v["id"] in reserved_ranges:
                vl["reservedIpRanges"] = reserved_ranges[v["id"]]
            if v["id"] in fixed_ips_by_vlid:
                vl["fixedIpAssignments"] = fixed_ips_by_vlid[v["id"]]

            # settings for each type of dhcpHandling
            if v["dhcp"].lower() == "disabled":
                vl["dhcpHandling"] = "Do not respond to DHCP requests"
            elif v["dhcp"].lower() == "relay":
                vl["dhcpHandling"] = "Relay DHCP to another server"
                relay_servers = v["dhcp_server"]
                relay_servers = relay_servers.replace(" ", ",")
                relay_servers = relay_servers.replace("\n", ",")
                relay_servers = relay_servers.split(",")
                relay_servers = [x for x in relay_servers if x != ""]
                vl["dhcpRelayServerIps"] = relay_servers
            elif v["dhcp"].lower() == "enabled":
                vl["dhcpHandling"] = "Run a DHCP server"
                if v.get("dns", False):
                    if "google" in v["dns"].lower():
                        vl["dnsNameservers"] = "google_dns"
                    elif "upstream" in v["dns"].lower():
                        vl["dnsNameservers"] = "upstream_dns"
                    elif "specify" in v["dns"].lower():
                        dns_servers = v["dns_servers"]
                        dns_servers = dns_servers.replace(" ", ",")
                        dns_servers = dns_servers.replace("\n", ",")
                        dns_servers = dns_servers.split(",")
                        dns_servers = [x for x in dns_servers if x != ""]
                        vl["dnsNameservers"] = "\n".join(dns_servers)

            # dhcp options for this vlan
            dhcp_options = [x for x in data["dp_network_lan_dhcp_options"] if x["vlan_id"] == v["id"]]

            # format options
            dhcp_options = [{"code": str(x["code"]), "type": x["type"], "value": x["value"]} for x in dhcp_options]
            if dhcp_options:
                vl["dhcpOptions"] = dhcp_options
            new_pl["properties"]["configurations"]["VLANS"].append(vl)

        # https://developer.cisco.com/meraki/api-v1/#!get-network-appliance-content-filtering
        categories = (
            site_details["policy_web_filter_category_blocking"]
            + ","
            + site_details["policy_web_filter_threat_categories"]
        )
        categories = categories.replace(" ", "").split(",")
        wl = site_details["policy_web_filter_url_whitelist"]
        bl = site_details["policy_web_filter_url_blacklist"]
        new_pl["properties"]["configurations"]["contentFiltering"] = {"blockedUrlCategories": categories}
        if wl not in [None, ""]:
            new_pl["properties"]["configurations"]["contentFiltering"]["allowedUrlPatterns"] = (
                wl.replace(", ", ",").replace(" ,", ",").replace(" ", ",").replace("\n", ",").replace(" ", "").split(",")
            )
        if bl not in [None, ""]:
            new_pl["properties"]["configurations"]["contentFiltering"]["blockedUrlPatterns"] = (
                bl.replace(", ", ",").replace(" ,", ",").replace(" ", ",").replace("\n", ",").replace(" ", "").split(",")
            )

        # https://developer.cisco.com/meraki/api-v1/#!update-network-appliance-security-intrusion
        new_pl["properties"]["configurations"]["ip_sec_rules"] = {
            "mode": site_details["policy_ips_mode"],
            "idsRulesets": site_details["policy_ips_ruleset"],
        }

        # https://developer.cisco.com/meraki/api-v1/#!update-network-appliance-firewall-one-to-one-nat-rules
        allowed_inbound = data["dp_policy_nat_allowed_inbound_connections"]
        new_pl["properties"]["configurations"]["one_1NAT"] = {"rules": []}
        one_one = data["dp_policy_nat_one_to_one_nats"]
        for n in one_one:
            rule = {
                "name": n["name"],
                "lanIp": n["internal_ip"],
                "publicIp": n["external_ip"],
                "uplink": clean_string(n["uplink"]),
                "allowedInbound": [
                    {
                        "protocol": clean_string(x["protocol"]),
                        "destinationPorts": clean_string(x["ports"]).split(","),
                        "allowedIps": ip_range(clean_string(x["remote_ips"]), _list=True),
                    }
                    for x in allowed_inbound
                    if x["one_to_one_nat_id"] == n["id"]
                ],
            }
            new_pl["properties"]["configurations"]["one_1NAT"]["rules"].append(rule)

        # https://developer.cisco.com/meraki/api-v1/#!set-the-1many-nat-mapping-rules-for-an-mx-network
        one_many = data["dp_policy_nat_one_to_many_nats"]
        # dict map {publicIP: [list nat rules for that public ip]}
        our_one_many_rules = {}
        for rule in one_many:
            public_iP = clean_string(rule["external_ip"])
            if public_iP not in our_one_many_rules:
                our_one_many_rules[public_iP] = []
            nat_rule = {
                "name": clean_string(rule["description"], default="Rule"),
                "protocol": clean_string(rule["protocol"]),
                "allowedIps": ip_range(rule["source_ips"], _list=True),
            }
            if rule["external_port"]:
                nat_rule["publicPort"] = rule["external_port"]
            if rule["internal_port"]:
                nat_rule["localPort"] = rule["internal_port"]
            if rule["internal_ip"]:
                nat_rule["localIp"] = rule["internal_ip"]

            our_one_many_rules[public_iP].append(nat_rule)
        # now turn that map into a list of one-many rules
        new_pl["properties"]["configurations"]["one_manyNAT"] = {
            "rules": [
                {
                    "publicIp": publicIP,
                    # internet1 or internet2 is not provided so setting this to internet1 by default
                    "uplink": "internet1",
                    "portRules": portRules,
                }
                for publicIP, portRules in our_one_many_rules.items()
            ]
        }

        # https://developer.cisco.com/meraki/api-v1/#!update-network-appliance-firewall-port-forwarding-rules
        new_pl["properties"]["configurations"]["portforward"] = {"rules": []}
        pf_rules = data["dp_policy_nat_port_forwardings"]
        new_pl["properties"]["configurations"]["portforward"] = pf_rules

        # https://developer.cisco.com/meraki/api-v1/#!update-network-appliance-firewall-l-3-firewall-rules
        new_pl["properties"]["configurations"]["L3_rules"] = {"rules": []}
        l3_rules = data["dp_policy_firewall_layer_three_firewall_policies"]
        for l3 in l3_rules:
            rule = {
                "comment": clean_string(l3["description"]),
                "policy": clean_string(l3["action"]),
                "protocol": clean_string(l3["protocol"]),
                "destPort": clean_string(l3["destination_po"]),
                "destCidr": ip_range(l3["destination_ip"]),
                "srcPort": clean_string(l3["source_port"]),
                "srcCidr": ip_range(l3["source_ip"]),
            }
            new_pl["properties"]["configurations"]["L3_rules"]["rules"].append(rule)

        # https://developer.cisco.com/meraki/api-v1/#!update-network-appliance-firewall-l-7-firewall-rules
        new_pl["properties"]["configurations"]["L7_rules"] = {"rules": []}
        l7_rules = data["dp_policy_firewall_layer_seven_firewall_policies"]
        for l7 in l7_rules:
            rule = {"policy": clean_string(l7["action"]), "type": l7["type"], "value": l7["value"]}
            new_pl["properties"]["configurations"]["L7_rules"]["rules"].append(rule)

        new_pl["properties"]["configurations"]["static_routes"] = []
        dp_network_static_routes = data["dp_network_static_routes"]
        if dp_network_static_routes:
            for r in dp_network_static_routes:
                s_route = {"name": r["name"], "subnet": r["subnet"], "gatewayIp": r["next_hop_ip"]}
                new_pl["properties"]["configurations"]["static_routes"].append(s_route)

        new_pl["properties"]["configurations"]["site_to_site_ipsecs"] = {"peers": []}
        dp_vpn_site_to_site_ipsecs = data["dp_vpn_site_to_site_ipsecs"]
        for x in dp_vpn_site_to_site_ipsecs:
            obj = {
                "name": x["name"],
                "ipsecPolicies": {"ikeAuthAlgo": ["sha1"], "ikePrfAlgo": ["prfsha1"]},
                "ipsecPoliciesPreset": "default",
                "secret": x["psk"],
                "networkTags": ["none"],
            }
            if x["remote_networks"]:
                obj["privateSubnets"] = x["remote_networks"].split(", ")
            if x["local_id"]:
                obj["localId"] = x["local_id"]
            if x["remote_id"]:
                obj["remoteId"] = x["remote_id"]
            if x["remote_gateway"]:
                obj["publicIp"] = x["remote_gateway"]
            if x["ike_version"]:
                obj["ikeVersion"] = x["ike_version"]
            if x["phase_one_encryption"]:
                obj["ipsecPolicies"]["ikeCipherAlgo"] = [
                    "tripledes" if x["phase_one_encryption"] == "3DES" else x["phase_one_encryption"].lower()
                ]
            if x["phase_one_authentication"]:
                obj["ipsecPolicies"]["ikeAuthAlgo"] = [x["phase_one_authentication"].lower()]
            # phase 1 psf is not provide in payload, keep as default value ["prfsha1"]
            if x["phase_one_dh_group"]:
                obj["ipsecPolicies"]["ikeDiffieHellmanGroup"] = [f"group{x['phase_one_dh_group']}"]
            if x["phase_one_lifetime"]:
                obj["ipsecPolicies"]["ikeLifetime"] = x["phase_one_lifetime"]
            if x["phase_two_encryption"]:
                childcipheralgo = x["phase_two_encryption"].split(", ")
                obj["ipsecPolicies"]["childCipherAlgo"] = ["tripledes" if x == "3DES" else x for x in childcipheralgo]
            if x["phase_two_authentication"]:
                obj["ipsecPolicies"]["childAuthAlgo"] = x["phase_two_authentication"].split(", ")
            if x["phase_two_pfs"]:
                if x["phase_two_pfs"].upper() == "OFF":
                    obj["ipsecPolicies"]["childPfsGroup"] = ["disabled"]
                else:
                    obj["ipsecPolicies"]["childPfsGroup"] = [f"group{x['phase_two_pfs']}"]
            if x["phase_two_lifetime"]:
                obj["ipsecPolicies"]["childLifetime"] = x["phase_two_lifetime"]
            new_pl["properties"]["configurations"]["site_to_site_ipsecs"]["peers"].append(obj)
            new_pl["properties"]["configurations"]["sensor_profiles"] = data.get("dp_sensor_alert_profiles", [])
    except Exception:
        return None
    return new_pl


def validate_net_name(net_name):
    """
    validate that there are no invalid characters like a comma in the network name
    """
    pattern = r"\w|.|@|#|_|-| "
    bad_chars = re.sub(pattern, "", net_name)
    return len(bad_chars) == 0


def clean_message(message):
    new_message = message
    try:
        new_message = re.split(pattern=r".merakiServices.merakiServices.(Activate|claimDevice), ", string=new_message)[2]
        new_message = re.split(pattern="Please check file: plan-script", string=new_message)[0]
        return new_message
    except Exception:
        return message
