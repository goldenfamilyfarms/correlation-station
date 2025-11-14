import json
import logging

logger = logging.getLogger(__name__)

root_url = "/palantir/v1/hvt/"


# tests for hvt/ctbh
def test_metrics_tid(client):
    """Test hvt/metrics with valid IPs and TIDs"""
    cid = "circuit_id=31.L1XX.003887..TWCC"
    a_tid = "a_side_tid=ONTRCACP70W"
    z_tid = "z_side_tid=RVSDCAYA70W"
    a_ip = "a_side_ip=173.196.33.5"
    z_ip = "z_side_ip=173.196.32.5"
    url = "{}ctbh?{}&{}&{}&{}&{}".format(root_url, cid, a_tid, a_ip, z_tid, z_ip)
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))
    assert resp.status_code == 200
    assert resp_data is not None


def test_metrics_invalid_params(client):
    """Test hvt/metrics with invalid TID"""
    cid = "circuit_id=31.L1XX.003887..TWCC"
    a_tid = "a_side_tid=ONTRCACP7@"
    z_tid = "z_side_tid=RVSDCAYA70W"
    a_ip = "a_side_ip=173.196.33.5"
    z_ip = "z_side_ip=173.196.32.5"

    # Testing invalid A TID
    url = "{}ctbh?{}&{}&{}&{}&{}".format(root_url, cid, a_tid, a_ip, z_tid, z_ip)
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))
    assert resp.status_code == 200
    assert "spectrum-error" in resp_data

    # Testing invalid Z TID
    a_tid = "a_side_tid=ONTRCACP70W"
    z_tid = "z_side_tid=ONTRCACP7@"

    url = "{}ctbh?{}&{}&{}&{}&{}".format(root_url, cid, a_tid, a_ip, z_tid, z_ip)
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))
    assert resp.status_code == 200
    assert "spectrum-error" in resp_data


def test_metrics_missing_params(client):
    """Test hvt/metrics with one parameter missing"""
    cid = "circuit_id=31.L1XX.003887..TWCC"
    a_tid = "a_side_tid=ONTRCACP70W"
    z_tid = "z_side_tid=RVSDCAYA70W"
    a_ip = "a_side_ip=173.196.33.5"
    z_ip = "z_side_ip=173.196.32.5"

    # testing with no A TID
    url = "{}ctbh?{}&{}&{}&{}".format(root_url, cid, a_ip, z_tid, z_ip)
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))
    assert resp_data["message"] == "necessary parameter missing"

    # testing with no Z TID
    url = "{}ctbh?{}&{}&{}&{}".format(root_url, cid, a_tid, a_ip, z_ip)
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))
    assert resp_data["message"] == "necessary parameter missing"

    # Testing with no A IP
    url = "{}ctbh?{}&{}&{}&{}".format(root_url, cid, a_tid, z_tid, z_ip)
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))
    assert resp_data["message"] == "necessary parameter missing"

    # Testing with no Z IP
    url = "{}ctbh?{}&{}&{}&{}".format(root_url, cid, a_tid, a_ip, z_tid)
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))
    assert resp_data["message"] == "necessary parameter missing"


# tests for hvt/metrics/pathid
def test_pathid_cid_successful(client):
    """Test hvt/metrics/{pathid} with valid CID and good Spectrum data"""
    pathid = "circuit_id=56.L1XX.000416..TWCC"
    url = "{}eece?{}".format(root_url, pathid)
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))
    assert resp.status_code == 200
    assert resp_data is not None


def test_pathid_cid_unsuccessful(client):
    """Test hvt/metrics/{pathid} with valid CID but no Spectrum data"""
    pathid = "circuit_id=31.L1XX.003887..TWCC"
    url = "{}eece?{}".format(root_url, pathid)
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))
    assert resp.status_code == 200
    assert "spectrum-error" in resp_data


def test_pathid_cid_invalid(client):
    """Test hvt/metrics/{pathid} with an invalid CID"""
    pathid = "circuit_id=003887"
    url = "{}eece?{}".format(root_url, pathid)
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))
    assert resp.status_code == 200
    assert "Denodo gives an empty response" in resp_data["error"]
