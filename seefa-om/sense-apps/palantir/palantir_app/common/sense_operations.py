"""This file is used to store methods that handle more involved calls to sense products"""

from palantir_app.dll.sense import post_sense


def arda_cpe_swap(cid, device_tid, new_model, new_vendor, timeout=60):
    # call arda cpe swap endpoint
    # update granite with correct cpe based on network discovery
    updated_cpe_data = {"cid": cid, "device_tid": device_tid, "new_model": new_model, "new_vendor": new_vendor}
    return post_sense("/arda/v1/cpe_swap/", timeout=timeout, payload=updated_cpe_data)
