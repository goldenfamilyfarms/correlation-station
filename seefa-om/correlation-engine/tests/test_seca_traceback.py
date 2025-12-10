from app.seca_xlsx_processor import SECAXLSXProcessor


def test_extract_traceback_and_files():
    sample = '''Some log lines
Traceback (most recent call last):
  File "/bp2/data/contexts/201/model-definitions/scripts/common_plan.py", line 434, in run
    response = self.process()
  File "/bp2/data/contexts/201/model-definitions/scripts/worker.py", line 58, in process
    raise Exception(f"Unable to connect to device at DEVICE.FQDN.COM")
Exception: Unable to connect to device at DEVICE.FQDN.COM

2025-12-10 01:42:08 INFO Next log
'''

    tb = SECAXLSXProcessor.extract_traceback(sample)
    assert tb is not None
    assert 'Traceback (most recent call last):' in tb

    files = SECAXLSXProcessor.extract_affected_files(tb)
    assert '/bp2/data/contexts/201/model-definitions/scripts/common_plan.py' in files
    assert '/bp2/data/contexts/201/model-definitions/scripts/worker.py' in files


def test_extract_log_file_from_orch_trace():
    single = {"timestamp": "01:42:08", "state": "FAILED", "log_file": "plan-script-abc-2025-12-10T01:41:08.538Z"}
    assert SECAXLSXProcessor.extract_log_file_from_orch_trace(single) == "plan-script-abc-2025-12-10T01:41:08.538Z"

    lst = [
        {"timestamp": "01:41:00", "state": "OK"},
        {"timestamp": "01:42:08", "state": "FAILED", "log_file": "plan-script-xyz"}
    ]

    assert SECAXLSXProcessor.extract_log_file_from_orch_trace(lst) == "plan-script-xyz"
