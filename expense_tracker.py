import json
import os
import time
from datetime import datetime, timedelta

data_file = "expenses.json"

# CRUD integration
CRUD_REQUEST_FILE = "crud_requests.json"
CRUD_RESPONSE_FILE = "crud_responses.json"
CRUD_DATA_FILE = "data.json"  # used by import/export microservice as the source file

def send_crud_request(command, data):
    request = [{
        "command": command,
        "data": data
    }]

    # Write the request list to the request file (overwrite any previous contents)
    with open(CRUD_REQUEST_FILE, "w", encoding="utf-8") as f:
        json.dump(request, f, indent=2)

    while True:
        try:
            with open(CRUD_RESPONSE_FILE, "r", encoding="utf-8") as f:
                responses = json.load(f)

            if isinstance(responses, list) and len(responses) > 0:
                return responses[0]

        except (FileNotFoundError, json.JSONDecodeError):
            # file not ready or not valid JSON yet
            pass

        time.sleep(0.2)

def crud_get_all_expenses():
    resp = send_crud_request("RETRIEVE", {})
    if resp.get("status") == "success":
        # When retrieving all, microservice uses 'items'
        return resp.get("items", [])
    else:
        print("  ! Error retrieving expenses from storage service:",
              resp.get("message", "Unknown error"))
        return []

def crud_next_id():
    items = crud_get_all_expenses()
    max_id = 0
    for item in items:
        try:
            current_id = int(item.get("id", 0))
            if current_id > max_id:
                max_id = current_id
        except (TypeError, ValueError):
            continue
    return max_id + 1

def crud_create_expense(expense):
    data = expense.copy()
    # Microservice expects 'id' as a string (based on example), so convert
    data["id"] = str(data["id"])

    resp = send_crud_request("CREATE", data)
    if resp.get("status") != "success":
        print("  ! Error saving expense:", resp.get("message", "Unknown error"))
    return resp

def crud_delete_expense(expense_id):
    resp = send_crud_request("DELETE", {"id": str(expense_id)})
    if resp.get("status") != "success":
        print("  ! Error deleting expense:", resp.get("message", "Unknown error"))
    return resp


SEARCH_DATABASE_FILE = "exampledatabase.txt"   # must match DATABASE in search microservice
SEARCH_PIPELINE_FILE = "examplepipeline.txt"   # must match PIPELINE in search microservice


def sync_expenses_to_search_database():
    expenses = crud_get_all_expenses()

    with open(SEARCH_DATABASE_FILE, "w", encoding="utf-8") as f:
        for e in expenses:
            category_value = e.get("category", "") or ""
            obj = {
                "id": str(e.get("id")),
                "date": e.get("date", ""),
                "category": category_value,                # original
                "category_lower": category_value.lower(),  # for case-insensitive search
                "amount": e.get("amount", 0.0),
                "note": e.get("note") or ""
            }
            f.write(json.dumps(obj) + "\n")


# SEARCH/FILTER INTEGRATION
def search_expenses_via_microservice(id_filter="", date_filter="", category_filter=""):
    sync_expenses_to_search_database()

    # lowercase
    category_lower = (category_filter or "").lower()

    # build request object
    request_obj = {
        "id": id_filter or "",
        "date": date_filter or "",
        "category": "",
        "category_lower": category_lower,
        "amount": "",
        "note": ""
    }

    # pipeline request
    with open(SEARCH_PIPELINE_FILE, "w", encoding="utf-8") as f:
        f.write("request\n")
        f.write(json.dumps(request_obj) + "\n")

    while True:
        try:
            with open(SEARCH_PIPELINE_FILE, "r", encoding="utf-8") as f:
                lines = [ln.strip() for ln in f.readlines() if ln.strip()]

            if lines and lines[0].lower() == "reply":
                matches = []
                for line in lines[1:]:
                    try:
                        matches.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
                return matches

        except FileNotFoundError:
            # file not created yet
            pass

        time.sleep(0.2)

IMPORT_EXPORT_REQUEST_FILE = "import_export_requests.json"
IMPORT_EXPORT_RESPONSE_FILE = "import_export_responses.json"


