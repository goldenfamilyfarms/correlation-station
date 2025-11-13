import json
from base64 import b64encode
from time import sleep

import requests
from requests.exceptions import (
    ConnectionError, ConnectTimeout, HTTPError, ReadTimeout)
from requests.packages.urllib3 import disable_warnings
from .utilities import get_model
JSONDecodeError = Exception

__version__ = '1.0.0'

disable_warnings()

'''
This module provides an easy way to interact with the FortiOS v7.0.5 REST API.
Additional methods and functionality is added as needed.

Every POST/PUT/DELETE request is followed by a GET to ensure that the Fortigate
object stays in sync with the actual device configuration.

Recommend to use fortigate.get_system_status() after instantiating a Fortigate.
This will ensure you have the correct device model, serial, and firmware.

Official FortiOS API documentation:
https://fndn.fortinet.net/index.php?/fortiapi/1-fortios/91/

'''


class Fortigate:
    def __init__(self, ip, key, logger, port=443):
        self.antivirus_settings = None
        self.config_url = 'https://{}:{}/api/v2/cmdb'.format(ip, str(port))
        self.firewall_addresses = None
        self.firewall_addrgrps = None
        self.firewall_ippools = None
        self.firewall_local_in_policies = None
        self.firewall_policies = None
        self.firewall_vips = None
        self.firewall_vipgrps = None
        self.firewall_custom_services = None
        self.firewall_service_groups = None
        self.firewall_shaper_traffic_shapers = None
        self.firmware = None
        self.firmware_build = None
        self.firmware_major = None
        self.firmware_minor = None
        self.firmware_patch = None
        self.forticloud = False
        self.forticloud_errors = 0
        self.forticloud_token = None
        self.hostname = None
        self.ip = ip
        self.ips_global = None
        self.ips_sensors = None
        self.key = key
        self.licenses = None
        self.logger = logger
        self.log_disk = None
        self.log_fortiguard_setting = None
        self.log_syslogd_setting = None
        self.model = None
        self.monitor_url = 'https://{}:{}/api/v2/monitor'.format(ip, str(port))
        self.port = port
        self.router_access_lists = None
        self.router_bgp = None
        self.router_ospf = None
        self.router_policy = None
        self.router_prefix_lists = None
        self.router_route_maps = None
        self.router_static = None
        self.serial = None
        self.switch_controller_fortilink_settings = None
        self.switch_controller_initial_config_templates = None
        self.switch_controller_initial_config_vlans = None
        self.switch_controller_lldp_profiles = None
        self.switch_controller_managed_switches = None
        self.switch_controller_snmp_community = None
        self.switch_controller_stp_instances = None
        self.switch_controller_stp_settings = None
        self.system_accprofiles = None
        self.system_admins = None
        self.system_api_users = None
        self.system_auto_scripts = None
        self.system_automation_actions = None
        self.system_automation_stitches = None
        self.system_automation_triggers = None
        self.system_autoupdate_push = None
        self.system_autoupdate_schedule = None
        self.system_central_management = None
        self.system_config_revisions = None
        self.system_config_scripts = None
        self.system_console = None
        self.system_dhcp_servers = None
        self.system_dhcp6_servers = None
        self.system_dscp_based_priority = None
        self.system_firmware_upgrade_paths = None
        self.system_fortiguard = None
        self.system_global = None
        self.system_gre_tunnels = None
        self.system_ha = None
        self.system_interfaces = None
        self.system_link_monitors = None
        self.system_ntp = None
        self.system_session_helpers = None
        self.system_settings = None
        self.system_snmp_community = None
        self.system_snmp_sysinfo = None
        self.system_snmp_users = None
        self.system_switch_interfaces = None
        self.system_vdoms = None
        self.system_virtual_switches = None
        self.system_zones = None
        self.user_groups = None
        self.user_ldap = None
        self.user_local = None
        self.user_radius = None
        self.user_tacacs = None
        self.voip_profiles = None
        self.vpn_ipsec_phase1_interfaces = None
        self.vpn_ipsec_phase2_interfaces = None
        self.vpn_ssl_realms = None
        self.vpn_ssl_settings = None
        self.vpn_ssl_web_portals = None
        self.webfilter_ftgd_local_cats = None
        self.webfilter_urlfilters = None
        self.webfilter_profiles = None
        self.wireless_controller_global = None
        self.wireless_controller_setting = None

    def get_antivirus_settings(self, format=None, vdom=None):
        response = self.send_request(
            '{}/antivirus/settings'.format(self.config_url), format=format,
            vdom=vdom)
        if response is not None:
            self.antivirus_settings = response['results']
        return response

    def get_firewall_addresses(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/firewall/address'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.firewall_addresses = response['results']
        return response

    def get_firewall_addrgrps(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/firewall/addrgrp'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.firewall_addrgrps = response['results']
        return response

    def get_firewall_ippools(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/firewall/ippool'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.firewall_ippools = response['results']
        return response

    def get_firewall_local_in_policies(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/firewall/local-in-policy'.format(self.config_url),
            filter=filter, format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.firewall_local_in_policies = response['results']
        return response

    def get_firewall_policies(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/firewall/policy'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.firewall_policies = response['results']
        return response

    def get_firewall_vips(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/firewall/vip'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.firewall_vips = response['results']
        return response

    def get_firewall_vipgrps(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/firewall/vipgrp'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.firewall_vipgrps = response['results']
        return response

    def get_firewall_custom_services(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/firewall.service/custom'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.firewall_custom_services = response['results']
        return response

    def get_firewall_service_groups(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/firewall.service/group'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.firewall_service_groups = response['results']
        return response

    def get_firewall_shaper_traffic_shapers(self, vdom=None):
        response = self.send_request(
            '{}/firewall.shaper/traffic-shaper'.format(self.config_url),
            vdom=vdom)
        if response is not None:
            self.firewall_shaper_traffic_shapers = response['results']
        return response

    def get_ips_global(self, format=None):
        response = self.send_request(
            '{}/ips/global'.format(self.config_url), format=format)
        if response is not None:
            self.ips_global = response['results']
        return response

    def get_ips_sensors(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/ips/sensor'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.ips_sensors = response['results']
        return response

    def get_licenses(self):
        response = self.send_request(
            '{}/license/status'.format(self.monitor_url))
        if response is not None:
            self.licenses = response['results']
        return response

    def get_forticloud_registration(self):
        response = self.send_request(
            '{}/registration/forticloud/device-status'.format(
                self.monitor_url))
        return response

    def get_log_fortiguard_setting(self, format=None, vdom=None):
        response = self.send_request(
            '{}/log.fortiguard/setting'.format(self.config_url), format=format,
            vdom=vdom)
        if response is not None:
            self.log_fortiguard_setting = response['results']
        return response

    def get_log_syslogd_setting(self, format=None):
        response = self.send_request(
            '{}/log.syslogd/setting'.format(self.config_url), format=format)
        if response is not None:
            self.log_syslogd_setting = response['results']
        return response

    def get_routing_table(self, start=None, vdom=None):
        response = self.send_request(
            '{}/router/ipv4'.format(self.monitor_url), start=start, vdom=vdom)
        return response['results']

    def get_system_ntp(
            self, filter=None, format=None, sort=None, start=None):
        response = self.send_request(
            '{}/system/ntp'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start)
        if response is not None:
            self.system_ntp = response['results']
        return response

    def get_router_access_lists(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/router/access-list'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.router_access_lists = response['results']
        return response

    def get_router_bgp(
            self, format=None, vdom=None):
        response = self.send_request(
            '{}/router/bgp'.format(self.config_url), format=format, vdom=vdom)
        if response is not None:
            self.router_bgp = response['results']
        return response

    def get_router_ospf(
            self, format=None, vdom=None):
        response = self.send_request(
            '{}/router/ospf'.format(self.config_url), format=format, vdom=vdom)
        if response is not None:
            self.router_ospf = response['results']
        return response

    def get_router_policy(
            self, filter=None, format=None, vdom=None):
        response = self.send_request(
            '{}/router/policy'.format(self.config_url), filter=filter,
            format=format, vdom=vdom)
        if response is not None:
            self.router_policy = response['results']
        return response

    def get_router_prefix_lists(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/router/prefix-list'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.router_prefix_lists = response['results']
        return response

    def get_router_route_maps(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/router/route-map'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.router_route_maps = response['results']
        return response

    def get_router_static(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/router/static'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.router_static = response['results']
        return response

    def get_switch_controller_fortilink_settings(self, vdom=None):
        response = self.send_request(
            '{}/switch-controller/fortilink-settings'.format(
                self.config_url), vdom=vdom)
        if response is not None:
            self.switch_controller_fortilink_settings = response['results']
        return response

    def get_switch_controller_fsw_firmware(self, vdom=None):
        response = self.send_request(
            '{}/switch-controller/fsw-firmware'.format(self.monitor_url),
            vdom=vdom)
        return response.get('results')

    def get_switch_controller_initial_config_templates(self, vdom=None):
        response = self.send_request(
            '{}/switch-controller.initial-config/template'.format(
                self.config_url), vdom=vdom)
        if response is not None:
            self.switch_controller_initial_config_templates = response['results']
        return response

    def get_switch_controller_initial_config_vlans(self, vdom=None):
        response = self.send_request(
            '{}/switch-controller.initial-config/vlans'.format(
                self.config_url), vdom=vdom)
        if response is not None:
            self.switch_controller_initial_config_vlans = response['results']
        return response

    def get_switch_controller_lldp_profiles(self, vdom=None):
        response = self.send_request(
            '{}/switch-controller/lldp-profile'.format(self.config_url),
            vdom=vdom)
        if response is not None:
            self.switch_controller_lldp_profiles = response['results']
        return response

    def get_switch_controller_managed_switches(self, vdom=None):
        response = self.send_request(
            '{}/switch-controller/managed-switch'.format(self.config_url),
            vdom=vdom)
        if response is not None:
            self.switch_controller_managed_switches = response['results']
        return response

    def get_switch_controller_managed_switch_models(self, vdom=None):
        response = self.send_request(
            '{}/switch-controller/managed-switch/models'.format(
                self.monitor_url),
            vdom=vdom)
        return response.get('results')

    def get_switch_controller_managed_switch_status(self, vdom=None):
        response = self.send_request(
            '{}/switch-controller/managed-switch/status'.format(
                self.monitor_url),
            vdom=vdom)
        return response.get('results')

    def get_switch_controller_snmp_community(self, vdom=None):
        response = self.send_request(
            '{}/switch-controller/snmp-community'.format(self.config_url),
            vdom=vdom)
        if response is not None:
            self.switch_controller_snmp_community = response['results']
        return response

    def get_switch_controller_stp_instances(self, vdom=None):
        response = self.send_request(
            '{}/switch-controller/stp-instance'.format(self.config_url),
            vdom=vdom)
        if response is not None:
            self.switch_controller_stp_instances = response['results']
        return response

    def get_switch_controller_stp_settings(self, vdom=None):
        response = self.send_request(
            '{}/switch-controller/stp-settings'.format(self.config_url),
            vdom=vdom)
        if response is not None:
            self.switch_controller_stp_settings = response['results']
        return response

    def get_system_accprofiles(
            self, filter=None, format=None, sort=None, start=None):
        response = self.send_request(
            '{}/system/accprofile'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start)
        if response is not None:
            self.system_accprofiles = response['results']
        # else:
        #     s
        return response

    def get_system_admins(
            self, filter=None, format=None, sort=None, start=None):
        response = self.send_request(
            '{}/system/admin'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start)
        if response is not None:
            self.system_admins = response['results']
        return response

    def get_system_auto_scripts(self, vdom=None):
        response = self.send_request(
            '{}/system/auto-script'.format(self.config_url), vdom=None)
        if response is not None:
            self.system_auto_scripts = response['results']
        return response

    def get_system_automation_actions(self, vdom=None):
        response = self.send_request(
            '{}/system/automation-action'.format(self.config_url), vdom=None)
        if response is not None:
            self.system_automation_actions = response['results']
        return response

    def get_system_automation_stitches(self, vdom=None):
        response = self.send_request(
            '{}/system/automation-stitch'.format(self.config_url), vdom=None)
        if response is not None:
            self.system_automation_stitches = response['results']
        return response

    def get_system_automation_triggers(self, vdom=None):
        response = self.send_request(
            '{}/system/automation-trigger'.format(self.config_url), vdom=None)
        if response is not None:
            self.system_automation_triggers = response['results']
        return response

    def get_system_available_interfaces(self, vdom=None):
        response = self.send_request(
            '{}/system/available-interfaces'.format(self.monitor_url),
            vdom=vdom)
        return response['results']

    def get_system_central_management(self, format=None):
        response = self.send_request(
            '{}/system/central-management'.format(self.config_url),
            format=format)
        if response is not None:
            self.system_central_management = response['results']
        return response

    def get_system_config_revisions(self):
        response = self.send_request(
            '{}/system/config-revision'.format(self.monitor_url))
        if response is not None:
            self.system_config_revisions = response['results']
        return response

    def get_system_config_scripts(self):
        response = self.send_request(
            '{}/system/config-script'.format(self.monitor_url))
        if response is not None:
            self.system_config_scripts = response['results']
        return response

    def get_system_console(self, format=None):
        response = self.send_request(
            '{}/system/console'.format(self.config_url), format=format)
        if response is not None:
            self.system_console = response['results']
        return response

    def get_system_dhcp_servers(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/system.dhcp/server'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.system_dhcp_servers = response['results']
        return response

    def get_system_dhcp6_servers(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/system.dhcp6/server'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.system_dhcp6_servers = response['results']
        return response

    def get_system_dscp_based_priority(self):
        response = self.send_request(
            '{}/system/dscp-based-priority'.format(self.config_url))
        if response is not None:
            self.system_dscp_based_priority = response['results']
        return response

    def get_system_firmware(self):
        '''
        Retrieve a list of firmware images available to use for upgrade on this
        device.
        '''
        response = self.send_request(
            '{}/system/firmware'.format(self.monitor_url))
        return response

    def get_system_firmware_upgrade_path(self):
        response = self.send_request(
            '{}/system/firmware/upgrade-paths'.format(self.monitor_url))
        return response

    def get_system_fortiguard(self, format=None):
        response = self.send_request(
            '{}/system/fortiguard'.format(self.config_url), format=format)
        if response is not None:
            self.system_fortiguard = response['results']
        return response

    def get_system_global(self, format=None):
        response = self.send_request(
            '{}/system/global'.format(self.config_url), format=format)
        if response is not None:
            self.system_global = response['results']
        return response

    def get_system_gre_tunnels(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/system/gre-tunnel'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.system_gre_tunnels = response['results']
        return response

    def get_system_ha(self, format=None):
        response = self.send_request(
            '{}/system/ha'.format(self.config_url), format=format)
        if response is not None:
            self.system_ha = response['results']
        return response

    def get_system_interfaces(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/system/interface'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.system_interfaces = response['results']
        return response

    def get_system_interface_statistics(self, interface):
        response = self.send_request(
            '{}/system/interface?interface_name={}'.format(self.monitor_url, interface))
        return response['results'][interface]

    def get_system_interface_transceivers(self, vdom=None):
        response = self.send_request(
            '{}/system/interface/transceivers'.format(self.monitor_url),
            vdom=vdom)
        if response is not None:
            self.system_interface_transceivers = response['results']
        return response

    def get_system_link_monitors(
            self, filter=None, format=None, start=None, vdom=None):
        response = self.send_request(
            '{}/system/link-monitor'.format(self.config_url), filter=filter,
            format=format, start=start, vdom=vdom)
        if response is not None:
            self.system_link_monitors = response['results']
        return response

    def get_system_session_helpers(
            self, filter=None, format=None, sort=None, start=None):
        response = self.send_request(
            '{}/system/session-helper'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start)
        if response is not None:
            self.system_session_helpers = response['results']
        return response

    def get_system_settings(self, format=None, vdom=None):
        response = self.send_request(
            '{}/system/settings'.format(self.config_url), format=format,
            vdom=vdom)
        if response is not None:
            self.system_settings = response['results']
        return response

    def get_system_snmp_community(
            self, filter=None, format=None, sort=None, start=None):
        response = self.send_request(
            '{}/system.snmp/community'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start)
        if response is not None:
            self.system_snmp_community = response['results']
        return response

    def get_system_snmp_sysinfo(self, format=None):
        response = self.send_request(
            '{}/system.snmp/sysinfo'.format(self.config_url), format=format)
        if response is not None:
            self.system_snmp_sysinfo = response['results']
        return response

    def get_system_snmp_users(
            self, filter=None, format=None, sort=None, start=None):
        response = self.send_request(
            '{}/system.snmp/user'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start)
        if response is not None:
            self.system_snmp_users = response['results']
        return response

    def get_system_switch_interfaces(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/system/switch-interface'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.system_switch_interfaces = response['results']
        return response

    def get_system_status(self):
        response = self.send_request(
            '{}/system/status'.format(self.monitor_url))
        if response is not None:
            self.firmware = response['version']
            self.firmware_build = response['build']
            self.serial = response['serial']
            try:
                self.hostname = response['results']['hostname']
                self.log_disk = response['results']['log_disk_status']
                self.model = response['results']['model_number']
            except KeyError:
                self.hostname = None
                self.log_disk = None
                self.model = get_model(self.serial)
            levels = self.firmware.replace('v', '').split('.')
            self.firmware_major, self.firmware_minor, self.firmware_patch = levels
        return response

    def get_system_vdoms(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/system/vdom'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.system_vdoms = response['results']
        return response

    def get_system_virtual_switches(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/system/virtual-switch'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.system_virtual_switches = response['results']
        return response

    def get_system_zones(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/system/zone'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.system_zones = response['results']
        return response

    def get_user_groups(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/user/group'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.user_groups = response['results']
        return response

    def get_user_ldap(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/user/ldap'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.user_ldap = response['results']
        return response

    def get_user_local(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/user/local'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.user_local = response['results']
        return response

    def get_user_radius(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/user/radius'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.user_radius = response['results']
        return response

    def get_user_tacacs(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/user/tacacs+'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.user_tacacs = response['results']
        return response

    def get_voip_profiles(self, vdom=None):
        response = self.send_request(
            '{}/voip/profile'.format(self.config_url), vdom=vdom)
        if response is not None:
            self.voip_profiles = response['results']
        return response

    def get_vpn_ipsec_phase1_interfaces(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/vpn.ipsec/phase1-interface'.format(self.config_url),
            filter=filter, format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.vpn_ipsec_phase1_interfaces = response['results']
        return response

    def get_vpn_ipsec_phase2_interfaces(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/vpn.ipsec/phase2-interface'.format(self.config_url),
            filter=filter, format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.vpn_ipsec_phase2_interfaces = response['results']
        return response

    def get_vpn_ssl_realms(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/vpn.ssl.web/realm'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.vpn_ssl_realms = response['results']
        return response

    def get_vpn_ssl_settings(self, format=None, vdom=None):
        response = self.send_request(
            '{}/vpn.ssl/settings'.format(self.config_url), format=format,
            vdom=vdom)
        if response is not None:
            self.vpn_ssl_settings = response['results']
        return response

    def get_vpn_ssl_web_portals(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/vpn.ssl.web/portal'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.vpn_ssl_web_portals = response['results']
        return response

    def get_webfilter_ftgd_local_cats(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/webfilter/ftgd-local-cat'.format(self.config_url),
            filter=filter, format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.webfilter_ftgd_local_cats = response['results']
            self.logger.info(f"Existing webfilter_ftgd_local_cats pulled: {json.dumps(self.webfilter_ftgd_local_cats, indent=2)}")
        else:
            self.logger.info("Failed to pull existing webfilter_ftgd_local_cats")
        return response

    def get_webfilter_profiles(
            self, filter=None, format=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/webfilter/profile'.format(self.config_url), filter=filter,
            format=format, sort=sort, start=start, vdom=vdom)
        if response is not None:
            self.webfilter_profiles = response['results']
        return response

    def get_wireless_controller_global(
            self, filter=None, format=None, start=None, vdom=None):
        response = self.send_request(
            '{}/wireless-controller/global'.format(self.config_url),
            filter=filter, format=format, start=start, vdom=vdom)
        if response is not None:
            self.wireless_controller_global = response['results']
        return response

    def get_wireless_controller_setting(
            self, filter=None, format=None, vdom=None):
        response = self.send_request(
            '{}/wireless-controller/setting'.format(self.config_url),
            filter=filter, format=format, vdom=vdom)
        if response is not None:
            self.wireless_controller_setting = response['results']
        return response

    def change_vdom_mode(self, mode):
        payload = {
            'vdom-mode': mode
        }
        if self.system_global is None:
            self.get_system_global()
        elif self.system_global['vdom-mode'] == mode:
            return None
        response = self.send_request(
            '{}/system/admin/change-vdom-mode'.format(self.monitor_url),
            action='POST', attempts=1, payload=payload)
        self.get_system_global()
        return response

    def config_antivirus_settings(
            self, cache_clean_result='enable', cache_infected_result='enable',
            grayware='enable', machine_learning_detection='enable',
            override_timeout=0):
        payload = {
            'cache-clean-result': cache_clean_result,
            'cache-infected-result': cache_infected_result,
            'grayware': grayware,
            'machine-learning-detection': machine_learning_detection,
            'override-timeout': override_timeout,
            'use-extreme-db': 'disable'
        }
        if self.antivirus_settings is None:
            self.get_antivirus_settings()
        response = self.send_request(
            '{}/antivirus/settings'.format(self.config_url), action='PUT',
            payload=payload, attempts=1, vdom=None)
        self.get_antivirus_settings()
        return response

    def config_firewall_address(
            self, name, allow_routing='disable', associated_interface='',
            color=0, comment='', country='', end_ip='', fqdn='', rename=None,
            start_ip='', subnet='0.0.0.0 0.0.0.0', addr_type='ipmask',
            visibility='enable', macaddr=None, vdom=None):
        url_name = requests.utils.quote(name, safe='')
        payload = {
            'allow-routing': allow_routing,
            'associated-interface': associated_interface,
            'color': color,
            'comment': comment,
            'list': [],
            'name': name,
            'type': addr_type,
            'visibility': visibility
        }
        if addr_type == 'ipmask':
            payload['subnet'] = subnet
        elif addr_type == 'iprange':
            payload['start-ip'] = start_ip
            payload['end-ip'] = end_ip
        elif addr_type == 'fqdn':
            payload['fqdn'] = fqdn
        elif addr_type == 'geography':
            payload['country'] = country
        elif addr_type == 'mac':
            payload['macaddr'] = [{'macaddr': i for i in macaddr}]
        else:
            print('Invalid address type')
            return None
        if rename is not None:
            payload['name'] = rename
        if self.firewall_addresses is None:
            self.get_firewall_addresses(vdom=vdom)
        for entry in self.firewall_addresses:
            if entry['name'] != name:
                continue
            response = self.send_request(
                '{}/firewall/address/{}'.format(self.config_url, url_name),
                action='PUT', payload=payload, attempts=1, vdom=vdom)
            self.get_firewall_addresses(vdom=vdom)
            return response
        else:
            response = self.send_request(
                '{}/firewall/address'.format(self.config_url),
                action='POST', payload=payload, attempts=1, vdom=vdom)
            self.get_firewall_addresses(vdom=vdom)
            return response

    def config_firewall_addrgrp(
            self, name, members, allow_routing='disable', color=0, comment='',
            rename=None, type='default', vdom=None):
        url_name = requests.utils.quote(name, safe='')
        member = [{'name': i} for i in members]
        payload = {
            'allow-routing': allow_routing,
            'color': 0,
            'comment': comment,
            'member': member,
            'name': name,
            'type': type
        }
        if rename is not None:
            payload['name'] = rename
        if self.firewall_addrgrps is None:
            self.get_firewall_addrgrps(vdom=vdom)
        for entry in self.firewall_addrgrps:
            if entry['name'] != name:
                continue
            response = self.send_request(
                '{}/firewall/addrgrp/{}'.format(self.config_url, url_name),
                action='PUT', payload=payload, attempts=1, vdom=vdom)
            self.get_firewall_addrgrps(vdom=vdom)
            return response
        else:
            response = self.send_request(
                '{}/firewall/addrgrp'.format(self.config_url), action='POST',
                payload=payload, attempts=1, vdom=vdom)
            self.get_firewall_addrgrps(vdom=vdom)
            return response

    def config_firewall_ippool(
            self, name, startip, endip, arp_intf='', arp_reply='enable',
            associated_interface=None, block_size=128, comments='',
            num_blocks_per_user=8, pool_type='overload', port_per_user=0,
            source_endip='0.0.0.0', source_startip='0.0.0.0', startport=5117,
            endport=65533, vdom=None):
        payload = {
            'arp-intf': arp_intf,
            'arp-reply': arp_reply,
            'comments': comments,
            'endip': endip,
            'name': name,
            'startip': startip,
            'type': pool_type
        }
        if associated_interface is not None:
            payload['associated-interface'] = associated_interface
        if pool_type == 'fixed-port-range':
            payload['block-size'] = block_size
            payload['source-startip'] = source_startip
            payload['source-endip'] = source_endip
            payload['port-per-user'] = port_per_user
            payload['startport'] = startport
            payload['endport'] = endport
        elif pool_type == 'port-block-allocation':
            payload['block-size'] = block_size
            payload['num-blocks-per-user'] = num_blocks_per_user
        if self.firewall_ippools is None:
            self.get_firewall_ippools(vdom=vdom)
        for i in self.firewall_ippools:
            if i['name'] != name:
                continue
            response = self.send_request(
                '{}/firewall/ippool/{}'.format(self.config_url, name),
                action='PUT', payload=payload, attempts=1, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/firewall/ippool'.format(self.config_url), action='POST',
                payload=payload, attempts=1, vdom=vdom)
        self.get_firewall_ippools(vdom=vdom)
        return response

    def config_firewall_local_in_policy(
            self, services, srcaddr, action='deny', comments='',
            dstaddr=['all'], intf='any', policyid=0, schedule='always',
            status='enable', vdom=None):
        dst = [{'name': i} for i in dstaddr]
        service = [{'name': i} for i in services]
        src = [{'name': i} for i in srcaddr]
        payload = {
            'action': action,
            'comments': comments,
            'dstaddr': dst,
            'intf': intf,
            'policyid': policyid,
            'schedule': schedule,
            'service': service,
            'srcaddr': src,
            'status': status,
        }
        if self.firewall_local_in_policies is None:
            self.get_firewall_local_in_policies(vdom=vdom)
        for entry in self.firewall_local_in_policies:
            if entry['policyid'] != policyid:
                continue
            response = self.send_request(
                f'{self.config_url}/firewall/local-in-policy/{policyid}',
                action='PUT',
                payload=payload,
                attempts=1,
                vdom=vdom
            )
            self.get_firewall_local_in_policies(vdom=vdom)
            return response
        else:
            response = self.send_request(
                '{}/firewall/local-in-policy'.format(self.config_url),
                action='POST', payload=payload, attempts=1, vdom=vdom)
            self.get_firewall_local_in_policies(vdom=vdom)
            return response

    def config_firewall_policy(
            self, srcintf, dstintf, srcaddr, dstaddr, action='deny',
            comments='', groups=None, inspection_mode='flow', logtraffic='utm',
            name=None, nat='disable', policyid=0, poolname=None,
            schedule='always', service=None, ssl_ssh_profile='no-inspection',
            status='enable', traffic_shaper=None, traffic_shaper_reverse=None,
            users=None, utm_status='disable', vdom=None, voip_profile=None):
        wrap_json = False

        srcaddrs = srcaddr
        dstaddrs = dstaddr

        if action == 'deny':
            inspection_mode = None

        if service is None:
            services = [{'name': 'ALL'}]
        else:
            services = service

        if not poolname:
            ippool = "disable"
        else:
            ippool = "enable"

        if groups is not None:
            groups = [{'name': i} for i in groups]

        if users is not None:
            users = [{'name': i} for i in users]

        payload = {
            'action': action,
            'comments': comments,
            'dstaddr': dstaddrs,
            'dstintf': dstintf,
            'groups': groups,
            'inspection-mode': inspection_mode,
            'ippool': ippool,
            'logtraffic': logtraffic,
            'name': name,
            'nat': nat,
            'policyid': policyid,
            'poolname': poolname,
            'schedule': schedule,
            'service': services,
            'srcaddr': srcaddrs,
            'srcintf': srcintf,
            'ssl-ssh-profile': ssl_ssh_profile,
            'status': status,
            'traffic-shaper': traffic_shaper,
            'traffic-shaper-reverse': traffic_shaper_reverse,
            'users': users,
            'utm-status': utm_status,
            'voip-profile': voip_profile
        }

        payload = {k: v for k, v in payload.items() if v not in [None, "", []]}
        if wrap_json:
            payload = {"json": payload}

        response = self.send_request(
            '{}/firewall/policy'.format(self.config_url), action='POST',
            payload=payload, attempts=1, vdom=vdom)
        self.get_firewall_policies(vdom="root")
        return response

    def config_firewall_vip(
            self, extintf, extip, mappedip, arp_reply='enable', color=0,
            comment='', extport=None, mappedport=None, name=None,
            nat_source_vip='disable', protocol=None, vdom=None):
        if name is None:
            name = '{}_{}'.format(extip, mappedip)
            if extport and protocol:
                name += '_{}{}'.format(protocol.upper(), extport)
        portforward = 'enable' if extport and mappedport else 'disable'
        mappedip = [{'range': mappedip}]
        extport = '0-65535' if extport is None else str(extport)
        mappedport = '0-65535' if mappedport is None else str(mappedport)

        payload = {
            'arp-reply': arp_reply,
            'color': color,
            'comment': comment,
            'extintf': extintf,
            'extip': extip,
            'extport': extport,
            'mappedip': mappedip,
            'mappedport': mappedport,
            'name': name,
            'nat-source-vip': nat_source_vip,
            'portforward': portforward,
            'portmapping-type': '1-to-1',
            'protocol': protocol,
            'type': 'static-nat'
        }
        if self.firewall_vips is None:
            self.get_firewall_vips(vdom=vdom)
        for entry in self.firewall_vips:
            if entry['name'] != name:
                continue
            response = self.send_request(
                '{}/firewall/vip/{}'.format(self.config_url, name),
                action='PUT', payload=payload, attempts=1, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/firewall/vip'.format(self.config_url), action='POST',
                payload=payload, attempts=1, vdom=vdom)
        self.get_firewall_vips(vdom=vdom)
        return response

    def config_firewall_vipgrp(
            self, name, interface, members, color=0, comments='', vdom=None):
        member = [{'name': i} for i in members]
        payload = {
            'color': color,
            'comments': comments,
            'interface': interface,
            'member': member,
            'name': name
        }
        if self.firewall_vipgrps is None:
            self.get_firewall_vipgrps(vdom=vdom)
        for entry in self.firewall_vipgrps:
            if entry['name'] != name:
                continue
            response = self.send_request(
                '{}/firewall/vipgrp/{}'.format(self.config_url, name),
                action='PUT', payload=payload, attempts=1, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/firewall/vipgrp'.format(self.config_url), action='POST',
                payload=payload, attempts=1, vdom=vdom)
        self.get_firewall_vipgrps(vdom=vdom)
        return response

    def config_firewall_custom_service(
            self, name, category='', color=0, comment='',
            protocol='TCP/UDP/SCTP', tcp_portrange='', udp_portrange='',
            icmptype='', icmpcode='', protocol_number=0,
            vdom=None):
        payload = {
            'category': category,
            'color': color,
            'comment': comment,
            'name': name,
            'protocol': protocol,
        }
        if 'TCP/UDP' in protocol.upper():
            payload['tcp-portrange'] = tcp_portrange
            payload['udp-portrange'] = udp_portrange
        elif protocol == 'UDP':
            payload['udp-portrange'] = udp_portrange
        elif protocol == "TCP":
            payload['tcp-portrange'] = tcp_portrange
        elif protocol == 'ICMP':
            payload['icmptype'] = icmptype
            payload['icmpcode'] = icmpcode
        elif protocol == 'IP':
            payload['protocol-number'] = protocol_number

        if self.firewall_custom_services is None:
            self.get_firewall_custom_services(vdom=vdom)
        if self.firewall_custom_services is None:
            return None
        for entry in self.firewall_custom_services:
            if entry['name'] != name:
                continue
            response = self.send_request(
                '{}/firewall.service/custom/{}'.format(self.config_url, name),
                action='PUT', payload=payload, attempts=1, vdom=vdom)
            self.get_firewall_custom_services(vdom=vdom)
            return response
        else:
            response = self.send_request(
                '{}/firewall.service/custom'.format(self.config_url),
                action='POST', payload=payload, attempts=1, vdom=vdom)
            self.get_firewall_custom_services(vdom=vdom)
            return response

    def config_firewall_service_group(
            self, name, member, comment='', color=0, fabric_object='disable',
            proxy='disable', vdom=None):
        members = [{'name': i} for i in member if member is not None]
        payload = {
            'name': name,
            'member': members,
            'comment': comment,
            'color': color,
            'fabric-object': fabric_object,
            'proxy': proxy
        }
        if self.firewall_service_groups is None:
            self.get_firewall_service_groups(vdom=vdom)
        for entry in self.firewall_service_groups:
            if entry['name'] != name:
                continue
            response = self.send_request(
                '{}/firewall.service/group/{}'.format(self.config_url, name),
                action='PUT', payload=payload, attempts=1, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/firewall.service/group'.format(self.config_url),
                action='POST', payload=payload, attempts=1, vdom=vdom)
        self.get_firewall_service_groups(vdom=vdom)
        return response

    def config_firewall_shaper_traffic_shaper(
            self, name, bandwidth_unit='kbps', diffserv='disable',
            diffservcode='000000', dscp_marking_method='static',
            exceed_bandwidth=0, exceed_class_id=0, exceed_dscp='000000',
            guaranteed_bandwidth=0, maximum_bandwidth=0, maximum_dscp='000000',
            overhead=0, per_policy='disable', priority='high', vdom=None):
        payload = {
            'name': name,
            'bandwidth-unit': bandwidth_unit,
            'diffserv': diffserv,
            'guaranteed-bandwidth': guaranteed_bandwidth,
            'maximum-bandwidth': maximum_bandwidth,
            'overhead': overhead,
            'per-policy': per_policy,
            'priority': priority
        }
        if diffserv == 'enable':
            payload['diffservcode'] = diffservcode
            payload['dscp-marking-method'] = dscp_marking_method
        if dscp_marking_method == 'multi-stage':
            payload['exceed-bandwidth'] = exceed_bandwidth
            payload['exceed-dscp'] = exceed_dscp
            payload['maximum-dscp'] = maximum_dscp
            payload['exceed-class-id'] = exceed_class_id

        if self.firewall_shaper_traffic_shapers is None:
            self.get_firewall_shaper_traffic_shapers(vdom=vdom)
        for entry in self.firewall_shaper_traffic_shapers:
            if entry['name'] != name:
                continue
            response = self.send_request(
                '{}/firewall.shaper/traffic-shaper/{}'.format(
                    self.config_url, name),
                action='PUT', payload=payload, attempts=1, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/firewall.shaper/traffic-shaper'.format(self.config_url),
                action='POST', payload=payload, attempts=1, vdom=vdom)
        self.get_firewall_shaper_traffic_shapers(vdom=vdom)
        return response

    def config_ips_global(self, traffic_submit='enable'):
        payload = {
            'traffic-submit': traffic_submit
        }
        if self.ips_global is None:
            self.get_ips_global()
        response = self.send_request(
            '{}/ips/global'.format(self.config_url), action='PUT',
            payload=payload, attempts=1)
        self.get_ips_global()
        return response

    def config_ips_sensor(
            self, name, entries, block_malicious_url='disable', comment='',
            extended_log='disable', replacemsg_group='',
            scan_botnet_connections='disable', vdom=None):
        payload = {
            'block-malicious-url': block_malicious_url,
            'comment': comment,
            'entries': entries,
            'extended-log': extended_log,
            'name': name,
            'replacemsg-group': replacemsg_group,
            'scan-botnet-connections': scan_botnet_connections
        }

        if self.ips_sensors is None:
            self.get_ips_sensors(vdom=vdom)
        for sensor in self.ips_sensors:
            if sensor['name'] != name:
                continue
            response = self.send_request(
                '{}/ips/sensor/{}'.format(self.config_url, name), action='PUT',
                payload=payload, attempts=1, vdom=vdom)
            self.get_ips_sensors(vdom=vdom)
            return response
        else:
            response = self.send_request(
                '{}/ips/sensor'.format(self.config_url), action='POST',
                payload=payload, attempts=1, vdom=vdom)
            self.get_ips_sensors(vdom=vdom)
            return response

    def config_log_fortiguard_setting(
            self, access_config='enable', conn_timeout=10, enc_algorithm='high',
            interface='', interface_select_method='auto', max_log_rate=0,
            priority='default', source_ip='0.0.0.0',
            ssl_min_proto_version='default', status='enable', upload_day='',
            upload_interval='daily', upload_option='5-minute',
            upload_time='00:00'):
        payload = {
            'access-config': access_config,
            'conn-timeout': conn_timeout,
            'enc-algorithm': enc_algorithm,
            'interface': interface,
            'interface-select-method': interface_select_method,
            'max-log-rate': max_log_rate,
            'priority': priority,
            'source-ip': source_ip,
            'ssl-min-proto-version': ssl_min_proto_version,
            'status': status,
            'upload-day': upload_day,
            'upload-interval': upload_interval,
            'upload-option': upload_option,
            'upload-time': upload_time
        }
        if self.log_fortiguard_setting is None:
            self.get_log_fortiguard_setting()
        response = self.send_request(
            '{}/log.fortiguard/setting'.format(self.config_url), action='PUT',
            payload=payload, attempts=1)
        self.get_log_fortiguard_setting()
        return response

    def config_log_syslogd_setting(
            self, server, certificate='', custom_field_name=None,
            enc_algorithm='disable', facility='local7', format='default',
            interface='', interface_select_method='auto', max_log_rate=0,
            mode='udp', port=514, priority='default', source_ip='',
            ssl_min_proto_version='default', status='disable', syslog_type=1):
        if custom_field_name is None:
            custom_field_name = []
        payload = {
            'certificate': certificate,
            'custom-field-name': custom_field_name,
            'enc-algorithm': enc_algorithm,
            'facility': facility,
            'format': format,
            'interface': interface,
            'interface-select-method': interface_select_method,
            'max-log-rate': max_log_rate,
            'mode': mode,
            'port': port,
            'priority': priority,
            'server': server,
            'source-ip': source_ip,
            'ssl-min-proto-version': ssl_min_proto_version,
            'status': 'disable',
            'syslog-type': syslog_type
        }
        if self.log_syslogd_setting is None:
            self.get_log_syslogd_setting()
        response = self.send_request(
            '{}/log.syslogd/setting'.format(self.config_url), action='PUT',
            payload=payload, attempts=1)
        self.get_log_syslogd_setting()
        return response

    def config_router_access_list(self, name, rules, comments='', vdom=None):
        payload = {
            'comments': comments,
            'name': name,
            'rule': rules
        }
        if self.router_access_lists is None:
            self.get_router_access_lists(vdom=vdom)
        for i in self.router_access_lists:
            if i['name'] != name:
                continue
            response = self.send_request(
                '{}/router/access-list/{}'.format(self.config_url, name),
                action='PUT', attempts=1, payload=payload, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/router/access-list'.format(self.config_url), action='POST',
                attempts=1, payload=payload, vdom=vdom)
        self.get_router_access_lists(vdom=vdom)
        return response

    def config_router_bgp(
            self, autonomous_system, router_id, default_local_preference=100,
            graceful_restart='disable', log_neighbour_changes='enable',
            neighbors=None, neighbor_groups=None, neighbor_ranges=None,
            networks=None, redistribute_ospf='disable',
            redistribute_ospf_route_map='', redistribute_static='disable',
            redistribute_static_route_map='',
            vdom=None):
        if neighbors is None:
            neighbors = []
        if neighbor_groups is None:
            neighbor_groups = []
        if neighbor_ranges is None:
            neighbor_ranges = []
        if networks is None:
            networks = []

        redistribute = [
            {
                'name': 'ospf',
                'status': redistribute_ospf,
                'route-map': redistribute_ospf_route_map
            },
            {
                'name': 'static',
                'status': redistribute_static,
                'route-map': redistribute_static_route_map
            },
        ]

        payload = {
            'as': autonomous_system,
            'router-id': router_id,
            'default-local-preference': default_local_preference,
            'graceful-restart': graceful_restart,
            'log-neighbour-changes': log_neighbour_changes,
            'neighbor': neighbors,
            'neighbor-group': neighbor_groups,
            'neighbor-range': neighbor_ranges,
            'network': networks,
            'redistribute': redistribute
        }

        self.logger.info("Inside config_bgp() This is the payload being sent to: /router/bgp ")

        if self.router_bgp is None:
            self.logger.info("Inside config_bgp() router_bgp is none... ")
            self.get_router_bgp(vdom=vdom)

        response = self.send_request(
            '{}/router/bgp'.format(self.config_url), action='PUT', attempts=1,
            payload=payload, vdom=vdom)
        self.get_router_bgp(vdom=vdom)
        return response

    def config_router_ospf(
            self, areas=None, auto_cost_ref_bandwidth=1000,
            default_information_metric=10, default_information_metric_type=2,
            default_information_originate='disable',
            default_information_route_map='', default_metric=10, distance=110,
            distribute_list=None, distribute_list_in='',
            distribute_route_map_in='', networks=None, interfaces=None,
            passive_interfaces=None, redistribute=None, router_id='',
            summary_address=None, vdom=None):
        area = [] if areas is None else areas
        interface = [] if interfaces is None else interfaces
        network = [] if networks is None else networks
        passive_interface = [] if passive_interfaces is None else passive_interfaces
        distribute_list = [] if distribute_list is None else distribute_list
        redistribute = [] if redistribute is None else redistribute
        summary = [] if summary_address is None else summary_address
        payload = {
            'area': area,
            'auto-cost-ref-bandwidth': auto_cost_ref_bandwidth,
            'default-information-metric': default_information_metric,
            'default-information-metric-type': default_information_metric_type,
            'default-information-originate': default_information_originate,
            'default-information-route-map': default_information_route_map,
            'default-metric': default_metric,
            'distance': distance,
            'distribute-list': distribute_list,
            'distribute-list-in': distribute_list_in,
            'distribute-route-map-in': distribute_route_map_in,
            'network': network,
            'ospf-interface': interface,
            'passive-interfaces': passive_interface,
            'redistribute': redistribute,
            'router-id': router_id,
            'summary-address': summary,
        }
        if self.router_ospf is None:
            self.get_router_ospf(vdom=vdom)
        response = self.send_request(
            '{}/router/ospf'.format(self.config_url), action='PUT', attempts=1,
            payload=payload, vdom=vdom)
        self.get_router_ospf(vdom=vdom)
        return response

    def config_router_policy(
            self, action='permit', comment='', dst=None, dstaddr=None,
            dst_negate='disable', end_port=65535, end_source_port=65535,
            entry=0, gateway='0.0.0.0', input_device=None,
            input_device_negate='disable', internet_service_custom=None,
            internet_service_id=None, output_device='', protocol=0, src=None,
            srcaddr=None, start_port=0, start_source_port=0, status='enable',
            tos='0x00', tos_mask='0x00', vdom=None):
        dsts = [] if dst is None else [{'subnet': i} for i in dst]
        dstaddrs = [] if dstaddr is None else [{'name': i} for i in dstaddr]
        input_devices = [] if input_device is None else [
            {'name': i} for i in input_device]
        isdb_custom = [] if internet_service_custom is None else [
            {'name': i} for i in internet_service_custom]
        isdb = [] if internet_service_id is None else [
            {'id': i} for i in internet_service_id]
        srcs = [] if src is None else [{'subnet': i} for i in src]
        srcaddrs = [] if srcaddr is None else [{'name': i} for i in srcaddr]

        payload = {
            'action': action,
            'comments': comment,
            'dst': dsts,
            'dstaddr': dstaddrs,
            'dst-negate': dst_negate,
            'seq-num': entry,
            'input-device': input_devices,
            'input-device-negate': input_device_negate,
            'internet-service-custom': isdb_custom,
            'internet-service-id': isdb,
            'output-device': output_device,
            'protocol': protocol,
            'src': srcs,
            'srcaddr': srcaddrs,
            'status': status,
            'tos': tos,
            'tos-mask': tos_mask
        }
        if action == 'permit':
            payload['gateway'] = gateway
        if protocol in [6, 17, 132]:
            payload['end-port'] = end_port
            payload['end-source-port'] = end_source_port
            payload['start-port'] = start_port
            payload['start-source-port'] = start_source_port

        if self.router_policy is None:
            self.get_router_policy(vdom=vdom)
        for i in self.router_policy:
            if i['seq-num'] != entry:
                continue
            response = self.send_request(
                '{}/router/policy/{}'.format(self.config_url, entry),
                action='PUT', attempts=1, payload=payload, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/router/policy'.format(self.config_url), action='POST',
                attempts=1, payload=payload, vdom=vdom)
        self.get_router_policy(vdom=vdom)
        return response

    def config_router_prefix_list(self, name, rules, comments='', vdom=None):
        payload = {
            'comments': comments,
            'name': name,
            'rule': rules
        }
        if self.router_prefix_lists is None:
            self.get_router_prefix_lists(vdom=vdom)
        for i in self.router_prefix_lists:
            if i['name'] != name:
                continue
            response = self.send_request(
                '{}/router/prefix-list/{}'.format(self.config_url, name),
                action='PUT', attempts=1, payload=payload, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/router/prefix-list'.format(self.config_url), action='POST',
                attempts=1, payload=payload, vdom=vdom)
        self.get_router_prefix_lists(vdom=vdom)
        return response

    def config_router_route_map(self, name, rules, comments='', vdom=None):
        payload = {
            'comments': comments,
            'name': name,
            'rule': rules
        }
        if self.router_route_maps is None:
            self.get_router_route_maps(vdom=vdom)
        for i in self.router_route_maps:
            if i['name'] != name:
                continue
            response = self.send_request(
                '{}/router/route-map/{}'.format(self.config_url, name),
                action='PUT', attempts=1, payload=payload, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/router/route-map'.format(self.config_url), action='POST',
                attempts=1, payload=payload, vdom=vdom)
        self.get_router_route_maps(vdom=vdom)
        return response

    def config_router_static(
            self, device, bfd='disable', blackhole='disable', comment='',
            distance=10, dst='0.0.0.0 0.0.0.0', dstaddr=None,
            dynamic_gateway='disable', entry=0, gateway='0.0.0.0',
            internet_service=0, internet_service_custom=None,
            link_monitor_exempt='disable', priority=1, sdwan_zone=None,
            status='enable', vdom=None, vrf=0, weight=0):
        payload = {
            'bfd': bfd,
            'blackhole': blackhole,
            'comment': comment,
            'device': device,
            'distance': distance,
            'dynamic-gateway': dynamic_gateway,
            'entry': entry,
            'gateway': gateway,
            'internet-service': internet_service,
            'internet-service-custom': internet_service_custom,
            'link-monitor-exempt': link_monitor_exempt,
            'priority': priority,
            'sdwan-zone': sdwan_zone,
            'status': status,
            'weight': weight
        }
        if dstaddr is None:
            payload['dst'] = dst
        else:
            payload['dstaddr'] = dstaddr
        if blackhole == 'enable':
            del payload['gateway']
            del payload['device']
            del payload['dynamic-gateway']
            del payload['sdwan-zone']
            payload['vrf'] = vrf

        if self.router_static is None:
            self.get_router_static(vdom=vdom)
        for i in self.router_static:
            if i['seq-num'] != entry:
                continue
            response = self.send_request(
                '{}/router/static/{}'.format(self.config_url, entry),
                action='PUT', attempts=1, payload=payload, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/router/static'.format(self.config_url), action='POST',
                attempts=1, payload=payload, vdom=vdom)
        self.get_router_static(vdom=vdom)
        return response

    def config_switch_controller_fortilink_settings(
            self, name, fortilink='fortilink', inactive_timer=15,
            link_down_flush='disable', nac_ports=None, vdom=None):
        ports = [] if nac_ports is None else nac_ports
        payload = {
            'name': name,
            'fortilink': fortilink,
            'inactive-timer': inactive_timer,
            'link-down-flush': link_down_flush,
            'nac-ports': ports
        }

        if self.switch_controller_fortilink_settings is None:
            self.get_switch_controller_fortilink_settings(vdom=vdom)
        for i in self.switch_controller_fortilink_settings:
            if i['name'] != name:
                continue
            response = self.send_request(
                '{}/switch-controller/fortilink-settings/{}'.format(
                    self.config_url, name),
                action='PUT', attempts=1, payload=payload, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/switch-controller/fortilink-settings'.format(
                    self.config_url),
                action='POST', attempts=1, payload=payload, vdom=vdom)
        self.get_switch_controller_fortilink_settings(vdom=vdom)
        return response

    def config_switch_controller_initial_config_template(
            self, name, vlanid, allowaccess='', auto_ip='enable',
            dhcp_server='disable', ip='0.0.0.0 0.0.0.0', vdom=None):
        payload = {
            'name': name,
            'vlanid': vlanid,
            'allowaccess': allowaccess,
            'dhcp-server': dhcp_server
        }
        if dhcp_server == 'enable':
            payload['auto-ip'] = auto_ip
            if auto_ip == 'disable':
                payload['ip'] == ip

        if self.switch_controller_initial_config_templates is None:
            self.get_switch_controller_initial_config_templates(vdom=vdom)
        for i in self.switch_controller_initial_config_templates:
            if i['name'] != name:
                continue
            response = self.send_request(
                '{}/switch-controller.initial-config/template/{}'.format(
                    self.config_url, name),
                action='PUT', attempts=1, payload=payload, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/switch-controller.initial-config/template'.format(
                    self.config_url),
                action='POST', attempts=1, payload=payload, vdom=vdom)
        self.get_switch_controller_initial_config_templates(vdom=vdom)
        return response

    def config_switch_controller_initial_config_vlans(
            self, default_vlan='_default', quarantine='quarantine',
            rspan='rspan', voice='voice', video='video', nac='onboarding',
            nac_segment='nac_segment', vdom=None):
        payload = {
            'default-vlan': default_vlan,
            'quarantine': quarantine,
            'rspan': rspan,
            'voice': voice,
            'video': video,
            'nac': nac,
            'nac-segment': nac_segment
        }
        if self.switch_controller_initial_config_vlans is None:
            self.get_switch_controller_initial_config_vlans(vdom=vdom)
        response = self.send_request(
            '{}/switch-controller.initial-config/vlans'.format(
                self.config_url),
            action='PUT', attempts=1, payload=payload, vdom=vdom)
        self.get_switch_controller_initial_config_vlans(vdom=vdom)
        return response

    def config_switch_controller_lldp_profile(
            self, name, auto_isl='enable', auto_isl_hello_timer=3,
            auto_isl_port_group=0, auto_isl_receive_timeout=60,
            auto_mclag_icl='disable', custom_tlvs=None,
            med_location_service=None, med_network_policy=None, med_tlvs=None,
            tlvs_802_1='', tlvs_802_3='', vdom=None):
        if med_tlvs is None:
            med_tlvs = 'inventory-management network-policy location-identification'
        if med_network_policy is None:
            med_network_policy = [
                {
                    'assign-vlan': 'disable', 'dscp': 0, 'name': 'voice',
                    'priority': 0, 'status': 'disable', 'vlan': 0,
                    'vlan-intf': ''
                },
                {
                    'assign-vlan': 'disable', 'dscp': 0,
                    'name': 'voice-signaling', 'priority': 0,
                    'status': 'disable', 'vlan': 0, 'vlan-intf': ''
                },
                {
                    'assign-vlan': 'disable', 'dscp': 0, 'name': 'guest-voice',
                    'priority': 0, 'status': 'disable', 'vlan': 0,
                    'vlan-intf': ''
                },
                {
                    'assign-vlan': 'disable', 'dscp': 0,
                    'name': 'guest-voice-signaling', 'priority': 0,
                    'status': 'disable', 'vlan': 0, 'vlan-intf': ''
                },
                {
                    'assign-vlan': 'disable', 'dscp': 0,
                    'name': 'softphone-voice', 'priority': 0,
                    'status': 'disable', 'vlan': 0, 'vlan-intf': ''
                },
                {
                    'assign-vlan': 'disable', 'dscp': 0,
                    'name': 'video-conferencing', 'priority': 0,
                    'status': 'disable', 'vlan': 0, 'vlan-intf': ''
                },
                {
                    'assign-vlan': 'disable', 'dscp': 0,
                    'name': 'streaming-video', 'priority': 0,
                    'status': 'disable', 'vlan': 0, 'vlan-intf': ''
                },
                {
                    'assign-vlan': 'disable', 'dscp': 0,
                    'name': 'video-signaling', 'priority': 0,
                    'status': 'disable', 'vlan': 0, 'vlan-intf': ''
                }
            ]
        if med_location_service is None:
            med_location_service = [
                {
                    'name': 'coordinates', 'status': 'disable',
                    'sys-location-id': ''
                },
                {
                    'name': 'address-civic', 'status': 'disable',
                    'sys-location-id': ''
                },
                {
                    'name': 'elin-number', 'status': 'disable',
                    'sys-location-id': ''
                }
            ]
        if custom_tlvs is None:
            custom_tlvs = []
        payload = {
            'name': name,
            'med-tlvs': med_tlvs,
            '802.1-tlvs': tlvs_802_1,
            '802.3-tlvs': tlvs_802_3,
            'auto-isl': auto_isl,
            'auto-isl-hello-timer': auto_isl_hello_timer,
            'auto-isl-receive-timeout': auto_isl_receive_timeout,
            'auto-isl-port-group': auto_isl_port_group,
            'auto-mclag-icl': auto_mclag_icl,
            'med-network-policy': med_network_policy,
            'med-location-service': med_location_service,
            'custom-tlvs': custom_tlvs,
        }
        if self.switch_controller_lldp_profiles is None:
            self.get_switch_controller_lldp_profiles(vdom=vdom)
        for i in self.switch_controller_lldp_profiles:
            if i['name'] != name:
                continue
            response = self.send_request(
                '{}/switch-controller/lldp-profile/{}'.format(
                    self.config_url, name),
                action='PUT', attempts=1, payload=payload, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/switch-controller/lldp-profile'.format(
                    self.config_url),
                action='POST', attempts=1, payload=payload, vdom=vdom)
        self.get_switch_controller_lldp_profiles(vdom=vdom)
        return response

    def config_switch_controller_managed_switch(
            self, serial, ports, description='', fsw_wan1_peer='fortilink',
            name='', stp_instance=None, stp_settings=None,
            switch_stp_settings='enable', vdom=None):
        instances = [] if stp_instance is None else stp_instance
        settings = {
            "local-override": "disable"} if stp_settings is None else stp_settings

        payload = {
            'description': description,
            'fsw-wan1-peer': fsw_wan1_peer,
            'name': name,
            'ports': ports,
            'stp-instance': instances,
            'stp-settings': settings,
            'switch-id': serial,
            'switch-stp-settings': switch_stp_settings
        }
        if self.switch_controller_managed_switches is None:
            self.get_switch_controller_managed_switches(vdom=vdom)
        for i in self.switch_controller_managed_switches:
            if i['switch-id'] != serial:
                continue
            response = self.send_request(
                '{}/switch-controller/managed-switch/{}'.format(
                    self.config_url, serial),
                action='PUT', attempts=1, payload=payload, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/switch-controller/managed-switch'.format(self.config_url),
                action='POST', attempts=1, payload=payload, vdom=vdom)
        self.get_switch_controller_managed_switches(vdom=vdom)
        return response

    def config_switch_controller_snmp_community(
            self, name, entry=0, hosts=None, status='enable',
            events='cpu-high mem-low log-full intf-ip ent-conf-change',
            query_v1_status='enable', query_v1_port=161,
            trap_v1_status='enable', trap_v1_lport=162, trap_v1_rport=162,
            query_v2c_status='enable', query_v2c_port=161,
            trap_v2c_status='enable', trap_v2c_lport=162, trap_v2c_rport=162,
            vdom=None):
        if hosts is None:
            host = []
        else:
            host = [{'id': hosts.index(i), 'ip': i}for i in hosts]
        payload = {
            'id': entry,
            'name': name,
            'hosts': host,
            'status': status,
            'events': events,
            'query-v1-status': query_v1_status,
            'query-v1-port': query_v1_port,
            'trap-v1-status': trap_v1_status,
            'trap-v1-lport': trap_v1_lport,
            'trap-v1-rport': trap_v1_rport,
            'query-v2c-status': query_v2c_status,
            'query-v2c-port': query_v2c_port,
            'trap-v2c-status': trap_v2c_status,
            'trap-v2c-lport': trap_v2c_lport,
            'trap-v2c-rport': trap_v2c_rport
        }

        if self.switch_controller_snmp_community is None:
            self.get_switch_controller_snmp_community(vdom=vdom)
        for i in self.switch_controller_snmp_community:
            if i['id'] != entry:
                continue
            response = self.send_request(
                '{}/switch-controller/snmp-community/{}'.format(
                    self.config_url, entry),
                action='PUT', attempts=1, payload=payload, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/switch-controller/snmp-community'.format(self.config_url),
                action='POST', attempts=1, payload=payload, vdom=vdom)
        self.get_switch_controller_snmp_community(vdom=vdom)
        return response

    def config_switch_controller_stp_instance(
            self, instance, vlan_range, vdom=None):
        instance = int(instance)
        vlans = [{'vlan-name': i} for i in vlan_range]
        payload = {
            'id': str(instance),
            'vlan-range': vlans
        }

        if self.switch_controller_stp_instances is None:
            self.get_switch_controller_stp_instances(vdom=vdom)
        for i in self.switch_controller_stp_instances:
            if i['id'] != instance:
                continue
            response = self.send_request(
                '{}/switch-controller/stp-instance/{}'.format(
                    self.config_url, instance),
                action='PUT', attempts=1, payload=payload, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/switch-controller/stp-instance'.format(self.config_url),
                action='POST', attempts=1, payload=payload, vdom=vdom)
        self.get_switch_controller_stp_instances(vdom=vdom)
        return response

    def config_switch_controller_stp_settings(
            self, name, revision, forward_time=15, hello_time=2, max_age=20,
            max_hops=20, vdom=None):
        payload = {
            'name': name,
            'revision': revision,
            'forward-time': forward_time,
            'hello-time': hello_time,
            'max-age': max_age,
            'max-hops': max_hops
        }

        if self.switch_controller_stp_settings is None:
            self.get_switch_controller_stp_settings(vdom=vdom)
        response = self.send_request(
            '{}/switch-controller/stp-settings'.format(self.config_url),
            action='PUT', attempts=1, payload=payload, vdom=vdom)
        self.get_switch_controller_stp_settings(vdom=vdom)
        return response

    def config_system_ntp(
            self, authentication='disable', interface=[], key='', ntpserver=[],
            ntpsync='enable', source_ip='0.0.0.0', syncinterval=60):
        if self.system_ntp is None:
            self.get_system_ntp()
        if len(interface) >= 1:
            interfaces = [{'interface-name': i} for i in interface]
            server_mode = 'enable'
        else:
            interfaces = []
            server_mode = 'disable'
        ntp_type = 'custom' if len(ntpserver) >= 1 else 'fortiguard'
        if len(ntpserver) >= 1:
            ntpservers = []
            index = 1
            for i in ntpserver:
                i = {
                    'authentication': 'disable',
                    'id': index,
                    'key': '',
                    'key-id': 0,
                    'ntpv3': 'disable',
                    'server': i
                }
                ntpservers.append(i)
                index += 1
        else:
            ntpservers = []
        payload = {
            'authentication': authentication,
            'interface': interfaces,
            'key': key,
            'key-id': 0,
            'key-type': 'MD5',
            'ntpserver': ntpservers,
            'ntpsync': ntpsync,
            'server-mode': server_mode,
            'source-ip': source_ip,
            'source-ip6': '::',
            'syncinterval': syncinterval,
            'type': ntp_type
        }
        response = self.send_request(
            '{}/system/ntp'.format(self.config_url), action='PUT',
            payload=payload, attempts=1)
        self.get_system_ntp()
        return response

    def config_system_accprofile(
            self, name, authgrp='read', comments='', ftviewgrp='read',
            fwgrp='read', loggrp='read', netgrp='read', scope='vdom',
            secfabgrp='read', sysgrp='read', system_diagnostics='enable',
            utmgrp='read', vpngrp='read', wanoptgrp='read', wifi='read'):
        payload = {
            'authgrp': authgrp,
            'comments': comments,
            'ftviewgrp': ftviewgrp,
            'fwgrp': fwgrp,
            'loggrp': loggrp,
            'name': name,
            'netgrp': netgrp,
            'scope': scope,
            'secfabgrp': secfabgrp,
            'sysgrp': sysgrp,
            'system-diagnostics': system_diagnostics,
            'utmgrp': utmgrp,
            'vpngrp': vpngrp,
            'wanoptgrp': wanoptgrp,
            'wifi': wifi
        }
        if self.system_accprofiles is None:
            self.get_system_accprofiles()
            if self.system_accprofiles is None:
                pass

        for i in self.system_accprofiles:
            if i['name'] != name:
                continue
            response = self.send_request(
                '{}/system/accprofile/{}'.format(self.config_url, name),
                action='PUT', payload=payload, attempts=1)
            break
        else:
            response = self.send_request(
                '{}/system/accprofile'.format(self.config_url), action='POST',
                payload=payload, attempts=1)
        self.get_system_accprofiles()
        return response

    def config_system_admin(
            self, name, password, accprofile, accprofile_override='disable',
            allow_remove_admin_session='enable', comments='', remote_group=None,
            vdom=None):
        if vdom is None:
            vdom = ['root']
        vdoms = [{'name': i} for i in vdom]
        payload = {
            'accprofile': accprofile,
            'comments': comments,
            'name': name,
            'password': password,
            'vdom': vdoms,
        }
        if remote_group is not None:
            payload['remote-auth'] = 'enable'
            payload['remote-group'] = remote_group
            payload['accprofile-override'] = accprofile_override
        if accprofile == 'super_admin':
            payload['allow-remove-admin-session'] = allow_remove_admin_session

        if self.system_admins is None:
            self.get_system_admins()
        for i in self.system_admins:
            if i['name'] != name:
                continue
            response = self.send_request(
                '{}/system/admin/{}'.format(self.config_url, name),
                action='PUT', payload=payload, attempts=1)
            break
        else:
            response = self.send_request(
                '{}/system/admin'.format(self.config_url), action='POST',
                payload=payload, attempts=1)
        self.get_system_admins()
        return response

    def config_system_auto_script(
            self, name, script, interval=0, repeat=1, start='manual',
            output_size=10, timeout=0, vdom=None):
        payload = {
            'name': name,
            'script': script,
            'interval': interval,
            'repeat': repeat,
            'start': start,
            'output-size': output_size,
            'timeout': timeout
        }
        if self.system_auto_scripts is None:
            self.get_system_auto_scripts()
        for i in self.system_auto_scripts:
            if i['name'] != name:
                continue
            response = self.send_request(
                '{}/system/auto-script/{}'.format(self.config_url, name),
                action='PUT', payload=payload, attempts=1, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/system/auto-script'.format(self.config_url), action='POST',
                payload=payload, attempts=1, vdom=vdom)
        self.get_system_auto_scripts(vdom=vdom)
        return response

    def config_system_automation_action(
            self, name, action_type='cli-script', script=None, accprofile=None,
            vdom=None):
        payload = {
            'name': name,
            'action-type': action_type,
            'script': script,
            'accprofile': accprofile
        }
        if self.system_automation_actions is None:
            self.get_system_automation_actions()
        for i in self.system_automation_actions:
            if i['name'] != name:
                continue
            response = self.send_request(
                '{}/system/automation-action/{}'.format(
                    self.config_url, name),
                action='PUT', payload=payload, attempts=1, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/system/automation-action'.format(self.config_url),
                action='POST', payload=payload, attempts=1, vdom=vdom)
        self.get_system_automation_actions(vdom=vdom)
        return response

    def config_system_automation_stitch(
            self, name, trigger, actions=None, description='', destination=None,
            status='enable', vdom=None):
        actions = [] if actions is None else actions
        destination = [] if destination is None else destination
        payload = {
            'name': name,
            'trigger': trigger,
            'actions': actions,
            'description': description,
            'destination': destination,
            'status': status
        }
        if self.system_automation_stitches is None:
            self.get_system_automation_stitches()
        for i in self.system_automation_stitches:
            if i['name'] != name:
                continue
            response = self.send_request(
                '{}/system/automation-stitch/{}'.format(
                    self.config_url, name),
                action='PUT', payload=payload, attempts=1, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/system/automation-stitch'.format(self.config_url),
                action='POST', payload=payload, attempts=1, vdom=vdom)
        self.get_system_automation_stitches(vdom=vdom)
        return response

    def config_system_automation_trigger(
            self, name, event_type='event-log', logid=None, fields=None,
            vdom=None):
        log_ids = [{'id': i} for i in logid] if logid is not None else None
        payload = {
            'name': name,
            'event-type': event_type,
            'logid': log_ids,
            'fields': fields
        }
        if self.system_automation_triggers is None:
            self.get_system_automation_triggers()
        for i in self.system_automation_triggers:
            if i['name'] != name:
                continue
            response = self.send_request(
                '{}/system/automation-trigger/{}'.format(
                    self.config_url, name),
                action='PUT', payload=payload, attempts=1, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/system/automation-trigger'.format(self.config_url),
                action='POST', payload=payload, attempts=1, vdom=vdom)
        self.get_system_automation_triggers(vdom=vdom)
        return response

    def config_system_central_management(
            self, allow_monitor='enable', allow_push_configuration='enable',
            allow_push_firmware='enable',
            allow_remote_firmware_upgrade='enable', ca_cert='',
            enc_algorithm='high', fmg='', fmg_source_ip='0.0.0.0',
            fmg_source_ip6='::', fmg_update_port='8890',
            include_default_servers='enable', interface='',
            interface_select_method='auto', local_cert='', mode='normal',
            schedule_config_restore='enable', schedule_script_restore='enable',
            serial_number='', server_list=None, type='fortiguard', vdom='root'):
        if server_list is None:
            server_list = []
        payload = {
            'allow-monitor': allow_monitor,
            'allow-push-configuration': allow_push_configuration,
            'allow-push-firmware': allow_push_firmware,
            'allow-remote-firmware-upgrade': allow_remote_firmware_upgrade,
            'ca-cert': ca_cert,
            'enc-algorithm': enc_algorithm,
            'fmg': fmg,
            'fmg-source-ip': fmg_source_ip,
            'fmg-source-ip6': fmg_source_ip6,
            'fmg-update-port': fmg_update_port,
            'include-default-servers': include_default_servers,
            'interface': interface,
            'interface-select-method': interface_select_method,
            'local-cert': local_cert,
            'mode': mode,
            'schedule-config-restore': schedule_config_restore,
            'schedule-script-restore': schedule_script_restore,
            'serial-number': serial_number,
            'server-list': server_list,
            'type': type,
            'vdom': vdom
        }
        if self.system_central_management is None:
            self.get_system_central_management()
        response = self.send_request(
            '{}/system/central-management'.format(self.config_url),
            action='PUT', payload=payload, attempts=1)
        self.get_system_central_management()
        return response

    def config_system_console(
            self, baudrate='9600', fortiexplorer='enable', login='enable',
            mode='line', output='standard'):
        payload = {
            'baudrate': baudrate,
            'fortiexplorer': fortiexplorer,
            'login': login,
            'mode': mode,
            'output': output
        }
        if self.system_console is None:
            self.get_system_console()
        response = self.send_request(
            '{}/system/console'.format(self.config_url), action='PUT',
            payload=payload, attempts=1)
        self.get_system_console()
        return response

    def config_system_dhcp_server(
            self, interface, default_gateway, netmask, ip_range,
            exclude_range=None, domain='', dns_server1='0.0.0.0',
            dns_server2='0.0.0.0', dns_server3='0.0.0.0', entry=0,
            lease_time=604800, next_server='0.0.0.0', ntp_server1='0.0.0.0',
            ntp_server2='0.0.0.0', ntp_server3='0.0.0.0', options=None,
            reserved_addresses=None, status='enable', timezone=None,
            vci_match='disable', vci_string='', vdom=None, wins_server1=None,
            wins_server2=None):
        dns_service = 'default' if (dns_server1, dns_server2, dns_server3) == (
            '0.0.0.0', '0.0.0.0', '0.0.0.0') else 'specify'
        ntp_service = 'default' if (ntp_server1, ntp_server2, ntp_server3) == (
            '0.0.0.0', '0.0.0.0', '0.0.0.0') else 'specify'
        timezone_option = 'disable' if timezone is None else 'specify'
        ip_ranges = [{'id': ip_range.index(
            i) + 1, 'start-ip': i[0], 'end-ip': i[1]} for i in ip_range]
        if exclude_range is not None:
            exclude_ranges = [{'id': exclude_range.index(
                i) + 1, 'start-ip': i[0], 'end-ip': i[1]} for i in exclude_range]
        else:
            exclude_ranges = []
        if options is not None:
            option = []
            for i in options:
                i['id'] = options.index(i) + 1
                if i['type'] == 'ip':
                    i['ip'] = i.pop('value')
                option.append(i)
        else:
            option = []
        if reserved_addresses is not None:
            reserved_address = []
            for i in reserved_addresses:
                i['id'] = reserved_addresses.index(i) + 1
                i['type'] = 'mac'
                i['action'] = 'reserved'
                reserved_address.append(i)
        else:
            reserved_address = []

        payload = {
            'default-gateway': default_gateway,
            'domain': domain,
            'dns-server1': dns_server1,
            'dns-server2': dns_server2,
            'dns-server3': dns_server3,
            'dns-service': dns_service,
            'exclude-range': exclude_ranges,
            'id': entry,
            'interface': interface,
            'ip-mode': 'range',
            'ip-range': ip_ranges,
            'lease_time': lease_time,
            'next-server': next_server,
            'netmask': netmask,
            'ntp-server1': ntp_server1,
            'ntp-server2': ntp_server2,
            'ntp-server3': ntp_server3,
            'ntp-service': ntp_service,
            'options': option,
            'reserved-address': reserved_address,
            'server-type': 'regular',
            'status': status,
            'tftp-server': '',
            'timezone': timezone,
            'timezone-option': timezone_option,
            'vci-match': vci_match,
            'wins-server1': wins_server1,
            'wins-server2': wins_server2
        }
        if vci_match == 'enable':
            vci_strings = vci_string.split(' ')
            vci_strings = [{'vci-string': i} for i in vci_strings]
            payload['vci-string'] = vci_strings
        if self.system_dhcp_servers is None:
            self.get_system_dhcp_servers(vdom=vdom)
        for i in self.system_dhcp_servers:
            if i['id'] != entry:
                continue
            response = self.send_request(
                '{}/system.dhcp/server/{}'.format(self.config_url, entry),
                action='PUT', payload=payload, attempts=1, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/system.dhcp/server'.format(self.config_url), action='POST',
                payload=payload, attempts=1, vdom=vdom)
        self.get_system_dhcp_servers(vdom=vdom)
        return response

    def config_system_dscp_based_priority(self, ds, priority, entry=0):
        payload = {
            'id': entry,
            'ds': ds,
            'priority': priority
        }
        if self.system_dscp_based_priority is None:
            self.get_system_dscp_based_priority()
        for i in self.system_dscp_based_priority:
            if i['id'] != entry:
                continue
            response = self.send_request(
                '{}/system/dscp-based-priority/{}'.format(
                    self.config_url, entry),
                action='PUT', payload=payload, attempts=1)
            break
        else:
            response = self.send_request(
                '{}/system/dscp-based-priority'.format(self.config_url),
                action='POST', payload=payload, attempts=1)
        self.get_system_dscp_based_priority()
        return response

    def config_system_fortiguard(
            self, antispam_force_off='disable', port='443',
            webfilter_force_off='disable'):
        payload = {
            'port': port,
            'antispam-force-off': antispam_force_off,
            'webfilter-force-off': webfilter_force_off,
        }
        if self.system_fortiguard is None:
            self.get_system_fortiguard()
        response = self.send_request(
            '{}/system/fortiguard'.format(self.config_url), action='PUT',
            payload=payload, attempts=1)
        self.get_system_fortiguard()
        return response

    def config_system_global(
            self, hostname, management_vdom, admintimeout=15,
            admin_console_timeout=15,
            admin_https_ssl_versions='tlsv1-1 tlsv1-2 tlsv1-3',
            admin_lockout_duration=60, admin_lockout_threshold=3,
            admin_ssh_v1='disable', admin_telnet='disable', dst='enable',
            gui_ipv6='disable', gui_theme='onyx', pre_login_banner='disable',
            ssl_min_proto_version='TLSv1-2', strong_crypto='enable',
            timezone='12', traffic_priority='tos',
            traffic_priority_level='medium'):
        payload = {
            'admintimeout': admintimeout,
            'admin-console-timeout': admin_console_timeout,
            'admin-https-ssl-versions': admin_https_ssl_versions,
            'admin-lockout-duration': admin_lockout_duration,
            'admin-lockout-threshold': admin_lockout_threshold,
            'admin-ssh-v1': admin_ssh_v1,
            'admin-telnet': admin_telnet,
            'dst': dst,
            'gui-ipv6': gui_ipv6,
            'gui-theme': gui_theme,
            'hostname': hostname,
            'management-vdom': management_vdom,
            'pre-login-banner': pre_login_banner,
            'ssl-min-proto-version': ssl_min_proto_version,
            'strong-crypto': strong_crypto,
            'timezone': timezone,
            'traffic-priority': traffic_priority,
            'traffic-priority-level': traffic_priority_level
        }
        if self.system_global is None:
            self.get_system_global()
        response = self.send_request(
            '{}/system/global'.format(self.config_url), action='PUT',
            payload=payload, attempts=1)
        self.get_system_global()
        return response

    def config_system_gre_tunnel(
            self, name, remote_gw, local_gw, checksum_reception='disable',
            checksum_transmission='disable', diffservcode='000000',
            dscp_copying='disable', interface='', keepalive_interval=0,
            key_inbound=0, key_outbound=0, sequence_number_reception='disable',
            sequence_number_transmission='disable', use_sdwan='disable',
            vdom=None):
        payload = {
            'name': name,
            'ip-version': '4',
            'remote-gw': remote_gw,
            'local-gw': local_gw,
            'checksum-reception': checksum_reception,
            'checksum-transmission': checksum_transmission,
            'diffservcode': diffservcode,
            'dscp-copying': dscp_copying,
            'interface': interface,
            'keepalive-interval': keepalive_interval,
            'key-inbound': key_inbound,
            'key-outbound': key_outbound,
            'sequence-number-reception': sequence_number_reception,
            'sequence-number-transmission': sequence_number_transmission,
            'use-sdwan': use_sdwan
        }
        if self.system_gre_tunnels is None:
            self.get_system_gre_tunnels(vdom=vdom)
        for entry in self.system_gre_tunnels:
            if entry['name'] != name:
                continue
            response = self.send_request(
                '{}/system/gre-tunnel/{}'.format(self.config_url, name),
                action='PUT', payload=payload, attempts=1, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/system/gre-tunnel'.format(self.config_url), action='POST',
                payload=payload, attempts=1, vdom=vdom)
        self.get_system_gre_tunnels(vdom=vdom)
        return response

    def config_system_ha(
            self, authentication='disable', encryption='disable', group_id=0,
            group_name=None, hbdev=None, mode='standalone', monitor=None,
            override='disable', override_wait_time=0, password=None,
            priority=128, session_pickup='disable',
            session_pickup_connectionless='disable', sync_config='enable'):
        monitor = '' if monitor is None else ' '.join(monitor)
        hbdev = '' if hbdev is None else ' '.join([str(i) for i in hbdev])
        payload = {
            'authentication': authentication,
            'encryption': encryption,
            'group-name': group_name,
            'group-id': group_id,
            'hbdev': hbdev,
            'mode': mode,
            'monitor': monitor,
            'override': override,
            'password': password,
            'priority': priority,
            'session-pickup': session_pickup,
            'sync-config': sync_config,
        }
        if session_pickup == 'enable':
            payload['session-pickup-connectionless'] = session_pickup_connectionless
        if override == 'enable':
            payload['override-wait-time'] = override_wait_time

        if self.system_ha is None:
            self.get_system_ha()
        response = self.send_request(
            '{}/system/ha'.format(self.config_url), action='PUT',
            payload=payload, attempts=1)
        self.get_system_ha()
        return response

    def raw_config_interface(self, payload):
        name = payload.get("name")
        vdom = "root"
        self.get_system_interfaces(vdom=vdom)
        existing_interfaces = [x["name"] for x in self.system_interfaces]
        if name is not None and name in existing_interfaces:
            self.logger.info(f"--- overwriting existing interface with name {name}")
            response = self.send_request(
                '{}/system/interface/{}'.format(self.config_url, name),
                action='PUT', payload=payload, attempts=1, vdom=vdom)
            self.logger.info(f"--- response for interface overwrite {response}")
        else:
            self.logger.info("--- creating new interface")
            response = self.send_request(
                '{}/system/interface'.format(self.config_url), action='POST',
                payload=payload, attempts=1, vdom=vdom)
            self.logger.info(f"--- response for interface creation {response}")
        return response

    def config_system_settings(
            self, allow_subnet_overlap='disable', central_nat='disable',
            default_voip_alg_mode='kernel-helper-based',
            gui_allow_unnamed_policy='enable', gui_default_policy_columns=None,
            gui_fortiextender_controller='disable', gui_ips='enable',
            gui_sslvpn_realms='enable', gui_switch_controller='disable',
            gui_voip_profile='disable', ngfw_mode='profile-based', opmode='nat',
            sip_expectation='disable', sip_nat_trace='disable',
            sip_tcp_port=5060, sip_udp_port=5060, sip_ssl_port=5061, vdom=None):
        if gui_default_policy_columns is None:
            gui_default_policy_columns = [
                'policyid', 'consolidated-srcaddr', 'consolidated-dstaddr',
                'service', 'consolidated-poolname', 'action', 'status',
                'profile', 'logtraffic', 'bytes'
            ]
        gui_policy_columns = [
            {'name': i} for i in gui_default_policy_columns]
        payload = {
            'allow-subnet-overlap': allow_subnet_overlap,
            'central-nat': central_nat,
            'default-voip-alg-mode': default_voip_alg_mode,
            'gui-allow-unnamed-policy': gui_allow_unnamed_policy,
            'gui-default-policy-columns': gui_policy_columns,
            'gui-fortiextender-controller': gui_fortiextender_controller,
            'gui-ips': gui_ips,
            'gui-sslvpn-realms': gui_sslvpn_realms,
            'gui-switch-controller': gui_switch_controller,
            'gui-voip-profile': gui_voip_profile,
            'ngfw-mode': ngfw_mode,
            'opmode': opmode,
            'sip-expectation': sip_expectation,
            'sip-nat-trace': sip_nat_trace,
            'sip-tcp-port': sip_tcp_port,
            'sip-udp-port': sip_udp_port,
            'sip-ssl-port': sip_ssl_port
        }
        if self.system_settings is None:
            self.get_system_settings(vdom=vdom)
        response = self.send_request(
            '{}/system/settings'.format(self.config_url), action='PUT',
            payload=payload, attempts=1, vdom=vdom)
        self.get_system_settings(vdom=vdom)
        return response

    def config_system_snmp_community(
            self, id, name, hosts, events=None, hosts6=None, query_v1_port=161,
            query_v1_status='disable', query_v2c_port=161,
            query_v2c_status='disable', status='enable', trap_v1_lport=162,
            trap_v1_rport=162, trap_v1_status='disable', trap_v2c_lport=162,
            trap_v2c_rport=162, trap_v2c_status='disable'):
        if events is None:
            events = (
                'cpu-high mem-low log-full intf-ip vpn-tun-up '
                'vpn-tun-down ha-switch ha-hb-failure ips-signature ips-anomaly '
                'av-virus av-oversize av-pattern av-fragmented fm-if-change '
                'bgp-established bgp-backward-transition ha-member-up '
                'ha-member-down ent-conf-change av-conserve av-bypass '
                'av-oversize-passed av-oversize-blocked ips-pkg-update '
                'ips-fail-open power-supply-failure faz-disconnect wc-ap-up '
                'wc-ap-down fswctl-session-up fswctl-session-down '
                'load-balance-real-server-down per-cpu-high dhcp '
                'ospf-nbr-state-change ospf-virtnbr-state-change')
        if hosts6 is None:
            hosts6 = []
        payload = {
            'events': events,
            'hosts': hosts,
            'hosts6': hosts6,
            'id': id,
            'name': name,
            'query-v1-port': query_v1_port,
            'query-v1-status': query_v1_status,
            'query-v2c-port': query_v2c_port,
            'query-v2c-status': query_v2c_status,
            'status': status,
            'trap-v1-lport': trap_v1_lport,
            'trap-v1-rport': trap_v1_rport,
            'trap-v1-status': trap_v1_status,
            'trap-v2c-lport': trap_v2c_lport,
            'trap-v2c-rport': trap_v2c_rport,
            'trap-v2c-status': trap_v2c_status
        }
        if self.system_snmp_community is None:
            self.get_system_snmp_community()
        for i in self.system_snmp_community:
            if i['id'] != id:
                continue
            response = self.send_request(
                '{}/system.snmp/community/{}'.format(self.config_url, id),
                action='PUT', payload=payload, attempts=1)
            break
        else:
            response = self.send_request(
                '{}/system.snmp/community'.format(self.config_url),
                action='POST', payload=payload, attempts=1)
        self.get_system_snmp_community()
        return response

    def config_system_snmp_sysinfo(
            self, contact_info='', description='', engine_id='',
            engine_id_type='text', location='', status='enable',
            trap_high_cpu_threshold=80, trap_log_full_threshold=90,
            trap_low_memory_threshold=80):
        payload = {
            'contact-info': contact_info,
            "description": description,
            'engine-id': engine_id,
            'engine-id-type': engine_id_type,
            "location": location,
            "status": status,
            'trap-high-cpu-threshold': trap_high_cpu_threshold,
            'trap-log-full-threshold': trap_log_full_threshold,
            'trap-low-memory-threshold': trap_low_memory_threshold
        }
        if self.system_snmp_sysinfo is None:
            self.get_system_snmp_sysinfo()
        response = self.send_request(
            '{}/system.snmp/sysinfo'.format(self.config_url), action='PUT',
            payload=payload, attempts=1)
        self.get_system_snmp_sysinfo()
        return response

    def config_system_snmp_user(
            self, name, notify_hosts, auth_pwd, priv_pwd, auth_proto='sha',
            priv_proto='aes', queries='enable', query_port=161,
            security_level='auth-priv', source_ip='', status='enable',
            trap_lport=162, trap_rport=162, trap_status='enable'):
        payload = {
            'auth-proto': auth_proto,
            'auth-pwd': auth_pwd,
            'name': name,
            'notify-hosts': notify_hosts,
            'priv-proto': priv_proto,
            'priv-pwd': priv_pwd,
            'queries': queries,
            'query-port': query_port,
            'security-level': security_level,
            'source-ip': source_ip,
            'status': status,
            'trap-lport': trap_lport,
            'trap-rport': trap_rport,
            'trap-status': trap_status
        }
        if self.system_snmp_users is None:
            self.get_system_snmp_users()
        for entry in self.system_snmp_users:
            if entry['name'] != name:
                continue
            response = self.send_request(
                '{}/system.snmp/user/{}'.format(self.config_url, name),
                action='PUT', payload=payload, attempts=1)
            break
        else:
            response = self.send_request(
                '{}/system.snmp/user'.format(self.config_url), action='POST',
                payload=payload, attempts=1)
        self.get_system_snmp_users()
        return response

    def config_system_switch_interface(
            self, name, vdom, dest_port=None, direction=None,
            intra_switch_policy='implicit', mac_ttl=300, members=None,
            source_ports=None, span='disable'):
        source_port = [] if source_ports is None else [
            {'interface-name': i} for i in source_ports]
        member = [] if members is None else [
            {'interface-name': i} for i in members]
        payload = {
            'intra-switch-policy': intra_switch_policy,
            'mac-ttl': mac_ttl,
            'member': member,
            'name': name,
            'span': span,
            'type': 'switch',
            'vdom': vdom
        }
        if span == 'enable':
            payload['span-dest-port'] = dest_port
            payload['span-direction'] = direction
            payload['span-source-port'] = source_port
        if self.system_switch_interfaces is None:
            self.get_system_switch_interfaces(vdom=vdom)
        for i in self.system_switch_interfaces:
            if i['name'] != name:
                continue
            response = self.send_request(
                '{}/system/switch-interface/{}'.format(self.config_url, name),
                action='PUT', payload=payload, attempts=1, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/system/switch-interface'.format(self.config_url),
                action='POST', payload=payload, attempts=1, vdom=vdom)
        self.get_system_switch_interfaces(vdom=vdom)
        return response

    def config_system_vdom(self, name, flag=0, vcluster_id=0):
        payload = {
            'flag': flag,
            'name': name,
            'short-name': name,
            'vcluster-id': vcluster_id
        }
        if self.system_vdoms is None:
            self.get_system_vdoms()
        for entry in self.system_vdoms:
            if entry['name'] != name:
                continue
            response = self.send_request(
                '{}/system/vdom/{}'.format(self.config_url, name), action='PUT',
                payload=payload, attempts=1)
            break
        else:
            response = self.send_request(
                '{}/system/vdom'.format(self.config_url), action='POST',
                payload=payload, attempts=1)
        self.get_system_vdoms()
        return response

    def config_system_zone(
            self, name, interfaces, description='', intrazone='deny',
            vdom=None):
        interface = [{'interface-name': i} for i in interfaces]
        payload = {
            'description': description,
            'interface': interface,
            'intrazone': intrazone,
            'name': name
        }
        if self.system_zones is None:
            self.get_system_zones(vdom=vdom)
        for i in self.system_zones:
            if i['name'] != name:
                continue
            response = self.send_request(
                '{}/system/zone/{}'.format(self.config_url, name), action='PUT',
                payload=payload, attempts=1, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/system/zone'.format(self.config_url), action='POST',
                payload=payload, attempts=1, vdom=vdom)
        self.get_system_zones(vdom=vdom)
        return response

    def config_user_group(
            self, name, member, group_type='firewall', match=None, vdom=None):
        members = [{'name': i} for i in member]
        payload = {
            'group-type': group_type,
            'match': match,
            'member': members,
            'name': name,
        }
        if self.user_groups is None:
            self.get_user_groups(vdom=vdom)
        for i in self.user_groups:
            if i['name'] != name:
                continue
            response = self.send_request(
                '{}/user/group/{}'.format(self.config_url, name), action='PUT',
                payload=payload, attempts=1, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/user/group'.format(self.config_url), action='POST',
                payload=payload, attempts=1, vdom=vdom)
        self.get_user_groups(vdom=vdom)
        return response

    def config_user_ldap(
            self, name, server, dn, auth_type='simple', cnid='cn',
            password=None, password_expiry_warning='disable',
            password_renewal='disable', port=None, secondary_server=None,
            secure='disable', source_ip=None, source_port=0,
            tertiary_server=None, two_factor='disable', username=None,
            vdom=None):
        if port is None:
            port = 636 if secure == 'ldaps' else 389
        payload = {
            'name': name,
            'server': server,
            'dn': dn,
            'cnid': cnid,
            'password-expiry-warning': password_expiry_warning,
            'password-renewal': password_renewal,
            'port': port,
            'secure': secure,
            'source-ip': source_ip,
            'source-port': source_port,
            'two-factor': two_factor,
            'type': auth_type
        }
        if auth_type == 'regular':
            payload['username'] = username
            payload['password'] = password
        if secondary_server is not None:
            payload['secondary-server'] = secondary_server
        if tertiary_server is not None:
            payload['tertiary-server'] = tertiary_server

        if self.user_ldap is None:
            self.get_user_ldap(vdom=vdom)
        for i in self.user_ldap:
            if i['name'] != name:
                continue
            response = self.send_request(
                '{}/user/ldap/{}'.format(self.config_url, name), action='PUT',
                payload=payload, attempts=1, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/user/ldap'.format(self.config_url), action='POST',
                payload=payload, attempts=1, vdom=vdom)
        self.get_user_ldap(vdom=vdom)
        return response

    def config_user_local(
            self, name, password, authtimeout=0,
            auth_concurrent_override='disable', auth_concurrent_value=0,
            email_to=None, server=None, sms_phone=None, status='enable',
            two_factor='disable', user_type='password', vdom=None,
            workstation=None):
        payload = {
            'name': name,
            'passwd': password,
            'authtimeout': authtimeout,
            'auth_concurrent_override': auth_concurrent_override,
            'email_to': email_to,
            'sms_phone': sms_phone,
            'status': status,
            'two_factor': two_factor,
            'type': user_type,
            'workstation': workstation
        }
        if user_type == 'ldap':
            payload['ldap-server'] = server
        elif user_type == 'tacacs+':
            payload['tacacs+-server'] = server
        elif user_type == 'radius':
            payload['radius-server'] = server

        if self.user_local is None:
            self.get_user_local(vdom=vdom)
        for i in self.user_local:
            if i['name'] != name:
                continue
            response = self.send_request(
                '{}/user/local/{}'.format(self.config_url, name), action='PUT',
                payload=payload, attempts=1, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/user/local'.format(self.config_url), action='POST',
                payload=payload, attempts=1, vdom=vdom)
        self.get_user_local(vdom=vdom)
        return response

    def config_user_radius(
            self, name, server, secret, acct_all_servers='disable',
            acct_interim_interval=60, all_usergroup='disable', auth_type='auto',
            interface=None, interface_select_method='auto', nas_ip='0.0.0.0',
            password_encoding='auto', password_renewal='enable',
            radius_coa='disable', radius_port=0, rsso='disable', source_ip=None,
            timeout=5, username_case_sensitive='disable',
            use_management_vdom='disable', vdom=None):
        if interface is not None:
            interface_select_method = 'specify'
        payload = {
            'name': name,
            'server': server,
            'secret': secret,
            'timeout': timeout,
            'all-usergroup': all_usergroup,
            'use-management-vdom': use_management_vdom,
            'nas-ip': nas_ip,
            'acct-interim-interval': acct_interim_interval,
            'radius-coa': radius_coa,
            'radius-port': radius_port,
            'auth-type': auth_type,
            'source-ip': source_ip,
            'username-case-sensitive': username_case_sensitive,
            'password-renewal': password_renewal,
            'password-encoding': password_encoding,
            'acct-all-servers': acct_all_servers,
            'interface': interface,
            'interface-select-method': interface_select_method,
            'rsso': rsso
        }
        if self.user_radius is None:
            self.get_user_radius(vdom=vdom)
        for i in self.user_radius:
            if i['name'] != name:
                continue
            response = self.send_request(
                '{}/user/radius/{}'.format(self.config_url, name), action='PUT',
                payload=payload, attempts=1, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/user/radius'.format(self.config_url), action='POST',
                payload=payload, attempts=1, vdom=vdom)
        self.get_user_radius(vdom=vdom)
        return response

    def config_user_tacacs(
            self, name, key, server, authen_type='ascii',
            authorization='enable', interface_select_method='auto', port=49,
            secondary_key='', secondary_server='', source_ip='',
            tertiary_key='', tertiary_server='', vdom=None):
        payload = {
            'authen-type': authen_type,
            'authorization': authorization,
            'interface-select-method': interface_select_method,
            'key': key,
            'name': name,
            'port': port,
            'secondary-key': secondary_key,
            'secondary-server': secondary_server,
            'server': server,
            'source-ip': source_ip,
            'tertiary-key': tertiary_key,
            'tertiary-server': tertiary_server
        }
        if self.user_tacacs is None:
            self.get_user_tacacs(vdom=vdom)
        for i in self.user_tacacs:
            if i['name'] != name:
                continue
            response = self.send_request(
                '{}/user/tacacs+/{}'.format(self.config_url, name),
                action='PUT', payload=payload, attempts=1, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/user/tacacs+'.format(self.config_url), action='POST',
                payload=payload, attempts=1, vdom=vdom)
        self.get_user_tacacs(vdom=vdom)
        return response

    def config_voip_profile(
            self, name, comment='', feature_set='proxy', msrp=None, sccp=None,
            sip=None, vdom=None):
        payload = {
            'name': name,
            'comment': comment,
            'feature-set': feature_set,
            'msrp': msrp,
            'sccp': sccp,
            'sip': sip
        }
        if self.voip_profiles is None:
            self.get_voip_profiles(vdom=vdom)
        for i in self.voip_profiles:
            if i['name'] != name:
                continue
            response = self.send_request(
                '{}/voip/profile/{}'.format(self.config_url, name),
                action='PUT', payload=payload, attempts=1, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/voip/profile'.format(self.config_url),
                action='POST', payload=payload, attempts=1, vdom=vdom)
        self.get_voip_profiles(vdom=vdom)
        return response

    def config_vpn_ipsec_phase1_interface(
            self, name, interface, local_gw, remote_gw, add_gw_route='disable',
            authmethod='psk', auto_discovery_forwarder='disable',
            auto_discovery_receiver='disable', auto_discovery_sender='disable',
            auto_negotiate='enable', certificate=None, comments='', dhgrp=[14],
            dpd='on-demand', dpd_retrycount=3, dpd_retryinterval=20,
            encapsulation='none', fragmentation='enable',
            idle_timeoutinterval=None, ike_version=1,
            ip_fragmentation='post-encapsulation', keepalive=10, keylife=86400,
            localid=None, localid_type='auto', mode='main', mode_cfg='disable',
            monitor=None, nattraversal='enable', negotiate_timeout=30,
            net_device='disable', npu_offload='enable', passive_mode='disable',
            peertype='any', psksecret=None, proposal=['aes256-sha256'],
            rekey='enable', vdom=None, vpn_type='static', xauthtype='disable'):
        idle_timeout = 'disable' if idle_timeoutinterval is None else 'enable'
        proposals = ' '.join(proposal)
        dhgrp.sort(reverse=True)
        dhgrps = ' '.join([str(i) for i in dhgrp])
        payload = {
            'add-gw-route': add_gw_route,
            'authmethod': authmethod,
            'auto-discovery-forwarder': auto_discovery_forwarder,
            'auto-discovery-receiver': auto_discovery_receiver,
            'auto-discovery-sender': auto_discovery_sender,
            'auto-negotiate': auto_negotiate,
            'comments': comments,
            'dhgrp': dhgrps,
            'dpd': dpd,
            'dpd-retrycount': dpd_retrycount,
            'dpd-retryinterval': dpd_retryinterval,
            'encapsulation': encapsulation,
            'fragmentation': fragmentation,
            'idle-timeout': idle_timeout,
            'idle-timeoutinterval': idle_timeoutinterval,
            'ike-version': ike_version,
            'interface': interface,
            'ip-fragmentation': ip_fragmentation,
            'ip-version': 4,
            'keepalive': keepalive,
            'keylife': keylife,
            'localid': localid,
            'localid-type': localid_type,
            'local-gw': local_gw,
            'mode-cfg': mode_cfg,
            'monitor': monitor,
            'name': name,
            'nattraversal': nattraversal,
            'negotiate-timeout': negotiate_timeout,
            'net-device': net_device,
            'npu-offload': npu_offload,
            'passive-mode': passive_mode,
            'peertype': peertype,
            'proposal': proposals,
            'rekey': rekey,
            'remote-gw': remote_gw,
            'type': vpn_type,
            'xauthtype': xauthtype,
        }
        if authmethod == 'signature':
            payload.update({'certificate': certificate})
        else:
            payload.update({'psksecret': psksecret})
        if ike_version == 1:
            payload.update({'mode': mode})
        if self.vpn_ipsec_phase1_interfaces is None:
            self.get_vpn_ipsec_phase1_interfaces(vdom)
        for i in self.vpn_ipsec_phase1_interfaces:
            if i['name'] != name:
                continue
            response = self.send_request(
                '{}/vpn.ipsec/phase1-interface/{}'.format(
                    self.config_url, name),
                action='PUT', payload=payload, attempts=1, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/vpn.ipsec/phase1-interface'.format(self.config_url),
                action='POST', payload=payload, attempts=1, vdom=vdom)
        self.get_vpn_ipsec_phase1_interfaces(vdom)
        return response

    def config_vpn_ipsec_phase2_interface(
            self, name, phase1name, source, destination, addr_type='subnet',
            auto_discovery_forwarder='phase1', auto_discovery_sender='phase1',
            auto_negotiate='disable', comments='', diffserv='disable',
            dhgrp=[14], encapsulation='tunnel-mode', ipv4_df='disable',
            pfs='enable', proposal=['aes256-sha256'], keepalive='disable',
            keylifekbs=5120, keylifeseconds=43200, keylife_type='seconds',
            replay='enable', vdom=None):
        proposals = ' '.join(proposal)
        payload = {
            'auto-discovery-forwarder': auto_discovery_forwarder,
            'auto-discovery-sender': auto_discovery_sender,
            'auto-negotiate': auto_negotiate,
            'comments': comments,
            'diffserv': diffserv,
            'encapsulation': encapsulation,
            'ipv4-df': ipv4_df,
            'name': name,
            'pfs': pfs,
            'phase1name': phase1name,
            'proposal': proposals,
            'keepalive': keepalive,
            'keylife-type': keylife_type,
            'replay': replay
        }
        if addr_type == 'name':
            payload['src-addr-type'] = addr_type
            payload['dst-addr-type'] = addr_type
            payload['src-name'] = source
            payload['dst-name'] = destination
        else:
            payload['src-addr-type'] = addr_type
            payload['dst-addr-type'] = addr_type
            payload['src-subnet'] = source
            payload['dst-subnet'] = destination

        if pfs == 'enable':
            dhgrp.sort(reverse=True)
            dhgrps = ' '.join([str(i) for i in dhgrp])
            payload['dhgrp'] = dhgrps

        if keylife_type == 'seconds':
            payload['keylifeseconds'] = keylifeseconds
        elif keylife_type == 'kbs':
            payload['keylifekbs'] = keylifekbs
        else:
            payload['keylifeseconds'] = keylifeseconds
            payload['keylifekbs'] = keylifekbs

        if self.vpn_ipsec_phase2_interfaces is None:
            self.get_vpn_ipsec_phase2_interfaces(vdom)
        for i in self.vpn_ipsec_phase2_interfaces:
            if i['name'] != name:
                continue
            response = self.send_request(
                '{}/vpn.ipsec/phase2-interface/{}'.format(
                    self.config_url, name),
                action='PUT', payload=payload, attempts=1, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/vpn.ipsec/phase2-interface'.format(self.config_url),
                action='POST', payload=payload, attempts=1, vdom=vdom)
        self.get_vpn_ipsec_phase2_interfaces(vdom)
        return response

    def config_vpn_ssl_realms(
            self, url_path, login_page=None, max_concurrent_user=0,
            radius_server=None, nas_ip='0.0.0.0', radius_port=0,
            virtual_host=None, virtual_host_only='disable',
            virtual_host_server_cert='', vdom=None):
        login_page = url_path if login_page is None else login_page
        payload = {
            'url-path': url_path,
            'max-concurrent-user': max_concurrent_user,
            'login-page': login_page,
            'virtual-host': virtual_host,
            'radius-server': radius_server,
        }
        if radius_server is not None:
            payload['nas-ip'] = nas_ip
            payload['radius-port'] = radius_port
        if virtual_host is not None:
            payload['virtual-host-only'] = virtual_host_only
            if virtual_host_only == 'enable':
                payload['virtual-host-server-cert'] = virtual_host_server_cert
        if self.vpn_ssl_realms is None:
            self.get_vpn_ssl_realms(vdom=vdom)
        for i in self.vpn_ssl_realms:
            if i['url-path'] != url_path:
                continue
            response = self.send_request(
                '{}/vpn.ssl.web/realm/{}'.format(self.config_url, url_path),
                action='PUT', payload=payload, attempts=1, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/vpn.ssl.web/realm'.format(self.config_url), action='POST',
                payload=payload, attempts=1, vdom=vdom)
        self.get_vpn_ssl_realms(vdom=vdom)
        return response

    def config_vpn_ssl_settings(
            self, algorithm='high', authentication_rule=None,
            auth_timeout=28800, default_portal='web-access',
            dns_server1='8.8.8.8', dns_server2='8.8.4.4', dns_suffix='',
            https_redirect='disable', idle_timeout=300, login_attempt_limit=2,
            login_block_time=60, login_timeout=30, port=10443,
            servercert='Fortinet_Factory', source_address=None,
            source_address_negate='disable', source_interface=None,
            ssl_min_proto_ver='tls1-2', tunnel_ip_pools=None, vdom=None):
        if source_address is None:
            source_address = ['all']
        if tunnel_ip_pools is None:
            tunnel_ip_pools = ['SSLVPN_TUNNEL_ADDR1']
        src_addr = [{'name': i} for i in source_address]
        ip_pools = [{'name': i} for i in tunnel_ip_pools]
        if source_interface is None:
            source_interface = []
        src_interface = [{'name': i} for i in source_interface]
        authentication_rule = [] if authentication_rule is None else authentication_rule
        for i in authentication_rule:
            i['groups'] = [{'name': j} for j in i['groups']]
        payload = {
            'algorithm': algorithm,
            'auth-timeout': auth_timeout,
            'default-portal': default_portal,
            'dns-server1': dns_server1,
            'dns-server2': dns_server2,
            'dns-suffix': dns_suffix,
            'https-redirect': https_redirect,
            'idle-timeout': idle_timeout,
            'login-attempt-limit': login_attempt_limit,
            'login-block-time': login_block_time,
            'login-timeout': login_timeout,
            'port': port,
            'servercert': servercert,
            'source-address': src_addr,
            'source-address-negate': source_address_negate,
            'ssl-min-proto-ver': ssl_min_proto_ver,
            'tunnel-ip-pools': ip_pools,
            'source-interface': src_interface,
            'authentication-rule': authentication_rule
        }
        if self.vpn_ssl_settings is None:
            self.get_vpn_ssl_settings(vdom=vdom)
        response = self.send_request(
            '{}/vpn.ssl/settings'.format(self.config_url), action='PUT',
            payload=payload, attempts=1, vdom=vdom)
        self.get_vpn_ssl_settings(vdom=vdom)
        return response

    def config_vpn_ssl_web_portals(
            self, name, tunnel_mode='disable', web_mode='disable',
            allow_user_access=None, forticlient_download='enable',
            forticlient_download_method='direct', ipv6_tunnel_mode='disable',
            limit_user_logins='disable', auto_connect='disable',
            dns_server1='0.0.0.0', dns_server2='0.0.0.0', dns_suffix='',
            host_check='none', ip_mode='range', ip_pools=None, ipv6_pools=None,
            keep_alive='disable', mac_addr_check='disable', os_check='disable',
            save_password='disable', split_dns=None, split_tunneling='enable',
            split_tunneling_routing_address=None,
            split_tunneling_routing_negate='disable', wins_server1='0.0.0.0',
            wins_server2='0.0.0.0', clipboard='enable', custom_lang='',
            display_bookmark='enable', display_connection_tools='enable',
            display_history='enable', display_status='enable',
            heading='SSL-VPN Portal', hide_sso_credential='enable',
            redir_url='', rewrite_ip_uri_ui='disable', smb_min_version='smbv2',
            smb_max_version='smbv3', smb_ntlmv1_auth='disable',
            theme='neutrino', use_sdwan='disable', user_bookmark='enable',
            user_group_bookmark='enable', vdom=None):
        ip_pools = ['SSLVPN_TUNNEL_ADDR1'] if ip_pools is None else ip_pools
        ip_pools = [{'name': i for i in ip_pools}]
        split_dns = [] if split_dns is None else split_dns
        if split_tunneling_routing_address is None:
            split_tunneling_routing_address = []
        if allow_user_access is None:
            allow_user_access = [
                'web', 'ftp', 'smb', 'sftp', 'telnet', 'ssh', 'vnc', 'rdp',
                'ping']
        allow_user_access = ' '.join(allow_user_access)
        payload = {
            'name': name,
            'tunnel-mode': tunnel_mode,
            'web-mode': web_mode,
            'ipv6-tunnel-mode': ipv6_tunnel_mode,
            'allow-user-access': allow_user_access,
            'limit-user-logins': limit_user_logins,
            'forticlient-download': forticlient_download,
            'forticlient-download-method': forticlient_download_method
        }
        if tunnel_mode == 'enable':
            payload['ip-mode'] = ip_mode
            payload['auto-connect'] = auto_connect
            payload['keep-alive'] = keep_alive
            payload['save-password'] = save_password
            payload['ip-pools'] = ip_pools
            payload['split-tunneling'] = split_tunneling
            if split_tunneling == 'enable':
                payload['split-tunneling-routing-negate'] = split_tunneling_routing_negate
                payload['split-tunneling-routing-address'] = split_tunneling_routing_address
            payload['dns-server1'] = dns_server1
            payload['dns-server2'] = dns_server2
            payload['wins-server1'] = wins_server1
            payload['wins-server2'] = wins_server2
            payload['host-check'] = host_check
            payload['mac-addr-check'] = mac_addr_check
            payload['os-check'] = os_check
            payload['split-dns'] = split_dns
        if web_mode == 'enable':
            payload['display-bookmark'] = display_bookmark
            payload['user-bookmark'] = user_bookmark
            payload['user-group-bookmark'] = user_group_bookmark
            payload['display-connection-tools'] = display_connection_tools
            payload['display-history'] = display_history
            payload['display-status'] = display_status
            payload['rewrite-ip-uri-ui'] = rewrite_ip_uri_ui
            payload['heading'] = heading
            payload['redir-url'] = redir_url
            payload['theme'] = theme
            payload['custom-lang'] = custom_lang
            payload['smb-ntlmv1-auth'] = smb_ntlmv1_auth
            payload['smb-min-version'] = smb_min_version
            payload['smb-max-version'] = smb_max_version
            payload['use-sdwan'] = use_sdwan
            payload['clipboard'] = clipboard
            payload['hide-sso-credential'] = hide_sso_credential
        if tunnel_mode == 'enable' or web_mode == 'enable':
            payload['dns-suffix'] = dns_suffix
        if self.vpn_ssl_web_portals is None:
            self.get_vpn_ssl_web_portals(vdom=vdom)
        for i in self.vpn_ssl_web_portals:
            if i['name'] != name:
                continue
            response = self.send_request(
                '{}/vpn.ssl.web/portal/{}'.format(self.config_url, name),
                action='PUT', payload=payload, attempts=1, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/vpn.ssl.web/portal'.format(self.config_url), action='POST',
                payload=payload, attempts=1, vdom=vdom)
        self.get_vpn_ssl_web_portals(vdom=vdom)
        return response

    def config_webfilter_ftgd_local_cat(
            self, desc, rename=None, status='enable', vdom="root"):
        payload = {
            'desc': desc,
            'status': status
        }
        if rename is not None:
            payload['desc'] = rename
        if self.webfilter_ftgd_local_cats is None:
            self.get_webfilter_ftgd_local_cats(vdom=vdom)

        for entry in self.webfilter_ftgd_local_cats:
            if entry['desc'] != desc:
                continue
            payload['id'] = entry['id']
            response = self.send_request(
                '{}/webfilter/ftgd-local-cat/{}'.format(self.config_url, desc),
                action='PUT', payload=payload, attempts=1, vdom=vdom)
            break
        else:
            payload['id'] = 0
            response = self.send_request(
                '{}/webfilter/ftgd-local-cat'.format(self.config_url),
                action='POST', payload=payload, attempts=1, vdom=vdom)
        self.get_webfilter_ftgd_local_cats(vdom=vdom)
        return response

    def config_webfilter_profile(
            self, name, comment='', error_allow=False, feature_set='flow',
            filters=None, options=None, rate_server_ip=False, vdom=None):
        ftgd_options = ''
        if error_allow:
            ftgd_options += 'error-allow '
        if rate_server_ip:
            ftgd_options += 'rate-server-ip '
        if filters is None:
            filters = []
        if options is None:
            options = ''
        payload = {
            'name': name,
            'comment': comment,
            'feature-set': feature_set,
            'options': options,
            'ftgd-wf': {
                'filters': filters,
                'options': ftgd_options
            }
        }
        if self.webfilter_profiles is None:
            self.get_webfilter_profiles(vdom=vdom)
        for entry in self.webfilter_profiles:
            if entry['name'] != name:
                continue
            response = self.send_request(
                '{}/webfilter/profile/{}'.format(self.config_url, name),
                action='PUT', payload=payload, attempts=1, vdom=vdom)
            break
        else:
            response = self.send_request(
                '{}/webfilter/profile'.format(self.config_url),
                action='POST', payload=payload, attempts=1, vdom=vdom)
        self.get_webfilter_profiles(vdom=vdom)
        return response

    def delete_firewall_address(self, name, vdom=None):
        url_name = requests.utils.quote(name, safe='')
        if self.firewall_addresses is None:
            self.get_firewall_addresses(vdom=vdom)
        for entry in self.firewall_addresses:
            if entry['name'] != name:
                continue
            response = self.send_request(
                '{}/firewall/address/{}'.format(self.config_url, url_name),
                action='DELETE', attempts=1, vdom=vdom)
            if response is not None:
                self.get_firewall_addresses(vdom=vdom)
            return response
        else:
            self.logger.warning('Entry does not exist')
            return None

    def delete_firewall_addrgrp(self, name, vdom=None):
        url_name = requests.utils.quote(name, safe='')
        if self.firewall_addrgrps is None:
            self.get_firewall_addrgrps(vdom=vdom)
        for entry in self.firewall_addrgrps:
            if entry['name'] != name:
                continue
            response = self.send_request(
                '{}/firewall/addrgrp/{}'.format(self.config_url, url_name),
                action='DELETE', attempts=1, vdom=vdom)
            if response is not None:
                self.get_firewall_addrgrps(vdom=vdom)
            return response
        else:
            self.logger.warning('Entry does not exist')
            return None

    def delete_firewall_policy(self, entry, vdom=None):
        if self.firewall_policies is None:
            self.get_firewall_policies(vdom=vdom)
        for i in self.firewall_policies:
            if i['policyid'] != entry:
                continue
            response = self.send_request(
                '{}/firewall/policy/{}'.format(self.config_url, entry),
                action='DELETE', attempts=1, vdom=vdom)
            if response is not None:
                self.get_firewall_policies(vdom=vdom)
            return response
        else:
            self.logger.warning('Entry does not exist')

    def delete_router_static(self, entry, vdom=None):
        if self.router_static is None:
            self.get_router_static(vdom=vdom)
        for i in self.router_static:
            if i['seq-num'] != entry:
                continue
            response = self.send_request(
                '{}/router/static/{}'.format(self.config_url, entry),
                action='DELETE', attempts=1, vdom=vdom)
            self.get_router_static(vdom=vdom)
            return response
        else:
            self.logger.warning('Entry does not exist')

    def delete_system_admin(self, name):
        if self.system_admins is None:
            self.get_system_admins()
        for i in self.system_admins:
            if i['name'] != name:
                continue
            response = self.send_request(
                '{}/system/admin/{}'.format(self.config_url, name),
                action='DELETE', attempts=1)
            self.get_system_admins()
            return response
        else:
            self.logger.warning('Entry does not exist')

    def delete_system_dhcp_server(self, entry, vdom=None):
        if self.system_dhcp_servers is None:
            self.get_system_dhcp_servers(vdom=vdom)
        for i in self.system_dhcp_servers:
            if i['id'] != entry:
                continue
            response = self.send_request(
                '{}/system.dhcp/server/{}'.format(self.config_url, entry),
                action='DELETE', attempts=1, vdom=vdom)
            self.get_system_dhcp_servers(vdom=vdom)
            return response
        else:
            self.logger.warning('Entry does not exist')

    def delete_system_dhcp6_server(self, entry, vdom=None):
        if self.system_dhcp6_servers is None:
            self.get_system_dhcp6_servers(vdom=vdom)
        for i in self.system_dhcp6_servers:
            if i['id'] != entry:
                continue
            response = self.send_request(
                '{}/system.dhcp6/server/{}'.format(self.config_url, entry),
                action='DELETE', attempts=1, vdom=vdom)
            self.get_system_dhcp6_servers(vdom=vdom)
            return response
        else:
            self.logger.warning('Entry does not exist')

    def delete_system_interface(self, name, vdom=None):
        if self.system_interfaces is None:
            self.get_system_interfaces(vdom=vdom)
        for i in self.system_interfaces:
            if i['name'] != name:
                continue
            response = self.send_request(
                '{}/system/interface/{}'.format(self.config_url, name),
                action='DELETE', attempts=1, vdom=vdom)
            self.get_system_interfaces(vdom=vdom)
            return response
        else:
            self.logger.warning('Entry does not exist')

    def delete_system_session_helper(self, name):
        if self.system_session_helpers is None:
            self.get_system_session_helpers()
        for entry in self.system_session_helpers:
            if entry['name'] != name:
                continue
            response = self.send_request(
                '{}/system/session-helper/{}'.format(
                    self.config_url, entry["id"]),
                action='DELETE', attempts=1)
            if response is not None:
                self.get_system_session_helpers()
                break
            return response
        else:
            self.logger.warning('Entry does not exist')
            return None

    def delete_system_switch_interface(self, name, vdom=None):
        if self.system_switch_interfaces is None:
            self.get_system_switch_interfaces(vdom=vdom)
        for i in self.system_switch_interfaces:
            if i['name'] != name:
                continue
            response = self.send_request(
                '{}/system/switch-interface/{}'.format(self.config_url, name),
                action='DELETE', attempts=1, vdom=vdom)
            self.get_system_switch_interfaces(vdom=vdom)
            return response
        else:
            self.logger.warning('Entry does not exist')

    def delete_system_virtual_switch(self, name, vdom=None):
        if self.system_virtual_switches is None:
            self.get_system_virtual_switches(vdom=vdom)
        for i in self.system_virtual_switches:
            if i['name'] != name:
                continue
            response = self.send_request(
                '{}/system/virtual-switch/{}'.format(self.config_url, name),
                action='DELETE', attempts=1, vdom=vdom)
            self.get_system_virtual_switches(vdom=vdom)
            return response
        else:
            self.logger.warning('Entry does not exist')

    def delete_system_vdom(self, name):
        if self.system_vdoms is None:
            self.get_system_vdoms()
        for entry in self.system_vdoms:
            if entry['name'] != name:
                continue
            response = self.send_request(
                '{}/system/vdom/{}'.format(self.config_url, name),
                action='DELETE', attempts=1)
            self.get_system_vdoms()
            return response
        else:
            self.logger.warning('Entry does not exist')

    def forticloud_login(
            self, email, password, domain='global', send_logs=True):
        payload = {
            'domain': domain,
            'email': email,
            'password': password,
            'send_logs': send_logs
        }
        response = self.send_request(
            '{}/registration/forticloud/login'.format(self.monitor_url),
            action='POST', payload=payload, attempts=1, timeout=(15, 20))
        return response

    def reboot(self, event_log_message='None'):
        payload = {
            'event_log_message': event_log_message
        }
        response = self.send_request(
            '{}/system/os/reboot'.format(self.monitor_url), action='POST',
            payload=payload, attempts=1)
        return response

    def restore_config(self, config_id, scope='global', source='revision'):
        payload = {
            'config_id': config_id,
            'scope': scope,
            'source': source,
        }
        if self.system_config_revisions is None:
            self.get_system_config_revisions()
        response = self.send_request(
            '{}/system/config/restore'.format(self.monitor_url), action='POST',
            payload=payload, attempts=1)
        return response

    def save_config_revision(self, comments):
        payload = {
            'comments': comments
        }
        if self.system_config_revisions is None:
            self.get_system_config_revisions()
        response = self.send_request(
            '{}/system/config-revision/save'.format(self.monitor_url),
            action='POST', payload=payload, attempts=1)
        self.get_system_config_revisions()
        return response

    def set_forticloud_proxy(self, proxy=False, token=None):
        forticloud_url = 'https://www.forticloud.com/forticloudapi/v1/fgt/'
        if proxy:
            self.config_url = '{}{}/api/v2/cmdb'.format(
                forticloud_url, self.serial)
            self.monitor_url = '{}{}/api/v2/monitor'.format(
                forticloud_url, self.serial)
            self.forticloud = True
            self.forticloud_token = token
        else:
            self.config_url = 'https://{}:{}/api/v2/cmdb'.format(
                self.ip, str(self.port))
            self.monitor_url = 'https://{}:{}/api/v2/monitor'.format(
                self.ip, str(self.port))
            self.forticloud = False
            self.forticloud_token = None

    def update_firmware(
            self, filename, file_location=None, source='fortiguard',
            timeout=120):
        payload = {
            'source': source,
            'filename': filename,
            'format_partition': True,
        }
        if self.firmware is None:
            self.get_system_status()
        if source == 'upload':
            try:
                with open('{}{}'.format(file_location, filename), 'rb') as file:
                    content = b64encode(file.read())
                    payload['file_content'] = content.decode('ascii')
            except TypeError:
                return None
        response = self.send_request(
            '{}/system/firmware/upgrade'.format(self.monitor_url),
            action='POST', payload=payload, attempts=1, timeout=timeout)
        return response

    def download_fsw_firmware(self, image_id, timeout=120):
        payload = {
            'image_id': image_id
        }
        response = self.send_request(
            '{}/switch-controller/fsw-firmware/download'.format(
                self.monitor_url),
            action='POST', payload=payload, attempts=1, timeout=timeout)
        return response

    def push_fsw_firmware(self, serial, image_id, timeout=120):
        payload = {
            'serial': serial,
            'image_id': image_id
        }
        response = self.send_request(
            '{}/switch-controller/fsw-firmware/push '.format(self.monitor_url),
            action='POST', payload=payload, attempts=1, timeout=timeout)
        return response

    def get_config_scripts(self):
        response = self.send_request(
            '{}/system/config-script'.format(self.monitor_url))
        return response

    def upload_config_script(self, name, content):
        b64_content = b64encode(bytes(content, 'utf-8')).decode('ascii')
        payload = {
            'filename': name,
            'file_content': b64_content
        }
        response = self.send_request(
            '{}/system/config-script/upload'.format(self.monitor_url),
            action='POST', attempts=1, payload=payload)
        return response

    def delete_config_scripts(self, entries):
        payload = {
            'id_list': entries,
        }
        response = self.send_request(
            '{}/system/config-script/delete'.format(self.monitor_url),
            action='POST', attempts=1, payload=payload)
        return response

    def send_request(
            self, url, action="GET", attempts=3, filter=None, format=None,
            headers=None, payload=None, sort=None, start=None, timeout=(5, 10),
            vdom=None, verify=False):
        if headers is None:
            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "deflate",
                "Content-Type": "application/json",
                "Authorization": f'Bearer {self.key}'
            }
        params = {
            'filter': filter,
            'format': format,
            'sort': sort,
            'start': start,
            'vdom': vdom,
        }

        tries = 0
        while (tries < attempts):
            if self.forticloud and self.forticloud_errors > 5:
                self.logger.warning(
                    '>> request not sent, FortiCloud errors too high')
                return None

            tries += 1
            self.logger.info('> {} | {}'.format(url, action))
            self.logger.info("PARAMS")
            self.logger.info(json.dumps(params or {}, indent=4))
            self.logger.info("PAYLOAD")
            self.logger.info(json.dumps(payload or {}, indent=4))
            try:
                if action == 'GET':
                    response = requests.get(
                        url=url, headers=headers, params=params,
                        timeout=timeout, verify=verify)

                elif action == 'POST':
                    attempts = 1
                    response = requests.post(
                        url=url, headers=headers, json=payload, params=params,
                        timeout=timeout, verify=verify)

                elif action == 'PUT':
                    attempts = 1
                    response = requests.put(
                        url=url, headers=headers, json=payload, params=params,
                        timeout=timeout, verify=verify)

                elif action == 'DELETE':
                    attempts = 1
                    response = requests.delete(
                        url=url, headers=headers, json=payload, params=params,
                        timeout=timeout, verify=verify)

                else:
                    print('Method not supported: {}'.format(action))
                    return None

            except (ConnectTimeout, ReadTimeout):
                self.logger.warning('>> Timeout, retry')
                continue

            except (ConnectionError, HTTPError):
                self.logger.warning('>> Failed to establish a new connection')
                break

            if response.ok:
                self.logger.info('>> Response: {} {} - {}'.format(
                    action, response.status_code, response.reason))
                if response.text:
                    try:
                        return response.json()
                    except JSONDecodeError:
                        return response.text

            # Handle rate limiting
            elif response.status_code == 429:
                self.logger.warning('>> Response: {} {} - {}'.format(
                    action, response.status_code, response.reason))
                sleep(1)
                if self.forticloud:
                    self.forticloud_errors += 1
                continue

            # Handle expected server error codes
            elif response.status_code > 299:
                self.logger.warning('>> Response: {} {} - {} \n text ---> {}'.format(
                    action, response.status_code, response.reason, response.text))
                self.logger.track_api_failures(response)
                if self.forticloud:
                    self.forticloud_errors += 1
                break

            # Catch all
            else:
                self.logger.warning('>> Response: {} {} - {}'.format(
                    action, response.status_code, response.reason))
                response.raise_for_status()

        # Return None if unsuccessful after all attempts
        self.logger.warning('>> Unable to get response after all attempts')
        return None
