success_payload = {
    "message": "IP SWIP operation completed",
    "IPs Assigned": "[{'ip': '72.128.143.88/29', 'status': 'success'}, {'ip': '64:ff9b:1::/48', 'status': 'success'}]",
}
success_payload_v2 = {
    "message": "IP SWIP operation completed",
    "IPs Assigned": "[{'ip': '72.128.143.88/30', 'status': 'success'}, {'ip': '64:ff9b:1::/48', 'status': 'success'}]",
}
ipv4_success = "IPs that fall out of subnet range: 0\n\n                    IPs that have been reassigned: [{'ip': '72.128.143.88/29', 'status': 'success'}]\n\n                    IPs that failed assignment: [{'ip': '64:ff9b:1::/48', 'status': 'failed', 'error_code': 'The XML data you provided did not pass the RelaxNG schema validation. Please try validating your XML content against RelaxNG prior to submitting it.'}]\n"
ipv6_success = "IPs that fall out of subnet range: 0\n\n                    IPs that have been reassigned: [{'ip': '64:ff9b:1::/48', 'status': 'success'}]\n\n                    IPs that failed assignment: [{'ip': '72.128.143.88/29', 'status': 'failed', 'error_code': 'The XML data you provided did not pass the RelaxNG schema validation. Please try validating your XML content against RelaxNG prior to submitting it.'}]\n"
ip_delete = "IPs that fall out of subnet range: 0\n\n                    IPs that have been reassigned: 0\n\n                    IPs that failed assignment: [{'ip': '72.128.143.88/29', 'error_code': 'Org not Charter Communications', 'status': 'Record deleted'}, {'ip': '64:ff9b:1::/48', 'error_code': 'Org not Charter Communications', 'status': 'Record deleted'}]\n"
ip_ticket = "IPs have been SWIP'd: [{'ip': '72.128.143.88/29', 'ticket': '1234', 'status': 'pending'}, {'ip': '64:ff9b:1::/48', 'status': 'success'}]"
ip_bad_cidr = "IPs that fall out of subnet range: [{'ip': '72.128.143.88/32', 'status': 'Does not meet cidr requirments'}, {'ip': '64:ff9b:1::/32', 'status': 'Does not meet cidr requirments'}]\n\n                    IPs that have been reassigned: 0\n\n                    IPs that failed assignment: 0\n"
no_whois = "IPs that fall out of subnet range: 0\n\n                    IPs that have been reassigned: 0\n\n                    IPs that failed assignment: [{'ip': '72.128.143.88/29', 'status': 'No whois record'}, {'ip': '64:ff9b:1::/48', 'status': 'No whois record'}]\n"

arin_whois_good = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><collection'
    ' xmlns="http://www.arin.net/regrws/core/v1" xmlns:ns2="http://www.arin.net/regrws/messages/v1"'
    ' xmlns:ns3="http://www.arin.net/regrws/shared-ticket/v1" xmlns:ns4="http://www.arin.net/regrws/ttl/v1"'
    ' xmlns:ns5="http://www.arin.net/regrws/rpki/v1"><net><pocLinks/><customerHandle>C11303900</customerHandle>'
    "<netBlocks><netBlock><cidrLength>29</cidrLength><description>Reassigned</description>"
    "<endAddress>066.057.114.183</endAddress><startAddress>066.057.114.176</startAddress><type>S</type>"
    "</netBlock></netBlocks><handle>NET-66-57-114-176-1</handle><netName>ATF-INC</netName><originASes/>"
    "<parentNetHandle>NET-66-56-96-0-1</parentNetHandle>"
    "<registrationDate>2025-08-04T10:02:04-04:00</registrationDate><version>4</version></net></collection>"
)

whois_get_good = {
    "net": {
        "@xmlns": {
            "ns3": "http://www.arin.net/whoisrws/netref/v2",
            "ns2": "http://www.arin.net/whoisrws/rdns/v1",
            "$": "http://www.arin.net/whoisrws/core/v1",
        },
        "@copyrightNotice": "Copyright 1997-2020, American Registry for Internet Numbers, Ltd.",
        "@inaccuracyReportUrl": "https://www.arin.net/resources/registry/whois/inaccuracy_reporting/",
        "@termsOfUse": "https://www.arin.net/resources/registry/whois/tou/",
        "registrationDate": {"$": "2004-07-12T16:39:43-04:00"},
        "rdapRef": {"$": "https://rdap.ote.arin.net/registry/ip/2001:1998::"},
        "ref": {"$": "https://whois.ote.arin.net/rest/net/NET6-2001-1998-1"},
        "customerRef": {
            "@handle": "C07585356",
            "@name": "SMILEY DENTAL",
            "$": "https://whois.ote.arin.net/rest/customer/C07585356",
        },
        "endAddress": {"$": "2001:1998:FFFF:FFFF:FFFF:FFFF:FFFF:FFFF"},
        "handle": {"$": "NET6-2001-1998-1"},
        "name": {"$": "SMILEY DENTAL"},
        "netBlocks": {
            "netBlock": {
                "cidrLength": {"$": "32"},
                "endAddress": {"$": "2001:1998:FFFF:FFFF:FFFF:FFFF:FFFF:FFFF"},
                "description": {"$": "Direct Allocation"},
                "type": {"$": "DA"},
                "startAddress": {"$": "2001:1998::"},
            }
        },
        "resources": {
            "@copyrightNotice": "Copyright 1997-2020, American Registry for Internet Numbers, Ltd.",
            "@inaccuracyReportUrl": "https://www.arin.net/resources/registry/whois/inaccuracy_reporting/",
            "@termsOfUse": "https://www.arin.net/resources/registry/whois/tou/",
            "limitExceeded": {"@limit": "256", "$": "false"},
        },
        "orgRef": {
            "@handle": "CC-3517",
            "@name": "Charter Communications Inc",
            "$": "https://whois.ote.arin.net/rest/org/CC-3517",
        },
        "parentNetRef": {
            "@handle": "NET6-2001-1800-0",
            "@name": "ARIN-002",
            "$": "https://whois.ote.arin.net/rest/net/NET6-2001-1800-0",
        },
        "startAddress": {"$": "2001:1998::"},
        "updateDate": {"$": "2018-04-30T11:47:54-04:00"},
        "version": {"$": "6"},
    }
}

