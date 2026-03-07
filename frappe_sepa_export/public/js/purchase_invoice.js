frappe.ui.form.on('Purchase Invoice', {
	refresh: function (frm) {
		// Only show for Submitted invoices that are unpaid / partly paid / overdue
		const allowed_statuses = ['Unpaid', 'Overdue', 'Partly Paid'];
		if (frm.doc.docstatus === 1 && allowed_statuses.includes(frm.doc.status)) {
			frm.add_custom_button(__('Export SEPA XML'), function () {
				show_sepa_export_dialog(frm);
			}, __('Create'));
		}
	}
});

function show_sepa_export_dialog(frm) {
	// Fetch debtor info from SEPA Settings / Company's default bank account
	frappe.call({
		method: 'frappe_sepa_export.utils.get_debtor_info',
		args: { company: frm.doc.company },
		callback(r) {
			if (r.message) {
				create_dialog(frm, r.message);
			}
		}
	});
}

function create_dialog(frm, debtor_info) {
	const d = new frappe.ui.Dialog({
		title: __('Export SEPA Payment Instruction'),
		fields: [
			{
				label: __('Purchase Invoice'),
				fieldname: 'invoices',
				fieldtype: 'Data',
				default: frm.doc.name,
				read_only: 1
			},
			{
				fieldtype: 'Section Break',
				label: __('Payment Details')
			},
			{
				label: __('Amount'),
				fieldname: 'amount',
				fieldtype: 'Currency',
				default: frm.doc.grand_total,
				read_only: 1
			},
			{
				fieldtype: 'Column Break'
			},
			{
				label: __('Currency'),
				fieldname: 'currency',
				fieldtype: 'Data',
				default: frm.doc.currency || 'EUR',
				read_only: 1
			},
			{
				fieldtype: 'Section Break'
			},
			{
				label: __('Execution Date'),
				fieldname: 'execution_date',
				fieldtype: 'Date',
				reqd: 1,
				default: frappe.datetime.add_days(frappe.datetime.nowdate(), 1)
			},
			{
				fieldtype: 'Column Break'
			},
			{
				label: __('Payment Reference'),
				fieldname: 'payment_reference',
				fieldtype: 'Data',
				reqd: 1,
				default: frm.doc.name,
				description: __('Verwendungszweck')
			}
		],
		primary_action_label: __('Generate SEPA XML'),
		primary_action(values) {
			d.hide();
			open_url_post(
				'/api/method/frappe_sepa_export.sepa_payment.export.export_payment_instruction_xml',
				{
					invoice_names: values.invoices,
					execution_date: values.execution_date,
					debtor_name: debtor_info.debtor_name,
					debtor_iban: debtor_info.debtor_iban,
					debtor_bic: debtor_info.debtor_bic || '',
					debtor_address: debtor_info.debtor_address,
					debtor_country: debtor_info.debtor_country,
					payment_reference: values.payment_reference
				}
			);
		}
	});

	d.show();
}
