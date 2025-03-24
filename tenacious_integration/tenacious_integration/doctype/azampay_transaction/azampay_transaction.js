// Copyright (c) 2025, Joshua Joseph Michael and contributors
// For license information, please see license.txt

frappe.ui.form.on("AzamPay Transaction", {
    refresh: function(frm) {
        if (!frm.doc.__islocal && frm.doc.status !== "Success") {  
            frm.add_custom_button("Process Payment", function() {
                frappe.call({
                    method: "tenacious_integration.tenacious_integration.doctype.azampay_transaction.azampay_transaction.mno_checkout",
                    args: { docname: frm.doc.name },
                    callback: function(r) {
                        if (r.message && r.message.status === "success") {
                            frappe.msgprint("Payment processed! Transaction ID: " + r.message.transaction_id);
                            frm.reload_doc();
                        } else {
                            frappe.msgprint("Payment failed.");
                        }
                    }
                });
            }).addClass("btn-primary");
        }
    }
});


frappe.ui.form.on("AzamPay Transaction", {
    refresh: function(frm) {
        if (!frm.doc.__islocal) {
            // Add QR Code generation button
            frm.add_custom_button("Generate QR Code", function() {
                frappe.call({
                    method: "tenacious_integration.tenacious_integration.doctype.azampay_transaction.azampay_transaction.generate_qr_code",
                    args: { docname: frm.doc.name },
                    callback: function(r) {
                        if (r.message && r.message.status === "success") {
                            frappe.msgprint({
                                title: __("Scan QR Code"),
                                message: `<div style="text-align: center;">
                                            <img src="${r.message.qr_image}" alt="QR Code" style="max-width: 300px; border-radius: 10px;">
                                            <br><br>
                                            <a href="${r.message.redirect_url}" target="_blank" class="btn btn-primary">Go to Payment</a>
                                          </div>`,
                                wide: true
                            });
                        } else {
                            frappe.msgprint("Failed to generate QR Code.");
                        }
                    }
                });
            }).addClass("btn-primary");
        }
    }
});