def send_import_export_request(operation, data):
    """
    Send a single IMPORT or EXPORT request to the import/export microservice
    and wait for the first response object.
    """
    # clear old responses
    try:
        with open(IMPORT_EXPORT_RESPONSE_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
    except FileNotFoundError:
        pass

    request = [{
        "operation": operation,
        "data": data
    }]

    with open(IMPORT_EXPORT_REQUEST_FILE, "w", encoding="utf-8") as f:
        json.dump(request, f, indent=2)

    while True:
        try:
            with open(IMPORT_EXPORT_RESPONSE_FILE, "r", encoding="utf-8") as f:
                responses = json.load(f)

            if isinstance(responses, list) and responses:
                return responses[0]

        except (FileNotFoundError, json.JSONDecodeError):
            pass

        time.sleep(0.2)


def export_expenses():
    banner("Export Data (Backup)")
    print("This will create a backup copy of all your expenses.")
    print(f"Current data source file (from CRUD service): {CRUD_DATA_FILE}")
    print("Example backup filename: expenses_backup.json")
    backup_path = input("Enter backup file path (or blank to cancel): ").strip()

    if not backup_path:
        print("Cancelled. No export performed.")
        pause()
        return

    resp = send_import_export_request(
        "EXPORT",
        {
            "source_file_path": CRUD_DATA_FILE,
            "file_path": backup_path
        }
    )

    banner("Export Result")
    message = resp.get("message", "No message from export service.")
    print(message)
    pause()


def import_expenses():
    banner("Import Data (Restore)")
    print("This will REPLACE your current expenses with data from a backup.")
    print("Example backup filename: expenses_backup.json")
    backup_path = input("Enter backup file path (or blank to cancel): ").strip()

    if not backup_path:
        print("Cancelled. No import performed.")
        pause()
        return

    resp = send_import_export_request(
        "IMPORT",
        {
            "file_path": backup_path
        }
    )

    banner("Import Result")
    status = resp.get("status", "error")
    message = resp.get("message", "No message from import service.")
    print(message)

    if status != "success":
        pause()
        return

    imported_data = resp.get("imported_data")
    if not isinstance(imported_data, list):
        print("  ! Import service did not return a list of expenses.")
        pause()
        return

    # delete all existing expenses
    current_items = crud_get_all_expenses()
    for item in current_items:
        item_id = item.get("id")
        if item_id is None:
            continue
        try:
            numeric_id = int(item_id)
        except (TypeError, ValueError):
            numeric_id = item_id
        crud_delete_expense(numeric_id)

    # create new expenses from imported_data
    for e in imported_data:
        new_item = {
            "id": e.get("id"),
            "amount": e.get("amount", 0.0),
            "date": e.get("date", ""),
            "category": e.get("category", ""),
            "note": e.get("note", None),
        }

        # check num
        try:
            new_item["amount"] = float(new_item["amount"])
        except (TypeError, ValueError):
            new_item["amount"] = 0.0

        # if no ID or empty string in imported data, assign one with CRUD
        if not new_item["id"]:
            new_item["id"] = crud_next_id()

        crud_create_expense(new_item)

    print("All expenses have been replaced with the imported data.")
    pause()


# UI Functions
def banner(title):
    print()
    print(title)
    print("-" * max(24, len(title)))

def pause():
    input("\nPress ENTER to return to Main Menu")


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
        print("Track, organize, and review your spending to stay on budget")
        print("1. Add Expense")
        print("2. List Expenses")
        print("3. Delete Expense")
        print("4. Search Expenses (microservice)")
        print("5. Export Data (backup)")
        print("6. Import Data (restore)")
        print("7. Exit")
        choice = input("\nEnter your choice (1-7): ").strip()

        if choice == "1":
            add_expense()
        elif choice == "2":
            list_expenses()
        elif choice == "3":
            delete_expense()
        elif choice == "4":
            search_expenses()
        elif choice == "5":
            export_expenses()
        elif choice == "6":
            import_expenses()
        elif choice == "7":
            print("\nGoodbye! Thanks for using Expense Tracker.")
            return
        else:
            print("  ! Invalid choice. Please enter a number from 1 to 7.")


def add_expense():
    banner("Add Expense")
    print("Amount, Category, Date, and Note (optional) will be collected for this entry")

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

    # CRUD integration
    new = {
        "id": crud_next_id(),
        "amount": amount,
        "date": date_string,
        "category": category,
        "note": note,
    }

    crud_create_expense(new)

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

        expenses = crud_get_all_expenses()

        if choice == "1":
            banner("Browse All — Expenses")
            print_expenses(expenses)
            pause()
            return

        elif choice == "2":
            # Search/Filter integration
            print("\nEnter filters (leave blank to skip a filter)")
            month = input("Month (YYYY-MM): ").strip()
            category = input("Category (contains text): ").strip()

            # Validate month format
            if month and len(month) != 7:
                print("  ! Month must be YYYY-MM (e.g., 2025-11).")
                pause()
                continue

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
    expenses = crud_get_all_expenses()
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
        # IDs stored as strings in the CRUD service
        match = next((e for e in expenses if str(e.get("id")) == str(exp_id)), None)
        if not match:
            print("  ! No expense found with that ID.")
            continue

        confirm = input(f"Delete expense ID {exp_id}? Type 'yes' to confirm: ").strip().lower()
        if confirm == "yes":
            resp = crud_delete_expense(exp_id)
            if resp.get("status") == "success":
                print("Expense deleted successfully.")
            else:
                print("  ! Delete failed:", resp.get("message", "Unknown error"))
        else:
            print("Cancelled. No expense deleted.")
        break

    pause()


def search_expenses():
    banner("Search Expenses (via Microservice)")
    print("Leave a field blank to ignore it.")
    print("You can search by:")
    print("  - ID (exact match)")
    print("  - Date (exact YYYY-MM-DD)")
    print("  - Category (case-insensitive)\n")

    id_filter = input("ID (exact): ").strip()
    date_filter = input("Date (YYYY-MM-DD, exact): ").strip()
    category_filter = input("Category (any case, exact): ").strip()

    if date_filter:
        normalized, err = validate_date(date_filter)
        if err:
            print(f"  ! {err}")
            pause()
            return
        date_filter = normalized

    matches = search_expenses_via_microservice(
        id_filter=id_filter,
        date_filter=date_filter,
        category_filter=category_filter
    )

    banner("Search Results")
    if not matches:
        print("No expenses matched your search criteria.")
    else:
        print_expenses(matches)

    pause()


if __name__ == "__main__":
    main_menu()