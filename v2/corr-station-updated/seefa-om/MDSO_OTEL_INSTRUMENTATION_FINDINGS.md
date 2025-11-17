# MDSO (Multi-Domain Service Orchestrator) OTEL Instrumentation Findings

## Analysis Date: 2025-11-13
## Source Directories:
- `/mdso-dev/all-product-logs-multiprocess/`
- `/mdso-dev/meta/`

---

## Executive Summary

This document extracts valuable patterns, logic, and metadata tracking strategies from existing MDSO logging infrastructure that can significantly improve OTEL instrumentation for SENSE applications (Beorn, Arda, Palantir).

---

## 1. Critical Signal Attributes to Track

### Product/Service Context
```python
# From log_search_and_rescue.py & meta_main.py
{
    # Core identifiers
    "product_name": str,          # e.g., "NetworkService", "ServiceMapper", "PortActivation"
    "product_type": str,           # e.g., "service_mapper", "network_service"
    "resource_id": str,            # MDSO resource UUID
    "resource_type_id": str,       # e.g., "tosca.resourceTypes.TraceLog"

    # Circuit/Service details
    "circuit_id": str,             # e.g., "80.L1XX.005054..CHTR"
    "label": str,                  # Resource label in MDSO
    "orch_state": str,             # Orchestration state
    "provider_resource_id": str,   # Format: bpo_{uuid}_{uuid}

    # Timestamps
    "created_at": datetime,        # UTC timestamp
    "time_zone": str,              # "US/Central", "UTC"
    "date_start": datetime,        # Start of time window
    "date_end": datetime,          # End of time window

    # Operational metadata
    "mdso_server": str,            # MDSO server URL
    "mdso_host": str,              # Specific MDSO host IP
    "log_dir_path": str,           # Path to logs
    "folder_name": str,            # Circuit_ID + timestamp
}
```

### Network Function/Device Context
```python
# From mdso_fqdn_beorn_capture.py & mdso_ra_log_capture.py
{
    # Device identification
    "fqdn": str,                   # e.g., "JFVLINBJ2CW.CHTRSE.COM"
    "tid": str,                    # 10-char device TID: "[A-Z0-9]{10}W"
    "management_ip": str,          # Device management IP
    "ip_address": str,             # From network function

    # Device classification
    "vendor": str,                 # "adva", "juniper", "cisco", "rad"
    "vendor_resource_type": str,   # Maps to RA type:
    # {
    #     "bpraadva": "bpraadva.resourceTypes.NetworkFunction",
    #     "rajuniper": "junipereq.resourceTypes.NetworkFunction",
    #     "radra": "radra.resourceTypes.NetworkFunction",
    #     "bpracisco": "bpracisco.resourceTypes.NetworkFunction"
    # }

    # Topology details
    "service_type": str,           # "FIA", "ELAN", "ELINE", "VOICE", "VIDEO"
    "aloc_path": list,             # A-location path nodes
    "zloc_path": list,             # Z-location path nodes (if not FIA)
    "device_role": str,            # "CPE", "PE"

    # Communication state
    "communication_state": str,    # From NetworkFunction check
}
```

### Error Tracking Context
```python
# From meta_main.py & auto_regex_error_tool.py
{
    # Error identification
    "error_code": str,             # e.g., "DE-1000", "DE-1001"
    "categorized_error": str,      # Standardized error message
    "raw_error": str,              # Original error text (first 500 chars)
    "new_error": bool,             # True if error pattern is new

    # Error context
    "defect_number": str,          # Associated defect ID
    "error_count": int,            # Occurrence count
    "resource_type": str,          # Resource type where error occurred
    "task_name": str,              # Failed task name
    "failed_task_number": int,     # Task sequence number

    # Trace information
    "orchestration_trace": dict,   # Full orch trace data
    "trace_log_available": bool,   # Whether orch trace exists

    # Log references
    "log_link": str,               # HTTP link to logs
    "log_path": str,               # File system path to logs
}
```

