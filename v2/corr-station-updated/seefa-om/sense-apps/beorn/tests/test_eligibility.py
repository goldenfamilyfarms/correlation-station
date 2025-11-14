import json
import pytest

from beorn_app.bll.eligibility import automation_eligibility
from beorn_app.bll.eligibility import mdso_eligible


def get_mock_data(file_path):
    with open(file_path, "r") as f:
        data = json.load(f)
    return data


topology_mock_path = "tests/mock_data/eligibility/new/fia-new-elig-21.L1XX.990535..CHTR.json"
topology = get_mock_data(topology_mock_path)


class TestFIA:
    fia_topology = get_mock_data("tests/mock_data/topologies/fia_typical_topologies.json")
    fia_circuit_elements = get_mock_data("tests/mock_data/topologies/fia_typical_denodo.json")["elements"]

    @pytest.mark.unittest
    def test_get_supported_port_roles_prov_new(self):
        workstream = automation_eligibility.Provisioning(self.fia_topology, self.fia_circuit_elements)
        assert workstream.device_eligibility.supported_port_roles["MX"] == ["INNI", "ENNI", "UNI"]

    @pytest.mark.unittest
    def test_get_supported_port_roles_prov_change(self):
        workstream = automation_eligibility.ProvisioningChange(self.fia_topology, self.fia_circuit_elements)
        assert workstream.device_eligibility.supported_port_roles["MX"] == ["INNI", "ENNI", "UNI"]

    @pytest.mark.unittest
    def test_get_supported_port_roles_comp_new(self):
        workstream = automation_eligibility.ComplianceNew(self.fia_topology, self.fia_circuit_elements)
        assert workstream.device_eligibility.supported_port_roles["MX"] == ["INNI", "ENNI", "UNI"]

    @pytest.mark.unittest
    def test_get_supported_port_roles_comp_change(self):
        workstream = automation_eligibility.ComplianceChange(self.fia_topology, self.fia_circuit_elements)
        assert workstream.device_eligibility.supported_port_roles["MX"] == ["INNI", "ENNI", "UNI"]

    @pytest.mark.unittest
    def test_get_supported_port_roles_comp_disco(self):
        workstream = automation_eligibility.ComplianceDisconnect(self.fia_topology, self.fia_circuit_elements)
        assert workstream.device_eligibility.supported_port_roles["MX"] == ["INNI", "ENNI", "UNI"]


class TestELINE:
    eline_topology = get_mock_data("tests/mock_data/topologies/eline1_topologies.json")
    eline_circuit_elements = get_mock_data("tests/mock_data/topologies/eline1_denodo.json")["elements"]

    @pytest.mark.unittest
    def test_get_supported_port_roles_prov_new(self):
        workstream = automation_eligibility.Provisioning(self.eline_topology, self.eline_circuit_elements)
        assert workstream.device_eligibility.supported_port_roles["MX"] == ["INNI", "ENNI"]

    @pytest.mark.unittest
    def test_get_supported_port_roles_prov_change(self):
        workstream = automation_eligibility.ProvisioningChange(self.eline_topology, self.eline_circuit_elements)
        assert workstream.device_eligibility.supported_port_roles["MX"] == ["INNI", "ENNI", "UNI"]

    @pytest.mark.unittest
    def test_get_supported_port_roles_comp_new(self):
        workstream = automation_eligibility.ComplianceNew(self.eline_topology, self.eline_circuit_elements)
        assert workstream.device_eligibility.supported_port_roles["MX"] == ["INNI", "ENNI", "UNI"]

    @pytest.mark.unittest
    def test_get_supported_port_roles_comp_change(self):
        workstream = automation_eligibility.ComplianceChange(self.eline_topology, self.eline_circuit_elements)
        assert workstream.device_eligibility.supported_port_roles["MX"] == ["INNI", "ENNI", "UNI"]

    @pytest.mark.unittest
    def test_get_supported_port_roles_comp_disco(self):
        workstream = automation_eligibility.ComplianceDisconnect(self.eline_topology, self.eline_circuit_elements)
        assert workstream.device_eligibility.supported_port_roles["MX"] == ["INNI", "ENNI"]


