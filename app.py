from __future__ import annotations

import json
import os
import re
import traceback
from pathlib import Path
from typing import Any

from openai import OpenAI

from run_logger import initialize_run_log, log_event, traced
from query_engine import (
    execute_pandas_query,
    get_customer_ids_by_name,
    get_customers_for_month_year,
    get_orders_by_customer_name,
    get_preference_summary_for_month_year,
    get_total_bill_for_month_year,
)


PANDAS_QUERY_EXAMPLES = [
    "customers_df[customers_df['dietary_preferences'].str.lower() == 'vegetarian']",
    "customers_df[customers_df['name'].str.contains('john carter', case=False, na=False)]",
    "sales_df[sales_df['items_ordered'].str.contains('pizza', case=False, na=False)]",
    "sales_df[sales_df['date'].dt.strftime('%Y-%m-%d') == '2026-06-19']",
    "sales_df[(sales_df['date'].dt.day == 19) & (sales_df['date'].dt.month == 6)]",
    "sales_df.loc[sales_df['order_id'] == 5005, 'bill_amount'].iloc[0] * 2",
    "customers_df[customers_df['customer_id'] == 1005]",
    "customers_df[customers_df['email'].str.contains('example.com', case=False, na=False)]",
    "customers_df[['customer_id', 'name', 'dietary_preferences']].head(10)",
    "customers_df['dietary_preferences'].value_counts()",
    "customers_df[customers_df['dietary_preferences'].str.contains('halal', case=False, na=False)][['customer_id', 'name']]",
    "sales_df[sales_df['bill_amount'] > 25]",
    "sales_df.loc[sales_df['order_id'] == 5005, ['items_ordered', 'bill_amount']]",
    "sales_df[sales_df['customer_id'] == 1001]['bill_amount'].sum()",
    "sales_df[sales_df['items_ordered'].str.contains('biryani', case=False, na=False)][['order_id', 'customer_id', 'bill_amount']]",
    "sales_df[sales_df['date'].between('2026-06-01', '2026-06-30')]",
    "sales_df[sales_df['date'].dt.month == 6]",
    "sales_df[(sales_df['date'].dt.month == 6) & (sales_df['date'].dt.year == 2026)]['bill_amount'].mean()",
    "sales_df.sort_values('bill_amount', ascending=False).head(5)",
    "sales_df.nlargest(3, 'bill_amount')[['order_id', 'customer_id', 'bill_amount']]",
    "sales_df['bill_amount'].sum()",
    "sales_df['bill_amount'].mean()",
    "sales_df.groupby('customer_id', as_index=False)['bill_amount'].sum().sort_values('bill_amount', ascending=False).head(10)",
    "sales_df.groupby('customer_id')['order_id'].count().sort_values(ascending=False).head(10)",
    "sales_df.groupby(sales_df['date'].dt.month)['order_id'].count().sort_index()",
    "sales_df.assign(order_month=sales_df['date'].dt.to_period('M').astype(str)).groupby('order_month', as_index=False)['bill_amount'].sum().sort_values('order_month')",
    "sales_df.merge(customers_df[['customer_id', 'name']], on='customer_id', how='left')",
    "sales_df.merge(customers_df[['customer_id', 'name']], on='customer_id', how='left')[lambda df: df['name'].str.contains('priya', case=False, na=False)]",
    "sales_df[sales_df['customer_id'].isin([1001, 1002, 1003])]",
    "sales_df[sales_df['items_ordered'].str.contains('pizza', case=False, na=False)]['order_id'].nunique()",
    "sales_df.merge(customers_df[['customer_id', 'dietary_preferences']], on='customer_id', how='left').groupby('dietary_preferences', as_index=False)['bill_amount'].mean().sort_values('bill_amount', ascending=False)",
]
PANDAS_QUERY_EXAMPLES_TEXT = "\n".join(
    f"- {example}" for example in PANDAS_QUERY_EXAMPLES
)
MAX_QUERY_OUTPUT_LINES = 40
MAX_QUERY_REPAIR_ATTEMPTS = 2


