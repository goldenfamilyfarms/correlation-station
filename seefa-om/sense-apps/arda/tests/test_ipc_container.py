import pytest

from arda_app.api import ipc_container as ipc


@pytest.mark.unittest
def test_v1_ipc_container(monkeypatch):
    payload = {"cid": "21.L1XX.012345..CHTR"}

    # bad test abort - No IPC container data found
    monkeypatch.setattr(ipc, "get_circuit_info_and_map_legacy", lambda *args, **kwargs: None)

    with pytest.raises(Exception):
        assert ipc.ipc_container_endpoint(payload) is None

    # good test
    monkeypatch.setattr(
        ipc, "get_circuit_info_and_map_legacy", lambda *args, **kwargs: {"ipc_path": "/texas/ipc/container"}
    )

    assert ipc.ipc_container_endpoint(payload) == {"ipam_container": "/texas/ipc/container"}
