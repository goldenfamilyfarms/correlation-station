import time
from datetime import date
import traceback
from .utilities.fortigateAPI import Fortigate
from .utilities.forticare3 import Forticare
from .utilities.forticloud import Forticloud


def onboard(
        serial, ip, key, description, forticare_api_id, forticare_api_password,
        forticare_client_id, forticloud_api_id, forticloud_api_password, forticloud_account,
        forticloud_password, logger, cloudkey=None, license=None):
    # This dict will keep track of status changes. Return this to the user.
    status = {
        'autoBackup': False,
        'cloudLicense': {
            'endDate': None,
            'key': None,
            'startDate': None,
            'supportType': None
        },
        'deviceClaimed': False,
        'management': False,
        'model': None,
        'serial': serial,
        'subaccount': {
            'name': None,
            'oid': None,
            'parentName': None,
            'parentOid': None
        },
        'warnings': []
    }

    # Login to Forticare (Fortinet Asset Management)
    forticare = Forticare(forticare_api_id, forticare_api_password, forticare_client_id, logger=logger)
    forticare.login()

    # Check if device is already registered, register if needed
    # If get_product_details() returns None, device is not yet registered
    # or there was some other failure.
    error1, error2, registration_response = "", "", ""
    device_register, error1 = forticare.get_product_details(serial)
    if device_register is None:
        device = [
            {
                'serialNumber': serial,
                'description': description,
                'isGovernment': False
            }
        ]
        registration_response = forticare.register_products(registrationUnits=device)
        device_register, error2 = forticare.get_product_details(serial)
    # Second check if device registration was successful. We don't want to
    # onboard a device to FortiCloud if not registered in Asset Management.
    if device_register is None:
        message = 'Device failed registration with asset management'
        logger.log_issue(
            external_message=message,
            internal_message=message,
            api_response=f"{error1} \n\n {error2} \n\n {registration_response}",
            code=2002,
            category=0
        )
        return False
    status.update({'model': device_register['assetDetails']['productModel']})
    status.update({'deviceClaimed': True})

    # Check device registration for active cloud licenses before applying any
    # additional licenses. Device may already have a license claimed or this
    # script may be run more than once on a single device.
    if license is not None:
        today = str(date.today())
        if device_register['assetDetails']['contracts'] is not None:
            for i in device_register['assetDetails']['contracts']:
                for j in i['terms']:
                    if j['supportType'] != 'FortiCloud Service':
                        continue
                    if j['endDate'][:11] > today:
                        status['cloudLicense']['endDate'] = j['endDate'][:10]
                        status['cloudLicense']['startDate'] = j['startDate'][:10]
                        status['cloudLicense']['supportType'] = j['supportType']
                        status['cloudLicense']['key'] = i['contractNumber']
                        break
                if status['cloudLicense']['endDate'] is not None:
                    break
            else:
                # Claim FortiCloud Service license
                payload = [
                    {
                        'serialNumber': serial,
                        'contractNumber': license,
                        'isGovernment': False,
                    }
                ]
                license_register = forticare.register_products(payload)
                if license_register is not None:
                    status['cloudLicense']['key'] = license
                    status['cloudLicense']['startDate'] = today
                    status['cloudLicense']['supportType'] = 'FortiCloud Service'
                else:
                    message = 'License registration failed'
                    logger.log_issue(
                        external_message=message,
                        internal_message=message,
                        api_response="",
                        code=2003,
                        category=0
                    )
        else:
            # Claim FortiCloud Service license
            payload = [
                {
                    'serialNumber': serial,
                    'contractNumber': license,
                    'isGovernment': False,
                }
            ]
            license_register = forticare.register_products(payload)
            if license_register is not None:
                status['cloudLicense']['key'] = license
                status['cloudLicense']['startDate'] = today
                status['cloudLicense']['supportType'] = 'FortiCloud Service'
            else:
                message = 'License registration failed'
                logger.log_issue(
                    external_message=message,
                    internal_message=message,
                    api_response="",
                    code=2003,
                    category=0
                )

    forticloud = Forticloud(
        forticloud_api_id, forticloud_api_password,
        forticloud_account, logger
    )

    # Check if device is already on FortiCloud, onboard if needed.
    cloud_status = forticloud.get_device(serial)
    if cloud_status is None:
        if cloudkey is not None:
            forticloud.add_device(cloudkey)
        else:
            try:
                fortigate = Fortigate(ip, key, logger)
                fortigate.get_system_status()
                if fortigate.serial == serial:
                    fortigate.forticloud_login(forticloud_account, forticloud_password)
                    fortigate.config_system_central_management()
                    fortigate.config_log_fortiguard_setting()
                else:
                    message = 'FortiGate serial number does not match the serial number provided'
                    logger.log_issue(
                        external_message=message,
                        internal_message=message,
                        api_response="",
                        code=2004,
                        category=0
                    )
                    status['warnings'].append(
                        'FortiGate serial number does not match the serial '
                        'number provided')
            except Exception:
                message = 'Exception occurred while trying to reach FortiGate'
                logger.log_issue(
                    external_message=message,
                    internal_message=message,
                    api_response="",
                    details=traceback.format_exc(),
                    code=2005,
                    category=0
                )
                status['warnings'].append('Unable to reach FortiGate')
        time.sleep(20)  # we give forticloud ~20 seconds to digest that the device was just onboarded
        cloud_status = forticloud.get_device(serial)
    else:
        logger.info("Device is already in forticloud portal")

    # Second check if cloud onboarding was successful. End if device is still
    # not seen on FortiCloud.
    if cloud_status is None:
        message = 'Cloud onboarding failed'
        logger.log_issue(
            external_message=message,
            internal_message=message,
            api_response="",
            details="cloud status is none",
            code=2005,
            category=0
        )
        return False
    return True
