

# import frappe
# import requests
# import json
# from frappe.model.document import Document

# class AzampaySettings(Document):
#     pass

# @frappe.whitelist()
# def generate_azampay_token():
#     # Fetch single doctype settings
#     doc = frappe.get_single("Azampay Settings")

#     # Ensure required fields are present
#     if not doc.app_name or not doc.client_id or not doc.client_secret:
#         frappe.throw("App Name, Client ID, and Client Secret are required.")

#     # API Endpoint
#     url = "https://authenticator-sandbox.azampay.co.tz/AppRegistration/GenerateToken"
    
#     # Payload
#     payload = {
#         "appName": doc.app_name,
#         "clientId": doc.get_password("client_id"),
#         "clientSecret": doc.get_password("client_secret")
#     }
    
#     headers = {
#         "Content-Type": "application/json"
#     }

#     try:
#         # Send request to AzamPay API
#         response = requests.post(url, headers=headers, data=json.dumps(payload))

#         # Log response for debugging
#         frappe.logger().info(f"Azampay API Response: {response.text}")

#         # Ensure valid JSON response
#         try:
#             data = response.json()
#         except ValueError:
#             frappe.throw(f"Invalid JSON response: {response.text}")

#         # Extract token and expiry
#         auth_token = data.get("data", {}).get("accessToken")
#         token_expiry = data.get("data", {}).get("expire")
#         frappe.throw(token_expiry)

#         # Handle object format in expire field
#         if isinstance(token_expiry, dict):
#             token_expiry = json.dumps(token_expiry)  # Convert to string if it's an object

#         if auth_token:
#             # Update fields in the Doctype
#             doc.auth_token = auth_token
#             doc.token_expiry = token_expiry  # Store expiry date as received
#             doc.token_status = "Active"

#             # Save the Doctype automatically
#             doc.save()
#             frappe.db.commit()  # Ensure changes are committed to the database

#             # Notify user
#             frappe.msgprint("Token generated and saved successfully!", alert=True, indicator="green")

#             # Return the token
#             return auth_token

#         else:
#             # Log and throw error if token is not found
#             frappe.logger().error(f"Azampay Token Generation Failed: {data}")
#             frappe.throw(f"No token received from API. Full response: {data}")

#     except requests.exceptions.RequestException as e:
#         frappe.log_error(frappe.get_traceback(), "Azampay Token Generation Request Error")
#         frappe.throw(f"Request failed: {str(e)}")

#     except Exception as e:
#         frappe.log_error(frappe.get_traceback(), "Azampay Token Generation Error")
#         frappe.throw(f"An error occurred: {str(e)}")




import frappe
import requests
import json
from frappe.model.document import Document
from datetime import datetime, timezone  # Using built-in timezone support

class AzampaySettings(Document):
    pass

@frappe.whitelist()
def generate_azampay_token():
    # Fetch single doctype settings
    doc = frappe.get_single("Azampay Settings")

    # Ensure required fields are present
    if not doc.app_name or not doc.client_id or not doc.client_secret:
        frappe.throw("App Name, Client ID, and Client Secret are required.")

    # API Endpoint
    url = "https://authenticator-sandbox.azampay.co.tz/AppRegistration/GenerateToken"
    
    # Payload
    payload = {
        "appName": doc.app_name,
        "clientId": doc.get_password("client_id"),
        "clientSecret": doc.get_password("client_secret")
    }
    
    headers = {
        "Content-Type": "application/json"
    }

    try:
        # Send request to AzamPay API
        response = requests.post(url, headers=headers, data=json.dumps(payload))

        # Log response for debugging
        frappe.logger().info(f"Azampay API Response: {response.text}")

        # Ensure valid JSON response
        try:
            data = response.json()
        except ValueError:
            frappe.throw(f"Invalid JSON response: {response.text}")

        # Extract token and expiry
        auth_token = data.get("data", {}).get("accessToken")
        token_expiry = data.get("data", {}).get("expire")  # Expecting "2025-03-10T18:50:22Z"

        # Convert expire field to proper datetime format
        if token_expiry:
            try:
                # Convert from ISO 8601 format to a Python datetime object in UTC
                token_expiry_dt = datetime.strptime(token_expiry, "%Y-%m-%dT%H:%M:%SZ")
                token_expiry_dt = token_expiry_dt.replace(tzinfo=timezone.utc)  # Ensure it's UTC
                
                # Convert to ERPNext-compatible datetime format
                token_expiry = token_expiry_dt.strftime("%Y-%m-%d %H:%M:%S")

            except ValueError:
                frappe.throw(f"Invalid expiry format received: {token_expiry}")

        if auth_token:
            # Update fields in the Doctype
            doc.auth_token = auth_token
            doc.token_expiry = token_expiry  # Store expiry date in proper format
            doc.token_status = "Active"

            # Save the Doctype automatically
            doc.save()
            frappe.db.commit()  # Ensure changes are committed to the database

            # Notify user
            frappe.msgprint("Token generated and saved successfully!", alert=True, indicator="green")

            # Return the token
            return auth_token

        else:
            # Log and throw error if token is not found
            frappe.logger().error(f"Azampay Token Generation Failed: {data}")
            frappe.throw(f"No token received from API. Full response: {data}")

    except requests.exceptions.RequestException as e:
        frappe.log_error(frappe.get_traceback(), "Azampay Token Generation Request Error")
        frappe.throw(f"Request failed: {str(e)}")

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Azampay Token Generation Error")
        frappe.throw(f"An error occurred: {str(e)}")
