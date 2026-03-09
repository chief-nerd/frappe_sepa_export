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
	// Fetch debtor info and supplier bank info in parallel
	let debtor_info = null;
	let supplier_bank = null;
	let calls_done = 0;

	function on_ready() {
		calls_done++;
		if (calls_done === 2 && debtor_info) {
			create_dialog(frm, debtor_info, supplier_bank || {});
		}
	}

	frappe.call({
		method: 'frappe_sepa_export.utils.get_debtor_info',
		args: { company: frm.doc.company },
		callback(r) {
			if (r.message) debtor_info = r.message;
			on_ready();
		}
	});

	frappe.call({
		method: 'frappe_sepa_export.utils.get_supplier_bank_info',
		args: { supplier: frm.doc.supplier },
		callback(r) {
			if (r.message) supplier_bank = r.message;
			on_ready();
		}
	});
}

function create_dialog(frm, debtor_info, supplier_bank) {
	const supplier_iban = supplier_bank.iban
		? supplier_bank.iban.replace(/(.{4})/g, '$1 ').trim()
		: '';

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
				default: frm.doc.outstanding_amount,
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
				fieldtype: 'Section Break',
				label: __('Supplier Bank Account')
			},
			{
				label: __('Supplier'),
				fieldname: 'supplier_name',
				fieldtype: 'Data',
				default: frm.doc.supplier_name || frm.doc.supplier,
				read_only: 1
			},
			{
				fieldtype: 'Column Break'
			},
			{
				label: __('Supplier IBAN'),
				fieldname: 'supplier_iban',
				fieldtype: 'Data',
				default: supplier_iban || __('Not configured'),
				read_only: 1,
				description: supplier_iban
					? ''
					: __('No Bank Account found for this supplier.')
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
				default: frm.doc.bill_no || frm.doc.name,
				description: __('Verwendungszweck – Supplier Invoice No.')
			}
		],
		primary_action_label: __('Generate SEPA XML'),
		primary_action(values) {
			// Validate address fields before export
			frappe.call({
				method: 'frappe_sepa_export.utils.validate_sepa_export',
				args: {
					invoice_names: JSON.stringify([frm.doc.name]),
					company: frm.doc.company
				},
				freeze: true,
				freeze_message: __('Validating…'),
				callback(vr) {
					if (!vr.message) return;
					const result = vr.message;
					if (!result.valid) {
						frappe.confirm(
							__('The following address fields are incomplete:')
							+ '<br><br><ul>'
							+ result.warnings.map(w => `<li>${w}</li>`).join('')
							+ '</ul><br>'
							+ __('The bank may reject the file. Continue anyway?'),
							() => do_export(),
							() => { }
						);
					} else {
						do_export();
					}
				}
			});

			function do_export() {
				d.hide();
				const payment_references = JSON.stringify({
					[frm.doc.name]: values.payment_reference
				});
				frappe.call({
					method: 'frappe_sepa_export.sepa_payment.export.export_payment_instruction_xml',
					args: {
						invoice_names: values.invoices,
						execution_date: values.execution_date,
						debtor_name: debtor_info.debtor_name,
						debtor_iban: debtor_info.debtor_iban,
						debtor_bic: debtor_info.debtor_bic || '',
						debtor_street: debtor_info.debtor_street || '',
						debtor_postcode: debtor_info.debtor_postcode || '',
						debtor_city: debtor_info.debtor_city || '',
						debtor_country: debtor_info.debtor_country,
						payment_references: payment_references
					},
					freeze: true,
					freeze_message: __('Generating SEPA XML…'),
					callback(r) {
						if (r.message) {
							const blob = new Blob([r.message.filecontent], { type: 'application/xml' });
							const url = URL.createObjectURL(blob);
							const a = document.createElement('a');
							a.href = url;
							a.download = r.message.filename;
							a.click();
							URL.revokeObjectURL(url);
						}
					}
				});
			}
		}
	});

	d.show();
}
