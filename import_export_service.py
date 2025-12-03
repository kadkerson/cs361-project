import json
import os
import time

REQUEST_FILE = "import_export_requests.json"
RESPONSE_FILE = "import_export_responses.json"

# Ensure request/response files exist
for file in [REQUEST_FILE, RESPONSE_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump([], f)


def export_data(source_file_path, backup_file_path):
    """
    Copy the JSON contents of source_file_path into backup_file_path.
    Returns a response dictionary which contains the status and a message.
    The main program decides what file to export and where the backup goes.
    """
    try:
        with open(source_file_path, "r") as source:
            data = json.load(source)

        with open(backup_file_path, "w") as destination:
            json.dump(data, destination, indent=2)

        return {
            "status": "success",
            "message": f"Export successful. Copied {source_file_path} to {backup_file_path}."
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Export failed: {str(e)}"
        }


def import_data(backup_file_path):
    """
    Load and return the JSON contents from backup_file_path.
    The 'imported_data' is sent back to the main program which decides how and where the data is used.
    """
    try:
        with open(backup_file_path, "r") as f:
            imported = json.load(f)

        return {
            "status": "success",
            "message": f"Import successful: {backup_file_path}",
            "imported_data": imported
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Import failed: {str(e)}"
        }

print("Import/Export microservice running...")

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
            data = req.get("data", {})

            if operation == "EXPORT":
                source = data.get("source_file_path")
                destination = data.get("file_path")

                # Check missing fields individually
                if not source and not destination:
                    responses.append({
                        "status": "error",
                        "message": "EXPORT missing both source_file_path and file_path."
                    })
                elif not source:
                    responses.append({
                        "status": "error",
                        "message": "EXPORT missing source_file_path."
                    })
                elif not destination:
                    responses.append({
                        "status": "error",
                        "message": "EXPORT missing file_path."
                    })
                else:
                    responses.append(export_data(source, destination))


            elif operation == "IMPORT":
                backup = data.get("file_path")

                if not backup:
                    responses.append({
                        "status": "error",
                        "message": "IMPORT missing file_path."
                    })
                else:
                    responses.append(import_data(backup))

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

    time.sleep(0.5) # Change this as needed