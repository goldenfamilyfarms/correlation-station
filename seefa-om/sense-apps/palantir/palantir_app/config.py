import logging
import os
from cryptography.fernet import Fernet
from pydantic import model_validator
from pydantic_settings import BaseSettings


logger = logging.getLogger(__name__)


class AppConfig(BaseSettings):
    """
    Environment settings for Palantir
    """

    LOGGING_LEVEL: str = "DEBUG"
    LOGGING_SETTINGS: str = "debug_logging_settings.json"
    MS_NAME: str = "PALANTIR"
    USAGE_DESIGNATION: str = "STAGE"

    @model_validator(mode="after")
    def environ_check(self) -> "AppConfig":
        if not self.USAGE_DESIGNATION:
            self.USAGE_DESIGNATION = "STAGE"
        return self


class AuthConfig(BaseSettings):
    """
    Environment settings for Authentication of Palantir services
    Note: All variables MUST be set in the environment
    """

    # Arin
    ARIN_API_KEY: str = ""
    ARIN_API_KEY_SKELLY: str = ""

    # Hydra
    PALANTIR_GENERAL_HYDRA_KEY: str = ""
    PALANTIR_GENERAL_HYDRA_KEY_SKELLY: str = ""
    PALANTIR_SPIRENT_HYDRA_KEY: str = ""
    PALANTIR_SPIRENT_HYDRA_KEY_SKELLY: str = ""
    PALANTIR_MNE_HYDRA_KEY: str = ""
    PALANTIR_MNE_HYDRA_KEY_SKELLY: str = ""
    PALANTIR_TID_HYDRA_KEY: str = ""
    PALANTIR_TID_HYDRA_KEY_SKELLY: str = ""
    PALANTIR_IPC_HYDRA_KEY: str = ""
    PALANTIR_IPC_HYDRA_KEY_SKELLY: str = ""
    PALANTIR_HYDRA_STAGIUS_KEY: str = ""
    PALANTIR_HYDRA_STAGIUS_KEY_SKELLY: str = ""

    # IP Control
    IPC_USER: str = ""
    IPC_PASS: str = ""
    IPC_PASS_SKELLY: str = ""

    # MDSO
    MDSO_USER: str = ""
    MDSO_PASS: str = ""
    MDSO_PASS_SKELLY: str = ""
    # Prod MDSO used by Arda and locally testing in Palantir
    MDSO_USER_PROD: str = ""
    MDSO_PASS_PROD: str = ""
    MDSO_PASS_PROD_SKELLY: str = ""

    # ODIN
    ODIN_USER: str = ""
    ODIN_PASS: str = ""
    ODIN_PASS_SKELLY: str = ""
    ODIN_TOKEN: str = ""
    ODIN_TOKEN_SKELLY: str = ""

    # Remedy
    REMEDY_USER: str = ""
    REMEDY_PASS: str = ""
    REMEDY_PASS_SKELLY: str = ""

    # SNMP
    SNMP_COMMUNITY_STRING: str = ""
    SNMP_COMMUNITY_STRING_SKELLY: str = ""
    SNMP_PUBLIC_STRING: str = ""
    SNMP_PUBLIC_STRING_SKELLY: str = ""

    # SENSE
    SENSE_SWAGGER_USER: str = ""
    SENSE_SWAGGER_PASS: str = ""
    SENSE_SWAGGER_PASS_SKELLY: str = ""
    SENSE_EMAIL_NAME: str = ""
    SENSE_EMAIL_PASS: str = ""
    SENSE_EMAIL_PASS_SKELLY: str = ""
    SENSE_TEST_SWAGGER_USER: str = ""
    SENSE_TEST_SWAGGER_PASS: str = ""
    SENSE_TEST_SWAGGER_PASS_SKELLY: str = ""

    # Network
    NETWORK_LOGIN_USER: str = ""
    NETWORK_LOGIN_PASS: str = ""
    NETWORK_LOGIN_PASS_SKELLY: str = ""
    TACACS_USER: str = ""
    TACACS_PASS: str = ""
    TACACS_PASS_SKELLY: str = ""

    # Salesforce
    SALESFORCE_EMAIL: str = ""
    SALESFORCE_PASS: str = ""
    SALESFORCE_PASS_SKELLY: str = ""
    SALESFORCE_TOKEN: str = ""
    SALESFORCE_TOKEN_SKELLY: str = ""

    # ESET
    ESET_USER: str = ""
    ESET_PASS: str = ""
    ESET_PASS_SKELLY: str = ""

    # ISE
    ISE_USER: str = ""
    ISE_PASS: str = ""
    ISE_PASS_SKELLY: str = ""
    ISE_STATIC_KEY: str = ""
    ISE_STATIC_KEY_SKELLY: str = ""
    ISE_STATIC_KEY_ADVA: str = ""
    ISE_STATIC_KEY_ADVA_SKELLY: str = ""
    ISE_STATIC_KEY_ALCATEL: str = ""
    ISE_STATIC_KEY_ALCATEL_SKELLY: str = ""
    ISE_STATIC_KEY_CIENA: str = ""
    ISE_STATIC_KEY_CIENA_SKELLY: str = ""
    ISE_STATIC_KEY_CISCO: str = ""
    ISE_STATIC_KEY_CISCO_SKELLY: str = ""
    ISE_STATIC_KEY_JUNIPER: str = ""
    ISE_STATIC_KEY_JUNIPER_SKELLY: str = ""
    ISE_STATIC_KEY_NOKIA: str = ""
    ISE_STATIC_KEY_NOKIA_SKELLY: str = ""
    ISE_STATIC_KEY_RAD: str = ""
    ISE_STATIC_KEY_RAD_SKELLY: str = ""

    @model_validator(mode="after")
    def decrypt_values(self) -> "AuthConfig":
        for key, value in self.__dict__.items():
            if "SKELLY" in key:
                continue
            if "KEY" in key or "TOKEN" in key or "PASS" in key or "SNMP" in key:
                f = Fernet(self.__dict__[f"{key}_SKELLY"])
                self.__dict__[key] = f.decrypt(value).decode()
        return self