SYSTEM_PROMPT = f"""You are a restaurant data assistant.
Always rely on the execute_pandas_query tool for any question about customer or sales data.
Do not guess, assume, or make up facts from the dataset.
If the answer depends on the data, use the tool first and then answer from the tool output.
When you call the tool, write pandas code against the preloaded DataFrames exactly as named:
- customers_df columns: customer_id, name, email, dietary_preferences
- sales_df columns: order_id, customer_id, items_ordered, bill_amount, date
For user-provided text values, prefer case-insensitive matching unless the user explicitly asks for exact case-sensitive matching.
Examples:
{PANDAS_QUERY_EXAMPLES_TEXT}
Prefer the domain tools first when they match the user's request:
- use get_total_bill_for_month_year(month, year) for total bill / total cost questions by month and year
- use get_customers_for_month_year(month, year) for listing customers who ordered in a given month and year
- use get_preference_summary_for_month_year(month, year) for majority / most common / popular dietary preference questions by month and year
- use get_customer_ids_by_name(name_query) for customer ID lookups by customer name
- use get_orders_by_customer_name(name_query) for questions about what a named customer ordered
Use execute_pandas_query only when the domain tools do not fit the user's request.
Treat sales_df['date'] as a datetime column. For natural-language date questions like '19 June', 'June 19', '19th June', or '2026-06-19', filter using .dt.day, .dt.month, .dt.year, or normalized date strings instead of .str.contains on the raw date column.
Use columns correctly:
- order_id and customer_id are numeric IDs
- items_ordered is text
- bill_amount is numeric
Never compare numeric IDs to items_ordered text.
For hypothetical questions like 'if order 5005 happened twice' or 'if 5005 was ordered twice', find the matching bill_amount and multiply it by 2.
If a bare numeric ID is in the 5000-series, treat it as order_id unless the user explicitly says customer/customer_id.
If a bare numeric ID is in the 1000-series, treat it as customer_id unless the user explicitly says order/order_id.
Use na=False with string matching to avoid errors on missing values.
After receiving tool output, answer in clear natural language."""

QUERY_GENERATION_PROMPT = f"""You translate restaurant data questions into a single pandas Python expression.
Return only one executable pandas expression as plain text.
Do not wrap the answer in markdown, backticks, JSON, XML, or explanations.
Use the already-loaded DataFrames exactly as named:
- customers_df columns: customer_id, name, email, dietary_preferences
- sales_df columns: order_id, customer_id, items_ordered, bill_amount, date
For user-provided text values, prefer case-insensitive matching.
Examples:
{PANDAS_QUERY_EXAMPLES_TEXT}
Treat sales_df['date'] as a datetime column. For natural-language date questions like '19 June', 'June 19', '19th June', or '2026-06-19', use .dt.day, .dt.month, .dt.year, or normalized date strings.
Use columns correctly:
- order_id and customer_id are numeric IDs
- items_ordered is text
- bill_amount is numeric
Never compare numeric IDs to items_ordered text.
For follow-up questions such as 'that', 'this', 'those', 'it', 'them', 'these customers', or 'this bill', reuse the most relevant filters from the recent conversation.
When combining multiple boolean conditions, always wrap each condition in parentheses before using & or |.
For column selection after filtering, prefer patterns like sales_df.loc[mask, ['order_id', 'customer_id', 'bill_amount']] or sales_df[mask][['order_id', 'customer_id', 'bill_amount']].
When the user asks for customers who ordered in a period, prefer joining sales_df to customers_df so names can be returned.
When the user asks for a total cost or total bill, return a numeric expression over the filtered bill_amount column, usually with .sum().
For hypothetical questions like 'if order 5005 happened twice' or 'if 5005 was ordered twice', return a numeric expression that multiplies the matching bill_amount.
If a bare numeric ID is in the 5000-series, treat it as order_id unless the user explicitly says customer/customer_id.
If a bare numeric ID is in the 1000-series, treat it as customer_id unless the user explicitly says order/order_id.
Use na=False with string matching to avoid errors on missing values.
Return only the pandas expression."""

