import socket

import palantir_app

system_health_results = {"tested": [], "untested": [], "passed": [], "failed": []}
test_failed = 0
test_passed = 1
test_skipped = 2


def are_systems_healthy(results):
    for key in dir(palantir_app.url_config):
        if key.isupper() and "_URL" in key:
            base_url = palantir_app.url_config.__getattribute__(key)
            status = test_failed  # assuming the worst
            for _i in range(3):
                status = check_oss_connection(base_url)
                if status == test_passed:
                    break
                elif status == test_failed:
                    # try 3 times to get a good result
                    continue
                else:  # status == test_skipped for now
                    results["untested"].append(base_url)
                    next(key)

            if status is test_passed:
                results["passed"].append(base_url)
                results["tested"].append(base_url)
            else:
                results["failed"].append(base_url)
                results["tested"].append(base_url)

    if len(results["failed"]) > 0:
        return False
    else:
        return True


def check_oss_connection(base_url, timeout=5):
    if "https://" in base_url:
        default_port = 443
    elif "http://" in base_url:
        default_port = 80
    else:  # TODO: neither http nor https specified will require additional logic
        return test_skipped

    target_elements = base_url.split("//")[1]
    host_port = target_elements.split(":")
    count = len(host_port)
    if count == 1:
        # No Port Specified
        port = default_port
        host = host_port[0]
    elif count == 2:
        port = host_port[1]
        host = host_port[0]
    else:
        # Oh boy ...
        # TODO: handle unexpected compound urls
        return test_skipped

    test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    test_socket.settimeout(timeout)
    try:
        test_socket.connect((host, int(port)))
        test_socket.shutdown(socket.SHUT_RDWR)
        return test_passed
    except socket.error:
        return test_failed
    finally:
        test_socket.close()
