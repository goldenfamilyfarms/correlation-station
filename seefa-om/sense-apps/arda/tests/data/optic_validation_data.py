def mock_payload_with_decimal():
    return {
        "remedy_fields": {
            "cid": "61.L1XX.007137..CHTR",
            "work_order_id": "WO0000011921102",
            "status": "Completed",
            "construction_complete": "\n No\n ",
            "pe_device": "SWNSILBL0QW/001.0001.004.24/SWT#1",
            "pe_port_number": "GE-1/0/47",
            "optic_format": "< 80km SFP",
            "fiber_distance": "2.5",
            "target_wavelength": "1561.42",
            "prism_id": "4006981",
            "order_number": "ENG-03605732",
            "mux_change_required": "No",
            "actual_wavelength_used": "1535.82",
            "closure_reason": "With Wavelength Change",
            "dwdm_overlay": "dwdm_overlay",
            "work_detail_notes": "Notes",
            "completed_date": "2022-08-12T11:32:45-05:00",
        },
        "sales_force_fields": {
            "construction_complete_date": "not completed",
            "email": "manager",
            "prism_construction_coord_email": "email",
        },
        "prism_fields": {
            "process_state": "state",
            "project_status": "status",
            "construction_coordinator": "coordinator",
            "wavelength": "1549.32",
        },
        "opticwave": {
            "interface_bandwidth": 1000,
            "wavelength_change": True,
            "wavelength_match": False,
            "construction_complete": "no",
            "acceptable_change": True,
            "pat_link": "'LIGHT_TEST_URL'/'SWNSILBL0QW'/'4006981'/'GE-1/0/47'",
            "optic_size_match": True,
            "mdso_port_info": "mdso_port_info",
            "actual_wavelength": "1549.32",
            "pe_device": "SWNSILBL0QW/001.0001.004.24/SWT#1",
            "pe_port_number": "GE-1/0/47",
            "target_wavelength": "1561.42",
        },
    }


def mock_payload_with_decimal_2():
    return {
        "remedy_fields": {
            "cid": "61.L1XX.007137..CHTR",
            "work_order_id": "WO0000011921102",
            "status": "Completed",
            "construction_complete": "\n No\n ",
            "pe_device": "SWNSILBL0QW/001.0001.004.24/SWT#1",
            "pe_port_number": "GE-1/0/47",
            "optic_format": "< 80km SFP",
            "fiber_distance": "2.5",
            "target_wavelength": "1561.42",
            "prism_id": "4006981",
            "order_number": "ENG-03605732",
            "mux_change_required": "No",
            "actual_wavelength_used": "1535.82",
            "closure_reason": "With Wavelength Change",
            "dwdm_overlay": "dwdm_overlay",
            "work_detail_notes": "Notes",
            "completed_date": "2022-08-12T11:32:45-05:00",
        },
        "sales_force_fields": {
            "construction_complete_date": "not completed",
            "email": "manager",
            "prism_construction_coord_email": "email",
        },
        "prism_fields": {
            "process_state": "state",
            "project_status": "status",
            "construction_coordinator": "coordinator",
            "wavelength": "1549.32",
        },
        "opticwave": {
            "interface_bandwidth": 1000,
            "wavelength_change": True,
            "wavelength_match": True,
            "construction_complete": "no",
            "acceptable_change": True,
            "pat_link": "'LIGHT_TEST_URL'/'SWNSILBL0QW'/'4006981'/'GE-1/0/47'",
            "optic_size_match": True,
            "mdso_port_info": "mdso_port_info",
            "actual_wavelength": "1549.32",
            "pe_device": "SWNSILBL0QW/001.0001.004.24/SWT#1",
            "pe_port_number": "GE-1/0/47",
            "email": "test_email",
            "prism_construction_coord_email": "prism_construction_coord_email",
            "prism_id": "prism_id",
            "work_order_id": "work_order_id",
            "order_number": "order_number",
            "target_wavelength": "1561.42",
        },
    }


