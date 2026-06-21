from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import random

import pandas as pd


OUTPUT_DIR = Path(__file__).resolve().parent / "data"
RANDOM_SEED = 20260621
CUSTOMER_COUNT = 60
SALES_COUNT = 360

CUSTOMER_NAMES = [
    "John Carter",
    "Priya Shah",
    "Maria Lopez",
    "Ethan Brooks",
    "Aisha Khan",
    "Liam Turner",
    "Sophia Nguyen",
    "Arjun Mehta",
    "Olivia Reed",
    "Noah Kim",
    "Fatima Ali",
    "Daniel Ross",
    "Isabella Patel",
    "Kabir Singh",
    "Meera Garcia",
    "Lucas Bennett",
    "Zara Coleman",
    "Henry Foster",
    "Anaya Griffin",
    "Mateo Hughes",
    "Nina Parker",
    "Rohan Das",
    "Elena Morris",
    "Vivaan Iyer",
    "Clara Murphy",
    "Aarav Nair",
    "Mila Cooper",
    "Ishaan Rao",
    "Layla Price",
    "Dev Malhotra",
    "Ava Peterson",
    "Kian Sethi",
    "Sara Wallace",
    "Reyansh Kapoor",
    "Leah Russell",
    "Aditya Menon",
    "Hannah Jenkins",
    "Krish Bansal",
    "Ruby Howard",
    "Vihaan Chawla",
    "Sana Mirza",
    "Aryan Desai",
    "Tara Wood",
    "Yash Arora",
    "Maya Butler",
    "Neel Joshi",
    "Pooja Anand",
    "Veer Tandon",
    "Ira Bhatt",
    "Ayaan Gulati",
    "Riya Suri",
    "Dhruv Bedi",
    "Myra Sinha",
    "Arnav Kohli",
    "Nora Dutta",
    "Parth Talwar",
    "Siya Batra",
    "Rudra Sachdeva",
    "Kiara Wadhwa",
    "Shaurya Luthra",
]

DIETARY_PREFERENCES = [
    "Vegetarian",
    "Gluten-Free",
    "Vegan",
    "No preference",
    "Halal",
    "Pescatarian",
    "Jain",
    "Nut-Free",
]

MENU_ITEMS = [
    "Margherita Pizza",
    "Garlic Bread",
    "Caesar Salad",
    "Lemonade",
    "Vegan Burger",
    "Sweet Potato Fries",
    "Pepperoni Pizza",
    "Cola",
    "Chicken Biryani",
    "Mango Lassi",
    "BBQ Pizza",
    "Iced Tea",
    "Paneer Tikka Pizza",
    "Lime Soda",
    "Grilled Salmon",
    "Herbed Rice",
    "Jain Special Thali",
    "Sweet Lassi",
    "Veg Alfredo Pasta",
    "Iced Latte",
    "Nut-Free Brownie",
    "Cappuccino",
    "Chicken Shawarma Plate",
    "Mint Lemonade",
    "Gluten-Free Pasta",
    "Orange Juice",
    "Vegan Pizza",
    "Kombucha",
    "Farmhouse Pizza",
    "Tomato Soup",
    "Mutton Biryani",
    "Rabdi",
    "Quinoa Salad",
    "Fresh Lime",
    "Smoked Chicken Pizza",
    "Fish Tacos",
    "Veggie Wrap",
    "Green Tea",
    "Falafel Bowl",
    "Mango Juice",
    "Gluten-Free Pizza",
    "Sparkling Water",
    "Mushroom Risotto",
    "Jain Pav Bhaji",
    "Rose Milk",
    "Avocado Toast",
    "Cold Coffee",
    "Pesto Pasta",
    "Roasted Veggies",
    "Paneer Wrap",
    "Masala Fries",
    "Berry Smoothie",
    "Stuffed Mushrooms",
    "Thai Curry Bowl",
    "Naan Pizza",
    "Hummus Platter",
    "Brown Rice Bowl",
]


def build_customers() -> pd.DataFrame:
    """Create a larger deterministic table of sample customer details."""
    customer_rows: list[dict[str, object]] = []

    for index in range(CUSTOMER_COUNT):
        customer_id = 1001 + index
        name = CUSTOMER_NAMES[index]
        email_local_part = name.lower().replace(" ", ".")
        email = f"{email_local_part}{customer_id}@example.com"
        dietary_preference = DIETARY_PREFERENCES[index % len(DIETARY_PREFERENCES)]

        customer_rows.append(
            {
                "customer_id": customer_id,
                "name": name,
                "email": email,
                "dietary_preferences": dietary_preference,
            }
        )

    return pd.DataFrame(customer_rows)


def build_sales() -> pd.DataFrame:
    """Create a larger deterministic table of sample food orders and bill amounts."""
    random_generator = random.Random(RANDOM_SEED)
    start_date = date(2025, 1, 1)
    customers = build_customers()
    customer_ids = customers["customer_id"].tolist()
    sales_rows: list[dict[str, object]] = []

    for order_offset in range(SALES_COUNT):
        order_id = 5001 + order_offset
        customer_id = customer_ids[order_offset % len(customer_ids)]
        primary_item = MENU_ITEMS[order_offset % len(MENU_ITEMS)]
        secondary_item = MENU_ITEMS[(order_offset * 7 + 3) % len(MENU_ITEMS)]
        order_date = start_date + timedelta(days=order_offset % 540)
        bill_amount = round(
            12
            + (order_offset % 9) * 1.85
            + random_generator.uniform(1.5, 11.5),
            2,
        )

        sales_rows.append(
            {
                "order_id": order_id,
                "customer_id": customer_id,
                "items_ordered": f"{primary_item}, {secondary_item}",
                "bill_amount": bill_amount,
                "date": order_date.isoformat(),
            }
        )

    return pd.DataFrame(sales_rows)


def main() -> None:
    """Generate the sample Excel files and save them into the data folder."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    customers = build_customers()
    sales = build_sales()

    customers_path = OUTPUT_DIR / "customers_data.xlsx"
    sales_path = OUTPUT_DIR / "sales_data.xlsx"

    customers.to_excel(customers_path, index=False, engine="openpyxl")
    sales.to_excel(sales_path, index=False, engine="openpyxl")

    print(f"Created {customers_path}")
    print(f"Created {sales_path}")
    print(f"Customer rows: {len(customers)}")
    print(f"Sales rows: {len(sales)}")


if __name__ == "__main__":
    main()
