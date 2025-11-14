====
Arda
====

Overview
--------

The 'Arda' microservice is an 'inventory microservice', meaning that it mediates connections between database
systems and presents an amazing RESTful API..


How to Install
--------------

Prerequisites:

- python 3.8
- git


Mac Steps:
----------

1. Clone the code repo from git into the directory of your choice.
    | ``$ git clone git@gitlab.spectrumflow.net:service-engineering-automation/sense/arda.git``
    |   or
    | ``$ git clone https://gitlab.spectrumflow.net/service-engineering-automation/sense/arda.git``
    |   depending on your local git setup

2. cd into the project root directory
    ``$ cd arda``

3. Create a virtual environment
    ``$ python3 -m venv arda_venv``

4. Activate your virtual environment
    ``$ source arda_venv/bin/activate``

5. Install the project requirements with pip
    | Upgrade pip
    | ``$ pip3 install --upgrade pip``

    | Install requirements
    | ``$ pip3 install -r requirements.txt``

6. Clone in common_sense submodule
    | ``$ git clone --recurse-submodules git@gitlab.spectrumflow.net:service-engineering-automation/sense/common_sense.git``
    |   or
    | ``$ git clone --recurse-submodules https://gitlab.spectrumflow.net/service-engineering-automation/sense/common_sense.git``
    |   depending on your local git setup

7. Activate the pre-commit hook
    ``$ pre-commit install``

    | To activate commit-msg pre-commit hook
    | ``$ pre-commit install --hook-type commit-msg``

8. Obtain the latest environment file from a team lead and place at top level of the project directory (same level as this README)


Windows Steps:
--------------

1. Clone the code repo from git into the directory of your choice
    | ``$ git clone git@gitlab.spectrumflow.net:service-engineering-automation/sense/arda.git``
    |   or
    | ``$ git clone https://gitlab.spectrumflow.net/service-engineering-automation/sense/arda.git``
    |   depending on your local git setup

2. cd into the project root directory
    ``$ cd arda``

3. Create a virtual environment
    ``$ py -m venv arda_venv``

4. Activate your virtual environment ( in Powershell or CMD)
    ``$ .\arda_venv\Scripts\activate``

5. Install the project requirements with pip
    | Upgrade pip
    | ``$ pip3 install --upgrade pip``

    | Install requirements
    | ``$ pip3 install -r requirements.txt``

6. Clone in common_sense submodule
    | ``$ git clone --recurse-submodules git@gitlab.spectrumflow.net:service-engineering-automation/sense/common_sense.git``
    |   or
    | ``$ git clone --recurse-submodules https://gitlab.spectrumflow.net/service-engineering-automation/sense/common_sense.git``
    |   depending on your local git setup

7. Activate the pre-commit hook
    ``$ pre-commit install``

    | To activate commit-msg pre-commit hook
    | ``$ pre-commit install --hook-type commit-msg``

    If you get an error upon trying your first commit that says "SSL certificate problem: self signed certificate in certificate chain", this step is needed:

    ``git config --global http.sslVerify false``

    Complete one commit so pre-commit can cache the Black repo locally. This commit doesn't need to be pushed to the repo. It can be done completely locally on a test branch which can be deleted afterwards. If you don't want that global setting to remain, you can change it back after.

    ``git config --global http.sslVerify true``

8. Obtain the latest environment file from a team lead and place at top level of the project directory (same level as this README)


How to Run
----------

1. Refer here for the steps to set up the app for debugging in VS Code
    `Local App Setup <https://chalk.charter.com/display/SESE/Gitlab+CI+Variables+-+Microservice+Credentials+and+DLL+Constants#GitlabCIVariablesMicroserviceCredentialsandDLLConstants-LocalAppSetup>`_

    If needed, reach out to a lead for assistance***


How to Run Tests
----------------

To run the test suite:
    ``$ pytest tests``

To run flake8 checks:
    ``$ pytest --flake8 arda_app``


Endpoints
---------

API endpoints as of Nov 8th 2023:

