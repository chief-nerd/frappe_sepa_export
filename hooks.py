app_name = "frappe_sepa_export"
app_title = "SEPA File Export"
app_publisher = "Mimirio"
app_description = "Generate SEPA XML Payment Instruction files for Purchase Invoices"
app_email = "dev@mimirio.com"
app_license = "MIT"

# Document Events
# ---------------
# Hook on document methods and events
doc_events = {
    "Purchase Invoice": {
        "on_submit": "frappe_sepa_export.frappe_sepa_export.utils.update_payment_status"
    }
}

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_js = "/assets/frappe_sepa_export/js/frappe_sepa_export.js"

# include js in doctype views
doctype_js = {"Purchase Invoice": "public/js/purchase_invoice.js"}

# Custom DocTypes
# --------------
# fixtures = ["Custom Field", "Custom Script"]

# DocTypes to expose as API
# ------------------------
# has_permission = {
#     "Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Installation
# ------------
# before_install = "frappe_sepa_export.frappe_sepa_export.install.setup.before_install"
after_install = "frappe_sepa_export.frappe_sepa_export.install.setup.after_install"

# Desk Notifications
# -----------------
# notification_config = "frappe_sepa_export.notifications.get_notification_config"

# Permissions Evaluation
# ---------------
# permission_query_conditions = {
#     "Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
