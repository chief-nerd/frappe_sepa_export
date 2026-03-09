# Copilot Instructions — frappe_sepa_export

## Three Export Entry Points — Keep In Sync!

This app has **three separate JS files** that all trigger the same SEPA XML export. Whenever you change export behaviour, UI columns, validation, or the data shown in the review table, **apply the change to all three files**:

| Entry Point | File | Backend Endpoint for Invoice Data |
|---|---|---|
| Single invoice (form button) | `frappe_sepa_export/public/js/purchase_invoice.js` | `get_supplier_bank_info`, `get_debtor_info` |
| List-view bulk (Actions menu) | `frappe_sepa_export/public/js/purchase_invoice_list.js` | `get_bulk_invoice_details`, `get_debtor_info` |
| Dedicated SEPA page | `frappe_sepa_export/sepa_file_export/page/sepa_export/sepa_export.js` | `get_open_invoices`, `get_debtor_info` |

All three call `export_payment_instruction_xml` for the final XML generation and use `frappe.call` + blob download (never `open_url_post`).

### What must stay consistent across all three:

- **Review table columns** — the list-view bulk dialog and the SEPA page table must show the same columns (Invoice, Supplier, Bank Account/IBAN, Supplier Inv. No., Amount, Status, Payment Reference). The single-invoice dialog shows a subset but must include the supplier IBAN.
- **IBAN display** — formatted with spaces (`IBAN.replace(/(.{4})/g, '$1 ').trim()`), or red "Missing" + "+ Add" button linking to `/app/bank-account/new?party_type=Supplier&party=...&account_name=...`.
- **Pre-flight validation** — all three must call `validate_sepa_export` before generating XML and show warnings with a confirm dialog.
- **Blob download pattern** — `new Blob([r.message.filecontent], { type: 'application/xml' })`, create object URL, click, revoke.
- **Error handling** — use `frappe.msgprint` for user-facing errors, never raw alert().

## Architecture

- **One-way dependency:** `export.py` imports from `utils.py` — never the reverse.
- **All whitelisted endpoints** live in `utils.py` except `export_payment_instruction_xml` which is in `sepa_payment/export.py`.
- **Bank account resolution:** query `tabBank Account` by `party_type='Supplier'`, `party=<name>`, `disabled=0`. Do NOT use `Supplier.default_bank_account`.
- **BIC:** resolved from `Bank.swift_number` (not `branch_code`). Fallback: `<Othr><Id>NOTPROVIDED</Id></Othr>`.
- **IBAN:** always strip spaces and uppercase via `_strip_iban()` before XML output.
- **Field lengths:** enforced by `_t(value, field)` using `_MAX_LEN` dict. Always truncate before writing to XML.
- **Amount:** use `outstanding_amount`, never `grand_total`.
- **Postal address:** structured elements in XSD order: `StrtNm`, `PstCd`, `TwnNm`, `Ctry` (PostalAddress6 sequence).

## SEPA XML Schema

- Namespace: `ISO:pain.001.001.03:APC:STUZZA:payments:003` (Austrian STUZZA variant)
- One `<PmtInf>` block per invoice