class TestVOICE:
    voice_topology = get_mock_data("tests/mock_data/topologies/voice1_topologies.json")
    voice_circuit_elements = get_mock_data("tests/mock_data/topologies/voice1_denodo.json")["elements"]

    @pytest.mark.unittest
    def test_get_supported_port_roles_prov_new(self):
        workstream = automation_eligibility.Provisioning(self.voice_topology, self.voice_circuit_elements)
        assert workstream.device_eligibility.supported_port_roles["MX"] == ["INNI", "ENNI", "UNI"]

    @pytest.mark.unittest
    def test_get_supported_port_roles_prov_change(self):
        workstream = automation_eligibility.ProvisioningChange(self.voice_topology, self.voice_circuit_elements)
        assert workstream.device_eligibility.supported_port_roles["MX"] == ["INNI", "ENNI", "UNI"]

    @pytest.mark.unittest
    def test_get_supported_port_roles_comp_new(self):
        workstream = automation_eligibility.ComplianceNew(self.voice_topology, self.voice_circuit_elements)
        assert workstream.device_eligibility.supported_port_roles["MX"] == ["INNI", "ENNI", "UNI"]

    @pytest.mark.unittest
    def test_get_supported_port_roles_comp_change(self):
        workstream = automation_eligibility.ComplianceChange(self.voice_topology, self.voice_circuit_elements)
        assert workstream.device_eligibility.supported_port_roles["MX"] == ["INNI", "ENNI", "UNI"]

    @pytest.mark.unittest
    def test_get_supported_port_roles_comp_disco(self):
        workstream = automation_eligibility.ComplianceDisconnect(self.voice_topology, self.voice_circuit_elements)
        assert workstream.device_eligibility.supported_port_roles["MX"] == ["INNI", "ENNI", "UNI"]


class TestVIDEO:
    video_topology = get_mock_data("tests/mock_data/topologies/video_rphy_topologies.json")
    video_circuit_elements = get_mock_data("tests/mock_data/topologies/video_rphy_denodo.json")["elements"]

    @pytest.mark.unittest
    def test_get_supported_port_roles_prov_new(self):
        workstream = automation_eligibility.Provisioning(self.video_topology, self.video_circuit_elements)
        assert workstream.device_eligibility.supported_port_roles["MX"] == ["INNI", "ENNI", "UNI"]

    @pytest.mark.unittest
    def test_get_supported_port_roles_prov_change(self):
        workstream = automation_eligibility.ProvisioningChange(self.video_topology, self.video_circuit_elements)
        assert workstream.device_eligibility.supported_port_roles["MX"] == ["INNI", "ENNI", "UNI"]

    @pytest.mark.unittest
    def test_get_supported_port_comp_new(self):
        workstream = automation_eligibility.ComplianceNew(self.video_topology, self.video_circuit_elements)
        assert not workstream.device_eligibility.supported_port_roles

    @pytest.mark.unittest
    def test_get_supported_port_roles_comp_change(self):
        workstream = automation_eligibility.ComplianceChange(self.video_topology, self.video_circuit_elements)
        assert not workstream.device_eligibility.supported_port_roles

    @pytest.mark.unittest
    def test_get_supported_port_roles_comp_disco(self):
        workstream = automation_eligibility.ComplianceDisconnect(self.video_topology, self.video_circuit_elements)
        assert not workstream.device_eligibility.supported_port_roles


