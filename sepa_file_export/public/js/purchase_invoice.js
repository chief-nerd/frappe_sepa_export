frappe.ui.form.on('Purchase Invoice', {
	refresh: function (frm) {
		// Only show for submitted invoices that are not paid
		if (frm.doc.docstatus === 1 && frm.doc.status !== 'Paid') {
			frm.add_custom_button(__('Export SEPA XML'), function () {
				show_sepa_export_dialog(frm);
			}, __('Create'));
		}
	}
});

function show_sepa_export_dialog(frm) {
	// Try to get SEPA Settings for the company first
	frappe.db.get_doc('SEPA Settings', frm.doc.company)
		.then(sepa_settings => {
			create_dialog_with_defaults(frm, sepa_settings);
		})
		.catch(() => {
			// If no SEPA settings found, just use company details
			frappe.db.get_value('Company', frm.doc.company, ['name', 'country'])
				.then(result => {
					create_dialog_with_defaults(frm, { company: result.name });
				});
		});
}

function create_dialog_with_defaults(frm, defaults) {
	const d = new frappe.ui.Dialog({
		title: __('Export SEPA Payment Instruction'),
		fields: [
			{
				label: __('Purchase Invoices'),
				fieldname: 'invoices',
				fieldtype: 'MultiSelect',
				options: frm.doc.name,
				default: frm.doc.name,
				read_only: 1
			},
			{
				fieldtype: 'Section Break',
				label: __('Payment Information')
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
				label: __('Currency'),
				fieldname: 'currency',
				fieldtype: 'Data',
				default: 'EUR',
				read_only: 1
			},
			{
				fieldtype: 'Section Break',
				label: __('Debtor Information (Your Company)')
			},
			{
				label: __('Debtor Name'),
				fieldname: 'debtor_name',
				fieldtype: 'Data',
				reqd: 1,
				default: defaults.default_debtor_name || frm.doc.company
			},
			{
				label: __('IBAN'),
				fieldname: 'debtor_iban',
				fieldtype: 'Data',
				reqd: 1,
				description: __('The IBAN of your company bank account')
			},
			{
				fieldtype: 'Column Break'
			},
			{
				label: __('BIC/SWIFT'),
				fieldname: 'debtor_bic',
				fieldtype: 'Data',
				reqd: 0,
				description: __('The BIC/SWIFT code of your company bank (optional, will use "NOTPROVIDED" if empty)')
			},
			{
				label: __('Country'),
				fieldname: 'debtor_country',
				fieldtype: 'Data',
				reqd: 1,
				default: defaults.default_country_code || 'AT',
				description: __('Country code, e.g., AT for Austria')
			},
			{
				fieldtype: 'Section Break'
			},
			{
				label: __('Address'),
				fieldname: 'debtor_address',
				fieldtype: 'Small Text',
				reqd: 1,
				description: __('Company address lines')
			}
		],
		primary_action_label: __('Generate SEPA XML'),
		primary_action(values) {
			// Call the server-side function to generate XML
			frappe.call({
				method: 'frappe_sepa_export.frappe_sepa_export.sepa_payment.export.export_payment_instruction_xml',
				args: {
					invoice_names: values.invoices,
					execution_date: values.execution_date,
					debtor_name: values.debtor_name,
					debtor_iban: values.debtor_iban,
					debtor_bic: values.debtor_bic,
					debtor_address: values.debtor_address.split('\n'),
					debtor_country: values.debtor_country
				},
				callback: function (r) {
					d.hide();
					// The download will be handled by the server
				}
			});
		}
	});

	// If we have default bank account from settings, load its details
	if (defaults.default_bank_account) {
		frappe.db.get_doc('Bank Account', defaults.default_bank_account)
			.then(bank_account => {
				d.set_value('debtor_iban', bank_account.iban);
				// BIC is optional - not using bank_account_no for BIC anymore
			});
	}

	d.show();
}
