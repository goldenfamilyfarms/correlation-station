fia = {
    "customerName": "TEST ACCT",
    "serviceName": "51.L1XX.010158..TWCC",
    "customerType": "CUST",
    "modelVersion": "2.0",
    "serviceType": "FIA",
    "serviceMedia": "FIBER",
    "topology": [
        {
            "model": "ONF_TAPI",
            "version": "2.0.0",
            "data": {
                "node": [
                    {
                        "uuid": "AUSDTXIR2CW",
                        "name": [
                            {"name": "hostName", "value": "AUSDTXIR2CW"},
                            {"name": "deviceRole", "value": "PE"},
                            {"name": "vendor", "value": "JUNIPER"},
                            {"name": "model", "value": "MX480"},
                            {"name": "managementIP", "value": "71.42.150.66"},
                            {"name": "address", "value": "11921 N MOPAC EXPY 78759"},
                            {"name": "fqdn", "value": "AUSDTXIR2CW.DEV.CHTRSE.COM"},
                            {"name": "equipmentStatus", "value": "LIVE"},
                        ],
                        "ownedNodeEdgePoint": [
                            {
                                "uuid": "AUSDTXIR2CW-ET-2/2/0",
                                "name": [
                                    {"name": "name", "value": "ET-2/2/0"},
                                    {"name": "portRole", "value": "INNI"},
                                    {"name": "transportId", "value": "51001.GE40L.AUSDTXIR2CW.AUSDTXIR2QW"},
                                    {"name": "lagMember", "value": "AE0"},
                                ],
                            },
                            {
                                "uuid": "AUSDTXIR2CW-ET-2/2/1",
                                "name": [
                                    {"name": "name", "value": "ET-2/2/1"},
                                    {"name": "portRole", "value": "INNI"},
                                    {"name": "transportId", "value": "51001.GE40L.AUSDTXIR2CW.AUSDTXIR2QW"},
                                    {"name": "lagMember", "value": "AE0"},
                                ],
                            },
                        ],
                    },
                    {
                        "uuid": "AUSDTXIR2QW",
                        "name": [
                            {"name": "hostName", "value": "AUSDTXIR2QW"},
                            {"name": "deviceRole", "value": "AGG"},
                            {"name": "vendor", "value": "JUNIPER"},
                            {"name": "model", "value": "QFX5100-96S"},
                            {"name": "managementIP", "value": "71.42.150.235"},
                            {"name": "address", "value": "11921 N MOPAC EXPY 78759"},
                            {"name": "fqdn", "value": "AUSDTXIR2QW.CHTRSE.COM"},
                            {"name": "equipmentStatus", "value": "LIVE"},
                        ],
                        "ownedNodeEdgePoint": [
                            {
                                "uuid": "AUSDTXIR2QW-ET-0/0/99",
                                "name": [
                                    {"name": "name", "value": "ET-0/0/99"},
                                    {"name": "portRole", "value": "INNI"},
                                    {"name": "transportId", "value": "51001.GE40L.AUSDTXIR2CW.AUSDTXIR2QW"},
                                    {"name": "lagMember", "value": "AE0"},
                                ],
                            },
                            {
                                "uuid": "AUSDTXIR2QW-ET-1/0/99",
                                "name": [
                                    {"name": "name", "value": "ET-1/0/99"},
                                    {"name": "portRole", "value": "INNI"},
                                    {"name": "transportId", "value": "51001.GE40L.AUSDTXIR2CW.AUSDTXIR2QW"},
                                    {"name": "lagMember", "value": "AE0"},
                                ],
                            },
                            {
                                "uuid": "AUSDTXIR2QW-GE-1/0/81",
                                "name": [
                                    {"name": "name", "value": "GE-1/0/81"},
                                    {"name": "portRole", "value": "INNI"},
                                    {"name": "transportId", "value": "51001.GE1.AUSDTXIR2QW.CNI2TXA49ZW"},
                                ],
                            },
                        ],
                    },
                    {
                        "uuid": "CNI2TXA49ZW",
                        "name": [
                            {"name": "hostName", "value": "CNI2TXA49ZW"},
                            {"name": "deviceRole", "value": "CPE"},
                            {"name": "vendor", "value": "ADVA"},
                            {"name": "model", "value": "FSP 150CC-GE114/114S"},
                            {"name": "managementIP", "value": "71.42.150.156"},
                            {"name": "address", "value": "11921 N MO PAC EXPY 78739"},
                            {"name": "fqdn", "value": "CNI2TXA49ZW.DEV.CHTRSE.COM"},
                            {"name": "equipmentStatus", "value": "LIVE"},
                        ],
                        "ownedNodeEdgePoint": [
                            {
                                "uuid": "CNI2TXA49ZW-NETWORK-1-1-1-1",
                                "name": [
                                    {"name": "name", "value": "NETWORK-1-1-1-1"},
                                    {"name": "portRole", "value": "INNI"},
                                    {"name": "transportId", "value": "51001.GE1.AUSDTXIR2QW.CNI2TXA49ZW"},
                                ],
                            },
                            {
                                "uuid": "CNI2TXA49ZW-ACCESS-1-1-1-3",
                                "name": [
                                    {"name": "name", "value": "ACCESS-1-1-1-3"},
                                    {"name": "portRole", "value": "UNI"},
                                    {"name": "transportId", "value": "51.L1XX.010158..TWCC"},
                                ],
                            },
                        ],
                    },
                ],
                "link": [
                    {
                        "nodeEdgePoint": ["AUSDTXIR2CW-ET-2/2/0", "AUSDTXIR2QW-ET-0/0/99"],
                        "uuid": "AUSDTXIR2CW-ET-2/2/0_AUSDTXIR2QW-ET-0/0/99",
                    },
                    {
                        "nodeEdgePoint": ["AUSDTXIR2CW-ET-2/2/1", "AUSDTXIR2QW-ET-1/0/99"],
                        "uuid": "AUSDTXIR2CW-ET-2/2/1_AUSDTXIR2QW-ET-1/0/99",
                    },
                    {
                        "nodeEdgePoint": ["AUSDTXIR2QW-GE-1/0/81", "CNI2TXA49ZW-NETWORK-1-1-1-1"],
                        "uuid": "AUSDTXIR2QW-GE-1/0/81_CNI2TXA49ZW-NETWORK-1-1-1-1",
                    },
                ],
            },
        }
    ],
    "service": [
        {
            "model": "MEF-LEGATO-EVC",
            "version": "2017-07-27",
            "data": {
                "evc": [
                    {
                        "cosNames": [{"name": "BRONZE"}],
                        "evc-ingress-bwp": "25m",
                        "evc-egress-bwp": "25m",
                        "adminState": True,
                        "userLabel": "51.L1XX.010158..TWCC",
                        "maxNumOfEvcEndPoint": 1,
                        "serviceType": "IP",
                        "connectionType": "Point to Point",
                        "sVlan": "1181",
                        "endPoints": [
                            {
                                "uniId": "CNI2TXA49ZW-ACCESS-1-1-1-3",
                                "adminState": True,
                                "address": "11921 N MO PAC EXPY 78739",
                                "sVlan": "1181",
                                "sVlanOperation": "PUSH",
                            }
                        ],
                    }
                ],
                "fia": [
                    {
                        "type": "STATIC",
                        "endPoints": [
                            {
                                "uniId": "AUSDTXIR2CW-ET-2/2/0",
                                "lanIpv4Addresses": ["192.168.181.32/28"],
                                "lanIpv6Addresses": ["2605:ED00:3E2F::/48"],
                                "wanIpv4Address": "192.168.181.128/30",
                                "wanIpv6Address": "2605:6000:0:8::F:5B1A/127",
                            }
                        ],
                    }
                ],
            },
        }
    ],
}


