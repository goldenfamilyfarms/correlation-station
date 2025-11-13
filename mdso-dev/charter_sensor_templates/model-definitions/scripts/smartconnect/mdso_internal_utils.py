class MDSOInternalSmartConnect(object):
    """Dynamic connection parameters specific to MDSO"""

    def __init__(self, plan):
        self.plan = plan

    def get_connection_type(self, vendor, model=""):
        PROFILE_CONNECTION_TYPE = {
            "JUNIPER": "netconf",
            "ADVA": "netconf" if "116PRO" in model else "cli",
            "CISCO": "cli",
            "RAD": "cli",
        }
        return PROFILE_CONNECTION_TYPE[vendor]

    def get_credentials(self, vendor, connection_type):
        """get device login credentials from vendor session profile"""
        session_profile = self._get_unobfuscated_session_profile(vendor)
        return session_profile["properties"]["authentication"][connection_type]

    def _build_session_name(self, vendor, model=""):
        session_name_vendor = "jnpr" if vendor == "JUNIPER" else vendor.lower()
        session_name = "sensor_{}".format(session_name_vendor)
        if "116PRO" in model:
            session_name += "_netconf"
        self.logger.info("Session Profile Name: {}".format(session_name))
        return session_name

    def _get_unobfuscated_session_profile(self, vendor, model=""):
        session_profile = self.bpo.resources.get_by_filters(
            resource_type=self.COMMON_TYPE_LOOKUP.get(vendor)["SESSION_PROFILE_TYPE"],
            q_params={"label": self._build_session_name(vendor, model)},
        )[0]
        return self.bpo.resources.get(session_profile["id"], obfuscate=False)

    def __getattr__(self, attr):
        if hasattr(self.plan, attr):
            return getattr(self.plan, attr)
        raise AttributeError("'{}' object has no attribute '{}'".format(self.__class__.__name__, attr))
