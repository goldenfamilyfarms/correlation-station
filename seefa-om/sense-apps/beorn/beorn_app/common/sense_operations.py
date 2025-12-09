"""This file is used to store methods that handle more involved calls to sense products"""

from beorn_app.dll.sense import sense_get, sense_post


# todo: this is here in the case we start polling palantir for resource status rather than EXPO doing it.
#  The intention is to remove extra sense calls from EXPO's plate. This is not used today.
def poll_palantir(resource, resp_code):
    iterations, secs_per_loop = 1, 600
    endpoint = f"v4/resourcestatus?resourceId={resource}&poll_counter={iterations}&poll_sleep={secs_per_loop}"
    poll = sense_get("palantir", endpoint)
    return {"status": poll["status"], "message": poll["message"]}, resp_code


def arda_cpe_swap(cid, device_tid, new_model, new_vendor, best_effort=False, timeout=60):
    # call arda cpe swap endpoint
    # update granite with correct cpe based on network discovery
    updated_cpe_data = {"cid": cid, "device_tid": device_tid, "new_model": new_model, "new_vendor": new_vendor}
    return sense_post("arda", "v1/cpe_swap/", timeout=timeout, best_effort=best_effort, json=updated_cpe_data)