- **Circuits, Paths, Topologies**:

  - v1/assign_enni - POST - [Build_Circuit_Design] Assign ENNI
  - v1/assign_evc - POST - [Build_Circuit_Design] Assign EVC
  - v1/assign_gsip - POST - [Build_Circuit_Design] Assign GSIP
  - v1/assign_handoffs_and_uplinks - POST - Assign handoffs and uplinks
  - v1/assign_parent_paths - PUT - PE record management operations
  - v1/bandwidth_change - PUT - Upgrade or Downgrade Bandwidth
  - v1/build_circuit_design - POST - SEnSE intake service to build a circuit
  - v1/circuit_design - POST - SEnSE Circuit Design
  - v1/create_mtu_transport - POST - Create MTU transport build
  - v1/disconnect - POST - Validate properties and return back and success or failure
  - v1/exit_criteria - PUT - get exit criteria for CID
  - v1/isp_update_related_circuits - PUT - Assigns Transport Path to List of CIDs
  - v1/logical_change - PUT - Processes Logical Change Orders
  - v1/noc_analysis - GET - returns service information from Granite based on either TID or Circuit ID
  - v1/noc_analysis - POST - Creates a new circuit in Granite
  - v1/qc_transport_path - POST - Construct Transport path for a given Circuit and post in Granite
  - v1/service_product_eligibility - POST - Returns eligibility of the Build circuit order submitted
  - v1/serviceable_shelf - POST - Serviceable shelf - select the available handoff from CPE
  - v1/supported_product - POST - Service to complete circuit design build for received product
  - v1/update_path_status/<pathid>/status - PUT - Update the status of a circuit, write GSIP standard UDA values to circuit
  - v3/transport_path - POST - Create Transport Path
  - v3/transport_path - PUT - Assign Transports to a Circuit
  - v4/circuitpath - POST - Create a path

- **Shelves**:

  - v1/adva_rad_by_year - GET - return which vendor to design the next CPE as
  - v1/cpe_swap - POST - Performs Shelf Swap of CPE
  - v1/create_shelf - POST - Create device shelf

- **Customer**:

  - v4/customer - PUT - Find existing customer or create a new customer

- **Device**:

  - v1/device - GET - executes MDSO onboading and executes command for the hostname and parameter in URI args

- **IP addresses and VLANs**:

  - v1/ip_reclamation - POST - Reclaim a Subnet Block by deleting it from IPControl
  - v1/ip_reclamation/subnet - POST - Retrieve Subnet Block Data from IPControl
  - v1/ip_reservation - POST - Reserve an IP from IP Control
  - v1/ip_swip - POST - Perform IP SWIP for a circuit
  - v1/ip_swip/unswip - POST - Perform IP un-SWIP for a circuit to release its IPs
  - v1/ip_swip/whois - GET - Perform IP WHOIS lookup
  - v1/ip_swip/subnets - GET - Retrieve a circuit's IPv4 and IPv6 subnets from Granite
  - v1/ip_swip/records - GET - Retrieve an organization's net and customer records from ARIN
  - v1/reclaim_cpe_mgmt_ip - POST - Reclaim static Management IPs from IPControl
  - v1/vlan_reservation - POST - VLAN assignment management
  - v3/ip/static - POST - Perform Static IP Assignment for a circuit
  - v5/blacklist_check - GET - Check information for ip address

- **Site-related**:

  - v5/site - PUT - Find existing site or create a new site

- **App Health Monitoring**:

  - v1/health - GET - a static 200 OK returned from server for checking if the service is live

- **Remedy / Hub Optic**:

  - v1/isp_group - GET - GET ISP group using clli
  - v1/light_test_check - GET - Perform light test check and return port activation link
  - v1/optic_check_validation - POST - optic validation results
  - v2/remedy_ticket - POST - Create Remedy ticket and workorder
  - v2/remedy_ticket/disconnect - POST - Remedy Ticket Data for Customer Disconnect

- **Development / testing only**:

  - v1/mock/{file_name} - GET - Read a file with some fake json data (eg: eline.json) and return it