QUERY_REPAIR_PROMPT = """You repair invalid pandas expressions for restaurant data queries.
Return only one corrected executable pandas expression as plain text.
Do not return explanations, markdown, backticks, or JSON.
Available DataFrames are exactly:
- customers_df columns: customer_id, name, email, dietary_preferences
- sales_df columns: order_id, customer_id, items_ordered, bill_amount, date
Rules:
- Preserve the user's original intent.
- If there are multiple boolean conditions, wrap each condition in parentheses before using & or |.
- When selecting columns after filtering, use .loc[mask, ['col1', 'col2']] or df[mask][['col1', 'col2']].
- Treat sales_df['date'] as datetime and use .dt accessors.
- For total bill questions, sum the filtered bill_amount values.
- For customer list questions, prefer returning identifying columns such as customer_id and name.
Return only the repaired pandas expression."""

RESULT_SUMMARY_PROMPT = """You are a restaurant data assistant.
You will be given a user's question and the raw output from a pandas query over restaurant data.
Answer only from that query output.
If the result is empty, clearly say that no matching records were found.
Keep the reply concise and natural."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_customer_ids_by_name",
            "description": (
                "Return customer IDs and names for customers whose names match a text query. "
                "Use this for questions like 'what is Daniel customer id' or 'show Priya's customer id'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name_query": {
                        "type": "string",
                        "description": "Full or partial customer name to search case-insensitively.",
                    }
                },
                "required": ["name_query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_orders_by_customer_name",
            "description": (
                "Return orders for customers whose names match a text query, including customer_id, name, order_id, items_ordered, bill_amount, and date. "
                "Use this for questions like 'what did Daniel order' or 'show orders for Priya'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name_query": {
                        "type": "string",
                        "description": "Full or partial customer name to search case-insensitively.",
                    }
                },
                "required": ["name_query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_total_bill_for_month_year",
            "description": (
                "Return the total bill amount for all restaurant orders in a given month and year. "
                "Use this for requests asking for the total bill, total sales, or total cost in a period like December 2025."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "month": {
                        "type": "integer",
                        "description": "Month number from 1 to 12.",
                    },
                    "year": {
                        "type": "integer",
                        "description": "4-digit year like 2025 or 2026.",
                    },
                },
                "required": ["month", "year"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_customers_for_month_year",
            "description": (
                "Return the unique customers who placed orders in a given month and year, including their customer_id, name, and dietary_preferences. "
                "Use this for requests like listing customers who ordered in December 2025."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "month": {
                        "type": "integer",
                        "description": "Month number from 1 to 12.",
                    },
                    "year": {
                        "type": "integer",
                        "description": "4-digit year like 2025 or 2026.",
                    },
                },
                "required": ["month", "year"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_preference_summary_for_month_year",
            "description": (
                "Return the dietary preference distribution for unique customers who ordered in a given month and year. "
                "Use this for questions about majority, most common, top, or popular customer preferences in a period like November 2025."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "month": {
                        "type": "integer",
                        "description": "Month number from 1 to 12.",
                    },
                    "year": {
                        "type": "integer",
                        "description": "4-digit year like 2025 or 2026.",
                    },
                },
                "required": ["month", "year"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_pandas_query",
            "description": (
                "Execute a raw pandas Python expression against two already-loaded DataFrames. "
                "Use the exact variable names customers_df and sales_df. "
                "customers_df columns are: customer_id, name, email, dietary_preferences. "
                "sales_df columns are: order_id, customer_id, items_ordered, bill_amount, date. "
                "Pass only executable pandas/Python code as code_string, such as filtering, "
                "groupby, merge, sorting, aggregation, or selecting rows/columns from customers_df "
                "and sales_df. For user text filters, prefer case-insensitive matching with "
                ".str.contains(..., case=False, na=False) or compare normalized strings with .str.lower(). "
                "Treat sales_df['date'] as a datetime column and use .dt accessors for date-based questions. "
                "Use order_id/customer_id as numeric IDs, items_ordered as text, and bill_amount for numeric cost calculations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code_string": {
                        "type": "string",
                        "description": (
                            "A raw pandas Python expression to evaluate with eval(). "
                            "The available DataFrame variables are exactly customers_df and sales_df. "
                            "customers_df has columns customer_id, name, email, dietary_preferences. "
                            "sales_df has columns order_id, customer_id, items_ordered, bill_amount, date. "
                            "When filtering by user-provided text, prefer case-insensitive matching. "
                            "For sales_df['date'], use datetime-style filtering with .dt when answering date questions. "
                            "For hypothetical cost questions, use bill_amount and numeric ID columns correctly."
                        ),
                    }
                },
                "required": ["code_string"],
                "additionalProperties": False,
            },
        },
    }
]


ENV_FILE = Path(__file__).resolve().parent / ".env"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"
MAX_HISTORY_MESSAGES = 6
MONTH_NAME_TO_NUMBER = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

MONTH_NAME_PATTERN = re.compile(
    r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b",
    re.IGNORECASE,
)
YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")
NUMERIC_MONTH_DAY_PATTERN = re.compile(r"\b\d{1,2}[/-]\d{1,2}\b")


@traced
def load_env_file(env_path: Path = ENV_FILE) -> None:
    """Load simple KEY=VALUE pairs from a local .env file into os.environ.

    Existing environment variables are left unchanged so explicit shell values
    still take priority over the file.
    """
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


@traced
def _get_groq_api_key() -> str | None:
    """Return a Groq API key from any supported environment variable name."""
    return (
        os.environ.get("GROQ_API_KEY")
        or os.environ.get("GROQ_API")
        or os.environ.get("GROQ_KEY")
    )


@traced
def get_llm_client_and_model(model: str | None = None) -> tuple[OpenAI, str, str]:
    """Create a configured LLM client and choose the provider/model from env.

    Provider selection priority:
    1. LLM_PROVIDER when explicitly set to "openai" or "groq"
    2. Groq, when a Groq key is present
    3. OpenAI, when an OpenAI key is present
    """
    load_env_file()

    provider = os.environ.get("LLM_PROVIDER", "").strip().lower()
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    groq_api_key = _get_groq_api_key()

    if provider == "groq" or (not provider and groq_api_key):
        if not groq_api_key:
            raise RuntimeError(
                "LLM_PROVIDER is set to 'groq' but GROQ_API_KEY/GROQ_API is not set."
            )

        selected_model = model or os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL)
        client = OpenAI(
            api_key=groq_api_key,
            base_url=os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
        )
        return client, selected_model, "groq"

    if provider == "openai" or (not provider and openai_api_key):
        if not openai_api_key:
            raise RuntimeError(
                "LLM_PROVIDER is set to 'openai' but OPENAI_API_KEY is not set."
            )

        selected_model = model or os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
        openai_base_url = os.environ.get("OPENAI_BASE_URL")
        client = (
            OpenAI(api_key=openai_api_key, base_url=openai_base_url)
            if openai_base_url
            else OpenAI(api_key=openai_api_key)
        )
        return client, selected_model, "openai"

    raise RuntimeError(
        "No supported LLM credentials were found. Add OPENAI_API_KEY or "
        "GROQ_API_KEY/GROQ_API to your environment or .env file."
    )


@traced
def _get_recent_history(conversation_history: list[dict[str, str]] | None) -> list[dict[str, str]]:
    """Keep only the latest user/assistant messages for short conversational context."""
    if not conversation_history:
        return []

    return [
        {"role": message["role"], "content": message["content"]}
        for message in conversation_history[-MAX_HISTORY_MESSAGES:]
        if message.get("role") in {"user", "assistant"} and message.get("content")
    ]


@traced
def _question_mentions_date_without_year(user_input: str) -> bool:
    """Return True when a question references a date but omits the year."""
    if YEAR_PATTERN.search(user_input):
        return False

    has_month_name = bool(MONTH_NAME_PATTERN.search(user_input))
    has_numeric_month_day = bool(NUMERIC_MONTH_DAY_PATTERN.search(user_input))
    return has_month_name or has_numeric_month_day


@traced
def _extract_year(user_input: str) -> str | None:
    """Extract a 4-digit year from the user's reply."""
    match = YEAR_PATTERN.search(user_input)
    return match.group(0) if match else None


