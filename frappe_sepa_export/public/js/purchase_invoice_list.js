/**
 * Purchase Invoice List View – Bulk SEPA Export
 *
 * Adds a "Export SEPA XML" action to the list view so the user can
 * select multiple submitted & unpaid invoices, review / correct the
 * values in a table, and generate a single bundled SEPA XML file.
 *
 * Pattern based on alyf-de/banking – custom/purchase_invoice_list.js
 */
console.log("[SEPA Export] purchase_invoice_list.js loaded");

// Ensure the settings object exists (ERPNext should have created it,
// but guard against load-order edge cases)
if (!frappe.listview_settings["Purchase Invoice"]) {
	frappe.listview_settings["Purchase Invoice"] = {};
}

const _sepa_old_onload = frappe.listview_settings["Purchase Invoice"].onload;

frappe.listview_settings["Purchase Invoice"].onload = function (listview) {
	if (_sepa_old_onload) _sepa_old_onload.call(this, listview);

	console.log("[SEPA Export] onload fired, adding action item");

	listview.page.add_action_item(__('Export SEPA XML'), () => {
		const selected = listview.get_checked_items()
			.filter((item) => item.docstatus === 1);
		if (!selected.length) {
			frappe.msgprint(__('Please select at least one submitted Purchase Invoice.'));
			return;
		}
		start_bulk_sepa_export(selected);
	});
};

function start_bulk_sepa_export(selected_docs) {
	const invoice_names = selected_docs.map(d => d.name);

	frappe.call({
		method: 'frappe_sepa_export.utils.get_bulk_invoice_details',
		args: { invoice_names: JSON.stringify(invoice_names) },
		freeze: true,
		freeze_message: __('Fetching invoice details…'),
		callback(r) {
			if (!r.message || !r.message.length) return;
			const invoices = r.message;

			// Derive company from the validated invoices (backend guarantees same company)
			const company = invoices[0].company;

			frappe.call({
				method: 'frappe_sepa_export.utils.get_debtor_info',
				args: { company },
				callback(r2) {
					if (!r2.message) return;
					show_bulk_review_dialog(invoices, r2.message);
				}
			});
		}
	});
}

