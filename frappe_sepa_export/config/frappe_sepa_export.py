import frappe
from frappe import _


def get_data():
    return [
        {
            "label": _("SEPA File Export"),
            "items": [
                {
                    "type": "doctype",
                    "name": "SEPA Settings",
                    "description": _("Configure SEPA Settings"),
                }
            ],
        },
        {
            "label": _("Banking"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Bank Account",
                    "description": _("Manage Bank Accounts"),
                }
            ],
        },
        {
            "label": _("Reports"),
            "items": [
                {
                    "type": "report",
                    "name": "Unpaid Supplier Invoices",
                    "doctype": "Purchase Invoice",
                    "is_query_report": True,
                }
            ],
        },
        {
            "label": _("Documentation"),
            "items": [
                {"type": "help", "label": _("SEPA Documentation"), "youtube_id": ""}
            ],
        },
    ]
