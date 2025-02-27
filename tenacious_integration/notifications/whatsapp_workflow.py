import frappe
import requests
from frappe import _
from frappe.utils.data import get_url
from frappe.workflow.doctype.workflow_action.workflow_action import get_next_possible_transitions, get_signed_params, get_users_with_role, get_workflow_name, get_workflow_state_field

def send_workflow_whatsapp_notification(doc, method):
    """
    Sends a WhatsApp notification when a document moves in the workflow
    and logs it in WhatsApp Message Log.
    """
    try:
        # Fetch WhatsApp Settings
        settings = frappe.get_single("WhatsApp Settings")

        if not settings.api_key:
            frappe.log_error("WhatsApp API Key missing", "WhatsApp Workflow Notification Error")
            return

        headers = {
            "Authorization": f"Bearer {settings.get_password('api_key')}",
            "Content-Type": "application/json"
        }

        # Get the current workflow state
        workflow_state = get_doc_workflow_state(doc)

        # Get the next possible transitions
        next_transitions = get_next_possible_transitions(doc.workflow_name, workflow_state, doc)

        if not next_transitions:
            return

        roles = {t.allowed for t in next_transitions}

        # Get next user(s) assigned to the workflow
        users_data = get_users_next_action_data(next_transitions, doc)

        for user, data in users_data.items():
            # ✅ Fetch `mobile_no` instead of email
            phone_number = frappe.db.get_value("User", user, "mobile_no")

            if not phone_number:
                frappe.log_error(f"No mobile number found for user: {user}", "WhatsApp Workflow Error")
                continue  # Skip this user if no mobile number is found

            message_content = f"New Workflow Action: {doc.doctype} ({doc.name}) is now in '{workflow_state}' state. Please review and take action."

            # WhatsApp Business API URL
            url = f"https://graph.facebook.com/v21.0/{settings.phone_number_id}/messages"

            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": phone_number,
                "type": "text",
                "text": {"body": message_content}
            }

            # Send request
            response = requests.post(url, headers=headers, json=payload)
            data = response.json()

            # Log the message in WhatsApp Message Log
            if response.status_code == 200 and "messages" in data:
                message_id = data["messages"][0]["id"]

                log_entry = frappe.get_doc({
                    "doctype": "WhatsApp Message Log",
                    "message_id": message_id,
                    "to_number": phone_number,
                    "message_type": "Text",
                    "message_content": message_content,
                    "status": "Sent",
                    "sent_at": frappe.utils.now()
                })
                log_entry.insert(ignore_permissions=True)
                frappe.db.commit()

                frappe.logger().info(f"WhatsApp message sent to {phone_number}: {message_content}")

            else:
                error_msg = data.get("error", {}).get("message", "Unknown error")
                frappe.log_error(f"Failed to send WhatsApp message: {error_msg}", "WhatsApp Workflow Notification Error")

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "WhatsApp Workflow Notification Error")


def get_doc_workflow_state(doc):
    """Retrieve the current workflow state of the document."""
    workflow_name = get_workflow_name(doc.get("doctype"))
    workflow_state_field = get_workflow_state_field(workflow_name)
    return doc.get(workflow_state_field)


def get_users_next_action_data(transitions, doc):
    """
    Get users who need to take action in the next step of the workflow.
    """
    user_data_map = {}

    @frappe.request_cache
    def user_has_permission(user: str) -> bool:
        from frappe.permissions import has_permission

        return has_permission(doctype=doc.doctype, user=user)

    for transition in transitions:
        users = get_users_with_role(transition.allowed)
        filtered_users = [
            user for user in users if user_has_permission(user)
        ]

        for user in filtered_users:
            if not user_data_map.get(user):
                user_data_map[user] = {
                    "possible_actions": [],
                    "mobile_no": frappe.db.get_value("User", user, "mobile_no"),
                }

            user_data_map[user]["possible_actions"].append({
                "action_name": transition.action,
                "action_link": get_workflow_action_url(transition.action, doc, user),
            })

    return user_data_map


def get_workflow_action_url(action, doc, user):
    """
    Generate a workflow action URL.
    """
    apply_action_method = "/api/method/frappe.workflow.doctype.workflow_action.workflow_action.apply_action"

    params = {
        "doctype": doc.get("doctype"),
        "docname": doc.get("name"),
        "action": action,
        "current_state": get_doc_workflow_state(doc),
        "user": user,
        "last_modified": doc.get("modified"),
    }

    return get_url(apply_action_method + "?" + get_signed_params(params))
