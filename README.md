# SEPA File Export

A Frappe/ERPNext application that generates ISO 20022 SEPA XML Payment Instruction files (`pain.001.001.03`, STUZZA Austrian variant) from Purchase Invoices.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## Features

- **SEPA XML generation** — pain.001.001.03 with STUZZA Austrian namespace (`ISO:pain.001.001.03:APC:STUZZA:payments:003`)
- **Three export entry points:**
  - Single invoice — via **Create → Export SEPA XML** on any open Purchase Invoice
  - List-view bulk — select multiple invoices in the Purchase Invoice list, then **Actions → Export SEPA XML**
  - Dedicated page — full-featured export tool at `/app/sepa-export` with company selector, review table, and summary
- **Pre-flight validation** — checks debtor and creditor addresses, bank accounts, and IBANs before generating XML
- **IBAN / BIC resolution** — supplier bank details resolved automatically from ERPNext Bank Account records linked via `party_type` / `party`
- **BIC fallback** — when no BIC (SWIFT code) is available, the XML uses `<Othr><Id>NOTPROVIDED</Id></Othr>` per SEPA rules
- **ISO 20022 field compliance** — automatic truncation to schema-mandated field lengths, structured postal addresses (`StrtNm`, `PstCd`, `TwnNm`, `Ctry`) in correct XSD order
- **Inline IBAN display** — the export dialogs show each supplier's IBAN so you can verify before exporting
- **Missing bank account helper** — a quick "+ Add" button links directly to the Bank Account creation form pre-filled with the supplier name

## Requirements

- Frappe/ERPNext **v15** or later
- Python **3.10+**

## Installation

```bash
bench get-app frappe_sepa_export https://github.com/chief-nerd/frappe_sepa_export && && bench install-app frappe_sepa_export
```

## Update

```bash
cd apps/frappe_sepa_export && git pull && cd ../.. && bench build --app frappe_sepa_export && bench migrate
```

## Configuration

### 1. SEPA Settings

Navigate to **SEPA Settings** and create a record for your company:

| Field                | Description                                                         |
| -------------------- | ------------------------------------------------------------------- |
| Company              | The ERPNext company that will act as debtor                         |
| Default Bank Account | The company's bank account used for outgoing SEPA payments          |
| Default Debtor Name  | Name that appears as debtor in the XML (falls back to company name) |
| Default Country Code | ISO country code, e.g. `AT`, `DE`                                   |
| SEPA Schema Version  | `pain.001.001.03` (default) or `pain.001.001.02`                    |

### 2. Company Address

Create an **Address** linked to your company (via Dynamic Link) with street, postcode, city, and country. This is required for the debtor postal address in the XML.

### 3. Supplier Bank Accounts

For each supplier you want to pay via SEPA:

1. Go to **Bank Account** and create a new record
2. Fill in the **IBAN** (required)
3. Set **Party Type** = `Supplier` and **Party** = the supplier name
4. Optionally link a **Bank** record that has a **SWIFT Number** — this will be used as the BIC in the XML

> **Tip:** If a supplier has no bank account yet, the export dialogs show a "+ Add" button that opens the Bank Account form pre-filled with the supplier's details.

### 4. Supplier Address

Create an **Address** linked to each supplier (via Dynamic Link) with at least street, postcode, city, and country. The XML requires structured creditor postal addresses.

## Usage

### Single Invoice Export

1. Open a submitted Purchase Invoice (status: Unpaid, Overdue, or Partly Paid)
2. Click **Create → Export SEPA XML**
3. Review the pre-filled debtor information and supplier IBAN
4. Click **Generate SEPA XML** — the file downloads immediately

### Bulk Export from List View

1. Go to the **Purchase Invoice** list
2. Select one or more invoices using the checkboxes
3. Click **Actions → Export SEPA XML**
4. Review the invoice table, edit payment references if needed
5. Click **Generate SEPA XML**

### Dedicated SEPA Export Page

1. Navigate to `/app/sepa-export`
2. Select a company — all open invoices are loaded with IBAN status
3. Check the invoices you want to export
4. Click **Export SEPA XML**

## Generated XML

The output is a valid pain.001.001.03 file using the STUZZA Austrian namespace. Key characteristics:

- One `<PmtInf>` block per invoice
- `<ReqdExctnDt>` set to the chosen execution date
- `<InstdAmt>` uses the invoice's **outstanding amount** (not grand total)
- Creditor BIC resolved from the linked Bank's SWIFT Number; falls back to `NOTPROVIDED`
- All text fields truncated to ISO 20022 maximum lengths (e.g. name 70, town 35, reference 140)

## License

MIT
