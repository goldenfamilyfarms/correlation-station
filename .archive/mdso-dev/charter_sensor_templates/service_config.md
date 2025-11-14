# Network Service configuration details

## Class of Service
### Juniper Class of Service EPL/EVPL configuration applicable to MVP

If `Unit_Type` (customer type) = `CARRIER`

| ServiceLevel value for CID    | Junos Configuration |
| :---------------------------: | :-----------------: |
| NULL                          | `set class-of-service interfaces <id> unit <id> apply-groups SERVICEPORT_UNCLASSIFIED_COS` |
| Bronze                        | `set class-of-service interfaces <id> unit <id> apply-groups SERVICEPORT_BRONZE_COS` |
| Silver                        | `set class-of-service interfaces <id> unit <id> apply-groups SERVICEPORT_SILVER_COS` |
| Gold                          | `set class-of-service interfaces <id> unit <id> apply-groups SERVICEPORT_GOLD_COS` |

If `Unit_Type` NOT EQUAL `CARRIER`

`set class-of-service interfaces <id> unit <id> apply-groups SERVICEPORT_UNCLASSIFIED_COS`

Those <configuration-groups> are already configured on the Juniper routers but safe checks can be added to verify if they are present.

There is a variety of service_types within Charter with different identifiers labels on Granite, for example, EE (Ethernet Everywhere) but those will be addressed when we improve the current JSON file and will discuss with other team members & other groups.

I think the information above is good for the MVP and the  2  chosen services for the PROD deployment should match the Unit_Type NOT EQUAL CARRIER because they are RETAIL SERVICES.

### p-bit for RAD

| ServiceLevel value for CID    | p-bit |
| :---------------------------: | ------|
| NULL                          | 0     |
| Bronze                        | 1     |
| Silver                        | 3     |
| Gold                          | 5     |


## Juniper example configuration
**PBP:**
```
bpadmin@re0.AUSDTXIR2CW> show configuration firewall policer 100m
logical-interface-policer;
if-exceeding {
    bandwidth-limit 100m;
    burst-size-limit 1m;
}
then discard;
```

**Network Service:**
```
bpadmin@re0.AUSDTXIR2CW# show interfaces ge-1/1/8 unit 1211
description "CARR:ELINE:ANDROMEDA PROJECT TEST@11921 N MOPAC EXPY:51.L1XX.009158..TWCC:11921 N MOPAC EXPY CUST SITE 5";
encapsulation vlan-ccc;
bandwidth 100m;
vlan-id 1211;
family ccc {
    policer {
        output 100m;
    }
}
```

```
bpadmin@AUSDTXIR5CW> show configuration class-of-service interfaces ge-2/1/0 unit 1211
apply-groups SERVICEPORT_UNCLASSIFIED_COS;
```
**Note:** COS determined by ServiceLevel specified in service. See above.

```
bpadmin@AUSDTXIR5CW> show configuration protocols l2circuit neighbor 71.42.150.66 interface ge-2/1/0.1211
virtual-circuit-id 429369;
description "CARR:ELINE:ANDROMEDA PROJECT TEST@11921 N MOPAC EXPY CUST SITE 5:51.L1XX.009158..TWCC:11921 N MOPAC EXPY";
```


**Note:** `ignore-mtu-mismatch` added to the l2circuit but not needed because is inherited from standards apply-groups

## RAD example configuration
**PBP:**
```
configure qos
        policer-profile "100m"
            bandwidth cir 100000 cbs 66400 eir 0 ebs 0
```

**Network Service:**
```
configure port
 ethernet 5
        no shutdown
        name "UNI:ELINE:ANDROMEDA PROJECT TEST@11921 N MOPAC EXPY:51.L1XX.009158..TWCC:"
        egress-mtu 12000
        l2cp profile "EP-UNI"
    exit
configure flows
    classifier-profile "CP-51.L1XX.009158..TWCC-IN" match-any
        match all
    exit
    classifier-profile "CP-51.L1XX.009158..TWCC-OUT" match-any
        match vlan 1211
    exit
   flow "51.L1XX.009158..TWCC-in"
        classifier "CP-51.L1XX.009158..TWCC-IN"
        policer profile "100m"
        vlan-tag push vlan 1211 p-bit fixed <value-based-of-COS-table: 1, 3, or 5>
        ingress-port ethernet 5
        egress-port ethernet 1 queue 1 block 0/1
        service-name "51.L1XX.009158..TWCC"
        no shutdown
    exit
    flow "51.L1XX.009158..TWCC-out"
        classifier "CP-51.L1XX.009158..TWCC-OUT"
        no policer
        vlan-tag pop vlan
        ingress-port ethernet 1
        egress-port ethernet 5 queue 1 block 0/1
        service-name "51.L1XX.009158..TWCC"
        no shutdown
    exit
```
**Note:** P-bit determined by ServiceLevel specified in service. See above.
