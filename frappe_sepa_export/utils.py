"""Shared helpers and whitelisted API endpoints for SEPA File Export.

Every data-resolution helper used by both ``utils`` (validation / UI)
and ``export`` (XML generation) is defined here so that there is a
single source of truth and a one-way dependency:
``export.py`` → ``utils.py``.
"""

import json

import frappe
from frappe import _


# ────────────────────────────────────────────────────────────────────
# ISO 20022 pain.001.001.03 — field-length limits
# ────────────────────────────────────────────────────────────────────

_MAX_LEN = {
    "Nm": 70,
    "StrtNm": 70,
    "PstCd": 16,
    "TwnNm": 35,
    "EndToEndId": 35,
    "InstrId": 35,
    "MsgId": 35,
    "PmtInfId": 35,
    "Ustrd": 140,
}


# ────────────────────────────────────────────────────────────────────
# Low-level helpers
# ────────────────────────────────────────────────────────────────────


def _t(value, field):
    """Truncate *value* to the ISO 20022 max length for *field*.

    Returns an empty string when *value* is ``None`` or empty.
    """
    if not value:
        return ""
    value = str(value)
    max_len = _MAX_LEN.get(field)
    if max_len and len(value) > max_len:
        return value[:max_len]
    return value


def _strip_iban(iban):
    """Remove spaces and normalise an IBAN for XML output."""
    if not iban:
        return ""
    return iban.replace(" ", "").strip().upper()


# ── Address resolution ─────────────────────────────────────────────


def _get_entity_address(link_doctype, link_name):
    """Resolve a structured postal address via *Dynamic Link → Address*.

    Works for any entity type (Company, Supplier, …) that links to
    Address through a Dynamic Link child table.

    Returns:
        dict: ``{country_code, street, postcode, city}``
    """
    address_name = frappe.db.get_value(
        "Dynamic Link",
        {"link_doctype": link_doctype, "link_name": link_name, "parenttype": "Address"},
        "parent",
    )
    if not address_name:
        return {"country_code": "AT", "street": "", "postcode": "", "city": ""}

    addr = frappe.db.get_value(
        "Address",
        address_name,
        ["address_line1", "address_line2", "pincode", "city", "country"],
        as_dict=True,
    )
    if not addr:
        return {"country_code": "AT", "street": "", "postcode": "", "city": ""}

    country_code = "AT"
    if addr.country:
        country_code = (
            frappe.db.get_value("Country", addr.country, "code") or "AT"
        ).upper()

    street_parts = list(filter(None, [addr.address_line1, addr.address_line2]))
    return {
        "country_code": country_code,
        "street": ", ".join(street_parts),
        "postcode": addr.pincode or "",
        "city": addr.city or "",
    }


def _get_company_address(company_name):
    """Convenience: postal address for a Company."""
    return _get_entity_address("Company", company_name)


def _get_supplier_address(supplier_name):
    """Convenience: postal address for a Supplier."""
    return _get_entity_address("Supplier", supplier_name)


# ── Bank-account resolution ───────────────────────────────────────


def _resolve_supplier_bank_account(supplier_name):
    """Resolve the Bank Account *name* for a Supplier.

    Lookup chain:
        1. ``Supplier.default_bank_account``
        2. A ``Bank Account`` record linked via ``party_type`` / ``party``

    Returns:
        str | None
    """
    default_ba = frappe.db.get_value("Supplier", supplier_name, "default_bank_account")
    if default_ba:
        return default_ba

    linked = frappe.db.get_value(
        "Bank Account",
        {"party_type": "Supplier", "party": supplier_name, "disabled": 0},
        "name",
    )
    return linked or None


