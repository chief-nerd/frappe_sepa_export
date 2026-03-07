import frappe


def after_install():
    """Setup after app installation."""
    frappe.publish_realtime(
        event="msgprint",
        message="SEPA File Export installed. Please configure SEPA Settings for your company.",
        user=frappe.session.user,
    )