def mock_payload_no_decimal():
    return {
        "remedy_fields": {
            "cid": "61.L1XX.007137..CHTR",
            "work_order_id": "WO0000011921102",
            "status": "Completed",
            "construction_complete": "\n No\n ",
            "pe_device": "SWNSILBL0QW/001.0001.004.24/SWT#1",
            "pe_port_number": "GE-1/0/47",
            "optic_format": "< 80km SFP",
            "fiber_distance": "2.5",
            "target_wavelength": "1310 nm",
            "prism_id": "4006981",
            "order_number": "ENG-03605732",
            "mux_change_required": "No",
            "actual_wavelength_used": "1310 nm",
            "closure_reason": "Complete",
            "dwdm_overlay": "dwdm_overlay",
            "work_detail_notes": "Notes",
            "completed_date": "2022-08-12T11:32:45-05:00",
        },
        "sales_force_fields": {
            "construction_complete_date": "not completed",
            "email": "manager",
            "prism_construction_coord_email": "email",
        },
        "prism_fields": {
            "process_state": "state",
            "project_status": "status",
            "construction_coordinator": "coordinator",
            "wavelength": "1549.32",
        },
        "opticwave": {
            "interface_bandwidth": 1000,
            "wavelength_change": False,
            "wavelength_match": True,
            "construction_complete": "yes",
            "acceptable_change": True,
            "pat_link": "'LIGHT_TEST_URL'/'SWNSILBL0QW'/'4006981'/'GE-1/0/47'",
            "optic_size_match": True,
            "mdso_port_info": "mdso_port_info",
            "actual_wavelength": "1310 nm",
            "pe_device": "SWNSILBL0QW/001.0001.004.24/SWT#1",
            "pe_port_number": "GE-1/0/47",
        },
    }


def mock_payload_no_decimal_1():
    return {
        "remedy_fields": {
            "cid": "61.L1XX.007137..CHTR",
            "work_order_id": "WO0000011921102",
            "status": "Completed",
            "construction_complete": "\n No\n ",
            "pe_device": "SWNSILBL0QW/001.0001.004.24/SWT#1",
            "pe_port_number": "GE-1/0/47",
            "optic_format": "< 80km SFP",
            "fiber_distance": "2.5",
            "target_wavelength": "1310 nm",
            "prism_id": "4006981",
            "order_number": "ENG-03605732",
            "mux_change_required": "No",
            "actual_wavelength_used": "1310 nm",
            "closure_reason": "Complete",
            "dwdm_overlay": "dwdm_overlay",
            "work_detail_notes": "Notes",
            "completed_date": "2022-08-12T11:32:45-05:00",
        },
        "sales_force_fields": {
            "construction_complete_date": "not completed",
            "email": "manager",
            "prism_construction_coord_email": "email",
        },
        "prism_fields": {
            "process_state": "state",
            "project_status": "status",
            "construction_coordinator": "coordinator",
            "wavelength": "1549.32",
        },
        "opticwave": {
            "interface_bandwidth": 1000,
            "wavelength_change": False,
            "wavelength_match": True,
            "construction_complete": "yes",
            "acceptable_change": True,
            "pat_link": "'LIGHT_TEST_URL'/'SWNSILBL0QW'/'4006981'/'GE-1/0/47'",
            "optic_size_match": True,
            "mdso_port_info": "mdso_port_info",
            "actual_wavelength": "1310 nm",
            "pe_device": "SWNSILBL0QW/001.0001.004.24/SWT#1",
            "pe_port_number": "GE-1/0/47",
            "target_wavelength": "1310 nm",
        },
    }


def mock_payload_no_decimal_3():
    return {
        "remedy_fields": {
            "cid": "61.L1XX.007137..CHTR",
            "work_order_id": "WO0000011921102",
            "status": "Completed",
            "construction_complete": "\n No\n ",
            "pe_device": "SWNSILBL0QW/001.0001.004.24/SWT#1",
            "pe_port_number": "GE-1/0/47",
            "optic_format": "< 80km SFP",
            "fiber_distance": "2.5",
            "target_wavelength": "1310 nm",
            "prism_id": "4006981",
            "order_number": "ENG-03605732",
            "mux_change_required": "No",
            "actual_wavelength_used": "1310 nm",
            "closure_reason": "Complete",
            "dwdm_overlay": "dwdm_overlay",
            "work_detail_notes": "Notes",
            "completed_date": "2022-08-12T11:32:45-05:00",
        },
        "sales_force_fields": {
            "construction_complete_date": "not completed",
            "email": "manager",
            "prism_construction_coord_email": "email",
        },
        "prism_fields": {
            "process_state": "state",
            "project_status": "status",
            "construction_coordinator": "coordinator",
            "wavelength": "1549.32",
        },
        "opticwave": {
            "interface_bandwidth": 1000,
            "wavelength_change": False,
            "wavelength_match": True,
            "construction_complete": "yes",
            "acceptable_change": True,
            "pat_link": "'LIGHT_TEST_URL'/'SWNSILBL0QW'/'4006981'/'GE-1/0/47'",
            "optic_size_match": False,
            "mdso_port_info": "mdso_port_info",
            "actual_wavelength": "1310 nm",
            "pe_device": "SWNSILBL0QW/001.0001.004.24/SWT#1",
            "pe_port_number": "GE-1/0/47",
            "target_wavelength": "1310 nm",
        },
    }


