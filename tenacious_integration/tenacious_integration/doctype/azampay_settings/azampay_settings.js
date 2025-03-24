// Copyright (c) 2025, Joshua Joseph Michael and contributors
// For license information, please see license.txt

frappe.ui.form.on('Azampay Settings', {
    generate_token: function (frm) {
        frappe.call({
            method: "tenacious_integration.tenacious_integration.doctype.azampay_settings.azampay_settings.generate_azampay_token",
            callback: function (r) {
                if (!r.exc) {
                    frm.refresh();
                }
            }
        });
    }
});
