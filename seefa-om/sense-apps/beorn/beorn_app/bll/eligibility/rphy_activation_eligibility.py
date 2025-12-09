import logging
from beorn_app.dll.granite import granite_get
from beorn_app.dll.sales_force import (
    salesforce_request,
    get_codes,
    PRODUCT_FAMILY,
    FIBER_CONNECT_PLUS,
    SF_NULL_RESPONSE,
    CIRCUIT_ID,
    ENGINEERING_TABLE,
)
from beorn_app.common.endpoints import DENODO_MDSO_MODEL_V3, DENODO_CIRCUIT_DEVICES, GRANITE_ELEMENTS

logger = logging.getLogger("")

ELIGIBLE = True
INELIGIBLE = False


class RPHYActivationEligibilityException(Exception):
    def __init__(self, exception_prefix: str, data: dict):  # noqa: B042
        self.exception_prefix = exception_prefix
        self.data = data
        self.message = f"Eligbility Failed at Step: {self.exception_prefix} | Data: {self.data}"
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message


class ServiceTypEligibilityException(RPHYActivationEligibilityException):
    def __init__(self, service_type_error: str, data: dict):
        super().__init__(service_type_error, data)


class RFCodesEligibilityException(RPHYActivationEligibilityException):
    def __init__(self, rf_codes_error: str, data: dict):
        super().__init__(rf_codes_error, data)


class CircuitIDEligilityException(RPHYActivationEligibilityException):
    def __init__(self, circuit_id_error: str, data: dict):
        super().__init__(circuit_id_error, data)


class GraniteEligibilityException(RPHYActivationEligibilityException):
    def __init__(self, granite_eligibility_error: str, data: dict):
        super().__init__(granite_eligibility_error, data)


