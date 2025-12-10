import tempfile
import os
from app.seca_xlsx_processor import SECAXLSXProcessor
import pandas as pd


def test_generate_reformatted_xlsx_creates_file():
    cols = [f'col{i}' for i in range(1, 35)]
    row1 = [""] * 34
    row1[3] = 'A.CKT.1'
    row1[4] = 'Error B'
    row1[6] = 'Product'
    row1[9] = 'SRV'
    row1[18] = '2025-12-10 01:59:32'

    row2 = [""] * 34
    row2[3] = 'B.CKT.2'
    row2[4] = 'Error A'
    row2[6] = 'Product'
    row2[9] = 'SRV'
    row2[18] = '2025-12-10 02:00:00'

    df = pd.DataFrame([row1, row2], columns=cols)

    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        path = tmp.name
    df.to_excel(path, index=False)

    proc = SECAXLSXProcessor(path)
    proc.load_xlsx()
    proc.parse_circuit_data()

    out = path + '-reformatted.xlsx'
    try:
        res = proc.generate_reformatted_xlsx(out)
        assert os.path.exists(res)
    finally:
        try:
            os.remove(path)
        except Exception:
            pass
        try:
            os.remove(out)
        except Exception:
            pass
