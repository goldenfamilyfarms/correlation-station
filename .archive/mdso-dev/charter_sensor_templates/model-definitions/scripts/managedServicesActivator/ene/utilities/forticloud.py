from time import sleep

import requests
import requests.packages.urllib3
from requests.exceptions import (
    ConnectionError, ConnectTimeout, HTTPError, ReadTimeout)

requests.packages.urllib3.disable_warnings()

'''
This module provides an easy way to interact with the FortiCloud REST API.

To access any FortiGate cloud API, a client program must send HTTPS GET/POST
request to https://www.forticloud.com/<api_path>

https://fndn.fortinet.net/index.php?/fortiapi/364-fortigate-cloud/392/
https://docs.fortinet.com/document/forticloud/21.3.0/identity-access-management-iam/19322/accessing-fortiapis#Accessing_FortiAPIs

Limits and Quotas
    - 100 calls/sec
    - 15 errors/min
'''


class Forticloud:
    def __init__(
            self,
            api_key,
            api_password,
            account,
            logger
    ):
        self.account = account
        self.api_client_id = "fortigatecloud"
        self.api_key = api_key
        self.api_password = api_password
        self.expires_in = None
        self.errors = 0
        self.logger = logger
        self.refresh_token = None
        self.token = None
        self.url = 'https://api.fortigate.forticloud.com/forticloudapi'

    def get_token(self):
        url = 'https://customerapiauth.fortinet.com/api/v1/oauth/token/'
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "deflate",
            "Content-Type": "application/json"
        }
        payload = {
            'username': self.api_key,
            'password': self.api_password,
            'client_id': self.api_client_id,
            'grant_type': 'password'
        }
        if self.errors >= 5:
            self.logger.warning(
                '>> request not sent, FortiCloud errors too high')
            return None
        self.logger.info('> {} | POST'.format(url))

        try:
            response = requests.post(
                url=url, headers=headers, json=payload, timeout=(5, 10))
        except (ConnectTimeout, ReadTimeout):
            self.logger.warning('>> Timeout')
            return None
        except (ConnectionError, HTTPError):
            self.logger.warning('>> Failed to establish a new connection')
            return None

        if response.ok:
            self.logger.info('>> Response: POST {} - {}'.format(
                response.status_code, response.reason))
            self.token = response.json()['access_token']
            self.expires_in = response.json()['expires_in']
            self.refresh_token = response.json()['refresh_token']
            return response.json()
        # Handle expected server error codes
        elif response.status_code in (
                400, 401, 403, 404, 405, 413, 424, 429, 500):
            self.logger.warning('>> Response: POST {} - {}'.format(
                response.status_code, response.reason))
            self.errors += 1
            return None
        # Catch all
        else:
            self.logger.warning('>> Response: {} {} - {}'.format(
                "post", response.status_code, response.reason))
            response.raise_for_status()
            return None

    def refresh_token(self):
        url = 'https://customerapiauth.fortinet.com/api/v1/oauth/token'
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "deflate",
            "Content-Type": "application/json"
        }
        payload = {
            'client_id': self.api_client_id,
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token
        }
        if self.errors >= 5:
            self.logger.warning(
                '>> request not sent, FortiCloud errors too high')
            return None
        self.logger.info('> {} | POST'.format(url))

        try:
            response = requests.post(
                url=url, headers=headers, json=payload, timeout=(5, 10))
        except (ConnectTimeout, ReadTimeout):
            self.logger.warning('>> Timeout')
            return None
        except (ConnectionError, HTTPError):
            self.logger.warning('>> Failed to establish a new connection')
            return None

        if response.ok:
            self.logger.info('>> Response: POST {} - {}'.format(
                response.status_code, response.reason))
            self.token = response.json()['access_token']
            self.expires_in = response.json()['expires_in']
            self.refresh_token = response.json()['refresh_token']
            return response.json()
        # Handle expected server error codes
        elif response.status_code in (
                400, 401, 403, 404, 405, 413, 424, 429, 500):
            self.logger.warning('>> Response: POST {} - {}'.format(
                response.status_code, response.reason))
            self.errors += 1
            return None
        # Catch all
        else:
            self.logger.warning('>> Response: {} {} - {}'.format(
                "post", response.status_code, response.reason))
            response.raise_for_status()
            return None

    def logout(self, expires_in=0):
        payload = {
            'access_token': self.token,
            'expires_in': expires_in
        }
        response = self.send_request(
            '{}/v1/auth/invalidate_token'.format(self.url), action='POST',
            payload=payload, attempts=1, status_only=True)
        self.token = None
        self.expires_in = None
        self.refresh_token = None
        return response

    def change_account(self, account):
        payload = {
            'accountId': account
        }
        response = self.send_request(
            '{}/v1/auth/account'.format(self.url), action='POST',
            payload=payload, attempts=1, status_only=True)
        return response

    def get_device(self, serial):
        response = self.send_request(
            '{}/v1/devices/{}'.format(self.url, serial))
        return response

    def get_devices(self, limit=100, offset=0, sort=False, timeout=(10, 20)):
        params = {
            'limit': str(limit),
            'offset': str(offset),
        }
        if sort:
            params['sort'] = 'true'
        response = self.send_request(
            '{}/v1/devices'.format(self.url), params=params, timeout=timeout)
        if response is not None:
            self.devices = response
        return response

    def add_device(self, cloudkey):
        self.logger.info("====================================================================")
        self.logger.info("onboarding device with cloudkey")
        self.logger.info("====================================================================")
        payload = {
            'deviceKey': cloudkey
        }
        response = self.send_request(
            '{}/v1/devices'.format(self.url), action='POST', payload=payload,
            attempts=1)
        return response

    def enable_management(
            self, serial, username=None, password=None, management=True,
            forcePasswordChange=False):
        '''
        Enable / disable FortiGate cloud management. Must provide a FortiGate's
        administrator credentials to enable cloud management.

        ------------------------------------------------------------------------
        Arguments
        ---------
        serial: (str)  FortiGate's serial number

        username: (str)  FortiGate administrator's username.  Must use an
            administrator account with super_user permissions.

        password: (str)  FortiGate administrator's password.  Must use an
            administrator account with super_user permissions.

        management: (bool)  Enable / disable cloud management feature.

        forcePasswordChange: (bool)  Force administrator to change password on
            next login.

        ------------------------------------------------------------------------
        Response
        --------
        None
        '''
        payload = {
            'management': management,
            'username': username,
            'password': password,
            'forcePasswordChange': forcePasswordChange
        }
        response = self.send_request(
            '{}/v1/devices/{}/management'.format(self.url, serial),
            action='PUT', payload=payload, attempts=1, status_only=True)
        return response

    def get_report_schedules(self, serial):
        response = self.send_request(
            '{}/v1/devices/{}/reportschedules'.format(self.url, serial))
        if response is not None:
            self.devices = response['results']
        return response

    def update_report_schedule(
            self, serial, organization_id, config_oid, schedule_type,
            email=None, vdom='root'):
        email_flag = True if email is not None else False
        payload = {
            'oid': organization_id,
            'configOid': config_oid,
            'scheduleType': schedule_type,
            'vdom': vdom,
            'email': email,
            'emailFlag': email_flag
        }
        response = self.send_request(
            '{}/v1/devices/{}/reportschedules'.format(self.url, serial),
            action='POST', payload=payload, attempts=1)
        return response

    def get_report_schedule(self, serial, organization_id):
        response = self.send_request(
            '{}/v1/devices/{}/reportschedules/{}'.format(
                self.url, serial, organization_id))
        return response

    def delete_report_schedule(self, serial, organization_id):
        response = self.send_request(
            '{}/v1/devices/{}/reportschedules/{}'.format(
                self.url, serial, organization_id),
            action='DELETE', attempts=1, status_only=True)
        return response

    def get_backup_setting(self, serial):
        response = self.send_request(
            '{}/v1/devices/{}/configbackups/setting'.format(self.url, serial))
        return response

    def update_backup_setting(
            self, serial, backup='PERSESSION', email=None, enable=True,
            language='en'):
        alert = True if email is not None else False
        payload = {
            'enable': enable,
            'backupOption': backup,
            'alert': alert,
            'alertLang': language,
            'alertEmails': email
        }
        response = self.send_request(
            '{}/v1/devices/{}/configbackups/setting'.format(self.url, serial),
            action='PUT', payload=payload, attempts=1, status_only=True)
        return response

    def get_subaccount_report_config(self, organization_id):
        response = self.send_request(
            '{}/v1/subaccounts/{}/reportconfigs'.format(
                self.url, organization_id))
        return response

    def get_subaccounts(self):
        '''
        Get all subaccounts

        ------------------------------------------------------------------------
        Response
        --------
        {
            "total": 2,
            "data": [
                {
                    "oid": -1,
                    "name": "<Default>",
                    "parent": 0
                },
                {
                    "oid": 100,
                    "name": "ACCT_CUSTOMER_NAME",
                    "parent": 0
                }
            ]
        }
        '''
        response = self.send_request('{}/v1/subaccounts'.format(self.url))
        return response

    def get_subaccount(self, organization_id):
        response = self.send_request('{}/v1/subaccounts/{}'.format(
            self.url, organization_id))
        return response

    def get_subaccount_children(self, organization_id):
        response = self.send_request(
            '{}/v1/subaccounts/{}/children'.format(self.url, organization_id))
        return response

    def update_device_subaccount(self, serial, organization_id):
        payload = {
            'sn': serial,
        }
        response = self.send_request(
            '{}/v1/subaccounts/{}/devices'.format(self.url, organization_id),
            action='POST', payload=payload, attempts=1)
        return response

    def proxy_command(
            self, serial, path, action='GET', filter=None, format=None,
            payload=None, sort=None, start=None, vdom=None):
        response = self.send_request(
            '{}/v1/fgt/{}/{}'.format(self.url, serial, path), action=action,
            payload=payload, filter=filter, format=format, sort=sort,
            start=start, vdom=vdom)
        return response

    def send_request(
            self, url, action="GET", attempts=3, filter=None, format=None,
            headers=None, params=None, payload=None, sort=None, start=None,
            timeout=(5, 10), vdom=None, verify=False, status_only=False):
        # Automatically login on first request. Fail out if unable to get token.
        if self.token is None:
            self.get_token()
        if self.token is None:
            self.logger.error('>> request not sent, token is not set')
            return None

        if headers is None:
            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "deflate",
                "Authorization": 'Bearer {}'.format(self.token),
                "Content-Type": "application/json"
            }

        parameters = {
            'filter': filter,
            'format': format,
            'sort': sort,
            'start': start,
            'vdom': vdom,
        }
        if params is not None:
            parameters.update(params)

        tries = 0
        while (tries < attempts):
            if self.errors >= 5:
                self.logger.warning(
                    '>> request not sent, FortiCloud errors too high')
                return None

            tries += 1
            self.logger.info('> {} | {}'.format(url, action))
            try:
                if action == 'GET':
                    response = requests.get(
                        url=url, headers=headers, params=parameters,
                        timeout=timeout, verify=verify)

                elif action == 'POST':
                    attempts = 1
                    response = requests.post(
                        url=url, headers=headers, json=payload,
                        params=parameters, timeout=timeout, verify=verify)

                elif action == 'PUT':
                    attempts = 1
                    response = requests.put(
                        url=url, headers=headers, json=payload,
                        params=parameters, timeout=timeout, verify=verify)

                elif action == 'DELETE':
                    attempts = 1
                    response = requests.delete(
                        url=url, headers=headers, json=payload,
                        params=parameters, timeout=timeout, verify=verify)

                else:
                    print('Method not supported: {}'.format(action))
                    return None

            except (ConnectTimeout, ReadTimeout):
                self.logger.warning('>> Timeout, retry')
                continue

            except (ConnectionError, HTTPError):
                self.logger.warning('>> Failed to establish a new connection')
                break
            self.logger.info("---------------------------------------------------------------------")
            self.logger.info(f"------ {url}")
            self.logger.info(f"------ {action}")
            self.logger.info(f"------ {response.status_code}")
            self.logger.info(f"------ {response.text[:200]}")
            self.logger.info("---------------------------------------------------------------------")
            if response.ok:
                self.logger.info('>> Response: {} {} - {}'.format(
                    action, response.status_code, response.reason))
                if status_only:
                    return True
                if response.text:
                    try:
                        return response.json()
                    except Exception:
                        return response.text

            # Handle rate limiting
            elif response.status_code == 429:
                self.logger.warning('>> Response: {} {} - {}'.format(
                    action, response.status_code, response.reason))
                sleep(1)
                self.errors += 1
                continue

            # Handle expected server error codes
            elif response.status_code in (
                    400, 401, 403, 404, 405, 413, 424, 500):
                self.logger.warning('>> Response: {} {} - {}'.format(
                    action, response.status_code, response.reason))
                self.errors += 1
                self.logger.track_api_failures(response)
                break

            # Catch all
            else:
                self.logger.warning('>> Response: {} {} - {}'.format(
                    action, response.status_code, response.reason))
                response.raise_for_status()

        if status_only:
            return False
        # Return None if unsuccessful after all attempts
        self.logger.warning('>> Unable to get response after all attempts')
        return None
