# Flake8: noqa: E501

ID_TABLE = {
    "G003": "Missing Data | Granite - Transport Path Not Found",
    "G018": "Network | No Available Hub Ports",
    "G019": "Granite | No Available Hub Ports",
    "G020": "Granite | No Path Channel Availability",
    "G022": "Granite | No Junipers At Hub",
    "M002": "MDSO | Authentication Timeout",
    "M004": "MDSO | GET Timeout",
    "M006": "MDSO | POST Timeout",
    "M011": "MDSO | Device Failed Onboarding",
    "M012": "SENSE | Bad Command",
}

ARDA_REGEX = [
    {
        "rule": r"GSIP compliance check failed for (.*) ODIN results:",
        "summary": "Granite | GSIP Compliance Checked Failed",
    },
    {"rule": r"Transport path bandwidth differences found for VLAN IDs:", "summary": "Granite | Transport Path Issue"},
    {"rule": r"PRISM ID not allowed in bw_change payload", "summary": "Incorrect Data | Prism - Invalid Field Value"},
    {"rule": r"Hostname must be exactly 11 chars HOSTNAME", "summary": "Incorrect Data | SENSE - Invalid Device Name"},
    {"rule": r"Missing association in granite for", "summary": "Missing Data | Granite - Missing Parameter"},
    {"rule": r"Missing bandwidth on network", "summary": "Missing Data | Network - Bandwidth Data Missing"},
    {"rule": r"Missing the following required data", "summary": "Missing Data | SENSE - Missing Payload Parameter"},
    {"rule": r"Network bandwidth data is missing", "summary": "Missing Data | Network - Bandwidth Data Missing"},
    {
        "rule": r"Unable to login into the device:",
        "summary": "Network | MDSO - Device Communication Issue",
    },
    {
        "rule": r"Handoff port on {'tid': '(.*)', 'port_id': '(.*)', 'vendor': '(.*)'} not found",
        "summary": "Network | Device Port Issue",
    },
    {
        "rule": r"No change required for (.*) - requested bandwidth (.*) matches current bandwidth",
        "summary": "Network | Requested Change Matches Current Configuration",
    },
    {"rule": r"Unable to find expected Granite vlan id (.*) on CW device", "summary": "Network | Missing VLAN"},
    {
        "rule": r"Device(.*)is not supported when checking handoff port duplex settings",
        "summary": "Unsupported | Device/Role - Cisco",
    },
    {
        "rule": r"An update to IPv6 is required. Maintenance window needed due to transport\/duplex update",
        "summary": "Unsupported | Maintenance Window Required ",
    },
    {
        "rule": r"Trunked handoff circuits are unsupported at this time",
        "summary": "Unsupported | Service Type - Trunked Handoff Circuit",
    },
    {"rule": r"EPON topology is unsupported", "summary": "Unsupported | Topology - EPON"},
    {
        "rule": r"Existing revision found for (.*) Circuits with an existing revision are currently not supported",
        "summary": "Unsupported | Topology - Existing Revision",
    },
    {
        "rule": r"Unsupported circuit status (.*) for (.*)Circuit must be in 'Live' status",
        "summary": "Unsupported | Topology - Granite Status",
    },
    {"rule": r"Home run topology without QFX is unsupported", "summary": "Unsupported | Topology - Home Run"},
    {
        "rule": r"Hub transport path upgrades are unsupported:",
        "summary": "Unsupported | Topology - Hub Transport Path Upgrade",
    },
    {
        "rule": r"Too many sets of path utilization values returned from Granite API call \/pathUtilization",
        "summary": "Incorrect Data | Granite - Too Many Path Utilization Values",
    },
    {"rule": r"Check device error. Hostname:", "summary": "Network | MDSO - Device Communication Issue"},
    {
        "rule": r"Unable to create circuit revision. Exception while processing Granite response",
        "summary": "SENSE | Exception - Granite",
    },
    {"rule": r"SENSE timeout - METHOD: (.*) URL:", "summary": "SENSE | Timeout"},
    {"rule": r"Either multiple or no uplink port found in transport path", "summary": "SENSE | Transport Path Issue"},
    {"rule": r"DB vlan data is missing", "summary": "SENSE | Missing VLAN"},
    {"rule": r"No ZW device found", "summary": "Granite | No ZW Device Found"},
    {
        "rule": r"Issue updating transport path in granite. Update parameters",
        "summary": "Granite | Transport Path Issue",
    },
    {
        "rule": r"Network check failed:(.*)Can't find correct path element to process",
        "summary": "Granite | Unable To Locate Correct Path Element",
    },
    {"rule": r"Issue updating cpe in granite. Update parameters:", "summary": "Granite | Unable To Update Device"},
    {"rule": r"Unable to determine CID from", "summary": "Incorrect Data | Salesforce - Invalid Circuit ID"},
    {
        "rule": r"More than 1 element ending in ZW found",
        "summary": "Incorrect Data | Granite - More Than One Expected Element Found",
    },
    {"rule": r"No Live paths found for cid:", "summary": "Missing Data | Granite - No Live Paths Found"},
    {
        "rule": r"No path elements ending in ZW found",
        "summary": "Missing Data | Granite - No Paths Ending In ZW Found",
    },
    {
        "rule": r"Network check failed:(.*)Unexpected encapsulation",
        "summary": "Network | Unexpected Encapsulation",
    },
    {"rule": r"No records found in Granite for cid:", "summary": "Missing Data | Granite - No Records Found"},
    {"rule": r"Missing data for E-Access order", "summary": "Missing Data | Missing Data For Order"},
    {"rule": r"No FQDN Address found for (.*) in Granite", "summary": "Missing Data | No FQDN Address"},
    {"rule": r"No site data found for site:", "summary": "Missing Data | No Site Data Found"},
    {"rule": r"Unable to acquire L2 data for", "summary": "Missing Data | SENSE - Unable To Acquire Data For CID"},
    {
        "rule": r"Network check failed: (.*)[A|Z]W', 'vendor': '', 'model': '', 'port_id': ''(.*)Device communication",
        "summary": "Network | MDSO - Device Communication Issue",
    },
    {
        "rule": r"Network check failed: (.*)[C|Q]W', 'vendor': '', 'model': '', 'port_id': ''(.*)Device communication",
        "summary": "Network | MDSO - Device Communication Issue",
    },
    {"rule": r"Network check failed:", "summary": "Network | Granite To Network Mismatch"},
    {"rule": r"Blacklist check failed:", "summary": "Network | IP Blacklist Check Failed"},
    {
        "rule": r"The network check and\/or blacklist check failed: Network check passed\?: True, Blacklist check passed\?: False",
        "summary": "Network | IP Blacklist Check Failed",
    },
    {
        "rule": r"The network check and\/or blacklist check failed: Network check passed\?: False, (.*) Blacklist check passed\?: True",
        "summary": "Network | IP Blacklist Check Failed",
    },
    {"rule": r"IP address not correct or empty", "summary": "SENSE | IP Address Not Correct Or Empty"},
    {"rule": r"No resource results for device_id:", "summary": "SENSE | MDSO - No Resource ID Found"},
    {"rule": r"503 Service Temporarily Unavailable(.*)Avi Vantage", "summary": "SENSE | Service Unavailable"},
    {"rule": r"Unable to locate MPLS object", "summary": "SENSE | Unable To Locate MPLS Object"},
    {
        "rule": r"Unexpected response from ARIN during NET record update",
        "summary": "SENSE | Unexpected Response From ARIN",
    },
    {"rule": r"Unsupported Vendor:", "summary": "Unsupported | Device - Alcatel"},
    {"rule": r"Unsupported model in the circuit path", "summary": "Unsupported | Device - Cisco"},
    {
        "rule": r"Existing revision found for this circuit",
        "summary": "Incorrect Data | Granite - Existing Revision Found",
    },
    {
        "rule": r"Class of Service Type in Granite and Salesforce matches",
        "summary": "SENSE | Logical Change Not Needed",
    },
    {
        "rule": r"Granite unexpected status code(.*)Could not find port for PORT_INST_ID",
        "summary": "Granite | Cannot Find Port",
    },
    {
        "rule": r"Granite unexpected status code(.*)The channels associated with the selected bandwidth cannot be loaded because they are incompatible with the assigned channels\/subrates",
        "summary": "Granite | Conflict Found With Existing Element",
    },
    {
        "rule": r"Granite unexpected status code(.*)Element (.*) cannot be added because it is already being used",
        "summary": "Granite | Element Reserved By Another Path",
    },
    {
        "rule": r"Granite unexpected status code(.*)Shelf create Failed",
        "summary": "Granite | Failed To Create Shelf",
    },
    {
        "rule": r"Granite unexpected status code(.*)locked",
        "summary": "Granite | Lock Error",
    },
    {
        "rule": r"Granite response(.*)temporarily locked",
        "summary": "Granite | Lock Error",
    },
    {
        "rule": r"No devices were found at this site",
        "summary": "Granite | No Devices Found At Site",
    },
    {
        "rule": r"Granite unexpected status code(.*)oversubscription limit",
        "summary": "Granite | Path Oversubscription Limit",
    },
    {
        "rule": r"Granite unexpected status code(.*)The path name(.*)is not unique",
        "summary": "Granite | Path Name Not Unique",
    },
    {
        "rule": r"Granite unexpected status code(.*)Can not add shelf(.*)already exists",
        "summary": "Granite | Shelf Already Exists",
    },
    {
        "rule": r"Device template or model not found in underlay device topology",
        "summary": "SENSE | Device Template Not Found",
    },
    {"rule": r"Granite timeout - METHOD", "summary": "Granite | Timeout"},
    {
        "rule": r"QC - Found existing transport path (.*) with status (.*), please investigate",
        "summary": "Granite | Transport Path Issue",
    },
    {
        "rule": r"Granite unexpected status code(.*)Path request failed while attempting to create a dynamic port ",
        "summary": "Granite | Error Creating Dynamic Port In Path",
    },
    {
        "rule": r"Granite unexpected status code(.*)Path request failed while attempting to remove a path from archive",
        "summary": "Granite | Error Creating Path - Archived Path Conflict",
    },
    {
        "rule": r"Unexpected number of parent paths returned",
        "summary": "Incorrect Data | Granite - Unexpected Number Of Parent Paths",
    },
    {
        "rule": r"multiple devices found at site",
        "summary": "Incorrect Data | Multiple Devices Found At Site",
    },
    {
        "rule": r"IPControl unexpected response - METHOD: (.*) - URL: (.*) - message:(.*)No candidates found",
        "summary": "IPC | No Candidates Found",
    },
    {
        "rule": r"IPControl unexpected response - METHOD: (.*) - URL: (.*) - message:(.*)There are no UDFs defined",
        "summary": "IPC | No UDFs Defined For Object",
    },
    {
        "rule": r"IPControl unexpected response - METHOD: (.*) - URL: (.*) - message:(.*)Block(.*)not found",
        "summary": "IPC | IP Block Not Found",
    },
    {
        "rule": r"IPControl unexpected response - METHOD: (.*) - URL: (.*) - message:(.*)",
        "summary": "IPC | Uncategorized Error",
    },
    {"rule": r"No IP found in MDSO for hostname (.*) and port", "summary": "MDSO | No IP Found For Hostname And Port"},
    {
        "rule": r"Error Code: M005 - Unexpected status code: (.*) returned from MDSO endpoint:(.*)DISCONNECTED",
        "summary": "MDSO | Disconnected",
    },
    {
        "rule": r"Error Code: M005 - Unexpected status code: (.*) returned from MDSO endpoint:(.*)File not found",
        "summary": "MDSO | File Not Found",
    },
    {
        "rule": r"Error Code: M005 - Unexpected status code: (.*) returned from MDSO endpoint:(.*)Failed to reach desired sync state",
        "summary": "MDSO | Sync Error",
    },
    {
        "rule": r"Error Code: M005 - Unexpected status code: (.*) returned from MDSO(.*)Cannot connect to host",
        "summary": "MDSO | Device Communication Issue",
    },
    {
        "rule": r"Error Code: M005 - Unexpected status code: (.*) returned from MDSO endpoint:(.*)Invalid input detected",
        "summary": "MDSO | Invalid Input Detected",
    },
    {
        "rule": r"Error Code: M005 - Unexpected status code:(.*)returned from MDSO endpoint(.*)Command sent while waiting on previous command",
        "summary": "MDSO | Command Sent While Waiting On Previous Command",
    },
    {
        "rule": r"Legacy Equipment Source is blank for edge router (.*), please populate",
        "summary": "Missing Data | Granite - Legacy Equipment Source Is Blank",
    },
    {
        "rule": r"Circuit path missing LVL1 or LVL2 element for",
        "summary": "Missing Data | Granite - Missing Elements",
    },
    {
        "rule": r"No CW Path Elements found for cid:",
        "summary": "Missing Data | Granite - Missing Elements",
    },
    {
        "rule": r"No circuit site data found in Granite for",
        "summary": "Missing Data | Granite - No Circuit Site Found For Device",
    },
    {
        "rule": r"No IPv4 Address found for (.*) in Granite",
        "summary": "Missing Data | Granite - No IP Address For Device",
    },
    {
        "rule": r"Granite endpoint \/pathElements(.*)No records found with the specified search criteria",
        "summary": "Missing Data | Granite - No Records Found",
    },
    {
        "rule": r"no matching customer site information found in Granite for existing devices",
        "summary": "Missing Data | Granite - Site Matching Issue",
    },
    {
        "rule": r"No supported device models were found at this site",
        "summary": "Missing Data | Granite - Site Matching Issue",
    },
    {
        "rule": r"no matching port found in Granite for cid",
        "summary": "Missing Data | Granite - Site Matching Issue",
    },
    {
        "rule": r"Missing LEGACY_EQUIP_SOURCE for Z-Side (.*) for INNI determinatio",
        "summary": "Missing Data | SENSE - Missing Field Value",
    },
    {
        "rule": r"service code was not provided and is required for SIP and PRI analog",
        "summary": "Missing Data | SENSE - Missing Field Value",
    },
    {
        "rule": r"The design of the circuit was completed successfully, but the ISP work failed one of these checks:",
        "summary": "Network | Design Complete, ISP Work Failed",
    },
    {
        "rule": r"ENNI Error: No Live items found",
        "summary": "Network | ENNI Error No Live Items Found",
    },
    {
        "rule": r"Error occured while trying to determine wavelength match",
        "summary": "Network | Error Determinining Wavelength Match",
    },
    {
        "rule": r"There are no available handoff ports for the requested RJ-45 connector",
        "summary": "Network | No Available Ports",
    },
    {
        "rule": r"There are no available handoff ports for the requested (.*) connector",
        "summary": "Network | No Available Ports",
    },
    {"rule": r"Optic not slotted for port", "summary": "Network | Optic Issue"},
    {
        "rule": r"Customer already has IPv4 assigned subnets as",
        "summary": "SENSE | Customer Already Has Assigned Subnets",
    },
    {
        "rule": r"Invalid v1\/create_shelf payload fields",
        "summary": "SENSE | Invalid Product Name",
    },
    {
        "rule": r"SupportedProdTemplate.check_payload_keys_for_task - Missing payload keys (.*) in z_side for task",
        "summary": "SENSE | Missing Payload Keys",
    },
    {"rule": r"First LVL 1 element in path:", "summary": "SENSE | Transport Path Issue"},
    {
        "rule": r"TYPE II determined by INNI matrix",
        "summary": "SENSE | Type II Determined By INNI Matrix",
    },
    {"rule": r"Unable to determine INNI", "summary": "SENSE | Unable To Determine INNI"},
    {
        "rule": r"Error attempting to determine region for parent network assignment using",
        "summary": "SENSE | Unable To Determine Region for Parent Network Assignment",
    },
    {
        "rule": r"Error attempting to determine legacy region for parent network assignment using",
        "summary": "SENSE | Unable To Determine Region for Parent Network Assignment",
    },
    {
        "rule": r"INNI added but unable to perform latency testing",
        "summary": "SENSE | Unable To Perform Latency Testing",
    },
    {"rule": r"Route table block in unexpected format:", "summary": "SENSE | Unexpected Format"},
    {
        "rule": r"Found existing cpe with an unsupported status of",
        "summary": "Unsupported | Device - Unsupported Status",
    },
    {
        "rule": r"ENNI device (.*) is not supported at this time. Only Juniper, Cisco, and RAD",
        "summary": "Unsupported | Device/Role - Alcatel",
    },
    {
        "rule": r"Cisco switches as ENNI devices are unsupported at this time",
        "summary": "Unsupported | Device/Role - Cisco",
    },
    {
        "rule": r"Unsupported CLLI (.*) detected in path: hub has more than one Legacy Company\. Dual-homed hubs are not supported at this time",
        "summary": "Unsupported | Dual Homed Hub",
    },
    {
        "rule": r"Unsupported state given for INNI determination:",
        "summary": "Unsupported | State For INNI Determination",
    },
    {"rule": r"Unsupported CPE uplink topology in Granite for", "summary": "Unsupported | Topology - CPE Uplink"},
    {
        "rule": r"Unsupported network combo given for INNI determination",
        "summary": "Unsupported | Topology - INNI Network Combination",
    },
    {"rule": r"Legacy company not supported", "summary": "Unsupported | Topology - Legacy Company"},
    {
        "rule": r"Unsupported scenario - 3 results found in transport path lookup for (.*). Only one result supported",
        "summary": "Unsupported | Topology - Multiple Results In Transport Path",
    },
    {
        "rule": r"Parent network (.*) is not supported",
        "summary": "Unsupported | Topology - Parent Network Not Supported",
    },
    {
        "rule": r"card template mismatch or no ports matched on Granite, Network and device topology",
        "summary": "Granite | Template Issue",
    },
    {
        "rule": r"Granite unexpected status code(.*)Connector type(.*)does not match the connector type in the port template",
        "summary": "Granite | Template Issue",
    },
    {
        "rule": r"Multiple paths found for",
        "summary": "Incorrect Data | Multiple Paths Found",
    },
    {
        "rule": r"No MTU ports found in Granite for CLLI: (.*) Bandwidth:",
        "summary": "Missing Data | Granite - Missing Elements",
    },
    {
        "rule": r"ARDA(.*)Unable to obtain device data for",
        "summary": "SENSE | Unable To Obtain Device Data",
    },
    {
        "rule": r"no supported ports found for (.*) device",
        "summary": "Unsupported | Device - No Supported Ports Found",
    },
    {"rule": r"Required query parameter\(s\) not specified:", "summary": "SENSE | Missing Payload Keys"},
    {"rule": r"Unable to understand path-specific bitrate string for path", "summary": "Granite | Template Issue"},
    {
        "rule": r"service_type (.*) requires an a and z side",
        "summary": "Incorrect Data | Granite - Service Type Requires Both A And Z Side",
    },
    {
        "rule": r"Multiple COLO/POP records at this address",
        "summary": "Incorrect Data | SENSE - Multiple Site Matches",
    },
    {
        "rule": r"Multiple potential buildings or CELL site matches",
        "summary": "Incorrect Data | SENSE - Multiple Site Matches",
    },
    {
        "rule": r"Instead of creating a new site, found potential match",
        "summary": "Incorrect Data | SENSE - Multiple Site Matches",
    },
    {"rule": r"More than one site tied as a good match", "summary": "Incorrect Data | SENSE - Multiple Site Matches"},
    {
        "rule": r"Couldn't create a CID - BW Unit must be in the formats of - 'GBPS' or 'MBPS'",
        "summary": "Incorrect Data | SENSE - Invalid Data Format",
    },
    {
        "rule": r"Bandwidth value is greater than 800 Gbps please check bandwidth conversion",
        "summary": "SENSE | Bandwidth Value Issue",
    },
    {"rule": r"Could not find site by ENNI", "summary": "SENSE | Could Not Find Site By ENNI"},
    {"rule": r"Call to Denodo unsuccessful", "summary": "SENSE | Denodo Call Unsuccessful"},
    {"rule": r"Multiple potential building matches", "summary": "Incorrect Data | Multiple Potential Building Matches"},
    {
        "rule": r"Failed to create site: Site Mgmt Failed - Failed to associate sitecom.granite.asi.exception.ServiceException: Field: Site Name must be unique",
        "summary": "Incorrect Data | LocateIt - Site Name Must Be Unique",
    },
    {
        "rule": r"Failed to create site: Site Mgmt Failed - Failed to associate sitecom.granite.asi.exception.ServiceException:(.*)Invalid Network Site Data",
        "summary": "Incorrect Data | LocateIt - Invalid Site Data",
    },
    {"rule": r"LocateIt found a questionable match", "summary": "Incorrect Data | LocateIt - Site Match Issue"},
    {"rule": r"LocateIt found multiple matches", "summary": "Incorrect Data | LocateIt - Site Match Issue"},
    {"rule": r"LocateIt match failed", "summary": "Incorrect Data | LocateIt - Site Match Issue"},
    {
        "rule": r"CLLI generation failed for Network Site(.*)Same Address found",
        "summary": "Incorrect Data | LocateIt - Site Match Issue",
    },
    {"rule": r"CLLI generation failed for Network Site", "summary": "SENSE | LocateIt - Network Site Generation Issue"},
    {"rule": r"LocateIt found a similar address", "summary": "Incorrect Data | LocateIt - Site Match Issue"},
    {
        "rule": r"The CLONES site with CLLI(.*)does not match the information in LocateIt",
        "summary": "Incorrect Data | LocateIt - Site Match Issue",
    },
    {"rule": r"Error occurred with error code: 0\.0", "summary": "SENSE | LocateIt - Unspecified Error"},
    {
        "rule": r"Failed to create site: Site Mgmt Failed - Failed to associate sitecom.granite.asi.exception.ServiceException: null - for payload",
        "summary": "SENSE | LocateIt - Unspecified Error",
    },
    {"rule": r"Failed to create site: Site Mgmt Failed", "summary": "SENSE | Granite - Unspecified Error"},
    {"rule": r"Could not find site by related CID", "summary": "Missing Data | Granite - No Related CID Site"},
    {"rule": r"Circuit path already has transport element:", "summary": "Granite | Transport Path Issue"},
    {
        "rule": r"No ports found on Path Elements call to Granite for circuit id:",
        "summary": "Granite | No Ports Found On Path Elements",
    },
    {
        "rule": r"Granite unexpected status code: (.*) URL:(.*)Can not add card(.*)Slot(.*)already contains a card",
        "summary": "Granite | Conflict Found With Existing Element",
    },
    {
        "rule": r"Granite unexpected status code: (.*) URL:(.*)The following ports are currently used in a Path\/Network",
        "summary": "Granite | Port Already In Use",
    },
    {
        "rule": r"Granite unexpected status code: (.*) URL:(.*)The Port is reserved",
        "summary": "Granite | Port Already Reserved",
    },
    {
        "rule": r"Granite unexpected status code: (.*) METHOD: (.*) URL:(.*)The scheduled date(.*)is later than the scheduled date(.*)of the path\/network. Do you wish to continue",
        "summary": "Granite | Date Conflict",
    },
    {
        "rule": r"Granite unexpected status code: (.*) METHOD: (.*) URL:(.*)your session has been killed",
        "summary": "SENSE | Gatekeeper Session Interrupted",
    },
    {
        "rule": r"Granite unexpected status code: (.*) METHOD: (.*) URL:(.*)Customer Service Circuit Path(.*)must have an Ordering Customer assigned",
        "summary": "Missing Data | Granite - No Ordering Customer Assigned",
    },
    {
        "rule": r"Granite unexpected status code: (.*) METHOD: (.*) URL:(.*)Channel\/subrate name (.*) is already used; it must be unique",
        "summary": "Granite | VLAN Already In Use",
    },
    {
        "rule": r"Granite unexpected status code: (.*) METHOD: (.*) URL: (.*) PAYLOAD:(.*)Pending Decommission is not a valid path\/network status for this revision",
        "summary": "Granite | Unable to Update Path/Network Status",
    },
    {
        "rule": r"Granite unexpected status code: (.*) METHOD: (.*) URL:(.*)retString(.*)(is required|parameter is mandatory)",
        "summary": "Granite | Missing Payload Parameter",
    },
    {
        "rule": r"Existing transport path (.*) with status (.*) did not match the customer and site",
        "summary": "Incorrect Data | Granite - Existing Transport Status Mismatch",
    },
    {
        "rule": r"construction_complete must be either 'yes' or 'no'; value entered:",
        "summary": "Incorrect Data | Salesforce - Unexpected Value",
    },
    {
        "rule": r"Could not find ISP group for HUB CLLI:",
        "summary": "Missing Data | SENSE - Could Not Find ISP Group For Hub",
    },
    {
        "rule": r"Unable to determine hub with hub_clli_code:",
        "summary": "Incorrect Data | SENSE - Unable To Determine Value From Data",
    },
    {
        "rule": r"Found Live existing transport path (.*), please investigate",
        "summary": "Network | Found Existing Transport Path ",
    },
    {
        "rule": r"Error Code: G018 - No available ports. CLLI Code:(.*)Bandwidth:",
        "summary": "Network | No Available Ports",
    },
    {
        "rule": r"ISP work failed the optic size validation check. Please investigate",
        "summary": "Network | Optic Issue",
    },
    {
        "rule": r"{'scenario': 6, 'optic_slotted': False, 'optic_validation_notes': 'It was unable to be determined if the optic has been slotted or not for",
        "summary": "Network | Optic Issue",
    },
    {
        "rule": r"ISP work failed the wavelength validation check. Please investigate",
        "summary": "Network | Optic Issue",
    },
    {"rule": r"1AW shelf exists, please investigate", "summary": "Network | Shelf Already Exists"},
    {
        "rule": r"Timed out getting data from Denodo for URL:(.*)remedy_isp_groups",
        "summary": "SENSE | Timeout - Denodo",
    },
    {
        "rule": r"CLLI (.*) has more than one Legacy Company. Dual-homed hubs are not supported at this time",
        "summary": "Unsupported | Dual Homed Hub",
    },
    {
        "rule": r"Granite unexpected status code(.*)(template(.*)does not exist|No templates found)",
        "summary": "Granite | Template Issue",
    },
    {"rule": r"Granite unexpected status code", "summary": "Incorrect Data | Granite"},
    {
        "rule": r"No CJ on order and no existing customer site found",
        "summary": "Missing Data | SENSE - Invalid Site Data",
    },
    {"rule": r"No record found for zip code", "summary": "Missing Data | SENSE - Invalid Site Data"},
    {
        "rule": r"Unexpected Remedy error. Work order was not created because",
        "summary": "SENSE | Remedy - Work Order Creation Issue",
    },
    {"rule": r"Error creating MTU site for CLLI:", "summary": "SENSE | MTU Site Creation Error"},
    {
        "rule": r"Unsupported existing shelf found. Must be no prior MTU shelf at site for this customer",
        "summary": "SENSE | Existing MTU Shelf Found",
    },
    {"rule": r"Build Circuit Design Error", "summary": "SENSE | Missing Payload Keys"},
    {"rule": r"CW:(.*)port:(.*) - no units configured", "summary": "Network | Unexpected Port Config"},
    {
        "rule": r"Found existing customer transport, existing transport unsuporrted",
        "summary": "Incorrect Data | Granite - Found Existing Transport",
    },
    {
        "rule": r"ipv4_type and block_size fields are required for FIA and Carrier FIA Products",
        "summary": "SENSE | Missing Payload Keys",
    },
    {
        "rule": r"network platform, High Capacity, not supported for SIP products",
        "summary": "Unsupported | Product - Voice High Capacity",
    },
    {
        "rule": r"No existing transport paths found that matches the customer's site",
        "summary": "Missing Data | Granite - No Transport Path Found",
    },
    {
        "rule": r"Parent path for TID: (.*) is not in Live or Designed status",
        "summary": "Incorrect Data | Granite - Parent Path Status",
    },
    {
        "rule": r"Multiple transport paths found that matches the customer's site",
        "summary": "Incorrect Data | Granite - Multiple Transport Paths Found",
    },
    {"rule": r"Unable to retrieve network data for", "summary": "Network | MDSO - Device Communication Issue"},
    {"rule": r"Unsupported shelf vendor", "summary": "Unsupported | SENSE - Shelf Vendor"},
    {"rule": r"Unable to swap 1G RAD for 10G ADVA", "summary": "Unsupported | SENSE - Shelf Swap"},
    {"rule": r"No paths found at any CPE shelf", "summary": "Missing Data | Granite - No Paths Found"},
    {"rule": r"Unable to assign VLAN (.*) to Granite path", "summary": "SENSE | VLAN Assignment Error"},
    {"rule": r"Unable to determine interface bandwidth", "summary": "Incorrect Data | Granite - Interface Bandwidth"},
    {
        "rule": r"Unable to locate IS-IS Area information from (.*) via MDSO",
        "summary": "Network | MDSO - IS-IS Area Information",
    },
    {"rule": r"Unexpected MDSO response for port", "summary": "MDSO | Unexpected Response"},
    {"rule": r"Timeout calling v1\/", "summary": "SENSE | Timeout"},
    {
        "rule": r"did not have any IPv4 or IPv6 addresses shown in Granite",
        "summary": "Missing Data | Granite - Missing IP Address",
    },
    {"rule": r"Duplex setting for(.*)was found to be negotiating", "summary": "Network | Handoff Port Link State"},
    {"rule": r"Failed to assign GSIP for", "summary": "SENSE | Granite - Assign GSIP Error"},
    {
        "rule": r"No qualified transport paths were found for",
        "summary": "Missing Data | Granite - No Transport Paths Found",
    },
    {
        "rule": r"Requested bandwidth (.*) is less than current bandwidth",
        "summary": "Incorrect Data | Salesforce - BW Change Value",
    },
    {
        "rule": r"There are no vrfid elements in revisio",
        "summary": "Missing Data | Granite - Missing Network Element",
    },
    {
        "rule": r"Class of Service is missing from order",
        "summary": "SENSE | Missing Payload Keys",
    },
    {
        "rule": r"More than 1 CPE found",
        "summary": "SENSE | Granite - Multiple CPEs Found at Site",
    },
    {
        "rule": r"TYPE 2 is unsupported at this time",
        "summary": "Unsupported | Type II Disconnect",
    },
    {
        "rule": r"Unable to acquire VLAN ID for",
        "summary": "Missing Data | Granite - Channel VLAN",
    },
    {
        "rule": r"Salesforce connector: (.*) not equal to granite connector type",
        "summary": "Incorrect Data | Salesforce - Connector Type",
    },
    {
        "rule": r"No CLASS OF SERVICE Type found in Granite for cid",
        "summary": "Missing Data | Granite - Class of Service Type",
    },
    {
        "rule": r"Found existing cpe that is not tied to a transport path",
        "summary": "Incorrect Data | Granite - Existing CPE at Site",
    },
    {
        "rule": r"Unable to acquire L1 data for",
        "summary": "Missing Data | Granite - Circuit Path L1 Elements",
    },
    {
        "rule": r"no shelf info found in Granite for site",
        "summary": "Missing Data | Granite - Shelf at Site",
    },
    {
        "rule": r"Spectrum (.*) E-NNI provided on EPR does not match Granite",
        "summary": "Incorrect Data | Salesforce - E-NNI",
    },
    {
        "rule": r"Salesforce IP address: (.*) not equal to granite IP address:",
        "summary": "Incorrect Data | Salesforce - IP Address",
    },
    {
        "rule": r"VLAN (.*) is already in use in network vlans",
        "summary": "Network | VLAN - Already in Use",
    },
    {
        "rule": r"Multiple equipment exist at the customer's site",
        "summary": "Incorrect Data | Granite - Existing Shelves",
    },
    {
        "rule": r"Connected to ODIN but timed out reading data for GSIP validation response",
        "summary": "ODIN | Timeout",
    },
    {
        "rule": r"Primary FIA Service type: (.*) not equal to granite IP service type:",
        "summary": "Incorrect Data | Granite - IP Type",
    },
    {
        "rule": r"Unable to remove vrfid elements. Exception while processing Granite response",
        "summary": "Granite | VRFID - Error Removing",
    },
    {
        "rule": r"Unable to retrieve EVC ID",
        "summary": "Missing Data | Granite - EVCID",
    },
]

