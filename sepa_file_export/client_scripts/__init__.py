import frappe


def get_context(context):
    """
    Add JS to client-side Purchase Invoice form
    """
    context.js = frappe.render_template(
        "frappe_sepa_export/client_scripts/purchase_invoice.js", {}
    )