whois_get_wrong_org = {
    "net": {
        "@xmlns": {
            "ns3": "http://www.arin.net/whoisrws/netref/v2",
            "ns2": "http://www.arin.net/whoisrws/rdns/v1",
            "$": "http://www.arin.net/whoisrws/core/v1",
        },
        "@copyrightNotice": "Copyright 1997-2020, American Registry for Internet Numbers, Ltd.",
        "@inaccuracyReportUrl": "https://www.arin.net/resources/registry/whois/inaccuracy_reporting/",
        "@termsOfUse": "https://www.arin.net/resources/registry/whois/tou/",
        "registrationDate": {"$": "2004-07-12T16:39:43-04:00"},
        "rdapRef": {"$": "https://rdap.ote.arin.net/registry/ip/2001:1998::"},
        "ref": {"$": "https://whois.ote.arin.net/rest/net/NET6-2001-1998-1"},
        "customerRef": {
            "@handle": "C07585356",
            "@name": "SMILEY DENTAL",
            "$": "https://whois.ote.arin.net/rest/customer/C07585356",
        },
        "endAddress": {"$": "2001:1998:FFFF:FFFF:FFFF:FFFF:FFFF:FFFF"},
        "handle": {"$": "NET6-2001-1998-1"},
        "name": {"$": "SMILEY DENTAL"},
        "netBlocks": {
            "netBlock": {
                "cidrLength": {"$": "32"},
                "endAddress": {"$": "2001:1998:FFFF:FFFF:FFFF:FFFF:FFFF:FFFF"},
                "description": {"$": "Direct Allocation"},
                "type": {"$": "DA"},
                "startAddress": {"$": "2001:1998::"},
            }
        },
        "resources": {
            "@copyrightNotice": "Copyright 1997-2020, American Registry for Internet Numbers, Ltd.",
            "@inaccuracyReportUrl": "https://www.arin.net/resources/registry/whois/inaccuracy_reporting/",
            "@termsOfUse": "https://www.arin.net/resources/registry/whois/tou/",
            "limitExceeded": {"@limit": "256", "$": "false"},
        },
        "orgRef": {"@handle": "CC-3517", "@name": "Someone else", "$": "https://whois.ote.arin.net/rest/org/CC-3517"},
        "parentNetRef": {
            "@handle": "NET6-2001-1800-0",
            "@name": "ARIN-002",
            "$": "https://whois.ote.arin.net/rest/net/NET6-2001-1800-0",
        },
        "startAddress": {"$": "2001:1998::"},
        "updateDate": {"$": "2018-04-30T11:47:54-04:00"},
        "version": {"$": "6"},
    }
}


class MockResponse:
    def __init__(self, json_data, status_code=401):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data


class MockResponseXML:
    def __init__(self, xml_data, status_code=401):
        self.xml_data = xml_data
        self.status_code = status_code

    def text(self):
        return self.xml_data


class MockResponseXMLText:
    def __init__(self, text, status_code=401):
        self.text = text
        self.status_code = status_code

    def text(self):
        return self.text


class MockResponseXMLv2:
    def __init__(self, xml_data, status_code=401):
        self.xml_data = xml_data
        self.status_code = status_code
        self.text = str(xml_data)


def mock_arin_whois_good(*args, **kwargs):
    status_code = 200
    data = arin_whois_good
    return MockResponseXMLText(data, status_code)


def mock_whois_good(*args, **kwargs):
    status_code = 200
    data = whois_get_good
    return MockResponse(data, status_code)


def mock_whois_wrong_org(*args, **kwargs):
    status_code = 200
    data = whois_get_wrong_org
    return MockResponse(data, status_code)


def mock_whois_not_200(*args, **kwargs):
    status_code = 404
    data = whois_get_good
    return MockResponse(data, status_code)


