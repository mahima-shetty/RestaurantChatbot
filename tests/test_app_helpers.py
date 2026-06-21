from __future__ import annotations

from app import _clean_generated_expression, _format_query_output_for_user


def test_clean_generated_expression_strips_code_fences() -> None:
    response_text = "```python\nsales_df['bill_amount'].sum()\n```"

    assert _clean_generated_expression(response_text) == "sales_df['bill_amount'].sum()"


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