class TestCTBH:
    ctbh_topology = get_mock_data("tests/mock_data/topologies/ctbh_topologies.json")["PRIMARY"]
    ctbh_circuit_elements = get_mock_data("tests/mock_data/topologies/ctbh_denodo.json")["elements"]

    @pytest.mark.unittest
    def test_get_supported_port_roles_prov_new(self):
        workstream = automation_eligibility.Provisioning(self.ctbh_topology, self.ctbh_circuit_elements)
        assert workstream.device_eligibility.supported_port_roles["MX"] == ["INNI", "ENNI"]

    @pytest.mark.unittest
    def test_get_supported_port_roles_prov_change(self):
        workstream = automation_eligibility.ProvisioningChange(self.ctbh_topology, self.ctbh_circuit_elements)
        assert workstream.device_eligibility.supported_port_roles["MX"] == ["INNI", "ENNI"]

    @pytest.mark.unittest
    def test_get_supported_port_roles_comp_new(self):
        workstream = automation_eligibility.ComplianceNew(self.ctbh_topology, self.ctbh_circuit_elements)
        assert workstream.device_eligibility.supported_port_roles["MX"] == ["INNI", "ENNI"]

    @pytest.mark.unittest
    def test_get_supported_port_roles_comp_change(self):
        workstream = automation_eligibility.ComplianceChange(self.ctbh_topology, self.ctbh_circuit_elements)
        assert workstream.device_eligibility.supported_port_roles["MX"] == ["INNI", "ENNI"]

    @pytest.mark.unittest
    def test_get_supported_port_roles_comp_disco(self):
        workstream = automation_eligibility.ComplianceDisconnect(self.ctbh_topology, self.ctbh_circuit_elements)
        assert not workstream.device_eligibility.supported_port_roles


class TestNNI:
    topology = get_mock_data("tests/mock_data/topologies/typeII_fia_topology.json")
    topology["serviceType"] = "NNI"
    circuit_elements = get_mock_data("tests/mock_data/topologies/typeII_fia_denodo.json")["elements"]

    @pytest.mark.unittest
    def test_get_supported_port_roles_prov_new(self):
        workstream = automation_eligibility.Provisioning(self.topology, self.circuit_elements)
        assert workstream.device_eligibility.supported_port_roles["MX"] == ["INNI", "ENNI", "UNI"]

    @pytest.mark.unittest
    def test_get_supported_port_roles_prov_change(self):
        workstream = automation_eligibility.ProvisioningChange(self.topology, self.circuit_elements)
        assert not workstream.device_eligibility.supported_port_roles

    @pytest.mark.unittest
    def test_get_supported_port_roles_comp_new(self):
        workstream = automation_eligibility.ComplianceNew(self.topology, self.circuit_elements)
        assert workstream.device_eligibility.supported_port_roles["MX"] == ["INNI", "ENNI", "UNI"]

    @pytest.mark.unittest
    def test_get_supported_port_roles_comp_change(self):
        workstream = automation_eligibility.ComplianceChange(self.topology, self.circuit_elements)
        assert not workstream.device_eligibility.supported_port_roles

    @pytest.mark.unittest
    def test_get_supported_port_roles_comp_disco(self):
        workstream = automation_eligibility.ComplianceDisconnect(self.topology, self.circuit_elements)
        assert not workstream.device_eligibility.supported_port_roles


