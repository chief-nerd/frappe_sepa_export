import frappe
from frappe import _
from xml.sax.saxutils import escape
from datetime import datetime


SEPA_NAMESPACES = {
    "pain.001.001.03": "ISO:pain.001.001.03:APC:STUZZA:payments:003",
    "pain.001.001.02": "ISO:pain.001.001.02:APC:STUZZA:payments:002",
}

# ISO 20022 pain.001.001.03 field length limits
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


def _t(value, field):
    """Truncate a value to the ISO 20022 max length for the given field."""
    max_len = _MAX_LEN.get(field)
    if max_len and len(value) > max_len:
        return value[:max_len]
    return value


def _resolve_supplier_bank_account(supplier_name):
    """Resolve the bank account for a supplier.

    Lookup chain:
        1. Supplier.default_bank_account
        2. Bank Account linked via party_type/party

    Returns:
        str or None: Bank Account name, or None if not found
    """
    supplier = frappe.get_doc("Supplier", supplier_name)

    if supplier.default_bank_account:
        return supplier.default_bank_account

    # Fallback: find a Bank Account linked to this Supplier
    linked = frappe.db.get_value(
        "Bank Account",
        {"party_type": "Supplier", "party": supplier_name, "is_company_account": 0},
        "name",
    )
    return linked or None


def _get_supplier_address(supplier_name):
    """Get structured address details for a supplier from the linked Address record.

    Returns:
        dict: {country_code, street, postcode, city}
    """
    address_name = frappe.db.get_value(
        "Dynamic Link",
        {
            "link_doctype": "Supplier",
            "link_name": supplier_name,
            "parenttype": "Address",
        },
        "parent",
    )
    if not address_name:
        return {"country_code": "AT", "street": "", "postcode": "", "city": ""}

    address = frappe.get_doc("Address", address_name)
    country_code = (
        frappe.db.get_value("Country", address.country, "code")
        if address.country
        else "AT"
    )
    country_code = (country_code or "AT").upper()

    street_parts = list(filter(None, [address.address_line1, address.address_line2]))
    return {
        "country_code": country_code,
        "street": ", ".join(street_parts),
        "postcode": address.pincode or "",
        "city": address.city or "",
    }


