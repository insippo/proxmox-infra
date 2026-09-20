"""ISO 20022 pain.001.001.03 (SEPA kreeditkorraldus) generaator.

Miks just see fail: pain.001 on ainus makse-ettevalmistuse viis, mis
tootab ILMA panga API-lepinguta ja ILMA PSD2 litsentsita. Fail imporditakse
internetipanka, inimene vaatab ule ja allkirjastab. Seda aktsepteerivad
SEB, Swedbank, LHV ja Coop Pank.

API-tee (SEB XS2A) on sama andmemudeli peal - vt bankprep/seb_xs2a.py.
"""

from __future__ import annotations

import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from decimal import Decimal

from bankprep.models import PaymentBatch

NS = "urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
SCHEMA_LOCATION = f"{NS} pain.001.001.03.xsd"

# Kes kannab pangatasud: SLEV = jagatud (SEPA standard, ainus lubatud).
CHARGE_BEARER = "SLEV"


def _msg_id(prefix: str = "BP") -> str:
    """Unikaalne sonumi ID, max 35 marki."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{prefix}-{stamp}-{uuid.uuid4().hex[:8].upper()}"


def _sub(parent: ET.Element, tag: str, text: str | None = None) -> ET.Element:
    """Lisab elemendi pain.001 nimeruumi. Nimeruum peab olema koigil
    elementidel, mitte ainult juurel - muidu ei leia XSD-valideerija neid."""
    el = ET.SubElement(parent, f"{{{NS}}}{tag}")
    if text is not None:
        el.text = text
    return el


def _agent(parent: ET.Element, tag: str, bic: str | None) -> None:
    """DbtrAgt/CdtrAgt. BIC-i puudumisel NOTPROVIDED (SEPA IBAN-only)."""
    agent = _sub(parent, tag)
    fin = _sub(agent, "FinInstnId")
    if bic:
        _sub(fin, "BIC", bic)
    else:
        othr = _sub(fin, "Othr")
        _sub(othr, "Id", "NOTPROVIDED")


def build_pain001(batch: PaymentBatch, *, message_id: str | None = None) -> ET.ElementTree:
    """Koostab pain.001.001.03 dokumendi maksepakist."""
    msg_id = message_id or batch.message_id or _msg_id()
    if len(msg_id) > 35:
        raise ValueError(f"MsgId on {len(msg_id)} marki, lubatud 35")

    ET.register_namespace("", NS)
    root = ET.Element(f"{{{NS}}}Document", {f"{{{XSI}}}schemaLocation": SCHEMA_LOCATION})
    init = _sub(root, "CstmrCdtTrfInitn")

    # --- Grupi paIs ---
    hdr = _sub(init, "GrpHdr")
    _sub(hdr, "MsgId", msg_id)
    _sub(hdr, "CreDtTm", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"))
    _sub(hdr, "NbOfTxs", str(batch.count))
    _sub(hdr, "CtrlSum", f"{batch.control_sum:.2f}")
    initg = _sub(hdr, "InitgPty")
    _sub(initg, "Nm", batch.debtor.name)

    # --- Makseinfo plokk (uks maksja + uks kuupaev) ---
    pmt = _sub(init, "PmtInf")
    _sub(pmt, "PmtInfId", msg_id)
    _sub(pmt, "PmtMtd", "TRF")
    _sub(pmt, "BtchBookg", "true" if batch.batch_booking else "false")
    _sub(pmt, "NbOfTxs", str(batch.count))
    _sub(pmt, "CtrlSum", f"{batch.control_sum:.2f}")

    tp = _sub(pmt, "PmtTpInf")
    svc = _sub(tp, "SvcLvl")
    _sub(svc, "Cd", "SEPA")

    _sub(pmt, "ReqdExctnDt", batch.requested_execution_date.isoformat())

    dbtr = _sub(pmt, "Dbtr")
    _sub(dbtr, "Nm", batch.debtor.name)
    dbtr_acct = _sub(pmt, "DbtrAcct")
    _sub(_sub(dbtr_acct, "Id"), "IBAN", batch.debtor.iban)
    _agent(pmt, "DbtrAgt", batch.debtor.bic)
    _sub(pmt, "ChrgBr", CHARGE_BEARER)

    # --- Uksiktehingud ---
    for payment in batch.payments:
        tx = _sub(pmt, "CdtTrfTxInf")
        pmt_id = _sub(tx, "PmtId")
        _sub(pmt_id, "EndToEndId", payment.end_to_end_id)

        amt = _sub(tx, "Amt")
        _sub(amt, "InstdAmt", payment.amount_str).set("Ccy", payment.currency)

        if payment.creditor.bic:
            _agent(tx, "CdtrAgt", payment.creditor.bic)

        cdtr = _sub(tx, "Cdtr")
        _sub(cdtr, "Nm", payment.creditor.name)
        cdtr_acct = _sub(tx, "CdtrAcct")
        _sub(_sub(cdtr_acct, "Id"), "IBAN", payment.creditor.iban)

        if payment.reference or payment.remittance:
            rmt = _sub(tx, "RmtInf")
            if payment.reference:
                strd = _sub(rmt, "Strd")
                ref_inf = _sub(strd, "CdtrRefInf")
                ref_tp = _sub(ref_inf, "Tp")
                cd_orprtry = _sub(ref_tp, "CdOrPrtry")
                _sub(cd_orprtry, "Cd", "SCOR")
                _sub(ref_inf, "Ref", payment.reference)
            else:
                _sub(rmt, "Ustrd", payment.remittance)

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    return tree


def to_xml(batch: PaymentBatch, *, message_id: str | None = None) -> bytes:
    """pain.001 XML baitidena (UTF-8, XML-deklaratsiooniga)."""
    tree = build_pain001(batch, message_id=message_id)
    import io

    buf = io.BytesIO()
    tree.write(buf, encoding="UTF-8", xml_declaration=True)
    return buf.getvalue()


def write_file(batch: PaymentBatch, path: str, *, message_id: str | None = None) -> str:
    """Kirjutab XML-i faili. Tagastab MsgId, et seda saaks logida."""
    tree = build_pain001(batch, message_id=message_id)
    root = tree.getroot()
    msg_id_el = root.find(f".//{{{NS}}}MsgId")
    tree.write(path, encoding="UTF-8", xml_declaration=True)
    return msg_id_el.text if msg_id_el is not None else ""


def checksum_report(batch: PaymentBatch) -> dict[str, object]:
    """Numbrid, mida inimene enne allkirjastamist pangas korvutab."""
    return {
        "maksete_arv": batch.count,
        "kogusumma": f"{batch.control_sum:.2f}",
        "valuuta": "EUR",
        "maksja_iban": batch.debtor.iban,
        "kuupaev": batch.requested_execution_date.isoformat(),
        "suurim_makse": f"{max((p.amount for p in batch.payments), default=Decimal('0')):.2f}",
        "korduvad_e2e_id": batch.duplicate_end_to_end_ids(),
    }
