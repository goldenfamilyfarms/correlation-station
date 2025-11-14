## Charter Sensor Templates

This project provides the repository for the Charter SENSOR project.

Administrators: 
Troy Gutjahr (tgutjahr@ciena.com)

Contributors:
Matt Becker (mbecker@ciena.com), John Wice (jwice@ciena.com)
                
## Changelog

v0.1:
Initial check-in for resources to support Ethernet service activation
across RAD CPE and Juniper MX Devices

v0.2:
Updating the process and objects with new features based on the testing done
through the MEF Services.  Also added some pre-checks and the ability for 
services to be able to delete themselves.

## Overview
The overall workflow for an Ethernet service activation is managed from a
top level resource called NetworkService (see below).  The overall program has
three levels of abstraction:

*tosca.resourceTypes...* from the RAs
- This provides the resource view of the network promoted by the RA
to support all the base level constructs from the device (device model).
- The model used is TPE_FRE which is based on the GP922 Information
framework from the TMForum.
- The base constructs are:
    - NetworkConstruct: Logical Representation of the device
    - Termination Point Encapsulation (TPE): Physical and logical connection points
    - Forward Relationship Encapsulation (FRE): Represents the connectivity between two TPEs
    - Other classes have been added to support device level profiles.
        
*mef.resourceTypes...* ST
- This layer of Service Templates provides a service level abstraction that
translates the TPE_FRE model from the device model to end-to-end Layer2
services.
- The model selected is based on the Legato MEF model promoted in the LSO project.
- The main constructor is done through the mef.resourceTypes.MEFService.
    - This is the main resource type for the higher layers to communicate through.
        
*charter.resourceTypes...* ST
- This layer provides the work flow Service Templates specific to the Charter
environment and circuit information.
- Its role is to transform the circuit information from Charter to the MEF model
that the service abstraction is using.
- The overall layers for interaction are:

        Charter API ----> Charter STs -----> MEF STs ----> TPE_FRE RA Model


Network config for service is detailed [here](service_config.md).

## Orchestration Workflow
This section describes the orchestration work flows for the various actions of the 
system.  It is intended to be used by people looking to understand or troubleshoot 
how the orchestrator is building various resources and the decisions required.

### Provisioning / Activation Workflow of a charter.resourceTypes.NetworkService
![Provisioning workflow](Charter_Sensor_Workflow.png "Provisioning / Activation Workflow")
      
### Resource Operation Explanation
#### charter.resourceTypes.NetworkService
*Input:* Charter Name of the circuit

*Actions:*
  - Provides the orchestration workflow above
  
#### tosca.resourceTypes.TraceLog
*Input:* Trace information

*Actions:*
  - As part of every template that extends CommonPlan and does not overwrite the "enter_exit_log()" function,
  a trace message will be created for the start and end of the orchestration activity.
  - There will be one TraceLog resource for each top-level resource / action
  - It uses the "tradeId" header provided to each ST to track which action the action is associated with.
  - This can be used to see all the major orchestration steps of a service.
  - It stores the start/end, time elapse, log file, action that was performed on the resource

#### charter.resourceTypes.UpdateObservedProperty
*Input:* Network Service ID, State String

*Actions:*
  - This will update the observed value of the resource ID passed int with the state string
  - It is meant to update the NetworkService state for the northbound system
  - The states have an ENUM so that needs to be modified if something is to be added
  - This resource deletes itself after completed

#### charter.resourceTypes.NetworkServiceCheck
*Input:* Charter Name of the circuit, Provisioning stage: PRE/POST

*Actions:*
  - When "PRE":
     - Verifies for activation that the circuit_id is proper (>5 characters) and that another "active" circuit 
     with the same name does not already exist in the orchestrator.
     - Verifies that there is not a MEF service already built with the VC_ID specified in the Circuit Details
  - When "POST":
     - Updates the CPE Site State in the NetworkService based on the success of the service provisioning
  - This resource deletes itself after completed

#### charter.resourceTypes.CircuitDetailsCollector
Input: Charter Name of the circuit