### Beorn Topology Metadata
```python
# From mdso_fqdn_beorn_capture.py
{
    # Circuit topology
    "beorn_url": str,              # Beorn API endpoint
    "data_validation": int,        # Element count (healthy = 8)
    "topology": [                  # List of topology nodes
        {
            "node": {
                "name": [          # Device name array
                    {"value": str},  # Various name fields
                    ...
                    {"value": str},  # vendor at index [2]
                    ...
                    {"value": str},  # FQDN at index [6]
                ]
            }
        }
    ]
}
```

---

## 2. Comprehensive Regex Patterns for Log Parsing

### Network Identifiers
```python
# Port patterns (auto_regex_error_tool.py lines 193-210)
PORT_PATTERNS = {
    "ET": r"(?i:ET-\d{1,2}/\d{1,2}/\d{1,2}(\.\d{1,4})?)",
    "GE": r"(?i:GE-\d{1,2}/\d{1,2}/\d{1,2}(\.\d{1,4})?)",
    "XE": r"(?i:XE-\d{1,2}/\d{1,2}/\d{1,2}(\.\d{1,4})?)",
    "ETH_PORT1": r"(?i:ETH-PORT-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2})",
    "ETH_PORT2": r"(?i:ETH PORT-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2})",
    "ETH_PORT3": r"(?i:ETH PORT \d/\d)",
    "ETH_PORT4": r"(?i:ETH PORT \d)",
    "LAG": r"(?i:LAG\d)",
    "AE": r"(?i:(?<=\W)AE(\d{1,2})?(\.\d{2,4})?)",
    "ETHERNET1": r"(?i:ETHERNET-\d(/\d{1,2})?)",
    "ETHERNET2": r"(?i:ETHERNET-)",
}

# Interface patterns
INTERFACE_PATTERNS = {
    "TPE_FP": r"(?i:TPE_FP-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}_CTP)",
    "TPE_ACCESS": r"(?i:TPE_ACCESS-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}_PTP)",
    "ACCESS": r"(?i:ACCESS-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2})",
    "FP": r"(?i:FP-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2})",
    "FP_SHAPER": r"(?i:FP SHAPER-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,3}-\d{1,3}-\d{1,3})",
    "FP_POLICER": r"(?i:FP POLICER-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,3}-\d{1,3}-\d{1,3})",
    "FRE_FLOW": r"(?i:FRE_flow-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2})",
    "MANAGEMENT_TUNNEL": r"(?:(?<=MANAGEMENT TUNNEL-)\d{1,2})",
}
```

### Service and Network Identifiers
```python
# Core identifiers (auto_regex_error_tool.py lines 212-227)
IDENTIFIER_PATTERNS = {
    "RESOURCE_ID": r"(?:[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})",
    "DATE_TIME": r"(?P<DateTime_Search>(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3,6}Z))",
    "IPV4": r"(?:(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d){1,3}(/\d{2})?)",
    "IPV6": r"(?:[a-fA-F0-9]{4}[:][^\s]+[:][a-fA-F0-9]{1,4})",
    "TID": r"(?:[A-Z0-9]{10}W(-)?(: )?)",
    "EVCID": r"(?<=evcId )\d{0,6}\s",
    "VRFID": r"(?:(?<=\s)[A-Z]+\.[A-Z]+\.[0-9]+.[A-Z0-9_]+\.[A-Z]+)",
    "VRFID_ELAN": r"(?:(?<=\s)[A-Z0-9_]+\.ELAN)",
    "SERVICE_VLANS": r"(?:(FIA|DIA|ELINE|ELAN|VOICE|VIDEO)\d{3,4})",
    "FQDN": r"[^\s]+COM",
    "CIRCUIT_ID": r"(?:(FRE_)?[0-9]{2}\.[A-Z0-9]{4}\.[0-9]{6}\.\.[A-Z]{0,4})",
    "REVISION_NUM": r"[0-9]{14}",
    "BPS_DIGITS": r"(?P<bps>(\d+)(?= bps))",
    "SHA_KEY": r"(?P<SHA>(?<=SHA )[a-f0-9]{40})",
}
```

