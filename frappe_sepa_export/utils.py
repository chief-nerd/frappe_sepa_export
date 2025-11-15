import frappe
from frappe import _


def update_payment_status(doc, method):
    """
    Update payment status when Purchase Invoice is submitted

    Args:
        doc: Purchase Invoice document
        method: Trigger method
    """
    # Example of a function that could be triggered on Invoice submission
    # You might want to set a custom field on the Purchase Invoice
    # to indicate it's ready for SEPA export
    pass


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
            "message": _("Supplier {0} doesn't have a default bank account configured").format(
                supplier_name
            ),
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
