import json
import os
from datetime import datetime, timedelta

data_file = "expenses.json"


# UI Functions
def banner(title):
    print()
    print(title)
    print("-" * max(24, len(title)))

def pause():
    input("\nPress ENTER to return to Main Menu")




# Storage helpers
def load():
    if not os.path.exists(data_file):
        return []
    with open(data_file, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []

def save(expenses):
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(expenses, f, indent=2, ensure_ascii=False)

def next_id(expenses):
    return max((e["id"] for e in expenses), default=0) + 1

# Data validation
def parse_amount(raw):
    try:
        amount = float(raw)
        if amount <= 0:
            return None, "Amount must be greater than 0."
        return round(amount, 2), None
    except ValueError:
        return None, "Amount must be a number (ex. 12.50)."

def validate_date(raw):
    try:
        datetime.strptime(raw, "%Y-%m-%d")
        return raw, None
    except ValueError:
        return None, "Date must be in YYYY-MM-DD format (ex. 2025-10-20)."

def normalize_keyword_date(token):
    token = token.strip().lower()
    if token == "today":
        return datetime.today().strftime("%Y-%m-%d")
    if token == "yesterday":
        return (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    return None

def require_nonempty(raw, field_name):
    val = raw.strip()
    if not val:
        return None, f"{field_name} cannot be empty."
    return val, None

# Pages

def main_menu():
    while True:
        banner("Expense Tracker — Main Menu")
        print("1. Add Expense")
        print("2. List Expenses")
        print("3. Delete Expense")
        print("4. Exit")
        choice = input("\nEnter your choice (1-4): ").strip()

        if choice == "1":
            add_expense()
        elif choice == "2":
            list_expenses()
        elif choice == "3":
            delete_expense()
        elif choice == "4":
            print("\nGoodbye! Thanks for using Expense Tracker.")
            return
        else:
            print("  ! Invalid choice. Please enter 1, 2, 3, or 4.")

def add_expense():
    banner("Add Expense")

    # Amount
    while True:
        raw = input("Enter amount (ex. 12.50) or leave blank to cancel: ").strip()
        if raw == "":
            print("Cancelled. No expense added.")
            return
        amount, err = parse_amount(raw)
        if err:
            print(f"  ! {err}")
            continue
        break

    # Category
    while True:
        raw = input("Enter category (ex. Food, Rent) or leave blank to cancel: ")
        if raw.strip() == "":
            print("Cancelled. No expense added.")
            return
        category, err = require_nonempty(raw, "Category")
        if err:
            print(f"  ! {err}")
            continue
        break

    # Date
    while True:
        raw = input("Enter date (YYYY-MM-DD or 'today'/'yesterday', blank = today): ").strip()
        if raw == "":
            date_string = datetime.today().strftime("%Y-%m-%d")
            break
        keyword = normalize_keyword_date(raw)
        if keyword:
            date_string = keyword
            break
        date_string, err = validate_date(raw)
        if err:
            print(f"  ! {err}")
            continue
        break

    # Note
    note = input("Enter note (optional): ").strip() or None

    expenses = load()
    new = {
        "id": next_id(expenses),
        "amount": amount,
        "date": date_string,
        "category": category,
        "note": note,
    }
    expenses.append(new)
    save(expenses)

    print("\nExpense added successfully!")
    print(f"  ID: {new['id']}  Date: {new['date']}  Category: {new['category']}  Amount: {new['amount']:.2f}")
    pause()

def print_expenses(expenses):
    print(f"{'ID':<4} {'Date':<10} {'Category':<14} {'Amount':>10}  Note")
    print("-" * 60)
    for expense in sorted(expenses, key=lambda x: (x["date"], x["id"]), reverse=True):
        note = expense.get("note") or ""
        if len(note) > 40:
            note = note[:37] + "..."
        print(f"{expense['id']:<4} {expense['date']:<10} {expense['category']:<14} {expense['amount']:>10.2f}  {note}")

def list_expenses():
    while True:
        banner("List / Find Expenses")
        print("Browse all expenses (newest first), or apply filters to narrow results.")
        print("\nOptions:")
        print("1. Browse All")
        print("2. Filter (by month and/or category)")
        print("3. Back to Main Menu")

        choice = input("\nEnter choice (1-3): ").strip()

        expenses = load()

        if choice == "1":
            banner("Browse All — Expenses")
            print_expenses(expenses)
            pause()
            return

        elif choice == "2":
            # Prompt for optional filters
            print("\nEnter filters (leave blank to skip a filter)")
            month = input("Month (YYYY-MM): ").strip()
            category = input("Category (contains text): ").strip()

            # Validate month format if provided
            if month and len(month) != 7:
                print("  ! Month must be YYYY-MM (e.g., 2025-11).")
                pause()
                continue

            # Add filters
            filtered = expenses
            if month:
                filtered = [e for e in filtered if e.get("date", "").startswith(month)]
            if category:
                cat_lower = category.lower()
                filtered = [e for e in filtered if cat_lower in (e.get("category", "")).lower()]

            banner("Filtered Results")
            if month or category:
                print(f"Applied filters: "
                      f"{'month='+month if month else ''}"
                      f"{' ' if (month and category) else ''}"
                      f"{'category contains '+category if category else ''}")
                print()
            else:
                print("(No filters provided; showing all.)\n")

            print_expenses(filtered)
            pause()
            return

        elif choice == "3":
            return
        else:
            print("  ! Invalid choice. Please enter 1, 2, or 3.")


def delete_expense():
    banner("Delete Expense")
    expenses = load()
    if not expenses:
        print("No expenses to delete.")
        pause()
        return

    print_expenses(expenses)
    while True:
        raw = input("\nEnter the ID to delete (or blank to cancel): ").strip()
        if raw == "":
            print("Cancelled. No expense deleted.")
            return
        if not raw.isdigit():
            print("  ! Please enter a numeric ID.")
            continue
        exp_id = int(raw)
        match = next((e for e in expenses if e["id"] == exp_id), None)
        if not match:
            print("  ! No expense found with that ID.")
            continue

        confirm = input(f"Delete expense ID {exp_id}? Type 'yes' to confirm: ").strip().lower()
        if confirm == "yes":
            expenses = [e for e in expenses if e["id"] != exp_id]
            save(expenses)
            print("Expense deleted successfully.")
        else:
            print("Cancelled. No expense deleted.")
        break

    pause()

if __name__ == "__main__":
    main_menu()