### Error-Specific Patterns
```python
# Error message extraction (auto_regex_error_tool.py lines 279-302)
ERROR_PATTERNS = {
    # IP validation errors
    "NOT_IPV4_IPV6": r"(?P<Not_IPv4_IPv6>([^\s]+)(?= does not appear to be an IPv4 or IPv6 address))",
    "NOT_NETWORK_ADDRESS": r"(?P<Not_IP>(?<=IP )[^\s]+(?= is not a network address.))",
    "IP_EXISTS": r"(?P<IP_Exists>(?<=IP )[^\s]+(?= already exists on device))",

    # Metadata extraction
    "ID_KEY": r"(?P<id_Key>(?<='id': )[^\s]+)",
    "CREATED_AT_KEY": r"(?P<createdAt_Key>(?<='createdAt': )[^\s]+)",
    "LABEL_KEY": r"(?P<label_Key>(?<='label': ')[^\s]+)",
    "PRODUCT_ID_KEY": r"(?P<productId_Key>(?<='productId': ')[^\s]+)",
    "MESSAGE_ID": r"(?P<message_id>(?<=junos' message-id=)[^>]+)",

    # Resource/Port errors
    "RESOURCE_FOR_PORT": r"(?P<resource_for_port>(?<=unable to get port resource for port)[^,]+)",
    "DEVICE_CPE_ROLE_INVALID": r"(?P<device_CPE_role_invalid>(?<=DEVICE ROLE CPE is INVALID for )[^\.]+)",
    "DEVICE_PE_ROLE_INVALID": r"(?P<device_PE_role_invalid>(?<=DEVICE ROLE PE is INVALID for )[^\.]+)",

    # Generic patterns
    "NODE_NAME_INVALID": r"Node name: (.*?) is not valid",
    "FAILED_TASK_NUM": r"(?:(?<=Failed task:)\(\d{1,2}\))",
    "LIST_PATTERN": r"\[(.*?)\]",
    "DICT_PATTERN": r"\{(.*?)\}",
}
```

### Special Character Handling
```python
# Character escaping for regex (auto_regex_error_tool.py lines 228-244)
SPECIAL_CHAR_ESCAPES = {
    "[+]": r"\+",
    "[|]": r"\|",
    "[[]": r"\[",
    "[]]": r"\]",
    "[(]": r"\(",
    "[)]": r"\)",
    "[{]": r"\{",
    "[}]": r"\}",
    "[\n]": r"\\n",
    "::": ":",  # IPv6 double colon normalization
}
```

---

## 3. Log Correlation Patterns

### Multi-Level Log Collection
```python
# From log_search_and_rescue.py lines 52-88
LOG_COLLECTION_STRATEGY = {
    "plan_script_logs": {
        "enabled": bool,
        "collection_method": "multi_server_parallel",
        "servers": ["server1_ip", "server2_ip", "server3_ip"],
        "directory_structure": "{log_dir}/{date_dir}/{circuit_id_timestamp}/plan-script-downloads/",
        "file_extension": ".log",
    },

    "orch_trace_logs": {
        "enabled": bool,
        "resource_type": "tosca.resourceTypes.TraceLog",
        "search_pattern": "{circuit_id}.orch_trace",
        "file_format": "{circuit_id}_orch_trace.txt",
        "api_endpoint": "/bpocore/market/api/v1/resources",
    },

    "ra_logs": {
        "enabled": bool,
        "collection_method": "fqdn_based",
        "vendor_mapping": {
            "bpraadva": "bpraadva.resourceTypes.NetworkFunction",
            "rajuniper": "junipereq.resourceTypes.NetworkFunction",
            "radra": "radra.resourceTypes.NetworkFunction",
            "bpracisco": "bpracisco.resourceTypes.NetworkFunction"
        },
        "directory_structure": "{log_dir}/{date_dir}/{circuit_id}/{fqdn}/ra-log-download/",
        "file_extension": ".txt",
    }
}
```

