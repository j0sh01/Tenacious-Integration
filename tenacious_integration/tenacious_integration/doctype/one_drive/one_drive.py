import frappe
from frappe.model.document import Document
from frappe.utils.background_jobs import enqueue
from frappe.utils.backups import new_backup
from frappe.utils import now_datetime, add_days
from frappe import _
import requests
import os
import traceback

class OneDrive(Document):
    pass

@frappe.whitelist()
def take_backup():
    """Enqueue a backup task to upload to OneDrive based on frequency settings."""
    one_drive = frappe.get_single("One Drive")

    if not one_drive.enable:
        frappe.throw(_("OneDrive backup is disabled. Enable it."))

    if not one_drive.backup_folder_name:
        frappe.throw(_("Please specify a Backup Folder Name in OneDrive settings."))

    if not is_backup_due(one_drive):
        frappe.msgprint(_("Backup is not due yet based on the selected frequency."))
        return

    enqueue(
        "tenacious_integration.tenacious_integration.doctype.one_drive.one_drive.upload_backup_to_onedrive",
        queue="long",
        timeout=1500,
    )
    frappe.msgprint(_("Backup process has been queued. It may take some time to complete."))

def is_backup_due(one_drive):
    """Check if the backup should run based on the frequency setting."""
    if not one_drive.last_backup_on:
        return True  # No previous backup, so run now

    try:
        last_backup = frappe.utils.get_datetime(one_drive.last_backup_on)

        if one_drive.frequency == "Daily":
            return now_datetime() >= add_days(last_backup, 1)
        elif one_drive.frequency == "Weekly":
            return now_datetime() >= add_days(last_backup, 7)

    except Exception:
        frappe.logger().error("Error parsing last_backup_on. Running backup to fix issue.")
        return True  # Run backup if date parsing fails

    return False  # Default: Don't run backup if frequency is missing

def upload_backup_to_onedrive():
    """Perform the backup and upload to OneDrive, ensuring error handling for RQ Jobs."""
    try:
        ms_settings = frappe.get_single("Microsoft Settings")
        one_drive = frappe.get_single("One Drive")

        if not ms_settings.refresh_token:
            raise Exception(_("Microsoft account is not authorized. Please authorize in Microsoft Settings."))

        access_token = refresh_access_token(ms_settings)

        #  Ensure backup folder exists
        folder_id = ensure_onedrive_folder_exists(access_token, one_drive)

        # Save folder ID if new
        if folder_id and folder_id != one_drive.backup_folder_id:
            frappe.db.set_value("One Drive", None, "backup_folder_id", folder_id)
            frappe.db.commit()

        #  Generate a new backup
        backup = new_backup()
        backup_files = [backup.backup_path_db, backup.backup_path_conf]

        if one_drive.file_backup:
            backup_files.extend([backup.backup_path_files, backup.backup_path_private_files])

        #  Upload files to OneDrive
        for file_path in backup_files:
            if file_path:
                upload_to_onedrive(access_token, file_path, folder_id)

        #  Update last backup time and status
        frappe.db.set_value("One Drive", None, "last_backup_on", now_datetime())
        frappe.db.set_value("One Drive", None, "last_backup_status", "Success")  
        frappe.db.commit()

        # Send email notification if enabled
        if one_drive.send_email_for_successful_backup and one_drive.email:
            send_backup_email(one_drive.email, backup_files)

        frappe.msgprint(_("Backup successfully uploaded to OneDrive."))

    except Exception as e:
        #  Capture full error message
        error_message = f"Backup failed: {str(e)}\n{traceback.format_exc()}"
        frappe.logger().error(error_message)

        # Store error message in a separate field (not last_backup_on)
        frappe.db.set_value("One Drive", None, "last_backup_status", error_message)
        frappe.db.commit()

        # Properly fail the RQ job (this will make it show as failed in UI)
        raise frappe.ValidationError(error_message)

