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
	// Get company details for default values
	frappe.db.get_value('Company', frm.doc.company, ['name', 'country'], function (result) {
		const company = result;

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
					default: frm.doc.company
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
					reqd: 1,
					description: __('The BIC/SWIFT code of your company bank')
				},
				{
					label: __('Country'),
					fieldname: 'debtor_country',
					fieldtype: 'Data',
					reqd: 1,
					default: company.country || 'AT',
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
		d.show();
	});
}
