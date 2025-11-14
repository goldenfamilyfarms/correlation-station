"""-*- coding: utf-8 -*-

CommonPlan Plans

Versions:
   0.1 Dec 06, 2017
       Initial check in of CommonPlan plans

"""

import ipaddress
import sys

sys.path.append("model-definitions")
import json
import logging
import os
import re
import time
import traceback
from collections import defaultdict
from copy import deepcopy
from logging.handlers import RotatingFileHandler

import requests
import six
from plansdk.apis.bpo import WaitTimer
from ra_plugins.ra_cutthrough import RaCutThrough
from six.moves.urllib import parse

from scripts.scriptplan import Plan
from scripts.utils import Utils


class sensitiveLogDataFormatter(object):
    # custom formatter objects that simply wrap
    # the real formatter objects such that,
    # messages can be intercepted right after they
    # have been formatted but before the handler
    # gets a chance to write them.
    def __init__(self, orig_formatter, patterns):
        self.orig_formatter = orig_formatter
        self._patterns = patterns

    def format(self, record):
        newmsg = self.orig_formatter.format(record)
        # newmsg = "----->>>{}".format(newmsg)
        bexit = False
        for pattern in self._patterns:
            # there are only two cases for
            # key value pair, either json object
            # or string
            if pattern.find('"') != -1:
                valdelim = '"'
            else:
                valdelim = "'"
            # set pointers to null
            currptr = 0
            nextptr = currptr
            # dealing with string buffer,
            # use simple string pointer arithmatic search and replace
            # for simpler and fast replacement rather than
            # splitting and marshalling/unmarshalling json files
            currptr = newmsg[currptr:].find(pattern)
            while currptr != -1:
                currptr = currptr + nextptr
                currptr = currptr + len(pattern)
                nextptr = currptr
                if currptr < len(newmsg):
                    passwd = newmsg[currptr:]
                    if passwd:
                        startIndex = passwd.find(valdelim)
                        if startIndex != -1:
                            endIndex = passwd.find(valdelim, startIndex + 1)
                            if startIndex != -1 and endIndex != -1:
                                if startIndex < endIndex:
                                    # not optimized, can
                                    # do more arithmatic operations here
                                    newmsg = newmsg.replace(
                                        passwd[startIndex: endIndex + 1], "{}******{}".format(valdelim, valdelim)
                                    )
                                    bexit = True
                                else:
                                    newmsg = "{} | error-1-password-obfuscation".format(newmsg)
                                    bexit = True
                            else:
                                newmsg = "{} | error-2-password-obfuscation".format(newmsg)
                                bexit = True
                        else:
                            newmsg = "{} | error-3-password-obfuscation".format(newmsg)
                            bexit = True
                    else:
                        newmsg = "{} | error-4-password-obfuscation".format(newmsg)
                        bexit = True
                else:
                    newmsg = "{} | error-5-password-obfuscation".format(newmsg)
                    bexit = True
                currptr = newmsg[currptr:].find(pattern)
            if bexit:
                break
        return newmsg

    def __getattr__(self, attr):
        return getattr(self.orig_formatter, attr)


