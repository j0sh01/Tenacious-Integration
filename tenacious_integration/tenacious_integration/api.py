import json
import frappe
import requests
from frappe import _

@frappe.whitelist()
def get_message_templates():
    """Get all message templates from WhatsApp Business API"""
    try:
        settings = frappe.get_single("WhatsApp Settings")
        
        if not settings.enabled:
            return {"success": False, "error": "WhatsApp integration is not enabled"}
        
        import requests
        headers = {
            "Authorization": f"Bearer {settings.get_password('api_key')}",
            "Content-Type": "application/json"
        }
        
        # Get message templates for the WhatsApp Business Account
        response = requests.get(
            f"https://graph.facebook.com/v21.0/{settings.whatsapp_business_account_id}/message_templates",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            templates = []
            
            if "data" in data:
                for template in data["data"]:
                    templates.append({
                        "name": template.get("name"),
                        "language": template.get("language"),
                        "category": template.get("category"),
                        "status": template.get("status"),
                    })
            
            return {"success": True, "templates": templates}
        else:
            return {"success": False, "error": response.text}
            
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("WhatsApp Templates Error"))
        return {"success": False, "error": str(e)}
    
@frappe.whitelist()
def test_connection():
    """Test the connection to the WhatsApp API"""
    try:
        settings = frappe.get_single("WhatsApp Settings")
        
        headers = {
            "Authorization": f"Bearer {settings.get_password('api_key')}",
            "Content-Type": "application/json"
        }

        url = f"https://graph.facebook.com/v21.0/{settings.phone_number_id}/whatsapp_business_profile"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return {"success": True}
        else:
            return {"success": False, "error": response.text}

    except Exception as e:
        return {"success": False, "error": str(e)}    
    
@frappe.whitelist()
def generate_webhook_url(doc_name):
    """Generate and return a Webhook URL for WhatsApp Settings"""
    try:
        # Fetch the settings document
        settings = frappe.get_doc("WhatsApp Settings", doc_name)
        
        # Get site URL
        site_url = frappe.utils.get_url()
        
        # Generate Webhook URL
        webhook_url = f"{site_url}/api/method/tenacious_integration.tenacious_integration.api.webhook_handler"

        # Save Webhook URL in the document
        settings.webhook_url = webhook_url
        settings.save()

        return webhook_url
    except Exception as e:
        frappe.log_error(f"Error generating Webhook URL: {str(e)}")
        return None    

@frappe.whitelist()
def send_whatsapp_message(doc_name):
    """
    Sends a WhatsApp message using the Meta API.
    Supports text, template, and media messages.
    """
    try:
        # Fetch the message document
        message = frappe.get_doc("WhatsApp Message Log", doc_name)
        settings = frappe.get_single("WhatsApp Settings")

        if not settings.api_key:
            return {"success": False, "error": "Access Token is missing in WhatsApp Settings"}

        headers = {
            "Authorization": f"Bearer {settings.get_password('api_key')}",
            "Content-Type": "application/json"
        }

        # WhatsApp Business API URL
        url = f"https://graph.facebook.com/v21.0/{settings.phone_number_id}/messages"

        # ✅ Check if it's a first-time message → Send a TEMPLATE
        if message.message_type == "Text":
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": message.to_number,
                "type": "template",
                "template": {
                    "name": "hello_world",  # Replace with your approved template name
                    "language": {"code": "en_US"},
                    "components": []
                }
            }
        elif message.message_type == "Template":
            if not message.template_name:
                return {"success": False, "error": "Template name is required for template messages"}

            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": message.to_number,
                "type": "template",
                "template": {
                    "name": message.template_name,
                    "language": {"code": "en_US"},
                    "components": []
                }
            }
        elif message.message_type == "Media":
            if not message.media_url:
                return {"success": False, "error": "Media URL is required for media messages"}

            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": message.to_number,
                "type": "image",
                "image": {"link": message.media_url}
            }
        else:
            return {"success": False, "error": "Invalid message type"}

        # Update status to queued
        message.status = "Queued"
        message.queued_at = frappe.utils.now()
        message.save(ignore_permissions=True)

        # Send request to WhatsApp API
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()

        # Store API response for debugging
        message.api_response = json.dumps(data, indent=2)
        message.save(ignore_permissions=True)

        if response.status_code == 200 and "messages" in data:
            message.message_id = data["messages"][0]["id"]
            message.status = "Sent"
            message.sent_at = frappe.utils.now()
            message.save(ignore_permissions=True)
            return {"success": True, "message_id": message.message_id}
        else:
            error_msg = data.get("error", {}).get("message", "Unknown error")
            message.status = "Failed"
            message.error_message = error_msg
            message.save(ignore_permissions=True)
            return {"success": False, "error": error_msg}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Error sending WhatsApp message"))
        return {"success": False, "error": str(e)}


@frappe.whitelist(allow_guest=True)
def webhook_handler():
    """
    Handles incoming WhatsApp webhook events & Meta verification requests.
    """
    try:
        # ✅ Handle Verification Request
        if frappe.request.method == "GET":
            # Meta sends `hub.challenge`, `hub.verify_token`
            verify_token = frappe.form_dict.get("hub.verify_token")
            challenge = frappe.form_dict.get("hub.challenge")

            # Replace this with your actual verification token
            expected_token = "joshuaanakula5"

            if verify_token == expected_token:
                return challenge
            else:
                return "Verification token mismatch", 403

        # ✅ Handle Incoming Webhook Events (Messages, Status Updates)
        if frappe.request.method == "POST":
            payload = frappe.request.get_data(as_text=True)
            data = json.loads(payload)

            if "statuses" in data["entry"][0]["changes"][0]["value"]:
                status_update = data["entry"][0]["changes"][0]["value"]["statuses"][0]

                message_id = status_update.get("id")
                status = status_update.get("status")
                timestamp = status_update.get("timestamp")

                if timestamp:
                    formatted_time = frappe.utils.format_datetime(frappe.utils.get_datetime_from_timestamp(int(timestamp)))

                message_log = frappe.get_all(
                    "WhatsApp Message Log",
                    filters={"message_id": message_id},
                    fields=["name"]
                )

                if message_log:
                    message = frappe.get_doc("WhatsApp Message Log", message_log[0].name)

                    if status == "delivered" and not message.delivered_at:
                        message.delivered_at = formatted_time
                    elif status == "read" and not message.read_at:
                        message.read_at = formatted_time

                    message.save(ignore_permissions=True)
                    frappe.db.commit()

            return {"success": True}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("WhatsApp Webhook Error"))
        return {"success": False, "error": str(e)}
 