def _get_bank_details(bank_account_name):
    """Return the IBAN (space-stripped) and BIC for a Bank Account.

    The BIC is resolved from the linked **Bank** record's
    ``swift_number`` field — *not* ``branch_code``.

    Returns:
        dict: ``{iban, bic}``
    """
    if not bank_account_name:
        return {"iban": "", "bic": ""}

    ba = frappe.db.get_value(
        "Bank Account",
        bank_account_name,
        ["iban", "bank"],
        as_dict=True,
    )
    if not ba:
        return {"iban": "", "bic": ""}

    iban = _strip_iban(ba.get("iban"))

    bic = ""
    if ba.get("bank"):
        bic = (frappe.db.get_value("Bank", ba["bank"], "swift_number") or "").strip()

    return {"iban": iban, "bic": bic}


# ────────────────────────────────────────────────────────────────────
# Whitelisted API endpoints
# ────────────────────────────────────────────────────────────────────


@frappe.whitelist()
def get_debtor_info(company):
    """Fetch debtor information for SEPA export.

    Bank-account resolution chain:
        1. SEPA Settings → ``default_bank_account``
        2. Company → ``default_bank_account``

    Returns:
        dict: debtor_name, debtor_iban, debtor_bic, debtor_country,
              debtor_street, debtor_postcode, debtor_city
    """
    if not frappe.db.exists("SEPA Settings", company):
        frappe.throw(
            _(
                "No SEPA Settings found for company {0}. Please create one first."
            ).format(company)
        )

    sepa_settings = frappe.get_doc("SEPA Settings", company)

    result = {
        "debtor_name": sepa_settings.default_debtor_name or company,
        "debtor_country": sepa_settings.default_country_code or "AT",
        "debtor_iban": "",
        "debtor_bic": "",
        "debtor_street": "",
        "debtor_postcode": "",
        "debtor_city": "",
    }

    # Resolve bank account: SEPA Settings → Company default
    bank_account_name = sepa_settings.default_bank_account
    if not bank_account_name:
        bank_account_name = frappe.db.get_value(
            "Company", company, "default_bank_account"
        )

    if bank_account_name:
        details = _get_bank_details(bank_account_name)
        if details["iban"]:
            result["debtor_iban"] = details["iban"]
            result["debtor_bic"] = details["bic"]
        else:
            frappe.msgprint(
                _(
                    "Bank Account {0} has no IBAN. Please update the bank account."
                ).format(bank_account_name),
                indicator="orange",
                alert=True,
            )
    else:
        frappe.msgprint(
            _(
                "No bank account found for {0}. "
                "Please set one in SEPA Settings or in the Company record."
            ).format(company),
            indicator="orange",
            alert=True,
        )

    addr = _get_company_address(company)
    result["debtor_street"] = addr["street"]
    result["debtor_postcode"] = addr["postcode"]
    result["debtor_city"] = addr["city"]

    return result


@frappe.whitelist()
def validate_sepa_export(invoice_names, company):
    """Pre-flight validation for SEPA export.

    Checks that the debtor (company) and all creditor (supplier)
    addresses, bank accounts and IBANs are present.

    Returns:
        dict: ``{valid: bool, warnings: list[str]}``
    """
    if isinstance(invoice_names, str):
        try:
            invoice_names = json.loads(invoice_names)
        except (ValueError, TypeError):
            invoice_names = [n.strip() for n in invoice_names.split(",") if n.strip()]

    warnings = []

    # ── Debtor (company) checks ──
    addr = _get_company_address(company)
    missing = []
    if not addr["street"]:
        missing.append(_("Street"))
    if not addr["postcode"]:
        missing.append(_("Postcode"))
    if not addr["city"]:
        missing.append(_("City"))
    if missing:
        warnings.append(
            _("Company {0} address is missing: {1}").format(company, ", ".join(missing))
        )

    # ── Creditor (supplier) checks ──
    invoices = frappe.get_all(
        "Purchase Invoice",
        filters={"name": ["in", invoice_names]},
        fields=["name", "supplier", "supplier_name"],
    )

    checked_suppliers = set()
    for inv in invoices:
        if inv["supplier"] in checked_suppliers:
            continue
        checked_suppliers.add(inv["supplier"])

        display = inv["supplier_name"] or inv["supplier"]

        # Bank account & IBAN
        ba_name = _resolve_supplier_bank_account(inv["supplier"])
        if not ba_name:
            warnings.append(
                _(
                    "Supplier {0} has no bank account. "
                    "Set a default bank account or link a Bank Account record."
                ).format(display)
            )
        else:
            details = _get_bank_details(ba_name)
            if not details["iban"]:
                warnings.append(
                    _("Supplier {0}: Bank Account {1} has no IBAN.").format(
                        display, ba_name
                    )
                )

        # Address
        supplier_addr = _get_supplier_address(inv["supplier"])
        missing = []
        if not supplier_addr["street"]:
            missing.append(_("Street"))
        if not supplier_addr["postcode"]:
            missing.append(_("Postcode"))
        if not supplier_addr["city"]:
            missing.append(_("City"))
        if missing:
            warnings.append(
                _("Supplier {0} address is missing: {1}").format(
                    display, ", ".join(missing)
                )
            )

    return {"valid": len(warnings) == 0, "warnings": warnings}