BEORN_REGEX = [
    {"rule": r"Granite Call - GRANITE failed to process the request", "summary": "Granite | Failed To Process Request"},
    {
        "rule": r"Granite Data Issue - FQDN Host: Error comparing Device_ID None with Equipment_ID TID:",
        "summary": "Granite | FQDN Host Issue",
    },
    {
        "rule": r"Granite Data Issue - FQDN Host:(.*) doesn't align with the Equipment_ID TID:",
        "summary": "Granite | FQDN Host Issue",
    },
    {"rule": r"Granite Data Issue - Invalid Channel Name -", "summary": "Granite | Invalid Channel Name"},
    {"rule": r"Granite Call - Timeout waiting on GRANITE to process the request", "summary": "Granite | Timeout"},
    {
        "rule": r"Granite Data Issue - Hydra data has no valid elements for cid:",
        "summary": "Missing Data | Granite - No Valid Elements For Circuit ID",
    },
    {
        "rule": r"Granite Data Issue - Number of evc_ids does not align with number of legs in circuit",
        "summary": "Incorrect Data | Granite - Value Number Does Not Match Criteria",
    },
    {
        "rule": r"Granite Data Issue - Number of IPs doesn't match number of subnets",
        "summary": "Incorrect Data | Granite - Value Number Does Not Match Criteria",
    },
    {
        "rule": r"Granite Data Issue - Circuit design has individual port(.*)linked more than once",
        "summary": "Incorrect Data | Granite - Port Linked More Than Once",
    },
    {
        "rule": r"Granite Data Issue - Multiple device pairings found",
        "summary": "Incorrect Data | Granite - Multiple Device Pairings",
    },
    {
        "rule": r"MDSO POST - Unknown exception occurred at MDSO for endpoint:(.*)payload:",
        "summary": "MDSO | Execption Error",
    },
    {"rule": r"Granite Data Issue - TID missing in Sequence:", "summary": "Missing Data | Granite - Missing Elements"},
    {
        "rule": r"Granite Call - Mandatory Granite Circuit Information Missing:",
        "summary": "Missing Data | Granite - Missing Field Value",
    },
    {
        "rule": r"Granite Data Issue - IPv4 Address supplied with no corresponding CIDR",
        "summary": "Missing Data | Granite - Missing Parameter",
    },
    {
        "rule": r"Granite Data Issue - IPv4 Subnet Data missing CIDR Data",
        "summary": "Missing Data | Granite - Missing Parameter",
    },
    {"rule": r"Granite Call - No records in Granite found for", "summary": "Missing Data | Granite - No Records Found"},
    {
        "rule": r"Unsupported change requested: no change request specified",
        "summary": "Unsupported | Change Request - None Specified",
    },
    {"rule": r"Granite Impact Analysis Error:", "summary": "Granite | Imact Analysis Error"},
    {
        "rule": r"Unable to swap CPE in Granite\. Error: {'message': 'ARDA - More than one path found for",
        "summary": "Incorrect Data | Granite - More Than One Path Found For CID",
    },
    {
        "rule": r"Topology Validation - Number of evc_ids does not align with number of legs in circuit",
        "summary": "Incorrect Data | Granite - Value Number Does Not Match Criteria",
    },
    {"rule": r"Timed out retrieving auth token from IPControl at url:", "summary": "IPC | Timeout"},
    {"rule": r"Timed out posting data to IPControl", "summary": "IPC | Timeout"},
    {
        "rule": r"Unexpected status code: (.*) returned from MDSO endpoint:",
        "summary": "MDSO | Unexpected Value",
    },
    {
        "rule": r"Granite Data Issue - ELAN (.*) missing VPLS VLAN ID",
        "summary": "Missing Data | Granite - ELAN Is Missing VPLS VLAN ID",
    },
    {"rule": r"Missing Valid Granite Elements -", "summary": "Missing Data | Granite - Missing Elements"},
    {
        "rule": r"Unable to swap CPE in Granite(.*)Unable to swap multi-circuit CPE. Related CID (.*) not found on the device",
        "summary": "Network | Related CID Not Found On Device",
    },
    {"rule": r"Unexpected status code: (.*) for URL:", "summary": "SENSE | ESET Issue"},
    {
        "rule": r"Error connecting to Arda CPE Swap endpoint: Connected to arda and timed out waiting for data for URL:",
        "summary": "SENSE | Timeout",
    },
    {
        "rule": r"CPE Swap Process Error: Installed device (.*) is not eligible for shelf swap",
        "summary": "Unsupported | Device/Role - Juniper",
    },
    {
        "rule": r"Unable to swap CPE in Granite(.*)(.*)CPE shelf has Live status. Only Planned and Designed are eligible at this time",
        "summary": "Unsupported | Topology - Granite Status",
    },
    {
        "rule": r"Unable to swap CPE in Granite(.*)(.*)Provided model is 10 Gbps but existing model is 1 Gbps. Only 1G -> 1G or 10G -> 10G model swaps are supported",
        "summary": "Unsupported | Topology - Higher Capacity CPE Swap",
    },
    {
        "rule": r"Unable to swap CPE in Granite(.*)(.*)Non-CPE device detected. Only CPEs can be swapped",
        "summary": "Unsupported | Topology - Non-CPE Shelf Swap",
    },
    {
        "rule": r"Granite Data Issue - Element missing management IP",
        "summary": "Missing Data | Granite - Management IP",
    },
    {
        "rule": r"Granite Data Issue - Leg Name has incorrect format",
        "summary": "Incorrect Data | Granite - Leg Name Format",
    },
    {
        "rule": r"Granite Data Issue - Unit missing from bandwidth: RF",
        "summary": "Missing Data | Granite - Bandwidth Unit",
    },
    {
        "rule": r"Topologies Modeling Unsupported - Cross Footprint Circuit - Internal NNI in path",
        "summary": "Unsupported | Cross Footprint Circuit - Internal NNI",
    },
    {
        "rule": r"Topologies Modeling Unsupported - Cross Footprint Circuit - Multiple Non-Sequential Clouds",
        "summary": "Unsupported | Cross Footprint Circuit - Multiple Non-Sequential Clouds",
    },
    {
        "rule": r"Topologies Modeling Unsupported - Service Type: Hairpin",
        "summary": "Unsupported | Topology - Hairpin",
    },
    {
        "rule": r"ACX port incorrectly named",
        "summary": "Incorrect Data | Granite - ACX Port",
    },
    {
        "rule": r"Unable to retrieve interface descriptions from the network",
        "summary": "SENSE | MDSO - CPE Config",
    },
]

