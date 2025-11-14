from vfirewall.chartervfw.virtualFirewall import VirtualFirewallCommonPlan


class Activate(VirtualFirewallCommonPlan):
    def process(self):
        properties = self.resource["properties"]

        self.logger.info("Properties {}".format(properties))
        # create customer.
        self.fortiportal_registrar.register()


class Terminate(VirtualFirewallCommonPlan):
    def process(self):
        pass
