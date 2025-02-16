// // Copyright (c) 2025, Joshua Joseph Michael and contributors
// // For license information, please see license.txt

// frappe.ui.form.on("Microsoft Settings", {
//     refresh: function(frm) {
//         // Show dashboard headline if integration is not enabled
//         if (!frm.doc.enable) {
//             frm.dashboard.set_headline(
//                 __("Enable Microsoft Integration to use this feature.")
//             );
//         }

//         // Add custom buttons based on the integration status
//         if (frm.doc.enable) {
//             // Show "Authorize Access" button if not authorized
//             if (!frm.doc.refresh_token && !frm.doc.authorization_code) {
//                 frm.add_custom_button(__("Authorize Access"), function() {
//                     frappe.call({
//                         method: "tenacious_integration.tenacious_integration.doctype.microsoft_settings.microsoft_settings.authorize_access",
//                         callback: function(r) {
//                             if (r.message && r.message.url) {
//                                 // Open the OAuth URL in a new tab
//                                 window.open(r.message.url, "_blank");
//                             }
//                         }
//                     });
//                 }).addClass("btn-primary");
//             }

//             // Show "List Files in OneDrive" button if authorized
//             if (frm.doc.refresh_token && frm.doc.authorization_code) {
//                 frm.add_custom_button(__("List Files in OneDrive"), function() {
//                     frappe.call({
//                         method: "tenacious_integration.tenacious_integration.doctype.microsoft_settings.microsoft_settings.list_files_in_onedrive",
//                         callback: function(r) {
//                             if (r.message) {
//                                 // Display the list of files
//                                 frappe.msgprint({
//                                     title: __("Files in OneDrive"),
//                                     message: JSON.stringify(r.message, null, 4)
//                                 });
//                             }
//                         }
//                     });
//                 });
//             }

//             // Show "Refresh Access Token" button if authorized
//             if (frm.doc.refresh_token) {
//                 frm.add_custom_button(__("Refresh Access Token"), function() {
//                     frappe.call({
//                         method: "tenacious_integration.tenacious_integration.doctype.microsoft_settings.microsoft_settings.refresh_access_token",
//                         callback: function(r) {
//                             if (r.message) {
//                                 frappe.msgprint(__("Access token refreshed successfully."));
//                             }
//                         }
//                     });
//                 });
//             }
//         }

//         // Set authorization status indicator
//         if (frm.doc.enable && frm.doc.refresh_token && frm.doc.authorization_code) {
//             frm.page.set_indicator(__("Authorized"), "green");
//         } else {
//             frm.page.set_indicator(__("Unauthorized"), "red");
//         }
//     }
// });

// Copyright (c) 2025, Joshua Joseph Michael and contributors
// For license information, please see license.txt

frappe.ui.form.on("Microsoft Settings", {
    refresh: function(frm) {
        if (!frm.doc.enable) {
            frm.dashboard.set_headline(
                __("Enable Microsoft Integration to use this feature.")
            );
        }

        if (frm.doc.enable) {
            // Show "Authorize Access" button if not authorized
            if (!frm.doc.refresh_token && !frm.doc.authorization_code) {
                frm.add_custom_button(__("Authorize Access"), function() {
                    frappe.call({
                        method: "tenacious_integration.tenacious_integration.doctype.microsoft_settings.microsoft_settings.authorize_access",
                        callback: function(r) {
                            if (r.message && r.message.url) {
                                // ✅ Redirect user to Microsoft's login page
                                window.location.href = r.message.url;
                            } else {
                                frappe.msgprint(__("Failed to generate authorization URL."));
                            }
                        }
                    });
                }).addClass("btn-primary");
            }

            // Show "List Files in OneDrive" button if authorized
            if (frm.doc.refresh_token && frm.doc.authorization_code) {
                frm.add_custom_button(__("List Files in OneDrive"), function() {
                    frappe.call({
                        method: "tenacious_integration.tenacious_integration.doctype.microsoft_settings.microsoft_settings.list_files_in_onedrive",
                        callback: function(r) {
                            if (r.message) {
                                let fileList = JSON.stringify(r.message, null, 4);
                                frappe.msgprint({
                                    title: __("Files in OneDrive"),
                                    message: `<pre>${fileList}</pre>`,
                                    indicator: "blue"
                                });
                            } else {
                                frappe.msgprint(__("No files found in OneDrive."));
                            }
                        }
                    });
                });
            }

            // Show "Refresh Access Token" button if authorized
            if (frm.doc.refresh_token) {
                frm.add_custom_button(__("Refresh Access Token"), function() {
                    frappe.call({
                        method: "tenacious_integration.tenacious_integration.doctype.microsoft_settings.microsoft_settings.refresh_access_token",
                        callback: function(r) {
                            if (r.message) {
                                frappe.msgprint(__("Access token refreshed successfully."));
                                frm.reload_doc();
                            }
                        }
                    });
                });
            }
        }

        // Set authorization status indicator
        if (frm.doc.enable && frm.doc.refresh_token && frm.doc.authorization_code) {
            frm.page.set_indicator(__("Authorized"), "green");
        } else {
            frm.page.set_indicator(__("Unauthorized"), "red");
        }
    }
});