class RPHYActivationEligibilityChecker:
    CID_WRONG_PRODUCT_FAMILY = "Product Family Not Listed as FC+."
    CID_NOT_FOUND = "Circuit ID Not Found in SalesForce Response"
    NEW_INSTALL_MSG = "Not Listed as New Install"
    REQUIRED_DATA = ["circuit_id", "rf_codes", "service_type", "cmts_data", "tid"]

    def __init__(self, eng_id: str, mac_address: str):
        self.activation_data: dict = {}
        self.eng_id: str = eng_id
        self.mac_address: str = mac_address

    def check_eligibility(self) -> dict:
        """
        Checks and scans the logged eligibility data to determine status
        :param: none
        :return: dict
        """
        try:
            self._check_eligibility()
            self._validate_eligibility_check()
            self.activation_data["eligible"] = (ELIGIBLE, "Device Eligible")
            return self.activation_data
        except CircuitIDEligilityException as circuit_id_ineligibility:
            self.activation_data["circuit_id"] = (INELIGIBLE, str(circuit_id_ineligibility))
            self.activation_data["granite"] = (INELIGIBLE, "Invalid CID prevents Granite Check")
            self._gather_remaining_data(CircuitIDEligilityException)
            self.activation_data["eligible"] = (INELIGIBLE, "Device Inegigible")
            return self.activation_data
        except ServiceTypEligibilityException as service_type_ineligibilty:
            self.activation_data["service_type"] = (INELIGIBLE, str(service_type_ineligibilty))
            self._gather_remaining_data(ServiceTypEligibilityException)
            self.activation_data["eligible"] = (INELIGIBLE, "Device Ineligible")
            return self.activation_data
        except RFCodesEligibilityException as rf_codes_ineligibility:
            self.activation_data["rf_codes"] = (INELIGIBLE, str(rf_codes_ineligibility))
            self._gather_remaining_data(RFCodesEligibilityException)
            self.activation_data["eligible"] = (INELIGIBLE, "Device Ineligible")
            return self.activation_data
        except GraniteEligibilityException as granite_ineligibility:
            self.activation_data["granite"] = (INELIGIBLE, str(granite_ineligibility))
            self.activation_data["eligible"] = (INELIGIBLE, "Device Ineligible")
            return self.activation_data
        except RPHYActivationEligibilityException as ineligible_reason:
            self.activation_data["eligible"] = (INELIGIBLE, str(ineligible_reason))
            return self.activation_data
        except Exception as e:
            self.activation_data["eligible"] = (INELIGIBLE, str(e))
            return self.activation_data

    def _check_eligibility(self) -> None:
        """
        Runs all eligibility check logic
        :param: none
        :return: none
        """
        self._check_circuit_id_eligibility()
        rf_codes = get_codes(self.eng_id)
        self._check_service_type_eligibility(rf_codes)
        self._check_rf_codes_eligibility(rf_codes)
        self._check_granite_eligibility()
        self._check_rphy_leg()

    def _check_rphy_leg(self) -> None:
        params = {"CIRC_PATH_HUM_ID": self.activation_data["circuit_id"][1], "LVL": "1"}
        response = granite_get(GRANITE_ELEMENTS, params=params)
        if response and response[0].get("LEG_NAME") != "RPHY":
            raise GraniteEligibilityException(
                "CIRCUIT LEG NOT RPHY. INELIGIBLE FOR AUTOMATION.", response[0].get("LEG_NAME")
            )

    def _validate_eligibility_check(self) -> None:
        missing_required_fields = sorted(RPHYActivationEligibilityChecker.REQUIRED_DATA) != sorted(
            self.activation_data.keys()
        )
        if missing_required_fields:
            errors: str = self._eligibility_error_formatter()
            msg = f"{self.eng_id} Ineligible for Auto Activation"
            raise RPHYActivationEligibilityException(msg, errors)

    def _eligibility_error_formatter(self) -> str:
        """
        Formats error dict into comma + space separated string
        :param: none
        :return: string
        """
        return ", ".join([f"{k}: {v[1]}" for k, v in self.activation_data if not self.activation_data[k][0]])

    def _check_circuit_id_eligibility(self) -> None:
        """
        Queries Salesforce to validate Circuit ID eligibility
        Circuit ID eligible if:
            Product Type is equal to FC+ (Fiber Connect Plus)
        :param: none
        :return: none
        """
        cid_result = self._query_circuit_id()
        self._validate_circuit_id(cid_result)
        self.activation_data["circuit_id"] = (ELIGIBLE, cid_result["records"][0].get(CIRCUIT_ID))

    def _query_circuit_id(self) -> dict:
        CID_QUERY: str = (
            f"SELECT {PRODUCT_FAMILY}, {CIRCUIT_ID} FROM {ENGINEERING_TABLE} WHERE Name IN ('{self.eng_id}')"
        )
        circuit_id_query: list = salesforce_request(CID_QUERY)
        return circuit_id_query

    def _validate_circuit_id(self, cid_result: dict) -> None:
        if "records" not in cid_result:
            raise CircuitIDEligilityException(RPHYActivationEligibilityChecker.CID_NOT_FOUND, cid_result)
        if len(cid_result["records"]) == 0:
            raise CircuitIDEligilityException(SF_NULL_RESPONSE, cid_result)
        if cid_result["records"][0].get(PRODUCT_FAMILY) != FIBER_CONNECT_PLUS:
            raise CircuitIDEligilityException(
                RPHYActivationEligibilityChecker.CID_WRONG_PRODUCT_FAMILY, cid_result["records"][0].get(PRODUCT_FAMILY)
            )
        if CIRCUIT_ID not in cid_result["records"][0].keys():
            raise CircuitIDEligilityException(RPHYActivationEligibilityChecker.CID_NOT_FOUND, cid_result)

    def _check_service_type_eligibility(self, rf_codes: dict) -> None:
        invalid_service_type: bool = rf_codes.get("error", "") == RPHYActivationEligibilityChecker.NEW_INSTALL_MSG
        if invalid_service_type:
            raise ServiceTypEligibilityException("Service Type Ineligible", rf_codes.get("error"))
        self.activation_data["service_type"] = (ELIGIBLE, "New Install")

    def _check_rf_codes_eligibility(self, rf_codes: dict) -> None:
        """
        Validates RF Code eligibility
        """
        if rf_codes.get("error"):
            raise RFCodesEligibilityException("RF Codes Ineligible", rf_codes.get("error"))
        self.activation_data["rf_codes"] = (ELIGIBLE, rf_codes.get("svc_codes"))

    def _check_granite_eligibility(self) -> None:
        # step 1 query granite
        response: dict = granite_get(
            endpoint=DENODO_MDSO_MODEL_V3, params={"cid": self.activation_data["circuit_id"][1], "$format": "json"}
        )
        # step 2 extract granite data
        self._extract_granite_data(response)

    def _extract_granite_data(self, response: dict) -> None:
        # check elements dict
        data: dict = self._validate_elements_dict(response)
        # get tid
        self._get_tid(data)
        # find cmts
        self._find_cmts(data)
        # grab rpd
        self._query_rpd()
        # validate cmts data
        self._validate_cmts_result()
        # clean ipv6
        self._clean_ipv6()

    def _validate_elements_dict(self, response: dict) -> dict:
        if not response.get("elements"):
            raise Exception("Elements Dict Not Found")
        if len(response.get("elements")) == 0:
            raise Exception("Empty elements response")
        return response.get("elements")[0]

    def _get_tid(self, data) -> None:
        response: dict = self._query_tid(data)
        tid_result = self._extract_tid(response)
        self._validate_tid(tid_result)
        self.activation_data["tid"] = (ELIGIBLE, tid_result.pop())

    def _query_tid(self, data):
        return granite_get(endpoint=DENODO_CIRCUIT_DEVICES, params={"cid": data.get("cid"), "$format": "json"})

    def _extract_tid(self, tid_query_result):
        def find_tid(record: dict) -> bool:
            harmonics_result = (
                record.get("vendor", "") == "HARMONIC"
                and record.get("eq_type", "") == "VIDEO CPE"
                and record.get("model") == "CABLEOS WAVE-1"
            )
            if not harmonics_result:
                vecima_result = (
                    record.get("vendor", "") == "VECIMA"
                    and record.get("eq_type", "") == "VIDEO MEDIA CONVERTER"
                    and record.get("model") == "RPD EN2112"
                )
                return vecima_result
            return harmonics_result

        elements_data = tid_query_result.get("elements", [{}])[0].get("data", [])
        return [record.get("tid", "") for record in elements_data if (find_tid(record))]

    def _validate_tid(self, tid_result):
        if len(tid_result) < 1:
            raise GraniteEligibilityException("TID Not Found", tid_result)

    def _find_cmts(self, data: dict) -> None:
        def _is_cmts(record: dict) -> bool:
            path_length_check: bool = len(record.get("path_name", "").split(".")) > 2
            matching_path_check: bool = (
                record.get("path_name", "").split(".")[-1] == record.get("path_name", "").split(".")[-2]
            )
            valid_path_name: bool = path_length_check and matching_path_check
            vendor_check: bool = record.get("vendor") == "HARMONIC"
            equipment_type_check: bool = record.get("eq_type") == "CMTS"
            model_check: bool = record.get("model") == "CABLEOS CORE"
            is_cmts: bool = vendor_check and equipment_type_check and model_check
            return valid_path_name and is_cmts

        cmts_res = [
            {
                "vendor": record.get("vendor", ""),
                "eq_type": record.get("eq_type", ""),
                "cmts_ip": record.get("management_ip", ""),
                "hostname": record.get("path_name", "").split(".")[-1],
                "model": record.get("model", ""),
            }
            for record in data.get("data", [])
            if (_is_cmts(record))
        ]
        self.activation_data["cmts_data"] = cmts_res[0] if len(cmts_res) > 0 else []

    def _validate_cmts_result(self) -> None:
        self._check_cmts_found()
        self._check_cmts_data_valid()
        self.activation_data["cmts_data"] = (ELIGIBLE, self.activation_data["cmts_data"])

    def _check_cmts_found(self) -> None:
        missing_cmts_key: bool = "cmts_data" not in self.activation_data
        null_cmts_field: bool = self.activation_data.get("cmts_data") is None
        empty_cmts_data: bool = len(self.activation_data.get("cmts_data")) == 0
        failed_to_find_cmts: bool = missing_cmts_key or null_cmts_field or empty_cmts_data
        if failed_to_find_cmts:
            raise GraniteEligibilityException("Failed to find CMTS", self.activation_data)

    def _check_cmts_data_valid(self) -> None:
        REQUIRED_CMTS_DATA: set = {"vendor", "eq_type", "rpd", "cmts_ip", "hostname", "model"}
        if REQUIRED_CMTS_DATA != set(self.activation_data["cmts_data"].keys()):
            raise GraniteEligibilityException("Missing CMTS Data", list(self.activation_data["cmts_data"].keys()))
        if not all(self.activation_data["cmts_data"].values()):
            raise GraniteEligibilityException("Null CMTS Data Found", list(self.activation_data["cmts_data"]))

    def _query_rpd(self) -> None:
        params = {"CIRC_PATH_HUM_ID": self.activation_data["circuit_id"][1], "LVL": "1"}
        response = granite_get(GRANITE_ELEMENTS, params=params)
        if response and response[0]:
            self.activation_data["cmts_data"].update({"rpd": f"{response[0].get('CHAN_NAME')}:0"})
        else:
            raise GraniteEligibilityException("Invalid RPD Found", {})

    def _clean_ipv6(self) -> None:
        if "/" in self.activation_data.get("cmts_data", {})[1].get("cmts_ip"):
            self.activation_data["cmts_data"][1]["cmts_ip"] = (
                self.activation_data.get("cmts_data", {})[1].get("cmts_ip", "").split("/")[0]
            )

    def _gather_remaining_data(self, exception: Exception) -> None:
        if exception == CircuitIDEligilityException:
            self._cleanup_cid_exception()
        if exception == ServiceTypEligibilityException:
            self._cleanup_service_type_exception()
        if exception == RFCodesEligibilityException:
            self._check_granite_eligibility()

    def _cleanup_cid_exception(self) -> None:
        rf_codes = get_codes(self.eng_id)
        self._check_service_type_eligibility(rf_codes)
        self._check_rf_codes_eligibility(rf_codes)

    def _cleanup_service_type_exception(self) -> None:
        rf_codes = get_codes(self.eng_id)
        self._check_rf_codes_eligibility(rf_codes)
        self._check_granite_eligibility()

    def __str__(self) -> str:
        status = self.activation_data.get("eligible", ["Undetermined"])[0]
        return f"Eligibility Status for {self.eng_id}: {status}"