@traced
def _extract_month_and_year(user_input: str) -> tuple[int, int] | None:
    """Extract a month and year from user input when both are present."""
    month_match = MONTH_NAME_PATTERN.search(user_input)
    year_text = _extract_year(user_input)

    if not month_match or not year_text:
        return None

    month_key = month_match.group(0).lower()[:3]
    month_number = MONTH_NAME_TO_NUMBER.get(month_key)
    if month_number is None:
        return None

    return month_number, int(year_text)


@traced
def _build_preference_summary_query(user_input: str) -> str | None:
    """Build a deterministic query for dietary preference summary questions."""
    normalized_input = user_input.lower()
    asks_about_preferences = (
        "preference" in normalized_input or "dietary" in normalized_input
    )
    asks_for_summary = any(
        phrase in normalized_input
        for phrase in ("majority", "most common", "top", "popular")
    )

    month_and_year = _extract_month_and_year(user_input)
    if not asks_about_preferences or not asks_for_summary or month_and_year is None:
        return None

    month_number, year_number = month_and_year
    return (
        "sales_df.loc["
        f"(sales_df['date'].dt.month == {month_number}) & "
        f"(sales_df['date'].dt.year == {year_number}), ['customer_id']]"
        ".drop_duplicates()"
        ".merge(customers_df[['customer_id', 'dietary_preferences']], on='customer_id', how='left')"
        "['dietary_preferences']"
        ".value_counts()"
        ".rename_axis('dietary_preferences')"
        ".reset_index(name='customer_count')"
    )


