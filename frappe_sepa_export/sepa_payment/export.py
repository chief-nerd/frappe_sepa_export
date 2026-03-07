import frappe
from frappe import _
from xml.sax.saxutils import escape
from datetime import datetime


SEPA_NAMESPACES = {
    "pain.001.001.03": "ISO:pain.001.001.03:APC:STUZZA:payments:003",
    "pain.001.001.02": "ISO:pain.001.001.02:APC:STUZZA:payments:002",
}


def _get_supplier_address(supplier_name):
    """Get address details for a supplier from the linked Address record.

    Returns:
        tuple: (country_code, address_lines list)
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
        return "AT", []

    address = frappe.get_doc("Address", address_name)
    country_code = (
        frappe.db.get_value("Country", address.country, "code")
        if address.country
        else "AT"
    )
    country_code = (country_code or "AT").upper()

    lines = []
    if address.address_line1:
        lines.append(address.address_line1)
    if address.address_line2:
        lines.append(address.address_line2)
    city_line = " ".join(filter(None, [address.pincode, address.city]))
    if city_line:
        lines.append(city_line)
    return country_code, lines


@frappe.whitelist()
def export_payment_instruction_xml(
    invoice_names,
    execution_date,
    debtor_name,
    debtor_iban,
    debtor_bic,
    debtor_address,
    debtor_country,
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
        debtor_address (list): List of address lines for the debtor
        debtor_country (str): Country code of the debtor (e.g., "AT" for Austria)

    Returns:
        XML file download response
    """
    if isinstance(invoice_names, str):
        invoice_names = invoice_names.split(",")

    if isinstance(debtor_address, str):
        debtor_address = debtor_address.split("\n")

    # Fetch invoice details
    invoices = frappe.get_all(
        "Purchase Invoice",
        filters={"name": ["in", invoice_names]},
        fields=[
            "name",
            "grand_total",
            "currency",
            "supplier",
            "supplier_name",
            "posting_date",
            "remarks",
        ],
    )

    if not invoices:
        frappe.throw(_("No invoices found for the given names."))

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
    ctrl_sum = sum(float(inv["grand_total"]) for inv in invoices)

    adr_lines = "".join(
        f"<AdrLine>{escape(line)}</AdrLine>" for line in debtor_address if line.strip()
    )

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="{namespace}" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<CstmrCdtTrfInitn>
<GrpHdr>
<MsgId>{msg_id}</MsgId>
<CreDtTm>{now_iso}</CreDtTm>
<NbOfTxs>{nb_of_txs}</NbOfTxs>
<CtrlSum>{ctrl_sum:.2f}</CtrlSum>
<InitgPty>
<Nm>{escape(debtor_name)}</Nm>
</InitgPty>
</GrpHdr>
<PmtInf>
<PmtInfId>{pmt_inf_id}</PmtInfId>
<PmtMtd>TRF</PmtMtd>
<BtchBookg>true</BtchBookg>
<PmtTpInf>
<SvcLvl>
<Cd>SEPA</Cd>
</SvcLvl>
</PmtTpInf>
<ReqdExctnDt>{execution_date}</ReqdExctnDt>
<Dbtr>
<Nm>{escape(debtor_name)}</Nm>
<PstlAdr>
<Ctry>{escape(debtor_country)}</Ctry>
{adr_lines}
</PstlAdr>
</Dbtr>
<DbtrAcct>
<Id>
<IBAN>{escape(debtor_iban)}</IBAN>
</Id>
<Ccy>EUR</Ccy>
</DbtrAcct>
<DbtrAgt>
<FinInstnId>
<BIC>{escape(debtor_bic) if debtor_bic else "NOTPROVIDED"}</BIC>
</FinInstnId>
</DbtrAgt>
<ChrgBr>SLEV</ChrgBr>
"""

    for idx, inv in enumerate(invoices, 1):
        # Fetch Supplier data
        supplier = frappe.get_doc("Supplier", inv["supplier"])

        # Get bank account info from the Supplier's default bank account
        supplier_iban = "NOTPROVIDED"

        if supplier.default_bank_account:
            try:
                bank_account = frappe.get_doc(
                    "Bank Account", supplier.default_bank_account
                )
                supplier_iban = bank_account.iban or "NOTPROVIDED"
            except frappe.DoesNotExistError:
                frappe.throw(
                    _("Bank account {0} not found for supplier {1}").format(
                        supplier.default_bank_account, supplier.name
                    )
                )
        else:
            frappe.throw(
                _(
                    "Supplier {0} does not have a default bank account configured."
                ).format(inv["supplier_name"] or inv["supplier"])
            )

        # Get country and address from the supplier's linked Address record
        supplier_country, supplier_addr_lines = _get_supplier_address(inv["supplier"])

        address_lines = "".join(
            f"<AdrLine>{escape(line.strip())}</AdrLine>"
            for line in supplier_addr_lines
            if line.strip()
        )
        rmt_info = inv.get("_payment_reference") or inv.get("remarks") or inv["name"]

        xml += f"""
<CdtTrfTxInf>
<PmtId>
<InstrId>{str(idx).zfill(8)}</InstrId>
<EndToEndId>{inv["name"]}</EndToEndId>
</PmtId>
<Amt>
<InstdAmt Ccy="EUR">{float(inv["grand_total"]):.2f}</InstdAmt>
</Amt>
<CdtrAgt>
<FinInstnId>
<BIC>NOTPROVIDED</BIC>
</FinInstnId>
</CdtrAgt>
<Cdtr>
<Nm>{escape(inv["supplier_name"] or inv["supplier"])}</Nm>
<PstlAdr>
<Ctry>{escape(supplier_country)}</Ctry>
{address_lines}
</PstlAdr>
</Cdtr>
<CdtrAcct>
<Id>
<IBAN>{escape(supplier_iban)}</IBAN>
</Id>
</CdtrAcct>
<RmtInf>
<Ustrd>{escape(rmt_info)}</Ustrd>
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