class UrlConfig(BaseSettings):
    """
    Environment settings for Palantir Service Urls
    """

    envs: dict = {
        "PRODUCTION": {"GRANITE": "https://hydra-vip.chtrse.com/prod", "DENODO": "https://hydra-vip.chtrse.com/prod"},
        "STAGE": {"GRANITE": "https://hydra-dev.chtrse.com", "DENODO": "https://hydra-vip.chtrse.com/qa"},
    }

    # URLs
    ARIN_CREATE_BASE_URL: str = ""
    BLACKLIST_IP_SERVICE_URL: str = ""
    DENODO_BASE_URL: str = ""
    HYDRA_BASE_URL: str = ""
    GRANITE_BASE_URL: str = ""
    IPC_BASE_URL: str = ""
    LIGHT_TEST_URL: str = ""
    MDSO_PROD_URL: str = ""  # prod and dev = MDSO prod for ARDA
    MDSO_BASE_URL: str = ""  # prod and dev different for BEORN and PALANTIR
    REMEDY_BASE_URL: str = ""
    SENSE_BASE_URL: str = ""
    WHOIS_BASE_URL: str = ""
    NICE_BASE_URL: str = ""  # ODIN v1
    ODIN_BASE_URL: str = ""  # ODIN v2
    ESET_BASE_URL: str = ""
    ISE_EAST_URL_PAN11: str = ""
    ISE_EAST_URL_PAN21: str = ""
    ISE_WEST_URL_PAN11: str = ""
    ISE_WEST_URL_PAN21: str = ""
    ISE_SOUTH_URL_PAN11: str = ""
    ISE_SOUTH_URL_PAN21: str = ""
    NDOS_BASE_URL: str = ""
    SALESFORCE_BASE_URL: str = ""
    SEEK_BASE_URL: str = ""

    ISE_CUBES_EAST: dict = {1: "", 2: ""}
    ISE_CUBES_WEST: dict = {1: "", 2: ""}
    ISE_CUBES_SOUTH: dict = {1: "", 2: ""}

    # Servers/Ports
    REMEDY_SERVER: str = ""
    SENSE_EMAIL_SERVER: str = ""
    SENSE_EMAIL_PORT: str = ""

    @model_validator(mode="after")
    def populate_ise_cubes(self) -> "UrlConfig":
        self.ISE_CUBES_EAST[1] = self.ISE_EAST_URL_PAN11
        self.ISE_CUBES_EAST[2] = self.ISE_EAST_URL_PAN21
        self.ISE_CUBES_WEST[1] = self.ISE_WEST_URL_PAN11
        self.ISE_CUBES_WEST[2] = self.ISE_WEST_URL_PAN21
        self.ISE_CUBES_SOUTH[1] = self.ISE_SOUTH_URL_PAN11
        self.ISE_CUBES_SOUTH[2] = self.ISE_SOUTH_URL_PAN21
        return self

    @model_validator(mode="after")
    def set_granite_url(self) -> "UrlConfig":
        self.GRANITE_BASE_URL = self.envs[os.environ.get("USAGE_DESIGNATION", "STAGE")]["GRANITE"]
        self.HYDRA_BASE_URL = self.envs[os.environ.get("USAGE_DESIGNATION", "STAGE")]["DENODO"]
        return self
