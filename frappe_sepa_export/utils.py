import frappe
from frappe import _


def _get_company_address(company_name):
    """Get address details for a company from its linked Address record.

    Returns:
        list: address lines
    """
    address_name = frappe.db.get_value(
        "Dynamic Link",
        {
            "link_doctype": "Company",
            "link_name": company_name,
            "parenttype": "Address",
        },
        "parent",
    )
    if not address_name:
        return []

    address = frappe.get_doc("Address", address_name)
    lines = []
    if address.address_line1:
        lines.append(address.address_line1)
    if address.address_line2:
        lines.append(address.address_line2)
    city_line = " ".join(filter(None, [address.pincode, address.city]))
    if city_line:
        lines.append(city_line)
    return lines


@frappe.whitelist()
def get_debtor_info(company):
    """Fetch debtor information from SEPA Settings and the company's default bank account.

    Args:
        company (str): Company name

    Returns:
        dict: debtor_name, debtor_iban, debtor_bic, debtor_country, debtor_address
    """
    try:
        sepa_settings = frappe.get_doc("SEPA Settings", company)
    except frappe.DoesNotExistError:
        frappe.throw(
            _(
                "No SEPA Settings found for company {0}. Please create one first."
            ).format(company)
        )

    result = {
        "debtor_name": sepa_settings.default_debtor_name or company,
        "debtor_country": sepa_settings.default_country_code or "AT",
        "debtor_iban": "",
        "debtor_bic": "",
        "debtor_address": "",
    }

    if sepa_settings.default_bank_account:
        try:
            bank_account = frappe.get_doc(
                "Bank Account", sepa_settings.default_bank_account
            )
            result["debtor_iban"] = bank_account.iban or ""
        except frappe.DoesNotExistError:
            frappe.throw(
                _("Bank Account {0} configured in SEPA Settings not found.").format(
                    sepa_settings.default_bank_account
                )
            )

    address_lines = _get_company_address(company)
    result["debtor_address"] = "\n".join(address_lines)

    return result


@frappe.whitelist()
def get_bulk_invoice_details(invoice_names):
    """Return full details for a list of Purchase Invoices so the
    client-side review table can be populated.

    Args:
        invoice_names (str): JSON-encoded list of Purchase Invoice names

    Returns:
        list[dict]: invoice records with key fields
    """
    import json

    if isinstance(invoice_names, str):
        invoice_names = json.loads(invoice_names)

    if not invoice_names:
        return []

    # Fetch WITHOUT docstatus filter so we can report ineligible ones explicitly
    invoices = frappe.get_all(
        "Purchase Invoice",
        filters={"name": ["in", invoice_names]},
        fields=[
            "name",
            "supplier",
            "supplier_name",
            "bill_no",
            "grand_total",
            "outstanding_amount",
            "currency",
            "status",
            "company",
            "posting_date",
            "docstatus",
        ],
        order_by="posting_date asc",
    )

    # Report invoices that are not submitted
    not_submitted = [inv["name"] for inv in invoices if inv["docstatus"] != 1]
    if not_submitted:
        frappe.throw(
            _(
                "The following invoices are not submitted and cannot be exported: {0}"
            ).format(", ".join(not_submitted))
        )

    allowed_statuses = {"Unpaid", "Overdue", "Partly Paid"}
    invalid = [inv["name"] for inv in invoices if inv["status"] not in allowed_statuses]
    if invalid:
        frappe.throw(
            _(
                "The following invoices are not eligible for SEPA export "
                "(must be Unpaid / Overdue / Partly Paid): {0}"
            ).format(", ".join(invalid))
        )

    # All invoices must belong to the same company
    companies = set(inv["company"] for inv in invoices)
    if len(companies) > 1:
        frappe.throw(
            _(
                "All selected invoices must belong to the same company. Found: {0}"
            ).format(", ".join(companies))
        )

    return invoices


@frappe.whitelist()
def validate_supplier_banking_details(supplier_name):
    """
    Validate if supplier has necessary banking details for SEPA export

    Args:
        supplier_name: Name of the supplier

    Returns:
        dict: Status and message
    """
    supplier = frappe.get_doc("Supplier", supplier_name)

    # Check if supplier has a default bank account
    if not supplier.default_bank_account:
        return {
            "valid": False,
            "message": _(
                "Supplier {0} doesn't have a default bank account configured"
            ).format(supplier_name),
        }

    # Check if bank account has necessary details
    try:
        bank_account = frappe.get_doc("Bank Account", supplier.default_bank_account)

        missing_fields = []
        if not bank_account.iban:
            missing_fields.append("IBAN")

        # BIC/SWIFT is optional, not checking for bank_account_no

        if missing_fields:
            return {
                "valid": False,
                "message": _("Bank account {0} is missing required fields: {1}").format(
                    supplier.default_bank_account, ", ".join(missing_fields)
                ),
            }

    except frappe.DoesNotExistError:
        return {
            "valid": False,
            "message": _("Bank account {0} for supplier {1} not found").format(
                supplier.default_bank_account, supplier_name
            ),
        }

    return {"valid": True}