### Orchestration Trace Structure
```python
# From mdso_orch_trace_capture_test.py & meta_main.py
ORCH_TRACE_STRUCTURE = {
    "items": [
        {
            "label": str,           # e.g., "80.L1XX.005054..CHTR.orch_trace"
            "properties": {
                "orchestration_trace": [
                    {
                        "resource_type": str,  # e.g., "tosca.resourceTypes.NetworkFunction"
                        "categorized_error": str,
                        "task_name": str,
                        "timestamp": str,
                        # Additional trace properties...
                    }
                ]
            }
        }
    ]
}
```

---

## 4. Time-Based Analysis Logic

### Flexible Time Windows
```python
# From meta_main.py lines 188-213
TIME_ANALYSIS_STRATEGY = {
    "minutes": {
        "subtract_method": "subtract(minutes=int(time_range))",
        "format": "YYYY-MM-DDTHH:mm",
        "display": "dddd MM-DD-YYYY HH:mm:ss",
    },
    "hours": {
        "subtract_method": "subtract(hours=int(time_range))",
        "format": "YYYY-MM-DDTHH",
        "display": "dddd MM-DD-YYYY HH:mm:ss",
    },
    "days": {
        "subtract_method": "subtract(days=int(time_range))",
        "format": "YYYY-MM-DD",
        "display": "dddd MM-DD-YYYY",
    },
    "weeks": {
        "subtract_method": "subtract(weeks=int(time_range))",
        "format": "YYYY-MM-DDTHH",
        "display": "Start: dddd MM-DD-YYYY through End: dddd MM-DD-YYYY",
    }
}

# Timezone handling
TIMEZONE_STRATEGY = {
    "system_timezone": "UTC",  # Sensor hosts are in UTC
    "display_timezone": "US/Central",  # Human-readable times
    "conversion_method": "pendulum.now('America/Chicago').set(tz='UTC')"
}
```

---

## 5. Data Validation & Quality Checks

### Beorn Data Validation
```python
# From mdso_fqdn_beorn_capture.py lines 36-74
BEORN_VALIDATION = {
    "healthy_element_count": 8,  # Minimum elements for valid response
    "retry_on_failure": True,
    "retry_count": 1,
    "required_fields": [
        "serviceType",
        "topology[0].data.node",
        "topology[0].data.node[i].name[6].value",  # FQDN
        "topology[0].data.node[i].name[2].value",  # Vendor
    ],
    "conditional_validation": {
        "if_not_FIA": "topology[1].data.node",  # Z-location path required
    },
    "skip_conditions": [
        "FQDN is None",
        "Vendor is None",
        "element_count < 8"
    ]
}
```

### Error Categorization Logic
```python
# From meta_main.py lines 396-399
ERROR_PROCESSING = {
    "character_filtering": {
        "remove": ["\n"],
        "replace": {'"': "'", "^": " "}
    },
    "truncation_length": 500,  # First 500 chars of error
    "deduplication_strategy": "regex_pattern_matching",
    "new_error_detection": "pattern_not_in_known_list"
}
```

---

## 6. Recommended OTEL Span Attributes

### High-Priority Attributes
```python
OTEL_SPAN_ATTRIBUTES = {
    # Service identification
    "service.name": "beorn|arda|palantir",
    "service.version": "VERSION",
    "service.instance.id": "container_id",

    # Request context
    "mdso.circuit_id": str,
    "mdso.resource_id": str,
    "mdso.product_type": str,
    "mdso.orch_state": str,

    # Network context
    "network.device.fqdn": str,
    "network.device.tid": str,
    "network.device.vendor": str,
    "network.device.role": "CPE|PE",
    "network.device.management_ip": str,
    "network.service.type": "FIA|ELAN|ELINE|VOICE|VIDEO",

    # Error tracking
    "error.code": str,  # DE-XXXX format
    "error.category": str,
    "error.resource_type": str,
    "error.is_new": bool,

    # Traceability
    "log.path": str,
    "log.link": str,
    "trace.orch_trace_available": bool,

    # Timing
    "time.window.start": datetime,
    "time.window.end": datetime,
    "time.collection.duration": float,
}
```