class TestELAN:
    topology = get_mock_data("tests/mock_data/topologies/elan1_topologies.json")
    circuit_elements = get_mock_data("tests/mock_data/topologies/elan1_denodo.json")["elements"]

    @pytest.mark.unittest
    def test_get_supported_port_roles_prov_new(self):
        workstream = automation_eligibility.Provisioning(self.topology, self.circuit_elements)
        assert workstream.device_eligibility.supported_port_roles["MX"] == ["INNI", "ENNI"]

    @pytest.mark.unittest
    def test_get_supported_port_roles_prov_change(self):
        workstream = automation_eligibility.ProvisioningChange(self.topology, self.circuit_elements)
        assert workstream.device_eligibility.supported_port_roles["MX"] == ["INNI", "ENNI"]

    @pytest.mark.unittest
    def test_get_supported_port_roles_comp_new(self):
        workstream = automation_eligibility.ComplianceNew(self.topology, self.circuit_elements)
        assert workstream.device_eligibility.supported_port_roles["MX"] == ["INNI", "ENNI"]

    @pytest.mark.unittest
    def test_get_supported_port_roles_comp_change(self):
        workstream = automation_eligibility.ComplianceChange(self.topology, self.circuit_elements)
        assert workstream.device_eligibility.supported_port_roles["MX"] == ["INNI", "ENNI"]

    @pytest.mark.unittest
    def test_get_supported_port_roles_comp_disco(self):
        workstream = automation_eligibility.ComplianceDisconnect(self.topology, self.circuit_elements)
        assert workstream.device_eligibility.supported_port_roles["MX"] == ["INNI", "ENNI"]

    @pytest.mark.unittest
    def test_missing_vpls_vlan_id_prov_new(self):
        self.topology["service"][0]["data"]["evc"][0]["vplsVlanId"] = None
        workstream = automation_eligibility.Provisioning(self.topology, self.circuit_elements)
        vpls_vlan_id_msg = workstream.service_eligibility.unsupported_service["reason"]["message"]
        assert vpls_vlan_id_msg == "Automation Unsupported:  Granite | Missing Data - VPLS VLAN ID: not populated"

    @pytest.mark.unittest
    def test_missing_vpls_vlan_id_prov_change(self):
        self.topology["service"][0]["data"]["evc"][0]["vplsVlanId"] = None
        workstream = automation_eligibility.ProvisioningChange(self.topology, self.circuit_elements)
        vpls_vlan_id_msg = workstream.service_eligibility.unsupported_service["reason"]["message"]
        assert vpls_vlan_id_msg == "Automation Unsupported:  Granite | Missing Data - VPLS VLAN ID: not populated"

    @pytest.mark.unittest
    def test_missing_vpls_vlan_id_comp_new(self):
        self.topology["service"][0]["data"]["evc"][0]["vplsVlanId"] = None
        workstream = automation_eligibility.ComplianceNew(self.topology, self.circuit_elements)
        vpls_vlan_id_msg = workstream.service_eligibility.unsupported_service["reason"]["message"]
        assert vpls_vlan_id_msg == "Automation Unsupported:  Granite | Missing Data - VPLS VLAN ID: not populated"

    @pytest.mark.unittest
    def test_missing_vpls_vlan_id_comp_change(self):
        self.topology["service"][0]["data"]["evc"][0]["vplsVlanId"] = None
        workstream = automation_eligibility.ComplianceChange(self.topology, self.circuit_elements)
        vpls_vlan_id_msg = workstream.service_eligibility.unsupported_service.get("reason", {}).get("message")
        assert vpls_vlan_id_msg is None

    @pytest.mark.unittest
    def test_missing_vpls_vlan_id_comp_disco(self):
        self.topology["service"][0]["data"]["evc"][0]["vplsVlanId"] = None
        workstream = automation_eligibility.ComplianceDisconnect(self.topology, self.circuit_elements)
        vpls_vlan_id_msg = workstream.service_eligibility.unsupported_service["reason"]["message"]
        assert vpls_vlan_id_msg == "Automation Unsupported:  Granite | Missing Data - VPLS VLAN ID: not populated"

    @pytest.mark.unittest
    def test_legacy_vpls_vlan_id_prov_new_false(self):
        self.topology["service"][0]["data"]["evc"][0]["vplsVlanId"] = "400"
        workstream = automation_eligibility.Provisioning(self.topology, self.circuit_elements)
        workstream.service_eligibility.set_legacy_vpls_vlan_id(
            self.topology["service"][0]["data"]["evc"][0]["vplsVlanId"]
        )
        assert workstream.service_eligibility.legacy_vpls_vlan_id is False

    @pytest.mark.unittest
    def test_legacy_vpls_vlan_id_prov_new_true(self):
        self.topology["service"][0]["data"]["evc"][0]["vplsVlanId"] = "0"
        workstream = automation_eligibility.Provisioning(self.topology, self.circuit_elements)
        workstream.service_eligibility.set_legacy_vpls_vlan_id(
            self.topology["service"][0]["data"]["evc"][0]["vplsVlanId"]
        )
        assert workstream.service_eligibility.legacy_vpls_vlan_id is True

    @pytest.mark.unittest
    def test_legacy_vpls_vlan_id_prov_change_false(self):
        self.topology["service"][0]["data"]["evc"][0]["vplsVlanId"] = "400"
        workstream = automation_eligibility.ProvisioningChange(self.topology, self.circuit_elements)
        workstream.service_eligibility.set_legacy_vpls_vlan_id(
            self.topology["service"][0]["data"]["evc"][0]["vplsVlanId"]
        )
        assert workstream.service_eligibility.legacy_vpls_vlan_id is False

    @pytest.mark.unittest
    def test_legacy_vpls_vlan_id_prov_change_true(self):
        self.topology["service"][0]["data"]["evc"][0]["vplsVlanId"] = "0"
        workstream = automation_eligibility.ProvisioningChange(self.topology, self.circuit_elements)
        workstream.service_eligibility.set_legacy_vpls_vlan_id(
            self.topology["service"][0]["data"]["evc"][0]["vplsVlanId"]
        )
        assert workstream.service_eligibility.legacy_vpls_vlan_id is True

    @pytest.mark.unittest
    def test_legacy_vpls_vlan_id_comp_new_false(self):
        self.topology["service"][0]["data"]["evc"][0]["vplsVlanId"] = "400"
        workstream = automation_eligibility.ComplianceNew(self.topology, self.circuit_elements)
        workstream.service_eligibility.set_legacy_vpls_vlan_id(
            self.topology["service"][0]["data"]["evc"][0]["vplsVlanId"]
        )
        assert workstream.service_eligibility.legacy_vpls_vlan_id is False

    @pytest.mark.unittest
    def test_legacy_vpls_vlan_id_comp_new_true(self):
        self.topology["service"][0]["data"]["evc"][0]["vplsVlanId"] = "0"
        workstream = automation_eligibility.ComplianceNew(self.topology, self.circuit_elements)
        workstream.service_eligibility.set_legacy_vpls_vlan_id(
            self.topology["service"][0]["data"]["evc"][0]["vplsVlanId"]
        )
        assert workstream.service_eligibility.legacy_vpls_vlan_id is True

    @pytest.mark.unittest
    def test_legacy_vpls_vlan_id_comp_change_false(self):
        self.topology["service"][0]["data"]["evc"][0]["vplsVlanId"] = "400"
        workstream = automation_eligibility.ComplianceChange(self.topology, self.circuit_elements)
        workstream.service_eligibility.set_legacy_vpls_vlan_id(
            self.topology["service"][0]["data"]["evc"][0]["vplsVlanId"]
        )
        assert workstream.service_eligibility.legacy_vpls_vlan_id is False

    @pytest.mark.unittest
    def test_legacy_vpls_vlan_id_comp_change_true(self):
        self.topology["service"][0]["data"]["evc"][0]["vplsVlanId"] = "0"
        workstream = automation_eligibility.ComplianceChange(self.topology, self.circuit_elements)
        workstream.service_eligibility.set_legacy_vpls_vlan_id(
            self.topology["service"][0]["data"]["evc"][0]["vplsVlanId"]
        )
        assert workstream.service_eligibility.legacy_vpls_vlan_id is True

    @pytest.mark.unittest
    def test_legacy_vpls_vlan_id_comp_disco_false(self):
        self.topology["service"][0]["data"]["evc"][0]["vplsVlanId"] = "400"
        workstream = automation_eligibility.ComplianceDisconnect(self.topology, self.circuit_elements)
        workstream.service_eligibility.set_legacy_vpls_vlan_id(
            self.topology["service"][0]["data"]["evc"][0]["vplsVlanId"]
        )
        assert workstream.service_eligibility.legacy_vpls_vlan_id is False

    @pytest.mark.unittest
    def test_legacy_vpls_vlan_id_comp_disco_true(self):
        self.topology["service"][0]["data"]["evc"][0]["vplsVlanId"] = "0"
        workstream = automation_eligibility.ComplianceDisconnect(self.topology, self.circuit_elements)
        workstream.service_eligibility.set_legacy_vpls_vlan_id(
            self.topology["service"][0]["data"]["evc"][0]["vplsVlanId"]
        )
        assert workstream.service_eligibility.legacy_vpls_vlan_id is True


