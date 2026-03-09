frappe.pages['sepa-export'].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __('SEPA Payment Export'),
		single_column: true
	});

	wrapper.sepa_tool = new SEPAExportTool(wrapper);
};

class SEPAExportTool {
	constructor(wrapper) {
		this.page = wrapper.page;
		this.body = $(this.page.body);
		this.invoices = [];
		this.debtor_info = null;
		this.setup();
	}

	setup() {
		this.page.set_primary_action(
			__('Generate SEPA XML'),
			() => this.generate_xml(),
			'download'
		);

		this.wrapper = $('<div class="sepa-export-tool"></div>').appendTo(this.body);
		this.make_controls();
		this.table_area = $('<div class="sepa-table-area mt-4"></div>').appendTo(this.wrapper);
		this.summary_area = $('<div class="sepa-summary mt-3"></div>').appendTo(this.wrapper);

		// Auto-load invoices if a company default is set
		if (this.field_group.get_value('company')) {
			this.load_invoices();
		} else {
			this.render_empty_state();
		}
	}

	make_controls() {
		const controls_wrapper = $(
			'<div class="frappe-card p-4"></div>'
		).appendTo(this.wrapper);

		this.field_group = new frappe.ui.FieldGroup({
			fields: [
				{
					fieldname: 'company',
					fieldtype: 'Link',
					options: 'Company',
					label: __('Company'),
					reqd: 1,
					default: frappe.defaults.get_user_default('Company'),
					change: () => {
						this.invoices = [];
						this.debtor_info = null;
						if (this.field_group.get_value('company')) {
							this.load_invoices();
						} else {
							this.render_empty_state();
						}
					}
				},
				{ fieldtype: 'Column Break' },
				{
					fieldname: 'execution_date',
					fieldtype: 'Date',
					label: __('Execution Date'),
					reqd: 1,
					default: frappe.datetime.add_days(frappe.datetime.nowdate(), 1)
				}
			],
			body: controls_wrapper
		});
		this.field_group.make();
	}

	render_empty_state() {
		this.table_area.html(`
			<div class="frappe-card text-center p-5" style="color: var(--text-muted);">
				<p class="mb-2" style="font-size: 1.1em;">
					${__('No invoices loaded yet.')}
				</p>
				<p class="text-muted">
					${__('Select a company and click <strong>Load Open Invoices</strong> to get started.')}
				</p>
			</div>
		`);
		this.summary_area.empty().hide();
	}

	load_invoices() {
		const company = this.field_group.get_value('company');
		if (!company) {
			frappe.msgprint(__('Please select a Company first.'));
			return;
		}

		frappe.call({
			method: 'frappe_sepa_export.utils.get_open_invoices',
			args: { company },
			freeze: true,
			freeze_message: __('Loading open invoices…'),
			callback: (r) => {
				if (!r.message || !r.message.length) {
					this.invoices = [];
					this.table_area.html(`
						<div class="frappe-card text-center p-5 text-muted">
							<p>${__('No open Purchase Invoices found for {0}.', [company])}</p>
						</div>
					`);
					this.summary_area.empty().hide();
					return;
				}

				this.invoices = r.message;
				this.render_table();
				this.update_summary();
			}
		});

		// Fetch debtor info in parallel
		frappe.call({
			method: 'frappe_sepa_export.utils.get_debtor_info',
			args: { company },
			callback: (r2) => {
				if (r2.message) this.debtor_info = r2.message;
			}
		});
	}

