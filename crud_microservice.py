import json
import os
import time

DATA_FILE = "data.json"
REQUEST_FILE = "crud_requests.json"
RESPONSE_FILE = "crud_responses.json"

# First, checks that data file exists within directory and if not, creates file
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump([], f)

# Ensure response file exists
if not os.path.exists(RESPONSE_FILE):
    with open(RESPONSE_FILE, 'w') as f:
        json.dump([], f)

# Ensures request file exists
if not os.path.exists(REQUEST_FILE):
    with open(REQUEST_FILE, 'w') as f:
        json.dump([], f)


# Helper functions
def load_data():
    # Reads and loads current list of items from JSON data file
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(items):
    # Writes updated list of items back to JSON file
    with open(DATA_FILE, "w") as f:
        json.dump(items, f, indent=2)


# Main functions
def create_item(item):
    items = load_data()
    items.append(item)
    save_data(items)
    return {
        'status': 'success',
        'message': f'Item {item["id"]} was successfully created!',
        'item': item
    }


def retrieve_item(item_id=None):
    items = load_data()
    if item_id is None:  # No ID provided, so return full list
        return {'status': 'success', 'items': items}
    for item in items:
        if item['id'] == item_id:
            return {'status': 'success', 'item': item}
    return {'status': 'error', 'message': 'Item not found.'}


def update_item(item_id, updates):
    items = load_data()
    for item in items:
        if item['id'] == item_id:
            old_item = item.copy()  # Save original data before updating, just to show old vs new after update
            item.update(updates)
            save_data(items)
            return {
                'status': 'success',
                'message': f'Item {item_id} successfully updated!',
                'old_item': old_item,
                'updated_item': item
            }
    return {'status': 'error', 'message': f'Item {item_id} not found.'}


def delete_item(item_id):
    items = load_data()
    # Receives a unique item ID and creates a new list excluding that item
    new_items, deleted_item = delete_helper(items, item_id)
    # If length of new items list < original list, item was removed; updates data
    if len(new_items) < len(items):
        save_data(new_items)
        return {
            'status': 'success',
            'message': f'Item {item_id} was successfully deleted!',
            'item': deleted_item
        }
    else:
        return {'status': 'error', 'message': f'Item {item_id} not found.'}


def delete_helper(items, item_id):
    new_items = []
    deleted_item = None
    for item in items:
        if item['id'] == item_id:
            deleted_item = item
        else:
            new_items.append(item)
    return new_items, deleted_item


# Main loop
print('CRUD microservice running...')
while True:
    # First, check if request file exists
    if os.path.exists(REQUEST_FILE):
        with open(REQUEST_FILE, 'r') as f:
            # Attempt to read and parse JSON file and convert to Python list
            try:
                requests = json.load(f)
            except json.JSONDecodeError:  # Error when data not valid JSON
                requests = []  # If no valid request, treat as if no requests to process

        if requests:  # Program looks for any request to process
            responses = []  # initialize empty list to store responses from each request
            for req in requests:
                # Get command from request (default to empty string if missing)
                command = req.get('command', '').upper()
                data = req.get('data', {})

                if command == 'CREATE':
                    responses.append(create_item(data))
                elif command == 'RETRIEVE':
                    item_id = data.get('id')
                    responses.append(retrieve_item(item_id))
                elif command == 'UPDATE':
                    item_id = data.get('id')
                    updates = data.get('updates', {})
                    responses.append(update_item(item_id, updates))
                elif command == 'DELETE':
                    item_id = data.get('id')
                    responses.append(delete_item(item_id))
                else:
                    responses.append(
                        {'status': 'error', 'message': f'Unknown command {command} sent. Unable to process.'})

            # Program writes responses to response file
            with open(RESPONSE_FILE, 'w') as f:
                json.dump(responses, f, indent=2)

        # After program finishes processing requests, clear request file for next request
        with open(REQUEST_FILE, 'w') as f:
            json.dump([], f)

    # Add delay so that program isn't checking constantly for new requests
    time.sleep(2)
