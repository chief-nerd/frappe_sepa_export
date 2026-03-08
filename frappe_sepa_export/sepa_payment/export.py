"""SEPA XML generation — pain.001.001.03 (STUZZA Austrian variant).

This module is responsible solely for building the XML document.
All data-resolution helpers live in :mod:`frappe_sepa_export.utils`.
"""

import json

import frappe
from frappe import _
from datetime import datetime
from xml.sax.saxutils import escape

from frappe_sepa_export.utils import (
    _t,
    _strip_iban,
    _get_supplier_address,
    _resolve_supplier_bank_account,
    _get_bank_details,
)

SEPA_NAMESPACES = {
    "pain.001.001.03": "ISO:pain.001.001.03:APC:STUZZA:payments:003",
    "pain.001.001.02": "ISO:pain.001.001.02:APC:STUZZA:payments:002",
}


# ────────────────────────────────────────────────────────────────────
# XML formatting helpers
# ────────────────────────────────────────────────────────────────────


def _bic_xml(bic):
    """Return the ``<FinInstnId>`` inner XML for a BIC value.

    Uses ``<BIC>`` when the value is a valid 8- or 11-char alphanumeric
    code, otherwise falls back to ``<Othr><Id>NOTPROVIDED</Id></Othr>``.
    """
    bic = (bic or "").strip()
    if bic and len(bic) in (8, 11) and bic.isalnum():
        return f"<BIC>{escape(bic)}</BIC>"
    return "<Othr><Id>NOTPROVIDED</Id></Othr>"


def _addr_xml(street, postcode, city, country):
    """Build the ``<PstlAdr>`` child elements (PostalAddress6 sequence).

    XSD element order: StrtNm, BldgNb, PstCd, TwnNm, CtrySubDvsn, Ctry.
    """
    return (
        f"<StrtNm>{escape(_t(street, 'StrtNm'))}</StrtNm>\n"
        f"<PstCd>{escape(_t(postcode, 'PstCd'))}</PstCd>\n"
        f"<TwnNm>{escape(_t(city, 'TwnNm'))}</TwnNm>\n"
        f"<Ctry>{escape(country)}</Ctry>\n"
    )


# ────────────────────────────────────────────────────────────────────
# Main export endpoint
# ────────────────────────────────────────────────────────────────────


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
    payment_references=None,
):
    """Generate a SEPA XML Payment Instruction file (pain.001.001.03).

    Args:
        invoice_names:       Comma-separated Purchase Invoice names.
        execution_date:      Requested execution date (YYYY-MM-DD).
        debtor_name:         Name of the debtor (company).
        debtor_iban:         IBAN of the debtor's bank account.
        debtor_bic:          BIC/SWIFT of the debtor's bank.
        debtor_country:      ISO country code of the debtor.
        debtor_street:       Street of the debtor.
        debtor_postcode:     Postal code of the debtor.
        debtor_city:         City/town of the debtor.
        payment_references:  JSON-encoded ``{invoice_name: reference}`` map.

    Returns:
        dict: ``{filename, filecontent}`` — XML as a string.
    """
    # ── Parse inputs ──────────────────────────────────────────────
    if isinstance(invoice_names, str):
        invoice_names = [n.strip() for n in invoice_names.split(",") if n.strip()]

    ref_map = {}
    if payment_references:
        if isinstance(payment_references, str):
            ref_map = json.loads(payment_references)
        elif isinstance(payment_references, dict):
            ref_map = payment_references

    # ── Fetch invoices ────────────────────────────────────────────
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

    # Attach per-invoice payment reference
    for inv in invoices:
        inv["_payment_reference"] = ref_map.get(inv["name"])

    # ── Validate ──────────────────────────────────────────────────
    debtor_iban = _strip_iban(debtor_iban)
    if not debtor_iban:
        frappe.throw(
            _(
                "Debtor IBAN is missing. "
                "Please configure a default bank account in SEPA Settings."
            )
        )

    non_eur = [inv["name"] for inv in invoices if inv["currency"] != "EUR"]
    if non_eur:
        frappe.throw(
            _(
                "SEPA only supports EUR. "
                "The following invoices have a different currency: {0}"
            ).format(", ".join(non_eur))
        )

    # ── SEPA schema ───────────────────────────────────────────────
    company = frappe.db.get_value("Purchase Invoice", invoices[0]["name"], "company")
    schema_version = "pain.001.001.03"
    try:
        sepa_settings = frappe.get_doc("SEPA Settings", company)
        schema_version = sepa_settings.sepa_schema_version or schema_version
    except frappe.DoesNotExistError:
        pass
    namespace = SEPA_NAMESPACES.get(schema_version, SEPA_NAMESPACES["pain.001.001.03"])

    # ── Header values ─────────────────────────────────────────────
    msg_id = datetime.now().strftime("%m%d%H%M") + frappe.generate_hash(length=16)
    pmt_inf_id = msg_id[:16]
    now_iso = datetime.now().isoformat(timespec="seconds")
    nb_of_txs = len(invoices)
    ctrl_sum = sum(float(inv["outstanding_amount"]) for inv in invoices)

    # ── Build XML ─────────────────────────────────────────────────
    debtor_addr = _addr_xml(debtor_street, debtor_postcode, debtor_city, debtor_country)
    debtor_agt = _bic_xml(debtor_bic)

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
{debtor_addr}</PstlAdr>
</Dbtr>
<DbtrAcct>
<Id>
<IBAN>{escape(debtor_iban)}</IBAN>
</Id>
<Ccy>EUR</Ccy>
</DbtrAcct>
<DbtrAgt>
<FinInstnId>
{debtor_agt}
</FinInstnId>
</DbtrAgt>
<ChrgBr>SLEV</ChrgBr>
"""

    for idx, inv in enumerate(invoices, 1):
        display = inv["supplier_name"] or inv["supplier"]

        # ── Resolve supplier bank details ─────────────────────────
        ba_name = _resolve_supplier_bank_account(inv["supplier"])
        if not ba_name:
            frappe.throw(
                _(
                    "No bank account found for supplier {0}. "
                    "Please set a default bank account or link a "
                    "Bank Account record to the supplier."
                ).format(display)
            )

        details = _get_bank_details(ba_name)
        supplier_iban = details["iban"]
        supplier_bic = details["bic"]

        if not supplier_iban:
            frappe.throw(
                _(
                    "Supplier {0}: Bank Account {1} has no IBAN. "
                    "Please add an IBAN to the bank account record."
                ).format(display, ba_name)
            )

        # ── Supplier address ──────────────────────────────────────
        supplier_addr = _get_supplier_address(inv["supplier"])

        creditor_addr = _addr_xml(
            supplier_addr["street"],
            supplier_addr["postcode"],
            supplier_addr["city"],
            supplier_addr["country_code"],
        )
        creditor_agt = _bic_xml(supplier_bic)

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
{creditor_agt}
</FinInstnId>
</CdtrAgt>
<Cdtr>
<Nm>{escape(_t(display, "Nm"))}</Nm>
<PstlAdr>
{creditor_addr}</PstlAdr>
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

    return {
        "filename": f"payment_instruction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml",
        "filecontent": xml,
    }
