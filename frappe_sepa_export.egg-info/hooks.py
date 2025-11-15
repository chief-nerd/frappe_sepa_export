# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "frappe_sepa_export"
app_title = "SEPA File Export"
app_publisher = "Mimirio"
app_description = "Generate SEPA XML Payment Instruction files for Purchase Invoices"
app_icon = "octicon octicon-file-binary"
app_color = "#2b9144"
app_email = "dev@mimirio.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_js = "/assets/frappe_sepa_export/js/frappe_sepa_export.min.js"

# include js, css files in header of web template
# web_include_css = "/assets/frappe_sepa_export/css/frappe_sepa_export.css"
# web_include_js = "/assets/frappe_sepa_export/js/frappe_sepa_export.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "frappe_sepa_export/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {"Purchase Invoice": "public/js/purchase_invoice.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# "Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------
# before_install = "frappe_sepa_export.frappe_sepa_export.install.setup.before_install"
after_install = "frappe_sepa_export.frappe_sepa_export.install.setup.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "frappe_sepa_export.notifications.get_notification_config"

# Permissions evaluation
# ---------------------
# Permission evaluation
# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Purchase Invoice": {
        "on_submit": "frappe_sepa_export.frappe_sepa_export.utils.update_payment_status"
    }
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"frappe_sepa_export.tasks.all"
# 	],
# 	"daily": [
# 		"frappe_sepa_export.tasks.daily"
# 	],
# 	"hourly": [
# 		"frappe_sepa_export.tasks.hourly"
# 	],
# 	"weekly": [
# 		"frappe_sepa_export.tasks.weekly"
# 	],
# 	"monthly": [
# 		"frappe_sepa_export.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "frappe_sepa_export.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "frappe_sepa_export.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "frappe_sepa_export.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"frappe_sepa_export.auth.validate"
# ]
