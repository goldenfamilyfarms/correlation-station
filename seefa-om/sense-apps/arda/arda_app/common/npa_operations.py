import logging
import json

from common_sense.common.errors import abort
from arda_app.dll.denodo import get_npa_three_digits
from arda_app.dll.granite import get_granite
from urllib.parse import quote

logger = logging.getLogger(__name__)


def look_up_npa_digits_in_stored_json(zip_code):
    with open("arda_app/data/zip_npa.json") as j:
        data = json.load(j)

        for i in data:
            if i["zipcode"] == zip_code:
                return i["npa"]
        abort(500, f"No record found for zip code {zip_code}")


def get_npa_digits(zip_code):
    return get_npa_three_digits(zip_code)[0:2]


def get_npa_and_site_type_with_site(site):
    url = f"/sites?SITE_HUM_ID={quote(site)}"
    site_records = get_granite(url)

    if len(site_records) == 1:
        npa = site_records[0].get("npaNxx")

        if npa:
            npa = npa[:2]

        site_type = site_records[0].get("siteType")

        return npa, site_type
    else:
        # TODO fall out here?
        return None, None
