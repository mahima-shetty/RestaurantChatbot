from __future__ import annotations

import traceback
from pathlib import Path

import pandas as pd

from run_logger import traced


DATA_DIR = Path(__file__).resolve().parent / "data"

customers_df = pd.read_excel(DATA_DIR / "customers_data.xlsx")
sales_df = pd.read_excel(DATA_DIR / "sales_data.xlsx")
sales_df["date"] = pd.to_datetime(sales_df["date"], errors="coerce")


def _sales_for_month_year(month: int, year: int) -> pd.DataFrame:
    """Return sales rows for a specific month and year."""
    return sales_df[
        (sales_df["date"].dt.month == month) & (sales_df["date"].dt.year == year)
    ].copy()


def _customers_matching_name(name_query: str) -> pd.DataFrame:
    """Return customers whose names match the provided text query."""
    normalized_query = (name_query or "").strip()
    return customers_df[
        customers_df["name"].str.contains(normalized_query, case=False, na=False)
    ].copy()


@traced
def get_total_bill_for_month_year(month: int, year: int) -> str:
    """Return the total bill amount for all orders in a given month and year."""
    filtered_sales = _sales_for_month_year(month, year)
    return str(round(float(filtered_sales["bill_amount"].sum()), 2))


@traced
def get_customers_for_month_year(month: int, year: int) -> str:
    """Return unique customers who placed orders in a given month and year."""
    filtered_sales = _sales_for_month_year(month, year)
    customer_rows = (
        filtered_sales[["customer_id"]]
        .drop_duplicates()
        .merge(
            customers_df[["customer_id", "name", "dietary_preferences"]],
            on="customer_id",
            how="left",
        )
        .sort_values("customer_id")
        .reset_index(drop=True)
    )
    return customer_rows.to_string(index=False)


@traced
def get_preference_summary_for_month_year(month: int, year: int) -> str:
    """Return the dietary preference distribution for customers ordering in a month."""
    filtered_sales = _sales_for_month_year(month, year)
    summary = (
        filtered_sales[["customer_id"]]
        .drop_duplicates()
        .merge(
            customers_df[["customer_id", "dietary_preferences"]],
            on="customer_id",
            how="left",
        )["dietary_preferences"]
        .value_counts()
        .rename_axis("dietary_preferences")
        .reset_index(name="customer_count")
    )
    return summary.to_string(index=False)


@traced
def get_customer_ids_by_name(name_query: str) -> str:
    """Return matching customer IDs and names for a customer-name lookup."""
    matched_customers = _customers_matching_name(name_query)
    result = matched_customers[["customer_id", "name"]].reset_index(drop=True)
    return result.to_string(index=False)


@traced
def get_orders_by_customer_name(name_query: str) -> str:
    """Return orders placed by customers whose names match the query."""
    matched_customers = _customers_matching_name(name_query)
    result = (
        sales_df.merge(
            matched_customers[["customer_id", "name"]],
            on="customer_id",
            how="inner",
        )[["customer_id", "name", "order_id", "items_ordered", "bill_amount", "date"]]
        .sort_values(["customer_id", "order_id"])
        .reset_index(drop=True)
    )
    return result.to_string(index=False)


@traced
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
