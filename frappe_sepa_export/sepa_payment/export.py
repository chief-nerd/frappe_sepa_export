import frappe
from xml.sax.saxutils import escape
from datetime import datetime


@frappe.whitelist()
def export_payment_instruction_xml(
    invoice_names,
    execution_date,
    debtor_name,
    debtor_iban,
    debtor_bic,
    debtor_address,
    debtor_country,
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

    # Header values
    msg_id = datetime.now().strftime("%m%d%H%M") + frappe.generate_hash(length=16)
    pmt_inf_id = msg_id[:16]
    now_iso = datetime.now().isoformat(timespec="seconds")
    nb_of_txs = len(invoices)
    ctrl_sum = sum(float(inv["grand_total"]) for inv in invoices)

    adr_lines = "".join(f"<AdrLine>{escape(line)}</AdrLine>" for line in debtor_address)

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="ISO:pain.001.001.03:APC:STUZZA:payments:003" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
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
        supplier_country = "AT"  # Default country code
        supplier_address = ""
        
        if supplier.default_bank_account:
            try:
                bank_account = frappe.get_doc("Bank Account", supplier.default_bank_account)
                supplier_iban = bank_account.iban or "NOTPROVIDED"
                # BIC is optional, leaving as NOTPROVIDED
                
                # Get supplier address
                if hasattr(bank_account, "address_html") and bank_account.address_html:
                    # Extract address from HTML if available
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(bank_account.address_html, 'html.parser')
                    supplier_address = soup.get_text("\n").strip()
            except frappe.DoesNotExistError:
                frappe.msgprint(f"Bank account {supplier.default_bank_account} not found for supplier {supplier.name}")
        
        # Get country from supplier if available
        if hasattr(supplier, "country") and supplier.country:
            supplier_country = supplier.country
            
        address_lines = "".join(
            f"<AdrLine>{escape(line.strip())}</AdrLine>"
            for line in supplier_address.split("\n")
            if line.strip()
        )
        rmt_info = inv.get("remarks") or inv["name"]

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
