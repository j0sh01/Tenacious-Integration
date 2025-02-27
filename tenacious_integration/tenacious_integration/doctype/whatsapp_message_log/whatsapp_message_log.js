// Copyright (c) 2025, Joshua Joseph Michael and contributors
// For license information, please see license.txt

frappe.ui.form.on('WhatsApp Message Log', {
    refresh: function(frm) {
        // Add resend button for failed messages
        // Add "Send Message" button for new messages
        if (!frm.doc.message_id && frm.doc.status !== "Sent") {
            frm.add_custom_button(__('Send Message'), function() {
                frappe.call({
                    method: 'tenacious_integration.tenacious_integration.api.send_whatsapp_message',
                    args: {
                        doc_name: frm.doc.name
                    },
                    callback: function(r) {
                        if (r.message && r.message.success) {
                            frappe.msgprint(__('Message sent successfully!'));
                            frm.reload_doc();
                        } else {
                            frappe.msgprint(__('Failed to send message: ') + (r.message ? r.message.error : 'Unknown error'));
                        }
                    }
                });
            }).addClass('btn-primary');
        }

        if (frm.doc.status === "Failed") {
            frm.add_custom_button(__('Resend Message'), function() {
                frappe.confirm(
                    __('Are you sure you want to resend this message?'),
                    function() {
                        // Yes
                        frm.call({
                            doc: frm.doc,
                            method: 'resend',
                            callback: function(r) {
                                if (r.message && r.message.success) {
                                    frappe.msgprint(__('Message resent successfully!'));
                                    frm.reload_doc();
                                } else {
                                    frappe.msgprint(__('Failed to resend message: ') + 
                                        (r.message ? r.message.error : 'Unknown error'));
                                }
                            }
                        });
                    },
                    function() {
                        // No - do nothing
                    }
                );
            });
        }
        
        // Show status indicators
        if (frm.doc.status) {
            let status_color = {
                "Queued": "blue",
                "Sent": "orange", 
                "Delivered": "green",
                "Read": "darkgreen",
                "Failed": "red"
            };
            
            frm.set_indicator(frm.doc.status, status_color[frm.doc.status]);
        }
        
        // Add button to check message status (only for sent messages)
        if (frm.doc.status !== "Queued" && frm.doc.status !== "Failed" && frm.doc.message_id) {
            frm.add_custom_button(__('Check Message Status'), function() {
                frm.call({
                    doc: frm.doc,
                    method: 'get_message_history',
                    callback: function(r) {
                        if (r.message && r.message.success) {
                            let data = r.message.data;
                            let status_msg = __('Current Status: ') + frm.doc.status;
                            
                            // Format timestamps
                            if (frm.doc.sent_at) {
                                status_msg += '<br>' + __('Sent: ') + frappe.datetime.str_to_user(frm.doc.sent_at);
                            }
                            if (frm.doc.delivered_at) {
                                status_msg += '<br>' + __('Delivered: ') + frappe.datetime.str_to_user(frm.doc.delivered_at);
                            }
                            if (frm.doc.read_at) {
                                status_msg += '<br>' + __('Read: ') + frappe.datetime.str_to_user(frm.doc.read_at);
                            }
                            
                            frappe.msgprint({
                                title: __('Message Status'),
                                message: status_msg,
                                indicator: status_color[frm.doc.status]
                            });
                            
                            // Reload in case status was updated
                            frm.reload_doc();
                        } else {
                            frappe.msgprint(__('Failed to check message status: ') + 
                                (r.message ? r.message.error : 'Unknown error'));
                        }
                    }
                });
            });
        }
    },

    
    
    onload: function(frm) {
        // For template messages, provide information about format
        if (frm.doc.message_type === "Template" && frm.doc.docstatus === 0) {
            frm.set_df_property('message_content', 'description', 
                __('For templates, use format: template_name:language_code (e.g., hello_world:en_US)'));
        }
    }
});