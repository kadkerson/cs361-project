import json
import os
import time

REQUEST_FILE = "notification_requests.json"
RESPONSE_FILE = "notification_responses.json"

# Ensure request/response files exist
for file in [REQUEST_FILE, RESPONSE_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump([], f)

def build_notification(status="success", custom_message=None, include_status=True):
    """
    Build a notification message dictionary.
    Defaults:
        status="success"
        include_status=True
    The main program can override both and choose whether the status label is included in the final message.
    """
    # Provide default message if missing
    custom_message = custom_message or "No message provided."

    status_label = status.capitalize()

    if custom_message and include_status:
        final_message = f"[{status_label}] {custom_message}"
    elif custom_message and not include_status:
        final_message = custom_message
    else:
        final_message = status_label

    return {"status": status, "message": final_message}

print("Notification microservice running...")

while True:
    # Read all requests
    with open(REQUEST_FILE, "r") as f:
        try:
            requests = json.load(f)
        except json.JSONDecodeError:
            requests = []

    if requests:
        responses = []
        for req in requests:
            operation = req.get("operation", "").upper()
            if operation == "SEND":
                data = req.get("data", {})
                status = data.get("status", "success")
                custom_message = data.get("message")
                include_status = data.get("include_status", True)

                response_obj = build_notification(status, custom_message, include_status)
                responses.append(response_obj)

            else:
                responses.append({
                    "status": "error",
                    "message": f"Unknown operation '{operation}'"
                })

        # Write responses
        with open(RESPONSE_FILE, "w") as f:
            json.dump(responses, f, indent=2)

        # Clear requests
        with open(REQUEST_FILE, "w") as f:
            json.dump([], f)

    time.sleep(0.5)  # Defaulted to 0.5 but change this as needed.