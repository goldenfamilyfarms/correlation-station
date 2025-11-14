path_elements = [
    {"EVC_ID": "454706", "ELEMENT_REFERENCE": "1663821", "ELEMENT_CATEGORY": "VPLS SVC"},
    {"EVC_ID": "454706", "ELEMENT_TYPE": "NETWORK LINK", "ELEMENT_REFERENCE": "1663821", "ELEMENT_CATEGORY": "VPLS SVC"},
]

devices = {
    "MCKYTXUH5ZW": "ETH PORT 5",
    "DLLATX371CW": "XE-3/0/2",
    "MCKNTXWF1CW": "AE17",
    "MCKNTXWF0QW": "XE-0/0/75",
    "MCKYTXUH2AW": "GE-0/0/4",
}

db_dev_list = [
    {
        "tid": "DLLATX371CW",
        "port_id": "XE-3/0/2",
        "vendor": "JUNIPER",
        "vlan_id": "3030",
        "description": True,
        "model": "MX480",
        "evc_id": "407294",
        "e_access_ip": "24.73.241.25",
    },
    {
        "tid": "MCKNTXWF1CW",
        "port_id": "AE17",
        "vendor": "JUNIPER",
        "vlan_id": "3030",
        "description": True,
        "model": "MX480",
        "evc_id": "407294",
        "e_access_ip": "67.79.252.145",
    },
    {
        "tid": "MCKNTXWF0QW",
        "port_id": "XE-0/0/75",
        "vendor": "JUNIPER",
        "vlan_id": "3030",
        "description": True,
        "model": "QFX5100-96S",
    },
    {
        "tid": "MCKYTXUH2AW",
        "port_id": "GE-0/0/4",
        "vendor": "JUNIPER",
        "vlan_id": "3030",
        "description": True,
        "model": "EX4200-24F",
    },
    {
        "tid": "MCKYTXUH5ZW",
        "port_id": "ETH PORT 5",
        "vendor": "RAD",
        "vlan_id": "3030",
        "description": True,
        "model": "ETX203AX/2SFP/2UTP2SFP",
    },
]

juniper_paired_router1_network_data = {
    "tid": "DLLATX371CW",
    "vendor": "JUNIPER",
    "model": "MX480",
    "vlan_id": "3030",
    "port_id": "XE-3/0/2",
    "description": True,
    "e_access_ip": "24.73.241.25",
    "evc_id": "407294",
}

juniper_paired_router2_network_data = {
    "tid": "MCKNTXWF1CW",
    "vendor": "JUNIPER",
    "model": "MX480",
    "vlan_id": "3030",
    "port_id": "AE17",
    "description": True,
    "e_access_ip": "67.79.252.145",
    "evc_id": "407294",
}

juniper_qw_network_data = {
    "tid": "MCKNTXWF0QW",
    "vendor": "JUNIPER",
    "model": "QFX5100-96S",
    "vlan_id": "3030",
    "port_id": "XE-0/0/75",
    "description": True,
}

juniper_aw_network_data = {
    "tid": "MCKYTXUH2AW",
    "vendor": "JUNIPER",
    "model": "EX4200-24F",
    "vlan_id": "3030",
    "port_id": "GE-0/0/4",
    "description": True,
}

rad_zw_network_data = {
    "tid": "MCKYTXUH5ZW",
    "vendor": "RAD",
    "model": "ETX203AX/2SFP/2UTP2SFP",
    "vlan_id": "3030",
    "port_id": "ETH PORT 5",
    "description": True,
}

device_info = {
    "tid": "CHCGILDT5CW",
    "port_id": "TE0/1/0/2",
    "vendor": "CISCO",
    "vlan_id": "11002:OV-553//IV-1101",
    "description": True,
    "model": "ASR 9010",
    "ipv4": "35.134.133.25/29",
    "ipv6": "2600:6C3A::48/127",
}

