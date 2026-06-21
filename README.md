# Restaurant Chatbot

Starter Python project for a tool-invocation restaurant chatbot.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Configure environment

Create a local `.env` file in the project root and add your model credentials.

Example using Groq:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
```

Example using OpenAI:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

## Generate mock data

```powershell
python generate_mock_data.py
```

This creates:

- `data/customers_data.xlsx`
- `data/sales_data.xlsx`

The generated mock data is deterministic and now includes a larger sample dataset
with 60 customers and 360 sales records.

## How to run the app

1. Activate the virtual environment:

```powershell
.venv\Scripts\Activate.ps1
```

2. Make sure your `.env` file is present with valid API credentials.

3. Generate or refresh the mock data:

```powershell
python generate_mock_data.py
```

4. Start the chatbot:

```powershell
python app.py
```

5. Ask questions in the terminal.

6. Type `exit` or `quit` to stop the app.

## Runtime logging

Each time the app starts, it recreates:

- `log/log_run.txt`

This file records:

- major runtime events
- traced function calls
- function returns
- runtime errors

The `log/` folder is kept in Git, but `log/log_run.txt` is ignored because it is
generated fresh on every run.

## Sample Questions You Can Ask

### Customer ID lookup

- `what is daniel cust_id`
- `what is priya customer id`
- `show maria customer id`

### Orders by customer name

- `what did daniel ordered`
- `what did priya order`
- `show orders for maria`
- `what items did noah order`

### Total bill / total sales by month and year

- `what is the total bill in dec 2025`
- `what is total sales in november 2025`
- `what is the total cost in june 2026`
- `sum of bills in dec 2025`

### Customer list by month and year

- `list customers who ordered in dec 2025`
- `show customers in november 2025`
- `who ordered in june 2026`

### Dietary preference summaries

- `what are the majority customer preferences in dec 2025`
- `most common dietary preferences in november 2025`
- `top preferences in june 2026`
- `popular customer preferences in dec 2025`

### Customer details and profile lookup

- `show customer details for daniel`
- `find customer maria`
- `show me customer 1012`
- `who is customer 1005`
- `what is the email of priya`

### Customers by dietary preference

- `show vegetarian customers`
- `list halal customers`
- `who are the gluten-free customers`
- `show vegan customers`

### Orders by item name

- `show pizza orders`
- `who ordered biryani`
- `show orders containing pasta`
- `find orders with salad`

### Bill lookup for an order

- `what is the bill amount for order 5005`
- `show bill for order 5012`
- `how much was order 5030`

### Hypothetical cost questions

- `if order 5005 happened twice what is the total`
- `if 5005 was ordered twice how much would it cost`
- `double the cost of order 5012`

### Date-based queries

- `show orders on 2025-12-24`
- `who ordered on 2026-06-19`
- `show sales for june 19 2026`

### Aggregation / analytics questions

- `what is the average bill amount`
- `what is the total bill amount`
- `which customer spent the most`
- `show top customers by total bill`
- `count orders by month`

## Best demo questions

If you want a short live demo, these are especially reliable:

1. `what is daniel cust_id`
2. `what did daniel ordered`
3. `what is the total bill in dec 2025`
4. `list customers who ordered in dec 2025`
5. `what are the majority customer preferences in dec 2025`
6. `show vegetarian customers`
7. `show pizza orders`
8. `what is the bill amount for order 5005`
9. `if order 5005 happened twice what is the total`
10. `show top 5 highest bill orders`