### Span Event Recommendations
```python
SPAN_EVENTS = {
    "device_lookup": {
        "event.name": "beorn.device.lookup",
        "attributes": ["circuit_id", "fqdn", "vendor", "topology_path"]
    },
    "orch_trace_fetch": {
        "event.name": "mdso.orch_trace.fetch",
        "attributes": ["resource_id", "trace_count", "error_found"]
    },
    "ra_log_collection": {
        "event.name": "mdso.ra_log.collect",
        "attributes": ["fqdn", "provider_resource_id", "vendor_type", "server_ip"]
    },
    "error_categorization": {
        "event.name": "error.categorize",
        "attributes": ["error_code", "regex_pattern", "is_new_error"]
    }
}
```

---

## 7. Correlation Strategies

### Multi-Source Log Correlation
```python
# Based on log_search_and_rescue.py
CORRELATION_KEYS = {
    "primary": "circuit_id",
    "secondary": ["resource_id", "tid", "fqdn"],
    "temporal": "created_at_timestamp",
    "directory_structure": "circuit_id_timestamp",

    # Cross-reference patterns
    "beorn_to_mdso": "circuit_id -> fqdn -> provider_resource_id",
    "orch_trace_to_ra_logs": "resource_id -> fqdn -> ra_log_files",
    "error_to_device": "error.categorized_error -> tid -> network_function"
}
```

### Trace Propagation
```python
TRACE_CONTEXT = {
    "span_naming": "{product_type}.{operation}",
    "parent_span": "mdso.product.execution",
    "child_spans": [
        "beorn.topology.fetch",
        "mdso.orch_trace.retrieve",
        "mdso.ra_log.collect",
        "error.analyze.categorize"
    ],
    "baggage_items": [
        "circuit_id",
        "resource_id",
        "product_name",
        "created_at"
    ]
}
```

---

## 8. Error Pattern Database Schema

### Recommended Structure
```sql
-- Based on auto_regex_error_tool.py
CREATE TABLE error_codes (
    error_code VARCHAR(10) PRIMARY KEY,  -- Format: DE-1000
    raw_error TEXT NOT NULL,
    categorized_error VARCHAR(500),
    regex_pattern TEXT NOT NULL,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP,
    occurrence_count INT DEFAULT 1,
    product_types JSON,  -- Array of products where error appears
    associated_defects JSON,  -- Array of defect numbers
    severity VARCHAR(20),  -- INFO, WARNING, ERROR, CRITICAL
    auto_generated BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_error_pattern ON error_codes(regex_pattern);
CREATE INDEX idx_product ON error_codes USING GIN(product_types);
```

---

## 9. Performance Optimization Strategies

### Parallel Processing
```python
# From log_search_and_rescue.py lines 59-60 & mdso_ra_log_capture.py lines 118-120
PARALLEL_STRATEGIES = {
    "plan_script_collection": {
        "executor": "concurrent.futures.ProcessPoolExecutor",
        "parallelization_level": "per_server",
        "servers": ["50.84.225.156", "50.84.225.157", "50.84.225.158"]
    },
    "ra_log_collection": {
        "executor": "concurrent.futures.ProcessPoolExecutor",
        "parallelization_level": "per_device_per_server",
        "iteration": "for server in mdso_host_list"
    }
}
```

### Pagination Strategy
```python
# From mdso_orch_trace_capture_test.py lines 59-63
API_PAGINATION = {
    "offset_difference": 100,
    "default_limit": 10,  # For trace logs
    "max_limit": 100000,  # For resource queries
    "count_endpoint": "/bpocore/market/api/v1/resources/count"
}
```

---

## 10. Integration Recommendations for SENSE Apps

