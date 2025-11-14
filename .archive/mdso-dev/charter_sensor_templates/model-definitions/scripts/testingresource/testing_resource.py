import json
import sys
sys.path.append('model-definitions')
from scripts.common_plan import CommonPlan


class Activate(CommonPlan):
    def vCMTS_login(self):

        # Get resource
        resource_id = self.params['resourceId']
        resource = self.bpo.resources.get(resource_id)
        properties = resource['properties']

        # Get device name and port name from test resource
        device_name = properties['deviceName']
        channel_number = properties['channel_number']
        rpd = properties['rpd']

        resource_id = self.get_network_function_by_host('172.31.10.95')
        channel_result = self.execute_ra_command_file(resource_id, 'get-channel.json', {'rpd': rpd, 'channel number': channel_number}).json()['result']

        # Split result
        channel_split = channel_result.split("\\r\r\n")
        row_split = channel_split.split()
        channel_status = row_split[4]
        clock_status = row_split[5]

        # Parse result
        circuit_status = "Channel status: " + channel_status + "\nClock status: " + clock_status
        self.logger.info("Output: " + json.dumps(circuit_status))

        if channel_status != "online" or clock_status != "locked":
            self.bpo.resources.patch_observed(self.resource['id'], {"properties": {"Error": circuit_status}})
        else:
            self.bpo.resources.patch_observed(self.resource['id'], {"properties": {"Error": "Channel and/or clock not found"}})

        # Get device's network function
        self.get_network_function_by_host_or_ip(device_name, device_name)


class Terminate(CommonPlan):
    pass