def mock_payload_no_decimal_4():
    return {
        "remedy_fields": {
            "cid": "61.L1XX.007137..CHTR",
            "work_order_id": "WO0000011921102",
            "status": "Completed",
            "construction_complete": "\n No\n ",
            "pe_device": "SWNSILBL0QW/001.0001.004.24/SWT#1",
            "pe_port_number": "GE-1/0/47",
            "optic_format": "< 80km SFP",
            "fiber_distance": "2.5",
            "target_wavelength": "1310 nm",
            "prism_id": "4006981",
            "order_number": "ENG-03605732",
            "mux_change_required": "No",
            "actual_wavelength_used": "1310 nm",
            "closure_reason": "Complete",
            "dwdm_overlay": "dwdm_overlay",
            "work_detail_notes": "Notes",
            "completed_date": "2022-08-12T11:32:45-05:00",
        },
        "sales_force_fields": {
            "construction_complete_date": "not completed",
            "email": "manager",
            "prism_construction_coord_email": "email",
        },
        "prism_fields": {
            "process_state": "state",
            "project_status": "status",
            "construction_coordinator": "coordinator",
            "wavelength": "1549.32",
        },
        "opticwave": {
            "interface_bandwidth": 1000,
            "wavelength_change": False,
            "wavelength_match": False,
            "construction_complete": "yes",
            "acceptable_change": True,
            "pat_link": "'LIGHT_TEST_URL'/'SWNSILBL0QW'/'4006981'/'GE-1/0/47'",
            "optic_size_match": True,
            "mdso_port_info": "mdso_port_info",
            "actual_wavelength": "1310 nm",
            "pe_device": "SWNSILBL0QW/001.0001.004.24/SWT#1",
            "pe_port_number": "GE-1/0/47",
            "target_wavelength": "1310 nm",
        },
    }


def mock_payload_xe_optic():
    return {
        "remedy_fields": {
            "cid": "61.L1XX.007137..CHTR",
            "work_order_id": "WO0000011921102",
            "status": "Completed",
            "construction_complete": "\n No\n ",
            "pe_device": "SWNSILBL0QW/001.0001.004.24/SWT#1",
            "pe_port_number": "XE-1/0/47",
            "optic_format": "< 80km SFP",
            "fiber_distance": "2.5",
            "target_wavelength": "1535.82",
            "prism_id": "4006981",
            "order_number": "ENG-03605732",
            "mux_change_required": "No",
            "actual_wavelength_used": "1535.82",
            "closure_reason": "Complete",
            "dwdm_overlay": "dwdm_overlay",
            "work_detail_notes": "Notes",
            "completed_date": "2022-08-12T11:32:45-05:00",
        },
        "sales_force_fields": {
            "construction_complete_date": "not completed",
            "email": "manager",
            "prism_construction_coord_email": "email",
        },
        "prism_fields": {
            "process_state": "state",
            "project_status": "status",
            "construction_coordinator": "coordinator",
            "wavelength": "1549.32",
        },
        "opticwave": {
            "interface_bandwidth": 10000,
            "wavelength_change": False,
            "wavelength_match": True,
            "construction_complete": "yes",
            "acceptable_change": True,
            "pat_link": "'LIGHT_TEST_URL'/'SWNSILBL0QW'/'4006981'/'GE-1/0/47'",
            "optic_size_match": False,
            "mdso_port_info": "mdso_port_info",
            "actual_wavelength": "1535.82",
            "pe_device": "SWNSILBL0QW/001.0001.004.24/SWT#1",
            "pe_port_number": "GE-1/0/47",
            "target_wavelength": "1535.82",
        },
    }


