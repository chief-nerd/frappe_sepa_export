# SEPA File Export

A custom Frappe application for ERPNext that enables exporting Purchase Invoices as SEPA XML Payment Instruction files (pain.001.001.03) for bank payments.

## Features

- Generate SEPA XML Payment Instruction files (pain.001.001.03) for Purchase Invoices
- Retrieve supplier banking information from the standard ERPNext Bank Account DocType
- Configure company banking details and SEPA export settings via the SEPA Settings DocType
- EUR currency validation

## Installation

### Prerequisites

- Frappe/ERPNext v15 or later
- Python 3.10+

### Install via Bench

```bash
bench get-app frappe_sepa_export https://github.com/chief-nerd/frappe_sepa_export
bench install-app frappe_sepa_export
```

## Configuration

1. After installation, navigate to **SEPA Settings** and create a new configuration for your company
2. Set up Bank Account records for your suppliers with valid IBANs
3. Set each supplier's `default_bank_account` field to their Bank Account

## Usage

1. Open a submitted Purchase Invoice (status must be Unpaid, Overdue, or Partly Paid)
2. Click **Create** > **Export SEPA XML**
3. Fill in the debtor (your company) information in the dialog
4. Click **Generate SEPA XML** to download the file
5. Import the downloaded XML file into your banking software to initiate the payment

## Bank Account Configuration

This app uses the standard ERPNext Bank Account DocType for supplier banking information. To set up a supplier for SEPA export:

1. Create a Bank Account record for the supplier with:
   - IBAN in the `iban` field (required)
   - Link the Bank Account to the Supplier via `party_type` = "Supplier" and `party` = [Your Supplier]
   
   Note: BIC/SWIFT code is not required and will be automatically set as "NOTPROVIDED" in the generated XML
   
2. Set this Bank Account as the default bank account for the Supplier by updating the `default_bank_account` field in the Supplier DocType

The app retrieves all necessary banking details from this standard structure.

## License

MIT
