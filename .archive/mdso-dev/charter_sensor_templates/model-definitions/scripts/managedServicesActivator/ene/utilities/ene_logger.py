import json
import time


class ENElogger:
    """
    Class to handle logging for ENE events and issues as well as finishing the resource and settings the status
    """
    def __init__(self, activate_object):
        self.activate_object = activate_object
        self.logger = activate_object.logger
        self.rid = activate_object.params["resourceId"]
        self.success = True
        self.issue_list = []
        self.steps = []
        self.events = []
        self.console_events = []
        self.api_failures = []
        self.info = self.logger.info
        self.warning = self.logger.warning
        self.error = self.logger.error
        self.critical = self.logger.critical
        self.debug = self.logger.debug

    def log_issue(self, external_message, internal_message, api_response="", code=2000, details="", category=0):
        """
        Logs issues that occur during automation
        :param external_message: string describing the issue encountered, includes dynamic information such as
         port number or vlan id
        :param internal_message: Used for reporting. does not include dynamic variables so that messages they can be
         aggregated
        :param api_response: (optional) api error response from meraki api
        :param details: non-important details that may be helpful for debugging later
        :param category: the category this issue falls in. See`broad_categories`
        :param code: Error code.
            Default (not provided): 2000
            Things that will not cause a failed status: 1xxx
            Non-critical issues that cause a failed status but do not result in halting automation: 2xxx
            Critical issue that does result in halting automation: 3xxx
        """
        broad_categories = {
            0: "Not Provided",
            1: "Design Configuration",
            2: "API / Network Error",
            3: "User Error",
            4: "Logical Errors"
        }
        if category not in broad_categories.keys():
            category = 0
        record = {
            "external_message": external_message,
            "internal_message": internal_message,
            "api_response": str(api_response),
            "code": code,
            "details": details.replace("|", ";"),  # replace pipe to avoid issues with splunk
            "subcategory": broad_categories[category]
        }
        self.logger.error("AN ERROR OCCURRED")
        self.logger.error(json.dumps(record, indent=4))
        self.issue_list.append(record)
        update_payload = {
            "properties": {
                "configurations": {
                    "issues": self.issue_list,
                }
            }
        }
        self.update_resource(update_payload)
        if code // 1000 == 3:
            self.success = False
            self.finish()

    def track_api_failures(self, resp):
        url = resp.url
        if "&access_token" in url:
            url = url.split("&access_token")[0]
        record = {
            "method": resp.request.method,
            "response": f"{resp.text}",
            "status_code": resp.status_code,
            "url": url,
            "timestamp": time.time(),
            "response_time": resp.elapsed.total_seconds(),
            "reason": f"{resp.reason}",
            "body": f"{resp.request.body}",
        }
        self.logger.info(json.dumps(record, indent=4))
        self.api_failures.append(record)
        update_payload = {
            "properties": {
                "configurations": {
                    "api_failures": self.api_failures,
                }
            }
        }
        self.update_resource(update_payload)

    def log_step(self, step):
        """
        Keeps track of where automation is at
        :param step: (str) current step for activation process
        """
        self.logger.info(f"STEP: {step}")
        log_event = {
            "step": step,
            "timestamp": time.time(),
        }
        self.steps.append(log_event)
        update_payload = {
            "properties": {
                "configurations": {
                    "steps": self.steps,
                }
            }
        }
        self.update_resource(update_payload)

    def log_info(self, event, details=""):
        """
        Keeps track of misc events that we want to be recorded to the resource
        :param step: (str) current step for activation process
        """
        self.logger.info(f"{event} | {details}")
        detail_event = {
            "event": event,
            "timestamp": time.time(),
        }
        self.events.append(detail_event)
        update_payload = {
            "properties": {
                "configurations": {
                    "info_log": self.steps,
                }
            }
        }
        self.update_resource(update_payload)

    def finish(self):
        if not self.success:
            messages = [x["external_message"] for x in self.issue_list]
            self.activate_object.exit_error("; ".join(messages))

    def update_resource(self, payload):
        """
        Updates the resource in MDSO
        :param payload:
        """
        # self.logger.info(f"updating the resource info with: {payload}")
        self.activate_object.bpo.resources.patch_observed(self.rid, payload)