def mock_payload_xe_optic_1():
    return {
        "remedy_fields": {
            "cid": "61.L1XX.007137..CHTR",
            "work_order_id": "WO0000011921102",
            "status": "Completed",
            "construction_complete": "\n No\n ",
            "pe_device": "SWNSILBL0QW/001.0001.004.24/SWT#1",
            "pe_port_number": "XE-1/0/47",
            "optic_format": "< 80km SFP",
            "fiber_distance": "2.5",
            "target_wavelength": "1535.82",
            "prism_id": "4006981",
            "order_number": "ENG-03605732",
            "mux_change_required": "No",
            "actual_wavelength_used": "1535.82",
            "closure_reason": "Complete",
            "dwdm_overlay": "dwdm_overlay",
            "work_detail_notes": "Notes",
            "completed_date": "2022-08-12T11:32:45-05:00",
        },
        "sales_force_fields": {
            "construction_complete_date": "not completed",
            "email": "manager",
            "prism_construction_coord_email": "email",
        },
        "prism_fields": {
            "process_state": "state",
            "project_status": "status",
            "construction_coordinator": "coordinator",
            "wavelength": "1549.32",
        },
        "opticwave": {
            "interface_bandwidth": 10000,
            "wavelength_change": False,
            "wavelength_match": True,
            "construction_complete": "yes",
            "acceptable_change": True,
            "pat_link": "'LIGHT_TEST_URL'/'SWNSILBL0QW'/'4006981'/'GE-1/0/47'",
            "optic_size_match": True,
            "mdso_port_info": "mdso_port_info",
            "actual_wavelength": "1535.82",
            "pe_device": "SWNSILBL0QW/001.0001.004.24/SWT#1",
            "pe_port_number": "GE-1/0/47",
            "target_wavelength": "1535.82",
        },
    }


def mock_payload_unacceptable_change():
    return {
        "remedy_fields": {
            "cid": "61.L1XX.007137..CHTR",
            "work_order_id": "WO0000011921102",
            "status": "Completed",
            "construction_complete": "\n    Yes  \n ",
            "pe_device": "SWNSILBL0QW/001.0001.004.24/SWT#1",
            "pe_port_number": "GE-1/0/47",
            "optic_format": "< 80km SFP",
            "fiber_distance": "2.5",
            "target_wavelength": "1561.42",
            "prism_id": "4006981",
            "order_number": "ENG-03605732",
            "mux_change_required": "No",
            "actual_wavelength_used": "1535.82",
            "closure_reason": "With Wavelength Change",
            "dwdm_overlay": "dwdm_overlay",
            "work_detail_notes": "Notes",
            "completed_date": "2022-08-12T11:32:45-05:00",
        },
        "sales_force_fields": {
            "construction_complete_date": "not completed",
            "email": "manager",
            "prism_construction_coord_email": "email",
        },
        "prism_fields": {
            "process_state": "state",
            "project_status": "status",
            "construction_coordinator": "coordinator",
            "wavelength": "1549.32",
        },
        "opticwave": {
            "interface_bandwidth": 1000,
            "wavelength_change": True,
            "wavelength_match": True,
            "construction_complete": "yes",
            "acceptable_change": False,
            "pat_link": "'LIGHT_TEST_URL'/'SWNSILBL0QW'/'4006981'/'GE-1/0/47'",
            "optic_size_match": True,
            "mdso_port_info": "mdso_port_info",
            "actual_wavelength": "1535.82",
            "pe_device": "SWNSILBL0QW/001.0001.004.24/SWT#1",
            "pe_port_number": "GE-1/0/47",
            "target_wavelength": "1561.42",
        },
    }


def mock_payload_bad_port():
    return {
        "remedy_fields": {
            "cid": "61.L1XX.007137..CHTR",
            "work_order_id": "WO0000011921102",
            "status": "Completed",
            "construction_complete": "\n No\n ",
            "pe_device": "SWNSILBL0QW/001.0001.004.24/SWT#1",
            "pe_port_number": "1047",
            "optic_format": "< 80km SFP",
            "fiber_distance": "2.5",
            "target_wavelength": "1561.42",
            "prism_id": "4006981",
            "order_number": "ENG-03605732",
            "mux_change_required": "No",
            "actual_wavelength_used": "1535.82",
            "closure_reason": "With Wavelength Change",
            "dwdm_overlay": "dwdm_overlay",
            "work_detail_notes": "Notes",
            "completed_date": "2022-08-12T11:32:45-05:00",
        },
        "sales_force_fields": {
            "construction_complete_date": "not completed",
            "email": "manager",
            "prism_construction_coord_email": "email",
        },
        "prism_fields": {
            "process_state": "state",
            "project_status": "status",
            "construction_coordinator": "coordinator",
            "wavelength": "1549.32",
        },
    }


