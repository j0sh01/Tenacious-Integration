// Copyright (c) 2025, Joshua Joseph Michael and contributors
// For license information, please see license.txt

// One Drive JavaScript
frappe.ui.form.on("One Drive", {
    refresh: function (frm) {
        if (!frm.doc.enable) {
            frm.dashboard.set_headline(
                __("Enable Microsoft Integration in {0}.", [
                    `<a href='/app/microsoft-settings'>${__("Microsoft Settings")}</a>`,
                ])
            );
        }

        if (frm.doc.enable && frm.doc.refresh_token && frm.doc.authorization_code) {
            frm.page.set_indicator("Authorized", "green");
        } else {
            frm.page.set_indicator("Unauthorized", "red");
        }

        if (frm.doc.enable && frm.doc.refresh_token) {
            frm.add_custom_button(__("Take Backup Now"), function () {
                frappe.call({
                    method: "tenacious_integration.tenacious_integration.doctype.one_drive.one_drive.take_backup",
                }).then(() => {
                    frappe.show_alert({
                        message: __("Backup has started. Check logs for progress."),
                        indicator: "green",
                    });
                });
            }).addClass("btn-success");
        }
    },
});

// // one_drive.js
// frappe.ui.form.on('One Drive', {
//     refresh: function(frm) {
//         frm.add_custom_button(__('Backup Now'), function() {
//             frappe.call({
//                 method: 'tenacious_integration.tenacious_integration.doctype.one_drive.one_drive.backup_to_onedrive',
//                 callback: function(r) {
//                     if (r.message) {
//                         frappe.msgprint(__('Backup initiated. Check logs for details.'));
//                     }
//                 }
//             });
//         });
//     }
// });


// frappe.ui.form.on("One Drive", {
//     refresh: function (frm) {
//         if (!frm.doc.enable) {
//             frm.dashboard.set_headline(
//                 __("To use One Drive, enable {0}.", [
//                     `<a href='/app/one-drive-settings'>${__("One Drive Settings")}</a>`,
//                 ])
//             );
//         }

//         frappe.realtime.on("upload_to_one_drive", (data) => {
//             if (data.progress) {
//                 const progress_title = __("Uploading to One Drive");
//                 frm.dashboard.show_progress(
//                     progress_title,
//                     (data.progress / data.total) * 100,
//                     data.message
//                 );
//                 if (data.progress === data.total) {
//                     frm.dashboard.hide_progress(progress_title);
//                 }
//             }
//         });

//         if (frm.doc.enable && frm.doc.refresh_token) {
//             let sync_button = frm.add_custom_button(__("Take Backup"), function () {
//                 frappe.show_alert({
//                     indicator: "green",
//                     message: __("Backing up to One Drive."),
//                 });
//                 frappe
//                     .call({
//                         method: "tenacious_integration.tenacious_integration.doctype.one_drive.one_drive.take_backup",
//                         btn: sync_button,
//                     })
//                     .then((r) => {
//                         frappe.msgprint(r.message);
//                     });
//             });
//         }

//         if (frm.doc.enable && frm.doc.backup_folder_name && !frm.doc.refresh_token) {
//             frm.dashboard.set_headline(
//                 __("Click on <b>Authorize One Drive Access</b> to authorize One Drive Access.")
//             );

//             frm.add_custom_button(__("Authorize One Drive Access"), function () {
//                 frappe.call({
//                     method: "tenacious_integration.tenacious_integration.doctype.one_drive.one_drive.authorize_access",
//                     args: {
//                         reauthorize: frm.doc.authorization_code ? 1 : 0,
//                         state: JSON.stringify({
//                             tenant_id: frm.doc.tenant_id,
//                             redirect: "/app/Form/One Drive",
//                             success_query_param: "",
//                             failure_query_param: ""
//                         }),
//                     },
//                     callback: function (r) {
//                         if (!r.exc) {
//                             frm.save();
//                             window.open(r.message.url);
//                         }
//                     },
//                 });
//             });
//         }

//         if (frm.doc.enable && frm.doc.refresh_token && frm.doc.authorization_code) {
//             frm.page.set_indicator("Authorized", "green");
//         }
//     },
//     authorize_one_drive_access: function (frm) {
//         frappe.call({
//             method: "tenacious_integration.tenacious_integration.doctype.one_drive.one_drive.authorize_access",
//             args: {
//                 reauthorize: frm.doc.authorization_code ? 1 : 0,
//                 state: JSON.stringify({
//                     tenant_id: frm.doc.tenant_id,
//                     redirect: "/app/Form/One Drive",
//                     success_query_param: "",
//                     failure_query_param: ""
//                 }),
//             },
//             callback: function (r) {
//                 if (!r.exc) {
//                     frm.save();
//                     window.open(r.message.url);
//                 }
//             },
//         });
//     },
// });
