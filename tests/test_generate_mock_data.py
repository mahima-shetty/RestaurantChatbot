from __future__ import annotations

from pathlib import Path

import pandas as pd

from generate_mock_data import build_customers, build_sales


def test_build_customers_has_no_missing_dietary_preferences() -> None:
    customers = build_customers()

    assert customers["dietary_preferences"].isna().sum() == 0
    assert "No preference" in customers["dietary_preferences"].tolist()
    assert len(customers) >= 60
    assert customers["customer_id"].is_unique


def test_customers_excel_round_trip_preserves_dietary_preferences(tmp_path: Path) -> None:
    customers = build_customers()
    output_path = tmp_path / "customers.xlsx"

    customers.to_excel(output_path, index=False, engine="openpyxl")
    reloaded = pd.read_excel(output_path)

    assert reloaded["dietary_preferences"].isna().sum() == 0
    assert "No preference" in reloaded["dietary_preferences"].tolist()


def test_build_sales_contains_expected_columns() -> None:
    sales = build_sales()

    assert list(sales.columns) == [
        "order_id",
        "customer_id",
        "items_ordered",
        "bill_amount",
        "date",
    ]
    assert len(sales) >= 360
    assert sales["order_id"].is_unique


def test_build_sales_customer_ids_exist_in_customers() -> None:
    customers = build_customers()
    sales = build_sales()

    customer_ids = set(customers["customer_id"])
    assert set(sales["customer_id"]).issubset(customer_ids)