class CommonPlan(Plan, Utils):
    BUILT_IN_DOMAIN_ID = "built-in"
    BUILT_IN_CIRCUIT_DATA_COLLECTOR_TYPE = "charter.resourceTypes.CircuitDetailsCollector"
    BUILT_IN_SERVICE_DEVICE_VALIDATORY_TYPE = "charter.resourceTypes.ServiceDeviceValidator"
    BUILT_IN_SERVICE_FRE_ONBOARDER_TYPE = "charter.resourceTypes.ServiceFreOnboarder"
    BUILT_IN_UPDATE_OBSERVED_PROP_TYPE = "charter.resourceTypes.UpdateObservedProperty"
    BUILT_IN_BPO_CONSTANTS_TYPE = "charter.resourceTypes.BpoConstants"
    BUILT_IN_CIRCUIT_DETAILS_TYPE = "charter.resourceTypes.CircuitDetails"
    BUILT_IN_NETWORK_SERVICE_TYPE = "charter.resourceTypes.NetworkService"
    BUILT_IN_WIA_CONSTANT_TYPE = "charter.resourceTypes.WIAConstants"
    BUILT_IN_NETWORK_FUNCTION_TYPE = "tosca.resourceTypes.NetworkFunction"
    BUILT_IN_BW_PROFILE_TYPE = "tosca.resourceTypes.PacketBandwidthProfile"
    BUILT_IN_DEVICE_STATE_CHECK_TYPE = "charter.resourceTypes.DeviceStateChecker"
    BUILT_IN_DEVICE_ONBOARDER_TYPE = "charter.resourceTypes.DeviceOnboarder"
    BUILT_IN_MEF_TEST_SERVICE_TYPE = "mef.resourceTypes.MEFService"
    BUILT_IN_MEF_PRODUCTION_SERVICE_TYPE = "mef.resourceTypes.LegatoService"
    BUILT_IN_FIA_TEST_TYPE = "mef.resourceTypes.FIAtestservice"
    BUILT_IN_FIA_PRODUCTION_TYPE = "mef.resourceTypes.FIAservice"
    BUILT_IN_NETWORK_CONSTRUCT_TYPE = "tosca.resourceTypes.NetworkConstruct"
    BUILT_IN_FRE_TYPE = "tosca.resourceTypes.FRE"
    BUILT_IN_TPE_TYPE = "tosca.resourceTypes.TPE"
    BUILT_IN_NETWORK_INSTANCE_TYPE = "tosca.resourceTypes.NetworkInstance"
    BUILT_IN_TRACE_LOG_TYPE = "tosca.resourceTypes.TraceLog"
    BUILT_IN_MONITOR_TYPE = "tosca.resourceTypes.Monitor"
    BUILT_IN_RESOURCE_TERMINATOR = "tosca.resourceTypes.ResourceTerminator"
    BUILT_IN_CONNECTIVITY_CHECK_TYPE = "tosca.resourceTypes.ConnectivityCheck"
    BUILT_IN_STATUS_UPDATER_TYPE = "tosca.resourceTypes.StatusUpdater"
    BUILT_IN_RESOURCE_PLUG_IN_TYPE = "tosca.resourceTypes.RaResourcePlugin"
    BUILT_IN_SERVICE_DEPENDENCY_MODIFIER_TYPE = "charter.resourceTypes.ServiceDependencyModifier"
    BUILT_IN_RESOURCE_SCHEDULER_TYPE = "scheduler.resourceTypes.ResourceScheduler"
    BUILT_IN_RESOURCE_PORT_ACTIVATION_TYPE = "charter.resourceTypes.PortActivation"
    BUILT_IN_NETWORK_SERVICE_UPDATE_TYPE = "charter.resourceTypes.NetworkServiceUpdate"
    BUILT_IN_BW_UPDATE_TYPE = "charter.resourceTypes.BandwidthUpdate"
    BUILT_IN_DESCRIPTION_UPDATE_TYPE = "charter.resourceTypes.DescriptionUpdate"
    BUILT_IN_SERVICE_DEVICE_ONBOARDER_TYPE = "charter.resourceTypes.ServiceDeviceOnboarder"
    BUILT_IN_SERVICE_DEVICE_PROFILE_CONFIGURATOR = "charter.resourceTypes.ServiceDeviceProfileConfigurator"
    BUILT_IN_NETWORK_SERVICE_DELETE_TYPE = "charter.resourceTypes.NetworkServiceDelete"
    BUILT_IN_NETWORK_SERVICE_STATE_TOGGLE_TYPE = "charter.resourceTypes.NetworkServiceStateToggle"
    BUILT_IN_IP_UPDATE_TYPE = "charter.resourceTypes.IpUpdate"
    BUILT_IN_PATH_FINDER_TYPE = "charter.resourceTypes.PathFinder"
    BUILT_IN_CPE_ACTIVATOR_TYPE = "charter.resourceTypes.cpeActivator"
    BUILT_IN_NETWORK_SERVICE_CLEANER_TYPE = "charter.resourceTypes.NetworkServiceCleaner"
    BUILT_IN_SERVICE_MAPPER_TYPE = "charter.resourceTypes.ServiceMapper"
    BUILT_IN_RESOURCE_VERSION_UPGRADE_TYPE = "charter.resourceTypes.VersionUpgrade"
    BUILT_IN_SFTP_FIRMWARE_CONSTANTS_TYPE = "charter.resourceTypes.SftpFirmwareConstants"
    BUILT_IN_CLI_MANAGER_TYPE = "charter.resourceTypes.CLIManager"
    BUILT_IN_MANAGED_SERVICE_ACTIVATOR_TYPE = "charter.resourceTypes.ManagedServicesActivator"
    BUILT_IN_MANAGED_SERVICES_FORTIANALYZER_TYPE = "charter.resourceTypes.managedServicesFortiAnalyzer"
    BUILT_IN_MANAGED_SERVICES_FORTIMANAGER_TYPE = "charter.resourceTypes.managedServicesFortiManager"
    BUILT_IN_MANAGED_ROUTER_SERVICE_ACTIVATOR_TYPE = "charter.resourceTypes.ManagedRouterServicesActivator"
    BUILT_IN_MANAGED_ROUTER_FIRMWARE_VALIDATOR_TYPE = "charter.resourceTypes.ManagedRouterFirmwareValidator"
    BUILT_IN_MANAGED_ROUTER_FIRMWARE_UPDATER_TYPE = "charter.resourceTypes.ManagedRouterFirmwareUpdater"
    BUILT_IN_MANAGED_SERVICES_FORTIPORTAL_TYPE = "charter.resourceTypes.managedServicesFortiPortal"
    BUILT_IN_MANAGED_SECURITY_SERVICES_TYPE = "charter.resourceTypes.managedSecurityServices"
    BUILT_IN_MANAGED_SERVICES_CUSTOMER_TYPE = "charter.resourceTypes.customer"
    BUILT_IN_MANAGED_SERVICES_DATASTORE = "charter.resourceTypes.datastore"
    BUILT_IN_MANAGED_NETWORK_EDGE_TYPE = "charter.resourceTypes.merakiServices"
    BUILT_IN_SLM_SERVICE_FINDER_TYPE = "charter.resourceTypes.slmServiceFinder"
    BUILT_IN_SLM_CONFIG_VARIABLES_TYPE = "charter.resourceTypes.slmConfigVariables"
    BUILT_IN_SLM_CONFIGURATOR_TYPE = "charter.resourceTypes.slmConfigurator"
    BUILT_IN_SLM_MODELER_TYPE = "charter.resourceTypes.slmModeler"
    BUILT_IN_DISCONNECT_MAPPER_TYPE = "charter.resourceTypes.DisconnectMapper"
    BUILT_IN_CONFIG_MODELER_TYPE = "charter.resourceTypes.configModeler"
    BUILT_IN_TRANSPORT_NNI_PROVISIONER_TYPE = "charter.resourceType.TransportNNIProvisioner"
    BUILT_IN_ELAN_MAPPER_TYPE = "charter.resourceTypes.ElanMapper"
    BUILT_IN_MULTI_LEG_SERVICE_TYPE = "charter.resourceTypes.multiLegCircuit"
    BUILT_IN_COMPLIANCE_TYPE = "charter.resourceTypes.Compliance"
    BUILT_IN_PROVISIONING_TYPE = "charter.resourceTypes.Provisioning"
    BUILT_IN_SMOKE_TEST_TYPE = "charter.resourceTypes.SmokeTest"
    BUILT_IN_DEVICE_RESET_TYPE = "charter.resourceTypes.DeviceReset"

    ORCH_TRACE_PRODUCTS = {
        BUILT_IN_CPE_ACTIVATOR_TYPE: True,
        BUILT_IN_SERVICE_MAPPER_TYPE: True,
        BUILT_IN_DISCONNECT_MAPPER_TYPE: True,
        BUILT_IN_NETWORK_SERVICE_UPDATE_TYPE: True,
        BUILT_IN_NETWORK_SERVICE_DELETE_TYPE: True,
        BUILT_IN_MULTI_LEG_SERVICE_TYPE: True,
        BUILT_IN_COMPLIANCE_TYPE: True,
        BUILT_IN_PROVISIONING_TYPE: True,
        BUILT_IN_SMOKE_TEST_TYPE: True,
        BUILT_IN_DEVICE_RESET_TYPE: True,
    }

    ACTIVATE_OPERATION_STRING = "ACTIVATE"
    UPDATE_OPERATION_STRING = "UPDATE"
    TERMINATE_OPERATION_STRING = "TERMINATE"

    DEFAULT_NETCONF_PORT = 830
    DEFAULT_CLI_PORT = 22
    DEFAULT_MTU_SIZE = {"UNI": 12000, "NNI": 12000}
    NONE_EXECUTED_CUSTOM_OPERATION_STATES = ["requested", "pending", "scheduled", "executing"]

    PE_SPECIFIC_RESOURCE_TYPES = {
        "FIA": "charter.resourceTypes.ServiceProvisioner_FIA",
        "ELAN": "charter.resourceTypes.ServiceProvisioner_ELAN",
    }

    ERROR_CATEGORY = {
        "MDSO": "MDSO | {}",
        "GRANITE": "GRANITE DESIGN | {}",
        "DATA_SUPPLY": "DATA SUPPLY | {}",
        "NETWORK": "NETWORK | {}",
    }

    # System Level Error Buckets
    CIRCUIT_DETAILS_DATABASE = "Granite"
    SENSE = "SEnSE"
    FORMATTED_SYSTEM_LEVELS = ["MDSO | ", f"{SENSE} | ", f"{CIRCUIT_DETAILS_DATABASE} | "]

    # Category Level Error Buckets
    CONNECTIVITY_ERROR_TYPE = "Connectivity Error"
    SYSTEM_ERROR_TYPE = "System Error"
    INCORRECT_DATA_ERROR_TYPE = "Incorrect Data"
    MISSING_DATA_ERROR_TYPE = "Missing Data"
    PROCESS_ERROR_TYPE = "Process Error"
    UNSUPPORTED_ERROR_TYPE = "Automation Unsupported"

    # Sub-Category Level Error Buckets
    TOPOLOGIES_DATA_SUBCATEGORY = "Required Topologies Data"
    RESOURCE_GET_SUBCATEGORY = "Resource Get"
    RESOURCE_CREATE_SUBCATEGORY = "Resource Create"

    STATUS_TRANSLATION = {
        "circuit_details_collector": "Processing circuit information",
        "network_service_pre_check": "Checking for pre-existing network service",
        "service_device_validator": "Validating device states",
        "pe_device_onboarder": "Onboarding PE network devices",
        "pe_device_config_validator": "Validating PE device configuration",
        "pe_bw_profile_configurator": "Configuring Bandwidth profiles for needed devices",
        "service_fia_provisioner": "Configuring logical interface and static routes for FIA service",
        "pe_service_provisioner": "Creating/Updating MEF service",
        "cpe_device_onboarder": "Onboarding CPE network devices",
        "cpe_device_config_validator": "Validating CPE configuration",
        "cpe_bw_profile_configurator": "Configuring bandwidth profile for CPE",
        "service_fre_onboarder": "Building Flow between CPE and PE",
        "cpe_service_provisioner": "Configurating service on CPE",
        "network_service_post_check": "Updating CPE site state",
        "service_dependency_modifier": "Updating service dependencies",
        "network_service_clean_up": "Cleaning up MDSO resources",
        "network_service_update": "Creating resource for MDSO network service update",
        "service_device_profile_configurator": "Configuring Bandwidth profiles for needed devices",
        "service_device_onboarder": "Instantiating device onboarders for missing network devices",
        "network_service_bandwidth_update": "Creating bandwidth update resource",
        "network_service_description_update": "Creating description update resource",
        "device_state_checker": "Checking device states",
        "device_onboarder": "Onboarding network devices",
    }

    # ADVA devices doesnt support bandwidth profiles option,
    # hence for ADVA BW_POLICIER_TYPE is not defined
    COMMON_TYPE_LOOKUP = {
        "JUNIPER": {
            "DOMAIN_TYPE": "urn:cyaninc:bp:domain:juniper",
            "SESSION_PROFILE_TYPE": "junipereq.resourceTypes.SessionProfile",
            "DEVICE_TYPE": "junipereq.resourceTypes.NetworkFunction",
            "INTERFACE_TYPE": "tosca.resourceTypes.TPE",
            "BW_POLICER_TYPE": "tosca.resourceTypes.PacketBandwidthProfile",
            "RESOURCE_TYPE_TO_CHECK": None,
            "PORT_ID_VALUE": "PORT_ID_LABEL",
            "PE_BW_DIR": "BOTH",
            "BW_POLICER_IGNORE_LIST": [{"deviceRole": ["CPE", "MTU"], "modelFamily": "EX"}],
        },
        "RAD": {
            "DOMAIN_TYPE": "urn:ciena:bp:domain:rad",
            "SESSION_PROFILE_TYPE": "radra.resourceTypes.SessionProfile",
            "DEVICE_TYPE": "radra.resourceTypes.NetworkFunction",
            "INTERFACE_TYPE": "tosca.resourceTypes.TPE",
            "BW_POLICER_TYPE": "tosca.resourceTypes.PacketBandwidthProfile",
            "RESOURCE_TYPE_TO_CHECK": "tosca.resourceTypes.FRE",
            "PORT_ID_VALUE": "PORT_RESOURCE_ID",
            "PE_BW_DIR": "egress",
            "NNI_LINK_ID": "ETHERNET-1",
            "UNI_L2CP_PROFILE": "EP-UNI",
            "EVP_UNI_L2CP_PROFILE": "EVP-UNI",
            "MTU": 12000,
            "BW_POLICER_INCLUSION_LIST": {"deviceRole": "MTU", "context": "CPE"},
            "MODEL": {"ETX203": {"NNI_LINK_ID": "ETHERNET-1"}, "ETX220": {"NNI_LINK_ID": "ETHERNET-4/1"}},
            "SET_HOSTNAME1": "configure system\n",
            "SET_HOSTNAME2": "name {}\n",
        },
        "ADVA": {
            "DOMAIN_TYPE": "urn:ciena:bp:domain:bpraadva",
            "SESSION_PROFILE_TYPE": "bpraadva.resourceTypes.SessionProfile",
            "DEVICE_TYPE": "bpraadva.resourceTypes.NetworkFunction",
            "RESOURCE_TYPE_TO_CHECK": "tosca.resourceTypes.FRE",
            "PORT_ID_VALUE": "PORT_RESOURCE_ID",
            "PE_BW_DIR": "egress",
            "INTERFACE_TYPE": "tosca.resourceTypes.TPE",
            "MTU": 9600,
            "SET_HOSTNAME1": "configure system\n",
            "SET_HOSTNAME2": "prompt {}\n",
            "MTU_BW_INCLUSION": {
                "deviceRole": "MTU",
                "context": "CPE",
                "MODEL": ["FSP 150-XG116PRO", "FSP 150-XG116PROH", "FSP 150-XG118PRO (SH)", "FSP 150-XG120PRO"],
            },
        },
        "ADVA0825": {
            "DOMAIN_TYPE": "urn:ciena:bp:domain:bpraadva0825",
            "SESSION_PROFILE_TYPE": "bpraadva0825.resourceTypes.SessionProfile",
            "DEVICE_TYPE": "bpraadva0825.resourceTypes.NetworkFunction",
            "RESOURCE_TYPE_TO_CHECK": "tosca.resourceTypes.FRE",
            "PORT_ID_VALUE": "PORT_ID_LABEL",
            "PE_BW_DIR": "egress",
            "INTERFACE_TYPE": "tosca.resourceTypes.TPE",
            "MTU": 9250,
        },
        "CISCO": {
            "DOMAIN_TYPE": "urn:ciena:bp:domain:bpracisco",
            "SESSION_PROFILE_TYPE": "bpracisco.resourceTypes.SessionProfile",
            "DEVICE_TYPE": "bpracisco.resourceTypes.NetworkFunction",
            "RESOURCE_TYPE_TO_CHECK": "tosca.resourceTypes.TPE",
            "PORT_ID_VALUE": "PORT_ID_LABEL",
            "PE_BW_DIR": "egress",
            "INTERFACE_TYPE": "tosca.resourceTypes.TPE",
            "MTU": 9216,
        },
        # Ciena devices are not yet actually supported, but will be in designs we support for CTBH Pre-installs
        "CIENA": {
            "DOMAIN_TYPE": None,
            "SESSION_PROFILE_TYPE": None,
            "DEVICE_TYPE": None,
            "RESOURCE_TYPE_TO_CHECK": "tosca.resourceTypes.TPE",
            "PORT_ID_VALUE": "PORT_ID_LABEL",
            "PE_BW_DIR": "egress",
            "INTERFACE_TYPE": "tosca.resourceTypes.TPE",
            "MTU": 9600,
        },
        "HARMONIC": {
            "DOMAIN_TYPE": "urn:ciena:bp:domain:bprarphy",
            "SESSION_PROFILE_TYPE": "bprarphy.resourceTypes.SessionProfile",
            "DEVICE_TYPE": "bprarphy.resourceTypes.NetworkFunction",
            "PORT_ID_VALUE": "PORT_ID_LABEL",
            "PE_BW_DIR": "egress",
            "INTERFACE_TYPE": "tosca.resourceTypes.TPE",
            "MTU": 9216,
        },
        "NOKIA": {
            "DOMAIN_TYPE": "urn:ciena:bp:domain:bpranokia",
            "SESSION_PROFILE_TYPE": "bpranokia.resourceTypes.SessionProfile",
            "DEVICE_TYPE": "bpranokia.resourceTypes.NetworkFunction",
            "RESOURCE_TYPE_TO_CHECK": "tosca.resourceTypes.configModeler",
            "PORT_ID_VALUE": "PORT_ID_LABEL",
            "PE_BW_DIR": "egress",
            "INTERFACE_TYPE": "tosca.resourceTypes.configModeler",
            "MTU": 9216,
        },
    }

    BPO_STATES = {
        "AVAILABLE": {"state": "AVAILABLE", "description": "Device is available from BPO (Communication is up)"},
        "NOT_AVAILABLE": {
            "state": "NOT-AVAILABLE",
            "description": "Device is in BPO, but the communication state is down",
        },
        "NOT_ONBOARD": {"state": "NOT-ONBOARD", "description": "Device is not in BPO"},
        "UNKNOWN": {
            "state": "NOT-ONBOARD",
            "description": "Device is not in BPO, though ip reachable, unable to add device",
        },
    }
    COS_LOOKUP = {
        "PE": {
            "NONE": "SERVICEPORT_UNCLASSIFIED_COS",
            "BRONZE": "SERVICEPORT_BRONZE_COS",
            "SILVER": "SERVICEPORT_SILVER_COS",
            "GOLD": "SERVICEPORT_GOLD_COS",
        },
        "CPE": {"NONE": "PBIT-0", "BRONZE": "PBIT-1", "SILVER": "PBIT-3", "GOLD": "PBIT-5"},
    }
    SESSION_URL = "http://blueplanet:80/ractrl/api/v1/sessions/{}"
    NumberOfRetries = 1
    WaitSeconds = 5
    UrlLookup = {}

    EnableEnterExitLog = True

    def run(self):
        """ """
        self.plansdk_logger = logging.getLogger("plansdk.bpo.http")
        self.plansdk_logger.setLevel(logging.WARN)
        self.logger = logging.getLogger("scriptplan")
        self.logger.info("Input params: " + str(self.params))
        self.plansdk_logger = logging.getLogger("plansdk.bpo.http")
        self.plansdk_logger.setLevel(logging.WARN)

        self.the_class = self.__module__ + "." + self.__class__.__name__
        self.trace_res_id = None
        self.logger.info("Starting execution for " + str(self.the_class))

        # splunk logger
        self.splunk_logger = self.splunk_logger_setup()

        # Class properties
        self.common_plan_start_time = time.time()
        self.log_file = self.params["logFile"].split("/")[-1]
        self.resource_id = self.params["resourceId"]

        # Initialize syslog
        self.syslogger = None
        self.__initialize_syslog()

        # logging Formatter handler, strip out any sensitive data
        for handler in logging.root.handlers:
            handler.setFormatter(sensitiveLogDataFormatter(handler.formatter, ['"password":', "u'password':"]))

        try:
            # Extract resource and properties
            self.resource = self.bpo.resources.get(self.resource_id)
            self.logger.info("resource %s", json.dumps(self.resource, indent=4))
            self.properties = self.resource.get("properties")
        except RuntimeError as ex:
            self.logger.info("runtime error %s", ex)

            msg = self.error_formatter(
                self.SYSTEM_ERROR_TYPE,
                self.RESOURCE_GET_SUBCATEGORY,
                f"unable to get resource: {str(self.the_class)} {self.resource_id}",
            )
            self.categorized_error = msg
            self.exit_error(msg)

        try:
            self.enter_exit_log("STARTED PROCESSING")
            self.logger.debug(" ###################### STARTING PROCESSING ######################")
            response = self.process()
            self.logger.debug(" ###################### FINISHED PROCESSING ######################")
        except Exception as ex:
            self.logger.exception(ex)
            reason = "Error: " + str(ex)
            if any(formatted_system in str(ex) for formatted_system in self.FORMATTED_SYSTEM_LEVELS):
                # error is categorized and formatted appropriately
                msg = str(ex)
                self.categorized_error = msg
            else:
                # generic categorization
                msg = reason
                self.categorized_error = self.error_formatter(
                    self.PROCESS_ERROR_TYPE, "Exception Raised", f"class: {str(self.the_class)} reason: {msg}"
                )
            self.exit_error(msg)

        self.complete()
        return response

    def process(self):
        """method to be implemented by the derived class to perform the processing
        of the event.
        """
        #
        # TO BE IMPLEMENTED BY SUBCLASS
        #
        pass

    def exit_error(self, reason=None):
        """called when there is a plan failure

        No return. If no reason is provided a generic failure messasge
        will be provided.

        :param reason: Reason for the failure
        :type reason: str
        """

        if reason is None:
            msg = f"Error when running class {self.the_class}, please check file {self.log_file}."
        else:
            msg = f"Error in {self.the_class}, {reason}.  Please check file: {self.log_file}"

        self.logger.error(msg)
        self.logger.debug(str(traceback.extract_stack()))
        sys.stderr.write(msg)

        self.enter_exit_log(msg, "FAILED")

        sys.exit(1)

    def error_formatter(self, category, subcategory, detail, system="MDSO"):
        """
        :param category: High level category of the error (Missing Data, Connectivity Error, etc)
        :type category: str
        :param subcategory: More explicit category information (what data is missing, what connectivity error, etc)
        :type subcategory: str
        :param detail: More detailed information (what device had missing data, what communication state, etc)
        :type detail: str
        :return: error formatted for reporting categorizations
        :rtype: str
        """
        return f"{system} | {category} - {subcategory}: {detail}"

    def complete(self):
        """this can be called at the end of the process to show completeness"""
        self.logger.info(
            "Completing execution for %s, elapsed time: %s secs"
            % (str(self.the_class), str(int(time.time() - self.common_plan_start_time)))
        )
        self.enter_exit_log("Completed successfully", "COMPLETED")

    def get_domain_id(self, resource_id, product_id=None):
        """returns the domain id for the given resource_id or product_id

        Provide only one of the resource_id or product_id.  If using the product_id, make
        the resource_id None.  Returns the associated domain ID.

        :param resource_id: BPO UUID of a resource
        :param product_id: BPO UUID of the product
        :type resource_id: str
        :type product_id: str

        :return: Domain ID associated with the resource or product
        :rtype: str

        :Example:

        >>> import CommonPlan
        >>> p = CommonPlan()
        >>> p.get_domain_id(None, "5a985e3a-4e19-4c7d-96ea-dfad82b0c6ca")
        '5a985e3c-683b-4000-8ed7-a3b52dd0757e'
        """
        if resource_id is not None:
            # fetch the product id from the resource id
            product_id = self.bpo.resources.get(resource_id)["productId"]
            self.logger.info(product_id)
        if product_id is None:
            msg = self.error_formatter(
                self.MISSING_DATA_ERROR_TYPE,
                "Resource Property",
                f"resource: {resource_id} missing: product ID requested by: get_domain_id",
            )
            self.categorized_error = msg
            raise Exception(msg)

        product_info = self.bpo.market.get("/products/{}".format(product_id))
        domain_id = product_info["domainId"]
        return domain_id

    def is_string_uuid(self, string):
        """returns true if the input string is a Blue Planet UUID

        This can be used when a string input can be the label of the UUID
        of an object/resource.

        :param string: Arbitrary String
        :type string: str

        :return: True if the input string is a UUID
        :rtype: boolean

        :Example:

        >>> import CommonPlan
        >>> p = CommonPlan()
        >>> p.is_string_uuid('5a4bf87e-595f-4ec4-9ec8-67f114c1db88')
        True

        """
        UUID_PATTERN = re.compile(r"^[\da-f]{8}-([\da-f]{4}-){3}[\da-f]{12}$", re.IGNORECASE)

        if UUID_PATTERN.match(string):
            return True
        else:
            return False

    def get_resources_by_label_or_uuid(self, domain_id, resource_type, id_label):
        """returns the resources based on the ID/Label

        This is a helper function so that either the UUID or the Label can be passed
        into the "id" field.

        :param resource_type: Resource Type ID
        :param domain_id: Domain ID for the associated resource
        :param id_label: UUID or label of the resource
        :type resource_type: str
        :type domain_id: str
        :type id_label: str

        :return: Resources list that matches the input
        :rtype: list
        """
        return_value = []

        if self.is_string_uuid(id_label):
            return_value.append(self.get_resource(id_label))
        else:
            return_value = self.get_resources_by_domain_type_and_label(domain_id, resource_type, id_label)["items"]

        return return_value

    def get_active_resources(self, resource_type, domain_id=None, obfuscate=True):
        """returns the active resources of based on the resource_type

        This will return the resource whose 'orchState' is active based on the
        resource type and domain.  If domain id is not provided the built-in
        domain will be used.

        :param resource_type: Resource Type ID
        :param domain_id: Domain ID
        :param obfuscate: Market will hide properties marked 'obfuscate' if True
        :type resource_type: str
        :type domain_id: str

        :return: Resources list that matches the resource_type and domain
        :rtype: list
        """
        if not domain_id:
            domain_id = self.BUILT_IN_DOMAIN_ID

        return_value = self.get_resources_by_type_and_query(
            resource_type, query="orchState:active", domain_id=domain_id, obfuscate=obfuscate
        )

        return return_value

    def get_resources_by_type_and_query(self, resource_type, query=None, query_p=None, domain_id=None, obfuscate=True):
        """returns the resources of the resource_type and matching the query filter

        :param resource_type: Resource Type ID
        :param query: Query filter string (q=)
        :param query_p: Partial Query filter string (p=)
            - allows for partial searches as well as wildcards
        :param domain_id: Domain ID
        :param obfuscate: Market will hide properties marked 'obfuscate' if True
        :type resource_type: str
        :type domain_id: str

        :return: Resources list that matches the resource_type and domain
        :rtype: list
        """

        st = "/resources?resourceTypeId=%s" % resource_type

        if query is not None:
            st += "&q=%s" % query
        if query_p is not None:
            st += "&p=%s" % query_p
        if domain_id is not None:
            st += "&domainId=%s" % domain_id
        if obfuscate:
            # Use existing Charter method when asking for obfuscated values.
            return_value = self.mget(st).json()["items"]
        else:
            # Use standard BP get method for unobfuscated support.  All calls should
            # really use this but it requires to much testing at this point.
            params = {"obfuscate": False}
            return_value = self.bpo.market.get(st, params=params)["items"]

        return return_value

    def get_packet_bw_profile_by_id(self, rid, vendor=None):
        """returns the Packet Bandwidth Profile resource which properties.id = id

        :param id: matches properties.id from tosca.resourceTypes.PacketBandwidthProfile
        :param vendor: vendor name
        :type id: str
        :type vendor: str

        :return: PacketBandwidthProfile
        :rtype: dict
        """
        return_value = None
        if vendor is not None:
            vrid = vendor.upper() + ":" + rid
            return_value = self.get_resource_by_type_and_properties(
                self.BUILT_IN_BW_PROFILE_TYPE, {"id": vrid}, no_fail=True
            )

        if return_value is None:
            return_value = self.get_resource_by_type_and_properties(
                self.BUILT_IN_BW_PROFILE_TYPE, {"id": rid}, no_fail=True
            )

        return return_value

    def get_bandwidth_int_and_units(self, bandwidth):
        """returns a list of bandwidth(int) and units (str) for the input"""
        rate = 1
        unit = "m"
        bw = str(bandwidth).lower()
        response = re.search(r"[0-9]+", bw)
        if response:
            rate = int(response.group())

        if "g" in bw:
            unit = "g"
        elif "k" in bw:
            unit = "k"

        return [rate, unit]

    def get_bandwidth_in_kbps(self, bw):
        """
        Converts a bandwidth string to kbps
        Parameters:
            bw (str): The bandwidth string ex. 100M, 1G
        Returns:
            str: The bandwidth in kbps ex. 100000, 1000000
        """
        return int(re.findall(r"\d+", bw)[0]) * (1000000 if "g" in bw.lower() else 1000 if "m" in bw.lower() else 1)

    def get_built_in_product(self, resource_type):
        """returns the built-in product based on the resource type

        If none found it will return an exception

        :param resource_type: Resource Type ID
        :type resource_type: str

        :return: Product resource
        :rtype: dict
        """
        products = self.get_products_by_type_and_domain(resource_type, self.BUILT_IN_DOMAIN_ID)
        if len(products) == 0:
            msg = self.error_formatter(
                self.SYSTEM_ERROR_TYPE, "No Products for Resource Type", f"resource type: {resource_type}"
            )
            self.categorized_error = msg
            raise Exception(msg)

        return products[0]

    def get_bpo_contants_resource(self):
        """returns the Blue Planet Constants resource

        If none found it will return None.

        :return: Blue Planet Constants object
        :rtype: dict
        """
        return_value = None

        resources = self.get_active_resources(self.BUILT_IN_BPO_CONSTANTS_TYPE, obfuscate=False)
        if len(resources) > 0:
            return_value = resources[0]

        return return_value

    def get_associated_network_service_for_resource(self, resource):
        """this returns the NetworkService associated with the resource or resource_id

        If the resource is the resourceId, then it will get the resource ID.

        :param resource: Either full resources or ID of resource
        :type resource_type: dict or str

        :return: NetworkService resource.  None if not found.
        :rtype: dict
        """
        return_value = None

        resource_id = resource

        # If resource is the ID, get the resource
        if isinstance(resource, dict):
            resource_id = resource["id"]

        # Get the dependents
        network_services = self.get_dependents(resource_id, self.BUILT_IN_NETWORK_SERVICE_TYPE, True, False)

        if len(network_services) == 0:
            if not isinstance(resource, dict):
                resource = self.get_resource(resource)

            if resource is not None:
                circuit_id = resource["properties"].get("circuit_id", None)
                if circuit_id is not None:
                    self.logger.debug("Getting associated NS for resource: " + str(resource))
                    try:
                        return_value = self.get_associated_network_service_for_circuit_id(circuit_id)
                    except Exception:
                        self.logger.info("Unable to get Network Service for resource.")
                else:
                    self.logger.debug("Resource has no circuit_id. Skipping get request for NetworkService.")

        else:
            return_value = network_services[0]

        return return_value

    def get_network_function_by_host_or_ip(self, hostname="FQDN", ip=None, require_active=False):
        """returns the NetworkFunction that has the hostname

        If none are found, None is returned.  if require_active, none will be returned if none are active.

        :param hostname: routeable name (FQDN)
        :type hostname: str

        :param ip: IP
        :type ip: str

        :param require_active: only return active network function; await active if activating
        :type: bool

        :return: NetworkFunction
        :rtype: dict
        """
        hostnames = []
        tid = None
        hostnames.append(hostname)  # fqdn
        if hostname.find(".") > 0:
            tid = hostname.split(".")[0]
            hostnames.append(tid)
        if ip:
            hostnames.append(ip)

        found_network_functions = []
        for hostname in hostnames:
            if hostname == "DHCP":
                continue
            self.logger.info("Try for hostname:{}".format(hostname))
            response = self.get_resources_by_type_and_properties(
                "tosca.resourceTypes.NetworkFunction", {"ipAddress": hostname}
            )
            if len(response) > 0:
                if require_active:
                    found_network_functions.append(response)
                else:
                    return response[0]
        if require_active:
            return self.find_active_network_function(found_network_functions)
        self.logger.info(f"No Network Functions found for {hostnames}")

    def find_active_network_function(self, network_functions):
        network_functions = [resource for resources in network_functions for resource in resources]
        for resource in network_functions:
            if resource["orchState"] == "activating":
                try:
                    self.bpo.resources.await_active([resource["id"]])  # blocks for up to 90s
                except RuntimeError:
                    self.logger.warning(f"Network function {resource['id']} failed to activate")
                    continue  # keep looking through remainder for available nf
            if resource["properties"].get("communicationState") == "AVAILABLE":
                return resource

    def remove_resource_and_dependents(self, resource_id):
        resource_dependents = self.bpo.resources.get_dependents_with_filters(resource_id)
        self.logger.info(f"resource dependents: {resource_dependents}")
        if resource_dependents:
            for resource_dependent in resource_dependents:
                self.logger.info("existing resource_dependent id found: {}".format(resource_dependent["id"]))
                self.bpo.resources.patch(
                    resource_dependent["id"],
                    {"desiredOrchState": "terminated", "orchState": "terminated"},
                )
        self.bpo.resources.delete(resource_id)

    def get_network_function_by_host(self, hostname, is_hostname_tid=False):
        """returns the NetworkFunction that has the hostname

        If none are found, None is returned.

        :param hostname: IP or routeable name
        :type hostname: str
        :param is_hostname_tid: hostname is tid (not fqdn)
        :type tid: bool

        :return: NetworkFunction
        :rtype: dict
        """
        hostnames = []
        hostnames.append(hostname)
        if hostname.find(".") > 0:
            hostnames.append(hostname.split(".")[0])
        query_property = "label" if is_hostname_tid else "properties.ipAddress"
        return_value = None
        # retry for short and long hostnames/fqdn
        for hostname in hostnames:
            self.logger.info("Try to get NetworkFunction for hostname:{}".format(hostname))
            response = self.mget(
                "/resources?resourceTypeId={}&q={}:{}".format(
                    self.BUILT_IN_NETWORK_FUNCTION_TYPE, query_property, hostname
                )
            )
            if response.status_code > 300:
                self.logger.info("Unable to get NetworkFunction for {}".format(hostname))
            else:
                resources = response.json()["items"]
                if len(resources) > 0:
                    return_value = resources[0]
                    break

        return return_value

    def get_tpe_by_name_and_host(self, fqdn, tpe_name):
        """returns the TPE based on the host and TPE name

        Tpe name should be the NativeName of the TPE.  None if not found.  No errors are thrown.  It will check
        against the names by converting them all to upper case.

        :param hostname: IP or routeable name
        :param tpe_name: Name of the TPE ("ethernet-1")
        :type hostname: str
        :type tpe_name: str

        :return: tosca.resourceTypes.TPE
        :rtype: dict
        """
        nf = self.get_network_function_by_host(fqdn)
        if nf is None:
            return None

        if tpe_name.lower().startswith("ethernet "):
            tpe_name = "TPE_ETHERNET-{}_PTP".format(tpe_name.split(" ")[-1])
        elif tpe_name.lower().startswith("ethernet-"):
            tpe_name = "TPE_ETHERNET-{}_PTP".format(tpe_name.split("-")[-1])
        elif tpe_name.lower().startswith("access "):
            tpe_name = "TPE_{}_PTP".format(tpe_name.upper())
        elif tpe_name.lower().startswith("access-"):
            tpe_name = "TPE_{}_PTP".format(tpe_name.upper())
        elif tpe_name.lower().startswith("network-"):
            tpe_name = "TPE_{}_PTP".format(tpe_name.upper())
        elif "lan" in tpe_name.lower() or "wan" in tpe_name.lower():
            tpe_name = "TPE_{}_PTP".format(tpe_name.upper())
        else:
            tpe_name = tpe_name.lower()

        nf_provider_resource_id = nf["providerResourceId"]
        domain_id = nf_provider_resource_id.split("_")[1]
        tpe_provider_resource_id = "%s::%s" % (nf_provider_resource_id, tpe_name)

        url = "/resources?domainId=%s&providerResourceId=%s" % (domain_id, tpe_provider_resource_id)
        server_response = self.mget(url).json()

        if "items" in server_response and len(server_response["items"]) > 0:
            tpe = server_response["items"][0]
            if "properties" in tpe:
                return tpe

        return None

    def get_network_function_for_resource(self, resource):
        """will return the network function resource associated with the resource.

        If there is not a network function (Controller RA, will return return None.
        If there should be one, but is not an exception will be returned

        :param resource: Any BPO resource
        :type resource: str

        :return: Network Function
        :rtype: dict
        """
        if isinstance(resource, str):
            prid = resource
        else:
            prid = resource["providerResourceId"]

        nf_id = None
        try:
            nf_id = prid.split(":")[0].split("_")[2]
        except Exception:
            pass

        if not nf_id:
            return None

        return self.bpo.resources.get(nf_id)

    def get_associated_network_service_for_circuit_id(self, circuit_id, include_all=False):
        """this returns the NetworkService associated with the circuit_id

        If not found None returned (No exception thrown).  If the include_all is True then a list of
        the response is return.

        :param circuit_id: Circuit ID
        :type circuit_id: str

        :return: NetworkService resource.  None if not found.
        :rtype: dict/list (list if include_all is True)
        """
        resources = self.get_resources_by_type_and_properties(
            self.BUILT_IN_NETWORK_SERVICE_TYPE, {"circuit_id": circuit_id}
        )
        if include_all is True:
            return_value = resources
        else:
            return_value = resources[0] if resources else None

        return return_value

    def get_session_profile(self, device_vendor, domain_id, session_name=None):
        """returns the session profile associated with the domain

        If the session profile is the UUID it will get the session profile.
        If the session_name is None, then it will pick the first one that is returned.  Raises
        an exception if it cannot find a session profile.

        :param device_vendor: Name of device vendor to match the CommonPlan.COMMON_TYPE_LOOKUP
        :param domain_id: UUID of the domain
        :param session_name: UUID or Label of the Session Profile
        :type device_vendor: str
        :type domain_id: str
        :type session_name: str

        :return: Session Profile resource
        :rtype: dict
        """
        domain_lookup = self.COMMON_TYPE_LOOKUP.get(device_vendor, {})
        session_profile_type = domain_lookup.get("SESSION_PROFILE_TYPE")
        if not session_profile_type:
            msg = self.error_formatter(
                self.SYSTEM_ERROR_TYPE,
                "Session Profile Type",
                f"device vendor: {device_vendor} session profile type not defined",
            )
            self.categorized_error = msg
            raise Exception(msg)

        if session_name is None:
            session_profiles = self.get_resource_by_type_and_domain(session_profile_type, domain_id)
            self.logger.info(session_profiles)
        else:
            session_profiles = self.get_resources_by_label_or_uuid(domain_id, session_profile_type, session_name)

        if len(session_profiles) == 0:
            msg = self.error_formatter(
                self.MISSING_DATA_ERROR_TYPE,
                "Session Profiles",
                f"device vendor: {device_vendor} session profile type: {session_profile_type} domain: {domain_id}",
            )
            self.categorized_error = msg
            raise Exception(msg)

        session_profile = session_profiles[0]
        self.logger.info(f"Returning session profile: {session_profile}")

        return session_profile

    def get_associated_network_service(self, sid, observed=False):
        """returns the charter.resourceType.NetworkService based on the input

        THe input can be the UUID of any object in the NetworkService chain or the
        circuit name.  If none are found, None is returned

        :param sid: Either UUID of an object or the Circuit ID
        :param observed: Return the observed state of the resource
        :type uuid: str
        :type observed: boolean

        :return: charter.resourceTyps.NetworkService
        :rtype: dict
        """
        return_value = None

        if self.is_string_uuid(sid):
            dep = self.get_dependents(
                sid, resource_type=self.BUILT_IN_NETWORK_SERVICE_TYPE, recursive=True, exception_on_failure=False
            )

            if len(dep) > 0:
                return_value = dep[0]

        else:
            try:
                return_value = self.get_resource_by_type_and_properties(
                    self.BUILT_IN_NETWORK_SERVICE_TYPE, {"circuit_id": sid}, no_fail=True
                )
            except Exception:
                msg = self.error_formatter(
                    self.SYSTEM_ERROR_TYPE,
                    self.RESOURCE_GET_SUBCATEGORY,
                    f"id: {sid} missing: network service resource requested by: get_associated_network_service",
                )
                self.categorized_error = msg
                raise Exception(msg)

        if observed is True and return_value is not None:
            return_value = self.get_observed(return_value["id"])

        self.logger.info("Returning network service: " + str(return_value))
        return return_value

    def get_associated_circuit_details(self, uuid):
        """returns the charter.resourceTyps.CircuitDetails based on the input

        The input can be the UUID of any object in the NetworkService chain or the
        circuit name.  If none are found, None is returned

        :param uuid: Either UUID of an object or the Circuit ID
        :type uuid: str

        :return: charter.resourceTyps.CircuitDetails
        :rtype: dict
        """
        return_value = None

        network_service = None

        if self.is_string_uuid(uuid):
            service = self.get_resource(uuid)
            if service["resourceTypeId"] == self.BUILT_IN_NETWORK_SERVICE_TYPE:
                network_service = service

        if network_service is None:
            network_service = self.get_associated_network_service(uuid)

        if network_service is None:
            network_service = self.get_associated_network_service_update_or_delete_for_resource(uuid)

        if network_service is None:
            network_service = self.get_associated_resource(uuid, self.BUILT_IN_SERVICE_MAPPER_TYPE)

        if network_service is None:
            msg = self.error_formatter(
                self.SYSTEM_ERROR_TYPE,
                self.RESOURCE_GET_SUBCATEGORY,
                f"id: {uuid} missing: network service resource requested by: get_associated_circuit_details",
            )
            self.categorized_error = msg
            raise Exception(msg)

        try:
            ns_id = network_service["id"]
            dep = self.get_dependencies(
                ns_id,
                resource_type=self.BUILT_IN_CIRCUIT_DETAILS_TYPE,
                recursive=False,
                exception_on_failure=False,
            )
            if len(dep) > 0:
                return_value = dep[0]
        except Exception:
            msg = self.error_formatter(
                self.SYSTEM_ERROR_TYPE,
                self.RESOURCE_GET_SUBCATEGORY,
                f"id: {uuid} network service: {ns_id} missing: circuit details resource requested by: get_associated_circuit_details",
            )
            self.categorized_error = msg
            raise Exception(msg)

        self.logger.info("Returning circuit details: " + str(return_value))
        return return_value

    def get_associated_circuit_details_for_network_service(self, network_res_id):
        return_value = None
        try:
            dep = self.get_dependencies(
                network_res_id,
                resource_type=self.BUILT_IN_CIRCUIT_DETAILS_TYPE,
                recursive=False,
                exception_on_failure=False,
            )
            if len(dep) > 0:
                return_value = dep[0]
        except Exception:
            msg = self.error_formatter(
                self.SYSTEM_ERROR_TYPE,
                self.RESOURCE_GET_SUBCATEGORY,
                f"network service resource id: {network_res_id} \
                missing: circuit details resource \
                requested by: get_associated_circuit_details_for_network_service",
            )
            self.categorized_error = msg
            raise Exception(msg)

        self.logger.info("Returning circuit details: " + str(return_value))
        return return_value

    def get_service_data(self, circuit_details):
        return circuit_details["properties"]["service"][0]["data"]

    def determine_pbit(self, service_data, device_role="CPE"):
        cos = service_data["evc"][0]["cosNames"][0]["name"]
        return self.COS_LOOKUP[device_role][cos].split("-")[1]

    def determine_onboard_status(self, network_function_orch_state):
        return network_function_orch_state == "active"

    def get_devices_by_property_value(
        self, circuit_details, requested_property, requested_value, evaluate_negative=False
    ):
        """
        Return list of device dictionaries matching provided prop/value
        If evaluate_negative = True, return list of device dictionaries that do NOT match provided prop/value
        Example usage:
        self.get_devices_by_property_value(circuit_details, 'Role', 'CPE')
        Example return:
        [{'Host Name': 'CNI2TXR26AW',
        'Role': 'CPE',
        'Vendor': 'RAD',
        'Model': 'ETX-220A',
        'Management IP': '71.42.150.150',
        'Address': '11921 N MOPAC EXPY 78759',
        'FQDN': 'CNI2TXR26AW.DEV.CHTRSE.COM',
        'Equipment Status': 'LIVE',
        'Network Neighbor': 'AUSDTXIR2CW',
        'Client Neighbor': 'None',
        'Network Interface': 'ETHERNET-4/1',
        'Network Neighbor Interface': 'XE-0/2/1',
        'Client Interface': 'ETHERNET-1/9',
        'Client Neighbor Interface': 'None',
        'Network Interface Description': 'UPLINK:AUSDTXIR2CW:XE-0/2/1:71.42.150.150:',
        'Client Interface Description': 'EP-UNI:ELINE:TEST ACCT DEV@11921 N MOPAC EXPY 78759:51.L1XX.010124..TWCC:'},
        {'Host Name': 'CNI3TXR36ZW',
        'Role': 'CPE',
        'Vendor': 'RAD',
        'Model': 'ETX203AX/2SFP/2UTP2SFP',
        'Management IP': '71.42.150.173',
        'Address': '11921 N MOPAC EXPY 78759',
        'FQDN': 'CNI3TXR36ZW.DEV.CHTRSE.COM',
        'Equipment Status': 'LIVE',
        'Network Neighbor': 'AUSDTXIR3CW',
        'Client Neighbor': 'None',
        'Network Interface': 'ETHERNET-1',
        'Network Neighbor Interface': 'GE-0/0/8',
        'Client Interface': 'ETHERNET-2',
        'Client Neighbor Interface': 'None',
        'Network Interface Description': 'UPLINK:AUSDTXIR3CW:GE-0/0/8:71.42.150.173:',
        'Client Interface Description': 'EP-UNI:ELINE:TEST ACCT DEV@11921 N MOPAC EXPY 78759:51.L1XX.010124..TWCC:'}]"""
        devices_matching_criteria = []
        devices = self.get_devices_from_circuit_details(circuit_details)
        for device in devices:
            device_data = self.get_device_details_from_circuit_details_device(device)
            if evaluate_negative:
                if device_data.get(requested_property) != requested_value:
                    devices_matching_criteria.append(device_data)
            else:
                if device_data.get(requested_property) == requested_value:
                    devices_matching_criteria.append(device_data)
        return devices_matching_criteria

    def get_devices_from_circuit_details(self, circuit_details):
        return [node for topology in circuit_details["properties"]["topology"] for node in topology["data"]["node"]]

    def get_device_details_from_circuit_details_device(self, device):
        device_details = device["name"]
        return {detail["name"]: detail["value"] for detail in device_details}

    def create_device_dict_from_circuit_details(self, circuit_details):
        """ returns a dictionary of devices from CircuitDetails indexed by hostname

        :param circuit_details: CircuitDetails resource or Circuit details server response or its topology section
        :type circuit_details: obj

        :return: dict keyed by hostname with the properties
        :rtype: dict

        :example response:
        [
            {
                "CNI2TXR37ZW": {
                    "links": [
                        "AUSDTXIR3AW-GE-0/0/3_CNI2TXR37ZW-ETHERNET-1"
                    ],
                    "Client Interface Description": \
                        "EP-UNI:FIA:ANDROMEDA PROJECT TEST UPDATE@11921 N MOPAC EXPY:51.L1XX.008488..TWCC:",
                    "Client Neighbor": "None",
                    "Lags": [],
                    "Role": "CPE",
                    "Network Neighbor": "AUSDTXIR3AW",
                    "Vendor": "RAD",
                    "Network Interface Description": "UPLINK:AUSDTXIR3AW:GE-0/0/3:DHCP:",
                    "FQDN": "CNI2TXR37ZW.SW.TWCBIZ.COM",
                    "Management IP": "DHCP",
                    "Address": "11921 N MOPAC EXPY",
                    "Provisioned": "True",
                    "Network Interface": "ETHERNET-1",
                    "Bpo State": "AVAILABLE",
                    "Ip Reachable": "True",
                    "Client Neighbor Interface": "None",
                    "Model": "ETX203AX/2SFP/2UTP2SFP",
                    "Ports": [
                        "ETHERNET-1",
                        "ETHERNET-3"
                    ],
                    "Network Neighbor Interface": "GE-0/0/3",
                    "Client Interface": "ETHERNET-3",
                    "Reachable Via": "FQDN",
                    "Host Name": "CNI2TXR37ZW"
                },
                "AUSDTXIR2CW": {
                    "Ip Reachable": "True",
        """
        return_value = []
        spoke_dict = {}
        name_value_pair = {}
        link_list = []
        port_list = []
        lag_port = {}
        lag_list = []
        # lag_members = []
        new_links = []
        topology = circuit_details
        if "properties" in circuit_details.keys() and "topology" in circuit_details["properties"]:
            topology = circuit_details["properties"]["topology"]
        if "topology" in circuit_details.keys():
            topology = circuit_details["topology"]

        for topo in topology:
            for node in topo["data"]["node"]:
                for name in node["name"]:
                    name_value_pair[name["name"]] = name["value"]
                tmp_lag_dict = defaultdict(list)
                for ownedNodeEdgePoint in node["ownedNodeEdgePoint"]:
                    port_name = self.get_node_port_name_from_uuid(ownedNodeEdgePoint["uuid"])[1]
                    for name in ownedNodeEdgePoint["name"]:
                        if name["name"] == "LAG Member":
                            lag_name = name["value"]
                            tmp_lag_dict[lag_name].append(port_name)
                    port_list.append(port_name)

                spoke_dict[node["uuid"]] = name_value_pair
                name_value_pair = {}
                if len(tmp_lag_dict) > 0:
                    for key, value in tmp_lag_dict.items():
                        lag_port[key] = value
                        lag_list.append(lag_port)
                        lag_port = {}
                spoke_dict[node["uuid"]]["Ports"] = port_list
                spoke_dict[node["uuid"]]["Lags"] = lag_list
                # lag_members = []
                port_list = []
                lag_list = []
                lag_port = {}
            return_value.append(spoke_dict)
            spoke_dict = {}

        for spoke in return_value:
            for key in spoke.keys():
                topo = topology[return_value.index(spoke)]
                if "link" in topo["data"].keys():
                    for link in topo["data"]["link"]:
                        if key in link["uuid"]:
                            link_list.append(link["uuid"])

                    spoke[key]["links"] = list(set(link_list))
                    link_list = []

        for device_dict in return_value:
            for node, values in device_dict.items():
                node_links = values.get("links")
                if node_links is not None:
                    for link in node_links:
                        node_ports = link.split("_")
                        lag_link = link
                        for np in node_ports:
                            new_np = self.replace_port_with_lag(np, device_dict)
                            lag_link = lag_link.replace(np, new_np)
                        new_links.append(lag_link)

                    values["links"] = list(set(new_links))
                    new_links = []

        self.logger.debug("Returning List of Spoke dicts: " + json.dumps(return_value, indent=4))
        return return_value

    def replace_port_with_lag(self, node_port, device_dict):
        port = self.get_node_port_name_from_uuid(node_port)[1]
        node = self.get_node_port_name_from_uuid(node_port)[0]
        new_node_port = node_port
        for lag in device_dict[node]["Lags"]:
            if isinstance(lag, dict) and port in list(lag.values())[0]:
                lag_port = list(lag.keys())[0]
            if "lag_port" in locals():
                new_node_port = node_port.replace(port, lag_port)

        return new_node_port

    def get_unique_links(self, link_list):
        """
        generates uninque links from a list of links.
        considers the fact that  same link may look different
        if the order of node-port is changed
        """

        set_node_ports = []
        list_node_ports = []
        list_links = []
        for i in range(0, len(link_list)):
            set_node_ports.append(set(link_list[i].split("/")))
        for np in set_node_ports:
            list_node_ports.append(list(np))
        for node_port in list_node_ports:
            list_links.append("_".join(c for c in node_port))
        unique_links = list(set(list_links))

        return unique_links

    def get_node_port_name_from_uuid(self, port_uuid):
        if (port_uuid[3]) == "-":
            node_name_1, node_name_2, port_name = port_uuid.split("-", 2)
            node_name = node_name_1 + "-" + node_name_2
        else:
            node_name, port_name = port_uuid.split("-", 1)

        if re.match(r"^[-a-zA-Z0-9]*$", node_name) and len(node_name) == 11:
            return [node_name, port_name]
        else:
            msg = self.error_formatter(
                self.INCORRECT_DATA_ERROR_TYPE, "Node Name", f"name: {node_name}", system=self.CIRCUIT_DETAILS_DATABASE
            )
            self.categorized_error = msg
            raise Exception(msg)

    def get_node_property(self, circuit_details, node_uuid, prop, which_index=None):
        return_value = None
        if "properties" in circuit_details.keys():
            topology = circuit_details["properties"]["topology"]
        else:
            topology = circuit_details["topology"]
        index = 0
        for topo in topology:
            if which_index is None or which_index == index:
                for node in topo["data"]["node"]:
                    if node["uuid"] == node_uuid:
                        return_value_list = [pair["value"] for pair in node["name"] if pair["name"] == prop]
                        if not len(return_value_list) == 0:
                            return_value = return_value_list[0]
            index += 1

        if return_value is None:
            self.logger.warn("unable to find property %s for node %s " % (prop, node_uuid))
        self.logger.info("Requested property: {}, value: {}".format(prop, return_value))
        return return_value

    def get_pe_nodes_from_circuit_details(self, circuit_details):
        """return the PE Host Names from Circuit Details
        If ther are none, it will return an empty string

        :param circuit_details: Circuit details resource
        :type circuit_details: dictionary

        :return list of host names
        :rtype list of str
        """
        return_value = []
        for spoke in self.create_device_dict_from_circuit_details(circuit_details):
            for values in spoke.values():
                if values["Role"] == "PE":
                    return_value.append(values["FQDN"])

        return return_value

    def get_node_role(self, circuit_details, node_uuid, which_index=None):
        """
        returns a node role i.e. AGG or CPE or PE etc

        :param circuit_details: Circuit details resource
        :type dictionary

        :param node - node uuid
        :type str

        :return Node Role
        :rtype str
        """
        role = self.get_node_property(circuit_details, node_uuid, "Role", which_index=which_index)
        if role is None:
            msg = self.error_formatter(
                self.MISSING_DATA_ERROR_TYPE,
                "Device Role",
                f"device: {node_uuid}",
                system=self.CIRCUIT_DETAILS_DATABASE,
            )
            self.categorized_error = msg
            self.exit_error(msg)

        return role

    def get_node_fqdn(self, circuit_details, node_uuid):
        """
        returns a node Fully Qualified domain name

        :param circuit_details: Circuit details resource
        :type dictionary

        :param node - node uuid
        :type str

        :return Node fqdn
        :rtype str
        """
        fqdn = self.get_node_property(circuit_details, node_uuid, "FQDN")
        if fqdn is None:
            msg = self.error_formatter(
                self.MISSING_DATA_ERROR_TYPE, "FQDN", f"device: {node_uuid}", system=self.CIRCUIT_DETAILS_DATABASE
            )
            self.categorized_error = msg
            self.exit_error(msg)

        return fqdn

    def is_node_provisioned(self, circuit_details, node_uuid, port=None):
        """
        returns if a node has yet been provisioned or not
        """

        nodes = []
        node_uuids = []
        if port is not None:
            node_port = node_uuid + "-" + port
        topology = circuit_details["properties"]["topology"]
        evc = circuit_details["properties"]["service"][0]["data"]["evc"][0]
        for topo in topology:
            for node in topo["data"]["node"]:
                if node["uuid"] == node_uuid:
                    if port is not None:
                        for ownedNodeEdgePoint in node["ownedNodeEdgePoint"]:
                            if ownedNodeEdgePoint["uuid"] == node_port:
                                nodes.append(node)
                                break
                    else:
                        # if no evcId is specified, do not add duplicate nodes
                        # two PEs with same node name is expected in locally switched PE
                        # otherwise we will add the node regardless and exit with error (see below)
                        if "evcId" not in evc and node["uuid"] in node_uuids:
                            continue
                        nodes.append(node)
                        node_uuids.append(node["uuid"])

        if len(nodes) == 0:
            msg = self.error_formatter(
                self.MISSING_DATA_ERROR_TYPE,
                self.TOPOLOGIES_DATA_SUBCATEGORY,
                f"device: {node_uuid}",
                system=self.CIRCUIT_DETAILS_DATABASE,
            )
            self.categorized_error = msg
            self.exit_error(msg)

        elif len(nodes) > 1:
            msg = self.error_formatter(
                self.INCORRECT_DATA_ERROR_TYPE,
                "Multiple Nodes Single Device",
                f"device: {node_uuid} nodes: {nodes}",
                system=self.CIRCUIT_DETAILS_DATABASE,
            )
            self.categorized_error = msg
            self.exit_error(msg)
        else:
            node = nodes[0]
            return_value_list = [pair["value"] for pair in node["name"] if pair["name"] == "Provisioned"]
            if len(return_value_list) == 0:
                return_value = "False"
            if not len(return_value_list) == 0:
                return_value = return_value_list[0]

        return return_value

    def get_port_role(self, circuit_details, port):
        """
        returns port role
        """

        role = None
        if "properties" in circuit_details.keys():
            topology = circuit_details["properties"]["topology"]
        else:
            topology = circuit_details["topology"]

        node_name, lag_name = self.get_node_port_name_from_uuid(port)
        self.logger.info("node name: %s" % node_name)

        for topo in topology:
            for node in topo["data"]["node"]:
                for ownedNodeEdgePoint in node["ownedNodeEdgePoint"]:
                    if ownedNodeEdgePoint["uuid"] == port:
                        role = [name["value"] for name in ownedNodeEdgePoint["name"] if name["name"] == "Role"][0]
                        return role

        # Check if its a lag port
        if role is None:
            member_ports = []
            spoke_list = self.create_device_dict_from_circuit_details(circuit_details)
            for spoke in spoke_list:
                self.logger.info(list(spoke.keys()))
                if node_name in spoke.keys():
                    device = spoke[node_name]
                    for lag in device["Lags"]:
                        self.logger.info("lag port: %s" % lag)
                        if lag_name in lag.keys():
                            member_ports = lag[lag_name]

        if not len(member_ports) == 0:
            member_port_roles = []
            for port in member_ports:
                port_uuid = node_name + "-" + port
                for topo in topology:
                    for node in topo["data"]["node"]:
                        for ownedNodeEdgePoint in node["ownedNodeEdgePoint"]:
                            if ownedNodeEdgePoint["uuid"] == port_uuid:
                                member_port_role = [
                                    name["value"] for name in ownedNodeEdgePoint["name"] if name["name"] == "Role"
                                ][0]
                                member_port_roles.append(member_port_role)
            if not len(set(member_port_roles)) <= 1:
                msg = self.error_formatter(
                    self.INCORRECT_DATA_ERROR_TYPE,
                    "LAG Member Port Role Mismatch",
                    f"device: {node_name} lagged port: {port} port roles: {member_port_roles}",
                    system=self.CIRCUIT_DETAILS_DATABASE,
                )
                self.categorized_error = msg
                self.exit_error(msg)

            role = member_port_roles[0]

        if role is None:
            msg = self.error_formatter(
                self.MISSING_DATA_ERROR_TYPE, "Port Role", f"device: {node_name}", system=self.CIRCUIT_DETAILS_DATABASE
            )
            self.categorized_error = msg
            self.exit_error(msg)

        self.logger.debug("Role for port %s is role %s" % (port, role))

        return role

    def get_port_description(self, circuit_details, nodeport):
        """
        returns description for the required port
        """

        port_description = None
        for topology in circuit_details["properties"]["topology"]:
            for node in topology["data"]["node"]:
                if node["uuid"] == self.get_node_port_name_from_uuid(nodeport)[0]:
                    filtered_ports = [
                        name["name"]
                        for name in node["name"]
                        if name["value"] == self.get_node_port_name_from_uuid(nodeport)[1]
                    ]
                    if len(filtered_ports) == 0:
                        # If port not found, pull LAG data to convert from LAG to port
                        lag_members = []
                        for edge in node["ownedNodeEdgePoint"]:
                            # Pull LAG name from details
                            lag_name = [name["value"] for name in edge["name"] if name["name"] == "LAG Member"]
                            if lag_name and lag_name[0] == self.get_node_port_name_from_uuid(nodeport)[1]:
                                lag_members.append(
                                    [name["value"] for name in edge["name"] if name["name"] == "Name"][0]
                                )
                        # Pull description from any matching LAG member
                        port_type = [name["name"] for name in node["name"] if name["value"] in lag_members][0]
                    else:
                        port_type = filtered_ports[0]
                    port_description_variable = port_type + " Description"
                    keys_list = [name["name"] for name in node["name"]]
                    if port_description_variable in keys_list:
                        port_description = [
                            name["value"] for name in node["name"] if name["name"] == port_description_variable
                        ][0]
                    else:
                        self.logger.debug(
                            "Port Description Variable %s not found in list %s"
                            % (port_description_variable, node["name"])
                        )

        return str(port_description)

    def get_port_transportId(self, circuit_details, nodeport):
        """
        returns transportId for the required port
        """

        # port_transportId = None
        if "properties" in circuit_details.keys():
            topology = circuit_details["properties"]["topology"]
        else:
            topology = circuit_details["topology"]
        for topology in topology:
            for node in topology["data"]["node"]:
                if node["uuid"] == self.get_node_port_name_from_uuid(nodeport)[0]:
                    for ownedNodeEdgePoint in node["ownedNodeEdgePoint"]:
                        if ownedNodeEdgePoint["uuid"].upper() == nodeport.upper():
                            for name in ownedNodeEdgePoint["name"]:
                                if name["name"] == "Transport ID":
                                    self.logger.debug(
                                        "Port {} transportId Variable: {}".format(nodeport, name["value"])
                                    )
                                    return str(name["value"])
        self.logger.debug("Port {} has no transportId Variable".format(nodeport))
        return None

    def get_service_type(self, circuit_details):
        """
        determines if a service is EP-type or EVP-type
        """

        cd_service = (
            circuit_details["service"] if circuit_details.get("service") else circuit_details["properties"]["service"]
        )
        raw_service_type = cd_service[0]["data"]["evc"][0]["serviceType"]
        if raw_service_type in ["EPL", "EP-LAN", "EP-TREE", "IP"]:
            service_type = "EP-UNI"
        else:
            service_type = "EVP-UNI"

        return service_type

    def get_node_bpo_state(self, circuit_details, node_uuid):
        """
        returns state of node on BPO

        :param circuit_details: Circuit details resource
        :type dictionary

        :param node - node uuid
        :type str

        :return Node State in BPO
        :rtype str
        """

        bpo_state = self.get_node_property(circuit_details, node_uuid, "Bpo State")

        return bpo_state

    def get_node_model(self, circuit_details, node_uuid):
        """
        returns Device model of node

        :param circuit_details: Circuit details resource
        :type dictionary

        :param node - node uuid
        :type str

        :return Device Model
        :rtype str
        """

        model = self.get_node_property(circuit_details, node_uuid, "Model")

        return model

    def get_node_vendor(self, circuit_details, node_uuid):
        """
        returns node's vendor

        :param circuit_details: Circuit details resource
        :type dictionary

        :param node - node uuid
        :type str

        :return Node vendor
        :rtype str
        """
        vendor = self.get_node_property(circuit_details, node_uuid, "Vendor")
        if vendor is None:
            msg = self.error_formatter(
                self.MISSING_DATA_ERROR_TYPE, "Vendor", f"device: {node_uuid}", system=self.CIRCUIT_DETAILS_DATABASE
            )
            self.categorized_error = msg
            self.exit_error(msg)

        return vendor

    def get_last_device(self, circuit_details, node_uuid):
        """
        returns last device in topo

        :param circuit_details: Circuit details resource
        :type dictionary

        :param node - node uuid
        :type str

        :return last device in topo
        :rtype str
        """
        count_devices = 0
        client_neighbor = self.get_node_client_neighbor(circuit_details, node_uuid)
        current_client_neighbor = None
        while str(client_neighbor) != "None":
            count_devices += 1
            current_client_neighbor = client_neighbor
            client_neighbor = self.get_node_client_neighbor(circuit_details, client_neighbor)
            if count_devices == 5:
                break
        return current_client_neighbor

    def get_node_client_neighbor(self, circuit_details, node_uuid, which_index=None):
        """
        returns node's client neighbor

        :param circuit_details: Circuit details resource
        :type dictionary

        :param node - node uuid
        :type str

        :return Node's client neighbor
        :rtype str
        """

        client_neighbor = self.get_node_property(circuit_details, node_uuid, "Client Neighbor", which_index)

        return client_neighbor

    def get_node_client_interface(self, circuit_details, node_uuid, which_index=None):
        """
        returns node's client interface

        :param circuit_details: Circuit details resource
        :type dictionary

        :param node - node uuid
        :type str

        :return Node's client interface
        :rtype str
        """

        client_interface = self.get_node_property(
            circuit_details, node_uuid, "Client Interface", which_index=which_index
        )

        return client_interface

    def get_node_client_interface_description(self, circuit_details, node_uuid):
        """
        returns node's client interface description

        :param circuit_details: Circuit details resource
        :type dictionary

        :param node - node uuid
        :type str

        :return Node's client interface description
        :rtype str
        """

        client_interface = self.get_node_property(circuit_details, node_uuid, "Client Interface Description")

        return client_interface

    def get_node_client_interface_role(self, circuit_details, node_uuid):
        """
        returns node's client interface role

        :param circuit_details: Circuit details resource
        :type dictionary

        :param node - node uuid
        :type str

        :return Node's client interface role
        :rtype str
        """

        client_interface = self.get_node_property(circuit_details, node_uuid, "Client Interface")
        client_interface_role = self.get_port_role(circuit_details, node_uuid + "-" + client_interface)

        return client_interface_role

    def get_node_network_interface(self, circuit_details, node_uuid, which_index=None):
        """
        returns node's network interface

        :param circuit_details: Circuit details resource
        :type dictionary

        :param node - node uuid
        :type str

        :return Node's network interface
        :rtype str
        """

        nw_interface = self.get_node_property(circuit_details, node_uuid, "Network Interface", which_index=which_index)

        return nw_interface

    def get_node_network_neighbor(self, circuit_details, node_uuid):
        """
        returns node's network neighbor

        :param circuit_details: Circuit details resource
        :type dictionary

        :param node - node uuid
        :type str

        :return Node's network neighbor
        :rtype str
        """

        network_neighbor = self.get_node_property(circuit_details, node_uuid, "Network Neighbor")

        return network_neighbor

    def get_node_network_neighbor_interface(self, circuit_details, node_uuid):
        """
        returns node's network neighbor interface

        :param circuit_details: Circuit details resource
        :type dictionary

        :param node - node uuid
        :type str

        :return Node's network neighbor interface
        :rtype str
        """

        network_neighbor_interface = self.get_node_property(circuit_details, node_uuid, "Network Neighbor Interface")

        return network_neighbor_interface

    def get_node_client_neighbor_interface(self, circuit_details, node_uuid, which_index=None):
        """
        returns node's client neighbor interface

        :param circuit_details: Circuit details resource
        :type dictionary

        :param node - node uuid
        :type str

        :return Node's client neighbor interface
        :rtype str
        """

        network_neighbor_interface = self.get_node_property(
            circuit_details, node_uuid, "Client Neighbor Interface", which_index
        )

        return network_neighbor_interface

    def get_node_hostname(self, circuit_details, node_uuid):
        """
        returns node's Host name

        :param circuit_details: Circuit details resource
        :type dictionary

        :param node - node uuid
        :type str

        :return Node Host name
        :rtype str
        """

        hostname = self.get_node_property(circuit_details, node_uuid, "Host Name")
        if hostname is None:
            msg = self.error_formatter(
                self.MISSING_DATA_ERROR_TYPE, "Host Name", f"device: {node_uuid}", system=self.CIRCUIT_DETAILS_DATABASE
            )
            self.categorized_error = msg
            self.exit_error(msg)

        return hostname

    def get_node_address(self, circuit_details, node_uuid):
        """
        returns node's Host name

        :param circuit_details: Circuit details resource
        :type dictionary

        :param node - node uuid
        :type str

        :return Node address
        :rtype str
        """

        address = self.get_node_property(circuit_details, node_uuid, "Address")
        if address is None:
            msg = self.error_formatter(
                self.MISSING_DATA_ERROR_TYPE, "Address", f"device: {node_uuid}", system=self.CIRCUIT_DETAILS_DATABASE
            )
            self.categorized_error = msg
            self.exit_error(msg)

        return address

    def get_customer_addresses(self, circuit_details):
        """
        Function returns the list of customer addresses under the evc endpoints
        For FIA a single address [0]
        For ELINE service 2 addresses assuming the order of the endpoints is provided
        in the same order as the topology list.

        :param circuit_details: Circuit Details dictionary

        :return: Customer addresses list
        :rtype: list
        """
        return_value = []
        service = (
            circuit_details["properties"]["service"] if "properties" in circuit_details else circuit_details["service"]
        )
        evc_service_type = service[0]["data"]["evc"][0]["serviceType"]
        if evc_service_type in ["EPL", "EVPL"]:
            customer_addr_topo_0 = service[0]["data"]["evc"][0]["endPoints"][0]["address"]
            customer_addr_topo_1 = service[0]["data"]["evc"][0]["endPoints"][1]["address"]
            return_value.append(customer_addr_topo_0.replace("\r", "").replace("\n", " "))
            return_value.append(customer_addr_topo_1.replace("\r", "").replace("\n", " "))
        else:
            customer_addr_topo_0 = service[0]["data"]["evc"][0]["endPoints"][0]["address"]
            return_value.append(customer_addr_topo_0.replace("\r", "").replace("\n", " "))

        return return_value

    def get_node_management_ip(self, circuit_details, node_uuid):
        """
        returns node's Host name

        :param circuit_details: Circuit details resource
        :type dictionary

        :param node - node uuid
        :type str

        :return Node mgmt ip
        :rtype str
        """

        ip = self.get_node_property(circuit_details, node_uuid, "Management IP")
        if ip is None:
            msg = self.error_formatter(
                self.MISSING_DATA_ERROR_TYPE, "IP Address", f"device: {node_uuid}", system=self.CIRCUIT_DETAILS_DATABASE
            )
            self.categorized_error = msg
            self.exit_error(msg)

        return ip

    def get_node_reachability(self, circuit_details, node_uuid):
        """
        returns node's reachable_via

        :param circuit_details: Circuit details resource
        :type dictionary

        :param node - node uuid
        :type str

        :return Node mgmt ip
        :rtype str
        """

        reachable_via = self.get_node_property(circuit_details, node_uuid, "Reachable Via")
        if reachable_via is None:
            msg = self.error_formatter(self.MISSING_DATA_ERROR_TYPE, "Reachable Via", f"device: {node_uuid}")
            self.categorized_error = msg
            self.exit_error(msg)

        return reachable_via

    def is_device_newly_onboarded(self, circuit_details, node_uuid):
        """
        returns if the device is newly onboarded onto bpo

        :param circuit_details: Circuit details resource
        :type dictionary

        :param node - node uuid
        :type str

        :return if the device is newly onboarded to bpo
        :rtype boolean
        """

        new_onboard = self.get_node_property(circuit_details, node_uuid, "Newly Onboarded")

        if new_onboard == "False":
            return False
        else:
            return True

    def is_device_ip_accessible(self, circuit_details, node_uuid):
        """
        returns if the device is accessible from bpo

        :param circuit_details: Circuit details resource
        :type dictionary

        :param node - node uuid
        :type str

        :return if the device is accessible bpo
        :rtype boolean
        """
        is_accessible = self.get_node_property(circuit_details, node_uuid, "Ip Accessible")

        if is_accessible == "False":
            return False
        else:
            return True

    def update_devices_prop_value(self, device_list, circuit_details_id, prop, value):
        """Updates the device list properties.
        :param device_list: list of device host names
        :type device_list: list

        :param circuit_details_id : circuit details resource_id
        :type circuit_details_id: str

        :param prop: property to be updated
        :type prop: str

        :param value: value to be updated
        :type prop: str
        """
        # Refresh circuit details so that it does not over write others changes
        circuit_details = self.bpo.resources.get(circuit_details_id)
        for device in device_list:
            self.update_node_prop_value(device, circuit_details_id, prop, value)

        try:
            self.await_differences_cleared_collect_timing(circuit_details["label"], circuit_details_id, interval=5.0)
        except Exception as ex:
            self.logger.info("Circuit %s failed update with error: %s" % (circuit_details_id, str(ex)))

    def update_node_prop_value(self, node_uuid, circuit_details_id, prop, value):
        """
        updates device's prop and its value to circuit details resource

        :param node_uuid: node uuid
        :type str

        :param circuit_details_id : circuit details resource_id
        :type str

        :param prop: property to be updated
        :type str or list

        :param value: value to be updated
        :type str or list

        """

        circuit_details_resource = self.get_resource(circuit_details_id)
        if isinstance(prop, str):
            prop = [prop]
            value = [value]
        for prop_cnt in range(len(prop)):
            for topology in circuit_details_resource["properties"]["topology"]:
                for node in topology["data"]["node"]:
                    if node["uuid"] == node_uuid:
                        for name in node["name"]:
                            if name["name"] == prop[prop_cnt]:
                                req_op = "Update"
                                name["value"] = value[prop_cnt]
                            else:
                                req_op = "Add"
                        if req_op == "Add":
                            prop_dict = {"name": prop[prop_cnt], "value": str(value[prop_cnt])}
                            node["name"].extend([prop_dict])

        patch = {"properties": circuit_details_resource["properties"]}

        self.patch_resource(circuit_details_id, patch)

    def get_topology_spoke_for_host_port(self, node_uuid, circuit_details, port_uuid=None):
        """
        returns the spoke to which node belongs
        """
        topo_list = []
        topology = circuit_details["properties"]["topology"]
        for topo in topology:
            for node in topo["data"]["node"]:
                if node["uuid"] == node_uuid:
                    if port_uuid is not None:
                        for ownedNodeEdgePoint in node["ownedNodeEdgePoint"]:
                            for name in ownedNodeEdgePoint["name"]:
                                if name["value"] == port_uuid:
                                    topo_list.append(topo)
                    else:
                        topo_list.append(topo)

        if len(topo_list) > 1:
            msg = self.error_formatter(
                self.INCORRECT_DATA_ERROR_TYPE,
                "Multiple Spokes Single Device",
                f"device: {node_uuid}, port: {port_uuid} spokes: {topo_list}",
                system=self.CIRCUIT_DETAILS_DATABASE,
            )
            self.categorized_error = msg
            self.exit_error(msg)

        elif len(topo_list) == 0:
            msg = self.error_formatter(
                self.MISSING_DATA_ERROR_TYPE, self.TOPOLOGIES_DATA_SUBCATEGORY, f"device: {node_uuid} port: {port_uuid}"
            )
            self.categorized_error = msg
            self.exit_error(msg)

        else:
            topo = {"topology": topo_list}

        return topo

    def get_neighbor_from_link(self, node, link):
        nodes = []
        for node_port in link.split("_"):
            if node_port[3] == "-":
                node_name_1, node_name_2, port_name = node_port.split("-", 2)
                node_name = node_name_1 + "-" + node_name_2
                nodes.append(node_name)
            else:
                nodes.append(node_port.split("-")[0])

        if node not in nodes:
            msg = self.error_formatter(
                self.INCORRECT_DATA_ERROR_TYPE,
                "Neighbor Device Not Linked",
                f"device: {node} link: {link}",
                system=self.CIRCUIT_DETAILS_DATABASE,
            )
            self.categorized_error = msg
            self.exit_error(msg)

        req_node = [n for n in nodes if n != node][0]

        return req_node

    def get_device_list(self, spoke_list):
        device_list = []
        for spoke in spoke_list:
            device_list.extend(spoke.keys())

        device_list = list(set(device_list))
        return device_list

    def get_updated_circuit_detail_host_prop(self, circuit_details, host, prop, value):
        """will find the host in the circuit_details and update its property

        It will make a copy of the input circuit details so the original object is not
        affected by the changes.

        :param circuit_details: Circuit Details object
        :param host: Host name of the device affected
        :param prop: The property that is to be updated
        :param value: The new value of the property
        :type circuit_details: dict (charter.resourceTypes.CircuitDetails)
        :type host: Host name of the device affected
        :type prop: The property that is to be updated
        :type value: The new value of the property

        :return: a new CircuitDetails
        :rtype: dict (charter.resourceTypes.CircuitDetails)
        """
        return_value = deepcopy(circuit_details)

        updated_topology = []
        cd_props = circuit_details["properties"]
        for topology in cd_props["topology"]:
            for dtype, device in topology.items():
                if "pe" in dtype and isinstance(device, dict):
                    return_value[device["hostname"]] = host
                    device[prop] = value
                elif "agg" in dtype:
                    for agg_dev in device:
                        if agg_dev["hostname"] == host:
                            agg_dev[prop] = value

            updated_topology.append(topology)

        return_value["properties"]["topology"] = updated_topology

        return return_value

    def get_vlan_id_list_from_string(self, vlan_list):
        """returns a list of VLAN ID (int) from an input list

        For instance 100-101 would return [100, 101].  Valid separators are , .. / -

        Input can be a list of strings or just a string.  If no VLANS can be deciphered,
        empty list is returned

        :param vlan_list: Single string or List of VLAN integers
        :type vlan_list: list or str

        :return: a list of individual VLANs
        :rtype: list

        :Example:

        >>> import CommonPlan
        >>> p = CommonPlan()
        >>> p.get_vlan_id_list_from_string("100,105,110-115,122")
        [100, 105, 110, 111, 112, 113, 114, 115, 122]
        """
        return_value = []
        if isinstance(vlan_list, str):
            vlan_list = [vlan_list]

        for vlan_str in vlan_list:
            if isinstance(vlan_str, int):
                vlan_str = str(vlan_str)
            vlan_str = vlan_str.replace("-", "..").strip()
            vlan_str = vlan_str.replace("/", "..").strip()
            vlan_str = vlan_str.replace("[", "").strip()
            vlan_str = vlan_str.replace("]", "").strip()

            for vlan_sub in vlan_str.split(","):
                if ".." in vlan_sub:
                    comp = vlan_sub.split("..")
                    for x in range(int(comp[0].strip()), (int(comp[1].strip()) + 1)):
                        if x not in return_value:
                            return_value.append(x)
                elif int(vlan_sub.strip()) not in return_value:
                    return_value.append(int(vlan_sub.strip()))

        return_value.sort()
        return return_value

    def get_tpe_by_name_and_host_return_errors(self, fqdn, tpe_name):
        """returns the TPE based on the host and TPE name

        Tpe name should be the NativeName of the TPE.  None if not found.  No errors are thrown.  It will check
        against the names by converting them all to upper case.

        :param hostname: IP or routeable name
        :param tpe_name: Name of the TPE ("ethernet-1")
        :type hostname: str
        :type tpe_name: str

        :return: tosca.resourceTypes.TPE
        :rtype: dict
        """
        nf = self.get_network_function_by_host(fqdn)
        self.logger.info("NetworkFunction under get_tpe(): %s" % nf)
        if nf is None:
            return {"status": "Device not present - %s  |  NetworkFunction: %s" % (fqdn, nf)}
        if nf["orchState"] != "active":
            return {"status": "Device %s is not MDSO reachable  |  NetworkFunction: %s" % (fqdn, nf)}

        nf_provider_resource_id = nf["providerResourceId"]
        domain_id = nf_provider_resource_id.split("_")[1]
        tpe_provider_resource_id = "%s::%s" % (nf_provider_resource_id, tpe_name)

        url = "/resources?domainId=%s&providerResourceId=%s" % (domain_id, tpe_provider_resource_id)
        server_response = self.mget(url).json()
        self.logger.info("Server response for %s: %s" % (tpe_provider_resource_id, server_response))

        if "items" in server_response and len(server_response["items"]) > 0:
            tpe = server_response["items"][0]
            if "properties" in tpe:
                return tpe
        return {"status": "Port not present on the device  |  server_response: %s" % (server_response)}

    def get_dependents_by_type_and_query(self, resource_id, resource_type, query=None, recursive=False):
        """return the list of dependents

        Dependents are those resources that depend upon this resource.  A specific resource
        type can be passed in as a filter. A Query is an optional parameter which can
         be passed to limit the numnber of responses.  If recursive is set to true
        it will walk the resource relationship tree to get all associated resources.

        :param resource_id: Id of the source resource
        :param resource_type: (Optional) Single resource type or List of resource types filter
        :param recursive: Perform a recursive search (Default is False)
        :param query: Query to limit the responses
        :type resource_id: str
        :type resource_type: list/str
        :type recursive: boolean
        :type query: str

        :return: List of resource objects
        :rtype: list of dicts
        """

        st = "/resources/%s/dependents?recursive=%s&resourceTypeId=%s" % (
            resource_id,
            str(recursive).lower(),
            resource_type,
        )

        if query is not None:
            st += "&q=%s" % query

        res = self.mget(st).json()["items"]

        return res

    def check_port_activation_resources(self, fqdn, port_name, returntype="standard"):
        """return status: Port Activation instance with resourceId <resourceId>
        already availabel with device <deviceName> and port <portname>
        if the port activation instance is already available in the market with the given deviceName and PortName

        :param fqdn: devicename
        :param port_name : Port name
        :type fqdn: str
        "type port_name: str
        """
        url = "/resources?domainId=built-in&resourceTypeId=%s" % (self.BUILT_IN_RESOURCE_PORT_ACTIVATION_TYPE)
        # Add deviceName and portname as query filters
        url += "&q=properties.deviceName:%s,properties.portname:%s,orchState:active" % (fqdn, port_name)
        port_activation_instances = self.mget(url).json()

        if returntype == "standard":
            if "items" in port_activation_instances and len(port_activation_instances["items"]) > 0:
                port_inst = port_activation_instances["items"][0]
                return {
                    "status": "Port Activation resource with resourceId %s is already available with device: %s and port: %s"
                    % (port_inst["id"], fqdn, port_name)
                }

            return {"status": "Resource does not exist - %s" % port_activation_instances}

        else:
            if "items" in port_activation_instances and len(port_activation_instances["items"]) > 0:
                port_inst = port_activation_instances["items"][0]
                return {"resourceId": port_inst["id"]}

            return None

    def enter_exit_log(self, message, state="STARTED"):
        """this is will create a log message in the overall ST orchestration logs

        It will first find if the orchestration file exists for the resource/traceid
        if not it will create one.  If so it will append to it.  No return provided.
        To turn off the trace log set EnableEnterExitLog is False in the Class
        declaration of the main ST (before __init()__ method).

        :param message: Message to output to the trace log
        :param state: Completion start of the action (Normally: STARTED, COMPLETED, FAILED),
                      if none provided, set to STARTED
        :type message: str
        :type state: str
        """
        if self.EnableEnterExitLog is False:
            return

        trace_id = self.params["traceId"]
        new_trace = True

        response = self.mget(
            "/resources?resourceTypeId={}&q=properties.trace_id:{}".format(self.BUILT_IN_TRACE_LOG_TYPE, trace_id)
        )
        trace = None
        if response.status_code < 300:
            resources = response.json()["items"]
            if len(resources) > 0:
                trace = resources[0]
                self.trace_res_id = trace["id"]
                new_trace = False

        # If there is not a trace, create one
        if trace is None:
            if self.resource["resourceTypeId"] in self.ORCH_TRACE_PRODUCTS:
                service = self.resource
            else:
                # see if resource is associated with service activation, update or resource
                service = self.get_associated_network_service_for_resource(self.resource_id)
                if service is None:
                    service = self.get_associated_network_service_update_or_delete_for_resource(self.resource["id"])
            # if we get here with no service still, this product isn't meant to have an orch trace
            if service is None:
                self.logger.info("Resource not associated with network service, so skipping trace log")
                return
            # Get the user
            user_res = self.tron_get("/users/" + self.params["bpUserId"]).json()

            product = self.get_built_in_product(self.BUILT_IN_TRACE_LOG_TYPE)
            trace = {
                "label": service["label"] + ".orch_trace",
                "productId": product["id"],
                "properties": {
                    "trace_id": trace_id,
                    "origination_id": service["id"],
                    "operation": self.params["operation"],
                    "start_time_sec": int(time.time()),
                    "user_name": user_res["username"],
                    "circuit_name": service["properties"]["circuit_id"],
                    "orchestration_trace": [],
                },
            }

        # Add the trace log
        start_time = trace["properties"]["start_time_sec"]
        trace_details = {
            "timestamp": str(time.strftime("%H:%M:%S")),
            "resource_type": self.resource["resourceTypeId"],
            "resource_id": self.resource_id,
            "process": self.the_class,
            "log_file": self.log_file,
            "message": message,
            "state": state,
            "elapsed_time": int(time.time() - start_time),
        }

        # only add categorized_error to trace_log if it exist
        # this error will be updated in the network_service parent_resource
        if hasattr(self, "categorized_error"):
            trace_details["categorized_error"] = self.categorized_error

        # only add resource_name to trace_log if it exist
        # this will be used to determine status in parent_resource
        if self.properties.get("resource_name"):
            trace_details["resource_name"] = self.properties.get("resource_name")

        if new_trace:
            trace["properties"]["orchestration_trace"].append(trace_details)
            self.create_active_resource(trace["label"], service["id"], trace)
        else:
            for i in range(0, 1):
                i = i
                trace["properties"]["orchestration_trace"].append(trace_details)
                response = self.mpatch("/resources/%s" % trace["id"], {"properties": trace["properties"]})
                if response.status_code >= 300:
                    time.sleep(1)
                    trace = self.get_resource(self.trace_res_id)
                else:
                    break

        # WRITE TO SYSLOG
        trace_details["trace_id"] = trace_id
        trace_details["operation"] = self.params["operation"]
        trace_details["circuit_name"] = trace["properties"]["circuit_name"]
        self.syslogger.info(json.dumps(trace_details))

    def get_vlan_strings_from_list(self, vlan_list):
        """returns a list of strings representing the VLAN ids

        Each entry will be either a single VLAN or a range of VLANS
        """
        first_value = -1
        last_value = -1
        return_value = []
        for vid in self.get_vlan_id_list_from_string(vlan_list):
            if first_value < 0:
                first_value = vid
                last_value = vid
                continue
            if vid == last_value + 1:
                last_value = vid
                continue
            if last_value == first_value:
                return_value.append(str(first_value))
            else:
                return_value.append(str(first_value) + ".." + str(last_value))
            first_value = vid
            last_value = vid

        if last_value == first_value:
            return_value.append(str(first_value))
        else:
            return_value.append(str(first_value) + ".." + str(last_value))
        first_value = vid
        last_value = vid

        return return_value

    def __initialize_syslog(self):
        """this will initialize the logs"""
        self.syslogger = logging.getLogger("syslog")
        self.syslogger.setLevel(logging.INFO)
        # add handler to the logger
        handler = logging.handlers.SysLogHandler("/dev/log")
        # add formatter to the handler
        formatter = logging.Formatter(
            self.params["traceId"]
            + ': { "loggerName":"%(name)s", "asciTime":"%(asctime)s", '
            + '"pathName":"%(pathname)s",'
            + '"logRecordCreationTime":"%(created)f", "functionName":"%(funcName)s", '
            '"levelNo":"%(levelno)s", '
            + '"lineNo":"%(lineno)d", "time":"%(msecs)d", "levelName":"%(levelname)s", '
            + '"message":"%(message)s"}'
        )
        handler.formatter = formatter
        self.syslogger.addHandler(handler)

    def get_port_res_from_port_name_and_device_id(self, port_name, device_id, device_role=None):
        """
        returns port resource id by taking port name and
        device resource id as input
        """

        device_res = self.bpo.resources.get(device_id)
        device_domain = self.bpo.market.get("/products/%s" % device_res["productId"])["domainId"]
        try:
            if device_res["properties"].get("resourceType") is not None:
                device_type = device_res["properties"]["resourceType"]
            else:
                self.logger.warning("ResourceType not found. Attempting to use type.")
                device_type = device_res["properties"]["type"]
        except Exception as e:
            msg = self.error_formatter(
                self.MISSING_DATA_ERROR_TYPE,
                "Resource Type Property",
                f"Unable to find port resource from port name {port_name} and device resource: {device_id} error: {e}",
            )
            self.categorized_error = msg
            self.exit_error(msg)

        if device_type in ["XG116PRO", "XG116PRO (H)", "XG120PRO"]:
            port_name = port_name.replace("ETH-PORT", "ETH_PORT")

        port_res = self.get_by_provider_resource_id(
            device_domain, device_res["providerResourceId"] + "::" + "TPE_" + port_name + "_PTP"
        )

        if port_res is None:
            if port_name.lower().startswith("lag"):
                port_res = self.get_by_provider_resource_id(
                    device_domain,
                    device_res["providerResourceId"] + "::" + "TPE_LAG-{}".format(port_name.split(" ")[-1]) + "_PTP",
                )
        if port_res is None:
            port_res = self.get_by_provider_resource_id(
                device_domain, device_res["providerResourceId"] + "::" + port_name
            )
        if port_res is None:
            port_res = self.get_by_provider_resource_id(
                device_domain, device_res["providerResourceId"] + "::" + port_name.upper()
            )
        if port_res is None:
            port_res = self.get_by_provider_resource_id(
                device_domain, device_res["providerResourceId"] + "::" + port_name.lower()
            )
        if port_res is None:
            port_name = port_name.replace("TenGigabitEthernet", "TenGigE")
            port_res = self.get_by_provider_resource_id(
                device_domain, device_res["providerResourceId"] + "::" + port_name
            )
        return port_res

    def get_port_id_from_port_name_and_device_id_retry(self, port_name, device_id, device_role=None, retries=20):
        """
        returns port resource id by taking port name, retry every 10 secs and
        device resource id as input
        """
        port_res = None
        for _cnt in range(retries):
            port_res = self.get_port_res_from_port_name_and_device_id(port_name, device_id, device_role)
            if port_res:
                break
            if _cnt == 0:
                self.bpo.market.post("/resources/{}/resync".format(device_id))
            time.sleep(10)

        if port_res is None:
            msg = self.error_formatter(
                self.MISSING_DATA_ERROR_TYPE,
                self.RESOURCE_GET_SUBCATEGORY,
                f"id: {device_id} port: {port_name} retries: {retries} \
                missing: port resource requested by: get_port_id_from_port_name_and_device_id_retry",
            )
            self.categorized_error = msg
            self.exit_error(msg)

        port_id = port_res["id"]
        return port_id

    """
    ## Deprecated and replaced with the rety fn

    def get_port_id_from_port_name_and_device_id(self, port_name, device_id, device_role=None):
        '''
        returns port resource id by taking port name and
        device resource id as input
        '''

        port_res = self.get_port_res_from_port_name_and_device_id(port_name, device_id, device_role)

        if port_res is None:
            self.exit_error("unable to get port resource for port %s, device id %s" % (port_name,
                                                                                        device_id))

        port_id = port_res['id']
        return port_id
    """

    def get_node_client_uniq_prop(self, circuit_details, node_uuid, prop, port_uuid=None):
        """
        returns node's unique client property

        :param circuit_details: Circuit details resource
        :type dictionary

        :param node - node_uuid
        :type str

        :param node - port_uuid
        :type str

        :return Node's client property
        :rtype str
        """
        return_value = None
        if "properties" in circuit_details.keys():
            topology = circuit_details["properties"]["topology"]
        else:
            topology = circuit_details["topology"]
        return_value_list = []
        for topo in topology:
            for node in topo["data"]["node"]:
                if node["uuid"] == node_uuid:
                    if port_uuid is not None:
                        for ownedNodeEdgePoint in node["ownedNodeEdgePoint"]:
                            for name in ownedNodeEdgePoint["name"]:
                                if name["value"] == port_uuid:
                                    return_value_list = [pair["value"] for pair in node["name"] if pair["name"] == prop]

        if len(return_value_list) > 1:
            msg = self.error_formatter(
                self.INCORRECT_DATA_ERROR_TYPE,
                "Multiple Spokes Single Device Port",
                f"device: {node_uuid} port: {port_uuid} spokes: {return_value_list}",
                system=self.CIRCUIT_DETAILS_DATABASE,
            )
            self.categorized_error = msg
            self.exit_error(msg)

        elif len(return_value_list) == 0:
            msg = self.error_formatter(
                self.MISSING_DATA_ERROR_TYPE, "Topology Spoke Device Port", f"device: {node_uuid} port: {port_uuid}"
            )
            self.categorized_error = msg
            self.exit_error(msg)

        else:
            return_value = return_value_list[0]

        return return_value

    def is_handoff_device(self, device_values):
        return device_values["Role"] == "CPE" or (
            device_values["Role"] == "MTU" and str(device_values["Client Neighbor"]).lower() == "none"
        )

    def update_device_states(self, circuit_details_id, device_list):
        # Refresh circuit details so that it does not over write others changes
        circuit_details = self.bpo.resources.get(circuit_details_id)
        for device in device_list:
            circuit_details = self.update_node_prop_value(device, circuit_details_id, "Provisioned", "True")

        try:
            self.await_differences_cleared_collect_timing(circuit_details["label"], circuit_details_id, interval=5.0)
        except Exception as ex:
            self.logger.info("Circuit %s failed update with error: %s" % (circuit_details_id, str(ex)))

    def get_network_instances_for_device_and_type(self, device, itype=None, group_name=None, evc_id=None):
        """returns a list of Network Instances (routing instances) for a device

        Returns an empty list of none are found.

        :param device: Device Name or ID
        :type device: string

        :param itype: type of instance (Optional)
        :type itype: str

        :return List of NetworkInstances
        :rtype list of NetworkInstances
        """
        return_value = []
        if self.is_string_uuid(device):
            nf_id = device
        else:
            nf = self.get_network_function_by_host(device)
            nf_id = nf["id"]
        try:
            deps = self.get_dependents(nf_id, self.BUILT_IN_NETWORK_INSTANCE_TYPE, recursive=True)
            filtered_deps = deps
            if itype:
                filtered_deps = []
                for dep in deps:
                    if (
                        dep["properties"].get("config", {}).get("type")
                        and dep["properties"]["config"]["type"].lower() == itype.lower()
                    ):
                        filtered_deps.append(dep)

            return_value = filtered_deps
            if group_name or evc_id:
                return_value = []
                for dep in filtered_deps:
                    if group_name:
                        if dep["properties"]["name"].lower() == group_name.lower():
                            return_value.append(dep)

                    if evc_id and dep not in return_value:
                        dep_evc_id = dep["properties"]["config"].get("routeTarget")
                        dep_evc_id = dep_evc_id.split(":")[-1] if dep_evc_id else dep_evc_id

                        if dep_evc_id == evc_id:
                            return_value.append(dep)

        except Exception as e:
            self.logger.exception(e)
            msg = self.error_formatter(
                self.MISSING_DATA_ERROR_TYPE, "Network Instances", f"device: {device} network function id: {nf_id}"
            )
            self.categorized_error = msg
            self.exit_error(msg)

        return return_value

    def build_monitor_resource(
        self,
        label,
        condition,
        json_contents,
        http_method="PATCH",
        parent_id=None,
        http_url=None,
        target_resource_id=None,
        topic="bp.ra.v1.alarms",
        user=None,
        tenant=None,
    ):
        # build a monitor resource
        self.logger.info(
            "Input params: label: %s,  condition: %s,  json_contents: %s,  http_method: %s, http_url: %s, \
                 target_resource_id: %s, topic: %s"
            % (label, condition, str(json_contents), http_method, str(http_url), str(target_resource_id), topic)
        )

        monitor_product_id = self.get_built_in_product("tosca.resourceTypes.Monitor")

        if target_resource_id is None:
            target_resource_id = self.params["resourceId"]
        if user is None:
            user = self.params["bpUserId"]  # in bpo.py
        if tenant is None:
            tenant = self.params["bpTenantId"]
        if http_url is None:
            http_url = "%s/bpocore/market/api/v1/resources/%s" % (self.params["uri"], target_resource_id)
        else:
            if "%s" in http_url:
                http_url = http_url % target_resource_id

            http_url = self.get_url("/bpocore/market/api/v1", http_url)

        monitor_res = {
            "label": label,
            "productId": monitor_product_id["id"],
            "properties": {
                "topic": topic,
                "condition": condition,
                "actionInfo": {
                    "transport": "HTTP",
                    "httpTransportInfo": {
                        "method": http_method,
                        "url": http_url,
                        "headers": [
                            {"name": "Cyan-Internal-Request", "value": "1"},
                            {"name": "bp-user-id", "value": user},
                            {"name": "bp-tenant-id", "value": tenant},
                        ],
                        "body": {"contentType": "application/json", "contents": json_contents},
                    },
                },
            },
        }
        self.logger.debug("creating monitor resource: " + str(monitor_res))

        linked_resource_id = parent_id if parent_id else self.params["resourceId"]
        monitor_resource = self.bpo.resources.create(linked_resource_id, monitor_res)
        return monitor_resource

    def log(self, message):
        """Override self.log function"""
        self.logger.info(message)

    def execute_ra_command_file(self, device, command_file, parameters=None, headers=None, retry=None):
        """executes the GET command file on the RA based on device

        The Device name, provideResourceId, IP, ID or object could be passed

        :param device: Device IP, ID or provierResourceId
        :param command_file: File on the RA to call
        :type device: str or dict
        :type command_file: str

        :return: response of command
        :rtype: tuple (status_code, reason, json())
        """

        if parameters is None:
            parameters = {}

        if not isinstance(device, dict) and device.startswith("bpo_"):
            ra_url = self.get_ra_url_for_session_id(device)
        else:
            ra_url = self.get_ra_url_for_device(device)

        ra_url += "/execute"
        self.logger.debug("RA Cuthrough url: " + ra_url)
        data = {"command": command_file, "parameters": parameters}

        return self.__ra_post_with_retry(ra_url, data=data, headers=headers, retry=retry)

    def ra_put_with_retry(self, url, data, headers=None, ignore_status_codes=[], var1=0):
        """Performs the retry mechanism for the URL command.

        Uses the self.NumberOfRetries and self.WaitSeconds for the retry
        mechanisms.  If it is an error response, an Exception will be raised

        :param command: HTTP Command
        :param parameters: Data Parameters for the PUT call
        :param headers: HTTP Headers
        :param ignore_status_codes: List of integers that it will return
        :type command: string
        :type parameters: dict
        :type headers: dict
        :type ignore_status_codes: list of ints

        :return: response of command
        :resource_type: tuple (status_code, reason, json())
        """
        if headers is None:
            headers = {"Content-Type": "application/json"}

        if data is None:
            data = {}

        response = None
        latest_response_code = None
        try_index = 0

        while try_index == 0 or try_index <= self.NumberOfRetries:
            try_index += 1
            if var1 == 1:
                response = requests.put(url, data=data, verify=False, headers=headers)
            else:
                response = requests.put(url, data=json.dumps(data), verify=False, headers=headers)

            latest_response_code = response.status_code
            if (
                latest_response_code < 300
                or latest_response_code in ignore_status_codes
                or try_index > self.NumberOfRetries
            ):
                break
            self.logger.warn("Failure in executing command to RA, trying again in %s seconds." % str(self.WaitSeconds))
            time.sleep(self.WaitSeconds)

        if latest_response_code >= 300 and latest_response_code not in ignore_status_codes:
            raise Exception(
                "Error making URL call.  Code: {}, while executing command: {} with Result: {}".format(
                    str(latest_response_code), response.json()["command"], response.json()["result"]
                )
            )

        return response

    def __ra_get_with_retry(self, command, headers={}, ignore_status_codes=[]):
        """Performs the retry mechanism for the URL command.

        Uses the self.NumberOfRetries and self.WaitSeconds for the retry
        mechanisms.  If it is an error response, an Exception will be raised

        :param command: HTTP Command
        :param headers: HTTP Headers
        :param ignore_status_codes: List of integers that it will return
        :type command: string
        :type headers: dict
        :type ignore_status_codes: list of ints

        :return: response of command
        :rtype: tuple (status_code, reason, json())
        """
        if headers is None:
            headers = {"Content-Type": "application/json"}

        response = None
        latest_response_code = None
        try_index = 0

        while try_index == 0 or try_index <= self.NumberOfRetries:
            try_index += 1
            response = requests.get(command, headers=headers)
            self.logger.debug(
                "Response: try_number={}, status_code={}, reason={}".format(
                    str(try_index), response.status_code, response.reason
                )
            )
            latest_response_code = response.status_code
            if (
                latest_response_code < 300
                or latest_response_code in ignore_status_codes
                or try_index > self.NumberOfRetries
            ):
                break
            self.logger.warn("Failure in executing command to RA, trying again in %s seconds." % str(self.WaitSeconds))
            time.sleep(self.WaitSeconds)

        if latest_response_code >= 300 and latest_response_code not in ignore_status_codes:
            msg = self.error_formatter(
                self.SYSTEM_ERROR_TYPE,
                "RA Get",
                f"command: {command} code: {str(latest_response_code)} response: {response.reason}",
            )
            self.categorized_error = msg
            raise Exception(msg)

        return response

    def __ra_post_with_retry(self, url, data, headers=None, ignore_status_codes=[], retry=None):
        """Performs the retry mechanism for the URL command.

        Uses the self.NumberOfRetries and self.WaitSeconds for the retry
        mechanisms.  If it is an error response, an Exception will be raised

        :param command: HTTP Command
        :param parameters: Data Parameters for the POST call
        :param headers: HTTP Headers
        :param ignore_status_codes: List of integers that it will return
        :type command: string
        :type parameters: dict
        :type headers: dict
        :type ignore_status_codes: list of ints

        :return: response of command
        :rtype: tuple (status_code, reason, json())
        """
        if headers is None:
            headers = {"Content-Type": "application/json"}

        if data is None:
            data = {}

        if retry is None:
            retry = self.NumberOfRetries

        response = None
        latest_response_code = None
        try_index = 0

        while try_index == 0 or try_index <= retry:
            try_index += 1
            response = requests.post(url, data=json.dumps(data), verify=False, headers=headers)
            self.logger.debug(
                f"Response: try_number={try_index}, status_code={response.status_code}, reason={response.reason}"
            )
            latest_response_code = response.status_code
            if latest_response_code < 300 or latest_response_code in ignore_status_codes or try_index > retry:
                break
            self.logger.warning(f"Failure in executing command to RA, trying again in {self.WaitSeconds} seconds.")
            time.sleep(self.WaitSeconds)

        self.logger.debug(f"{response = }")
        try:
            response_content = response.json()
        except requests.exceptions.JSONDecodeError:
            response_content = "No response when attempting RA Post with retry"
        self.logger.debug(f"Post response after while loop: {response = } {response_content}")

        if latest_response_code >= 300 and latest_response_code not in ignore_status_codes:
            msg = self.error_formatter(
                self.SYSTEM_ERROR_TYPE,
                "RA Post",
                f"command: {data.get('command')} code: {latest_response_code} response: {response_content}",
            )
            self.categorized_error = msg
            raise Exception(msg)

        return response

    def get_ra_url_for_session_id(self, session_id):
        """Returns the URL for the RA based in the session ID of the device

        Exceptions when there is an error connecting the RACTL or if
        the session is not established.

        :param session_id: Session ID of the device
        :type session_id: string

        :return: url for device
        :rtype: str
        """
        if session_id in self.UrlLookup.keys():
            return self.UrlLookup[session_id]

        response = self.__ra_get_with_retry(
            self.SESSION_URL.format(session_id), headers={"Content-Type": "application/json"}
        )
        if response is None:
            msg = self.error_formatter(
                self.SYSTEM_ERROR_TYPE,
                "RA Get",
                f"command: {self.SESSION_URL.format(session_id)} code: NA, response: No response when attempting to get session URL",
            )
            self.categorized_error = msg
            raise Exception(msg)

        ra_url = "http://blueplanet:80/ractrl/api/v1/devices/" + str(session_id)

        return ra_url

    def post_bpprov_filter(self, resource_id):
        """Sends an request to bpprovlogfilter API to create log filter for given resource

        The log filter microservice will retrieve device dependencies for the service and copy related bpprov logs
        to a target directory

        :param resource_id: Resource ID of service
        :return:
        """
        type_list = []
        for rtype in self.COMMON_TYPE_LOOKUP:
            type_list.append(self.COMMON_TYPE_LOOKUP[rtype]["DEVICE_TYPE"])
        type_list.append(self.BUILT_IN_FRE_TYPE)
        type_list.append(self.BUILT_IN_TPE_TYPE)
        type_str = ",".join(type_list)
        headers = {"Content-Type": "application/json"}
        url = "http://blueplanet:80/bplogfilter/api/v1/bpprovlogfilter?resourceId={}&deviceTypes={}".format(
            resource_id, type_str
        )
        data = {}
        response = requests.post(url, data=json.dumps(data), headers=headers)
        self.logger.debug(
            "Response: status_code={}, reason={}, json={}".format(
                response.status_code, response.reason, response.json()
            )
        )

        if response.status_code >= 300:
            msg = self.error_formatter(
                self.SYSTEM_ERROR_TYPE,
                "BP Prov Log Filter",
                f"url: {url} code: {response.status_code} response: {response.reason}",
            )
            self.categorized_error = msg
            raise Exception(msg)

    def get_network_construct_id_by_device_id(self, device_id):
        """
        returns the resource id of network construct
        associated with the device
        """

        network_construct = self.get_network_construct_by_device_id(device_id)
        network_construct_id = network_construct["id"]

        return network_construct_id

    def get_network_construct_by_device_id(self, device_id):
        """
        returns the resource of network construct
        associated with the device
        """

        network_constructs = self.get_resources_by_type_and_properties(
            self.BUILT_IN_NETWORK_CONSTRUCT_TYPE, {"device": device_id}
        )
        if len(network_constructs) != 1:
            msg = self.error_formatter(
                self.INCORRECT_DATA_ERROR_TYPE,
                "Network Constructs",
                f"device: {device_id} network constructs found: {len(network_constructs)}",
            )
            self.categorized_error = msg
            self.exit_error(msg)

        return network_constructs[0]

    def get_service_userLabel(self, circuit_details):
        """
        generate Service User Label for Particular node port
        """
        customer_address = self.get_customer_addresses(circuit_details)
        self.logger.info("Customer address: {}".format(customer_address))
        customer_zipcode = customer_address[0].split(" ")[-1]
        service_description = circuit_details["properties"]["service"][0]["data"]["evc"][0]["endPoints"][0]["userLabel"]
        self.logger.info("Customer zipcode: {}".format(customer_zipcode))
        self.logger.info("Service description for service is %s " % service_description)

        return service_description.replace("\r", "").replace("\n", "")

    def get_associated_network_service_update_or_delete_for_resource(self, resource_id):
        """
        :param resource_id: resource id
        :return: return_value either network service update resource or delete resource
        gets associated network service update resource or delete resource
        based on rtype for the resource id mentioned.
        """

        return_value = None
        update_type = self.BUILT_IN_NETWORK_SERVICE_UPDATE_TYPE
        delete_type = self.BUILT_IN_NETWORK_SERVICE_DELETE_TYPE
        for rtype in [update_type, delete_type]:
            res_deps = self.get_dependents(resource_id, rtype, True, False)
            if len(res_deps) == 1:
                return_value = res_deps[0]
                break
            if len(res_deps) > 1:
                msg = self.error_formatter(
                    self.INCORRECT_DATA_ERROR_TYPE,
                    "Resource Dependents",
                    f"resource type: {rtype} associated resources found: {len(res_deps)} expected: 1",
                )
                self.categorized_error = msg
                self.exit_error(msg)

        return return_value

    def get_all_circuit_devices(self, circuit_details):
        """
        fetches the devices present on the circuit
        """

        spoke_list = self.create_device_dict_from_circuit_details(circuit_details)
        device_list = self.get_device_list(spoke_list)
        return_value = device_list

        return return_value

    def get_ordered_topology(self, device_dict):
        """This will return the array of devices associated with a specific hostname that
        are in the same spoke chain.

        Chain defined as PE --> AGG --> MTU --> CPE (and combinations).

        :param device_dict: device dictionary indexed by hostname
        :device_dict type: obj

        :return: list of dicts keyed by hostname with the properties
        :rtype: list
        """
        pe_list = []
        section = []
        section_list = []
        node_dict = {}

        for uuid, device in device_dict.items():
            if device["Role"] == "PE":
                pe_list.append(uuid)
            if len(pe_list) > 1:
                msg = self.error_formatter(
                    self.INCORRECT_DATA_ERROR_TYPE,
                    "More Than One PE Found In Spoke",
                    f"PE devices: {pe_list}",
                    system=self.CIRCUIT_DETAILS_DATABASE,
                )
                self.categorized_error = msg
                self.exit_error(msg)

        pe = pe_list[0]

        section.append(pe)
        last_node = pe
        next_link = None
        last_link = None
        link_list = None
        neighbor = None
        while True:
            link_list = device_dict[last_node].get("links")
            if link_list is None:
                break
            if len(link_list) == 0:
                break
            elif len(link_list) == 1:
                if link_list[0] == last_link:
                    break
                next_link = link_list[0]
            else:
                next_link = [li for li in link_list if not li == last_link][0]
            neighbor = self.get_neighbor_from_link(last_node, next_link)
            section.append(neighbor)
            if device_dict[neighbor]["Role"] == "CPE":
                break
            last_node = neighbor
            last_link = next_link

        for node in section:
            node_dict[node] = device_dict[node]
            section_list.append(node_dict)
            node_dict = {}

        self.logger.debug("Returning topology chain %s" % json.dumps(section_list, indent=4))
        return section_list

    def soft_terminate_process(self):
        for ra_resource in self.get_all_associated_ra_resources():
            for ns_resource in self.get_all_associated_dependents(ra_resource["id"]):
                self.logger.debug(
                    "Deleting relationship between %s and %s" % (ns_resource["label"], ra_resource["label"])
                )
                if ra_resource["discovered"] is False:
                    if len(ra_resource.get("differences", [])) > 0:
                        observed_resource = self.bpo.resources.get_observed(ra_resource["id"])
                        self.bpo.resources.patch(ra_resource["id"], {"properties": observed_resource["properties"]})
                        self.await_differences_cleared_collect_timing(ra_resource["label"], ra_resource["id"])

                self.bpo.relationships.delete_by_source_and_target(ns_resource["id"], ra_resource["id"])

        self.logger.info("Completed soft termination")

    def get_all_associated_ra_resources(self):
        """returns the list of RA resources that have a relationship to the network service"""
        return_value = []
        for dependency in self.bpo.market.get("/resources/%s/dependencies?recursive=true" % self.resource["id"])[
            "items"
        ]:
            self.all_dependencies_ids.append(dependency["id"])
            if (
                dependency.get("providerResourceId")
                and "NetworkConstruct" not in dependency["resourceTypeId"]
                and "NetworkFunction" not in dependency["resourceTypeId"]
            ):
                return_value.append(dependency)

        self.logger.debug("Returning %s associated RA resources." % len(return_value))
        return return_value

    def get_all_associated_dependents(self, resource_id):
        """returns the list of non-RA resources associated with the passed in resource ID

        Goal is to return a list of resources that are part of the "built-in" domain.

        """
        return_value = []
        for dep in self.bpo.resources.get_dependents(resource_id):
            if not dep.get("providerResourceId") and dep["id"] in self.all_dependencies_ids:
                return_value.append(dep)

        self.logger.debug("Returning %s associated NS resources." % len(return_value))
        return return_value

    def create_and_delete_segment_resource(
        self, parent_resource_id, segment_product_id, segment_properties, circuit_id, wait_active=True
    ):
        """
        function which creates the mef segment resource
        and deletes it.
        """

        segment_res_obj = {
            "label": circuit_id + segment_properties["operation"],
            "productId": segment_product_id,
            "properties": segment_properties,
        }

        segment_res = self.bpo.resources.create(parent_resource_id, segment_res_obj, wait_active=wait_active)

        self.bpo.relationships.delete_relationships(segment_res.resource_id)
        self.bpo.resources.delete(segment_res.resource_id)
        self.await_termination_collect_timing(segment_res.resource_id, "mef.resourceTypes.LegatoSegment", True)

    def get_cvlans_for_uni_ep(self, circuit_details, interface_uuid):
        """
        returns the cvlan list for a particular
        UNI port
        """
        if "properties" in circuit_details.keys():
            service_dict = circuit_details["properties"]["service"]
        else:
            service_dict = circuit_details["service"]

        return_value = []

        for service in service_dict:
            evc = service["data"]["evc"][0]
            for ep in evc["endPoints"]:
                if ep["uniId"].upper() == interface_uuid.upper():
                    return_value = ep.get("ceVlans", [])
                    break

        return return_value

    def get_network_function_for_spoke_device(self, device, no_fail=False):
        """
        Finds the network function using fqdn of device
        :param device: device details from spoke list
        :return: device's network function resource
        """
        self.logger.info("Getting network function for spoke device %s" % device["Host Name"])
        host = device["FQDN"]
        device_nf = self.get_network_function_by_host(host)
        if device_nf is None:
            host = device["Management IP"]
            device_nf = self.get_network_function_by_host(host)
        if device_nf is None:
            if device["Role"] != "CPE":
                msg = self.error_formatter(
                    self.SYSTEM_ERROR_TYPE,
                    "Missing Network Function",
                    f"device: {device['Host Name']} fqdn: {device['FQDN']} mgmt IP: {device['Management IP']}",
                )
                self.categorized_error = msg
                self.exit_error(msg)
        else:
            if device_nf["orchState"] != "active":
                msg = self.error_formatter(
                    self.CONNECTIVITY_ERROR_TYPE,
                    "Inactive State",
                    f"device: {host} orchState: {device_nf['orchState']}",
                )
                self.categorized_error = msg
                self.exit_error(msg)

            return device_nf

    def get_ra_plugin_product(self, rtype, package):
        """returns the RA Plugin product for the specific resource type and package

        Returns None if none is found

        :param rtype: Resource Type ID (tosca.resourceTypes.NetworkElement)
        :param package: RA Package Name (radra, bpadvara, etc)
        :type rtype: str
        :type package: str
        :return: url for device
        :rtype: str
        """
        cutthrough_product = None
        try:
            products = self.bpo.market.get_products_by_resource_type(self.BUILT_IN_RESOURCE_PLUG_IN_TYPE)
            for product in products:
                template = product["providerData"]["template"]
                if template.startswith(package + ".") and template.endswith("." + rtype.split(".")[-1]):
                    cutthrough_product = product["id"]
                    break
        except Exception as e:
            self.logger.warning("Error getting package " + self.BUILT_IN_RESOURCE_PLUG_IN_TYPE)
            self.logger.exception(e)

        return cutthrough_product

    def get_mef_plugin_product(self, package):
        """returns the RA mef Plugin product for the specific package

        Returns None if none is found

        :param package: RA Package Name (radra, bpadvara, etc)
        :type package: str
        :return: product_id
        :rtype: str
        """
        mef_products = self.bpo.products.get_by_domain_and_type(
            self.BUILT_IN_DOMAIN_ID, "mef.resourceTypes.LegatoSegment"
        )
        product_id = None
        for product in mef_products:
            if product["providerData"]["template"].startswith(package + "."):
                product_id = product["id"]

        if not product_id:
            msg = self.error_formatter(self.SYSTEM_ERROR_TYPE, "Missing MEF Service Template", f"package: {package}")
            self.categorized_error = msg
            self.exit_error(msg)

        return product_id

    def get_fia_service_object_from_details(self, pe_details, circuit_details):
        """
        generates FIA TPE Object from  PE Details

        :param pe_details: PE details generated by create_device_dict function
        :pe_details type: dict

        :param circuit_details: circuit details resource
        :pe_details type: dict

        :return_value TPE object
        :rtype dict
        """

        fia_optional_keys = [
            "nextIpv4Hop",
            "nextIpv6Hop",
            "asn",
            "firewallFilters",
            "ipv4ArpPolicer",
            "wanIpv4Address",
            "wanIpv6Address",
            "lanIpv4Addresses",
            "lanIpv6Addresses",
        ]

        # For an FIA service both evc and fia would have only one element exactly
        evc_data = circuit_details["properties"]["service"][0]["data"]["evc"][0]
        type_2_endpoint = evc_data["endPoints"][0]
        fia_data = circuit_details["properties"]["service"][0]["data"]["fia"][0]
        fia_ep = fia_data["endPoints"][0]
        port_name = self.get_node_port_name_from_uuid(fia_ep["uniId"])[1]
        nf_resource = self.get_network_function_by_host_or_ip(pe_details["FQDN"], pe_details["Management IP"])
        is_type_2 = True if evc_data["endPoints"][0].get("type2") else False

        self.logger.info("NF Resource for FIA Service %s" % nf_resource)

        properties = {
            "pe_device_rid": nf_resource["id"],
            "network_construct_id": self.get_network_construct_id_by_device_id(nf_resource["id"]),
            "port_name": port_name,
            "port_id": self.get_port_id_from_port_name_and_device_id_retry(port_name, nf_resource["id"]),
            "interface_userLabel": self.get_port_description(circuit_details, fia_ep["uniId"]),
            "cos": self.COS_LOOKUP[pe_details["Role"]][evc_data["cosNames"][0]["name"]],
            "vlan": str(evc_data["sVlan"]),
            "fia_type": fia_data["type"],
            "userLabel": self.get_service_userLabel(circuit_details),
            "port_role": self.get_port_role(circuit_details, fia_ep["uniId"]),
            "type_2": False,
        }

        # Udate properties with Type II info if needed
        if is_type_2:
            properties["type_2"] = True
            properties["unit"] = str(type_2_endpoint["unit"])
            properties["outer_vlan"] = str(type_2_endpoint["outerVlan"])
            properties["inner_vlan"] = str(type_2_endpoint["innerVlan"])
            del properties["vlan"]

        for key in fia_optional_keys:
            if key in fia_ep.keys():
                properties[key] = fia_ep[key]

        # currently only PE or PE-CPE is supported and hence ingress policing on PE
        # would be required only when its a PE only service
        # when AGG and MTUs are supported, need to introduce logic to find
        # last node for ingress policing
        client_neighbor = self.get_node_client_neighbor(circuit_details, pe_details["Host Name"])
        last_device = self.get_last_device(circuit_details, pe_details["Host Name"])
        last_device_vendor = self.get_node_vendor(circuit_details, last_device) if str(last_device) != "None" else None
        if "evc-ingress-bwp" in evc_data.keys() and (
            client_neighbor == "None"
            or (last_device and self.COMMON_TYPE_LOOKUP[last_device_vendor].get("PE_BW_DIR") == "BOTH")
        ):
            properties["in_bwProfileFlowParameters"] = evc_data["evc-ingress-bwp"]
        if "evc-egress-bwp" in evc_data.keys():
            properties["e_bwProfileFlowParameters"] = evc_data["evc-egress-bwp"]

        return_value = {"label": circuit_details["properties"]["circuit_id"] + ".fia_service", "properties": properties}
        return return_value

    def get_plugin_product(self, package, resource_type):
        """
        returns the RA Plugin product for the specific package

        Returns None if none is found

        :param package: RA Package Name (radra, bpadvara, etc)
        :type package: str
        :return: product_id
        :rtype: str
        """
        products = self.bpo.products.get_by_domain_and_type(self.BUILT_IN_DOMAIN_ID, resource_type)
        self.logger.info("Products from get_plugin_product: {}".format(products))
        product_id = None
        for product in products:
            if product["providerData"]["template"].startswith(package + "."):
                product_id = product["id"]

        return product_id

    def get_network_function_connection_type(self, network_function_resource):
        """Intakes network function resource, returns str: cli or netconf"""
        return list(network_function_resource["properties"]["authentication"].keys())[0]

    def get_session_profile_by_type(self, device_vendor, domain_id, profile_type):
        """returns the netconf session profile associated with the domain

        :param device_vendor: Name of device vendor to match the CommonPlan.COMMON_TYPE_LOOKUP
        :param domain_id: UUID of the domain
        :param profile_type: Type of session profile (netconf, cli)
        :type device_vendor: str
        :type domain_id: str

        :return: Session Profile resource
        :rtype: dict
        """
        domain_lookup = self.COMMON_TYPE_LOOKUP.get(device_vendor)

        session_profiles = self.get_resource_by_type_and_domain(domain_lookup["SESSION_PROFILE_TYPE"], domain_id)

        if len(session_profiles) == 0:
            msg = self.error_formatter(
                self.SYSTEM_ERROR_TYPE,
                "Missing Session Profile",
                f"vendor: {device_vendor} session profile type: {domain_lookup['SESSION_PROFILE_TYPE']} \
                requested by: get_session_profile_by_type",
            )
            self.categorized_error = msg
            raise Exception(msg)

        return_value = None

        for profile in session_profiles:
            if profile_type in profile["properties"]["connection"]:
                return_value = profile
                break

        self.logger.info("Returning session profile: " + str(return_value))

        return return_value

    def get_affected_devices_from_circuit(self, resource_id, circuit_details, operation):
        if operation == "CPE_ACTIVATION":
            return self.get_affected_devices_cpe_activation(resource_id, circuit_details)

        affected_devices = self.get_all_circuit_devices(circuit_details)
        self.logger.debug(f"Affected Devices: {affected_devices}")

        return affected_devices

    def get_affected_devices_cpe_activation(self, resource_id, circuit_details):
        try:
            cpe_activator_res = self.bpo.resources.get_dependent_by_type(resource_id, self.BUILT_IN_CPE_ACTIVATOR_TYPE)

        except Exception as ex:
            self.logger.warn(str(ex))
            self.logger.info("Not Called as part of CPE Activator")
            msg = self.error_formatter(
                self.SYSTEM_ERROR_TYPE,
                "CPE Activator",
                f"calling resource: {resource_id} requested resource: {self.BUILT_IN_CPE_ACTIVATOR_TYPE}",
            )
            self.categorized_error = msg
            raise Exception(msg)

        affected_devices = self.get_cpe_activation_devices_to_update(cpe_activator_res, circuit_details)
        self.logger.debug("Affected Devices for CPE activation are: " + str(affected_devices))
        return affected_devices

    def get_cpe_activation_devices_to_update(self, cpe_activator_res, circuit_details):
        """
        Fetches the Affected devices in case
        of CPE Activation
        """

        return_value = []
        site = cpe_activator_res["properties"]["site"]
        port = cpe_activator_res["properties"]["port"].upper()

        spoke_list = self.create_device_dict_from_circuit_details(circuit_details)

        for spoke in spoke_list:
            for device_info in spoke.values():
                if not device_info["Client Neighbor"] == "None":
                    role = spoke[device_info["Client Neighbor"]].get("Role")
                if device_info["Client Interface"] == port and role == "CPE":
                    device_spoke = self.get_topology_spoke_for_host_port(site, circuit_details, port)
                    spoke_list = self.create_device_dict_from_circuit_details(device_spoke)
                    device_list = self.get_device_list(spoke_list)
                    return_value = device_list
                    break

        self.logger.debug("Returning affected devices: " + str(return_value))
        return return_value

    def is_service_mapper_remediation(self, service_mapper_resource):
        if not service_mapper_resource:
            return False
        else:
            return (
                True
                if service_mapper_resource["properties"]["remediation_flag"]
                and "remediation_attempted" not in service_mapper_resource["properties"]
                else False
            )

    def get_tids_from_circuit_details(self, circuit_details, role=""):
        """
        Finds all device in circuit and returns list of TID(s) optional role filter
        Parameters:
            circuit_details (dict): Circuit details
            role (str): Role of device to filter ("CPE", "PE")
        Returns:
            list: List of TID(s)
        """
        device_tids = []
        devices = self.create_device_dict_from_circuit_details(circuit_details)
        if role:
            self.logger.info("Filtering TIDs by Role: {}".format(role))
        for device in devices:
            for tid in device:
                if role and device[tid]["Role"] == role:
                    device_tids.append(tid)
                else:
                    device_tids.append(tid)
        self.logger.info("Device TIDs: {}".format(device_tids))

        return device_tids

    def get_tpe_id(self, device_id, circuit_id, await_active=False):
        """
        :param device_id: str resource id of network function
        :param circuit_id: str circuit id
        :returntype: str | tpe id or None if none found
        """
        device_nc = self.bpo.resources.get_dependent_by_type(device_id, "tosca.resourceTypes.NetworkConstruct")

        device_tpes = self.get_dependents(
            device_nc["id"], resource_type="tosca.resourceTypes.TPE", await_active=await_active
        )
        self.logger.info("TPEs found: {}".format(device_tpes))
        uni_tpe = [
            tpe["id"]
            for tpe in [
                tpe
                for tpe in device_tpes
                if "userLabel" in tpe["properties"]["data"]["attributes"].keys()
                if circuit_id.upper() in tpe["properties"]["data"]["attributes"]["userLabel"].upper()
            ]
            if "owningServerTpe" in tpe["properties"]["data"]["relationships"].keys()
        ]
        if uni_tpe:
            return uni_tpe[0]
        else:
            return

    def get_fre_id(self, device_id, circuit_id):
        """
        Finds the associated fre given the device id and circuit id
        Returns resource id of first fre found or none if none found
        """
        uni_tpe = self.get_tpe_id(device_id, circuit_id, await_active=True)
        if not uni_tpe:
            self.logger.error("Unable to find TPE, no FRE dependent will exist.")
            return
        device_fres = self.get_dependents(uni_tpe, resource_type="tosca.resourceTypes.FRE", await_active=True)
        device_fre_id = device_fres[0]["id"] if device_fres else None
        self.logger.info("FRE ID: {}".format(device_fre_id))
        return device_fre_id

    def get_tpe_by_name(self, device_id, circuit_id, name):
        """
        Finds the associated tpe given the device and circuit id and return based on NativeName of the TPE
        Must give specific nativeName to be lowered and used.
        EG: eth_port-1-1-1-5
        """
        device_nc = self.bpo.resources.get_dependent_by_type(device_id, "tosca.resourceTypes.NetworkConstruct")

        device_tpes = self.get_dependents(device_nc["id"], resource_type="tosca.resourceTypes.TPE")
        self.logger.info("CPE TPES from Network Construct:  {}".format(device_tpes))

        found = False
        for tpe in device_tpes:
            if tpe["properties"]["data"]["attributes"]["nativeName"].lower() == name.lower():
                self.logger.info("TPE with nativeName {} found. TPE:{}".format(name, tpe))
                found = True
                return tpe
            else:
                pass

        if not found:
            self.logger.info("Couldn't find TPE with given nativeName {}".format(name))

    def get_legato_and_build_relationship_to_fre(self, network_service_id, fre):
        legato_id = None
        self.logger.info("FRE_HERE: {}".format(fre))
        design_fre = self.bpo.resources.get(fre)
        network_function_id = design_fre["properties"]["device"].split("_")[-1]

        try:
            legato_id = self.bpo.resources.get_dependency_by_type(
                network_service_id, self.BUILT_IN_MEF_PRODUCTION_SERVICE_TYPE
            )["id"]

        except RuntimeError:
            self.logger.info("There is no Legato Service for this circuit")

        if legato_id:
            legato_builder = self.bpo.resources.get_dependencies_by_type(legato_id, "mef.resourceTypes.LegatoBuilder")[
                0
            ]

            legato_segment = self.bpo.resources.get_dependencies(legato_builder["id"])

            self.logger.info("Legato service id: {}".format(legato_id))
            self.logger.info("Legato Builder: {}".format(legato_builder))
            self.logger.info("Legato Segment: {}".format(legato_segment))

            legato_segment_id = [
                legato["id"]
                for legato in legato_segment
                if legato["properties"]["segment_info"]["endpoints"][0]["node_id"] == network_function_id
            ]

            legato_segment_2 = self.bpo.resources.get_dependencies(legato_segment_id[0])[0]["id"]

            self.bpo.market.add_relationship(legato_segment_2, fre)

    def resource_remodeling_tpe(
        self,
        network_tpe_resource,
        design_tpe_resource,
        mapper_resource_id,
        device,
        circuit_details=None,
        standalone=False,
    ):
        """
        Creating a list of tupel key value pairs from the network_tpe_resource design_tpe_resource variables
        mapper_resource_id and device variables used for patching
        """
        network_tpe_resource = (
            network_tpe_resource["data"]["attributes"]
            if standalone
            else network_tpe_resource["properties"]["data"]["attributes"]
        )
        design_tpe_resource = (
            design_tpe_resource["data"]["attributes"]
            if standalone
            else design_tpe_resource["properties"]["data"]["attributes"]
        )

        self.logger.info("TPE from network data: {}".format(network_tpe_resource))
        self.logger.info("TPE from design data: {}".format(design_tpe_resource))
        resources = [network_tpe_resource, design_tpe_resource]
        network_tupel_compare_list = []
        design_tupel_compare_list = []

        # extracting 1st level values by excluding the keys total capacity and layerTerminations
        count = 0
        for resource in resources:
            for items in resource.items():
                if items[0] == "totalCapacity" or items[0] == "layerTerminations":
                    pass
                else:
                    if count == 0:
                        network_tupel_compare_list.append(items)
                    else:
                        design_tupel_compare_list.append(items)
            count += 1

        # extracting values in the totalCapacity key for both resources
        if design_tpe_resource.get("totalCapacity"):
            count = 0
            for index in design_tpe_resource["totalCapacity"]:
                for key in index:
                    if key == "capacitySize":
                        values = design_tpe_resource["totalCapacity"][count][key].items()
                        for value in values:
                            design_tupel_compare_list.append(value)
                count += 1

        if network_tpe_resource.get("totalCapacity"):
            count = 0
            for index in network_tpe_resource["totalCapacity"]:
                for key in index:
                    if key == "capacitySize":
                        values = network_tpe_resource["totalCapacity"][count][key].items()
                        for value in values:
                            network_tupel_compare_list.append(value)
                count += 1

        # extracting values in layerTerminations key for both resources
        if design_tpe_resource.get("layerTerminations"):
            count = 0
            for index in design_tpe_resource["layerTerminations"]:
                for key in index:
                    if key == "additionalAttributes":
                        self.logger.info(
                            "resource 2 aa: {}".format(design_tpe_resource["layerTerminations"][count][key].items())
                        )
                        values = design_tpe_resource["layerTerminations"][count][key].items()
                        for value in values:
                            if "l2cpProfile" not in value:
                                design_tupel_compare_list.append(value)
                count += 1
        if network_tpe_resource.get("layerTerminations"):
            count = 0
            for index in network_tpe_resource["layerTerminations"]:
                for key in index:
                    if key == "additionalAttributes":
                        self.logger.info(
                            "resource 1 aa: {}".format(network_tpe_resource["layerTerminations"][count][key].items())
                        )
                        values = network_tpe_resource["layerTerminations"][count][key].items()
                        for value in values:
                            if "l2cpProfile" not in value:
                                network_tupel_compare_list.append(value)
                count += 1
        self.resource_compare_tpe(
            network_tupel_compare_list, design_tupel_compare_list, mapper_resource_id, device, circuit_details
        )

    def check_duplex_against_bw(self, network_tupel_compare_list, circuit_details):
        admin_speed = 0
        for tupel in network_tupel_compare_list:
            if tupel[0] == "adminSpeed":
                admin_speed = int(tupel[1])
                break
        bandwidth = circuit_details["properties"]["service"][0]["data"]["evc"][0]["evc-egress-bwp"]
        bw_in_kbps = self.get_bandwidth_in_kbps(bandwidth)
        if admin_speed < bw_in_kbps:
            msg = self.error_formatter(
                self.INCORRECT_DATA_ERROR_TYPE,
                "Unsupported AdminSpeed for Bandwidth",
                f"admin speed: {admin_speed} bandwidth: {bw_in_kbps}",
                system=self.CIRCUIT_DETAILS_DATABASE,
            )
            self.categorized_error = msg
            self.exit_error(msg)
        self.logger.info(f"AdminSpeed: {admin_speed},  Bandwidth: {bw_in_kbps}")

    def resource_compare_tpe(
        self, network_tupel_compare_list, design_tupel_compare_list, mapper_resource_id, device, circuit_details=None
    ):
        """
        Comparing the two tupel lists againast each other for any pairing not found in the other
        """
        # comparing all the values found and appending them to lists
        network_diff_list = []
        design_diff_list = []
        network_tupel_compare_list, design_tupel_compare_list = self.data_normalization(
            network_tupel_compare_list, design_tupel_compare_list
        )
        self.logger.info("network_tupel_compare_list: {}".format(network_tupel_compare_list))
        self.logger.info("design_tupel_compare_list: {}".format(design_tupel_compare_list))
        self.logger.info("Device: {}".format(device))
        match = False
        for tupel in design_tupel_compare_list:
            if tupel not in network_tupel_compare_list:
                if tupel[0] == "userLabel":
                    userlabel = ""
                    count = 0
                    for letter in tupel[1]:
                        if count < 164:
                            userlabel += letter
                            count += 1
                    userlabel_tupel = ("userLabel", userlabel)
                    if userlabel_tupel not in network_tupel_compare_list:
                        for tupel in network_tupel_compare_list:
                            if tupel[0] == "userLabel":
                                if userlabel not in tupel[1]:
                                    pass
                                else:
                                    match = True
                    if not match:
                        design_diff_list.append(userlabel_tupel)
                else:
                    self.logger.info("props: {}".format(tupel))
                    design_diff_list.append(tupel)

        match = False
        for tupel in network_tupel_compare_list:
            if tupel not in design_tupel_compare_list:
                if tupel[0] == "userLabel":
                    userlabel = ""
                    count = 0
                    for letter in tupel[1]:
                        if count < 164:
                            userlabel += letter
                            count += 1
                    userlabel_tupel = ("userLabel", userlabel)
                    if userlabel_tupel not in design_tupel_compare_list:
                        for tupel in design_tupel_compare_list:
                            if tupel[0] == "userLabel":
                                if userlabel not in tupel[1]:
                                    pass
                                else:
                                    match = True
                    if not match:
                        network_diff_list.append(userlabel_tupel)
                else:
                    self.logger.info("props: {}".format(tupel))
                    network_diff_list.append(tupel)

        # converting the tuples in the list to dictionaries
        network_diff_dict, design_diff_dict = self.list_to_dict(network_diff_list, design_diff_list)

        # checking if the dictionaries are not empty and then performing a patch with the differences found
        if design_diff_dict or network_diff_dict:
            self.patch_service_mapper_diffs_tpe(mapper_resource_id, device, network_diff_dict, design_diff_dict)
            self.logger.info(
                "Mapper TPE design resource_diff: {} \n Mapper TPE network resource diff {}".format(
                    design_diff_dict, network_diff_dict
                )
            )
        else:
            self.logger.info("No TPE differences found.")

    def resource_compare_tpe_pro(self, ntpe, dtpe, mapper_resource_id, device, service_type):
        """
        This function will take 2 tpe objects as input and compare values relevant to adva116pro/120pro compliance
        Afterwards, it calls a different module to post said differences found to the ServiceMapper object
        """
        network_diff_dict = {}
        design_diff_dict = {}
        # match = False

        # Compare displayAlias (description) and add to both if different.
        if (
            ntpe["properties"]["data"]["attributes"]["userLabel"]
            != dtpe["properties"]["data"]["attributes"]["userLabel"]
        ):
            network_diff_dict["userLabel"] = ntpe["properties"]["data"]["attributes"]["userLabel"]
            design_diff_dict["userLabel"] = dtpe["properties"]["data"]["attributes"]["userLabel"]

        # dictionary values for matching SF values provided by SEnSE to 116pro/120pro port settings
        """
        mediaType = {"LC": "fiber", "RJ45": "copper-sfp"}
        duplex = {
            "Auto Auto": "auto-speed-detect",
            "1000 Autonegotiate": "auto-1000-full",
            "1000 Full Duplex": "1000-full",
            "10 Full Duplex": "fixed-10g-full",
        }
        """

        self.logger.info(
            "here is mediatype: {} \n and portSpeed: {}".format(
                ntpe["properties"]["data"]["attributes"]["mediaType"],
                ntpe["properties"]["data"]["attributes"]["configSpeed"],
            )
        )

        # getting mapper resource to index into the data sent by SEnSE
        mapper_device_properties = self.bpo.resources.get(mapper_resource_id)["properties"].get(
            "device_properties", None
        )
        if service_type != "VOICE":
            if mapper_device_properties:
                mapper_device_props = mapper_device_properties.get(device, None)
                if mapper_device_props:
                    mapper_media_type = mapper_device_props.get("MediaType", "")
                    # mapper_portSpeed = mapper_device_props.get("Duplex", None)
                    # Comparing Physical Attributes. only Media Type for now until Exfo can send SEnSE Duplex
                    # For now Network Duplex value will simply be handed back.
                    if "fiber" in ntpe["properties"]["data"]["attributes"]["mediaType"]:
                        ntpe["properties"]["data"]["attributes"]["mediaType"] = "LC"
                    if "copper" in ntpe["properties"]["data"]["attributes"]["mediaType"]:
                        ntpe["properties"]["data"]["attributes"]["mediaType"] = "RJ-45"
                    if ntpe["properties"]["data"]["attributes"]["mediaType"] not in mapper_media_type:
                        network_diff_dict["MediaType"] = ntpe["properties"]["data"]["attributes"]["mediaType"]
                        design_diff_dict["MediaType"] = mapper_media_type
            # network_diff_dict["Duplex"] = ntpe["properties"]["data"]["attributes"]["configSpeed"]
            # design_diff_dict["Duplex"] = "NOT AVAILABLE"

        # if ntpe["properties"]["data"]["attributes"][]
        adminState = ntpe["properties"]["data"]["attributes"]["state"].upper()
        if adminState != "IS":
            network_diff_dict["portStatus"] = ntpe["properties"]["data"]["attributes"]["state"].upper()
            design_diff_dict["portStatus"] = dtpe["properties"]["data"]["attributes"]["state"].upper()

        # checking if the dictionarys are not empty and then performing a patch with the differences found
        if network_diff_dict:
            network_diff_dict["Port"], design_diff_dict["Port"] = (
                ntpe["properties"]["data"]["id"][4:-4],
                dtpe["properties"]["data"]["id"][4:-4],
            )
            self.patch_service_mapper_diffs_tpe(mapper_resource_id, device, network_diff_dict, design_diff_dict)
            self.logger.info(
                "Mapper 116/120pro TPE design resource_diff: {} \n Mapper TPE network resource diff {}".format(
                    design_diff_dict, network_diff_dict
                )
            )
        else:
            self.logger.info("No TPE differences found.")

    def resource_compare_tpe_fp_pro(self, ntpe, dtpe, mapper_resource_id, device):
        """
        Comparing the two tupel flowpoint TPEs againast each other for given set of key:value pairs to match
        returns 2 lists of items not found in the other.
        """
        # comparing all the values found and appending them to lists
        fp_id = ntpe["data"]["id"]
        network_diff_dict, design_diff_dict = {"flowpoint name": fp_id}, {"flowpoint name": fp_id}
        self.logger.info("network_fp_tpe: {}".format(ntpe))
        self.logger.info("design_fp_tpe: {}".format(dtpe))

        # comparing set vlan-id
        if (
            ntpe["data"]["attributes"]["flexibleEncapsulation"]["localTrafficDefaultEncaps"]["outerTag"]["vlanId"]
            != dtpe["data"]["attributes"]["flexibleEncapsulation"]["localTrafficDefaultEncaps"]["outerTag"]["vlanId"]
        ):
            network_diff_dict["vlan"] = ntpe["data"]["attributes"]["flexibleEncapsulation"][
                "localTrafficDefaultEncaps"
            ]["outerTag"]["vlanId"]
            design_diff_dict["vlan"] = dtpe["data"]["attributes"]["flexibleEncapsulation"]["localTrafficDefaultEncaps"][
                "outerTag"
            ]["vlanId"]
        # comparing tag behavior
        if (
            ntpe["data"]["attributes"]["flexibleEncapsulation"]["localTrafficDefaultEncaps"]["outerTag"]["tagType"]
            != dtpe["data"]["attributes"]["flexibleEncapsulation"]["localTrafficDefaultEncaps"]["outerTag"]["tagType"]
        ):
            network_diff_dict["tagType"] = ntpe["data"]["attributes"]["flexibleEncapsulation"][
                "localTrafficDefaultEncaps"
            ]["outerTag"]["tagType"]
            design_diff_dict["tagType"] = dtpe["data"]["attributes"]["flexibleEncapsulation"][
                "localTrafficDefaultEncaps"
            ]["outerTag"]["tagType"]
        # comparing name
        if ntpe["data"]["attributes"]["displayAlias"] != dtpe["data"]["attributes"]["displayAlias"]:
            network_diff_dict["displayAlias"] = ntpe["data"]["attributes"]["displayAlias"]
            design_diff_dict["displayAlias"] = dtpe["data"]["attributes"]["displayAlias"]
        # comparing vlan members
        if ntpe["data"]["attributes"]["additionalAttributes"]["vlan_members"] != dtpe["data"]["attributes"][
            "additionalAttributes"
        ]["vlan_members"] and ntpe["data"]["attributes"]["additionalAttributes"]["vlan_members"] != [""]:
            network_diff_dict["vlan_members"] = ntpe["data"]["attributes"]["additionalAttributes"]["vlan_members"]
            design_diff_dict["vlan_members"] = dtpe["data"]["attributes"]["additionalAttributes"]["vlan_members"]
        # comparing p-bits
        if (
            ntpe["data"]["attributes"]["additionalAttributes"]["c_tag_pbit"]
            != dtpe["data"]["attributes"]["additionalAttributes"]["c_tag_pbit"]
        ):
            network_diff_dict["c_tag_p-bit"] = ntpe["data"]["attributes"]["additionalAttributes"]["c_tag_pbit"]
            design_diff_dict["c_tag_p-bit"] = dtpe["data"]["attributes"]["additionalAttributes"]["c_tag_pbit"]
        # comparing policer values
        npolicer = ntpe["data"]["attributes"]["additionalAttributes"]["policerProfile"]
        remove_keys = ["max_cir", "max_eir", "policer_name", "policer_id"]
        [npolicer.pop(key) for key in remove_keys]
        nbw_dict, dbw_dict = {}, {}
        dpolicer = dtpe["data"]["attributes"]["additionalAttributes"]["policerProfile"]

        for key in npolicer:
            if npolicer[key] != dpolicer[key]:
                nbw_dict[key] = npolicer[key]
                dbw_dict[key] = dpolicer[key]

        # TODO: remove the :: split version before merging into develop
        network_bw_dict, design_bw_dict = {ntpe["data"]["attributes"]["nativeName"]: nbw_dict}, {
            dtpe["data"]["id"].rsplit("_")[1].lower(): dbw_dict
        }
        self.logger.info("network bw dict: {}, design bw dict: {}".format(network_bw_dict, design_bw_dict))

        if len(nbw_dict) > 0 or len(dbw_dict) > 0:
            self.patch_service_mapper_diffs_policer(mapper_resource_id, device, network_bw_dict, design_bw_dict)

        adminState = ntpe["data"]["attributes"]["state"].upper()
        if adminState != "IS":
            network_diff_dict["flowpoint"] = "not enabled"

        self.logger.info("network_diff_list: {}".format(network_diff_dict))
        self.logger.info("design_diff_list: {}".format(design_diff_dict))

        # checking if the dictionarys are not empty and then performing a patch with the differences found
        if len(network_diff_dict) > 1 or len(design_diff_dict) > 1:
            self.patch_service_mapper_diffs_fre(mapper_resource_id, network_diff_dict, design_diff_dict, device)
            self.logger.info(
                "Mapper TPE design resource_diff: {} \n Mapper TPE network resource diff {}".format(
                    design_diff_dict, network_diff_dict
                )
            )
        else:
            self.logger.info("No TPE differences found.")

    def is_empty(self, iterable):
        return len(iterable) == 0

    def resource_comparison_pe(
        self, network_fre, design_fre, design_diff_holder=None, network_diff_holder=None, list_name: str = None
    ):
        """This function is used to compare the network and design resources for a FRE and return the differences
        Params:
            network_fre (dict): actual network fre data
            design_fre (dict): modeled in granite fre data
            design_diff_holder (dict, optional): DO NOT CALL DIRECTLY this is a holder var for recursive passing. Defaults to {}.
            network_diff_holder (dict, optional): DO NOT CALL DIRECTLY this is a holder var for recursive passing. Defaults to {}.
            list_name (str, optional): DO NOT CALL DIRECTLY this is a holder var for recursive passing. Defaults to None.

        Returns:
            design_diff (dict): differences in (key:value) for design data this will only exist if diff is found
            network_diff (dict): differences in (key:value) for network data this will only exist if diff is found
        """
        if design_diff_holder is None:
            design_diff_holder = {}
        if network_diff_holder is None:
            network_diff_holder = {}
        design_diff = design_diff_holder
        network_diff = network_diff_holder
        if isinstance(network_fre, str):
            if design_fre != network_fre:
                # updates the differences dict with the key and value of the difference
                design_diff.update({list_name: design_fre})
                network_diff.update({list_name: network_fre})
        if isinstance(network_fre, dict):
            for key, value in design_fre.items():
                if key not in network_fre:
                    self.logger.info("{} on MODEL but not NETWORK FIX Structure".format(key))
                elif isinstance(value, dict):
                    # gets the inner dict and calls the function again
                    self.resource_comparison_pe(network_fre[key], value, design_diff, network_diff)
                elif isinstance(value, list):
                    for index, element in enumerate(value):
                        self.resource_comparison_pe(
                            network_fre[key][index],
                            value[index],
                            design_diff,
                            network_diff,
                            key,
                        )
                else:
                    if value != network_fre[key]:
                        # updates the differences dict with the key and value of the difference
                        design_diff.update({key: value})
                        network_diff.update({key: network_fre[key]})

        if network_diff.get("ipv6") and design_diff.get("ipv6"):
            net_ip = network_diff["ipv6"]
            design_ip = design_diff["ipv6"]
            net_ip = ipaddress.ip_address(net_ip.split("/")[0])
            design_ip = ipaddress.ip_address(design_ip.split("/")[0])
            if net_ip.exploded == design_ip.exploded:
                network_diff.pop("ipv6")
                design_diff.pop("ipv6")
        self.logger.info("final diffies:\ndesign: {}\nnetwork: {}".format(design_diff, network_diff))
        return network_diff, design_diff

    def compare_design_ips_to_network(self, design_ipv4_block, network_ipv4_block, mapper_resource_id, device):
        """iterates both design and network ipv4 blocks and shows the diff"""
        copy_1 = design_ipv4_block.copy()
        copy_2 = network_ipv4_block.copy()
        for ip_block in copy_1:
            if ip_block in copy_2:
                network_ipv4_block.remove(ip_block)
                design_ipv4_block.remove(ip_block)
        if design_ipv4_block or network_ipv4_block:
            self.patch_service_mapper_diffs_tpe(
                mapper_resource_id, device, {"ipv4": network_ipv4_block}, {"ipv4": design_ipv4_block}, is_core=True
            )
            self.logger.info(
                "Mapper IPV4 Design Diffs: {}\nMapper IPV4 Network Diffs: {}".format(
                    design_ipv4_block, network_ipv4_block
                )
            )
        else:
            self.logger.info("No IPV4 Differences Found.")

    def resource_comparison_fre(self, network_fre, design_fre, mapper_resource_id, device, vendor):
        """
        Creates and compares tupel lists created from network_fre and design_fre resource
        """
        self.logger.info(design_fre)
        self.logger.info(network_fre)
        ports = [0, 1]
        design_tupel_list_portindex_0 = []
        design_tupel_list_portindex_1 = []
        network_tupel_list_portindex_0 = []
        network_tupel_list_portindex_1 = []
        network_diff_list = []
        design_diff_list = []
        pop_values_114c = [
            "epAccessN2AFlowEbs",
            "epAccessN2AFlowCir",
            "epAccessN2AFlowCbs",
            "epAccessN2AFlowEir",
            "epAccessFlowPBBFramesControl",
            "epAccessFlowIVlan",
            "epAccessFlowPBBFramesControl",
            "PolicerType",
            "policerName",
        ]
        if vendor == "ADVA":
            ap_attributes = "additionalAttributes"
        elif vendor == "RAD":
            ap_attributes = "provisioningAttributes"

        resources = [design_fre, network_fre]

        if (
            network_fre["properties"]["included"][0]["attributes"][ap_attributes]["portId"]
            != design_fre["properties"]["included"][0]["attributes"][ap_attributes]["portId"]
        ):
            network_fre2 = network_fre["properties"]["included"][0]
            network_fre["properties"]["included"][0] = network_fre["properties"]["included"][1]
            network_fre["properties"]["included"][1] = network_fre2

        if vendor == "ADVA":
            for resource in resources:
                for port in ports:
                    for key in resource["properties"]["included"][port]["attributes"][ap_attributes].copy():
                        if key in pop_values_114c:
                            resource["properties"]["included"][port]["attributes"][ap_attributes].pop(key, None)

        for port in ports:
            for item in design_fre["properties"]["included"][port]["attributes"][ap_attributes].items():
                if port == 0:
                    design_tupel_list_portindex_0.append(item)
                elif port == 1:
                    design_tupel_list_portindex_1.append(item)

            for item in network_fre["properties"]["included"][port]["attributes"][ap_attributes].items():
                if port == 0:
                    network_tupel_list_portindex_0.append(item)
                elif port == 1:
                    network_tupel_list_portindex_1.append(item)

            if port == 0:
                design_tupel_list_portindex_0, network_tupel_list_portindex_0 = self.data_normalization(
                    design_tupel_list_portindex_0, network_tupel_list_portindex_0
                )
                design_tupel_list_portindex_1, network_tupel_list_portindex_1 = self.data_normalization(
                    design_tupel_list_portindex_1, network_tupel_list_portindex_1
                )
                self.logger.info("Network_Tupel_List_0 is {}".format(network_tupel_list_portindex_0))
                self.logger.info("Design_Tupel_List_0 is {}".format(design_tupel_list_portindex_0))
                self.logger.info("Network_Tupel_List_1 is {}".format(network_tupel_list_portindex_1))
                self.logger.info("Design_Tupel_List_1 is {}".format(design_tupel_list_portindex_1))

                # these two dictionaries will contain the classifier string data that will be sent to
                # classifier_diff_format_adjustment method
                network_classifier_diff_dict = {}
                design_classifier_diff_dict = {}

                for item in network_tupel_list_portindex_0:
                    if item not in design_tupel_list_portindex_0:
                        if "classifier" in item:
                            self.logger.info("Item is {}".format(item))
                            network_classifier_diff_dict["classifier"] = item[1]
                            classifier_vlan = self.classifier_diff_format_adjustment(network_classifier_diff_dict)
                            vlan_tupel = ["classifier_vlan", classifier_vlan]
                            network_diff_list.append(vlan_tupel)
                        else:
                            network_diff_list.append(item)
                for item in design_tupel_list_portindex_0:
                    if item not in network_tupel_list_portindex_0:
                        if "classifier" in item:
                            self.logger.info("Item is {}".format(item))
                            design_classifier_diff_dict["classifier"] = item[1]
                            classifier_vlan = self.classifier_diff_format_adjustment(design_classifier_diff_dict)
                            vlan_tupel = ["classifier_vlan", classifier_vlan]
                            design_diff_list.append(vlan_tupel)
                        else:
                            design_diff_list.append(item)
            elif port == 1:
                design_tupel_list_portindex_1, network_tupel_list_portindex_1 = self.data_normalization(
                    design_tupel_list_portindex_1, network_tupel_list_portindex_1
                )
                for item in network_tupel_list_portindex_1:
                    if item not in design_tupel_list_portindex_1:
                        if "classifier" in item:
                            self.logger.info("Item is {}".format(item))
                            network_classifier_diff_dict["classifier"] = item[1]
                            classifier_vlan = self.classifier_diff_format_adjustment(network_classifier_diff_dict)
                            vlan_tupel = ["classifier_vlan", classifier_vlan]
                            network_diff_list.append(vlan_tupel)
                        else:
                            network_diff_list.append(item)
                for item in design_tupel_list_portindex_1:
                    if item not in network_tupel_list_portindex_1:
                        if "classifier" in item:
                            self.logger.info("Item is {}".format(item))
                            design_classifier_diff_dict["classifier"] = item[1]
                            classifier_vlan = self.classifier_diff_format_adjustment(design_classifier_diff_dict)
                            vlan_tupel = ["classifier_vlan", classifier_vlan]
                            design_diff_list.append(vlan_tupel)
                        else:
                            design_diff_list.append(item)

        self.logger.info("FRE Design Diffs list: {}".format(design_diff_list))
        self.logger.info("FRE Network Diffs list: {}".format(network_diff_list))

        network_diff_dict, design_diff_dict = self.list_to_dict(network_diff_list, design_diff_list)

        if design_diff_dict or network_diff_dict:
            self.patch_service_mapper_diffs_fre(mapper_resource_id, network_diff_dict, design_diff_dict, device)
            self.logger.info(
                "Mapper FRE Design Diffs: {}\nMapper FRE Network Diffs: {}".format(design_diff_dict, network_diff_dict)
            )
        else:
            self.logger.info("No FRE Differences Found.")

    def classifier_diff_format_adjustment(self, either_dictionary):
        """This is a supporting method for the resource_comparison_fre method.
        It takes the classifier list item and formats it so that the vlan
        can be extracted for use in the comparison

        """
        classifier_vlan = either_dictionary["classifier"].strip("[]{}").split(",")[0]
        if "VLAN" not in classifier_vlan:
            classifier_vlan = either_dictionary["classifier"].strip("[]{}").split(",")[1]
        classifier_vlan = classifier_vlan.split(": ")[1]

        return classifier_vlan

    def get_interface_config(self, device_provider_resource_id, interface, vlan=None):
        ra = RaCutThrough()
        interface_parameter = "{}.{}".format(interface, vlan) if vlan else interface
        try:
            subinterface_config = ra.execute_ra_command_file(
                device_provider_resource_id, "get-interface-config.json", parameters={"name": interface_parameter}
            ).json()["result"]
        except Exception as ex:
            self.logger.info("No interface configuration found for {}. Exception: {}".format(interface_parameter, ex))
            subinterface_config = None
        return subinterface_config

    def get_route_config(self, device_provider_resource_id, ip_add):
        ra = RaCutThrough()
        try:
            route_config = ra.execute_ra_command_file(
                device_provider_resource_id, "seefa-cd-show-route.json", parameters={"ip_add": ip_add}
            ).json()["result"]
        except Exception as ex:
            self.logger.info("No route configuration found for {}. Exception: {}".format(ip_add, ex))
            route_config = None
        return route_config

    def get_routed_solution_next_hop(self, device_provider_resource_id, ipv4):
        """confirms ipv4 and gets next-hop"""

        self.ra = RaCutThrough()
        try:
            if isinstance(ipv4, list):
                all_found_circuit_static_routes = self.check_for_multiple_ip_routed(device_provider_resource_id, ipv4)
                static_route_config = self.append_multiple_ipblocks_to_list(all_found_circuit_static_routes)
                self.logger.info("static_route_config: {}.".format(static_route_config))
            else:
                static_route_config = self.ra.execute_ra_command_file(
                    device_provider_resource_id, "get-routed-solution-next-hop.json", parameters={"ipv4": ipv4}
                ).json()["result"]
                self.logger.info("default static_route_config: {}.".format(static_route_config))
        except Exception as ex:
            self.logger.info("No route configuration found for {}. Exception: {}".format(ipv4, ex))
            static_route_config = None
        return static_route_config

    def check_for_multiple_ip_routed(self, device_provider_resource_id, ipv4):
        """Checks for a list of multiple lanIpv4Addresses for a STATIC / routed solution. each ipblock gets passed to the racutthrough
        and all associated static routes that exist are appended to a list which is returned"""

        all_found_circuit_static_routes = []
        for ip_block in ipv4:
            static_route = self.ra.execute_ra_command_file(
                device_provider_resource_id, "get-routed-solution-next-hop.json", parameters={"ipv4": ip_block}
            ).json()["result"]
            if static_route["data"]["configuration"]:
                all_found_circuit_static_routes.append(
                    static_route["data"]["configuration"]["routing-options"]["static"]["route"]
                )
        self.logger.info("all_found_circuit_static_routes: {}.".format(all_found_circuit_static_routes))
        return all_found_circuit_static_routes

    def append_multiple_ipblocks_to_list(self, all_found_circuit_static_routes):
        """takes the list of routed and adds lists where needed for ipv4 and next-hop"""

        static_route_update_dictionary = {
            "data": {"configuration": {"routing-options": {"static": {"route": {"name": [], "next-hop": []}}}}}
        }
        data = static_route_update_dictionary["data"]["configuration"]["routing-options"]["static"]["route"]
        for ip_static_route in all_found_circuit_static_routes:
            if ip_static_route["name"] not in data["name"]:
                data["name"].append(ip_static_route["name"])
                if ip_static_route["next-hop"] not in data["next-hop"]:
                    data["next-hop"].append(ip_static_route["next-hop"])
        if not data["name"]:
            data["name"] = ["None"]
        if not data["next-hop"]:
            data["next-hop"] = ["None"]
        static_route_config = static_route_update_dictionary
        return static_route_config

    def get_cos_config(self, device_provider_resource_id, interface, vlan):
        ra = RaCutThrough()
        data_id = "{}.{}".format(interface, vlan)
        try:
            cos_config = ra.execute_ra_command_file(
                device_provider_resource_id, "get-cos-interfaces.json", parameters={"data.id": data_id}
            ).json()["result"]
        except Exception as ex:
            self.logger.info("No cos configuration found for {}. Exception: {}".format(data_id, ex))
            cos_config = None
        return cos_config

    def get_l2circuit_config(self, device_provider_resource_id, core_device, circuit_details, interface, vlan):
        ra = RaCutThrough()
        l2circuit_id = "{}:{}.{}".format(self.get_l2circuit_neighbor_ip(core_device, circuit_details), interface, vlan)
        try:
            l2circuit_config = ra.execute_ra_command_file(
                device_provider_resource_id, "get-l2-circuits-full.json", parameters={"name": l2circuit_id}
            ).json()["result"]
        except Exception as ex:
            self.logger.info("No l2circuit configuration found for {}. Exception: {}".format(l2circuit_id, ex))
            l2circuit_config = {}
        return l2circuit_config

    def get_vlan_config(self, device_provider_resource_id, vlan_name):
        """ra cutthrough get vlan config, use limited to EX and QFX devices"""
        ra = RaCutThrough()
        try:
            vlan_config = ra.execute_ra_command_file(
                device_provider_resource_id,
                "get-vlanidentifier-full.json",
                parameters={"name": vlan_name},
            ).json()["result"]
        except Exception as ex:
            self.logger.info("No vlan configuration found for {}. Exeption: {}".format(vlan_name, ex))
            vlan_config = None
        return vlan_config

    def get_network_config_data(
        self, circuit_details, service_type, device_tid, device_provider_resource_id, is_service_mapper=False
    ):
        vlan = circuit_details["properties"]["service"][0]["data"]["evc"][0]["sVlan"]
        vlan_name = service_type.upper() + str(vlan)
        core_device = self.get_devices_by_property_value(circuit_details, "Host Name", device_tid)[0]
        interface = core_device["Client Interface"].lower()
        port_role = self.get_port_role(circuit_details, device_tid + "-" + interface.upper())
        self.logger.info("Gathering configuration data from device: {}".format(device_tid))
        if core_device["Role"] == "PE":
            if port_role == "UNI":
                self.logger.info("Untagged handoff detected for device/interface: {}/{}".format(device_tid, interface))
                unit = 0
            else:
                unit = vlan
            network_config_data = {
                "interface": interface,
                "subinterface_config": self.get_interface_config(device_provider_resource_id, interface, unit),
                "cos_config": self.get_cos_config(device_provider_resource_id, interface, vlan),
                "l2circuit_config": {},
                "next_hop_ipv6": None,
                "next_hop_ipv4": None,
            }
            if service_type == "ELINE":
                network_config_data["l2circuit_config"] = self.get_l2circuit_config(
                    device_provider_resource_id, core_device, circuit_details, interface, vlan
                )
            else:  # FIA
                ipv6_next_hop, ipv4_next_hop = None, None
                try:
                    ipv6_next_hop = circuit_details["properties"]["service"][0]["data"]["fia"][0]["endPoints"][0][
                        "lanIpv6Addresses"
                    ][0]
                except Exception:
                    self.logger.info("Could not find next hop for device: {}".format(device_tid))
                if ipv6_next_hop:
                    try:
                        network_config_data["next_hop_ipv6"] = self.get_route_config(
                            device_provider_resource_id, ipv6_next_hop
                        )
                    except Exception:
                        self.logger.info("IPV6 next hop not found for device: {}".format(device_tid))
                try:
                    ipv4_next_hop = circuit_details["properties"]["service"][0]["data"]["fia"][0]["endPoints"][0][
                        "wanIpv4Address"
                    ]
                except Exception:
                    self.logger.info("Could not find next hop for device: {}".format(device_tid))
                if ipv4_next_hop:
                    try:
                        network_config_data["next_hop_ipv4"] = self.get_route_config(
                            device_provider_resource_id, ipv4_next_hop
                        )
                    except Exception:
                        self.logger.info("IPV4 next hop not found for device: {}".format(device_tid))
        else:  # AGG, MTU
            if "ACX" in core_device["Model"]:
                subinterface_config = self.get_interface_config(device_provider_resource_id, interface, vlan)
                if is_service_mapper and not subinterface_config:
                    msg = "Unable to return interface config for {} with interface {} and VLAN {}".format(
                        device_tid, interface, vlan
                    )
                    self.logger.error(msg)
                    self.exit_error(msg)
                subinterface_config = (
                    {}
                    if not subinterface_config
                    else subinterface_config["configuration"]["interfaces"][interface]["unit"][0]
                )
                network_config_data = {
                    "vlan-id": subinterface_config.get("vlan-id"),
                    "vlan_config": self.get_vlan_config(device_provider_resource_id, vlan_name),
                    "vlan_name": vlan_name,
                    "interface_config": subinterface_config,
                    "subinterface_description": subinterface_config.get("description"),
                    "unit": subinterface_config.get("name"),
                }
            else:
                vlan_config = self.get_vlan_config(device_provider_resource_id, vlan_name)
                if vlan_config == {} and "FIA" in vlan_name:
                    vlan_name = vlan_name.replace("FIA", "DIA")
                    vlan_config = self.get_vlan_config(device_provider_resource_id, vlan_name)
                network_config_data = {
                    "interface": interface,
                    "interface_config": self.get_interface_config(device_provider_resource_id, interface),
                    "vlan_config": vlan_config,
                    "vlan_name": vlan_name,
                }
        self.logger.info("network config data! {}".format(network_config_data))

        return network_config_data

    def get_ipv6_next_hop_data(self, ipv6_next_hop):
        if ipv6_next_hop:
            return (
                ipv6_next_hop.get("route-information", dict())
                .get("route-table", dict())
                .get("rt", dict())
                .get("rt-entry", dict())
                .get("nh", dict())
                .get("to")
            )
        else:
            return None

    def check_for_multiple_ip(self, network_config_data):
        """checks for a list of multiple ips and if found returns a list
        else returns the single item"""

        multiple_ip_block_list = []
        network_config_data_check = (
            network_config_data.get("subinterface_config", dict())
            .get("configuration", dict())
            .get("interfaces", dict())
            .get(network_config_data["interface"], dict())
            .get("unit", dict())[0]
            .get("family", dict())
            .get("inet", dict().get("address", dict()))
            .get("address", dict())
        )
        if isinstance(network_config_data_check, list):
            for item in network_config_data_check:
                for ip_block in item.values():
                    if ip_block:
                        multiple_ip_block_list.append(ip_block)
            multiple_ip_block_list.sort()
            return {"name": multiple_ip_block_list, "next-hop": None}
        else:
            return {"name": [network_config_data_check.get("name")], "next-hop": None}

    def get_ipv4_next_hop_data(self, network_config_data, device_provider_resource_id, ipv4):
        """gets the ipv4 and next hop from device"""
        if network_config_data["next_hop_ipv4"]:
            route = self.get_routed_solution_next_hop(device_provider_resource_id, ipv4)
            self.logger.info("route is: %s" % route)
            return (
                route.get("data", dict())
                .get("configuration", dict())
                .get("routing-options", dict())
                .get("static", dict())
                .get("route")
                if route.get("data").get("configuration")
                else None
            )
        else:
            return (
                self.check_for_multiple_ip(network_config_data)
                if network_config_data.get("subinterface_config")
                else None
            )

    def is_locally_switched(self, circuit_details):
        pe_devices = self.get_devices_by_property_value(circuit_details, "Role", "PE")
        locally_switched = False
        if self.a_side_pe_ip_matches_z_side_pe_ip(pe_devices):
            locally_switched = True
        return locally_switched

    def a_side_pe_ip_matches_z_side_pe_ip(self, pe_devices):
        return pe_devices[0]["Management IP"] == pe_devices[1]["Management IP"]

    def get_l2circuit_neighbor_ip(self, device, circuit_details):
        """Retreives l2circuit neighbor IP"""
        a_side_pe = circuit_details["properties"]["topology"][0]["data"]["node"][-1]
        a_side_pe_ip = self.get_node_property(circuit_details, a_side_pe["uuid"], "Management IP")
        z_side_pe = circuit_details["properties"]["topology"][-1]["data"]["node"][0]
        z_side_pe_ip = self.get_node_property(circuit_details, z_side_pe["uuid"], "Management IP")
        # if device is z side pe, neighbor is a side pe
        if device["Management IP"] == z_side_pe_ip:
            neighbor = a_side_pe_ip
        # if device is a side pe, neighbor is z side pe
        elif device["Management IP"] == a_side_pe_ip:
            neighbor = z_side_pe_ip
        # if circuit is locally switched, neighbor is self
        else:
            neighbor = device["Management IP"]
        self.logger.info("l2circuit neighbor ip: {}".format(neighbor))
        return neighbor

    def resource_comparison_fre_pro(self, network_fre, design_fre, mapper_resource_id, device, vendor):
        """
        Creates and compares tupel lists created from network_fre and design_fre resource
        """
        network_diff_dict, design_diff_dict = {}, {}

        if (
            network_fre["properties"]["included"][0]["relationships"]["tpes"]["data"][0]["id"].rsplit("-", 2)[-2]
            != design_fre["properties"]["included"][0]["relationships"]["tpes"]["data"][0]["id"].rsplit("-", 2)[-2]
        ):
            network_fre2 = network_fre["properties"]["included"][0]
            network_fre["properties"]["included"][0] = network_fre["properties"]["included"][1]
            network_fre["properties"]["included"][1] = network_fre2

        # append MP circuitName to design/network tupels
        design_diff_dict["MP-flow"] = design_fre["properties"]["data"]["attributes"]["additionalAttributes"][
            "circuitName"
        ].upper()
        network_diff_dict["MP-flow"] = network_fre["properties"]["data"]["attributes"]["additionalAttributes"][
            "circuitName"
        ].upper()

        if design_diff_dict["MP-flow"] != network_diff_dict["MP-flow"]:
            self.patch_service_mapper_diffs_fre(mapper_resource_id, network_diff_dict, design_diff_dict, device)
            self.logger.info(
                "Mapper MP FRE Design Diffs: {}\nMapper MP FRE Network Diffs: {}".format(
                    design_diff_dict, network_diff_dict
                )
            )
        else:
            self.logger.info("No FRE MP-flow Differences Found.")

    def patch_service_mapper_diffs_tpe(
        self, mapper_resource_id, device, network_resource_diff, mdso_resource_diff, is_core=False
    ):
        mapper_resource = self.bpo.resources.get(mapper_resource_id)
        mapper = mapper_resource["properties"]
        self.logger.info("patching differences from TPE")
        self.logger.info("initial mapper is: " + str(mapper))
        if not mapper.get("service_differences"):
            mapper["service_differences"] = {}
        if not mapper.get("service_differences").get(device):
            mapper["service_differences"][device] = {}

        if not mapper.get("service_differences").get(device).get("port"):
            mapper["service_differences"][device]["port"] = {
                "Network": network_resource_diff,
                "Design": mdso_resource_diff,
            }
        else:
            network, design = (
                mapper["service_differences"][device]["port"]["Network"],
                mapper["service_differences"][device]["port"]["Design"],
            )
            self.logger.info("Network:{} \n Design:{}".format(network, design))
            network.update(network_resource_diff), design.update(mdso_resource_diff)
            mapper["service_differences"][device]["port"]["Network"] = network
            mapper["service_differences"][device]["port"]["Design"] = design

        self.logger.info("mapper is: " + str(mapper["service_differences"]))

        # on initial run in prod (remediation_flag is always True) all service differences moved to initial differences
        if self.is_service_mapper_remediation(mapper_resource) and not is_core:
            try:
                self.logger.info("Updating service mapper resource with initial differences found.")
                self.bpo.resources.patch_observed(
                    mapper_resource_id, data={"properties": {"initial_differences": mapper["service_differences"]}}
                )
            except Exception:
                self.logger.error("Unable to update initial differences", Exception)
        # on secondary run to re-evaluate differences after initial run + remediation attempts,
        # any remaining service differences are repopulated
        else:
            try:
                self.logger.info(
                    "Updating service mapper resources with service differences remaining after remediation attempt."
                )
                self.bpo.resources.patch_observed(
                    mapper_resource_id, data={"properties": {"service_differences": mapper["service_differences"]}}
                )
            except Exception:
                self.logger.error("Unable to update service differences", Exception)

    def get_resource_by_dependency_or_association(
        self, get_resource_type, dependent_resource_id=None, associated_resource_id=None
    ):
        """
        param get_resource_type: CONSTANT resource type of resource to get
        param dependant_resource_id: str ID of resource to get dependencies of to find requested resource
        param associated_resource_id: str ID of resource requesting get resource
        return type dict if requested resource found or None if none found
        """
        if dependent_resource_id:
            resource_get = self.get_dependencies(dependent_resource_id, get_resource_type)
            resource = resource_get[0] if resource_get else None
        else:
            self.logger.info("Checking for indpendent resource")
            resource = self.get_associated_resource(associated_resource_id, get_resource_type)
        return resource

    def patch_service_mapper_diffs_policer(self, mapper_resource_id, device, network_bw_dict, design_bw_dict):
        mapper_resource = self.bpo.resources.get(mapper_resource_id)
        mapper = mapper_resource["properties"]
        self.logger.info("Patching policer differences")
        self.logger.info("initial mapper is: " + str(mapper))
        if not mapper.get("service_differences"):
            mapper["service_differences"] = {}
        if not mapper.get("service_differences").get(device):
            mapper["service_differences"][device] = {}
        if not mapper.get("service_differences").get(device).get("bw_profile"):
            mapper["service_differences"][device]["bw_profile"] = {"Network": network_bw_dict, "Design": design_bw_dict}
        else:
            network, design = (
                mapper["service_differences"][device]["bw_profile"]["Network"],
                mapper["service_differences"][device]["bw_profile"]["Design"],
            )
            self.logger.info("Network:{} \n Design:{}".format(network, design))
            network.update(network_bw_dict), design.update(design_bw_dict)
            mapper["service_differences"][device]["bw_profile"]["Network"] = network
            mapper["service_differences"][device]["bw_profile"]["Design"] = design

        self.logger.info("mapper is: " + str(mapper["service_differences"]))

        if self.is_service_mapper_remediation(mapper_resource):
            try:

                self.bpo.resources.patch_observed(
                    mapper_resource_id, data={"properties": {"initial_differences": mapper["service_differences"]}}
                )
            except Exception:
                self.logger.error("Unable to update initial differences", Exception)
        else:
            try:
                self.bpo.resources.patch_observed(
                    mapper_resource_id, data={"properties": {"service_differences": mapper["service_differences"]}}
                )
            except Exception:
                self.logger.error("Unable to update service differences", Exception)

    def patch_service_mapper_diffs_fre(
        self, mapper_resource_id, network_resource_diff, mdso_resource_diff, device, is_core=False
    ):
        mapper_resource = self.bpo.resources.get(mapper_resource_id)
        mapper = mapper_resource["properties"]
        self.logger.info("Patching FRE differences")
        self.logger.info("initial mapper is: " + str(mapper))
        if not mapper.get("service_differences"):
            mapper["service_differences"] = {}
        if not mapper.get("service_differences").get(device):
            mapper["service_differences"][device] = {}
        if not mapper.get("service_differences").get(device).get("flow"):
            mapper["service_differences"][device]["flow"] = {
                "Network": network_resource_diff,
                "Design": mdso_resource_diff,
            }
        else:
            network, design = (
                mapper["service_differences"][device]["flow"]["Network"],
                mapper["service_differences"][device]["flow"]["Design"],
            )
            network.update(network_resource_diff)
            design.update(mdso_resource_diff)
            mapper["service_differences"][device]["flow"] = {"Network": network, "Design": design}

        self.logger.info("post mapper is: " + str(mapper["service_differences"]))

        if self.is_service_mapper_remediation(mapper_resource) and not is_core:
            try:
                self.bpo.resources.patch_observed(
                    mapper_resource_id, data={"properties": {"initial_differences": mapper["service_differences"]}}
                )
            except Exception:
                self.logger.error("Unable to update initial differences", Exception)

        else:
            try:
                self.bpo.resources.patch_observed(
                    mapper_resource_id, data={"properties": {"service_differences": mapper["service_differences"]}}
                )
            except Exception:
                self.logger.error("Unable to update service differences", Exception)

    def patch_service_mapper_diffs_mp(self, mapper_resource_id, network_resource_diff, mdso_resource_diff, device):
        mapper_resource = self.bpo.resources.get(mapper_resource_id)
        mapper = mapper_resource["properties"]
        self.logger.info("Patching MP differences")
        self.logger.info("initial mapper is: " + str(mapper))
        if not mapper.get("service_differences"):
            mapper["service_differences"] = {}
        if not mapper.get("service_differences").get(device):
            mapper["service_differences"][device] = {}

        mapper["service_differences"][device]["mp-flow"] = {
            "Network": network_resource_diff,
            "Design": mdso_resource_diff,
        }

        self.logger.info("post mapper is: " + str(mapper["service_differences"]))
        if self.is_service_mapper_remediation(mapper_resource):
            try:

                self.bpo.resources.patch_observed(
                    mapper_resource_id, data={"properties": {"initial_differences": mapper["service_differences"]}}
                )
            except Exception:
                self.logger.error("Unable to update initial differences", Exception)
        else:
            try:
                self.bpo.resources.patch_observed(
                    mapper_resource_id, data={"properties": {"service_differences": mapper["service_differences"]}}
                )
            except Exception:
                self.logger.error("Unable to update service differences", Exception)

    def compare_bw_profile(self, design_bw_profile, network_bw_profile):
        network_tupel_list = []
        design_tupel_list = []

        # on the network but not on MDSO
        additional_props = ["committedBurstSize", "committedInformationRate"]
        for tupel in network_bw_profile["properties"].items():
            if tupel[0] in additional_props:
                pass
            else:
                if tupel not in design_bw_profile["properties"].items():
                    network_tupel_list.append(tupel)

        # on MDSO but not on the Network
        for tupel in design_bw_profile["properties"].items():
            if tupel[0] in additional_props:
                pass
            else:
                if tupel not in network_bw_profile["properties"].items():
                    design_tupel_list.append(tupel)

        for property in additional_props:
            for tupel in network_bw_profile["properties"][property].items():
                if tupel not in design_bw_profile["properties"][property].items():
                    modified_tupel = (property, str(tupel[1]) + network_bw_profile["properties"][property]["units"])
                    network_tupel_list.append(modified_tupel)
            for tupel in design_bw_profile["properties"][property].items():
                if tupel not in network_bw_profile["properties"][property].items():
                    modified_tupel = (property, str(tupel[1]) + network_bw_profile["properties"][property]["units"])
                    design_tupel_list.append(modified_tupel)

        design_tupel_dict, network_tupel_dict = self.list_to_dict(design_tupel_list, network_tupel_list)
        return design_tupel_dict, network_tupel_dict

    def get_associated_resource(self, resource_id, resource_type):
        """
        :param resource_id: resource id
        :return: resource or None
        :error: if more than one associated resource found
        """
        resource = None
        resource_dependents = self.get_dependents(resource_id, resource_type, True, False)
        if len(resource_dependents) == 1:
            resource = resource_dependents[0]
        if len(resource_dependents) > 1:
            msg = self.error_formatter(
                self.SYSTEM_ERROR_TYPE, "Multiple Associated Dependent Resources", f"resource type: {resource_type}"
            )
            self.categorized_error = msg
            self.exit_error(msg)
        return resource

    def get_by_provider_resource_id(self, domain_id, provider_resource_id, retries=1, obfuscate=None):
        """
        OVERRIDING THIS FUNCTION HERE TO AVOID SLEEPING  FOR 10 SECS
        EVERYTIME  THIS FUNCTION IS CALLED. THIS IS A BUG IN PLANSDK
        CODE
        Retrieve first resource from the given provider resource id.

        As of Orchestrate 19.02 (bpocore 3.0.0), values of properties that are marked with `obfuscate = true` in the
        resource type definition are, by default, replaced with sequences of asterisks (`*`) in Market API responses.
        In rare circumstances where unobfuscated values are required, set the `obfuscate` parameter to `False` to
        override the default.

        .. versionchanged:: 3.5.0
            added *obfuscate* parameter;
            *domain_id* may be ``None``

        :param str domain_id: Domain identifier or None
        :param str provider_resource_id: Provider resource identifier
        :param int retries: Retry-count when it failed
        :param bool obfuscate: Request obfuscation for values of properties whose definitions are marked with
            `obfuscate = true`
            If None, the Market API default obfuscation applies.
            Ciena recommends always passing obfuscate=True
        :return: :class:`dict` -- GET body if the request was successful
        :exception: RuntimeError when requests failed
        """
        params = {"providerResourceId": provider_resource_id}

        if domain_id is not None:
            params["domainId"] = domain_id

        if obfuscate is not None:
            params["obfuscate"] = obfuscate

        url = "/resources?{}".format(parse.urlencode(params))

        for cnt in six.moves.xrange(retries):
            reply = self.bpo.market.get(url, return_full=True)

        if reply["status_code"] == 200:
            return reply["body"]["items"][0]

        return None

    def get_resource_await_orchstate(self, resource_id, orchstates, timeout, poll_interval):
        """
        Check and await for orchstate to match orchstates that are defined.

        Parameters:
        resource_id (string) : resource id of resource to be checked
        orchstates (set) : set of expected orchstates to await for. ex : {'active','failed'}
        timeout (int) : how long to await for in seconds ex: 300
        poll_interval (int) : how long between polling cycles

        Returns:
        result (dict) : returns entire resource, if orchstate of resource matches expected orchstates

        Raises:
        ResourceFailed : When one of the resources has orchState=failed and 'failed' isn't in orch_states.
        ResourceNotFound :  When BPO returns a 404 for one of the resources.
        TimeOut : When wait_timer expires.
        """
        # instantiate wait timer
        wait_timer = WaitTimer.from_timeout(timeout=timeout, poll_interval=poll_interval)

        # get resource from mdso
        resource = self.bpo.resources.get(resource_id)

        # await for orch state
        result = self.bpo.resources.await_orch_state(orchstates, [resource], wait_timer=wait_timer)

        return result[0]

    def get_session_profile_by_type_and_label(self, device_vendor, domain_id, profile_type, operation):
        """returns the netconf session profile associated with the domain

        :param device_vendor: Name of device vendor to match the CommonPlan.COMMON_TYPE_LOOKUP
        :param domain_id: UUID of the domain
        :param profile_type: Type of session profile (netconf, cli)
        :type device_vendor: str
        :type domain_id: str

        :return: Session Profile resource
        :rtype: dict
        """
        domain_lookup = self.COMMON_TYPE_LOOKUP.get(device_vendor)

        session_profiles = self.get_resource_by_type_and_domain(domain_lookup["SESSION_PROFILE_TYPE"], domain_id)

        if len(session_profiles) == 0:
            msg = self.error_formatter(
                self.SYSTEM_ERROR_TYPE,
                "Missing Session Profile",
                f"vendor: {device_vendor} session profile type: {domain_lookup['SESSION_PROFILE_TYPE']} \
                requested by: get_session_profile_by_type_and_label",
            )
            self.categorized_error = msg
            raise Exception(msg)

        return_value = None

        if operation == "CPE_ACTIVATION":
            for profile in session_profiles:
                if profile_type in profile["properties"]["connection"]:
                    if profile_type == "netconf":
                        if profile["label"] == "default_netconf":
                            return_value = profile
                            break
                    else:
                        if profile["label"] == "default":
                            return_value = profile
                            break

        elif operation == "MANAGED_SERVICES_ACTIVATION":
            for profile in session_profiles:
                if profile_type in profile["properties"]["connection"]:
                    if "managed_service" in profile["label"]:
                        return_value = profile
                        break

        else:
            for profile in session_profiles:
                if profile_type in profile["properties"]["connection"]:
                    if "sensor" in profile["label"]:
                        return_value = profile
                        break

        self.logger.info("Returning session profile: " + str(return_value))

        return return_value

    def get_session_profile_by_label(self, device_vendor, domain_id, operation, session_name=None):
        """returns the session profile associated with the domain

        If the session profile is the UUID it will get the session profile.
        If the session_name is None, then it will pick the first one that is returned.  Raises
        an exception if it cannot find a session profile.

        :param device_vendor: Name of device vendor to match the CommonPlan.COMMON_TYPE_LOOKUP
        :param domain_id: UUID of the domain
        :param session_name: UUID or Label of the Session Profile
        :type device_vendor: str
        :type domain_id: str
        :type session_name: str

        :return: Session Profile resource
        :rtype: dict
        """
        domain_lookup = self.COMMON_TYPE_LOOKUP.get(device_vendor)

        if session_name is None:
            session_profiles = self.get_resource_by_type_and_domain(domain_lookup["SESSION_PROFILE_TYPE"], domain_id)
        else:
            session_profiles = self.get_resources_by_label_or_uuid(
                domain_id, domain_lookup["SESSION_PROFILE_TYPE"], session_name
            )

        if len(session_profiles) == 0:
            msg = self.error_formatter(
                self.SYSTEM_ERROR_TYPE,
                "Missing Session Profile",
                f"vendor: {device_vendor} session profile type: {domain_lookup['SESSION_PROFILE_TYPE']} \
                requested by: get_session_profile_by_label",
            )
            self.categorized_error = msg
            raise Exception(msg)

        return_value = None

        if len(session_profiles) > 1:
            if operation == "CPE_ACTIVATION":
                for profile in session_profiles:
                    if profile["label"] == "default":
                        return_value = profile
                        break
            elif operation == "MANAGED_SERVICES_ACTIVATION":
                for profile in session_profiles:
                    if "managed_service" in profile["label"]:
                        return_value = profile
                        break
            else:
                for profile in session_profiles:
                    if "sensor" in profile["label"]:
                        return_value = profile
                        break
        else:
            return_value = session_profiles[0]

        self.logger.info("Returning session profile: " + str(return_value))

        return return_value

    def is_skip_bw_policer(self, context, node_vendor, device_role, node_model):
        # check if we need to skip applying policer to particular device role
        skip = False
        lookup = self.COMMON_TYPE_LOOKUP[node_vendor]
        if "BW_POLICER_IGNORE_LIST" in lookup:
            ignores = lookup.get("BW_POLICER_IGNORE_LIST")
            for ignore in ignores:
                if (context in ignore["deviceRole"] and device_role in ignore["deviceRole"]) and (
                    ignore["modelFamily"] in node_model
                ):
                    skip = True
        return skip

    def get_tpe_res_id_retry(self, fre_resource_id, retries=4):
        """
        returns tpe resource id, retries if 'Unmapped ProviderId' is found.
        """
        for _cnt in range(retries):
            tpe_res_id = self.bpo.resources.get(fre_resource_id)["properties"]["included"][0]["id"]
            if "Unmapped ProviderId" not in tpe_res_id:
                break
            time.sleep(5)

        if "Unmapped ProviderId" in tpe_res_id:
            self.logger.info(
                f"Unmapped ID found for tpe resource : {tpe_res_id} in fre resource {fre_resource_id}. Retries : {retries}."
            )
            msg = self.error_formatter(
                self.SYSTEM_ERROR_TYPE,
                "Unmapped Provider ID",
                f"tpe resource: {tpe_res_id} fre resouce: {fre_resource_id} retries: {retries}",
            )
            self.categorized_error = msg
            self.exit_error(msg)

        else:
            self.logger.info("Tpe resource found, id : {} after retries {}".format(tpe_res_id, retries))
        return tpe_res_id

    def status_messages(self, msg, error=False, parent="cpe_activation"):
        # Receive status/error messages from Managed Service Activator code & update fields in:
        # cpe_activation & Network Service resources & Managed Services

        # Display status messages for polling by the Web UI
        self.logger.info("PROGRESS REPORT: {}".format(msg))

        # Updating properties for CPE activation resource and Managed Resources
        activation_properties = self.resource["properties"]

        if parent == "cpe_activation":
            # Updating properties for network service resource
            network_service_resourceid = self.network_service_id
            self.network_ser_res = self.mget("/resources/%s" % self.network_service_id).json()
            network_service_properties = self.network_ser_res["properties"]

        elif parent == "network_service":
            network_service_resource_id = self.properties.get("network_service_resource_id")

            if network_service_resource_id:  # check that the resource has network service resource id
                self.logger.info("Attempting to grab properties for {}".format(network_service_resource_id))
                self.network_service_resource = self.mget("/resources/%s" % network_service_resource_id).json()

                self.logger.info("The network service resource : {}".format(self.network_service_resource))

                network_service_properties = self.network_service_resource["properties"]

                if error:  # if there is an error, update the "error" property instead of status
                    network_service_properties[parent + "_error"] = msg
                    self.bpo.resources.patch_observed(
                        network_service_resource_id, {"properties": {parent + "_error": msg}}
                    )
                else:  # When there is no error, that means we update "status"
                    network_service_properties[parent + "_status"] = msg  # update status message
                    self.bpo.resources.patch_observed(
                        network_service_resource_id, {"properties": {parent + "_status": msg}}
                    )  # patch properties to parent resource
            else:
                self.logger.info("Network resource ID not available to be updated")

        if not error:
            activation_properties[parent] = msg
            if parent == "cpe_activation":
                network_service_properties[parent] = msg
        else:
            activation_properties[parent + "_error"] = msg
            if parent == "cpe_activation":
                network_service_properties[parent + "_error"] = msg

        if parent != "network_service":
            self.bpo.resources.patch_observed(self.resource["id"], {"properties": activation_properties})
        if parent == "cpe_activation":
            self.bpo.resources.patch_observed(network_service_resourceid, {"properties": network_service_properties})

    def splunk_logger_setup(self):
        """
        Setup splunk logger and return logger instance

        Returns:
        logging.logger (class) : returns splunk logger that can be called for logging to splunk

        Ex: splunk_logger.log("test data")
        """

        splunk_logger = logging.getLogger("SensorSplunkLogger")
        splunk_logger.setLevel(logging.DEBUG)
        if not os.path.exists("/bp2/log/splunk-logs"):
            os.makedirs("/bp2/log/splunk-logs")
        splunk_file_handler = RotatingFileHandler("/bp2/log/splunk-logs/sensor-templates-splunk.log", backupCount=10)
        splunk_file_handler.setLevel(logging.DEBUG)
        splunk_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        splunk_file_handler.setFormatter(splunk_formatter)
        splunk_logger.addHandler(splunk_file_handler)

        return splunk_logger

    def resync_poll_free_network_functions(self, circuit_details):
        """
        resyncs only devices whos RAs are poll free
        requires the full circuit details resource
        Supported RAs: Juniper
        """
        poll_free_ras = ["JUNIPER"]

        spoke_list = self.create_device_dict_from_circuit_details(circuit_details)
        # cycle through devices in circuit and resync all supported vendor devices
        for device in spoke_list[0]:
            if spoke_list[0][device]["Vendor"] in poll_free_ras:
                device_name = spoke_list[0][device]["FQDN"]
                device_ip = spoke_list[0][device]["Management IP"]
                self.resync_network_function(device_name, device_ip)

    def resync_network_function(self, device_name, device_ip=None, network_function_resource=None):
        """
        resyncs any device provided a FQDN or ip
        """
        if not network_function_resource:
            network_function_resource = self.get_network_function_by_host_or_ip(device_name, device_ip)
        if network_function_resource:
            self.bpo.resources.resync(network_function_resource["id"])
            self.logger.info(
                f"Resync requested. ResourceID: {network_function_resource['id']} TID: {network_function_resource['label']} "
            )

    def flatten_complex_dict(self, complex_dict, parent_key=False, seperator="."):
        """
        Flatten a complex and nested dictionary structure into a single level dictionary
        Parameters
            complex_dict (dict): The complex dictionary to flatten
            parent_key (str): Thge string to prepend to the new key
            seperator (str): The seperator to use for the flattened dictionary
        Returns
            dict: The flattened dictionary
        """
        items = []
        for key, value in complex_dict.items():
            new_key = str(parent_key) + seperator + key if parent_key else key
            if isinstance(value, dict):
                if not value.items():
                    items.append((new_key, None))
                else:
                    items.extend(self.flatten_complex_dict(value, new_key, seperator).items())
            elif isinstance(value, list):
                if len(value):
                    for k, v in enumerate(value):
                        items.extend(self.flatten_complex_dict({str(k): v}, new_key, seperator).items())
                else:
                    items.append((new_key, None))
            else:
                items.append((new_key, value))

        return dict(items)

    def check_is_edna(self, device_prid):
        """
        GET the NetworkFunction resource and check for the isEdna value
        if the value exist is and is True then proceed with the business logic
        if the value doesn't exist or is False then use RACUTTHROUGH command to check is_edna and patch NF resource with the isEdna value
        """
        network_function = self.bpo.market.get_resources_by_type_and_provider_id(
            "junipereq.resourceTypes.NetworkFunction", device_prid
        )[0]
        is_edna = network_function["properties"].get("isEdna")
        if is_edna:
            return True
        else:
            is_edna = self.execute_ra_command_file(device_prid, "is_edna.json", parameters={}, headers=None).json()[
                "result"
            ]
            self.bpo.resources.patch(network_function["id"], {"properties": {"isEdna": is_edna}})
            return is_edna

    def get_sensor_profile_connection_details(self, network_function_id, vendor, model, tid):
        domain_id = self.get_domain_id(network_function_id)
        session_name = self.get_session_name(vendor, model)
        session_profile = self.get_session_profile(vendor, domain_id, session_name)
        profile_connection_type = {
            "connection_type": connection_type for connection_type in session_profile["properties"]["connection"]
        }
        connection_type = profile_connection_type["connection_type"]
        hostport = session_profile["properties"]["connection"][connection_type]["hostport"]
        session_profile_authentication_creds = session_profile["properties"]["authentication"][connection_type]

        sensor_profile_connection_details = {
            "label": tid,
            "properties": {
                "sessionProfile": session_profile["id"],
                "connection": {"hostname": tid, connection_type: {"hostport": hostport}},
                "authentication": {
                    connection_type: {
                        "password": session_profile_authentication_creds["password"],
                        "username": session_profile_authentication_creds["username"],
                    }
                },
            },
        }

        return sensor_profile_connection_details

    def update_device_connection_details(self, network_function_id, data, discovered=True):
        self.logger.info("Updating session profile to: {}".format(data["properties"]["sessionProfile"]))
        # the dance

        self.bpo.resources.patch(network_function_id, {"discovered": False})

        self.bpo.resources.patch(network_function_id, data)

        self.bpo.resources.patch(network_function_id, {"discovered": True})

    def is_typeii_cpe_mgmt_built(self, interface_config, outer_vlan):
        interface = list(interface_config.get("configuration").get("interfaces").keys())[0]
        unit_configs = interface_config.get("configuration").get("interfaces").get(interface).get("unit")

        for unit in unit_configs:
            if unit.get("vlan-tags"):
                if unit["vlan-tags"]["outer"] == outer_vlan and unit["vlan-tags"]["inner"] == "99":
                    return True
        return False

    def get_session_name(self, vendor, model):
        session_name_vendor = "jnpr" if vendor == "JUNIPER" else vendor.lower()
        session_name = "sensor_{}".format(session_name_vendor)
        if "116PRO" in model:
            session_name += "_netconf"
        return session_name

    def is_default_session_profile(self, network_function_user, sensor_user, network_function_pass, sensor_pass):
        return network_function_user != sensor_user and network_function_pass != sensor_pass

    def ip_update(self, tid, cpe_ip):
        """
        Calls Palantir endpoint to update CPE's management IP in Granite
        """
        self.bpo_constants = self.get_bpo_contants_resource()
        url = self.bpo_constants["properties"]["circuit_details_server_info"]["server_url"]
        self.logger.info("BPO CONSTANTS URL: {}".format(url))
        ip_update_endpoint = url + "/palantir/v2/device/ip_update?IP={}&TID={}"

        ip_update_response = requests.post(ip_update_endpoint.format(cpe_ip, tid))
        self.logger.info(
            "IP UPDATE RESPONSE: status_code={}, reason={}, json={}".format(
                ip_update_response.status_code, ip_update_response.reason, ip_update_response.json()
            )
        )

        return ip_update_response

    def iseupdate(self, cpe, cpe_ip):
        """
        Calls Palantir endpoint to add CPE to ISE
        """
        self.bpo_constants = self.get_bpo_contants_resource()
        url = self.bpo_constants["properties"]["circuit_details_server_info"]["server_url"]
        self.logger.info("BPO CONSTANTS URL: {}".format(url))
        isin_endpoint = url + "/palantir/v3/ise/isin?ip={}&tid={}"

        # Attempt to add device to CEDR via isin
        get_isin_response = requests.get(isin_endpoint.format(cpe_ip, cpe["tid"]))
        # put_isin_response = requests.put(
        #     isin_endpoint.format(self.cpe_ip), data=None, headers={"Content-Type": "application/json"}, timeout=5
        # )
        self.logger.info(
            "ISIN GET Response: status_code{}, reason={}, json={}".format(
                get_isin_response.status_code, get_isin_response.reason, get_isin_response.json()
            )
        )

    def get_network_function_resource_type_by_vendor(self, vendor):
        return self.COMMON_TYPE_LOOKUP[vendor]["DEVICE_TYPE"]

    def get_circuit_details_with_retry(self, url, headers, retries=3):
        res = requests.get(url, verify=False, headers=headers)
        self.logger.info(f"Response code: {res.status_code}")

        if res.status_code >= 300 and retries > 0:
            self.logger.info(
                f"Call failed to circuit details server with response code {res.status_code}, message: {res.text}"
            )
            self.logger.info(f"Remaining Retries: {retries}. Retrying call to circuit details server.")
            time.sleep(15)

            return self.get_circuit_details_with_retry(url, headers, retries=retries - 1)

        elif res.status_code >= 300:
            self.logger.info(
                f"Call failed to circuit details server with response code {res.status_code}, message: {res.text}"
            )
            msg = self.error_formatter(
                self.SYSTEM_ERROR_TYPE,
                "Circuit Details Collection",
                f"url: {url} code: {res.status_code}, message: {res.text}",
                system=self.SENSE,
            )
            self.categorized_error = msg
            self.exit_error(msg)

        else:
            return res

    def get_device_model_dir_name(self, device_model):
        """This is to adjust directory name if device model is 116PROH"""
        return "116pro" if "116PROH" in device_model or "118PRO" in device_model else device_model[-6:].lower()


class SingletonActivate(CommonPlan):
    """this is a generic plan that can be used to unsure that only a single instance
    of a built-in resource is active at a time
    """

    def process(self):
        # See if there are any active resources already there.
        # If there are, exception out.
        active_resources = self.get_active_resources(self.resource["resourceTypeId"])
        if len(active_resources) > 1 or (
            len(active_resources) == 1 and active_resources[0]["id"] != self.resource["id"]
        ):
            self.logger.info("ERROR: Only able to create a single type of this service.")

            msg = self.error_formatter(
                self.SYSTEM_ERROR_TYPE,
                "Singleton Violation",
                f"resource type: {self.resource['resourceTypeId']} only one of this type of service allowed",
            )
            self.categorized_error = msg
            raise Exception(msg)