def upload_to_onedrive(access_token, file_path, folder_id):
    """Upload a file to OneDrive inside the specified folder."""
    headers = {"Authorization": f"Bearer {access_token}"}
    file_name = os.path.basename(file_path)

    upload_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{folder_id}:/{file_name}:/content"
    with open(file_path, "rb") as file_data:
        try:
            response = requests.put(upload_url, headers=headers, data=file_data, timeout=60)
        except requests.exceptions.Timeout:
            frappe.logger().error(f"Timeout while uploading {file_name}. Retrying...")
            frappe.throw(_("Upload to OneDrive timed out. Please try again."))

    if response.status_code in (200, 201):
        frappe.logger().info(f"File uploaded successfully: {file_name}")
    elif response.status_code == 401:
        frappe.logger().warning(f"⚠️ Access token expired. Retrying upload after refreshing token...")
        access_token = refresh_access_token(frappe.get_single("Microsoft Settings"))
        upload_to_onedrive(access_token, file_path, folder_id)  # Retry upload
    else:
        frappe.logger().error(f"Failed to upload {file_name}. Response: {response.text}")
        frappe.throw(_("Failed to upload file {0} to OneDrive.").format(file_name))

def refresh_access_token(ms_settings):
    """Refresh the access token using the refresh token."""
    response = requests.post(
        f"https://login.microsoftonline.com/{ms_settings.tenant_id}/oauth2/v2.0/token",
        data={
            "client_id": ms_settings.client_id,
            "client_secret": ms_settings.get_password("client_secret"),
            "refresh_token": ms_settings.refresh_token,
            "grant_type": "refresh_token",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    ).json()

    if "access_token" in response:
        frappe.db.set_value("Microsoft Settings", None, "access_token", response["access_token"])
        frappe.db.set_value("Microsoft Settings", None, "token_expiry", 
                            frappe.utils.add_to_date(now_datetime(), seconds=response.get("expires_in", 3600)))
        if "refresh_token" in response:
            frappe.db.set_value("Microsoft Settings", None, "refresh_token", response["refresh_token"])

        frappe.db.commit()
        return response["access_token"]
    
    else:
        raise Exception(_("Unable to refresh access token. Please reauthorize Microsoft account."))

def ensure_onedrive_folder_exists(access_token, one_drive):
    """Check or create a folder in OneDrive."""
    folder_name = one_drive.backup_folder_name
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    try:
        search_url = f"https://graph.microsoft.com/v1.0/me/drive/root/children?$filter=name eq '{folder_name}'"
        search_response = requests.get(search_url, headers=headers, timeout=15).json()

        if "value" in search_response and search_response["value"]:
            return search_response["value"][0]["id"]

        create_url = "https://graph.microsoft.com/v1.0/me/drive/root/children"
        create_response = requests.post(
            create_url,
            headers=headers,
            json={"name": folder_name, "folder": {}, "@microsoft.graph.conflictBehavior": "rename"},
            timeout=15,
        ).json()

        if "id" in create_response:
            return create_response["id"]

        elif "error" in create_response:
            error_message = create_response["error"].get("message", "Unknown error")
            error_code = create_response["error"].get("code", "No error code")
            raise Exception(f"OneDrive API Error: {error_code} - {error_message}")

    except requests.exceptions.RequestException as re:
        raise Exception(f"OneDrive API Request Failed: {str(re)}")

def send_backup_email(email, backup_files):
    """Send an email notification after a successful backup."""
    user_full_name = frappe.db.get_value("User", frappe.session.user, "full_name") or "User"

    subject = _("OneDrive Backup Completed")
    message = f"<p>Dear {user_full_name},</p><p>Your backup to OneDrive was successful.</p><ul>"
    for file in backup_files:
        message += f"<li>{os.path.basename(file)}</li>"
    message += "</ul><p>Thank you.</p>"

    frappe.sendmail(recipients=email, subject=subject, message=message)
    frappe.logger().info(f"Backup email sent to {email}")
