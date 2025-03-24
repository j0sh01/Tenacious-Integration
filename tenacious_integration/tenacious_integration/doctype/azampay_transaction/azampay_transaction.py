import frappe
import requests
import json
from frappe.model.document import Document
import random


class AzamPayTransaction(Document):
    def before_insert(self):
        """Auto-generate external_id before saving the transaction."""
        if not self.external_id:
            random_integer = random.randint(1, 99)
            self.external_id = f"{random_integer}"

    def autoname(self):
        """Set the docname as AZPAY-{YYYY}-{external_id}."""
        if not self.external_id:
            self.before_insert()  # Ensure external_id is set
        current_year = frappe.utils.now_datetime().year
        self.name = f"AZPAY-{current_year}-{self.external_id}"

@frappe.whitelist()
def mno_checkout(docname):
    """
    Process MNO checkout request with Azampay API using an existing transaction record.
    """

    # Fetch the transaction document
    transaction = frappe.get_doc("AzamPay Transaction", docname)

    # Ensure transaction is not already processed
    if transaction.status in ["Success", "Failed"]:
        frappe.throw("Transaction already processed. Create a new transaction.")

    # Fetch the auth token from Azampay Settings
    azampay_settings = frappe.get_single("Azampay Settings")
    auth_token = azampay_settings.auth_token

    if not auth_token:
        frappe.throw("Azampay token is missing. Generate a new token first.")

    # API Endpoint
    url = "https://sandbox.azampay.co.tz/azampay/mno/checkout"

    # Payload
    payload = {
        "accountNumber": transaction.account_number,
        "additionalProperties": {},
        "amount": str(transaction.amount),
        "currency": transaction.currency,
        "externalId": transaction.external_id,
        "provider": transaction.provider
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    }

    try:
        # Send request to Azampay API
        response = requests.post(url, headers=headers, data=json.dumps(payload))

        # Log response for debugging
        frappe.logger().info(f"MNO Checkout API Response: {response.text}")

        # Parse JSON response
        try:
            data = response.json()
        except ValueError:
            frappe.throw(f"Invalid JSON response: {response.text}")

        # Extract transaction info
        transaction_id = data.get("transactionId", "N/A")
        success = data.get("success", False)
        message = data.get("message", "No message from API")
        trace_id = data.get("traceId", "")
        status = "Success" if success else "Failed"

        # Capture errors if transaction failed
        error_details = ""
        if not success:
            errors = data.get("errors", {})
            error_details = json.dumps(errors, indent=2)

        # Update transaction record
        transaction.transaction_id = transaction_id
        transaction.status = status
        transaction.message = json.dumps(data, indent=2)  # Store full API response as pretty JSON
        transaction.trace_id = trace_id
        transaction.error_details = error_details
        transaction.time = frappe.utils.now_datetime()
        transaction.save(ignore_permissions=True)

        # Notify user
        if success:
            frappe.msgprint(f"Transaction successful! Transaction ID: {transaction_id}", alert=True, indicator="green")
            return {"status": "success", "transaction_id": transaction_id, "message": message}
        else:
            frappe.throw(f"Transaction failed: {message}\n\nDetails: {error_details}")

    except requests.exceptions.RequestException as e:
        frappe.log_error(frappe.get_traceback(), "Azampay MNO Checkout Request Error")
        frappe.throw(f"Request failed: {str(e)}")

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Azampay MNO Checkout Error")
        frappe.throw(f"An error occurred: {str(e)}")