@frappe.whitelist()
def get_bulk_invoice_details(invoice_names):
    """Return details for a list of Purchase Invoices for the review table.

    Args:
        invoice_names: JSON-encoded list of Purchase Invoice names

    Returns:
        list[dict]
    """
    if isinstance(invoice_names, str):
        invoice_names = json.loads(invoice_names)

    if not invoice_names:
        return []

    invoices = frappe.get_all(
        "Purchase Invoice",
        filters={"name": ["in", invoice_names]},
        fields=[
            "name",
            "supplier",
            "supplier_name",
            "bill_no",
            "outstanding_amount",
            "currency",
            "status",
            "company",
            "posting_date",
            "docstatus",
        ],
        order_by="posting_date asc",
    )

    not_submitted = [inv["name"] for inv in invoices if inv["docstatus"] != 1]
    if not_submitted:
        frappe.throw(
            _(
                "The following invoices are not submitted and cannot be exported: {0}"
            ).format(", ".join(not_submitted))
        )

    allowed = {"Unpaid", "Overdue", "Partly Paid"}
    invalid = [inv["name"] for inv in invoices if inv["status"] not in allowed]
    if invalid:
        frappe.throw(
            _(
                "The following invoices are not eligible for SEPA export "
                "(must be Unpaid / Overdue / Partly Paid): {0}"
            ).format(", ".join(invalid))
        )

    companies = {inv["company"] for inv in invoices}
    if len(companies) > 1:
        frappe.throw(
            _(
                "All selected invoices must belong to the same company. Found: {0}"
            ).format(", ".join(companies))
        )

    return invoices


@frappe.whitelist()
def get_open_invoices(company):
    """Return submitted, open Purchase Invoices for the given company.

    Each row is enriched with ``supplier_iban`` resolved via
    :func:`_resolve_supplier_bank_account` / :func:`_get_bank_details`.
    """
    invoices = frappe.get_all(
        "Purchase Invoice",
        filters={
            "company": company,
            "docstatus": 1,
            "status": ["in", ["Unpaid", "Overdue", "Partly Paid"]],
        },
        fields=[
            "name",
            "supplier",
            "supplier_name",
            "bill_no",
            "outstanding_amount",
            "currency",
            "status",
            "company",
            "posting_date",
        ],
        order_by="posting_date asc",
    )

    # Enrich with supplier IBAN (cached per supplier to avoid repeated queries)
    iban_cache = {}
    for inv in invoices:
        supplier = inv["supplier"]
        if supplier not in iban_cache:
            ba_name = _resolve_supplier_bank_account(supplier)
            details = _get_bank_details(ba_name) if ba_name else {"iban": "", "bic": ""}
            iban_cache[supplier] = details["iban"]
        inv["supplier_iban"] = iban_cache[supplier]

    return invoices