function show_bulk_review_dialog(invoices, debtor_info) {
	// Build HTML table with editable reference fields
	const total = invoices.reduce((s, inv) => s + inv.outstanding_amount, 0);

	const d = new frappe.ui.Dialog({
		title: __('Review & Export SEPA Payment Bundle'),
		size: 'extra-large',
		fields: [
			{
				fieldtype: 'HTML',
				fieldname: 'invoice_table_area'
			},
			{
				fieldtype: 'Section Break',
				label: __('Summary')
			},
			{
				label: __('Total Amount'),
				fieldname: 'total_amount',
				fieldtype: 'Currency',
				default: total,
				read_only: 1
			},
			{
				fieldtype: 'Column Break'
			},
			{
				label: __('Number of Invoices'),
				fieldname: 'nb_invoices',
				fieldtype: 'Int',
				default: invoices.length,
				read_only: 1
			},
			{
				fieldtype: 'Section Break',
				label: __('Execution')
			},
			{
				label: __('Execution Date'),
				fieldname: 'execution_date',
				fieldtype: 'Date',
				reqd: 1,
				default: frappe.datetime.add_days(frappe.datetime.nowdate(), 1)
			}
		],
		primary_action_label: __('Generate SEPA XML'),
		primary_action(values) {
			// Collect (possibly edited) values from the table
			const rows = d.$wrapper.find('.sepa-review-table tbody tr');
			const invoice_names = [];
			const payment_references = {};
			let has_error = false;

			rows.each(function () {
				const $row = $(this);
				const name = $row.data('invoice');
				const ref = $row.find('.sepa-ref-input').val().trim();
				if (!ref) {
					frappe.msgprint({
						title: __('Missing Reference'),
						message: __('Please provide a payment reference for {0}', [name]),
						indicator: 'orange'
					});
					has_error = true;
					return false; // break
				}
				invoice_names.push(name);
				payment_references[name] = ref;
			});

			if (has_error) return;

			// Validate address fields before export
			frappe.call({
				method: 'frappe_sepa_export.utils.validate_sepa_export',
				args: {
					invoice_names: JSON.stringify(invoice_names),
					company: invoices[0].company
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
				frappe.call({
					method: 'frappe_sepa_export.sepa_payment.export.export_payment_instruction_xml',
					args: {
						invoice_names: invoice_names.join(','),
						execution_date: values.execution_date,
						debtor_name: debtor_info.debtor_name,
						debtor_iban: debtor_info.debtor_iban,
						debtor_bic: debtor_info.debtor_bic || '',
						debtor_street: debtor_info.debtor_street || '',
						debtor_postcode: debtor_info.debtor_postcode || '',
						debtor_city: debtor_info.debtor_city || '',
						debtor_country: debtor_info.debtor_country,
						payment_references: JSON.stringify(payment_references)
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

	// Render the editable table
	const table_html = build_review_table(invoices);
	d.fields_dict.invoice_table_area.$wrapper.html(table_html);
	d.show();

	// Recalculate total when amounts are not editable but keep this
	// hook in case we make amounts editable later
	d.$wrapper.on('change', '.sepa-ref-input', function () {
		// nothing to recalculate, just a hook
	});
}

function build_review_table(invoices) {
	let rows = '';
	for (const inv of invoices) {
		const ref = inv.bill_no || inv.name;
		const status_color = {
			'Unpaid': 'orange',
			'Overdue': 'red',
			'Partly Paid': 'blue'
		}[inv.status] || 'grey';

		const iban_cell = inv.supplier_iban
			? frappe.utils.escape_html(inv.supplier_iban.replace(/(.{4})/g, '$1 ').trim())
			: '<span class="text-danger">' + __('Missing') + '</span>'
			+ ' <a href="/app/bank-account/new?party_type=Supplier'
			+ '&party=' + encodeURIComponent(inv.supplier)
			+ '&account_name=' + encodeURIComponent(inv.supplier_name || inv.supplier)
			+ '" target="_blank" class="btn btn-xs btn-default" style="margin-left:6px;">'
			+ '<i class="fa fa-plus" style="margin-right:3px;"></i>' + __('Add') + '</a>';

		rows += `
		<tr data-invoice="${frappe.utils.escape_html(inv.name)}">
			<td style="vertical-align:middle;">
				<a href="/app/purchase-invoice/${encodeURIComponent(inv.name)}" target="_blank">
					${frappe.utils.escape_html(inv.name)}
				</a>
			</td>
			<td style="vertical-align:middle;">${frappe.utils.escape_html(inv.supplier_name || inv.supplier)}</td>
			<td style="vertical-align:middle; font-family:monospace; font-size:0.9em; white-space:nowrap;">
				${iban_cell}
			</td>
			<td style="vertical-align:middle;">${frappe.utils.escape_html(inv.bill_no || '–')}</td>
			<td style="vertical-align:middle; text-align:right; font-variant-numeric:tabular-nums;">
				${format_currency(inv.outstanding_amount, inv.currency || 'EUR')}
			</td>
			<td style="vertical-align:middle;">
				<span class="indicator-pill ${status_color}">${frappe.utils.escape_html(inv.status)}</span>
			</td>
			<td style="vertical-align:middle;">
				<input
					class="form-control form-control-sm sepa-ref-input"
					type="text"
					value="${frappe.utils.escape_html(ref)}"
					style="min-width:160px;"
				/>
			</td>
		</tr>`;
	}

	return `
	<div style="max-height:400px; overflow:auto; border:1px solid var(--border-color); border-radius:var(--border-radius);">
		<table class="table table-bordered sepa-review-table" style="margin-bottom:0;">
			<thead style="position:sticky; top:0; background:var(--bg-color); z-index:1;">
				<tr>
					<th>${__('Invoice')}</th>
					<th>${__('Supplier')}</th>
					<th>${__('Bank Account (IBAN)')}</th>
					<th>${__('Supplier Inv. No.')}</th>
					<th style="text-align:right;">${__('Amount')}</th>
					<th>${__('Status')}</th>
					<th>${__('Payment Reference')}</th>
				</tr>
			</thead>
			<tbody>
				${rows}
			</tbody>
		</table>
	</div>`;
}