*Actions:*
  - Loads the charter.resourceTypes.BpoConstants resource which holds the URL information to talk to the ARDA
  service to retrieve the circuit information.
  - Replaces the "circuit_id" in the URL with the input one (if required).
  - Makes an HTTPS call to the server and expects a JSON structure returned.
  - Verifies that the response from the call has the same circuit ID provided.
  - Transforms the JSON structure and builds an instance of charter.resourceTypes.CircuitDetails.
  - Builds a relationship between the CircuitDetails object and the NetworkService.

#### charter.resourceTypes.CircuitDetails
Input: Circuit information transformed from ARDA/Granite Server

*Actions:*
   - None

#### charter.resourceTypes.ServiceDeviceValidator
*Input:* Circuit Details ID and Circuit Name

*Actions:*
   - Verifies that that PEs are on-boarded into Blue Planet and that they have a good communication state.
   - Checks the CPEs devices to see which ones are active already in the network ("Type") and then checks
   which ones are already onboarded into BPO.  
   - Finds the associated NetworkFunction in BPO based on the hostname in the CircuitDetails matching the 
   IPAddress in the NetworkFunction, so these must match.
   - For those not already onboarded into BPO, it will update the CircuitDetails with the missing device 
   names ("devices_to_onboard").  
   - For those device resources that are onboarded it will verify the communication state of those CPEs.  If the
   state is not listed as "AVAILABLE" it will fail.
   - When it on-boards a device it will call the DeviceOnboarder activate plan.
   - This resource deletes itself after completed

#### tosca.resourceTypes.ServiceDeviceOnboarder
*Input:* CircuitDetails ID

*Actions:*
   - From the "devices_to_onboard" property in the CircuitDetails it will onboard the CPEs that are missing
   from the BPO Market.
   - For each device that is missing it will call the charter.resourceTypes.DeviceOnboarder.
   - If no devices are found it will just complete.
   - It will then change the deployed state in the CircuitDetails properties.
   - This resource deletes itself after completed
 
#### charter.resourceTypes.DeviceOnboarder
*Input:* Device Vendor, Hostname, SessionProfile Name (Optional)

*Actions:*
   - Assumes that the input hostname is routeable.
   - Finds all the domains associated with the vendor and selects the least used domain for addition.
   - Finds the SessionProfile for the device if one is not input.  It assumes that all SessionProfiles for the 
   domain are valid and available.
   - This also means that there is a session profile for each domain.
   - Creates a NetworkFunction in the domain with the SessionProfile.
   - This resource deletes itself after completed

#### charter.resourceTypes.UpdateObservedProperty
*Input:* Resource ID, Patch Properties

*Actions:*
   - Helper resource that will patch the observed value of the resource.  
   - This typically is used for ST resources that have properties with config = False, so that the observed
   value becomes the orch value.
   - This is used specifically to update the state of the NetworkService resource with the stage it is at
   and the CPE onboarding state.
   - This resource deletes itself after completed
   
#### charter.resourceTypes.ServiceDeviceProfileConfigurator
*Input:* Circuit Details IS, Circuit ID, Context

*Actions:*
   - Verify if the packet bandwith profile (PBW profile) exists in the device.
   - If the packet bandwith profile (PBW profile) does not exist on the device then it configures the packet bandwith profile (PBW profile) or policer using the product instance matching the values.
   - If the packet bandwith profile (PBW profile) does exist on the device then break and skipt the step.

#### charter.resourceTypes.ServiceFreOnboarder
*Input:* Circuit Details ID

*Actions:*
   - Based on the circuit topology it will build FREs (Link representation) between the CPE devices
   and the PE device.
   - Typically the CPE is a TPE and the PE is a juniper Port
   - If the TPE/Port already have a relationship with another FRE, than it is ignored.  If the TPE/Port
   cannot be found in the Market, than an error is thrown.
   - This resource deletes itself after completed

#### charter.resourceTypes.ServiceProvisioner
*Input:* Circuit Details ID, Context

*Actions:*
   - Based on the context (PE or CPE) it will determine the type of service that is to be provisioned. 
   - This can be PE-to-PE, CPE-to-PE or CPE-to-CPE.
   - It uses the Context property and the Circuit Details to determine what to do.
   - The pe_service_provisioner resource will be created with context of PE so that the resource will look to 
   provision the PE-to-PE service.
   - The CircuitDetails object will then be consumed and transformed into a MEFService resource.
   - On the PE context the MEFService will be called with an Activate.
   - On the CPE context the MEFService will be patched with either one or both endpoints changing from the
   PE to the CPE.