@traced
def _route_domain_tool_from_text(
    user_input: str,
) -> tuple[str, dict[str, int]] | None:
    """Match certain questions to explicit domain-level tools."""
    normalized_input = user_input.lower()
    words = re.findall(r"[a-zA-Z]+", user_input)

    if any(phrase in normalized_input for phrase in ("cust_id", "customer id", "customer_id")):
        stop_words = {"what", "is", "customer", "cust", "id"}
        candidate_words = [word for word in words if word.lower() not in stop_words]
        if candidate_words:
            return ("get_customer_ids_by_name", {"name_query": candidate_words[0]})

    month_and_year = _extract_month_and_year(user_input)
    if month_and_year is not None:
        month_number, year_number = month_and_year

        if (
            ("preference" in normalized_input or "dietary" in normalized_input)
            and any(
                phrase in normalized_input
                for phrase in ("majority", "most common", "top", "popular")
            )
        ):
            return (
                "get_preference_summary_for_month_year",
                {"month": month_number, "year": year_number},
            )

        if (
            any(word in normalized_input for word in ("total", "sum"))
            and any(word in normalized_input for word in ("bill", "cost", "sales"))
        ):
            return (
                "get_total_bill_for_month_year",
                {"month": month_number, "year": year_number},
            )

        if "customer" in normalized_input and any(
            word in normalized_input for word in ("list", "show", "who", "ordered")
        ):
            return (
                "get_customers_for_month_year",
                {"month": month_number, "year": year_number},
            )

    if any(phrase in normalized_input for phrase in ("what did", "show orders", "ordered")):
        stop_words = {
            "what",
            "did",
            "show",
            "orders",
            "order",
            "ordered",
            "customer",
            "in",
        }
        candidate_words = [word for word in words if word.lower() not in stop_words]
        if candidate_words:
            return (
                "get_orders_by_customer_name",
                {"name_query": candidate_words[0]},
            )

    return None


@traced
def _assistant_message_to_dict(message: Any) -> dict[str, Any]:
    """Turn the model's reply into a plain dictionary that can be reused later.

    This keeps normal text replies and any requested tool calls in a format that
    can be added back into the running conversation.
    """
    payload: dict[str, Any] = {
        "role": "assistant",
        "content": message.content or "",
    }

    if message.tool_calls:
        payload["tool_calls"] = [
            {
                "id": tool_call.id,
                "type": "function",
                "function": {
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments,
                },
            }
            for tool_call in message.tool_calls
        ]

    return payload


@traced
def _run_tool_call(tool_name: str, arguments_json: str) -> str:
    """Run one requested tool locally and return its output as text.

    Right now this only supports the pandas query tool used for reading the
    restaurant data.
    """
    try:
        arguments = json.loads(arguments_json or "{}")

        if tool_name == "execute_pandas_query":
            code_string = arguments["code_string"]
            print("\nGenerated pandas code:")
            print(code_string)
            print()
            return execute_pandas_query(code_string)

        if tool_name == "get_customer_ids_by_name":
            return get_customer_ids_by_name(name_query=arguments["name_query"])

        if tool_name == "get_orders_by_customer_name":
            return get_orders_by_customer_name(name_query=arguments["name_query"])

        if tool_name == "get_total_bill_for_month_year":
            return get_total_bill_for_month_year(
                month=int(arguments["month"]), year=int(arguments["year"])
            )

        if tool_name == "get_customers_for_month_year":
            return get_customers_for_month_year(
                month=int(arguments["month"]), year=int(arguments["year"])
            )

        if tool_name == "get_preference_summary_for_month_year":
            return get_preference_summary_for_month_year(
                month=int(arguments["month"]), year=int(arguments["year"])
            )

        return f"Unsupported tool: {tool_name}"
    except Exception:
        return traceback.format_exc()


