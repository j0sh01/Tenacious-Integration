import frappe
from frappe.model.workflow import get_workflow_name

def send_whatsapp_on_workflow_transition(doc, method):
    """
    Dynamically send WhatsApp messages when a workflow state changes.
    Only sends if enable_whatsapp_workflow_messages is checked in Twilio Settings.
    """

    if not frappe.db.get_single_value("Twilio Settings", "enable_whatsapp_workflow_messages"):
        return
    
    # Get Workflow Name for the Doctype
    workflow = get_workflow_name(doc.doctype)

    if not workflow:
        return  # No workflow exists for this doctype, exit

    # Fetch Workflow State Field
    workflow_state_field = frappe.get_value("Workflow", workflow, "workflow_state_field")
    current_state = doc.get(workflow_state_field)

    if not current_state:
        return  # No workflow state found, exit

    # Find recipients dynamically based on the workflow state
    recipients = get_recipients_for_workflow(doc.doctype, current_state)

    if not recipients:
        return  # No recipients to send messages to

    # Construct the message dynamically
    message = f"📢 Update: {doc.doctype} {doc.name} has transitioned to '{current_state}'.\n"

    # Add document details dynamically
    for field in doc.meta.get("fields"):
        if field.get("fieldtype") in ["Data", "Select", "Text", "Datetime"] and doc.get(field.get("fieldname")):
            message += f"{field.get('label')}: {doc.get(field.get('fieldname'))}\n"

    # Log and send WhatsApp messages
    for recipient in recipients:
        log_and_send_whatsapp_message(doc, recipient, message, current_state)


def get_recipients_for_workflow(doctype, state):
    """
    Fetch recipients dynamically based on workflow state.
    This can be based on User Roles, Assigned Users, or Custom Rules.
    """
    workflow_states = frappe.get_all(
        "Workflow Document State",
        filters={"parent": get_workflow_name(doctype), "state": state},
        fields=["allow_edit"]
    )

    users = []
    for state in workflow_states:
        users += frappe.get_all("Has Role", filters={"role": state["allow_edit"]}, pluck="parent")

    phone_numbers = [
        frappe.get_value("User", user, "mobile_no") for user in set(users) if user
    ]
    return [num for num in phone_numbers if num]  # Remove empty numbers


def log_and_send_whatsapp_message(doc, recipient, message, status):
    """
    Logs the WhatsApp message and triggers sending it via the API.
    """
    try:
        # Create a WhatsApp Message Log entry
        whatsapp_log = frappe.get_doc({
            "doctype": "WhatsApp Message Log",
            "to_number": recipient,
            "message_type": "Text",
            "message_content": message,
            "status": "Queued",
            "reference_doctype": doc.doctype,
            "reference_name": doc.name
        })
        whatsapp_log.insert(ignore_permissions=True)
        frappe.db.commit()

        # Call the API function with the document name
        from tenacious_integration.tenacious_integration.api import send_whatsapp_message
        send_whatsapp_message(doc_name=whatsapp_log.name)


    except Exception as e:
        frappe.log_error("WhatsApp Messaging Error", f"Error sending WhatsApp message: {str(e)}, Traceback: {frappe.get_traceback()}")

