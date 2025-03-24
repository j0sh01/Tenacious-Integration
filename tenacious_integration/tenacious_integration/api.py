import json
import frappe
import requests
from frappe import _
from twilio.rest import Client


@frappe.whitelist()
def test_twilio_connection():
    """Test the connection to Twilio API"""
    try:
        settings = frappe.get_single("Twilio Settings")
        
        if not settings.account_sid or not settings.auth_token:
            return {"success": False, "error": "Twilio credentials are missing in Twilio Settings"}
        
        client = Client(settings.account_sid, settings.get_password("auth_token"))
        
        # Fetch account details as a test
        account = client.api.accounts(settings.account_sid).fetch()
        
        return {"success": True, "account_name": account.friendly_name}
    
    except Exception as e:
        frappe.log_error("Twilio Connection Error", frappe.get_traceback())
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def send_whatsapp_message(doc_name):
    """
    Sends a WhatsApp message using Twilio API.
    Supports text and media messages.
    """
    try:
        # Fetch the message document
        message = frappe.get_doc("WhatsApp Message Log", doc_name)
        settings = frappe.get_single("Twilio Settings")
        
        if not settings.account_sid or not settings.auth_token:
            return {"success": False, "error": "Twilio credentials are missing in Twilio Settings"}
        
        client = Client(settings.account_sid, settings.get_password("auth_token"))

        # Ensure recipient and sender numbers are correctly formatted
        recipient_number = f"whatsapp:+{message.to_number.strip()}"
        sender_number = settings.twilio_whatsapp_number.strip()

        # ✅ Send the message exactly as done in manual test
        twilio_message = client.messages.create(
            from_=sender_number,
            body=message.message_content,
            to=recipient_number
        )

        # ✅ Update status in WhatsApp Message Log
        message.message_id = twilio_message.sid
        message.status = "Sent"
        message.sent_at = frappe.utils.now()
        message.save(ignore_permissions=True)

        return {"success": True, "message_id": twilio_message.sid}

    except Exception as e:
        frappe.log_error("Error sending Twilio WhatsApp message", frappe.get_traceback())
        return {"success": False, "error": str(e)}
    
@frappe.whitelist(allow_guest=True)
def twilio_webhook_handler():
    """
    Handles incoming Twilio webhook events for message delivery updates & Debugger events.
    """
    try:
        # ✅ Get incoming payload
        payload = frappe.request.get_data(as_text=True)
        data = json.loads(payload)

        # ✅ Log the complete payload for debugging
        frappe.log_error(title="Twilio Webhook Received", message=json.dumps(data, indent=2))

        # ✅ Handle Twilio Debugger Event
        if "Sid" in data and "Payload" in data:
            debugger_event = {
                "sid": data.get("Sid"),
                "account_sid": data.get("AccountSid"),
                "parent_account_sid": data.get("ParentAccountSid", "N/A"),
                "timestamp": data.get("Timestamp"),
                "level": data.get("Level"),
                "payload": json.dumps(data.get("Payload", {}), indent=2)
            }

            # ✅ Store Debugger event in Error Log
            frappe.log_error(
                title=f"Twilio Debugger Event [{debugger_event['level']}]",
                message=json.dumps(debugger_event, indent=2)
            )
            
            return {"success": True, "message": "Debugger event logged successfully"}

        # ✅ Handle Twilio Message Delivery Updates
        if "MessageStatus" in data:
            message_sid = data.get("MessageSid")
            status = data.get("MessageStatus")

            message_log = frappe.get_all(
                "WhatsApp Message Log",
                filters={"message_id": message_sid},
                fields=["name"]
            )

            if message_log:
                message = frappe.get_doc("WhatsApp Message Log", message_log[0].name)
                message.status = status.capitalize()
                message.save(ignore_permissions=True)
                frappe.db.commit()

            return {"success": True, "message": f"Message {message_sid} updated to {status}"}

        return {"success": False, "error": "Unknown event type received"}

    except Exception as e:
        frappe.log_error("Twilio Webhook Error", frappe.get_traceback())
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def generate_webhook_url(doc_name):
    """
    Generate and return a Webhook URL for Twilio WhatsApp API.
    Saves the generated webhook URL in Twilio Settings.
    """
    try:
        # Fetch the Twilio Settings document
        settings = frappe.get_doc("Twilio Settings", doc_name)

        # Get site URL
        site_url = frappe.utils.get_url()

        # Generate Webhook URL
        webhook_url = f"{site_url}/api/method/tenacious_integration.tenacious_integration.api.twilio_webhook_handler"

        # Save Webhook URL in Twilio Settings
        settings.webhook_url = webhook_url
        settings.save()

        return {"success": True, "webhook_url": webhook_url}

    except Exception as e:
        frappe.log_error("Error generating Webhook URL", frappe.get_traceback())
        return {"success": False, "error": str(e)}