@traced
def _clean_generated_expression(response_text: str) -> str:
    """Normalize model output into a bare pandas expression string."""
    cleaned = (response_text or "").strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            cleaned = "\n".join(lines[1:-1]).strip()

    if cleaned.lower().startswith("python\n"):
        cleaned = cleaned.split("\n", 1)[1].strip()

    if "To answer the question:" in cleaned:
        cleaned = cleaned.split("To answer the question:", 1)[1].strip()

    return cleaned.strip().strip("`")


@traced
def _execute_generated_query(code_string: str) -> str:
    """Print and execute a generated pandas expression."""
    print("\nGenerated pandas code:")
    print(code_string)
    print()
    return execute_pandas_query(code_string)


@traced
def _format_query_output_for_user(query_output: str) -> str:
    """Convert raw pandas output into a tool-grounded user-facing response."""
    cleaned_output = (query_output or "").strip()

    if not cleaned_output:
        return "The query ran, but it did not produce any visible output."

    if cleaned_output.startswith("Traceback"):
        return cleaned_output

    if "Empty DataFrame" in cleaned_output or cleaned_output.startswith("Series([],"):
        return "No matching records were found."

    if "\n" not in cleaned_output:
        return f"Result: {cleaned_output}"

    lines = cleaned_output.splitlines()
    if len(lines) > MAX_QUERY_OUTPUT_LINES:
        preview = "\n".join(lines[:MAX_QUERY_OUTPUT_LINES])
        return (
            f"Here are the matching records (showing the first {MAX_QUERY_OUTPUT_LINES} lines):\n"
            f"{preview}"
        )

    return f"Here are the matching records:\n{cleaned_output}"


@traced
def _repair_generated_query(
    client: OpenAI,
    selected_model: str,
    user_input: str,
    failing_expression: str,
    error_text: str,
    conversation_history: list[dict[str, str]] | None = None,
) -> str:
    """Ask the model to repair a pandas expression that failed at runtime."""
    repair_response = client.chat.completions.create(
        model=selected_model,
        messages=[
            {"role": "system", "content": QUERY_REPAIR_PROMPT},
            *_get_recent_history(conversation_history),
            {
                "role": "user",
                "content": (
                    f"User question: {user_input}\n\n"
                    f"Failing pandas expression:\n{failing_expression}\n\n"
                    f"Runtime error:\n{error_text}"
                ),
            },
        ],
    )
    return _clean_generated_expression(repair_response.choices[0].message.content or "")


@traced
def _fallback_chatbot_response(
    client: OpenAI,
    selected_model: str,
    user_input: str,
    conversation_history: list[dict[str, str]] | None = None,
) -> str:
    """Fallback flow for providers where tool-calling is unreliable.

    Step 1: ask the model for a plain pandas expression.
    Step 2: execute it locally.
    Step 3: ask the model to summarize the result for the user.
    """
    routed_tool = _route_domain_tool_from_text(user_input)
    if routed_tool is not None:
        tool_name, tool_arguments = routed_tool
        log_event(f"Using routed domain tool: {tool_name}")
        tool_output = _run_tool_call(tool_name, json.dumps(tool_arguments))
        if tool_output.startswith("Traceback"):
            raise RuntimeError(f"Generated pandas query failed:\n{tool_output}")
        return _format_query_output_for_user(tool_output)

    query_response = client.chat.completions.create(
        model=selected_model,
        messages=[
            {"role": "system", "content": QUERY_GENERATION_PROMPT},
            *_get_recent_history(conversation_history),
            {"role": "user", "content": user_input},
        ],
    )
    generated_expression = _clean_generated_expression(
        query_response.choices[0].message.content or ""
    )

    if not generated_expression:
        raise RuntimeError("The model did not generate a pandas expression.")

    latest_error = ""
    for _ in range(MAX_QUERY_REPAIR_ATTEMPTS + 1):
        query_output = _execute_generated_query(generated_expression)
        if not query_output.startswith("Traceback"):
            return _format_query_output_for_user(query_output)

        latest_error = query_output
        repaired_expression = _repair_generated_query(
            client,
            selected_model,
            user_input,
            generated_expression,
            query_output,
            conversation_history=conversation_history,
        )
        if not repaired_expression or repaired_expression == generated_expression:
            break
        generated_expression = repaired_expression

    raise RuntimeError(f"Generated pandas query failed:\n{latest_error}")


