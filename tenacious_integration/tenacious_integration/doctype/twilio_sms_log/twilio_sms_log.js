// Copyright (c) 2025, Joshua Joseph Michael and contributors
// For license information, please see license.txt

frappe.ui.form.on('Twilio SMS Log', {
    refresh: function(frm) {
        if (!frm.is_new()) {  // Only show button for existing records
            frm.add_custom_button(__('Send SMS'), function() {
                frappe.call({
                    method: 'tenacious_integration.tenacious_integration.api.send_twilio_sms',
                    args: {
                        doc_name: frm.doc.name  // Pass the document name
                    },
                    callback: function(response) {
                        if (response.message.success) {
                            frappe.msgprint(__('SMS Sent Successfully! Message ID: ' + response.message.message_id));
                            frm.set_value('status', 'Queued'); // Update status field
                            frm.refresh_field('status');
                        } else {
                            frappe.msgprint(__('Error Sending SMS: ' + response.message.error));
                        }
                    }
                });
            }).addClass('btn-primary btn-success'); // Green-Blue Button
        }
    }
});
