// Custom script for Purchase Invoice to enable SEPA export
frappe.ui.form.on('Purchase Invoice', {
	refresh: function (frm) {
		if (frm.doc.docstatus === 1 && frm.doc.status !== 'Paid') {
			frm.add_custom_button(__('Export SEPA XML'), function () {
				// Check if supplier has banking details
				frappe.call({
					method: 'frappe_sepa_export.frappe_sepa_export.utils.validate_supplier_banking_details',
					args: {
						supplier_name: frm.doc.supplier
					},
					callback: function (r) {
						if (r.message && r.message.valid) {
							// Show export dialog
							show_sepa_export_dialog(frm);
						} else {
							frappe.msgprint({
								title: __('Missing Banking Details'),
								indicator: 'red',
								message: r.message.message || __('Supplier does not have banking details for SEPA export')
							});
						}
					}
				});
			}, __('Create'));
		}
	}
});