device_config = {
    "command": "seefa-cd-show-interface-config.json",
    "parameters": {"interface": "te0/1/0/2"},
    "result": [
        {"interface": "TenGigE0/1/0/2", "description": '"NNI2::INTADEL:31.KGFD.000168..CHTR:"'},
        {
            "interface": "TenGigE0/1/0/2.9013 l2transport",
            "description": "MGMT:::STCIMOGQ1ZW:",
            "encapsulation": "dot1q 2606",
        },
        {
            "interface": "TenGigE0/1/0/2.9014 l2transport",
            "description": ":MGMT::BFGVILDJ1ZW:",
            "encapsulation": "dot1q 2615",
        },
        {
            "interface": "TenGigE0/1/0/2.11001",
            "description": "CUST:FIA:SPECTRUM BRANDS - NATIONAL@31100 W 196TH ST:91.L1XX.804441..CHTR:",
            "ipv4": ["35.134.132.169 255.255.255.248"],
            "ipv6": ["2600:6c3a::10:0:0:42/127"],
            "encapsulation": "dot1q 552",
        },
        {
            "interface": "TenGigE0/1/0/2.11002",
            "description": "CUST:FIA:BUILDERS FIRSTSOURCE@1045 S 6TH ST:60.L1XX.993969..CHTR:",
            "ipv4": ["35.134.133.25 255.255.255.248"],
            "ipv6": ["2600:6c3a::48/127"],
            "encapsulation": "dot1q 553",
        },
        {
            "interface": "TenGigE0/1/0/2.11003",
            "description": "CUST:FIA:TWE NONWOVENS US@9403 AVIONICS DR:26.L1XX.990099..CHTR:",
            "ipv4": ["35.134.150.65 255.255.255.248"],
            "ipv6": ["2600:6c3a::10:0:0:1008/127"],
            "encapsulation": "dot1q 2586",
        },
    ],
}

device_config1 = {
    "command": "seefa-cd-show-interface-config.json",
    "result": {
        "data": {
            "configuration": {
                "@xmlns": "http://xml.juniper.net/xnm/1.1/xnm",
                "@junos:commit-localtime": "2023-10-19 14:15:50 UTC",
                "interfaces": {
                    "interface": {
                        "description": "AGG:MNTVALAP1QW:ae18:10.27.19.45:20001.GE40L.MNTVALAP1CW.MNTVALAP1QW",
                        "name": "ae18",
                        "unit": [
                            {
                                "name": "1228",
                                "family": {"vpls": {"policer": {"output": "50m"}, "apply-groups": "BPDU-Filter"}},
                                "bandwidth": "50m",
                                "vlan-id": "1228",
                                "encapsulation": "vlan-vpls",
                                "description": "CUST:ELAN:CITY OF CALERA - FIRE ST@360 GEORGE ROY PKWY:20.L1XX.902572..TWCC:VPLS454706",
                            },
                            {
                                "name": "1228",
                                "family": {"vpls": {"policer": {"output": "50m"}, "apply-groups": "BPDU-Filter"}},
                                "bandwidth": "50m",
                                "vlan-id": "1228",
                                "encapsulation": "vlan-vpls",
                                "description": "CUST:ELAN:CITY OF CALERA - FIRE ST@360 GEORGE ROY PKWY:20.L1XX.902572..TWCC:VPLS454706",
                            },
                        ],
                        "apply-groups": ["SERVICEPORT", "SERVICEPORT-MS", "TP_TDIST_LAG"],
                    }
                },
                "@junos:commit-user": "sensor",
                "@junos:commit-seconds": "1697836201",
            }
        }
    },
    "parameters": {"interface": "ae18"},
}

device_config2 = {
    "command": "get-routing instances-full.json",
    "result": [
        {
            "orchState": "active",
            "properties": {
                "relationships": {
                    "networkConstruct": {"data": {"type": "networkConstructs", "id": "MNTVALAP1CW.CHTRSE.COM"}}
                },
                "interfaces": [
                    {"config": {"interface": "ae17.900"}},
                    {"config": {"interface": "ae17.1205"}},
                    {"config": {"interface": "ae18.900"}},
                    {"config": {"interface": "ae18.1228"}},
                    {"config": {"interface": "ae18.1230"}},
                    {"config": {"interface": "ae18.1236"}},
                ],
                "vlans": [{"vlanId": 900}],
                "config": {
                    "type": "vpls",
                    "routeTarget": "7843:454706",
                    "additionalConfiguration": {"noTunnelServices": False, "interfaceMacLimit": "512"},
                    "description": "TRANS:ELAN:CITY OF CALERA - FIRE ST:VPLS454706:",
                },
                "name": "CITY_OF_CALERA_454706.ELAN",
            },
            "label": "RI::CITY_OF_CALERA_454706.ELAN",
        }
    ],
}

