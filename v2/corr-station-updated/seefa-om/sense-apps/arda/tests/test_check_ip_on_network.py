import pytest

import arda_app.api.check_ip_on_network as ip


@pytest.mark.unittest
def test_v1_ipc_container(monkeypatch):
    # bad test - IP not in CIDR notation
    with pytest.raises(Exception):
        assert ip.check_ip_on_network_endpoint("108.176.59.176", "PGHKNY091CW") is None

    # good test - IPs in use
    monkeypatch.setattr(ip, "mdso_static_validation", lambda *args, **kwargs: "IP in use")
    assert ip.check_ip_on_network_endpoint("108.176.59.176/29", "PGHKNY091CW") == {"ip_in_use": True}

    # good test - IPs not in use
    monkeypatch.setattr(ip, "mdso_static_validation", lambda *args, **kwargs: None)
    assert ip.check_ip_on_network_endpoint("108.176.59.176/29", "PGHKNY091CW") == {"ip_in_use": False}
