# PORT ACTIVATION  
  
## Overview  
This Port Activation ResourceTypes provides a new capability to activate (enable) and/or terminate (disable) the port . As part of container deployment, the supporting resources and service templates are onboarded automatically into the BPO Market.  
  
## 1. Create Port Activation Instance/resource  
  
*Input:* Required Input: label, deviceName, portname, terminationTime, vendor  
  
We will get the below mentioned status from the activation process:  
- {'status': 'Ready to configure'} – If the device and port are available on the BP server.  
- {'status': 'Device not present'} – If the device is not present on the BP server.  
- {'status': 'Port not present on the device'} – If the port is not present on the device.  
  
*NOTE*: If the received status is  Device not present, then ST will automatically add/onboard the device.  
  
### 1.1 How to create the Port Activation resource  
  
#### 1.1.1 Get ProductId of the Port Activation resource types  
  
##### CURL command to get  the product -  
  
*curl -X GET "https://97.105.228.217/bpocore/market/api/v1/products?includeInactive=false&q=resourceTypeId%3Acharter.resourceTypes.PortActivation&offset=0&limit=1000" -H "accept: application/json" -H "Authorization: Bearer d10dd7deb818a9e2ee2e"*  
##### Request URL -  
  
*https://97.105.228.217/bpocore/market/api/v1/products?includeInactive=false&q=resourceTypeId%3Acharter.resourceTypes.PortActivation&offset=0&limit=1000*  
##### Server response -  
    {  
      "items": [   
        {  
           "id": "5b6d34ff-2738-47a0-bbed-c91f702a9322",  
           "resourceTypeId": "charter.resourceTypes.PortActivation",  
           "title": "Port Activation",  
           "active": true,  
           "domainId": "built-in",  
           "constraints": {},  
           "providerData": {  
              "template": "charter.serviceTemplates.PortActivation"  
           }  
        }  
      ],  
      "total": 67,  
      "offset": 0,  
      "limit": 1000  
    }  
#### 1.1.2 Create Port Activation Instance using the productId  
  
##### CURL command to create PortActivation instance -  
  
*curl -X POST "https://97.105.228.217/bpocore/market/api/v1/resources?validate=false" -H "accept: application/json" -H "Authorization: Bearer 0776c26ab0be6f52bd82" -H "Content-Type: application/json" -d "{ \"desiredOrchState\": \"active\", \"label\": \"test1\", \"autoClean\": false, \"reason\": \"string\", \"discovered\": false, \"properties\": { \"portname\":\"ge-0/0/5\",\"deviceName\":\"AUSDTXIR2CW.one.twcbiz.com\" }, \"productId\": \"5b6d34ff-2738-47a0-bbed-c91f702a9322\"}"*  
##### Request URL -  
  
*https://97.105.228.217/bpocore/market/api/v1/resources?validate=false*  
##### Server response -  
    {  
      "id": "5b76a014-4c5a-40ec-8c8f-32d410aaa9dc",  
      "label": "test1",  
      "resourceTypeId": "charter.resourceTypes.PortActivation",  
      "productId": "5b6d34ff-2738-47a0-bbed-c91f702a9322",  
      "tenantId": "c740f2cd-c59c-4e11-815b-5f1a4571389c",  
      "shared": false,  
      "properties": {  
        "deviceName": "AUSDTXIR2CW.one.twcbiz.com",  
        "portname": "ge-0/0/5",
        "vendor": "JUNIPER",
        "terminationTime": 30  
      },  
      "discovered": false,  
      "differences": [],  
      "desiredOrchState": "active",  
      "orchState": "requested",  
      "reason": "",  
      "tags": {},  
      "providerData": {},  
      "updatedAt": "2018-08-17T10:14:44.165Z",  
      "createdAt": "2018-08-17T10:14:44.165Z",  
      "autoClean": false  
    }  
# 2. Get Port Status  
  
Get the current state of the port. If the returned status from activation process is 'Ready to configure' , get the state of port else it will returned the status- 'Resource not in Ready to configure state, hence operation can not be executed'  
*Output:* status, adminstate, operationalstate  
  
### 2.1 Creating operation for getPortStatus  
  
##### CURL command to create operation for getPortStatus -  
  
*curl -X POST "https://97.105.228.217/bpocore/market/api/v1/resources/5b6d7e6c-d6a1-429a-92af-267383110dd5/operations" -H "accept: application/json" -H "Authorization: Bearer 132ca8706f17231adbc8" -H "Content-Type: application/json" -d "{ \"description\": \"string\", \"interface\": \"getPortStatus\", \"inputs\": { }, \"title\": \"string\"}"*  
##### Request URL -  
  
*https://97.105.228.217/bpocore/market/api/v1/resources/5b6d7e6c-d6a1-429a-92af-267383110dd5/operations*  
##### Server response -  
    {  
      "id": "5b7173ce-83cd-4b69-b0c3-29255f6e0484",  
      "resourceId": "5b6d7e6c-d6a1-429a-92af-267383110dd5",  
      "interface": "getPortStatus",  
      "title": "string",  
      "description": "string",  
      "inputs": {},  
      "outputs": {},  
      "state": "requested",  
      "reason": "",  
      "progress": [],  
      "providerData": {},  
      "createdAt": "2018-08-13T12:04:30.319Z",  
      "updatedAt": "2018-08-13T12:04:30.319Z",  
      "resourceStateConstraints": {},  
      "executionGroup": "lifecycle"  
    }  
