from scripts.common_plan import CommonPlan
from .utilities.ssh_connection import SSHConnection
from .utilities.fortigateAPI import Fortigate
from .utilities.ene_logger import ENElogger
from .cli_scripts import load_base_config, send_cli_commands, did_encounter_error, set_user_password, del_admin_script
from .interfaces import disable_unused_interfaces
from .api_user import create_system_api_user, delete_system_api_user
from .destination_nat import configure_vip
from .firewall_policies import config_firewall_policy
from .interfaces import handle_interface
from .onboard import onboard
from .routing import config_bgp, config_ospf, config_static_routes
from .services import config_service_groups, config_services
from .upgrade_firmware import upgrade_firmware_fortiguard
from .users import config_ldap_servers, config_radius_servers, config_user_groups
from .webfilter import config_default_webfilter
import ipaddress
import re
import time
import json
import traceback


class Activate(CommonPlan):
    def process(self):
        self.ene_logger = ENElogger(self)
        try:
            self.load_resource_vars()
            self.load_private_vars()
        except Exception as e:
            tb = traceback.format_exc()
            self.ene_logger.log_step("Loading resource variables")
            external_message = "Failed to initialize resource variables"
            internal_message = "Failed to initialize resource variables"
            self.ene_logger.log_issue(
                external_message=external_message,
                internal_message=internal_message,
                api_response=str(e.args),
                code=3001,
                details=tb,
                category=5
            )
        try:
            self.ene_logger.log_step("Creating SSH connection to device")
            self.create_ssh_connection()

            self.ene_logger.log_step("Creating API User")
            self.create_api_user()

            self.ene_logger.log_step("Checking device status")
            self.serial_check()

            self.ene_logger.log_step("Updating firmware")
            self.upgrade_firmware()

            self.ene_logger.log_step("Applying base configuration")
            self.apply_base_script()

            self.ene_logger.log_step("Onboarding Device")
            self.onboard_device()

            self.ene_logger.log_step("Applying Services")
            self.apply_services()

            self.ene_logger.log_step("Applying interface configs")
            self.apply_interface_configs()

            self.ene_logger.log_step("Applying IP pools")
            self.apply_ip_pools()

            self.ene_logger.log_step("Applying VIPs")
            self.apply_vips()

            self.ene_logger.log_step("Applying Users")
            self.apply_users()

            self.ene_logger.log_step("Applying Routing")
            self.apply_routing()

            self.ene_logger.log_step("Applying firewall policies")
            self.apply_firewall_policies()

            self.ene_logger.log_step("Deleting API user")
            self.clean_up_users()
        except Exception as e:
            tb = traceback.format_exc()
            resource_id = ""
            label = ""
            external_message = "An unknown error occurred while activating. Please reach out to MS fulfillment"
            internal_message = ("Outer try except caught an exception, please the review the traceback."
                                f" resource_id={resource_id}; label={label}; error={e.args}")
            self.ene_logger.log_issue(
                external_message=external_message,
                internal_message=internal_message,
                api_response="",
                code=3001,
                details=tb,
                category=5
            )

    def create_ssh_connection(self):
        self.ene_logger.info('--- Beginning ssh connection ---')
        # will need these later, so make them class variables
        self.main_username = self.private_vars.get('FORTIGATE_USERNAME')
        self.main_pw = self.private_vars.get('FORTIGATE_PW')
        self.main_password_hash = self.private_vars.get('FORTIGATE_PASSWORD_HASH')
        admin = "admin"
        staging_pw = self.private_vars.get('FORTIGATE_ADMIN_PW_STAGING')
        field_pw = self.private_vars.get('FORTIGATE_ADMIN_PW_FIELD')
        if self.user_type.upper() == "STAGING":
            # attempt all credential pairs, but attempt them in the order of 'most likely'
            login_pairs = [
                (admin, staging_pw),
                (self.main_username, self.main_pw),
                (admin, field_pw)
            ]
        else:
            login_pairs = [
                (admin, field_pw),
                (self.main_username, self.main_pw),
                (admin, staging_pw)
            ]
        for username, password in login_pairs:
            try:
                self.ene_logger.logger.info(f"Attempting to create ssh connection with {username}")
                self.ssh_connection = SSHConnection(
                    username=username,
                    password=password,
                    hostname=self.ip,
                    logger=self.ene_logger
                )
                return   # if it did not throw an exception then we are logged in
            except Exception:
                self.ene_logger.logger.info(f"Failed to create ssh connection with {username}")
                time.sleep(1)  # wait just a sec before trying the next credential pair
        # if we made it out of the loop, then we failed to create an ssh connection with all attempted loging pairs
        # logging this issues will cause the resource to halt and fail out
        tb = traceback.format_exc()
        internal_message = "Failed to create SSH connection to device."
        external_message = (f"{internal_message} Attempted {admin}@{self.ip} AND {self.main_username}@{self.ip} "
                            "Please ensure the user has been created on the device, and SSH and HTTPs traffic"
                            " is permitted")
        self.ene_logger.log_issue(
            external_message=external_message,
            internal_message=internal_message,
            details=tb,
            code=3210,
            category=0
        )

    def load_bgp(self, order_info):
        asn = order_info["dp_site_detail"]['bgp_asn']
        self.ene_logger.info(f"Inside load_bgp(). asn set: {asn}")

        neighbors = order_info['dp_bgp_neighbors']
        self.ene_logger.info(f"Inside load_bgp(). neighbors set: {neighbors}")

        neighbor_ranges = order_info['dp_bgp_neighbor_ranges']
        self.ene_logger.info(f"Inside load_bgp(). neighbor_ranges set: {neighbor_ranges}")

        neighbor_groups = order_info["dp_bgp_neighbors"]
        self.ene_logger.info(f"Inside load_bgp(). neighbor_groups set: {neighbor_groups}")

        networks = order_info['dp_bgp_networks']
        self.ene_logger.info(f"Inside load_bgp(). networks set: {networks}")

        router_id = order_info["dp_site_detail"]['bgp_router_id']
        if router_id != "" and router_id is not None:
            self.ene_logger.info(f"Inside load_bgp(). router_id set: {router_id}")
            try:
                ipaddress.IPv4Address(router_id)
            except ipaddress.AddressValueError:
                router_id = self.ip
        else:
            self.ene_logger.info(f"Inside load_bgp(). router_id is an empty string or None: {router_id}")
            router_id = self.ip
        self.bgp = {
            "asn": asn,
            "neighbors": [] if neighbors else None,
            "neighbor_ranges": [] if neighbor_ranges else None,
            "neighbor_groups": [] if neighbor_groups else None,
            "networks": [] if networks else None,
            "router_id": router_id
        }
        if neighbors:
            exclude_lower_case = []
            for neighbor in neighbors:
                new_neighbor_definition = {
                    "ip": neighbor["neighbor_ip"],
                    "local-as": neighbor["local_as"],
                    "password": neighbor["password"],
                    "next-hop-self": neighbor["next_hop_self"],
                    "next-hop-self-rr": neighbor["next_hop_self_rr"],
                    "route-reflector-client": neighbor["route_reflector_client"],
                    "prefix-list-in": neighbor["prefix_list_in"],
                    "prefix-list-out": neighbor["prefix_list_out"],
                    "route-map-in": neighbor["route_map_in"],
                    "route-map-out": neighbor["route_map_out"]
                }
                if neighbor["bgp_neigh_int"]:
                    new_neighbor_definition["interface"] = self.interface_map.get(neighbor["bgp_neigh_int"]["device_interface_id"])

                if neighbor["bgp_neigh_src"]:
                    new_neighbor_definition["update-source"] = self.interface_map.get(neighbor["bgp_neigh_src"]["device_interface_id"])

                if neighbor["remote_as"]:
                    new_neighbor_definition["remote-as"] = str(neighbor["remote_as"])

                new_neighbor_definition = {
                    k: v.lower
                    if isinstance(v, str) and k not in exclude_lower_case
                    else v
                    for k, v in new_neighbor_definition.items()
                }
                new_neighbor_definition = {
                    k: v
                    for k, v in new_neighbor_definition.items()
                    if v is not None
                }
                self.bgp['neighbors'].append(new_neighbor_definition)
        if neighbor_ranges:
            for nr in neighbor_ranges:
                new_nr_definition = {
                    "id": nr["neighbor_range_id"],
                    "prefix6": nr["prefix"],
                    "neighbor-group": nr["neighbor_group"]
                }
                self.bgp['neighbor_ranges'].append(new_nr_definition)
        if neighbor_groups:
            # iterate through the neighbors dp_bgp_neighbors
            for ng in neighbor_groups:
                if ng["is_neighbor_group"] == "true":

                    new_definition = {
                        "name": ng["name"],
                        "advertisement-interval": int(order_info["dp_site_detail"]["bgp_advertisement_interval"]),
                        "link-down-failover": order_info["dp_site_detail"]["bgp_link_down_failover"].lower(),
                        "soft-reconfiguration": order_info["dp_site_detail"]["bgp_soft_reconfiguration"].lower(),
                        "remote-as": order_info["dp_site_detail"]["bgp_asn"],
                        "route-map-in": order_info["dp_site_detail"]["route_map_in"],
                        "route-reflector-client": ng["route_reflector_client"],

                    }
                    self.bgp['neighbor_groups'].append(new_definition)
        if networks:
            for network in networks:
                new_network_definition = {
                    "id": network["prefix_id"],
                    "network-import-check": order_info["dp_site_detail"]["bgp_network_import_check"].lower(),
                    "prefix": network["prefix"]
                }
                self.bgp['networks'].append(new_network_definition)

    def load_firewall_policies(self, order_info):
        firewall_policies = order_info["dp_policy_firewalls"]
        formatted_policies = []
        interfaces = order_info["dp_device_interfaces"]
        interfaces = {intf["id"]: intf["interface"] for intf in interfaces}
        for policy in firewall_policies:
            new_policy = {
                "policyid": policy["dp_policy_firewall_id"],
                'action': policy['action'].lower(),
                'nat': policy['nat'].lower(),
                "schedule": policy['schedule'].lower(),
                "status": policy['status'].lower(),
                'comments': '',
                'name': policy.get('name', ''),
                'poolname': policy.get('poolname', []),
                'users': policy.get('users', []),
            }

            new_policy["srcintf"] = [
                {"name": x["name"] if x["name"] else interfaces[x["device_interface_id"]]}
                for x in policy["firewall_source_int"] if x["device_interface_id"] or x["name"]
            ]
            new_policy["dstintf"] = [
                {"name": x["name"] if x["name"] else interfaces[x["device_interface_id"]]}
                for x in policy["firewall_dest_int"] if x["device_interface_id"] or x["name"]
            ]
            new_policy["srcaddr"] = [{"name": x["name"].lower()} for x in policy["firewall_source_add_obj"] if x["name"]]
            new_policy["dstaddr"] = [{"name": x["name"].lower()} for x in policy["firewall_dest_add_obj"] if x["name"]]
            formatted_policies.append(new_policy)
        self.firewall_policies = formatted_policies if len(formatted_policies) > 0 else None
        if self.firewall_policies:
            self.logger.info(f"firewall_policies are: \n{json.dumps(self.firewall_policies, indent=4)}")
        else:
            self.logger.info("firewall_policies are: None")

    def load_lan_intf(self, interface_data):
        intf_id = interface_data['device_interface_id']
        if intf_id not in self.interface_map:
            message = "could not find physical interface associated with lan object"
            self.ene_logger.log_issue(
                external_message=message,
                internal_message=message,
                code=2999,
                category=1,
                details=f"{intf_id} no in {list(self.interface_map.keys())}"
            )
            return None
        else:
            self.used_interfaces.append(self.interface_map[intf_id])
        allow_access = interface_data["allow_access"].lower().replace(",", "") if interface_data["allow_access"] else ""
        return {
            "vdom": "root",
            "name": self.interface_map[intf_id],
            "allowaccess": allow_access,
            "role": "lan",
            "type": "physical",
        }

    def load_wan_intf(self, interface_data):
        intf_id = interface_data['device_interface_id']
        if intf_id not in self.interface_map:
            message = "could not find physical interface associated with wan object"
            self.ene_logger.log_issue(
                external_message=message,
                internal_message=message,
                code=2999,
                category=1,
                details=f"{intf_id} no in {list(self.interface_map.keys())}"
            )
            return None
        else:
            self.used_interfaces.append(self.interface_map[intf_id])
        allow_access = interface_data["allow_access"].lower().replace(",", "") if interface_data["allow_access"] else ""
        return {
            "vdom": "root",
            "name": self.interface_map[intf_id],
            "allowaccess": allow_access,
            "role": "an",
            "type": "physical",
        }

    def load_vlan_intf(self, interface_data, vlan_intf_map):
        vlan_id = interface_data['vlan_id']
        if vlan_id not in vlan_intf_map:
            message = "there is no parent interface configured for VLAN"
            self.ene_logger.log_issue(
                external_message=f"{message} {interface_data['name']}",
                internal_message=message,
                code=2999,
                category=1,
                details=f"{vlan_id} no in {list(self.interface_map.keys())}"
            )
            return None
        allow_access = interface_data["allow_access"].lower().replace(",", "") if interface_data["allow_access"] else ""
        name = interface_data["name"] if interface_data[
            "name"] else f"{interface_data['interface_type']}_{interface_data['id']}"
        name = name[:18]
        alias = interface_data["alias"] if interface_data["alias"] else name
        mode = interface_data["mode"].lower() if interface_data["mode"] else None
        role = interface_data["role"].lower() if interface_data["role"] else "undefined"
        return {
            "vdom": "root",
            "name": name,
            "alias": alias,
            "type": "vlan",
            "vlanid": vlan_id,
            "ip": interface_data["ip"],
            "description": interface_data["description"],
            "allowaccess": allow_access,
            "mode": mode,
            "role": role,
            "interface": vlan_intf_map[vlan_id],
        }

    def load_agg_intf(self, interface_data):
        allow_access = interface_data["allow_access"].lower().replace(",", "") if interface_data["allow_access"] else ""
        name = interface_data["name"] if interface_data[
            "name"] else f"{interface_data['interface_type']}_{interface_data['id']}"
        name = name[:18]
        alias = interface_data["alias"] if interface_data["alias"] else name
        mode = interface_data["mode"].lower() if interface_data["mode"] else None
        role = interface_data["role"].lower() if interface_data["role"] else "undefined"
        fortilink = interface_data["fortilink"].lower() if interface_data["fortilink"] else None
        members = interface_data["int_members"]
        added_members = []
        for m in members:
            if m["device_interface_id"] in self.interface_map:
                added_members.append(self.interface_map[m["device_interface_id"]])
        members = added_members
        return {
            "vdom": "root",
            "name": name,
            "alias": alias,
            "type": "aggregate",
            "description": interface_data["description"],
            "allowaccess": allow_access,
            "mode": mode,
            "role": role,
            "members": members,
            "fortilink": fortilink,
        }

    def load_loopback_intf(self, interface_data):
        allow_access = interface_data["allow_access"].lower().replace(",", "") if interface_data["allow_access"] else ""
        name = interface_data["name"] if interface_data[
            "name"] else f"{interface_data['interface_type']}_{interface_data['id']}"
        name = name[:18]
        alias = interface_data["alias"] if interface_data["alias"] else name
        mode = interface_data["mode"].lower() if interface_data["mode"] else None
        role = interface_data["role"].lower() if interface_data["role"] else "undefined"
        return {
            "vdom": "root",
            "name": name,
            "alias": alias,
            "type": "loopback",
            "description": interface_data["description"],
            "allowaccess": allow_access,
            "ip": interface_data["ip"],
            "mode": mode,
            "role": role,
        }

    def load_interfaces(self, order_info):
        new_interfaces = {
            "lan": [],
            "wan": [],
            "aggregate": [],
            "vlan": [],
            "loopback": [],
        }
        dp_interfaces = order_info["dp_network_lans"]
        self.used_interfaces = []
        vlan_id_to_physical_map = {}
        for intf in dp_interfaces:
            if intf["int_vlans"]:
                for vlan in intf["int_vlans"]:
                    vlan_id_to_physical_map[vlan["vlan_id"]] = self.interface_map[intf["device_interface_id"]]
                    self.used_interfaces.append(self.interface_map[intf["device_interface_id"]])

        for interface in dp_interfaces:
            if interface["wan_preference"] == "Primary":
                continue
            intf_type = interface["interface_type"]
            if intf_type == "LAN":
                lan_info_payload = self.load_lan_intf(interface)
                if not lan_info_payload:
                    self.ene_logger.info("Failed to load LAN intf. ")
                else:
                    new_interfaces["lan"].append(lan_info_payload)
            elif intf_type == "VLAN":
                vlan_info_payload = self.load_vlan_intf(interface, vlan_id_to_physical_map)
                if not vlan_info_payload:
                    self.ene_logger.info("Failed to load vlan intf. ")
                else:
                    new_interfaces["vlan"].append(vlan_info_payload)
            elif intf_type == "Aggregate":
                agg_info_payload = self.load_agg_intf(interface)
                if not agg_info_payload:
                    self.ene_logger.info("Failed to load agg intf. ")
                else:
                    new_interfaces["aggregate"].append(agg_info_payload)
            elif intf_type == "WAN":
                wan_info_payload = self.load_wan_intf(interface)
                if not wan_info_payload:
                    self.ene_logger.info("Failed to load agg intf. ")
                else:
                    new_interfaces["wan"].append(wan_info_payload)
            elif intf_type == "Loopback":
                loopback_info_payload = self.load_loopback_intf(interface)
                if not loopback_info_payload:
                    self.ene_logger.info("Failed to load loopback intf. ")
                else:
                    new_interfaces["loopback"].append(loopback_info_payload)
            else:
                self.ene_logger.error(f"Unknown intf type: {intf_type}")

        all_interfaces = []
        for type_ in new_interfaces.keys():
            all_interfaces.extend(new_interfaces[type_])

        self.interfaces = all_interfaces
        if self.interfaces:
            if self.staging_interface:
                interfaces_to_remove = [x for x in self.interfaces if x["name"] == self.staging_interface]
                self.logger.info(f"Removing staging interface: {json.dumps(interfaces_to_remove, indent=4)}")
                self.interfaces = [x for x in self.interfaces if x["name"] != self.staging_interface]
                self.used_interfaces.append(self.staging_interface)
                self.used_interfaces = list(set(self.used_interfaces))
            self.logger.info(f"interfaces are: \n{json.dumps(self.interfaces, indent=4)}")
            self.logger.info(f"used interfaces are: \n{json.dumps(self.used_interfaces, indent=4)}")
        else:
            self.logger.info("interfaces are: None")

    def load_ippools(self, order_info):
        self.ippools = []
        ippools = order_info["dp_policy_ip_pools"]
        for ippool in ippools:
            new_pool = {
                "name": ippool["name"],
                "startip": ippool["start_ip"],
                "endip": ippool["end_ip"],
                "source_endip": ippool["source_start_ip"],
                "source_startip": ippool["source_end_ip"],
            }
            self.ippools.append(new_pool)
        self.ippools = self.ippools if self.ippools else None
        if self.ippools:
            self.ene_logger.info(f"IP POOLS ARE: \n{self.ippools}")

    def load_ldap(self, order_info):
        default_name = "ldap_name_placeholder"
        required_fields = ["name", "ip", "dn"]
        self.ldap = []
        user_ldaps = order_info["dp_users_ldaps"]
        for i, ul in enumerate(user_ldaps):
            new_ldap = {
                # enforce as not null
                'name': ul["name"] if ul["name"] else default_name,
                'ip': ul["ip"] if ul["ip"] else "",
                'dn': ul["dn"] if ul["dn"] else "",
                'cnid': ul["cnid"],                       # optional
                'port': ul["port"],                        # optional
                'source_ip': ul["source_ip"],              # optional
                'username': ul["username"],                # optional
                'password': ul["password"],                # optional
                'vdom': 'root'                             # optional
            }
            required = [new_ldap[x] for x in required_fields]
            if None in required or "" in required:
                details = [f"{k}={v}" for k, v in zip(required_fields, required)]
                self.ene_logger.log_issue(
                    external_message=f"Not all required LDAP fields are populated fo LDAP {i} ",
                    internal_message="not all required LDAP fields are populated",
                    code=2999,
                    category=1,
                    details=f"{details}"
                )
                continue
            new_ldap = {k: v for k, v in new_ldap.items() if v is not None}
            self.ldap.append(new_ldap)
        self.ldap = self.ldap if self.ldap else None

    def load_ospf(self, order_info):
        areas = order_info["dp_ospf_areas"]
        networks = order_info["dp_ospf_networks"]
        interfaces = order_info["dp_ospf_interfaces"]
        areas = [
            {
                "type": a["type"].lower(),
                "id": f"{a['area_id']}".lower(),
                "authentication": a["authentication"].lower(),
            } for a in areas
        ]
        interfaces = [
            {
                "authentication": i["authentication"].lower() if i["authentication"] else None,
                "authentication-key": i["authentication_key"] if i["authentication_key"] else None,
                "dead-interval": i["dead_interval"],
                "hello-interval": i["hello_interval"],
                "name": i["name"],
                "network-type": i["network_type"].lower(),
            } for i in interfaces
        ]
        networks_updated = []
        for n in networks:
            areas = [x for x in areas if x["id"] == n["area_id"]]
            if len(areas) == 0:
                self.ene_logger.info(f"skipping ospf network {n['id']}")
                continue
            new_network = {
                "id": n["id"],
                "area": areas[0]["area_id"],
                "prefix": n["prefix"]
            }
            networks_updated.append(new_network)
        networks = networks_updated
        self.ospf = {
            "areas": areas,
            "networks": networks,
            "interfaces": interfaces,
        }

    def load_radius(self, order_info):
        self.radius = []
        radius_servers = order_info["dp_users_radius"]
        for rs in radius_servers:
            new_rs = {
                'name': rs["name"],
                'ip': rs["ip"],
                'secret': rs["psk"],
                'auth_type': rs["authentication_type"],  # optional
                # 'interface': '',  # optional
                'radius_port': 1812,  # optional
                'vdom': 'root'
            }
            if rs["nas_ip"]:
                new_rs["nas_ip"] = rs["nas_ip"]
            if rs["port"]:
                new_rs["port"] = rs["port"]
            self.radius.append(new_rs)
        self.radius = self.radius if self.radius else None

    def load_services(self, order_info):
        self.services = []
        service_objects = order_info["dp_policy_service_objects"]
        for service_obj in service_objects:
            tcp_start = service_obj["tcp_start_port"]
            tcp_end = service_obj["tcp_end_port"]
            udp_start = service_obj["udp_start_port"]
            udp_end = service_obj["udp_end_port"]
            protocol = service_obj["protocol"].upper()
            if "TCP/UDP" in protocol:
                protocol = "TCP/UDP/UDP-Lite/SCTP"
            new_service = {
                "vdom": "root",
                "protocol": protocol,
                "name": service_obj["name"],
                "protocol_number": service_obj["protocol_number"],
                "icmptype": service_obj["icmp_type"],
                "icmpcode": service_obj["icmp_code"],
                "port_range": {'tcp': [tcp_start, tcp_end], 'udp': [udp_start, udp_end]},
            }
            self.services.append(new_service)
        self.services = self.services if len(self.services) > 0 else None
        if self.services:
            self.logger.info(f"SERVICES ARE: {json.dumps(self.services, indent=4)}")

    def load_service_groups(self, order_info):
        service_groups = order_info["dp_policy_service_groups"]
        self.service_groups = []
        for group in service_groups:
            members = []
            for member in group["dp_policy_service_objects"]:
                members.append(
                    {
                        "name": member["name"],
                        "id": member["id"],
                    }
                )
            new_group = {
                "name": group["name"],
                "comment": group["description"],
                "vdom": "root",
                "members": members,
            }
            self.service_groups.append(new_group)
        self.service_groups = self.service_groups if self.service_groups else None

    def load_static_routes(self, order_info):
        self.static_routes = []
        dp_static_routes = order_info["dp_network_static_routes"]
        for sr in dp_static_routes:
            new_sr = {
                'name': sr["name"],
                "vdom": "root"
            }
            self.static_routes.append(new_sr)
        self.static_routes = {"routes": self.static_routes} if self.static_routes else None

    def load_user_groups(self, order_info):
        dp_user_groups = order_info["dp_users_user_groups"]
        self.user_groups = []
        for group in dp_user_groups:
            locals = group["members_local"]
            locals = [m["username"] for m in locals]
            new_group = {
                "name": group["name"],
                "local": locals,
                "servers": []
            }
            self.user_groups.append(new_group)
        self.user_groups = self.user_groups if self.user_groups else None

    def load_vips(self, order_info):
        self.vips = []
        policy_vips = order_info["dp_policy_vips"]
        for vip in policy_vips:
            new_vip = {
                "extip": vip["external_ip"],
                "mappedip": vip["internal_ip"],
                "extport": vip["external_port"],
                "mappedport": vip["internal_port"],
                "protocol": vip["protocol"].lower() if isinstance(vip["protocol"], str) else None,
                "srcaddr": vip["source_address"],
            }
            self.vips.append(new_vip)
        self.vips = self.vips if self.vips else None

    def get_fortigate_info(self, order_info):
        dp_network_lans = order_info["dp_network_lans"]
        self.interface_map = order_info["dp_device_interfaces"]
        self.interface_map = {x["id"]: x["interface"] for x in self.interface_map}
        primary = None
        for interface in dp_network_lans:
            if interface["interface_type"] == "WAN":
                if interface["wan_preference"] == "Primary":
                    primary = interface
                    break
        if not primary:
            message = "Unable to find primary WAN interface"
            self.ene_logger.log_issue(
                external_message=message,
                internal_message=message,
                code=3999,
                category=1,
                details=""
            )
            return
        if primary["vlan_id"] is not None:
            # tagged
            self.wan_intf_name = primary["alias"]
        else:
            self.wan_intf_name = self.interface_map[primary["device_interface_id"]]
        self.wan_intf_name = primary["alias"]
        self.ip = order_info.get("device_ip")
        if not self.ip:
            message = "Unable to determine device IP address"
            self.ene_logger.log_issue(
                external_message=message,
                internal_message=message,
                code=3210,
                category=1,
                details=""
            )
        self.serial = self.devices[0]["serial"]
        self.tid = self.devices[0]["tid"]
        customer_name = order_info["customer_name"].strip().replace(" ", "_").upper()
        customer_name = re.sub(r'[^a-zA-Z0-9_]', '', customer_name)
        self.sub_account = f"ACCT-{customer_name}"

    def load_resource_vars(self):
        self.config = self.resource["properties"]["configurations"]
        self.address = self.config["address"]
        self.customer = self.config["customer_name"]
        self.state = self.config["state"]
        self.user_type = self.config["user_type"]
        self.cloudkey = None
        self.cloud_license = None
        self.staging_interface = self.config.get("interface", None)
        self.ene_logger.info(f"Staging interface from dice is: {self.staging_interface}")
        self.devices = []
        for device in self.config["dp_devices"]:
            device = {
                "serial": device["serial"],
                "tid": device["hostname"],
                "ip": device["ip"],
                "address": self.config["address"],
                "addresses": self.config.get("addresses", None),
                "address_groups": self.config.get("address_groups", None),
                "advpn": self.config.get("advpn", None),
                "interfaces": []
            }
            self.devices.append(device)
        self.get_fortigate_info(self.config)
        configs_to_load = [
            'interfaces',  # interfaces must be first
            'bgp',
            'firewall_policies',
            'ippools',
            'ldap',
            'ospf',
            'radius',
            'services',
            'service_groups',
            'static_routes',
            'user_groups',
            'vips',
        ]
        for config in configs_to_load:
            try:
                config = f"load_{config}"
                assert hasattr(self, config), f"Config {config} not found"
                getattr(self, config)(self.config)
            except Exception:
                message = f"unable to load config for {config}"
                self.ene_logger.log_issue(
                    external_message=message,
                    internal_message=message,
                    code=2999,
                    category=1,
                    details=traceback.format_exc()
                )

    def load_private_vars(self):
        resources = self.get_resources_by_type_and_label(
            "charter.resourceTypes.ENEData",
            "default",
            no_fail=True
        )
        if resources is None or len(resources) == 0:
            message = 'no private data resources'
            self.ene_logger.log_issue(
                external_message=message,
                internal_message=message,
                code=3002,
                category=1
            )
        rid = resources[0]['id']
        self.ene_logger.info(f"LOADING PRIVATE VARS FROM RESOURCE {rid}")
        self.private_vars = self.bpo.resources.get(rid, obfuscate=False)['properties']
        private_var_keys = json.dumps(
            list(self.private_vars.keys()),
            indent=4
        )
        self.ene_logger.info(f"PRIVATE VAR KEYS {private_var_keys}")

    def create_api_user(self):
        """
        Generate the api user and set the api key.
        Key generation failure is handled by the config_system_api_user script
        :return:
        """
        # key generations failure is handled by function
        try:
            self.api_key = create_system_api_user(
                ip=self.ip,
                username=self.private_vars.get('FORTIGATE_USERNAME'),
                source=self.private_vars.get('MDSO_PUBLIC'),
                ssh=self.ssh_connection,
                logger=self.ene_logger
            )
        except Exception as e:
            tb = traceback.format_exc()
            logger_message = "Failed to create api user"
            self.ene_logger.log_issue(
                external_message=logger_message,
                internal_message=logger_message,
                api_response=e.args,
                details=tb,
                code=3008,
                category=0
            )

    def serial_check(self):
        self.fortigate = Fortigate(self.ip, self.api_key, self.ene_logger)
        self.fortigate.get_system_status()
        if self.fortigate.serial is None:
            logger_message = "Automation was able to create an ssh connection to the device, but was not able get system status using REST calls. Please ensure HTTPS traffic is enabled"
            self.ene_logger.log_issue(
                external_message=logger_message,
                internal_message=logger_message,
                code=3998,
                category=2
            )

        if self.fortigate.serial != self.serial:
            error_message = f"FortiGate serial number does not match the serial number provided. {self.serial} != { self.fortigate.serial}"
            self.ene_logger.log_issue(
                external_message=error_message,
                internal_message=error_message,
                code=3005,
                category=2
            )

    def upgrade_firmware(self):
        result = upgrade_firmware_fortiguard(
            fortigate=self.fortigate,
            logger=self.ene_logger,
            target_version=self.private_vars.get("FORTIGATE_FIRMWARE", "7.4.8")
        )
        if not result:
            msg = 'Failed to upgrade system firmware. Please update manually and reattempt.'
            self.ene_logger.log_issue(
                external_message=msg,
                internal_message=msg,
                code=2040,
                category=2
            )

    def apply_base_script(self):
        base_config = load_base_config(
            private_vars=self.private_vars,
            model=self.fortigate.model
        )
        if not base_config:
            internal_message = 'Failed to load base config'
            external_message = f'Failed to load base config for model {self.fortigate.model}'
            self.ene_logger.log_issue(
                external_message=external_message,
                internal_message=internal_message,
                code=2006,
                category=0
            )
            return
        responses = send_cli_commands(
            configs=[base_config],
            ssh_connection=self.ssh_connection,
        )
        if did_encounter_error(responses):
            message = 'Errors occurred when applying base config'
            self.ene_logger.log_issue(
                external_message=message,
                internal_message=message,
                api_response=responses,
                details=base_config,
                code=2600,
                category=0
            )

    def onboard_device(self):
        utm_status = 'NO_UTM'
        description = '{}-{}-{}-{}'.format(
            self.state, utm_status, self.tid, self.fortigate.model)
        onboard_parameters = {
            'serial': self.fortigate.serial,
            'ip': self.ip,
            'key': self.api_key,
            'description': description,
            'forticare_api_id': self.private_vars.get('FORTICARE_API_ID'),
            'forticare_api_password': self.private_vars.get('FORTICARE_API_PASSWORD'),
            'forticare_client_id': self.private_vars.get('FORTICARE_CLIENT_ID'),
            'forticloud_api_id': self.private_vars.get('FORTICLOUD_API_ID'),
            'forticloud_api_password': self.private_vars.get('FORTICLOUD_API_PASSWORD'),
            'forticloud_account': self.private_vars.get('FORTICLOUD_ACCOUNT'),
            'forticloud_password': self.private_vars.get('FORTICLOUD_PASSWORD'),
            'logger': self.ene_logger,
            'cloudkey': self.cloudkey,
            'license': self.cloud_license
        }
        onboard(**onboard_parameters)

    def apply_interface_configs(self):
        for i, interface in enumerate(self.interfaces):
            errors = handle_interface(
                interface_payload=interface,
                fortigate=self.fortigate,
                logger=self.ene_logger,
            )
            if errors:
                self.ene_logger.log_issue(
                    external_message=f'failed to apply interface configs for interface {i}',
                    internal_message='failed to apply interface configs',
                    api_response="",
                    details=f"{errors}",
                    code=2018,
                    category=0
                )
        errors = disable_unused_interfaces(self.used_interfaces, self.fortigate, logger=self.ene_logger)
        if len(errors) > 0:
            message = 'failed to disable some unused interfaces'
            self.ene_logger.log_issue(
                external_message=message,
                internal_message=message,
                api_response=errors,
                details=f"used_interfaces={self.used_interfaces}",
                code=2000,
                category=0
            )

    def apply_services(self):
        if self.services is not None:
            errors = config_services(
                self.ip, self.api_key, self.ene_logger, self.services)
            if errors:
                message = 'failed to apply services to device'
                self.ene_logger.log_issue(
                    external_message=message,
                    internal_message=message,
                    api_response="",
                    details=f"{errors}",
                    code=2019,
                    category=0
                )
        if self.service_groups is not None:
            errors = config_service_groups(
                self.ip, self.api_key, self.ene_logger, self.service_groups
            )
            if errors:
                message = 'failed to apply service group to device'
                self.ene_logger.log_issue(
                    external_message=message,
                    internal_message=message,
                    api_response="",
                    details=f"{errors}",
                    code=2020,
                    category=0
                )

    def apply_ip_pools(self):
        if self.ippools is not None:
            for ippool in self.ippools:
                self.ene_logger.debug(f"IPPOOL IS\n{json.dumps(ippool, indent=4)}")
                response = self.fortigate.config_firewall_ippool(**ippool)
                if not response:
                    self.ene_logger.log_issue(
                        external_message=f"failed to apply ip pool '{ippool.get('name')}' to device",
                        internal_message='failed to apply ip pools to device',
                        api_response=f"{self.ippools}",
                        code=2021,
                        category=0
                    )

    def apply_vips(self):
        if self.vips:
            for i, vip in enumerate(self.vips):
                vip.update(
                    {'ip': self.ip, 'key': self.api_key, 'logger': self.ene_logger}
                )
                errors = configure_vip(**vip)
                if errors:
                    self.ene_logger.log_issue(
                        external_message=f"failed to apply vip '{i}' to device",
                        internal_message='failed to apply VIP',
                        details=f"vip: {vip}",
                        api_response=f"{errors}",
                        code=2099,
                        category=0
                    )

    def apply_users(self):
        if self.ldap is not None:
            errors = config_ldap_servers(
                self.ip, self.api_key, self.ene_logger, self.ldap
            )
            if errors:
                message = 'failed to apply ldap settings'
                self.ene_logger.log_issue(
                    external_message=message,
                    internal_message=message,
                    details=f"{errors}",
                    code=2022,
                    category=0
                )

        if self.radius is not None:
            errors = config_radius_servers(
                self.ip, self.api_key, self.ene_logger, self.radius
            )
            if errors:
                message = 'failed to apply radius settings'
                self.ene_logger.log_issue(
                    external_message=message,
                    internal_message=message,
                    details=f"{errors}",
                    code=2023,
                    category=0
                )

        if self.user_groups is not None:
            errors = config_user_groups(
                self.ip, self.api_key, self.ene_logger, self.user_groups
            )
            if errors:
                message = 'failed to apply user groups'
                self.ene_logger.log_issue(
                    external_message=message,
                    internal_message=message,
                    details=f"{errors}",
                    code=2024,
                    category=0
                )

    def apply_webfilters(self):
        errors = config_default_webfilter(self.ip, self.api_key, self.ene_logger)
        if errors:
            message = "failed to apply default webfilters"
            self.ene_logger.log_issue(
                external_message=message,
                internal_message=message,
                details=f"{errors}",
                code=2028,
                category=0
            )

    def apply_routing(self):
        if self.static_routes is not None:
            self.static_routes.update(
                {'ip': self.ip, 'key': self.api_key, 'logger': self.ene_logger})
            errors = config_static_routes(**self.static_routes)
            if errors:
                message = "failed to apply routing settings"
                self.ene_logger.log_issue(
                    external_message=message,
                    internal_message=message,
                    details=f"{errors}",
                    code=2030,
                    category=0
                )

        if self.ospf is not None:
            self.ospf.update(
                {'ip': self.ip, 'key': self.api_key, 'logger': self.ene_logger})
            errors = config_ospf(**self.ospf)
            if errors:
                message = "failed to apply OSPF settings"
                self.ene_logger.log_issue(
                    external_message=message,
                    internal_message=message,
                    details=f"{errors}",
                    code=2031,
                    category=0
                )

        if self.bgp is not None:
            self.bgp.update(
                {'ip': self.ip, 'key': self.api_key, 'logger': self.ene_logger})
            errors = config_bgp(**self.bgp)
            if errors:
                message = "failed to apply BGP settings"
                self.ene_logger.log_issue(
                    external_message=message,
                    internal_message=message,
                    details=f"{errors}",
                    code=2032,
                    category=0
                )

    def apply_firewall_policies(self):
        if self.firewall_policies is not None:
            errors = config_firewall_policy(
                self.ip, self.api_key, self.ene_logger, self.firewall_policies
            )
            if errors:
                message = "failed to apply some firewall policies"
                self.ene_logger.log_issue(
                    external_message=message,
                    internal_message=message,
                    details=f"{errors}",
                    code=2033,
                    category=0
                )

    def clean_up_users(self):
        """
        delete the API user and the admin user
        also ensure that the msod user has the right password set
        """
        self.ene_logger.info("----- Deleting API user -----")
        success = delete_system_api_user(
            ssh=self.ssh_connection,
            logger=self.ene_logger
        )
        if not success:
            message = "Failed to delete API user"
            self.ene_logger.log_issue(
                external_message=message,
                internal_message=message,
                code=2036,
                category=0
            )

        self.ene_logger.info(f"----- Setting new password for {self.main_username} -----")
        set_user_password_script = set_user_password(username=self.main_username, password_enc=self.main_password_hash)
        script_lines = set_user_password_script.split("\n")
        response = self.ssh_connection.send_commands(script_lines)
        if did_encounter_error(response):
            message = f"Failed to set new password for {self.main_username}"
            self.ene_logger.log_issue(
                external_message=message,
                internal_message=message,
                code=2037,
                category=0
            )

        if self.ssh_connection.username != self.main_username:
            # log out of the current ssh connection if we are still logged into admin
            self.ene_logger.info(f"----- Logging out of admin and logging back into {self.main_username} -----")
            self.ssh_connection.close_connection()
            del self.ssh_connection
            time.sleep(1)
            try:
                self.ene_logger.logger.info(f"Attempting to create ssh connection with {self.main_username}")
                self.ssh_connection = SSHConnection(
                    username=self.main_username,
                    password=self.main_pw,
                    hostname=self.ip,
                    logger=self.ene_logger
                )
                return  # if that did not throw an exception then we are logged in
            except Exception:
                tb = traceback.format_exc()
                message = "Failed to create SSH connection to delete admin user."
                self.ene_logger.log_issue(
                    external_message=message,
                    internal_message=message,
                    details=tb,
                    code=3210,
                    category=0
                )

        self.ene_logger.info("----- Deleting user admin -----")
        delete_user_script = del_admin_script()
        script_lines = delete_user_script.split("\n")
        response = self.ssh_connection.send_commands(script_lines)
        if did_encounter_error(response):
            self.ene_logger.log_issue(
                external_message="Failed to delete admin user profile",
                internal_message="Failed to delete admin user profile",
                api_response=response,
                details=None,
                code=2000,
                category=0
            )


class Terminate(CommonPlan):
    def process(self):
        pass
