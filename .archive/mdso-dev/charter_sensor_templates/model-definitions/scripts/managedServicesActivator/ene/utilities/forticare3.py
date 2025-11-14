import requests
import requests.packages.urllib3
from time import sleep

requests.packages.urllib3.disable_warnings()

'''
This module is used to interact with the FortiCare REST API V3.

https://fndn.fortinet.net/index.php?/fortiapi/55-foricare-registration/648/
https://docs.fortinet.com/document/forticloud/21.3.0/identity-access-management-iam/19322/accessing-fortiapis#Accessing_FortiAPIs

Limits and Quotas
    - Maximum 100 calls per minute
    - Maximum 1000 calls per hour
    - Maximum 10 errors per hour
    - Maximum number of units per batch registration is 10
    - Maximum number of errors allowed per batch registration is 5
'''


class Forticare:
    def __init__(self, key, password, client_id, logger):
        logger.info("====================================================================")
        logger.info(f"instantiating forticare object product k={key} | p={password} | cid=assetmanagement")
        logger.info("====================================================================")
        self.logger = logger if logger else None  # todo fix
        self.url = 'https://support.fortinet.com/ES/api/registration/v3'
        self.key = key
        self.password = password
        self.client_id = "assetmanagement"
        self.token = None
        self.refresh_token = None
        self.expires_in = None
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": 'Bearer {}'.format(self.token)
        }

    def login(self):
        '''
        ------------------------------------------------------------------------
        Request OAuth access token
        ------------------------------------------------------------------------
        username:  (string) API key

        password:  (string) API user password

        client_id:  (string) clientId for Asset Managment CLoud:assetmanagment

        grant_type:  (string)
        example:  password
        ------------------------------------------------------------------------
        Response
        ------------------------------------------------------------------------
        {
            'access_token':  'paLreKW6YGDfgSUfreEH90UcC1915v3',
            'expires_in': 14400,
            'message': 'sucessfully authenticated',
            'refresh_token': 'WpD0HVYUdshsiW1MBR0Q6uUoV2TGUIa',
            'scope': 'read write',
            'status': 'success',
            'token_type': 'Bearer'
        }
        '''
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        payload = {
            'username': self.key,
            'password': self.password,
            'client_id': self.client_id,
            'grant_type': 'password'
        }

        response, error = api_call(
            'https://customerapiauth.fortinet.com/api/v1/oauth/token/',
            headers=headers, action='POST', payload=payload, attempts=1, logger=self.logger)
        if response is not None:
            self.token = response['access_token']
            self.refresh_token = response['refresh_token']
            self.headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": 'Bearer {}'.format(self.token)
            }
        return response

    def refresh_token(self):
        '''
        ------------------------------------------------------------------------
        Refresh OAuth access token
        ------------------------------------------------------------------------
        client_id:  (string) clientId for Asset Managment CLoud:assetmanagment

        grant_type:  (string)
        example:  password

        refresh_token:  (string) API user refresh token
        example:  WpD0HVYUdshsiW1MBR0Q6uUoV2TGUIa

        ------------------------------------------------------------------------
        Response
        ------------------------------------------------------------------------
        {
            'access_token':  'qeOreKW6YGDfgSUfreEH90UCc1915v3',
            'expires_in': 14400,
            'message': 'Token has been refreshed successfully',
            'refresh_token': 'xpD0HVYUdshsiW1MBR0Q6uUoV2TDSa',
            'scope': 'read write',
            'status': 'success',
            'token_type': 'Bearer'
        }
        '''

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        payload = {
            'client_id': self.client_id,
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token
        }

        response, error = api_call(
            'https://customerapiauth.fortinet.com/api/v1/oauth/token',
            headers=headers, action='POST', payload=payload, attempts=1, logger=self.logger)
        if response is not None:
            self.token = response['access_token']
            self.refresh_token = response['refresh_token']
            self.headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": 'Bearer {}'.format(self.token)
            }
        return response

    '''
    ###################
    ##    LICENSE    ##
    ###################
    '''

    # Register a license based on SN or license registration code
    # If SN field is empty, a virtual product will be created for the registered license
    def register_license(
            self, serialNumber, description,
            additionalInfo='', isGovernment=False,
            licenseRegistrationCode=None):
        '''
        ------------------------------------------------------------------------
        Used for registering license
        ------------------------------------------------------------------------
        serialNumber:  (string) Optional product serial number, if this field
        is not empty, the license will be registered under it, otherwise a
        virtual product will be created for the registered license (if applicable)

        licenseRegistrationCode*:  (string) License registration code
        example: K06V2-U795H-9PKR7-2TXNM-V8GL6B

        description:  (string) Optional, the description for the new product
        example: Backup device

        additionalInfo:  (string) Store extra info for certain product registration,
        for example system ID, IP address etc.
        example: 121.24.56.198

        isGovernment:  (boolean) Product will be used for government or not
        example: true

        ------------------------------------------------------------------------
        Response
        ------------------------------------------------------------------------
        {
            "token": "WIvPXcYH1gTphtjc6nVGkFxL3JjNqX",
            "version": "3.0",
            "status": 0,
            "message": "",
            "build": "1.0.0",
            "error": "",
            "assetDetails": {
            "productModel": "FortiGate VM 2 CPU",
            "serialNumber": "FGT90D1234567890",
            "description": "Backup device",
            "isDecommissioned": false,
            "partner": "Fortinet Canada Ltd.",
            "registrationDate": "2021-10-21T10:36:42",
            "warrantySupports": null,
            "assetGroups": null,
            "contracts": null,
            "productModelEoR": null,
            "productModelEoS": null,
            "license": [
                {
                    "licenseNumber": "FGVM0099483",
                    "licenseSKU": "FG-VM00",
                    "licenseType": "Standard",
                    "experiationDate": "2019-01-20T10:11:11-8:00",
                    "licenseFile": "QAAAAIy8mCwzkPNx2ajP2a2Ynkvm5bhp0CWiKdkbciVL/iDXiYbFGk+dvCFXgYq1QUrID356ngZ3 iSGROLXP+H1hlo9gAAAAFhYJLHAH9w+vXVMXpo/UhGV4e/1pvlhjqXJrmLjP1WGLKf5A9mx8aTOr 5+cgqh2nkFEsn3HBRu9Tum3hYULVYJFoqg8qM/amKjnwWfRbjgOeZJqHp44HvCznvhnQIa1f"
                }
            ],
            "entitlements": [
                {
                    "level": 6,
                    "levelDesc": "Web/Online",
                    "type": 20,
                    "typeDesc": "Enterprise Technical Support",
                    "startDate": "2018-09-10T11:20:11-08:00",
                    "endDate": "2019-09-10T11:20:11-08:00"
                }
            ],
            "location": null
            }
        }
        '''
        payload = {
            'serialNumber': serialNumber,
            'licenseRegistrationCode': licenseRegistrationCode,
            'description': description,
            'additionalInfo': additionalInfo,
            'isGovernment': isGovernment
        }

        response, error = api_call(
            '{}/licenses/register'.format(self.url), headers=self.headers,
            action='POST', payload=payload, attempts=1, logger=self.logger)
        return response

    # Download license key file
    def download_license(self, serialNumber):
        '''
        ------------------------------------------------------------------------
        Used for license key file download
        ------------------------------------------------------------------------
        serialNumber*:  (string) Product serial number
        example: FGT90D1234567890

        ------------------------------------------------------------------------
        Response
        ------------------------------------------------------------------------
        {
            "token": "WIvPXcYH1gTphtjc6nVGkFxL3JjNqX",
            "version": "3.0",
            "status": 0,
            "message": "",
            "build": "1.0.0",
            "error": "",
            "serialNumber": "FGT90D1234567890",
            "licenseFile": "QAAAAIy8mCwzkPNx2ajP2a2Ynkvm5bhp0CWiKdkbciVL/iDXiYbFGk+dvCFXgYq1QUrID356ngZ3 iSGROLXP+H1hlo9gAAAAFhYJLHAH9w+vXVMXpo/UhGV4e/1pvlhjqXJrmLjP1WGLKf5A9mx8aTOr 5+cgqh2nkFEsn3HBRu9Tum3hYULVYJFoqg8qM/amKjnwWfRbjgOeZJqHp44HvCznvhnQIa1f"
        }
        '''
        payload = {
            'serialNumber': serialNumber,
        }

        response, error = api_call(
            '{}/licenses/download'.format(self.url), headers=self.headers,
            action='POST', payload=payload, attempts=1, logger=self.logger)
        return response

    '''
    ###################
    ##    PRODUCT    ##
    ###################
    '''

    # Returns product list based on product SN search pattern or
    # support package expiration date
    # Expire date given in ISO 8601 format, Example:  2019-01-20T10:11:11-8:00
    def get_products_list(
            self, serialNumber, expireBefore=None,
            pageNumber=1):
        '''
        ------------------------------------------------------------------------
        Returns product list based on product SN search pattern or support
        package expiration date
        ------------------------------------------------------------------------
        serialNumber:  (string) Serial number or serial number search pattern
        example: FGT90D1234567890

        expireBefore:  (string) Date time in ISO 8601 format
        example: 2019-01-20T10:11:11-8:00

        pageNumber:  (integer) Pagination control, default = 1 with page
        size = 25 example: 1

        ------------------------------------------------------------------------
        Response
        ------------------------------------------------------------------------
        {
            "token": "WIvPXcYH1gTphtjc6nVGkFxL3JjNqX",
            "version": "3.0",
            "status": 0,
            "message": "",
            "build": "1.0.0",
            "error": "",
            "assets": [
                {
                    "serialNumber": "FGT90D1234567890",
                    "registrationDate": "2019-01-20T10:11:11-8:00",
                    "description": "Backup device",
                    "isDecommissioned": false,
                    "productModel": "FortiWiFi 50B",
                    "productModelEoR": "2022-05-08T00:00:00",
                    "productModelEoS": "2023-05-08T00:00:00",
                    "entitlements": [
                        {
                            "level": 6,
                            "levelDesc": "Web/Online",
                            "type": 20,
                            "typeDesc": "Enterprise Technical Support",
                            "startDate": "2018-09-10T11:20:11-08:00",
                            "endDate": "2019-09-10T11:20:11-08:00"
                        }
                    ],
                    "assetGroups": [
                        {
                            "assetGroupId": 12,
                            "assetGroup": "Asset Group #6"
                        }
                    ],
                    "warrantySupports": [
                        {
                            "level": 6,
                            "levelDesc": "Web/Online",
                            "type": 20,
                            "typeDesc": "Enterprise Technical Support",
                            "startDate": "2018-09-10T11:20:11-08:00",
                            "endDate": "2019-09-10T11:20:11-08:00"
                        }
                    ],
                    "trialTypes": [
                        "Antivirus",
                        "Web Filtering",
                        "AntiSpam"
                    ]
                }
            ]
        }
        '''
        payload = {
            'serialNumber': serialNumber,
            'expireBefore': expireBefore,
            'pageNumber': pageNumber
        }

        response, error = api_call(
            '{}/products/list'.format(self.url), headers=self.headers, action='POST',
            payload=payload, attempts=1, logger=self.logger)
        return response

    # Register multiple products and contracts in one request
    def register_products(
            self, registrationUnits=None, locations=None):
        '''
        ------------------------------------------------------------------------
        Register multiple products/contracts in one request
        ------------------------------------------------------------------------
        Units must be a list with each entry in the following format:
                {
                    'serialNumber': 'FGT90D1234567890',
                    'contractNumber': '2121DJ8902',
                    'description': 'Backup device',
                    'assetGroupIds': [6, 12, 18],
                    'replacedSerialNumber': 'FGT90D9876543210',
                    'additionalInfo': '121.24.56.198',
                    'cloudKey': 80X4LSN3,
                    'isGovernment': True,
                    'location': {'ref': '#/locations/0'}
                }

        Locations must be a list with each entry in the following format:
                {
                    "company": "Test Company Inc",
                    "address": "1234 Wall Street",
                    "city": "Sunnyvale",
                    "stateOrProvince": "CA",
                    "countryCode": "US",
                    "postalCode": "34510",
                    "email": "test@testcompany.com",
                    "phone": "3151231234",
                    "fax": "3151231235"
                }

        ------------------------------------------------------------------------
        Response
        ------------------------------------------------------------------------
        {
            "token": "WIvPXcYH1gTphtjc6nVGkFxL3JjNqX",
            "version": "3.0",
            "status": 0,
            "message": "",
            "build": "1.0.0",
            "error": "",
            "assets": [
                {
                    "serialNumber": "FGT90D1234567890",
                    "registrationDate": "2019-01-20T10:11:11-8:00",
                    "description": "Backup device",
                    "isDecommissioned": false,
                    "productModel": "FortiWiFi 50B",
                    "productModelEoR": "2022-05-08T00:00:00",
                    "productModelEoS": "2023-05-08T00:00:00",
                    "entitlements": [
                        {
                            "level": 6,
                            "levelDesc": "Web/Online",
                            "type": 20,
                            "typeDesc": "Enterprise Technical Support",
                            "startDate": "2018-09-10T11:20:11-08:00",
                            "endDate": "2019-09-10T11:20:11-08:00"
                        }
                    ],
                    "assetGroups": [
                        {
                            "assetGroupId": 12,
                            "assetGroup": "Asset Group #6"
                        }
                    ],
                    "warrantySupports": [
                        {
                            "level": 6,
                            "levelDesc": "Web/Online",
                            "type": 20,
                            "typeDesc": "Enterprise Technical Support",
                            "startDate": "2018-09-10T11:20:11-08:00",
                            "endDate": "2019-09-10T11:20:11-08:00"
                        }
                    ],
                    "trialTypes": [
                        "Antivirus",
                        "Web Filtering",
                        "AntiSpam"
                    ]
                }
            ]
        }
        '''

        payload = {
            'RegistrationUnits': registrationUnits,
            'locations': locations
        }

        response, error = api_call(
            '{}/products/register'.format(self.url), headers=self.headers,
            action='POST', payload=payload, attempts=1, logger=self.logger)
        self.logger.debug("--------------------------------- response from device register is:")
        self.logger.debug(response)
        self.logger.debug("--------------------------------- error from device register is:")
        self.logger.debug(error)

        return response

    # Update desciption of a product.  Search by SN.
    def update_product_description(
            self, serialNumber, description):
        '''
        ------------------------------------------------------------------------
        Update description of a product using serial number
        ------------------------------------------------------------------------
        serialNumber*:  (string) Product serial number
        example: FGT90D1234567890

        description:  (string) Description for product
        example: New description for the product

        ------------------------------------------------------------------------
        Response
        ------------------------------------------------------------------------
        {
            "token": "WIvPXcYH1gTphtjc6nVGkFxL3JjNqX",
            "version": "3.0",
            "status": 0,
            "message": "",
            "build": "1.0.0",
            "error": ""
        }
        '''
        payload = {
            'serialNumber': serialNumber,
            'description': description
        }

        response, error = api_call(
            '{}/products/description'.format(self.url), headers=self.headers,
            action='POST', payload=payload, attempts=1, logger=self.logger)
        return response

    def get_product_details(self, serialNumber):
        '''
        ------------------------------------------------------------------------
        Returns product detailed information, including active support coverage
        and associated licenses
        ------------------------------------------------------------------------
        serialNumber*:  (string) Serial number
        example: FGT90D1234567890

        ------------------------------------------------------------------------
        Response
        ------------------------------------------------------------------------
        {
            "token": "WIvPXcYH1gTphtjc6nVGkFxL3JjNqX",
            "version": "3.0",
            "status": 0,
            "message": "",
            "build": "1.0.0",
            "error": "",
            "assetDetails": {
                "productModel": "FortiGate VM 2 CPU",
                "productModelEoR": "2022-05-08T00:00:00",
                "productModelEoS": "2023-05-08T00:00:00",
                "serialNumber": "FGT90D1234567890",
                "description": "Backup device",
                "partner": "Fortinet Canada Ltd.",
                "licenses": [
                    {
                        "licenseNumber": "FGVM0099483",
                        "licenseSKU": "FG-VM00",
                        "licenseType": "Standard",
                        "experiationDate": "2019-01-20T10:11:11-8:00"
                    }
                ],
                "entitlements": [
                    {
                        "level": 6,
                        "levelDesc": "Web/Online",
                        "type": 20,
                        "typeDesc": "Enterprise Technical Support",
                        "startDate": "2018-09-10T11:20:11-08:00",
                        "endDate": "2019-09-10T11:20:11-08:00"
                    }
                ]
            }
        }
        '''
        payload = {
            'serialNumber': serialNumber,
        }
        # https://community.fortinet.com/t5/FortiCloud-Products/Technical-Tip-API-how-to-retrieve-list-of-registered-units-for/ta-p/194760
        response, error = api_call(
            f'{self.url}/products/details', headers=self.headers,
            action='POST', payload=payload, attempts=1, logger=self.logger)
        return response, error

    def update_product_location(self, serialNumber, location=None):
        '''
        ------------------------------------------------------------------------
        Update or delete (pass null as parameter) location of a product using
        serial number
        ------------------------------------------------------------------------
        serialNumber*:  (string) Product serial number
        example: FGT90D1234567890

        location:  (dictionary): Use the following format:
            {
                "company": "Test Company Inc",
                "address": "1234 Wall Street",
                "city": "Sunnyvale",
                "stateOrProvince": "CA",
                "countryCode": "US",
                "postalCode": "34510",
                "email": "test@testcompany.com",
                "phone": "3151231234",
                "fax": "3151231235"
            }

        ------------------------------------------------------------------------
        Response
        ------------------------------------------------------------------------
        {
            "token": "WIvPXcYH1gTphtjc6nVGkFxL3JjNqX",
            "version": "3.0",
            "status": 0,
            "message": "",
            "build": "1.0.0",
            "error": ""
        }
        '''
        payload = {
            'serialNumber': serialNumber,
            'location': location
        }

        response, error = api_call(
            '{}/products/location'.format(self.url), headers=self.headers,
            action='POST', payload=payload, attempts=1, logger=self.logger)
        return response

    '''
    ###################
    ##    SERVICE    ##
    ###################
    '''

    def register_services(
            self, contractNumber, description,
            additionalInfo='', isGovernment=False):
        '''
        ------------------------------------------------------------------------
        Register a subscription contract (e.g. VM-S) to generate serial number
        ------------------------------------------------------------------------
        contractNumber*:  (string) Contract number to register
        example: 2121DJ8902

        description:  (string) Set product description during registration
        process example: Backup device

        additionalInfo:  (string) Store extra info for certain product
        registration, for example system ID, IP address etc.
        example: IP: 121.24.56.198

        isGovernment:  (boolean) Whether the product will be used for government
        or not example: true

        ------------------------------------------------------------------------
        Response
        ------------------------------------------------------------------------
        {
            "token": "WIvPXcYH1gTphtjc6nVGkFxL3JjNqX",
            "version": "3.0",
            "status": 0,
            "message": "",
            "build": "1.0.0",
            "error": "",
            "assetDetails": {
                "serialNumber": "FGVMSLTM20000179",
                "registrationDate": "2019-01-20T10:11:11-8:00",
                "description": "Backup device",
                "isDecommissioned": false,
                "productModel": null,
                "productModelEoR": null,
                "productModelEoS": null,
                "warrantySupports": null,
                "assetGroups": null,
                "entitlements": [
                    {
                        "level": 6,
                        "levelDesc": "Web/Online",
                        "type": 20,
                        "typeDesc": "Enterprise Technical Support",
                        "startDate": "2018-09-10T11:20:11-08:00",
                        "endDate": "2019-09-10T11:20:11-08:00"
                    }
                ],
                "partner": "Fortinet Canada Ltd.",
                "licenses": [
                    {
                        "licenseNumber": "FGVM0099483",
                        "licenseSKU": "FG-VM00",
                        "licenseType": "Standard",
                        "experiationDate": "2019-01-20T10:11:11-8:00"
                    }
                ],
                "contracts": null,
                "location": null
            }
        }
        '''
        payload = {
            'contractNumber': contractNumber,
            'description': description,
            'additionalInfo': additionalInfo,
            'isGovernment': isGovernment
        }

        response, error = api_call(
            '{}/services/register'.format(self.url), headers=self.headers,
            action='POST', payload=payload, attempts=1, logger=self.logger)
        return response


