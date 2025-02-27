# Copyright (c) 2025, Joshua Joseph Michael and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
import json

class WhatsAppMessageLog(Document):
    def validate(self):
        if not self.message_id and self.status == "Sent":
            frappe.throw(_("Message ID is required for sent messages"))
    
    def update_status(self, status, error_message=None):
        """Update message status and corresponding timestamp"""
        if status not in ["Queued", "Sent", "Delivered", "Read", "Failed"]:
            frappe.throw(_("Invalid status value"))

        if self.status != status or status in ["Sent", "Delivered", "Read"]:
            self.status = status
            
            if status == "Sent" and not self.sent_at:
                self.sent_at = frappe.utils.now()
            elif status == "Delivered" and not self.delivered_at:
                self.delivered_at = frappe.utils.now()
            elif status == "Read" and not self.read_at:
                self.read_at = frappe.utils.now()

            if status == "Failed" and error_message:
                self.error_message = error_message

            self.save(ignore_permissions=True)

    
    def resend(self):
        """Resend a failed message"""
        if self.status != "Failed":
            frappe.throw(_("Only failed messages can be resent"))

        try:
            from tenacious_integration.api import send_whatsapp_message

            # Handle template formatting
            if self.message_type.lower() == "template" and ":" not in self.message_content:
                self.message_content = f"{self.message_content}:en_US"

            result = send_whatsapp_message(
                to_number=self.to_number,
                message=self.message_content,
                message_type=self.message_type
            )

            if result.get("success"):
                self.update_status("Queued")  # Set status to "Queued" after resending
                return result
            else:
                return {"success": False, "error": result.get("error", "Unknown error")}

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), _("Error resending WhatsApp message"))
            return {"success": False, "error": str(e)}

    
    def get_message_history(self):
        """Get message status history from Meta's API and update status"""
        try:
            if not self.message_id:
                return {"success": False, "error": "No message ID available"}

            settings = frappe.get_single("WhatsApp Settings")

            import requests
            headers = {
                "Authorization": f"Bearer {settings.get_password('api_key')}",
                "Content-Type": "application/json"
            }

            response = requests.get(
                f"https://graph.facebook.com/v21.0/{self.message_id}",
                headers=headers
            )

            if response.status_code == 200:
                data = response.json()

                # Assuming response contains a `status` field, update the document
                new_status = data.get("status")
                if new_status and new_status in ["Sent", "Delivered", "Read", "Failed"]:
                    self.update_status(new_status)

                return {"success": True, "data": data}
            else:
                return {"success": False, "error": response.text}

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), _("Error fetching message history"))
            return {"success": False, "error": str(e)}