def mock_create_200(*args, **kwargs):
    status_code = 200
    data = {"handle": "NET-1-1-1-1"}
    return MockResponse(data, status_code)


def mock_create_fail(*args, **kwargs):
    status_code = 404
    data = whois_get_wrong_org
    return MockResponse(data, status_code)


def mock_create_ticket(*args, **kwargs):
    status_code = 200

    data = {"ticket": "1234"}
    return MockResponse(data, status_code)


def mock_create_error(*args, **kwargs):
    status_code = 200
    data = {"error": {"code": "E_SCHEMA_VALIDATION"}}
    return MockResponse(data, status_code)


def mock_create_error_from_arin(*args, **kwargs):
    status_code = 200
    data = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\
    <error xmlns="http://www.arin.net/regrws/core/v1">\
    <additionalInfo/><code>E_ENTITY_VALIDATION</code><components><component>\
    <message>IP range overlaps with existing network(s).</message>\
    <name>startAddress</name></component></components>\
    <message>Payload entity failed to validate; see component messages for details.</message></error>'
    return MockResponseXMLv2(data, status_code)


xml_put_good = """<ticketedRequest xmlns="http://www.arin.net/regrws/core/v1" >
    <net>
        <version>4</version>
        <comment>
            <line number = "1">Line 1</line>
        </comment>
        <registrationDate>Tue Jan 25 16:17:18 EST 2011
        </registrationDate>
        <orgHandle>ARIN</orgHandle>
        <handle>NET-10-0-0-0-1</handle>
        <netBlocks>
            <netBlock>
                <type>A</type>
                <description>DESCRIPTION</description>
                <startAddress>010.000.000.000</startAddress>
                <endAddress>010.000.000.255</endAddress>
                <cidrLength>24</cidrLength>
            </netBlock>
        </netBlocks>
        <customerHandle>C12341234</customerHandle>
        <parentNetHandle>PARENTNETHANDLE</parentNetHandle>
        <netName>NETNAME</netName>
        <originASes>
            <originAS>AS102</originAS>
        </originASes>
        <pocLinks>
            <pocLinkRef>
            </pocLinkRef>
        </pocLinks>
    </net>
</ticketedRequest>"""

xml_ticket = """<ticketedRequest xmlns="http://www.arin.net/regrws/core/v1" xmlns:ns2="http://www.arin.net/regrws/messages/v1">
    <ticket>
        <messages>
            <message>
                <ns2:messageId>MESSAGEID</ns2:messageId>
                <ns2:createdDate>Tue Feb 28 17:41:17 EST 2012
                </ns2:createdDate>
                <subject>SUBJECT</subject>
                <text>
                    <line number = "1">Line 1</line>
                </text>
                <category>NONE</category>
                <attachments>
                    <attachment>
                        <data>DATA</data>
                        <filename>FILENAME</filename>
                    </attachment>
                </attachments>
            </message>
        </messages>
        <ticketNo>1234</ticketNo>
        <createdDate>Tue Jan 25 16:17:18 EST 2011</createdDate>
        <resolvedDate>Tue Jan 25 16:17:18 EST 2011</resolvedDate>
        <closedDate>Tue Jan 25 16:17:18 EST 2011</closedDate>
        <updatedDate>Tue Jan 25 16:17:18 EST 2011</updatedDate>
        <webTicketType>POC_RECOVERY</webTicketType>
        <webTicketStatus>PENDING_CONFIRMATION</webTicketStatus>
        <webTicketResolution>ACCEPTED</webTicketResolution>
    </ticket>
</ticketedRequest>"""

xml_error = """<error xmlns="http://www.arin.net/regrws/core/v1" >
    <message>MESSAGE</message>
    <code>E_SCHEMA_VALIDATION</code>
    <components>
        <component>
            <name>NAME</name>
            <message>MESSAGE</message>
        </component>
    </components>
    <additionalInfo>
        <message>MESSAGE</message>
    </additionalInfo>
</error>"""

arin_error_codes = {
    "E_SCHEMA_VALIDATION": "The XML data you provided did not pass the RelaxNG schema validation. Please try validating your XML content against RelaxNG prior to submitting it.",
    "E_ENTITY_VALIDATION": "This database object failed to pass ARIN’s validation (fields were missing or contained invalid characters, etc.).",
    "E_OBJECT_NOT_FOUND": "The database object you specified was not found in our database.",
    "E_AUTHENTICATION": "The API key specified in your URL either does not exist, or is not associated with/authoritative over the object specified in your URL/payload.",
    "E_NOT_REMOVEABLE": "The database object you specified was not able to be removed due to current associations/links to other objects. Remove those links/associations and try again.",
    "E_BAD_REQUEST": "The request you made was invalid. The most common reasons are: a bad URL, invalid parameter types, invalid parameters, or your mime type wasn’t properly set to application/xml. The source of your error will likely be an error in your REST client, and the error message will provide details for the fix.",
    "E_OUTAGE": "The Reg-RWS server is currently undergoing maintenance and is not available.",
    "E_UNSPECIFIED": "A universal error code for unspecified errors.",
}