def mock_ports_info_with_decimal_cisco():
    return [
        {
            "fiber-mode": "SM",
            "cable-type": "GIGE 1000LH",
            "sfp-vendor-name": "CISCO-PR361-120",
            "port-number": "47",
            "sfp-vendor-pno": "SFP-3661-120-X",
            "sfp-vendor-fw-ver": "0.0",
            "wavelength": "1536 nm",
        }
    ]


def mock_ports_info_with_decimal_prolabs():
    return [
        {
            "fiber-mode": "SM",
            "cable-type": "GIGE 1000LH",
            "sfp-vendor-name": "PROLABS",
            "port-number": "47",
            "sfp-vendor-pno": "SFPD6142-120-JA",
            "sfp-vendor-fw-ver": "0.0",
            "wavelength": "1561 nm",
        }
    ]


def mock_ports_info_with_decimal_prolabssfpp():
    return [
        {
            "fiber-mode": "SM",
            "cable-type": "GIGE 1000LH",
            "sfp-vendor-name": "PROLABS",
            "port-number": "47",
            "sfp-vendor-pno": "SFPPDTCW1561.42",
            "sfp-vendor-fw-ver": "0.0",
            "wavelength": "1561 nm",
        }
    ]


def mock_ports_info_with_decimal_cisco_match():
    return [
        {
            "fiber-mode": "SM",
            "cable-type": "GIGE 1000SX",
            "sfp-vendor-name": "CISCO-PR3582-120",
            "port-number": "47",
            "sfp-vendor-pno": "SFP-3582",
            "sfp-vendor-fw-ver": "0.0",
            "wavelength": "1535 nm",
        }
    ]


def mock_ports_info_with_decimal_cisco_match_xe():
    return [
        {
            "fiber-mode": "SM",
            "cable-type": "10GBASE ZR",
            "sfp-vendor-name": "CISCO-PR3582-120",
            "port-number": "47",
            "sfp-vendor-pno": "SFP-3582",
            "sfp-vendor-fw-ver": "0.0",
            "wavelength": "1535 nm",
        }
    ]


def mock_ports_info_no_decimal():
    return [
        {
            "fiber-mode": "MM",
            "cable-type": "GIGE 1000SX",
            "sfp-vendor-name": "CISCO-AVAGO",
            "port-number": "47",
            "sfp-vendor-pno": "SFBR-5766PZ-CS1",
            "sfp-vendor-fw-ver": "0.0",
            "wavelength": "850 nm",
        }
    ]


def mock_ports_info_no_decimal_match():
    return [
        {
            "fiber-mode": "MM",
            "cable-type": "GIGE 1000SX",
            "sfp-vendor-name": "CISCO-AVAGO",
            "port-number": "47",
            "sfp-vendor-pno": "SFBR-5766PZ-CS1",
            "sfp-vendor-fw-ver": "0.0",
            "wavelength": "1310 nm",
        }
    ]


def mock_ports_info_optic_mismatch():
    return [
        {
            "fiber-mode": "MM",
            "cable-type": "10GBASE ZR",
            "sfp-vendor-name": "CISCO-AVAGO",
            "port-number": "47",
            "sfp-vendor-pno": "SFBR-5766PZ-CS1",
            "sfp-vendor-fw-ver": "0.0",
            "wavelength": "1310 nm",
        }
    ]


def mock_ports_info_optic_mismatch_xe():
    return [
        {
            "fiber-mode": "SM",
            "cable-type": "GIGE 1000LH",
            "sfp-vendor-name": "CISCO-PR3582-120",
            "port-number": "47",
            "sfp-vendor-pno": "SFP-3582",
            "sfp-vendor-fw-ver": "0.0",
            "wavelength": "1535 nm",
        }
    ]