@traced
def get_chatbot_response(
    user_input: str,
    conversation_history: list[dict[str, str]] | None = None,
    model: str | None = None,
) -> str:
    """Send the user's question to OpenAI, handle any tool calls, and return the final reply.

    In simple terms, this is the main brain of the app: it asks the model what to
    do, runs data queries when the model requests them, and then asks the model to
    turn those results into a natural-language answer.
    """
    client, selected_model, provider_name = get_llm_client_and_model(model)

    if provider_name == "groq":
        return _fallback_chatbot_response(
            client,
            selected_model,
            user_input,
            conversation_history=conversation_history,
        )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *_get_recent_history(conversation_history),
        {"role": "user", "content": user_input},
    ]

    for _ in range(5):
        response = client.chat.completions.create(
            model=selected_model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        assistant_message = response.choices[0].message
        messages.append(_assistant_message_to_dict(assistant_message))

        if not assistant_message.tool_calls:
            return assistant_message.content or ""

        for tool_call in assistant_message.tool_calls:
            tool_output = _run_tool_call(
                tool_name=tool_call.function.name,
                arguments_json=tool_call.function.arguments,
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": tool_output,
                }
            )

    return "The model did not produce a final response after multiple tool calls."


@traced
def main() -> None:
    """Run a simple command-line chat loop until the user types exit or quit."""
    load_env_file()
    conversation_history: list[dict[str, str]] = []
    pending_date_question: str | None = None

    log_event("Application chat loop started")

    print("Restaurant chatbot is ready. Type a question, or type 'exit' to quit.")

    try:
        _client, selected_model, provider_name = get_llm_client_and_model()
        print(f"Using LLM provider: {provider_name} (model: {selected_model})")
    except RuntimeError as exc:
        print(f"Startup warning: {exc}")

    while True:
        try:
            user_input = input("User: ").strip()
        except (EOFError, KeyboardInterrupt):
            log_event("Application interrupted while waiting for user input")
            print("\nExiting chatbot.")
            break

        if user_input.lower() in {"exit", "quit"}:
            log_event("User requested application exit")
            print("Exiting chatbot.")
            break
        if not user_input:
            continue

        log_event(f"User input received: {user_input}")

        if pending_date_question is not None:
            selected_year = _extract_year(user_input)
            if not selected_year:
                log_event("Year clarification requested again because input had no 4-digit year")
                print("Assistant: Please provide a 4-digit year, for example 2026.")
                continue
            effective_input = f"{pending_date_question} in {selected_year}"
            pending_date_question = None
        else:
            if _question_mentions_date_without_year(user_input):
                pending_date_question = user_input
                log_event("Date clarification required before processing the question")
                print("Assistant: Which year do you mean for that date?")
                continue
            effective_input = user_input

        log_event(f"Effective input sent for processing: {effective_input}")

        try:
            response_text = get_chatbot_response(
                effective_input,
                conversation_history=conversation_history,
            )
            log_event("Assistant response generated successfully")
            print(f"Assistant: {response_text}")
            conversation_history.extend(
                [
                    {"role": "user", "content": effective_input},
                    {"role": "assistant", "content": response_text},
                ]
            )
            conversation_history = conversation_history[-MAX_HISTORY_MESSAGES:]
        except Exception as exc:
            log_event(
                f"Application-level error while answering user input: {exc.__class__.__name__}: {exc}"
            )
            print(f"Error: {exc}")


if __name__ == "__main__":
    initialize_run_log()
    main()