device_config3 = {
    "command": "get-routing instances-full.json",
    "result": {
        "orchState": "active",
        "properties": {
            "relationships": {
                "networkConstruct": {"data": {"type": "networkConstructs", "id": "MNTVALAP1CW.CHTRSE.COM"}}
            },
            "interfaces": [
                {"config": {"interface": "ae17.900"}},
                {"config": {"interface": "ae17.1205"}},
                {"config": {"interface": "ae18.900"}},
                {"config": {"interface": "ae18.1228"}},
                {"config": {"interface": "ae18.1230"}},
                {"config": {"interface": "ae18.1236"}},
            ],
            "vlans": [{"vlanId": 900}],
            "config": {
                "type": "vpls",
                "routeTarget": "7843:454706",
                "additionalConfiguration": {"noTunnelServices": False, "interfaceMacLimit": "512"},
                "description": "TRANS:ELAN:CITY OF CALERA - FIRE ST:VPLS454706:",
            },
            "name": "te0/1/0/2:11002:OV-553//IV-1101:",
            "description": "cid",
            "virtual-circuit-id": "1234",
        },
        "label": "RI::CITY_OF_CALERA_454706.ELAN",
    },
}

device_config4 = {
    "command": "seefa-cd-show-interface-config.json",
    "parameters": {"interface": "te0/0/0/8"},
    "result": [
        {
            "interface": "TenGigE0/0/0/8",
            "description": "chc00135680,-,level3,l2enni,-,tge,Ports008.807.01.44_3and4|LEVEL3NNI",
        },
        {
            "interface": "TenGigE0/0/0/8.102 l2transport",
            "description": "chc00135680,chc00427479,level3,l2epl,acr01arsnsc_0/2/1/3.102,100m,172.31.96.35_1-269498155",
            "encapsulation": "dot1q 102",
        },
        {
            "interface": "TenGigE0/0/0/8.2275 l2transport",
            "description": "chc00135680,chc00341779,level3,l2epl,acr10mtgmal_0/5/1/0.2275,10m,172.31.151.34_1-231162922",
            "encapsulation": "dot1q 2275",
        },
        {
            "interface": "TenGigE0/0/0/8.2282 l2transport",
            "description": "chc00135680,chc00426956,l3,l2epl,acr05sghlga_0/1/0/7.2282,50m,172.31.160.160_1-254644249",
            "encapsulation": "dot1q 2282",
        },
        {
            "interface": "TenGigE0/0/0/8.2283 l2transport",
            "description": "CARR:ELINE:LEVEL 3 COMMUNICATIONS LEGACY CHTR@56 MARIETTA ST NW:93.L1XX.800996..TWCC:GOV0061 - 1843 FOREMAN DR",
            "encapsulation": "dot1q 2283",
        },
    ],
}

network_associations = [
    {
        "networkInstId": "1079410",
        "networkHumId": "NE.VRFID.417060.CAYUGA MEDICAL ASSOCIATES",
        "networkRevNbr": "1",
        "networkStatus": "Live",
        "assocInstId": "34411",
        "associationName": "EVC ID NUMBER/NETWORK",
        "associationType": "NETWORK TO EVC ID",
        "associationValue": "417060",
        "associationObjectType": "Number",
        "numberRangeName": "MANUAL ASSIGNMENT RETAIL/CARRIER RANGE 0018",
    }
]