### Beorn-Specific Enhancements
```python
BEORN_INSTRUMENTATION = {
    "spans_to_add": [
        "beorn.circuit.topology.fetch",
        "beorn.device.vendor.map",
        "beorn.fqdn.extract",
        "beorn.service.type.determine"
    ],
    "attributes": [
        "beorn.service_type",
        "beorn.topology.aloc.node_count",
        "beorn.topology.zloc.node_count",
        "beorn.data.validation_status",
        "beorn.retry.attempt"
    ],
    "metrics": [
        "beorn.api.response_time",
        "beorn.api.error_rate",
        "beorn.topology.node_count",
        "beorn.validation.failure_count"
    ]
}
```

### Arda & Palantir Enhancements
```python
SENSE_APP_INSTRUMENTATION = {
    "common_spans": [
        "sense.device.query",
        "sense.network_function.check",
        "sense.communication_state.verify",
        "sense.provider_resource.lookup"
    ],
    "vendor_specific_attributes": [
        "sense.vendor.type",  # adva, juniper, cisco, rad
        "sense.vendor.resource_type_id",
        "sense.device.communication_state"
    ],
    "correlation_attributes": [
        "sense.circuit_id",
        "sense.fqdn",
        "sense.tid",
        "sense.provider_resource_id"
    ]
}
```

---

## 11. Monitoring & Alerting Triggers

### Critical Patterns to Monitor
```python
# Based on meta_main.py test_to_perform patterns
ALERT_TRIGGERS = {
    "device_connectivity": {
        "pattern": r"unable to connect to device",
        "check_frequency": "every_15_minutes",
        "severity": "CRITICAL"
    },
    "partial_disconnect": {
        "pattern": "properties_.*_disconnect.*PARTIAL",
        "exclude_tids": "endpoint_tids_with_PARTIAL_status",
        "severity": "WARNING"
    },
    "granite_design_errors": {
        "pattern": r"GRANITE DESIGN \|.*",
        "aggregate": "all_granite_errors_together",
        "severity": "ERROR"
    },
    "new_error_discovered": {
        "condition": "error_pattern not in known_regex_patterns",
        "action": "auto_generate_regex_and_assign_code",
        "severity": "INFO"
    }
}
```

---

## 12. Implementation Priority

### Phase 1: Foundation (Week 1-2)
1. Add core OTEL attributes: circuit_id, resource_id, fqdn, tid
2. Implement regex patterns for log parsing
3. Add span events for major operations

### Phase 2: Enhanced Tracking (Week 3-4)
1. Integrate Beorn topology data into spans
2. Add vendor-specific attributes
3. Implement error categorization logic

### Phase 3: Advanced Features (Week 5-6)
1. Multi-source log correlation
2. Auto-regex error pattern generation
3. Historical error tracking database

### Phase 4: Optimization (Week 7-8)
1. Parallel log collection strategies
2. Performance metrics collection
3. Alerting rule implementation

---

## Appendix A: Key File References

| File | Key Contribution |
|------|------------------|
| `log_search_and_rescue.py` | Multi-level log collection, parallel processing |
| `mdso_orch_trace_capture.py` | Orch trace retrieval and parsing |
| `mdso_fqdn_beorn_capture.py` | Device topology extraction, vendor mapping |
| `mdso_ra_log_capture.py` | RA log collection, provider resource ID mapping |
| `meta_main.py` | Error categorization, time-based analysis, data validation |
| `auto_regex_error_tool.py` | **GOLD MINE**: Comprehensive regex patterns, auto-categorization |

---

## Appendix B: Vendor Resource Type Mapping

```python
VENDOR_MAPPING = {
    "bpraadva": {
        "resource_type": "bpraadva.resourceTypes.NetworkFunction",
        "ra_directory": "bpraadva"
    },
    "rajuniper": {
        "resource_type": "junipereq.resourceTypes.NetworkFunction",
        "ra_directory": "rajuniper"
    },
    "radra": {
        "resource_type": "radra.resourceTypes.NetworkFunction",
        "ra_directory": "radra"
    },
    "bpracisco": {
        "resource_type": "bpracisco.resourceTypes.NetworkFunction",
        "ra_directory": "bpracisco"
    }
}
```

---

**End of Document**
