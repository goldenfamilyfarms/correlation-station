import tempfile
import pandas as pd
from app.seca_xlsx_processor import SECAXLSXProcessor


def test_parse_circuit_data_minimal():
    # Build a minimal dataframe matching expected columns
    # We'll create 23+ columns to match indices used in processor
    cols = [f'col{i}' for i in range(1, 26)]
    # Create a single row with values at the relevant indices
    row = [""] * 25
    row[3] = '33.L1XX.801233..TWCC'  # D (index 3)
    row[18] = pd.Timestamp('2025-12-10 01:59:32')  # S (index 18)
    row[9] = 'SECA_TYPE'  # J (index 9)
    row[6] = 'PRODUCT_X'  # G (index 6)
    row[4] = 'Example Error'  # E (index 4)
    row[22] = 'CDNC summary here'  # W (index 22)

    df = pd.DataFrame([row], columns=cols)

    # Write to a temp xlsx
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        path = tmp.name
    df.to_excel(path, index=False)

    proc = SECAXLSXProcessor(path)
    proc.load_xlsx()
    errors = proc.parse_circuit_data()

    assert len(errors) == 1
    key = list(errors.keys())[0]
    assert '33.L1XX.801233' in key
    err = errors[key]
    assert err.circuit_id.startswith('33.L1XX')
    assert err.product_name == 'PRODUCT_X'