PALANTIR_REGEX = [
    {
        "rule": r"(Palantir|PALANTIR) - MDSO(.*)(CIRCUITDETAILSCOLLECTOR|NEEDS TO BE UPDATED IN GRANITE)",
        "summary": "MDSO | Granite Data Issue",
    },
    {
        "rule": r"(Palantir|PALANTIR) - MDSO(.*)(COMMUNICATION STATE IS NOT UP|ONBOARD)",
        "summary": "MDSO | Device Connectivity Issue",
    },
    {"rule": r"(Palantir|PALANTIR) - MDSO(.*)COMMIT", "summary": "MDSO | Commit Script Failure"},
    {"rule": r"(Palantir|PALANTIR) - MDSO(.*)(TIMEOUT|TIMED OUT)", "summary": "MDSO | Timeout"},
    {"rule": r"(Palantir|PALANTIR) - MDSO(.*)ACTIVATING_PE", "summary": "MDSO | Uncategorized - ACTIVATING_PE"},
    {"rule": r"(Palantir|PALANTIR) - MDSO(.*)BANDWIDTH_UPDATE", "summary": "MDSO | Uncategorized - BANDWIDTH_UPDATE"},
    {
        "rule": r"(Palantir|PALANTIR) - MDSO(.*)CPEDEVICECONFIGVALIDATOR",
        "summary": "MDSO | Uncategorized - CPEDEVICECONFIGVALIDATOR",
    },
    {"rule": r"(Palantir|PALANTIR) - MDSO(.*)DISCONNECTMAPPER", "summary": "MDSO | Uncategorized - DISCONNECTMAPPER"},
    {"rule": r"(Palantir|PALANTIR) - MDSO(.*)FIA_CISCO", "summary": "MDSO | Uncategorized - FIA_CISCO"},
    {"rule": r"(Palantir|PALANTIR) - MDSO(.*)MEF_ADVA_FRE", "summary": "MDSO | Uncategorized - MEF_ADVA_FRE"},
    {"rule": r"(Palantir|PALANTIR) - MDSO(.*)MEF_JUNIPER_FRE", "summary": "MDSO | Uncategorized - MEF_JUNIPER_FRE"},
    {"rule": r"(Palantir|PALANTIR) - MDSO(.*)MEF_RAD_FRE", "summary": "MDSO | Uncategorized - MEF_RAD_FRE"},
    {"rule": r"(Palantir|PALANTIR) - MDSO(.*)MERAKIACCEPTANCE", "summary": "MDSO | Uncategorized - MERAKIACCEPTANCE"},
    {"rule": r"(Palantir|PALANTIR) - MDSO(.*)MERAKICOMPLIANCE", "summary": "MDSO | Uncategorized - MERAKICOMPLIANCE"},
    {
        "rule": r"(Palantir|PALANTIR) - MDSO(.*)NETWORKSERVICECHECK",
        "summary": "MDSO | Uncategorized - NETWORKSERVICECHECK",
    },
    {
        "rule": r"(Palantir|PALANTIR) - MDSO(.*)NETWORKSERVICEUPDATE",
        "summary": "MDSO | Uncategorized - NETWORKSERVICEUPDATE",
    },
    {"rule": r"(Palantir|PALANTIR) - MDSO(.*)PATH_FINDER", "summary": "MDSO | Uncategorized - PATH_FINDER"},
    {
        "rule": r"(Palantir|PALANTIR) - MDSO(.*)PEDEVICECONFIGVALIDATOR",
        "summary": "MDSO | Uncategorized - PEDEVICECONFIGVALIDATOR",
    },
    {
        "rule": r"(Palantir|PALANTIR) - MDSO(.*)READY_PRE_PRODUCTION",
        "summary": "MDSO | Uncategorized - READY_PRE_PRODUCTION",
    },
    {
        "rule": r"(Palantir|PALANTIR) - MDSO(.*)RESOURCETERMINATOR",
        "summary": "MDSO | Uncategorized - RESOURCETERMINATOR",
    },
    {
        "rule": r"(Palantir|PALANTIR) - MDSO(.*)MODELER",
        "summary": "MDSO | Uncategorized - MODELER",
    },
    {
        "rule": r"(Palantir|PALANTIR) - MDSO(.*)SERVICEDEVICEPROFILECONFIGURATOR",
        "summary": "MDSO | Uncategorized - SERVICEDEVICEPROFILECONFIGURATOR",
    },
    {
        "rule": r"(Palantir|PALANTIR) - MDSO(.*)SERVICEELANPROVISIONER",
        "summary": "MDSO | Uncategorized - SERVICEELANPROVISIONER",
    },
    {
        "rule": r"(Palantir|PALANTIR) - MDSO(.*)SERVICEFIAPROVISIONER",
        "summary": "MDSO | Uncategorized - SERVICEFIAPROVISIONER",
    },
    {"rule": r"(Palantir|PALANTIR) - MDSO(.*)SERVICEMAPPER", "summary": "MDSO | Uncategorized - SERVICEMAPPER"},
    {
        "rule": r"(Palantir|PALANTIR) - MDSO(.*)SERVICEPROVISIONER",
        "summary": "MDSO | Uncategorized - SERVICEPROVISIONER",
    },
    {
        "rule": r"(Palantir|PALANTIR) - MDSO(.*)SLMCONFIGVARIABLES",
        "summary": "MDSO | Uncategorized - SLMCONFIGVARIABLES",
    },
    {
        "rule": r"(Palantir|PALANTIR) - MDSO(.*)DESCRIPTION_UPDATE",
        "summary": "MDSO | Uncategorized - DESCRIPTION_UPDATE",
    },
    {
        "rule": r"(Palantir|PALANTIR) - MDSO(.*)ELANMAPPER",
        "summary": "MDSO | Uncategorized - ELANMAPPER",
    },
    {
        "rule": r"(Palantir|PALANTIR) - MDSO(.*)SERVICEDEVICECVALIDATOR",
        "summary": "MDSO | Uncategorized - SERVICEDEVICECVALIDATOR",
    },
    {"rule": r"(Palantir|PALANTIR) - MDSO(.*)SLMSERVICEFINDER", "summary": "MDSO | Uncategorized - SLMSERVICEFINDER"},
    {
        "rule": r"(Palantir|PALANTIR) - GRANITE CALL - PATH_NAME DOES NOT MATCH CID ENTERED",
        "summary": "Incorrect Data | Granite - Path Name",
    },
    {"rule": r"(Palantir|PALANTIR) - MDSO", "summary": "MDSO | Uncategorized"},
    {"rule": r"Connection Timeout at authentication with MDSO", "summary": "MDSO | Authentication Timeout"},
    {"rule": r"Read timeout during authentication with MDSO", "summary": "MDSO | Authentication Timeout"},
    {
        "rule": r"FAILURE retCode = 2, Shelf Mgmt Failed : Failed to map shelf attributes java.lang.NullPointerException, for shelf ID",
        "summary": "SENSE | Failed To Map Shelf Attributes",
    },
    {"rule": r"Erroneous return from Salesforce:", "summary": "Incorrect Data | Salesforce - Erroneous Data Return"},
    {
        "rule": r"PATH_NAME does not match CID entered",
        "summary": "Incorrect Data | SENSE - Path Name Does Not Match CID",
    },
    {"rule": r"IPC Call - No device found with TID", "summary": "IPC | No Device Found For TID"},
    {"rule": r"Timed out getting data from IPControl", "summary": "IPC | Timeout"},
    {
        "rule": r"{'(.*)': \['Config Remediation Failed'",
        "summary": "SENSE | Config Remediation Failed",
    },
    {
        "rule": r"{'(.*)': \['Connectivity Failed",
        "summary": "Network | Connectivity Failed",
    },
    {
        "rule": r"{'(.*)Bandwidth Config Failed",
        "summary": "SENSE | Bandwidth Config Failed",
    },
    {
        "rule": r"{'(.*)No Port Configuration Found",
        "summary": "Missing Data | Network",
    },
    {
        "rule": r"{'(.*)product name match failed",
        "summary": "Incorrect Data | Granite/Salesforce Data Mismatch",
    },
    {
        "rule": r"{'(.*)Port Config Failed",
        "summary": "SENSE | Port Config Failed",
    },
    {
        "rule": r"{'(.*)The customer name listed in Granite(.*)did not match the customer name",
        "summary": "Incorrect Data | Granite/IPC Data Mismatch",
    },
    {
        "rule": r"{'(.*)The site cannot be deleted because",
        "summary": "Incorrect Data | Granite - Site Still in Use",
    },
    {
        "rule": r"status code returned from MDSO endpoint (.*) \| Function that called mdso_get\(\): (.*) \| Response:",
        "summary": "MDSO | Status Code Error",
    },
    {"rule": r"No records found for URL:(.*)equipments", "summary": "Missing Data | Granite - No Records Found"},
    {"rule": r"No records found for URL:(.*)pathElements", "summary": "Missing Data | Granite - No Records Found"},
    {"rule": r"Missing Elements. nwid: (.*) clli:", "summary": "Missing Data | SENSE - Missing Elements"},
    {
        "rule": r"Failure Checking L2circuit Connection Status for TID:(.*)and Interface:(.*)Unknown interface",
        "summary": "Network | L2Circuit Issue",
    },
    {"rule": r"l2circuit is not Up", "summary": "Network | L2Circuit Issue"},
    {
        "rule": r"{'(.*)'CA Spectrum Failed",
        "summary": "SENSE | CA Spectrum Failed",
    },
    {"rule": r"Connected to Beorn and timed out waiting for data for URL", "summary": "SENSE | Timeout"},
    {"rule": r"Unable to retrieve IP address for", "summary": "SENSE | Unable To Retrieve Device IP Address"},
    {"rule": r"Vendor not supported", "summary": "Unsupported | Device Not Supported"},
    {"rule": r"Element is reserved by another path/network", "summary": "Granite | Element Reserved By Another Path"},
    {
        "rule": r"Granite has members not in 'Pending Decommission' Status for Z-side FULL Disco",
        "summary": "Granite | Ineligible Element State",
    },
    {
        "rule": r"Path Validation Failed : Path specifed in request does not exist",
        "summary": "Granite | Path Validation Failed, Path Does Not Exist",
    },
    {"rule": r"Connection timed out updating data to Granite for url:", "summary": "Granite | Timeout"},
    {
        "rule": r"Service Activation failed on updating the path(.*)Live is not a valid path/network status for this revision",
        "summary": "Granite | Unable to Update Path/Network Status",
    },
    {"rule": r"Unexpected error from Granite for URL:(.*)", "summary": "Granite | Unexpected Error"},
    {
        "rule": r"Granite-Delete Path Errored Unexpected error from Granite for url:",
        "summary": "Granite | Unexpected Error",
    },
    {"rule": r"ZW TID not found : Endpoint =", "summary": "Missing Data | Granite - TID Not Found"},
    {
        "rule": r"CIDR missing from IP block (.*), unable to complete fping check",
        "summary": "Missing Data | Granite - CIDR Missing From IP Block",
    },
    {
        "rule": r"Circuit is not in Designed, Auto-Designed, or Auto-Provisioned state",
        "summary": "Incorrect Data | Granite - Circuit Not In A Valid State For Automation",
    },
    {
        "rule": r"Missing one of Designed, Auto-Designed, Auto-Provisioned revision in Granite",
        "summary": "Missing Data | Granite - Expected Revision Status",
    },
    {
        "rule": r"Live is not a valid path/network status for this revision",
        "summary": "Incorrect Data | Granite - Path/Network Status Invalid",
    },
    {
        "rule": r"Granite Path Status not accurate in Granite for CID",
        "summary": "Incorrect Data | Granite - Path/Network Status Invalid",
    },
    {
        "rule": r"The site cannot be deleted because 1 piece\(s\) of equipment is/are still provisioned",
        "summary": "Incorrect Data | Granite - Unable To Detete Site",
    },
    {
        "rule": r"Unable to correlate full disconnect Granite address",
        "summary": "Incorrect Data | Granite/Salesforce Data Mismatch",
    },
    {
        "rule": r"Failed - Salesforce', 'Errors': \['connector type match failed, Granite value: (.*) not matching Salesforce value: (.*)']}",
        "summary": "Incorrect Data | Granite/Salesforce Data Mismatch",
    },
    {
        "rule": r"Granite Service Type Value: (.*) not matching Salesforce Service Type value:",
        "summary": "Incorrect Data | Granite/Salesforce Data Mismatch",
    },
    {
        "rule": r"Failed - Salesforce', 'Errors': \['Granite Subnet CIDR Notation: (.*) not matching Salesforce CIDR value: (.*)']}",
        "summary": "Incorrect Data | Granite/Salesforce Data Mismatch",
    },
    {"rule": r"connector type match failed", "summary": "Incorrect Data | Granite/Salesforce Data Mismatch"},
    {
        "rule": r"Error during Arda IP Unswip for cid (.*) , Message : ARDA - The customer name listed in Granite (.*) did not match the customer",
        "summary": "Incorrect Data | SENSE - Customer Name Mismatch With Granite",
    },
    {
        "rule": r"Error during Arda IP Reclaim for cid(.*)IPs without matching Granite/IPControl customer names",
        "summary": "IPC | Mismatch During IP Reclaim",
    },
    {
        "rule": r"Service Map Validation Failed: Could not onboard the CPE - ",
        "summary": "MDSO | Device Failed Onboarding",
    },
    {
        "rule": r"status code returned from MDSO endpoint: (.*) \| Function that called mdso_post\(\): (.*) \| Response:",
        "summary": "MDSO | Status Code Error",
    },
    {
        "rule": r"Service Activation failed on updating the path(.*)P010(.*)Active and Pending Paths must contain",
        "summary": "Missing Data | Granite - Missing Field Value",
    },
    {
        "rule": r"Service Activation failed on updating the path(.*)Channelization (.*) does not match the port template",
        "summary": "Incorrect Data | Granite - Port Channelization",
    },
    {
        "rule": r"Service Activation failed on updating the path(.*) Connector type (.*) does not match the connector type in the port template",
        "summary": "Incorrect Data | Granite - Connector Type",
    },
    {
        "rule": r"Service Activation failed on updating the path(.*)Port template (.*) does not exist",
        "summary": "Incorrect Data | Granite - Port Template",
    },
    {
        "rule": r"Service Activation failed on updating the path(.*)Equipment Shelf (.*) must have a Purchase Info",
        "summary": "Missing Data | Granite - Purchase Info",
    },
    {
        "rule": r"Service Activation failed on updating the path(.*)(The shelf must be locked|You do not currently have the item locked)",
        "summary": "Granite | Lock Error",
    },
    {
        "rule": r"Active and Pending Paths must contain a SERVICE MEDIA value in SERVICE TYPE",
        "summary": "Missing Data | Granite - Service Media",
    },
    {"rule": r"Missing Live revision in Granite", "summary": "Missing Data | Granite - Missing Live Revision"},
    {
        "rule": r"Shelf Update Failed(.*)Device information must contain",
        "summary": "Missing Data | Granite - Missing Parameter",
    },
    {"rule": r"No valid/expected records found in Granite", "summary": "Missing Data | Granite - No Records Found"},
    {
        "rule": r"TIDS ending in CW,QW,ZW,AW are not found",
        "summary": "Missing Data | Granite - No TIDs Found Matching Expected Syntax",
    },
    {"rule": r"Incorrect Managed Services data passed in", "summary": "Missing Data | No Reccords Found For CID"},
    {"rule": r"Bad request - Missing Input Data -", "summary": "Missing Data | SENSE - Input Data Missing"},
    {"rule": r"No matching Meraki Svcs Found", "summary": "Missing Data | SENSE - Meraki SVCs"},
    {"rule": r"No Parent Meraki SVCs found", "summary": "Missing Data | SENSE - Meraki SVCs"},
    {"rule": r"COMMUNICATION STATE IS NOT UP", "summary": "Network | MDSO - Device Communication Issue"},
    {
        "rule": r"Service Map Validation Failed: Unable to establish communication with :",
        "summary": "Network | MDSO - Device Communication Issue",
    },
    {"rule": r"ONBOARD", "summary": "Network | Device Connectivity Issue"},
    {
        "rule": r"Disconnect Validation Failed - Circuit ID discovered on",
        "summary": "Network | Disconnect Failed Validation",
    },
    {
        "rule": r"Disconnect Validation Failed - Interface config found on",
        "summary": "Network | Disconnect Failed Validation",
    },
    {
        "rule": r"Disconnect Validation Failed - Service config found on",
        "summary": "Network | Disconnect Failed Validation",
    },
    {
        "rule": r"Disconnect Validation Failed - SLM config found on reflector",
        "summary": "Network | Disconnect Failed Validation",
    },
    {
        "rule": r"Disconnect Validation Failed - Unable to verify remnant configs on reflector",
        "summary": "Network | Disconnect Failed Validation",
    },
    {
        "rule": r"Disconnect Validation Failed - IP routing discovered on",
        "summary": "Network | Disconnect Failed Validation",
    },
    {
        "rule": r"fping found at least 1 IP in (.*) marked alive",
        "summary": "Network | Live IP Detected Cannot Disconnect",
    },
    {
        "rule": r"Error during Arda IP Unswip for cid (.*) Message : ARDA - IP un-SWIP operation aborted. IPv4 block (.*) larger than \/28",
        "summary": "SENSE | IP Block Too Large For UnSWIP",
    },
    {
        "rule": r"Network Granite Compliance': 'Network Compliance Failure: (.*)",
        "summary": "SENSE | Network Compliance Failure",
    },
    {
        "rule": r"Flow Config Failed - ",
        "summary": "SENSE | Flow Config Failed",
    },
    {
        "rule": r"No Port Configuration Found - ",
        "summary": "Missing Data | Network - Port Config",
    },
    {
        "rule": r"Port Config Failed - ",
        "summary": "SENSE | Port Config Failed",
    },
    {
        "rule": r"SLM Traffic Validation Failed - ",
        "summary": "SENSE | SLM Validation Failed",
    },
    {"rule": r"Network - Service Map Voice IP Failed", "summary": "SENSE | Service Map Voice IP Failed"},
    {"rule": r"Timed out posting data to url:", "summary": "SENSE | Timeout"},
    {
        "rule": r"Error creating Remedy Disconnect Ticket(.*)Unexpected Remedy error. Work order was not created",
        "summary": "SENSE | Unexpected Remedy Error",
    },
    {"rule": r"Unsupported service type: locally switched ELINE", "summary": "Unsupported | Locally Switched"},
    {
        "rule": r"SF Granite Compliance': 'Unsupported Product Name",
        "summary": "Unsupported | Product - Unsupported Product Name",
    },
    {
        "rule": r"PALANTIR - No records found for",
        "summary": "Missing Data | Granite - No Records Found",
    },
    {
        "rule": r"Timeout error - Connected to MDSO and timed out for request",
        "summary": "SENSE | MDSO - Timeout",
    },
    {
        "rule": r"Error during Arda IP Unswip(.*)does not have an existing record in Granite",
        "summary": "Missing Data | Granite - CID Path",
    },
    {
        "rule": r"Error during Arda IP Unswip(.*)IP address is composed Incorrectly",
        "summary": "Incorrect Data | Granite - IP Address",
    },
    {
        "rule": r"Error during Arda IP Unswip(.*)IPs without matching Granite\/ARIN customer names",
        "summary": "Incorrect Data | Granite - Customer Name",
    },
    {
        "rule": r"MX Shelf not present in Granite",
        "summary": "Missing Data | Granite - Hub Shelf",
    },
    {
        "rule": r"Failure connecting to NDOS",
        "summary": "SENSE | NDOS - Connection Failure",
    },
    {
        "rule": r"GRANITE CALL - INVALID TID",
        "summary": "Incorrect Data | Granite - TID",
    },
    {
        "rule": r"Unsupported Product Name",
        "summary": "Unsupported | Product",
    },
    {
        "rule": r"'TACACS'",
        "summary": "Network | Device Validator - TACACS",
    },
    {
        "rule": r"'TACACS_REMEDIATION'",
        "summary": "Network | Device Validator - TACACS_REMEDIATION",
    },
    {
        "rule": r"'HOSTNAME_VALIDATION'",
        "summary": "Network | Device Validator - HOSTNAME_VALIDATION",
    },
    {
        "rule": r"'FQDN_RESOLVES'",
        "summary": "Network | Device Validator - FQDN_RESOLVES",
    },
    {
        "rule": r"'IPC_CALL'",
        "summary": "Network | Device Validator - IPC_CALL",
    },
    {
        "rule": r"'PING_CHECK'",
        "summary": "Network | Device Validator - PING_CHECK",
    },
    {
        "rule": r"'ISIN'",
        "summary": "Network | Device Validator - ISIN",
    },
    {
        "rule": r"'SNMP_DISABLED'",
        "summary": "Network | Device Validator - SNMP_DISABLED",
    },
    {
        "rule": r"bandwidth config failed",
        "summary": "Compliance Mismatch - Bandwidth Config",
    },
    {
        "rule": r"network config validation failed",
        "summary": "Compliance Mismatch - Network Config",
    },
    {
        "rule": r"SLM traffic validation failed",
        "summary": "Compliance Mismatch - SLM Validation",
    },
    {
        "rule": r"no port configuration found",
        "summary": "Compliance Mismatch - Network Config",
    },
    {
        "rule": r"'CA_SPECTRUM'",
        "summary": "Network | Device Validator - CA_SPECTRUM",
    },
]

REGEX_TABLE = [
    {"rule": r"SEnSE Bug!!", "summary": "SENSE | SENSE Bug Error"},
    *ARDA_REGEX,
    *BEORN_REGEX,
    *PALANTIR_REGEX,
]
