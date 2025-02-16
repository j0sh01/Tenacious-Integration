# Copyright (c) 2025, Joshua Joseph Michael and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import get_datetime, now_datetime, add_to_date
import requests
from frappe import _
from urllib.parse import quote
from frappe.model.document import Document

class MicrosoftSettings(Document):
    pass

def get_token_endpoint(tenant_id):
    """Generate Microsoft OAuth token endpoint dynamically."""
    return f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

def get_authorization_endpoint(tenant_id):
    """Generate Microsoft OAuth authorization endpoint dynamically."""
    return f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"

@frappe.whitelist()
def authorize_access(code=None):
    """Handle Microsoft OAuth authorization flow and save tokens in Microsoft Settings and One Drive."""
    ms_settings = frappe.get_single("Microsoft Settings")

    if not ms_settings.enable:
        frappe.throw(_("Microsoft integration is not enabled."))

    if not ms_settings.client_id or not ms_settings.get_password("client_secret"):
        frappe.throw(_("Please configure Client ID and Client Secret in Microsoft Settings."))

    if not ms_settings.tenant_id:
        frappe.throw(_("Please configure Tenant ID in Microsoft Settings."))

    if not ms_settings.redirect_uri:
        frappe.throw(_("Redirect URI is not set in Microsoft Settings."))

    token_endpoint = get_token_endpoint(ms_settings.tenant_id)

    if code:
        """ Exchange authorization code for tokens """
        try:
            token_response = requests.post(
                token_endpoint,
                data={
                    "client_id": ms_settings.client_id,
                    "client_secret": ms_settings.get_password("client_secret"),
                    "code": code,
                    "redirect_uri": ms_settings.redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10,
            )

            frappe.logger().info(f"Token response status: {token_response.status_code}")
            frappe.logger().info(f"Token response body: {token_response.text}")

            token_response.raise_for_status()
            token_data = token_response.json()

            if "access_token" in token_data:
                """ Save tokens in Microsoft Settings """
                save_tokens(ms_settings, token_data, code)

                """ Redirect user to Microsoft Settings Page """
                frappe.local.response["type"] = "redirect"
                frappe.local.response["location"] = "/app/microsoft-settings/Microsoft Settings"
                return

            else:
                frappe.logger().error(f"Token exchange failed. Response: {token_data}")
                frappe.throw(_("Failed to obtain access token from Microsoft."))

        except requests.exceptions.RequestException as e:
            frappe.logger().error(f"Error during token exchange: {str(e)}")
            frappe.throw(_("An error occurred while exchanging the authorization code. Please try again."))

    """ If no code, generate the authorization URL and return it """
    authorization_url = (
        f"https://login.microsoftonline.com/{ms_settings.tenant_id}/oauth2/v2.0/authorize"
        f"?client_id={ms_settings.client_id}"
        f"&response_type=code"
        f"&redirect_uri={quote(ms_settings.redirect_uri)}"
        f"&scope=Files.ReadWrite.All offline_access"
    )

    frappe.logger().info(f"Generated OAuth URL: {authorization_url}")
    return {"url": authorization_url}

def save_tokens(ms_settings, token_data, code):
    """Save authorization code, access token, and refresh token in Microsoft Settings and One Drive."""
    
    """ Save in Microsoft Settings """
    frappe.db.set_value("Microsoft Settings", None, "authorization_code", code)
    frappe.db.set_value("Microsoft Settings", None, "access_token", token_data["access_token"])
    
    # Ensure correct Datetime format
    token_expiry_time = add_to_date(now_datetime(), seconds=token_data.get("expires_in", 3600))
    frappe.db.set_value("Microsoft Settings", None, "token_expiry", token_expiry_time.strftime('%Y-%m-%d %H:%M:%S'))
    
    last_refresh_time = now_datetime()
    frappe.db.set_value("Microsoft Settings", None, "last_token_refresh_time", last_refresh_time.strftime('%Y-%m-%d %H:%M:%S'))

    if "refresh_token" in token_data:
        frappe.db.set_value("Microsoft Settings", None, "refresh_token", token_data["refresh_token"])

    """ Save in One Drive doctype """
    frappe.db.set_value("One Drive", None, "authorization_code", code)
    if "refresh_token" in token_data:
        frappe.db.set_value("One Drive", None, "refresh_token", token_data["refresh_token"])

    frappe.db.commit()
    frappe.logger().info("Microsoft tokens saved successfully with correct datetime format.")


@frappe.whitelist()
def refresh_access_token():
    """Refresh the access token using the refresh token."""
    ms_settings = frappe.get_single("Microsoft Settings")

    if not ms_settings.refresh_token:
        frappe.throw(_("No refresh token found. Please reauthorize."))

    token_endpoint = get_token_endpoint(ms_settings.tenant_id)

    try:
        token_response = requests.post(
            token_endpoint,
            data={
                "client_id": ms_settings.client_id,
                "client_secret": ms_settings.get_password("client_secret"),
                "refresh_token": ms_settings.refresh_token,
                "grant_type": "refresh_token",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )

        frappe.logger().info(f"Token refresh response status: {token_response.status_code}")
        frappe.logger().info(f"Token refresh response body: {token_response.text}")

        token_response.raise_for_status()
        token_data = token_response.json()

        save_tokens(ms_settings, token_data, ms_settings.authorization_code)

        return {"message": "Access token refreshed successfully."}

    except requests.exceptions.RequestException as e:
        frappe.logger().error(f"Error refreshing access token: {str(e)}")
        frappe.throw(_("Failed to refresh access token. Please reauthorize."))

@frappe.whitelist()
def list_files_in_onedrive():
    """List files in the user's OneDrive."""
    ms_settings = frappe.get_single("Microsoft Settings")
    
    if not ms_settings.access_token:
        frappe.throw(_("No access token found. Please authorize first."))

    token_expiry = get_datetime(ms_settings.token_expiry) if ms_settings.token_expiry else None

    # Check if token is expired
    if token_expiry and now_datetime() > token_expiry:
        frappe.logger().info("Access token expired. Refreshing...")
        refresh_access_token()
        ms_settings = frappe.get_single("Microsoft Settings")

    try:
        response = requests.get(
            "https://graph.microsoft.com/v1.0/me/drive/root/children",
            headers={"Authorization": f"Bearer {ms_settings.access_token}"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        # Attempt to extract meaningful error message from API response
        try:
            error_data = response.json().get("error", {})
            error_code = error_data.get("code", "UnknownError")
            error_message = error_data.get("message", str(e))

            full_error_msg = _("OneDrive API Error: {0} - {1}").format(error_code, error_message)
            frappe.logger().error(f"{full_error_msg}")

            # Throw only this detailed error, avoiding the fallback
            frappe.throw(full_error_msg)

        except Exception:
            # Prevent duplicate error messages by NOT using frappe.throw() twice
            fallback_error = _("Failed to list OneDrive files. Please check the access token.")
            frappe.logger().error(f"{fallback_error}: {str(e)}")
            raise  
