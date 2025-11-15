# SEPA File Export

A custom Frappe application for ERPNext that enables exporting Purchase Invoices as SEPA XML Payment Instruction files (pain.001.001.03) for bank payments.

## Features

- Generate SEPA XML Payment Instruction files (pain.001.001.03) for single or multiple Purchase Invoices
- Retrieve supplier banking information directly from the Supplier DocType
- Configure company banking details and SEPA export settings
- Support for batch payments

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

1. After installation, navigate to SEPA Settings and create a new configuration for your company
2. Add custom fields to your Supplier DocType for banking details (these will be added automatically during installation)
3. Configure default banking information for your suppliers

## Usage

1. Open a submitted Purchase Invoice
2. Click on "Create" > "Export SEPA XML"
3. Fill in the required information in the dialog
4. Click "Generate SEPA XML" to download the file
5. Import the downloaded XML file to your banking software to initiate the payment

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
