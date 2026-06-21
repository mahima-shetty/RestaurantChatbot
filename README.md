# Restaurant Chatbot

Starter Python project for a tool-invocation restaurant chatbot.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
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
