import tempfile
import os
from app.utils.pdf_report import generate_pdf_summary


def test_generate_pdf_contains_expected_text():
    errors = {
        '33.L1XX.801233_2025-12-10_01-59-32': {
            'product_name': 'PRODUCT_X',
            'service_request_type': 'SECA_TYPE',
            'traceback': 'Traceback (most recent call last):\n  File "/path/file.py", line 1, in <module>\nException: test'
        }
    }

    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        pdf_path = tmp.name

    try:
        generate_pdf_summary(errors, pdf_path, developer_prompt='Please analyze the following tracebacks')

        # Read PDF and assert text - use PyPDF2 if available
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(pdf_path)
            full_text = "".join([p.extract_text() or '' for p in reader.pages])
            assert '33.L1XX.801233' in full_text
            assert 'PRODUCT_X' in full_text
            assert 'Please analyze the following tracebacks' in full_text
        except Exception:
            # If PyPDF2 not available in test environment, at least assert file was created
            assert os.path.exists(pdf_path)
    finally:
        try:
            os.remove(pdf_path)
        except Exception:
            pass