import json
import frappe
from frappe import _
from twilio.rest import Client

@frappe.whitelist()
def send_twilio_sms(doc_name=None, to_number=None, message_content=None):
    """
    Sends an SMS using Twilio API.
    Supports sending via a `Twilio SMS Log` document or direct arguments.
    """
    try:
        settings = frappe.get_single("Twilio Settings")

        if not settings.account_sid or not settings.auth_token:
            return {"success": False, "error": "Twilio credentials are missing in Twilio Settings"}

        client = Client(settings.account_sid, settings.get_password("auth_token"))

        # ✅ If `doc_name` is provided, fetch from `Twilio SMS Log`
        if doc_name:
            try:
                sms = frappe.get_doc("Twilio SMS Log", doc_name)  # Ensure this matches your Doctype name
                to_number = f"+{sms.to_number.strip()}"
                message_content = sms.message_content
            except frappe.DoesNotExistError:
                return {"success": False, "error": f"Twilio SMS Log '{doc_name}' not found"}

        # ✅ Handle direct API calls (without doc_name)
        else:
            if not to_number or not message_content:
                return {"success": False, "error": "Missing `to_number` or `message_content`"}
            to_number = f"+{to_number.strip()}"

        sender_number = f"{settings.twilio_sms_number.strip()}"

        # ✅ Send SMS via Twilio
        twilio_message = client.messages.create(
            from_=sender_number,
            body=message_content,
            to=to_number
        )

        # ✅ Update status if doc_name was provided
        if doc_name:
            sms.message_sid = twilio_message.sid
            sms.status = "Queued"
            sms.date_sent = frappe.utils.now()
            sms.save(ignore_permissions=True)

        return {"success": True, "message_id": twilio_message.sid}

    except Exception as e:
        frappe.log_error("Error sending Twilio SMS", frappe.get_traceback())
        return {"success": False, "error": str(e)}
    
@frappe.whitelist(allow_guest=True)
def twilio_sms_webhook():
    """
    Handles incoming Twilio webhook events for SMS delivery updates.
    """
    try:
        payload = frappe.request.get_data(as_text=True)
        data = json.loads(payload)

        if "MessageStatus" in data:
            message_sid = data.get("MessageSid")
            status = data.get("MessageStatus")
            error_code = data.get("ErrorCode")
            error_message = data.get("ErrorMessage")

            sms_log = frappe.get_all(
                "Twilio SMS Log",
                filters={"message_sid": message_sid},
                fields=["name"]
            )

            if sms_log:
                sms = frappe.get_doc("Twilio SMS Log", sms_log[0].name)
                sms.status = status.capitalize()
                sms.error_code = error_code if error_code else None
                sms.error_message = error_message if error_message else None
                sms.save(ignore_permissions=True)
                frappe.db.commit()

            return {"success": True}

        return {"success": False, "error": "Unknown event type received"}

    except Exception as e:
        frappe.log_error("Twilio SMS Webhook Error", frappe.get_traceback())
        return {"success": False, "error": str(e)}    