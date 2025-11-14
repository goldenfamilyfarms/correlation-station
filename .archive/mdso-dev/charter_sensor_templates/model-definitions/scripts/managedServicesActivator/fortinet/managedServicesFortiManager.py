from vfirewall.chartervfw.virtualFirewall import VirtualFirewallCommonPlan


class Activate(VirtualFirewallCommonPlan):
    def process(self):
        properties = self.resource["properties"]
        self.logger.info("Properties {}".format(properties))
        fmg = self.fortimanager_registrar.pre_install()

        self.logger.info("FMG {}".format(fmg))


class Terminate(VirtualFirewallCommonPlan):
    def process(self):
        pass
