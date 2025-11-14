import sys
sys.path.append('model-definitions')
from scripts.common_plan import CommonPlan
import scripts.networkservice.circuitdetailscollector
import scripts.scriptplan


class Activate(CommonPlan):

    def process(self):
        self.circuit_id = self.properties['circuit_id']

        # Create tracelog on multi-leg resource
        self.enter_exit_log(message="Multi-Leg Circuit")

        self.use_alternate_url = bool(self.properties.get('use_alternate_circuit_details_server', False))
        raw_details = scripts.networkservice.circuitdetailscollector.Activate.get_circuit_details_server_response(self, True)
        self.timeout_per_leg = self.properties['timeout_per_leg']

        self.legs_list = []
        for k in raw_details:
            self.legs_list.append(k)

        self.logger.info("==== Legs List: {}".format(self.legs_list))

        network_service_prod_id = self.get_products_by_type_and_domain("charter.resourceTypes.NetworkService", "built-in")[0]['id']

        for leg_name in self.legs_list:
            try:
                cid = raw_details[leg_name]['serviceName'] + "-" + leg_name
                self.logger.info("The CID I will send is: {}".format(cid))
                props = {
                    "circuit_id": cid,
                    "use_alternate_circuit_details_server": self.resource['properties']['use_alternate_circuit_details_server']}
                net_serv_body = {
                    "productId": network_service_prod_id,
                    "label": cid,
                    "properties": props}

                net_serv_response = self.create_active_resource(title=cid, parent_res_id=self.resource_id, body=net_serv_body, waittime=self.timeout_per_leg)
                self.logger.info("=&=$=%=&=$=%=&=$=% NET_SERV_RESPONSE %=$=&=%=$=&=%=$=&=%=$=&=")
                self.logger.info(net_serv_response)

            except Exception as e:
                msg = "Failure in the Multileg process"
                self.categorized_error = self.ERROR_CATEGORY['MDSO'].format(msg) if self.ERROR_CATEGORY.get("MDSO") else ""
                self.exit_error("Failed during the multileg process : %s" % str(e))


class Terminate(CommonPlan):
    """This is the class that is called for the termination of a Multileg Circuit resource.
    """
    """
        Disable the enter_exit_log behavior to prevent creating a new instance of TraceLog that would
        not be terminated automatically after the Multileg Circuit terminates. Unless this is disabled,
        TraceLog resources will accumulate for each Multileg Circuit that we terminate.
    """
    EnableEnterExitLog = False
    all_dependencies_ids = []

    def process(self):

        self.soft_terminate_process()

        try:
            dependencies = self.bpo.resources.get_dependencies(self.resource['id'])
            # is_service_built = False

            self.logger.debug("Deleting resources. " + str(len(dependencies)))
            self.bpo.resources.delete_dependencies(self.resource['id'],
                                                   None,
                                                   dependencies,
                                                   force_delete_relationship=True)

        except Exception as ex:
            self.logger.exception(ex)
            raise Exception(ex)
        pass
