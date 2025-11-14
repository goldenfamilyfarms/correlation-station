import logging

from json import JSONDecodeError
from arda_app.dll.sense import get_thor
from common_sense.common.errors import abort


logger = logging.getLogger(__name__)


def thor_gsip_check(cid, prod_name, designed, raw_response=False):
    """GSIP THOR check if PASS or FAIL"""
    try:
        thor_response = execute_thor_rules_check(cid, designed)

        results = thor_results(thor_response)

        if raw_response:
            return results

        if results == "PASS":
            return (True, [])

        compliant = True
        for error in results:
            # ctbh secondary enni site name can be different than primary enni
            if "does not match the first element A-Side Site" in error and prod_name == "Carrier CTBH":
                pass
            elif error not in [
                "Design Exception Approved - skipping rule validation",
                "Invalid Port Status 'IN USE'.",
                'Invalid Port Status "IN USE".',
                "Invalid Port Status 'Ok'.",
                'Invalid Port Status "Ok".',
                "Invalid Service Type COM-MRS EPLAN.",
                "Invalid Service Type COM-MRS INTERNET DIA.",
                "Invalid Service Type COM-MRS_MSS DIA.",
                "Invalid Service Type COM-MSS DIA.",
                "Invalid Service Type COM-MANAGED WIFI DIA.",
                "Managed Service UDA = 'YES' - skipping rule validation",
                'Managed Service UDA = "YES" - skipping rule validation',
            ]:
                compliant = False
                break

        return compliant, results
    except JSONDecodeError:
        logger.exception("JSON decode error while parsing THOR response payload")
        abort(500, "Error while processing THOR response for GSIP validation")


def execute_thor_rules_check(cid, designed):
    endpoint = f"/thor/v2/{cid}?designed={designed}"

    return get_thor(endpoint)


def thor_results(data):
    if len(data["records"]):
        errors = []
        for x in data["records"]:
            errors.append(x.get("error_code"))
        return errors

    return "PASS"
