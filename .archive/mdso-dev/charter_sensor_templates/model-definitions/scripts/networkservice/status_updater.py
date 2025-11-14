""" -*- coding: utf-8 -*-

StatusUpdater Plans

Versions:
   0.1 Jan 03, 2018
       Initial check in of StatusUpdater plans

"""
import sys
sys.path.append('model-definitions')
from scripts.complete_and_terminate_plan import CompleteAndTerminatePlan
from plansdk.apis.bpo import WaitTimer


class Activate(CompleteAndTerminatePlan):
    """this is the class that is called for the initial activation of the
    StatusUpdater
    """

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

    def process(self):
        try:
            network_service_resource_id = self.properties.get("network_service_resource_id")
            # completed orchstates - states that represent the parent_resource has finished
            orchstates = {"failed", "active"}
            self.logger.info("awaiting for orchstate")
            try:
                result = self.get_resource_await_orchstate(
                    resource_id=network_service_resource_id, orchstates=orchstates, timeout=400, poll_interval=10
                )
            except Exception:
                self.logger.exception("Failure waiting orchstate for {}".format(network_service_resource_id))
                # exit

            self.logger.info("awaiting for orchstate complete, orch state is {}".format(result.get("orchState")))
            resource_orchstate = result.get("orchState")

            # operation to product translation
            operation = self.properties["operation"]
            product = {
                "NETWORK_SERVICE_ACTIVATION": "network_service",
                "NETWORK_SERVICE_UPDATE": "network_service_update",
                "NETWORK_SERVICE_DELETE": "network_service_update",
            }

            if resource_orchstate == "failed":
                # grab tracelog
                trace_logs = self.get_dependencies(
                    resource_id=network_service_resource_id, resource_type=self.BUILT_IN_TRACE_LOG_TYPE
                )
                orchestration_traces = trace_logs[0]["properties"].get("orchestration_trace")
                self.logger.info("Orchestration traces: \n{}\n".format(orchestration_traces))

                # determine which resource failed
                for index, orchestration_trace in enumerate(orchestration_traces):
                    if orchestration_trace.get("state") not in [
                        "STARTED",
                        "COMPLETED",
                    ] and "deviceconnectivitycheck" not in orchestration_trace.get("process"):
                        break

                categorized_error = orchestration_traces[index].get("categorized_error", "")

                # if error is too long, truncate to 150 characters
                if len(categorized_error) > 150:
                    categorized_error = categorized_error[:150]

                self.logger.info("categorized error is {}".format(categorized_error))

                # grab resource_name from tracelog
                failed_resource_name = orchestration_traces[index].get("resource_name")

                # grab resource_type, in case there is no translation for resource_name
                failed_resource_type = orchestration_traces[index].get("resource_type")

                self.logger.info("failed_resource_name is {}".format(failed_resource_name))

                # translate resource_name to status_message
                resource_status = self.STATUS_TRANSLATION.get(
                    failed_resource_name, "No resource_name to translate for {}".format(failed_resource_type)
                )

                # update parent resource with status
                self.status_messages(msg=resource_status, error=False, parent="network_service")

                # update parent resource with error
                self.status_messages(msg=categorized_error, error=True, parent="network_service")

                # build splunk message for failure
                splunk_msg = (
                    "resource_id={} | circuit_id={} | product={} | resource_status={} | resource_error={}".format(
                        network_service_resource_id,
                        self.properties.get("circuit_id", ""),
                        product[operation],
                        resource_status,
                        categorized_error.replace("|", ":"),  # replace '|' delimiter
                    )
                )

                self.splunk_logger.info(splunk_msg)

            else:  # service was sucessful
                # status messaging indicating success
                # update parent resource with status
                resource_status = "Completed"
                resource_error = ""  # should be blank, this is a pass
                self.status_messages(msg=resource_status, error=False, parent="network_service")
                self.status_messages(msg=resource_error, error=True, parent="network_service")

                # build splunk message for pass
                splunk_msg = (
                    "resource_id={} | circuit_id={} | product={} | resource_status={} | resource_error={}".format(
                        network_service_resource_id,
                        self.properties.get("circuit_id", ""),
                        product[operation],
                        resource_status,
                        resource_error,
                    )
                )

                self.splunk_logger.info(splunk_msg)

        except Exception:
            self.logger.exception("Status Updater failed.")

    def enter_exit_log(self, message, state="STARTED"):
        """OVERWRITING THE TRACELOGS SO THEY DO NOT GET CREATED
        FOR THIS RESOURCE.
        """
        pass