elements = get_mock_data("tests/mock_data/topologies/fia_dv_mdso_model_v20210209_1.json")["elements"]


class TestDeviceEligibility:
    # FIA mock data
    device_eligibility = automation_eligibility.Provisioning(topology, elements).device_eligibility

    @pytest.mark.unittest
    def test_is_supported_vendor_true(self):
        supported = self.device_eligibility._is_supported_vendor("JUNIPER")
        assert supported

    @pytest.mark.unittest
    def test_is_supported_vendor_false(self):
        supported = self.device_eligibility._is_supported_vendor("HAUNTED EQUIPMENT")
        assert not supported

    @pytest.mark.unittest
    def test_is_supported_model_true(self):
        supported = self.device_eligibility._is_supported_model("MX960")
        assert supported

    @pytest.mark.unittest
    def test_is_supported_model_false(self):
        supported = self.device_eligibility._is_supported_model("SPOOKY MODEL")
        assert not supported

    @pytest.mark.unittest
    def test_is_supported_port_role_true(self):
        supported = self.device_eligibility._is_supported_port_role("INNI", "JUNIPER", "MX960")
        assert supported

    @pytest.mark.unittest
    def test_is_supported_port_role_false(self):
        supported = self.device_eligibility._is_supported_port_role("UNI", "JUNIPER", "QFX")
        assert not supported

    @pytest.mark.unittest
    def test_is_supported_equipment_status_true(self):
        topology = get_mock_data("tests/mock_data/topologies/video_rphy_topologies.json")
        elements = get_mock_data("tests/mock_data/topologies/video_rphy_denodo.json")["elements"]
        device_eligibility = automation_eligibility.Provisioning(topology, elements).device_eligibility
        supported = device_eligibility._is_supported_equipment_status("PE", "LIVE")
        assert supported

    @pytest.mark.unittest
    def test_is_supported_equipment_status_false(self):
        topology = get_mock_data("tests/mock_data/topologies/video_rphy_topologies.json")
        elements = get_mock_data("tests/mock_data/topologies/video_rphy_denodo.json")["elements"]
        device_eligibility = automation_eligibility.Provisioning(topology, elements).device_eligibility
        supported = device_eligibility._is_supported_equipment_status("CPE", "LIVE")
        assert not supported


