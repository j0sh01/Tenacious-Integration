// Copyright (c) 2025, Joshua Joseph Michael and contributors
// For license information, please see license.txt

frappe.ui.form.on('Twilio Settings', {
    refresh: function(frm) {
        // ✅ Add Button for Testing Twilio Connection
        frm.add_custom_button(__('Test Twilio Connection'), function() {
            frappe.call({
                method: 'tenacious_integration.tenacious_integration.api.test_twilio_connection',
                callback: function(response) {
                    if (response.message.success) {
                        frappe.msgprint(__('Twilio Connection Successful: ' + response.message.account_name));
                    } else {
                        frappe.msgprint(__('Error: ' + response.message.error));
                    }
                }
            });
        }, __('Actions')).addClass('btn-primary btn-success'); // Green-Blue Button

        // ✅ Add Button for Generating Webhook URL
        frm.add_custom_button(__('Generate Webhook URL'), function() {
            frappe.call({
                method: 'tenacious_integration.tenacious_integration.api.generate_webhook_url',
                args: {
                    doc_name: frm.doc.name
                },
                callback: function(response) {
                    if (response.message.success) {
                        frappe.msgprint(__('Webhook URL Generated: <b>' + response.message.webhook_url + '</b>'));
                        frm.set_value('webhook_url', response.message.webhook_url); // Auto-fill field if exists
                        frm.refresh_field('webhook_url'); // Refresh UI
                    } else {
                        frappe.msgprint(__('Error Generating Webhook: ' + response.message.error));
                    }
                }
            });
        }, __('Actions')).addClass('btn-primary btn-success'); // Green-Blue Button
    }
});

