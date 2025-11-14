full_success_response = {
    "summary": "NETWORK - CONNECTIVITY ERROR - TACACS DEVICE VALIDATION FAILED",
    "pretty_format": True,
    "message": {
        "IRMTMIBJ1CW": {
            "hostname": {"status": "validated", "message": "device name matches design"},
            "ip": {"status": "validated", "message": "usable: 150.181.2.44 source: granite"},
            "fqdn": {"status": "validated", "message": "fqdn resolves to usable ip"},
            "tacacs": {"status": "validated", "message": "logged in successfully"},
            "ise": {"status": "validated", "message": "onboarded device"},
            "reachable": "IRMTMIBJ1CW.DEV.CHTRSE.COM",
        }
    },
}


fqdn_not_resolving_response = {
    "summary": "NETWORK - CONNECTIVITY ERROR - TACACS DEVICE VALIDATION FAILED",
    "pretty_format": True,
    "message": {
        "IRMTMIBJ1CW": {
            "hostname": {"status": "validated", "message": "device name matches design"},
            "ip": {"status": "validated", "message": "usable: 150.181.2.44 source: granite"},
            "fqdn": {
                "status": "failed",
                "message": "not resolvable",
                "data": {"fqdn": "IRMTMIBJ1CW.DEV.CHTRSE.COM", "dns": "150.181.2.99", "usable": "150.181.2.44"},
            },
            "tacacs": {"status": "validated", "message": "logged in successfully"},
            "ise": {"status": "validated", "message": "onboarded device"},
            "reachable": "150.181.2.44",
        }
    },
}