eline = {
    "customerName": "TEST ACCT DEV",
    "serviceName": "51.L1XX.814265..TWCC",
    "customerType": "CARR",
    "modelVersion": "2.0",
    "serviceType": "ELINE",
    "serviceMedia": "FIBER",
    "topology": [
        {
            "model": "ONF_TAPI",
            "version": "2.0.0",
            "data": {
                "node": [
                    {
                        "uuid": "AUSDTXIR2CW",
                        "name": [
                            {"name": "hostName", "value": "AUSDTXIR2CW"},
                            {"name": "deviceRole", "value": "PE"},
                            {"name": "vendor", "value": "JUNIPER"},
                            {"name": "model", "value": "MX480"},
                            {"name": "managementIP", "value": "71.42.150.66"},
                            {"name": "address", "value": "11921 N MOPAC EXPY 78759"},
                            {"name": "fqdn", "value": "AUSDTXIR2CW.DEV.CHTRSE.COM"},
                            {"name": "equipmentStatus", "value": "LIVE"},
                        ],
                        "ownedNodeEdgePoint": [
                            {
                                "uuid": "AUSDTXIR2CW-GE-4/2/7",
                                "name": [
                                    {"name": "name", "value": "GE-4/2/7"},
                                    {"name": "portRole", "value": "ENNI"},
                                    {"name": "transportId", "value": "51.KFFD.000069..TWCC"},
                                ],
                            }
                        ],
                    }
                ],
                "link": [],
            },
        },
        {
            "model": "ONF_TAPI",
            "version": "2.0.0",
            "data": {
                "node": [
                    {
                        "uuid": "AUSDTXIR5CW",
                        "name": [
                            {"name": "hostName", "value": "AUSDTXIR5CW"},
                            {"name": "deviceRole", "value": "PE"},
                            {"name": "vendor", "value": "JUNIPER"},
                            {"name": "model", "value": "MX240"},
                            {"name": "managementIP", "value": "71.42.150.68"},
                            {"name": "address", "value": "11921 N MOPAC EXPY 78759"},
                            {"name": "fqdn", "value": "AUSDTXIR5CW.DEV.CHTRSE.COM"},
                            {"name": "equipmentStatus", "value": "LIVE"},
                        ],
                        "ownedNodeEdgePoint": [
                            {
                                "uuid": "AUSDTXIR5CW-GE-2/0/2",
                                "name": [
                                    {"name": "name", "value": "GE-2/0/2"},
                                    {"name": "portRole", "value": "INNI"},
                                    {"name": "transportId", "value": "51001.GE1.AUSDTXIR5CW.CNI5TXR38ZW"},
                                ],
                            }
                        ],
                    },
                    {
                        "uuid": "CNI5TXR38ZW",
                        "name": [
                            {"name": "hostName", "value": "CNI5TXR38ZW"},
                            {"name": "deviceRole", "value": "CPE"},
                            {"name": "vendor", "value": "ADVA"},
                            {"name": "model", "value": "FSP 150CC-GE114/114S"},
                            {"name": "managementIP", "value": "71.42.150.187"},
                            {"name": "address", "value": "11921 N MOPAC EXPY 78759"},
                            {"name": "fqdn", "value": "CNI5TXR38ZW.DEV.CHTRSE.COM"},
                            {"name": "equipmentStatus", "value": "LIVE"},
                        ],
                        "ownedNodeEdgePoint": [
                            {
                                "uuid": "CNI5TXR38ZW-NETWORK-1-1-1-1",
                                "name": [
                                    {"name": "name", "value": "NETWORK-1-1-1-1"},
                                    {"name": "portRole", "value": "INNI"},
                                    {"name": "transportId", "value": "51001.GE1.AUSDTXIR5CW.CNI5TXR38ZW"},
                                ],
                            },
                            {
                                "uuid": "CNI5TXR38ZW-ACCESS-1-1-1-5",
                                "name": [
                                    {"name": "name", "value": "ACCESS-1-1-1-5"},
                                    {"name": "portRole", "value": "UNI"},
                                    {"name": "transportId", "value": "51.L1XX.814265..TWCC"},
                                ],
                            },
                        ],
                    },
                ],
                "link": [
                    {
                        "nodeEdgePoint": ["AUSDTXIR5CW-GE-2/0/2", "CNI5TXR38ZW-NETWORK-1-1-1-1"],
                        "uuid": "AUSDTXIR5CW-GE-2/0/2_CNI5TXR38ZW-NETWORK-1-1-1-1",
                    }
                ],
            },
        },
    ],
    "service": [
        {
            "model": "MEF-LEGATO-EVC",
            "version": "2017-07-27",
            "data": {
                "evc": [
                    {
                        "cosNames": [{"name": "GOLD"}],
                        "perfTier": [{"name": "METRO"}],
                        "evc-ingress-bwp": "75m",
                        "evc-egress-bwp": "75m",
                        "evcId": "495001",
                        "adminState": True,
                        "userLabel": "51.L1XX.814265..TWCC",
                        "maxNumOfEvcEndPoint": 2,
                        "serviceType": "EPL",
                        "connectionType": "Point to Point",
                        "sVlan": "1414",
                        "endPoints": [
                            {
                                "uniId": "AUSDTXIR2CW-GE-4/2/7",
                                "adminState": True,
                                "address": "11921 N MOPAC EXPY 78759",
                                "sVlan": "1414",
                            },
                            {
                                "uniId": "CNI5TXR38ZW-ACCESS-1-1-1-5",
                                "adminState": True,
                                "address": "11921 N MOPAC EXPY 78759",
                                "sVlan": "1414",
                                "sVlanOperation": "PUSH",
                            },
                        ],
                    }
                ]
            },
        }
    ],
}
