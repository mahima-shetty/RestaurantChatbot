from __future__ import annotations

from query_engine import (
    get_customer_ids_by_name,
    get_customers_for_month_year,
    get_orders_by_customer_name,
    get_preference_summary_for_month_year,
    get_total_bill_for_month_year,
)


def test_get_total_bill_for_month_year_returns_numeric_text() -> None:
    result = get_total_bill_for_month_year(12, 2025)

    assert float(result) > 0


def test_get_customers_for_month_year_returns_customer_columns() -> None:
    result = get_customers_for_month_year(12, 2025)

    assert "customer_id" in result
    assert "dietary_preferences" in result


def test_get_preference_summary_for_month_year_returns_summary_rows() -> None:
    result = get_preference_summary_for_month_year(12, 2025)

    assert "dietary_preferences" in result
    assert "customer_count" in result


def test_get_customer_ids_by_name_returns_matching_customer() -> None:
    result = get_customer_ids_by_name("daniel")

    assert "1012" in result
    assert "Daniel Ross" in result


def test_get_orders_by_customer_name_returns_order_history() -> None:
    result = get_orders_by_customer_name("daniel")

    assert "Daniel Ross" in result
    assert "items_ordered" in result