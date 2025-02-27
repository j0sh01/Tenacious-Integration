// Copyright (c) 2025, Joshua Joseph Michael and contributors
// For license information, please see license.txt


frappe.ui.form.on('WhatsApp Settings', {
    refresh: function(frm) {
        // Add a button to test the connection
        frm.add_custom_button(__('Test Connection'), function() {
            frappe.call({
                method: 'tenacious_integration.tenacious_integration.api.test_connection',
                args: {},
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.msgprint(__('Connection successful!'));
                    } else {
                        frappe.msgprint(__('Connection failed: ') + (r.message ? r.message.error : 'Unknown error'));
                    }
                }
            });
        });

        // Add a button to generate Access Token
        frm.add_custom_button(__('Generate Access Token'), function() {
            frappe.call({
                method: 'tenacious_integration.tenacious_integration.api.generate_access_token',
                args: {
                    doc_name: frm.doc.name
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('api_key', r.message);
                        frm.save();
                        frappe.msgprint(__('Access Token generated successfully!'));
                    } else {
                        frappe.msgprint(__('Failed to generate Access Token.'));
                    }
                }
            });
        });

        
        // Add a button to generate webhook URL
        frm.add_custom_button(__('Generate Webhook URL'), function() {
            frappe.call({
                method: 'tenacious_integration.tenacious_integration.api.generate_webhook_url',
                args: {
                    doc_name: frm.doc.name
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('webhook_url', r.message);
                        frm.save();
                        frappe.msgprint(__('Webhook URL generated: ') + r.message);
                        
                        frappe.msgprint({
                            title: __('Webhook Configuration Instructions'),
                            message: __('Important: You need to configure this webhook URL in your Meta Developer Portal. '
                            + 'Go to your WhatsApp app settings, navigate to Webhooks, and add this URL. '
                            + 'Set the webhook fields to include "messages".'),
                        });
                    } else {
                        frappe.msgprint(__('Failed to generate Webhook URL.'));
                    }
                }
            });
        });
        
        // Add a button to view available templates 
        frm.add_custom_button(__('View Message Templates'), function() {
            if (!frm.doc.enabled || !frm.doc.api_key || !frm.doc.whatsapp_business_account_id) {
                frappe.msgprint(__('Please enable integration and provide access token and WhatsApp Business Account ID first.'));
                return;
            }
            
            frappe.call({
                method: 'tenacious_integration.tenacious_integration.api.get_message_templates',
                args: {},
                callback: function(r) {
                    if (r.message && r.message.success && r.message.templates) {
                        // Format templates for display
                        let message = __('Available Templates:<br><br>');
                        r.message.templates.forEach(template => {
                            message += `<b>${template.name}</b> (${template.language})<br>`;
                            message += `Category: ${template.category}<br>`;
                            message += `Status: ${template.status}<br><br>`;
                        });
                        
                        frappe.msgprint({
                            title: __('WhatsApp Message Templates'),
                            message: message,
                            wide: true
                        });
                    } else {
                        frappe.msgprint(__('Failed to fetch templates: ') + (r.message ? r.message.error : 'Unknown error'));
                    }
                }
            });
        });
    },
    
    enabled: function(frm) {
        // Toggle required fields based on enabled status
        frm.toggle_reqd(['api_key', 'phone_number_id', 'whatsapp_business_account_id', 'phone_number'], frm.doc.enabled);
    }
});