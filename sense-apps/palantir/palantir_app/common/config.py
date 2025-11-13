from os import environ

# from tests.test_logging import test_format_api_call


class Config:
    """Main configuration settings for Palantir service"""

    def __init__(self, orchestrator="MDSO"):
        self.orchestrator = orchestrator
        # Prod
        if environ.get("ENV") == "PROD":
            if self.orchestrator == "MDSO":
                self.MDSO_IP = "50.84.225.107"
            else:
                raise NotImplementedError
        # Staging
        else:
            if self.orchestrator == "MDSO":
                self.MDSO_IP = "97.105.228.53"
            else:
                raise NotImplementedError
