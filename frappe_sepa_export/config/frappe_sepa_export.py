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
    ]