@frappe.whitelist()
def export_payment_instruction_xml(
    invoice_names,
    execution_date,
    debtor_name,
    debtor_iban,
    debtor_bic,
    debtor_country,
    debtor_street="",
    debtor_postcode="",
    debtor_city="",
    payment_reference=None,
    payment_references=None,
):
    """
    Generate SEPA XML Payment Instruction file (pain.001.001.03) for purchase invoices

    Args:
        invoice_names (str): Comma-separated list of Purchase Invoice names
        execution_date (str): Requested execution date in YYYY-MM-DD format
        debtor_name (str): Name of the debtor (company making the payment)
        debtor_iban (str): IBAN of the debtor's bank account
        debtor_bic (str): BIC/SWIFT code of the debtor's bank
        debtor_country (str): Country code of the debtor (e.g., "AT" for Austria)
        debtor_street (str): Street name of the debtor
        debtor_postcode (str): Postal code of the debtor
        debtor_city (str): City/town name of the debtor

    Returns:
        XML file download response
    """
    if isinstance(invoice_names, str):
        invoice_names = invoice_names.split(",")

    # Fetch invoice details
    invoices = frappe.get_all(
        "Purchase Invoice",
        filters={"name": ["in", invoice_names]},
        fields=[
            "name",
            "outstanding_amount",
            "currency",
            "supplier",
            "supplier_name",
            "posting_date",
            "remarks",
        ],
    )

    if not invoices:
        frappe.throw(_("No invoices found for the given names."))

    # Validate debtor IBAN is present
    if not debtor_iban:
        frappe.throw(
            _(
                "Debtor IBAN is missing. Please configure a default bank account in SEPA Settings."
            )
        )

    # Build per-invoice payment reference map
    import json as _json

    ref_map = {}
    if payment_references:
        if isinstance(payment_references, str):
            ref_map = _json.loads(payment_references)
        elif isinstance(payment_references, dict):
            ref_map = payment_references

    # Fall back to legacy single-reference parameter
    if payment_reference and not ref_map:
        for inv in invoices:
            ref_map[inv["name"]] = payment_reference

    for inv in invoices:
        inv["_payment_reference"] = ref_map.get(inv["name"])

    # Validate all invoices are in EUR
    non_eur = [inv["name"] for inv in invoices if inv["currency"] != "EUR"]
    if non_eur:
        frappe.throw(
            _(
                "SEPA only supports EUR. The following invoices have a different currency: {0}"
            ).format(", ".join(non_eur))
        )

    # Determine SEPA schema namespace from settings (if available)
    company = frappe.db.get_value("Purchase Invoice", invoices[0]["name"], "company")
    schema_version = "pain.001.001.03"
    try:
        sepa_settings = frappe.get_doc("SEPA Settings", company)
        schema_version = sepa_settings.sepa_schema_version or schema_version
    except frappe.DoesNotExistError:
        pass
    namespace = SEPA_NAMESPACES.get(schema_version, SEPA_NAMESPACES["pain.001.001.03"])

    # Header values
    msg_id = datetime.now().strftime("%m%d%H%M") + frappe.generate_hash(length=16)
    pmt_inf_id = msg_id[:16]
    now_iso = datetime.now().isoformat(timespec="seconds")
    nb_of_txs = len(invoices)
    ctrl_sum = sum(float(inv["outstanding_amount"]) for inv in invoices)

    # Build structured debtor address XML (all fields required by schema)
    # PostalAddress6 sequence: StrtNm, BldgNb, PstCd, TwnNm, CtrySubDvsn, Ctry
    debtor_addr_xml = f"""<StrtNm>{escape(_t(debtor_street, "StrtNm"))}</StrtNm>
<PstCd>{escape(_t(debtor_postcode, "PstCd"))}</PstCd>
<TwnNm>{escape(_t(debtor_city, "TwnNm"))}</TwnNm>
<Ctry>{escape(debtor_country)}</Ctry>
"""

    # BIC element – use <Othr><Id>NOTPROVIDED</Id></Othr> when no valid BIC
    if debtor_bic and len(debtor_bic) in (8, 11) and debtor_bic.isalnum():
        debtor_agt_id = f"<BIC>{escape(debtor_bic)}</BIC>"
    else:
        debtor_agt_id = "<Othr><Id>NOTPROVIDED</Id></Othr>"

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="{namespace}" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<CstmrCdtTrfInitn>
<GrpHdr>
<MsgId>{_t(msg_id, "MsgId")}</MsgId>
<CreDtTm>{now_iso}</CreDtTm>
<NbOfTxs>{nb_of_txs}</NbOfTxs>
<CtrlSum>{ctrl_sum:.2f}</CtrlSum>
<InitgPty>
<Nm>{escape(_t(debtor_name, "Nm"))}</Nm>
</InitgPty>
</GrpHdr>
<PmtInf>
<PmtInfId>{_t(pmt_inf_id, "PmtInfId")}</PmtInfId>
<PmtMtd>TRF</PmtMtd>
<BtchBookg>true</BtchBookg>
<PmtTpInf>
<SvcLvl>
<Cd>SEPA</Cd>
</SvcLvl>
</PmtTpInf>
<ReqdExctnDt>{execution_date}</ReqdExctnDt>
<Dbtr>
<Nm>{escape(_t(debtor_name, "Nm"))}</Nm>
<PstlAdr>
{debtor_addr_xml}</PstlAdr>
</Dbtr>
<DbtrAcct>
<Id>
<IBAN>{escape(debtor_iban)}</IBAN>
</Id>
<Ccy>EUR</Ccy>
</DbtrAcct>
<DbtrAgt>
<FinInstnId>
{debtor_agt_id}
</FinInstnId>
</DbtrAgt>
<ChrgBr>SLEV</ChrgBr>
"""

    for idx, inv in enumerate(invoices, 1):
        # Fetch Supplier data
        display_name = inv["supplier_name"] or inv["supplier"]

        # Resolve bank account: default_bank_account > linked Bank Account
        bank_account_name = _resolve_supplier_bank_account(inv["supplier"])
        supplier_iban = ""

        if bank_account_name:
            try:
                bank_account = frappe.get_doc("Bank Account", bank_account_name)
                supplier_iban = bank_account.iban or ""
            except frappe.DoesNotExistError:
                frappe.throw(
                    _(
                        "Bank Account {0} not found for supplier {1}. Please fix the supplier's bank account configuration."
                    ).format(bank_account_name, display_name)
                )
        else:
            frappe.throw(
                _(
                    "No bank account found for supplier {0}. Please set a default bank account or link a Bank Account record to the supplier."
                ).format(display_name)
            )

        if not supplier_iban:
            frappe.throw(
                _(
                    "Supplier {0}: the Bank Account {1} has no IBAN. Please add an IBAN to the bank account record."
                ).format(display_name, bank_account_name)
            )

        # Get country and address from the supplier's linked Address record
        supplier_addr = _get_supplier_address(inv["supplier"])
        supplier_country = supplier_addr["country_code"]

        # Build structured creditor address XML (all fields required by schema)
        # PostalAddress6 sequence: StrtNm, BldgNb, PstCd, TwnNm, CtrySubDvsn, Ctry
        creditor_addr_xml = f"""<StrtNm>{escape(_t(supplier_addr["street"], "StrtNm"))}</StrtNm>
<PstCd>{escape(_t(supplier_addr["postcode"], "PstCd"))}</PstCd>
<TwnNm>{escape(_t(supplier_addr["city"], "TwnNm"))}</TwnNm>
<Ctry>{escape(supplier_country)}</Ctry>
"""

        rmt_info = inv.get("_payment_reference") or inv.get("remarks") or inv["name"]

        xml += f"""
<CdtTrfTxInf>
<PmtId>
<InstrId>{_t(str(idx).zfill(8), "InstrId")}</InstrId>
<EndToEndId>{_t(inv["name"], "EndToEndId")}</EndToEndId>
</PmtId>
<Amt>
<InstdAmt Ccy="EUR">{float(inv["outstanding_amount"]):.2f}</InstdAmt>
</Amt>
<CdtrAgt>
<FinInstnId>
<Othr><Id>NOTPROVIDED</Id></Othr>
</FinInstnId>
</CdtrAgt>
<Cdtr>
<Nm>{escape(_t(inv["supplier_name"] or inv["supplier"], "Nm"))}</Nm>
<PstlAdr>
{creditor_addr_xml}</PstlAdr>
</Cdtr>
<CdtrAcct>
<Id>
<IBAN>{escape(supplier_iban)}</IBAN>
</Id>
</CdtrAcct>
<RmtInf>
<Ustrd>{escape(_t(rmt_info, "Ustrd"))}</Ustrd>
</RmtInf>
</CdtTrfTxInf>
"""

    xml += """
</PmtInf>
</CstmrCdtTrfInitn>
</Document>
"""

    frappe.local.response.filename = (
        f"payment_instruction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
    )
    frappe.local.response.filecontent = xml
    frappe.local.response.type = "download"