def api_call(url, action="GET", payload=None, timeout=10, attempts=3,
             verify=False, headers=None, logger=None):
    """
    Basic wrapper for API calls. Parameters:
    - url: API-specific part of URL (prefixed with $base_url)
    - action: HTTP verb: GET/POST/DELETE etc.
    - timeout: seconds before request timeout
    - attempts: max number of requests sent
    - json: data for PUT/POST calls
    Return: API response results
    """
    if headers is None:
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "deflate",
            "Content-Type": "application/json",
        }

    tries = 0
    while (tries < attempts):
        tries += 1
        try:
            response = requests.request(
                method=action,
                url=url,
                headers=headers,
                json=payload,
                timeout=timeout,
                verify=verify
            )
            if response.ok:
                if response.text:
                    return response.json(), None

            elif response.status_code == 400:
                print('Bad Request for url')
                break

            elif response.status_code == 401:
                print('Forbidden: unauthenticated')
                break

            elif response.status_code == 403:
                print('Forbidden: unauthorized')
                break

            elif response.status_code == 404:
                print('Not found')
                break

            elif response.status_code == 405:
                print('Method not allowed')
                break

            elif response.status_code == 429:
                try:
                    retry_after = int(response.headers.get('Retry-After'))
                except Exception:
                    retry_after = 1
                print("Retry after {} seconds".format(retry_after))
                sleep(retry_after)
                continue

            elif response.status_code == 500:
                print('Internal Server Error')
                break

            else:
                print("HTTP error: {}".format(response.status_code))
                response.raise_for_status()

        # if timeout error, retry. If any other error, leave it unhandled
        except requests.exceptions.ConnectTimeout:
            print("Timeout, retry")
            continue

        except requests.exceptions.ReadTimeout:
            print('Timeout, retry')
            continue

        except requests.exceptions.ConnectionError:
            print('Failed to establish a new connection')
            return None

    # return "None" if unsuccessful after all attempts
    print("Unable to get any response\n")
    try:
        return None, response.text
    except Exception:
        return None, None