class TestServiceEligibility:
    @pytest.mark.unittest
    def test_is_bgp_fia_true(self):
        bgp_fia = get_mock_data("tests/mock_data/topologies/fia_bgp.json")
        service_eligibility = automation_eligibility.ServiceEligibility(bgp_fia["elements"])
        is_bgp = service_eligibility._is_bgp_fia()
        assert is_bgp

    @pytest.mark.unittest
    def test_is_bgp_fia_false(self):
        fia = get_mock_data("tests/mock_data/topologies/fia_dv_mdso_model_v20210209_1.json")
        service_eligibility = automation_eligibility.ServiceEligibility(fia["elements"])
        is_bgp = service_eligibility._is_bgp_fia()
        assert not is_bgp

    @pytest.mark.unittest
    def test_is_swap_operation_true(self):
        fia = get_mock_data("tests/mock_data/topologies/fia_vlan_swap.json")
        service_eligibility = automation_eligibility.ServiceEligibility(fia["elements"])
        is_swap = service_eligibility._is_swap_operation()
        assert is_swap

    @pytest.mark.unittest
    def test_is_swap_operation_false(self):
        fia = get_mock_data("tests/mock_data/topologies/fia_dv_mdso_model_v20210209_1.json")
        service_eligibility = automation_eligibility.ServiceEligibility(fia["elements"])
        is_swap = service_eligibility._is_swap_operation()
        assert not is_swap

    @pytest.mark.unittest
    def test_is_cevlan_true(self):
        cevlan = get_mock_data("tests/mock_data/topologies/cevlan.json")
        service_eligibility = automation_eligibility.ServiceEligibility(cevlan)
        is_cevlan = service_eligibility._is_cevlan()
        assert is_cevlan

    @pytest.mark.unittest
    def test_is_cevlan_false(self):
        cevlan_same_as_svlan = get_mock_data("tests/mock_data/topologies/cevlan_same_as_svlan.json")
        service_eligibility = automation_eligibility.ServiceEligibility(cevlan_same_as_svlan)
        is_cevlan = service_eligibility._is_cevlan()
        assert not is_cevlan

    @pytest.mark.unittest
    def test_get_svlans(self):
        mx_uni_circuit = get_mock_data("tests/mock_data/eligibility/single_vlan.json")
        service_eligibility = automation_eligibility.ServiceEligibility(mx_uni_circuit)
        equipment = get_mock_data("tests/mock_data/eligibility/single_vlan_equipment.json")
        svlans = service_eligibility._get_svlans(equipment)
        assert svlans == {"1204"}

    @pytest.mark.unittest
    def test_get_svlans_mx_uni(self):
        mx_uni_circuit = get_mock_data("tests/mock_data/eligibility/mx_uni.json")
        service_eligibility = automation_eligibility.ServiceEligibility(mx_uni_circuit)
        equipment = get_mock_data("tests/mock_data/eligibility/mx_uni_equipment.json")
        svlans = service_eligibility._get_svlans(equipment)
        assert svlans == {"1204"}

    @pytest.mark.unittest
    def test_get_svlans_multiple_non_uni(self):
        mx_uni_circuit = get_mock_data("tests/mock_data/eligibility/multi_vlan.json")
        service_eligibility = automation_eligibility.ServiceEligibility(mx_uni_circuit)
        equipment = get_mock_data("tests/mock_data/eligibility/multi_vlan_equipment.json")
        svlans = service_eligibility._get_svlans(equipment)
        assert svlans == {"1204", "1239"}

    @pytest.mark.unittest
    def test_get_svlans_multiple_uni(self):
        mx_uni_circuit = get_mock_data("tests/mock_data/eligibility/uni_multi_vlan.json")
        service_eligibility = automation_eligibility.ServiceEligibility(mx_uni_circuit)
        equipment = get_mock_data("tests/mock_data/eligibility/uni_multi_vlan_equipment.json")
        svlans = service_eligibility._get_svlans(equipment)
        assert svlans == {"1204", "1239"}

    @pytest.mark.unittest
    def test_are_multiple_vlans_true(self):
        fia = get_mock_data("tests/mock_data/topologies/fia_dv_mdso_model_v20210209_1.json")
        fia["elements"][0]["data"][1]["chan_name"] = "VLAN1111"
        service_eligibility = automation_eligibility.ServiceEligibility(fia["elements"])
        multiple_vlans = service_eligibility._are_multiple_vlans()
        assert multiple_vlans

    @pytest.mark.unittest
    def test_are_multiple_vlans_false(self):
        fia = get_mock_data("tests/mock_data/topologies/fia_dv_mdso_model_v20210209_1.json")
        service_eligibility = automation_eligibility.ServiceEligibility(fia["elements"])
        multiple_vlans = service_eligibility._are_multiple_vlans()
        assert not multiple_vlans

    @pytest.mark.unittest
    def test_is_supported_service_type_true(self):
        fia = get_mock_data("tests/mock_data/topologies/fia_dv_mdso_model_v20210209_1.json")
        service_eligibility = automation_eligibility.ServiceEligibility(fia["elements"])
        service_eligibility.eligible_products = mdso_eligible.PROVISIONING_SERVICES
        supported = service_eligibility._is_supported_service_type()
        assert supported

    @pytest.mark.unittest
    def test_is_supported_service_type_false(self):
        fia = get_mock_data("tests/mock_data/topologies/fia_dv_mdso_model_v20210209_1.json")
        fia["elements"][0]["service_type_full"] = "UNSUPPORTED"
        service_eligibility = automation_eligibility.ServiceEligibility(fia["elements"])
        service_eligibility.eligible_products = mdso_eligible.PROVISIONING_SERVICES
        supported = service_eligibility._is_supported_service_type()
        assert not supported
