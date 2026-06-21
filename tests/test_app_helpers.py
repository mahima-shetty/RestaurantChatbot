from __future__ import annotations

from app import (
    _clean_generated_expression,
    _format_query_output_for_user,
    _route_domain_tool_from_text,
)


def test_clean_generated_expression_strips_code_fences() -> None:
    response_text = "```python\nsales_df['bill_amount'].sum()\n```"

    assert _clean_generated_expression(response_text) == "sales_df['bill_amount'].sum()"


def test_clean_generated_expression_strips_explanatory_prefix() -> None:
    response_text = (
        "To answer the question: customers_df['dietary_preferences'].value_counts()"
    )

    assert (
        _clean_generated_expression(response_text)
        == "customers_df['dietary_preferences'].value_counts()"
    )


def test_format_query_output_for_user_handles_scalar_result() -> None:
    assert _format_query_output_for_user("689.0") == "Result: 689.0"


def test_format_query_output_for_user_handles_empty_dataframe() -> None:
    empty_output = "Empty DataFrame\nColumns: [order_id, customer_id]\nIndex: []"

    assert _format_query_output_for_user(empty_output) == "No matching records were found."


def test_format_query_output_for_user_handles_table_output() -> None:
    table_output = (
        "   order_id  customer_id  bill_amount\n"
        "0      5001         1001        24.50\n"
        "1      5002         1002        18.75"
    )

    formatted = _format_query_output_for_user(table_output)

    assert formatted.startswith("Here are the matching records:\n")
    assert "order_id" in formatted


def test_route_domain_tool_for_preference_summary() -> None:
    routed_tool = _route_domain_tool_from_text(
        "what are the majority customer preferences in dec 2025"
    )

    assert routed_tool == (
        "get_preference_summary_for_month_year",
        {"month": 12, "year": 2025},
    )


def test_route_domain_tool_for_total_bill() -> None:
    routed_tool = _route_domain_tool_from_text(
        "what is the total bill in nov 2025"
    )

    assert routed_tool == (
        "get_total_bill_for_month_year",
        {"month": 11, "year": 2025},
    )


def test_route_domain_tool_for_customer_id_lookup() -> None:
    routed_tool = _route_domain_tool_from_text("what is daniel cust_id")

    assert routed_tool == (
        "get_customer_ids_by_name",
        {"name_query": "daniel"},
    )


def test_route_domain_tool_for_orders_by_customer_name() -> None:
    routed_tool = _route_domain_tool_from_text("what did daniel ordered")

    assert routed_tool == (
        "get_orders_by_customer_name",
        {"name_query": "daniel"},
    )


def test_route_domain_tool_for_customer_list() -> None:
    routed_tool = _route_domain_tool_from_text(
        "list customers who ordered in dec 2025"
    )

    assert routed_tool == (
        "get_customers_for_month_year",
        {"month": 12, "year": 2025},
    )


def test_route_domain_tool_returns_none_for_generic_query() -> None:
    assert _route_domain_tool_from_text("show me pizza orders") is None