	render_table() {
		let rows = '';
		for (const inv of this.invoices) {
			const ref = inv.bill_no || inv.name;
			const status_color = {
				'Unpaid': 'orange',
				'Overdue': 'red',
				'Partly Paid': 'blue'
			}[inv.status] || 'grey';

			rows += `
			<tr data-invoice="${frappe.utils.escape_html(inv.name)}"
			    data-amount="${inv.outstanding_amount}">
				<td class="text-center" style="vertical-align:middle; width:40px;">
					<input type="checkbox" class="sepa-row-check" checked />
				</td>
				<td style="vertical-align:middle;">
					<a href="/app/purchase-invoice/${encodeURIComponent(inv.name)}"
					   target="_blank" style="font-weight:600;">
						${frappe.utils.escape_html(inv.name)}
					</a>
				</td>
				<td style="vertical-align:middle;">
					${frappe.utils.escape_html(inv.supplier_name || inv.supplier)}
				</td>
				<td style="vertical-align:middle; font-family:monospace; font-size:0.9em; white-space:nowrap;">
					${inv.supplier_iban
					? frappe.utils.escape_html(inv.supplier_iban.replace(/(.{4})/g, '$1 ').trim())
					: '<span class="text-danger">' + __('Missing') + '</span>'
					+ ' <a href="/app/bank-account/new?party_type=Supplier'
					+ '&party=' + encodeURIComponent(inv.supplier)
					+ '&account_name=' + encodeURIComponent(inv.supplier_name || inv.supplier)
					+ '" target="_blank" class="btn btn-xs btn-default" style="margin-left:6px;">'
					+ '<i class="fa fa-plus" style="margin-right:3px;"></i>' + __('Add') + '</a>'}
				</td>
				<td style="vertical-align:middle;">
					${frappe.utils.escape_html(inv.bill_no || '–')}
				</td>
				<td style="vertical-align:middle;">
					${frappe.utils.escape_html(inv.posting_date || '')}
				</td>
				<td style="vertical-align:middle; text-align:right; font-variant-numeric:tabular-nums;">
					${format_currency(inv.outstanding_amount, inv.currency || 'EUR')}
				</td>
				<td style="vertical-align:middle;">
					<span class="indicator-pill ${status_color}">
						${frappe.utils.escape_html(inv.status)}
					</span>
				</td>
				<td style="vertical-align:middle;">
					<input class="form-control form-control-sm sepa-ref-input"
					       type="text"
					       value="${frappe.utils.escape_html(ref)}"
					       style="min-width:180px;"
					       placeholder="${__('Payment reference…')}" />
				</td>
			</tr>`;
		}

		this.table_area.html(`
			<div class="frappe-card sepa-table-card">
				<div style="max-height:60vh; overflow:auto;">
					<table class="table table-bordered sepa-export-table" style="margin-bottom:0;">
						<thead style="position:sticky; top:0; background:var(--card-bg); z-index:1;">
							<tr>
								<th class="text-center" style="width:40px;">
									<input type="checkbox" class="sepa-check-all" checked
									       title="${__('Select / Deselect All')}" />
								</th>
								<th>${__('Invoice')}</th>
								<th>${__('Supplier')}</th>
								<th>${__('Bank Account (IBAN)')}</th>
								<th>${__('Supplier Inv. No.')}</th>
								<th>${__('Date')}</th>
								<th style="text-align:right;">${__('Amount')}</th>
								<th>${__('Status')}</th>
								<th>${__('Payment Reference')}</th>
							</tr>
						</thead>
						<tbody>${rows}</tbody>
					</table>
				</div>
			</div>
		`);

		// Bind checkbox events
		this.table_area.find('.sepa-check-all').on('change', (e) => {
			const checked = $(e.target).prop('checked');
			this.table_area.find('.sepa-row-check').prop('checked', checked);
			this.update_summary();
		});
		this.table_area.find('.sepa-row-check').on('change', () => {
			// Update the "all" checkbox state
			const total = this.table_area.find('.sepa-row-check').length;
			const checked = this.table_area.find('.sepa-row-check:checked').length;
			this.table_area.find('.sepa-check-all').prop('checked', total === checked);
			this.update_summary();
		});
	}

	update_summary() {
		const rows = this.table_area.find('tbody tr');
		let count = 0;
		let total = 0;

		rows.each(function () {
			if ($(this).find('.sepa-row-check').prop('checked')) {
				count++;
				total += parseFloat($(this).data('amount')) || 0;
			}
		});

		if (count > 0) {
			this.summary_area.html(`
				<div class="frappe-card p-3 d-flex justify-content-between align-items-center">
					<span>
						<strong>${count}</strong> ${__('invoice(s) selected')}
					</span>
					<span style="font-size: 1.1em; font-variant-numeric: tabular-nums;">
						${__('Total')}: <strong>${format_currency(total, 'EUR')}</strong>
					</span>
				</div>
			`).show();
		} else {
			this.summary_area.html(`
				<div class="frappe-card p-3 text-muted text-center">
					${__('No invoices selected.')}
				</div>
			`).show();
		}
	}

	generate_xml() {
		const company = this.field_group.get_value('company');
		const execution_date = this.field_group.get_value('execution_date');

		if (!company || !execution_date) {
			frappe.msgprint(__('Please fill in Company and Execution Date.'));
			return;
		}

		if (!this.debtor_info) {
			frappe.msgprint(
				__('Debtor information not loaded. Please click "Load Open Invoices" first.')
			);
			return;
		}

		// Collect checked rows
		const rows = this.table_area.find('tbody tr');
		const invoice_names = [];
		const payment_references = {};
		let has_error = false;

		rows.each(function () {
			const $row = $(this);
			if (!$row.find('.sepa-row-check').prop('checked')) return; // skip unchecked

			const name = $row.data('invoice');
			const ref = $row.find('.sepa-ref-input').val().trim();

			if (!ref) {
				frappe.msgprint({
					title: __('Missing Reference'),
					message: __('Please provide a payment reference for {0}.', [name]),
					indicator: 'orange'
				});
				has_error = true;
				return false; // break
			}

			invoice_names.push(name);
			payment_references[name] = ref;
		});

		if (has_error) return;

		if (!invoice_names.length) {
			frappe.msgprint(__('Please select at least one invoice.'));
			return;
		}

		// Validate address fields before export
		const self = this;
		frappe.call({
			method: 'frappe_sepa_export.utils.validate_sepa_export',
			args: {
				invoice_names: JSON.stringify(invoice_names),
				company: company
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
			frappe.call({
				method: 'frappe_sepa_export.sepa_payment.export.export_payment_instruction_xml',
				args: {
					invoice_names: invoice_names.join(','),
					execution_date: execution_date,
					debtor_name: self.debtor_info.debtor_name,
					debtor_iban: self.debtor_info.debtor_iban,
					debtor_bic: self.debtor_info.debtor_bic || '',
					debtor_street: self.debtor_info.debtor_street || '',
					debtor_postcode: self.debtor_info.debtor_postcode || '',
					debtor_city: self.debtor_info.debtor_city || '',
					debtor_country: self.debtor_info.debtor_country,
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
}
