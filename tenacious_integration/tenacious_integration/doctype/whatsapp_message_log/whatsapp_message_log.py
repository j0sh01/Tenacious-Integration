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


    @frappe.whitelist()
    def resend(self):
        """Resend a failed message"""
        if self.status != "Failed":
            frappe.throw(_("Only failed messages can be resent"))

        try:
            from tenacious_integration.tenacious_integration.api import send_whatsapp_message
            result = send_whatsapp_message(doc_name=self.name)

            if result.get("success"):
                self.update_status("Queued")  # Set status to "Queued" after resending
                return result
            else:
                return {"success": False, "error": result.get("error", "Unknown error")}

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), _("Error resending WhatsApp message"))
            return {"success": False, "error": str(e)}

    @frappe.whitelist()
    def process_queued_messages():
        """Send all messages that are in the 'Queued' status"""
        queued_messages = frappe.get_all("WhatsApp Message Log", filters={"status": "Queued"})
        for msg in queued_messages:
            doc = frappe.get_doc("WhatsAppMessageLog", msg.name)
            try:
                from tenacious_integration.tenacious_integration.api import send_whatsapp_message
                result = send_whatsapp_message(doc_name=doc.name)

                if result.get("success"):
                    doc.update_status("Sent")
                else:
                    doc.update_status("Failed", result.get("error", "Unknown error"))

            except Exception as e:
                doc.update_status("Failed", str(e))
                frappe.log_error(_("Error sending queued WhatsApp message"), frappe.get_traceback())
