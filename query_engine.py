from __future__ import annotations

import traceback
from pathlib import Path

import pandas as pd


DATA_DIR = Path(__file__).resolve().parent / "data"

customers_df = pd.read_excel(DATA_DIR / "customers_data.xlsx")
sales_df = pd.read_excel(DATA_DIR / "sales_data.xlsx")
sales_df["date"] = pd.to_datetime(sales_df["date"], errors="coerce")


def execute_pandas_query(code_string: str) -> str:
    """Run a pandas code snippet on the Excel data and return the result as text.

    If the code breaks, this returns the error details as a string so the caller
    can see what went wrong.
    """
    try:
        result = eval(
            code_string,
            {"pd": pd},
            {"customers_df": customers_df, "sales_df": sales_df},
        )
        return str(result)
    except Exception:
        return traceback.format_exc()