#### mef.resourceTypes.MEFService
*Input:* All circuit information (see ResourceType)

*Actions:*
   - This is a test resource that will not do anything to the network.  It is invoked if the stage of the 
   Network Service is set to "TEST"
   
#### mef.resourceTypes.LegatoService
Input: All circuit information (see ResourceType)

*Actions:*
   - This is the Layer2 service definition.  Once called it will determine what needs to be provisioned in the 
   network based on the circuit description and the links (FREs) in the network.
   - It only take two endpoints of the service and determines the rest of the provisioning chain.
   - It decomposes into provisioning the RAD/ADVA (TPE/FRE) and Juniper (L2Circuit) RA
   
#### charter.resourceTypes.ServiceFreOnboarder
*Input:* CircuitDetails ID

*Actions:*
   - Based on the misssing_devices, deployed state and type described in the CircuitDetails it will build
   FREs (Links) between the PE and CPE ports in the BPO Market.
   - It will collect the TPE/Port resource that has been learned from the RAs.
   - If it cannot find a PTP it will raise a failure.
   - Check if there is already a link built on the PTP, if so it will exist assuming it is the one
   already there.
   - An FRE will then be built to represent the connectivity and a relationship will be created between it
   and the supporting TPEs/Ports.
   - The FRE label will be prepended with the "AUTO" string.
   - This resource deletes itself after completed
 
#### charter.resourceTypes.NetworkServiceCleaner
*Input:* NetworkService ID

*Actions:*  
   - Deletes any resources that might be required to stay around during the orchestration process (ie cannot
   delete themselves) after all the orchestration activies are completed.  These currently include
   the CircuitDetailsCollector as its output is used throughout the activation series.
   - This also ensure that the sub-sub-resources that are created as part of the activation are deleted when 
   the top level NetworkService is deleted.
   
#### tosca.resourceTypes.ResourceTerminator
*Input:* Resource ID, Wait Time (Sec)

*Actions:*  
   - Since declaratively created resources cannot delete themselves due to the relationship with other resources
    a resource that implements the CompleteAndTerminatePlan class will automatically create a ResourceTerminator
    when its activation is successfully completed.
    - The activation of this resources does nothing but build a relationship to the resource that called it
    - On the parent resource's completion of the activation, the termination of the ResourceTerminator will be called.
    - It will wait the period of time specified in the wait_time (default = 10sec) and then delete the parent resource
    and will delete itself so neither resource is left over.
    
#### charter.resourceTypes.ServiceDependencyModifier
*Input:* Circuit ID, CircuitDetails ID

*Actions:*
   - After the Flows/FRE is created through LegatoService, there are parts on the node that need to be updated that
   are not part of the flows.  For instance the TPEs/Ports on the PE and CPEs might need to be updated with descitpions, etc.
   This is not part of the standard flow creation, but needs to be done after provisioning.
   - This resource will determine if the ports are already updated with the information and if not, update the ports. Most
   notably it will put the ports in-service if the flows on them are up.
   - On deletion it will also updated the port state if it find that no other service using the port.
    
#### charter.resourceTypes.BpoConstants
*Input:* See resource

*Actions:*
   - This resource does not do anything, but store any static configuration information required for the orchestration.
   - Right now it stores the ARDA API command syntax to get the Circuit Details information.
   - There can only be one of these resources per server, any attempt to create more will fail.

#### charter.resourceTypes.DeviceFileOnboarder
*Input:* File Name, Batch Size, % Complete

*Actions:*
   - This will take a CSV file placed in the /bp2/scriptplan...###/data directory and load the device list specified
   - It expects two field in each row: DEVICE_HOST,VENDOR.
   - If the VENDOR is not provided, JUNIPER is assumed
   - It will launch the batch size number (default 10) charter.resourceTypes.DeviceOnboarder resources to on-board the devices into BPO
   - Once a certain percentage of these devices are complete/failed it will continue to on-board more until the file is exhaused.

#### tosca.resourceTypes.NetworkFunction
Input: Name, IP, SessionProfile

*Actions:*
   - None, this is the representation of a Device in the Blue Planet Market.