### 2.2 getPortStatus using operationId and ResourceId  
  
##### CURL command to get the port status -  
  
*curl -X GET "https://97.105.228.217/bpocore/market/api/v1/resources/5b6d7e6c-d6a1-429a-92af-267383110dd5/operations/5b7173ce-83cd-4b69-b0c3-29255f6e0484" -H "accept: application/json" -H "Authorization: Bearer 132ca8706f17231adbc8"*  
##### Request URL -  
  
*https://97.105.228.217/bpocore/market/api/v1/resources/5b6d7e6c-d6a1-429a-92af-267383110dd5/operations/5b7173ce-83cd-4b69-b0c3-29255f6e0484*  
##### Server response -  
    {  
      "id": "5b7173ce-83cd-4b69-b0c3-29255f6e0484",  
      "resourceId": "5b6d7e6c-d6a1-429a-92af-267383110dd5",  
      "interface": "getPortStatus",  
      "title": "string",  
      "description": "string",  
      "inputs": {},  
      "outputs": {  
        "status": "Successfully able to retreive port state",  
        "adminstate": "up",  
        "operstate": "down"  
      },  
      "state": "successful",  
      "reason": "",  
      "progress": [],  
      "providerData": {},  
      "createdAt": "2018-08-13T12:04:30.319Z",  
      "updatedAt": "2018-08-13T12:04:40.437Z",  
      "resourceStateConstraints": {},  
      "executionGroup": "lifecycle"  
    }  
# 3. Set Port Status  
  
*Input:* reqdstate  
*Output:* status  
Set the port state based on the port Activation instance status. If the returned status from activation process is 'Ready to configure' , this will set the state of port given by the user else it will returned the status- 'Resource not in Ready to configure state, hence operation can not be executed'  
  
### 3.1 Create operation for setPortStatus  
  
##### CURL command to create operation for setPortStatus -  
  
*curl -X POST "https://97.105.228.217/bpocore/market/api/v1/resources/5b6d7e6c-d6a1-429a-92af-267383110dd5/operations" -H "accept: application/json" -H "Authorization: Bearer 132ca8706f17231adbc8" -H "Content-Type: application/json" -d "{ \"interface\": \"setPortStatus\", \"inputs\": { \"reqdstate\": \"down\" }}"*  
##### Request URL -  
  
*https://97.105.228.217/bpocore/market/api/v1/resources/5b6d7e6c-d6a1-429a-92af-267383110dd5/operations*  
##### Server response -  
    {  
      "id": "5b718c3b-551a-44cb-a9e5-5b5169fb1fd4",  
      "resourceId": "5b6d7e6c-d6a1-429a-92af-267383110dd5",  
      "interface": "setPortStatus",  
      "inputs": {  
        "reqdstate": "down"  
      },  
      "outputs": {},  
      "state": "requested",  
      "reason": "",  
      "progress": [],  
      "providerData": {},  
      "createdAt": "2018-08-13T13:48:43.655Z",  
      "updatedAt": "2018-08-13T13:48:43.655Z",  
      "resourceStateConstraints": {},  
      "executionGroup": "lifecycle"  
    }  
### 3.2 Get the details of the operation using ResourceId and operationId

We can get the details of a specific operation created (in 3.1) using ResourceId("resourceId": "5b6d7e6c-d6a1-429a-92af-267383110dd5" from 3.1) and operationId("id": "5b718c3b-551a-44cb-a9e5-5b5169fb1fd4" from 3.1)
  
##### CURL command to get details of a specific operation for a given resource -
  
*curl -X GET "https://97.105.228.217/bpocore/market/api/v1/resources/5b6d7e6c-d6a1-429a-92af-267383110dd5/operations/5b718c3b-551a-44cb-a9e5-5b5169fb1fd4" -H "accept: application/json" -H "Authorization: Bearer 132ca8706f17231adbc8"*
##### Request URL -  
  
*https://97.105.228.217/bpocore/market/api/v1/resources/5b6d7e6c-d6a1-429a-92af-267383110dd5/operations/5b718c3b-551a-44cb-a9e5-5b5169fb1fd4*  
##### Server response -  
  
    {  
      "id": "5b718c3b-551a-44cb-a9e5-5b5169fb1fd4",  
      "resourceId": "5b6d7e6c-d6a1-429a-92af-267383110dd5",  
      "interface": "setPortStatus",  
      "inputs": {  
        "reqdstate": "down"  
      },  
      "outputs": {  
        "status": "Successfully triggered patch operation for adminstate change"  
      },  
      "state": "successful",  
      "reason": "",  
      "progress": [],  
      "providerData": {},  
      "createdAt": "2018-08-13T13:48:43.655Z",  
      "updatedAt": "2018-08-13T13:49:28.887Z",  
      "resourceStateConstraints": {},  
      "executionGroup": "lifecycle"  
    }  
## 4. Termination  
Based on the termination time provided during the Port Activation resource creation, the port will be terminated/disabled.  
While enabling the port, scheduler resource will be created internally which will schedule the termination of port based on the terminationTime. After completion of given terminationTime, terminate will be invoked and disable the port.After completion of port disabling the Port Activation and scheduler resource will be deleted.  
  
*Note:* 30 min is the default value for terminationTime, we can change the the value based on user requirement.