show_interfaces = {
    "command": "seefa-cd-show-interface-config.json",
    "result": {
        "data": {
            "configuration": {
                "@xmlns": "http://xml.juniper.net/xnm/1.1/xnm",
                "@junos:commit-localtime": "2023-10-19 14:15:50 UTC",
                "interfaces": {
                    "interface": {
                        "description": "AGG:MNTVALAP1QW:ae18:10.27.19.45:20001.GE40L.MNTVALAP1CW.MNTVALAP1QW",
                        "name": "ae18",
                        "unit": [
                            {
                                "name": "1228",
                                "family": {"vpls": {"policer": {"output": "50m"}, "apply-groups": "BPDU-Filter"}},
                                "bandwidth": "50m",
                                "vlan-id": "1228",
                                "encapsulation": "vlan-vpls",
                                "description": "CUST:ELAN:CITY OF CALERA - FIRE ST@360 GEORGE ROY PKWY:20.L1XX.902572..TWCC:VPLS454706",
                            },
                            {
                                "name": "1228",
                                "family": {"vpls": {"policer": {"output": "50m"}, "apply-groups": "BPDU-Filter"}},
                                "bandwidth": "50m",
                                "vlan-id": "1228",
                                "encapsulation": "vlan-vpls",
                                "description": "CUST:ELAN:CITY OF CALERA - FIRE ST@360 GEORGE ROY PKWY:20.L1XX.902572..TWCC:VPLS454706",
                            },
                        ],
                        "apply-groups": ["SERVICEPORT", "SERVICEPORT-MS", "TP_TDIST_LAG"],
                    }
                },
                "@junos:commit-user": "sensor",
                "@junos:commit-seconds": "1697836201",
            }
        }
    },
    "parameters": {"interface": "ae18"},
}

juniper_data1 = {
    "command": "seefa-cd-show-interface-config.json",
    "result": {
        "data": {
            "configuration": {
                "@xmlns": "http://xml.juniper.net/xnm/1.1/xnm",
                "@junos:commit-localtime": "2023-10-17 07:40:18 UTC",
                "interfaces": {
                    "interface": {
                        "aggregated-ether-options": {"lacp": {"active": None, "periodic": "fast"}, "link-speed": "40g"},
                        "description": "AGG:MNTVALAP1QW:ae18:10.27.19.45:20001.GE40L.MNTVALAP1CW.MNTVALAP1QW",
                        "name": "ae18",
                        "unit": [
                            {
                                "name": "1228",
                                "family": {"vpls": {"policer": {"output": "50m"}, "apply-groups": "BPDU-Filter"}},
                                "bandwidth": "50m",
                                "vlan-id": "1228",
                                "encapsulation": "vlan-vpls",
                                "description": "CUST:ELAN:CITY OF CALERA - FIRE ST@360 GEORGE ROY PKWY:20.L1XX.902572..TWCC:VPLS454706",
                            }
                        ],
                        "apply-groups": ["SERVICEPORT", "SERVICEPORT-MS", "TP_TDIST_LAG"],
                    }
                },
                "@junos:commit-user": "e774658",
                "@junos:commit-seconds": "1697528418",
            }
        }
    },
    "parameters": {"interface": "ae18"},
}

juniper_data2 = {
    "command": "get-routinginstances-full.json",
    "result": [
        {
            "orchState": "active",
            "properties": {
                "relationships": {
                    "networkConstruct": {"data": {"type": "networkConstructs", "id": "MNTVALAP1CW.CHTRSE.COM"}}
                },
                "interfaces": [
                    {"config": {"interface": "ae17.900"}},
                    {"config": {"interface": "ae17.1205"}},
                    {"config": {"interface": "ae18.900"}},
                    {"config": {"interface": "ae18.1228"}},
                    {"config": {"interface": "ae18.1230"}},
                    {"config": {"interface": "ae18.1236"}},
                ],
                "vlans": [{"vlanId": 900}],
                "config": {
                    "type": "vpls",
                    "routeTarget": "7843:454706",
                    "additionalConfiguration": {"noTunnelServices": False, "interfaceMacLimit": "512"},
                    "description": "TRANS:ELAN:CITY OF CALERA - FIRE ST:VPLS454706:",
                },
                "name": "CITY_OF_CALERA_454706.ELAN",
            },
            "label": "RI::CITY_OF_CALERA_454706.ELAN",
        }
    ],
    "parameters": {},
}
