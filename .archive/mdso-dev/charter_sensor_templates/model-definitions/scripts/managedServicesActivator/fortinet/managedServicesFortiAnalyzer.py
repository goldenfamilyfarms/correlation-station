from vfirewall.chartervfw.virtualFirewall import VirtualFirewallCommonPlan


class Activate(VirtualFirewallCommonPlan):
    def process(self):
        props = self.resource["properties"]
        self.logger.info("props: {}".format(props))
        # add device parameter required
        self.fortianalyzer_registrar.register(add_device=False)


class Terminate(VirtualFirewallCommonPlan):
    def process(self):
        pass
