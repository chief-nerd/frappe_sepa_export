import frappe


def after_install():
    """Setup after app installation."""
    create_module_def()
    frappe.publish_realtime(
        event="msgprint",
        message="SEPA File Export installed. Please configure SEPA Settings for your company.",
        user=frappe.session.user,
    )


def create_module_def():
    """Create the Module Def record if it doesn't exist."""
    if not frappe.db.exists("Module Def", "SEPA File Export"):
        module_def = frappe.new_doc("Module Def")
        module_def.module_name = "SEPA File Export"
        module_def.app_name = "frappe_sepa_export"
        module_def.insert(ignore_permissions=True)
        frappe.db.commit()
