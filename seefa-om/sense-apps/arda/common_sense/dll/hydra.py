from datetime import datetime
import logging
import requests
from common_sense.common.api import wait_for_success


class HydraConnector:
    """Make API calls to Hydra"""

    def __init__(self, url: str, api_key: str, environment: str = "dev"):
        """Environment is used to determine the api path. Options are dev and prd."""
        self.url = url
        self._api_key = api_key
        self.logger = logging.getLogger(__name__)
        self.logger.debug(f"Log_Message=Granite connector created for url '{self.url}'")
        self.environment = environment

    def get_site_inst(self, site_id: str) -> dict:
        self.logger.info(f"Retrieving site instance for site_id {site_id}")
        if self.environment == "prd":
            endpoint = f"{self.url}/prod/granite/ise/siteUDAs"
        else:
            self.logger.error(f"Unrecognized environment for get_site_inst - '{self.environment}'")
            return {}
        payload = {
            "SITE_INST_ID": site_id,
            "api_key": self._api_key,
        }
        try:
            response = requests.get(url=endpoint, params=payload, timeout=150, verify=False)
            response = response.json()
            self.logger.debug(f"Retrieved response for legacy company. Response {response}")
            return response
        except Exception as ex:
            error_msg = (
                f"Url={endpoint} | Log_Message=Exception while fetching site instances from Granite Exception: {ex}"
            )
            self.logger.error(error_msg, exc_info=True)
            return {}

    @wait_for_success
    def topology(self, circuit_id: str) -> dict:
        """
        Queries Granite with Circuit ID and returns the raw response.
        :return:
        """
        if self.environment == "prd":
            endpoint = f"{self.url}/prod/denodo/app_int/dice/views/dv_dice_topology_v5"
        else:
            self.logger.error(f"Unrecognized environment for get_site_inst - '{self.environment}'")
            return {}
        payload = {
            "cid": circuit_id,
            "format": "json",
            "api_key": self._api_key,
        }
        try:
            self.logger.info(endpoint)
            response = requests.get(url=endpoint, params=payload, timeout=30, verify=False)
            response = response.json()
            self.logger.debug(f"Retrieved response for circuit topology. Response {response}")
            if not response:
                self.logger.warning(f"Circuit_ID={circuit_id} | " f"Log_Message=Granite Query Returned No Data")
            return response
        except Exception as ex:
            error_msg = (
                f"Url={endpoint} | Circuit_ID={circuit_id} | Log_Message=Exception while fetching site "
                + f"instances from Granite Exception: {ex}"
            )
            self.logger.error(error_msg)
            return {}

    @wait_for_success
    def dv_circ_path_attr_settings(
        self, filter: str, format: str = "json", displayRESTfulReferences: str = "false"
    ) -> dict:
        """
        Queries Granite for Circuit Path Attr settings. Filter should be a sql query.
        :return:
        """
        if self.environment == "prd":
            endpoint = f"{self.url}/prod/denodo/granite/ise/views/dv_circ_path_attr_settings"
        else:
            self.logger.error(f"Unrecognized environment for dv_circ_path_attr_settings - '{self.environment}'")
            return {}
        payload = {
            "$format": format,
            "$displayRESTfulReferences": displayRESTfulReferences,
            "$filter": filter,
            "api_key": self._api_key,
        }
        try:
            self.logger.info(endpoint)
            self.logger.info(payload)
            response = requests.get(url=f"{endpoint}", params=payload, timeout=30, verify=False)
            response = response.json()
            self.logger.debug(f"Retrieved response for circuit topology. Response {response}")
            if not response:
                self.logger.warning("Log_Message=Granite Query Returned No Data for dv_circ_path_attr_settings")
            return response
        except Exception as ex:
            error_msg = (
                f"Url={endpoint} | Log_Message=Exception while fetching dv_circ_path_attr_settings "
                + f"from Granite Exception: {ex}"
            )
            self.logger.error(error_msg)
            return {}

    @wait_for_success
    def pop_nfx(
        self,
        latitude: str,
        longitude: str,
        legacy_company: list = [],
        model: str = "",
        test_type: str = "",
        equipment_status: str = "Live",
    ):
        if self.environment == "prd":
            endpoint = f"{self.url}/prod/denodo/app_int/bv_nfx_distance/views/bv_nfx_distance_v3"
        elif self.environment == "dev":
            endpoint = f"{self.url}/qa/app_int/bv_nfx_distance/views/bv_nfx_distance_v3"
        else:
            self.logger.error(f"Unrecognized environment for get_site_inst - '{self.environment}'")
            return {}
        start_time = datetime.now()
        if not legacy_company:
            self.logger.warning("Log_Message=No legacy company provided for pop nfx. Defaulting to EDNA.")
            legacy_company = ["EDNA"]
        else:
            if isinstance(legacy_company, str):
                legacy_company = [legacy_company]
            if len(legacy_company) == 1:
                legacy_company = f"&legacy_company={legacy_company[0]}"
            else:
                lc = [f"'{c}'" for c in legacy_company]
                legacy_company = f"&$filter=legacy_equip in ({','.join(lc)})"
        optional_param = (
            f"{f'&model={model}' if model else ''}"
            f"{f'&test_type={test_type}' if test_type else ''}"
            f"{f'&equip_status={equipment_status}' if equipment_status else ''}"
            f"{legacy_company}"
        )
        nfx_endpoint = f"{endpoint}?inlong={longitude}&inlat={latitude}"
        nfx_endpoint = nfx_endpoint + optional_param
        msg = f"Nfx Endpoint - {nfx_endpoint}"
        self.logger.info(msg)
        self.logger.debug(f"Log_Message=Longitude '{longitude}' Latitude '{latitude}'")
        try:
            response = requests.get(nfx_endpoint + f"&api_key={self._api_key}", timeout=120, verify=False)
            if response.status_code != 200:
                error_msg = (
                    f"Response_Time={datetime.now() - start_time} | Status_Code={response.status_code} | "
                    + f"Url={nfx_endpoint} | Log_Message=Unsuccessful status code while fetching pop nfx from Granite"
                )
                self.logger.error(error_msg)
                return False
            msg = (
                f"Response_Time={datetime.now() - start_time} | Url={nfx_endpoint} | Log_Message=Granite "
                + "Retrieved list of pop nfx from Granite."
            )
            self.logger.info(msg)
            return response
        except Exception as ex:
            error_msg = (
                f"Response_Time={datetime.now() - start_time} | Url={nfx_endpoint} | Log_Message="
                + f"Exception while fetching pop nfx from Granite Exception: {ex}"
            )
            self.logger.error(error_msg)
            return False
