"""bankprep testid.

Jooksuta repo juurest:
    python3 -m unittest discover -s payments/tests -t payments
"""

from __future__ import annotations

import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal
from pathlib import Path

from bankprep.batch import BatchError, load_batch
from bankprep.iban import IbanError, format_iban, validate_bic, validate_iban
from bankprep.models import (
    Party,
    Payment,
    PaymentBatch,
    ValidationError,
    parse_amount,
    to_sepa_charset,
)
from bankprep.pain001 import NS, checksum_report, to_xml
from bankprep.reference import (
    ReferenceError,
    is_valid_et_reference,
    is_valid_rf_reference,
    make_et_reference,
    make_rf_reference,
    validate_reference,
)
from bankprep.seb_xs2a import bulk_body, classify_status, payment_body

DEBTOR_IBAN = "EE382200221020145685"
CREDITOR_IBAN = "EE471000001020145685"
CREDITOR_IBAN_2 = "EE741010027141501000"


def debtor() -> Party:
    return Party("Soetuppa OU", DEBTOR_IBAN, bic="EEUHEE2X")


def payment(**kwargs) -> Payment:
    defaults = dict(
        creditor=Party("Tarnija AS", CREDITOR_IBAN),
        amount="19.90",
        remittance="Arve 1",
    )
    defaults.update(kwargs)
    return Payment(**defaults)


class TestIban(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate_iban("ee38 2200 2210 2014 5685"), DEBTOR_IBAN)

    def test_bad_checksum(self):
        with self.assertRaises(IbanError):
            validate_iban("EE382200221020145686")

    def test_wrong_length_for_country(self):
        with self.assertRaises(IbanError):
            validate_iban("EE3822002210201456")

    def test_non_sepa_rejected_by_default(self):
        with self.assertRaises(IbanError):
            validate_iban("TR330006100519786457841326")

    def test_format(self):
        self.assertEqual(format_iban(DEBTOR_IBAN), "EE38 2200 2210 2014 5685")

    def test_bic(self):
        self.assertEqual(validate_bic("eeuhee2x"), "EEUHEE2X")
        self.assertIsNone(validate_bic(""))
        with self.assertRaises(IbanError):
            validate_bic("XX1")


class TestReference(unittest.TestCase):
    def test_et_check_digit(self):
        self.assertEqual(make_et_reference("12345"), "123453")
        self.assertTrue(is_valid_et_reference("123453"))
        self.assertFalse(is_valid_et_reference("123455"))

    def test_rf_roundtrip(self):
        ref = make_rf_reference("539007547034")
        self.assertEqual(ref, "RF18539007547034")
        self.assertTrue(is_valid_rf_reference(ref))
        self.assertFalse(is_valid_rf_reference("RF19539007547034"))

    def test_validate(self):
        self.assertEqual(validate_reference("RF18 5390 0754 7034"), "RF18539007547034")
        self.assertIsNone(validate_reference(None))
        with self.assertRaises(ReferenceError):
            validate_reference("123455")


class TestAmounts(unittest.TestCase):
    def test_comma_decimal(self):
        self.assertEqual(parse_amount("19,90"), Decimal("19.90"))

    def test_float_rejected(self):
        with self.assertRaises(ValidationError):
            parse_amount(19.90)

    def test_three_decimals_rejected(self):
        with self.assertRaises(ValidationError):
            parse_amount("19.905")

    def test_zero_rejected(self):
        with self.assertRaises(ValidationError):
            parse_amount("0.00")


class TestCharset(unittest.TestCase):
    def test_estonian_letters(self):
        self.assertEqual(to_sepa_charset("Müügitöö õhtul"), "Muugitoo ohtul")

    def test_ampersand_and_euro(self):
        self.assertEqual(to_sepa_charset("Arve & 5€"), "Arve + 5EUR")


class TestPayment(unittest.TestCase):
    def test_reference_wins_over_remittance(self):
        p = payment(reference="123453", remittance="Vaba tekst")
        self.assertEqual(p.reference, "123453")
        self.assertEqual(p.remittance, "")

    def test_long_remittance_rejected(self):
        with self.assertRaises(ValidationError):
            payment(remittance="x" * 141)

    def test_non_eur_rejected(self):
        with self.assertRaises(ValidationError):
            payment(currency="USD")

    def test_same_account_rejected(self):
        with self.assertRaises(ValidationError):
            PaymentBatch(
                debtor=debtor(),
                payments=[payment(creditor=Party("Ise", DEBTOR_IBAN))],
            )

    def test_duplicate_e2e_detected(self):
        batch = PaymentBatch(
            debtor=debtor(),
            payments=[
                payment(end_to_end_id="ARVE-1"),
                payment(creditor=Party("Teine", CREDITOR_IBAN_2), end_to_end_id="ARVE-1"),
            ],
        )
        self.assertEqual(batch.duplicate_end_to_end_ids(), ["ARVE-1"])


class TestPain001(unittest.TestCase):
    def setUp(self):
        self.batch = PaymentBatch(
            debtor=debtor(),
            payments=[
                payment(amount="1250.00", reference="123453", end_to_end_id="ARVE-1"),
                payment(
                    creditor=Party("Victron Energy B.V.", "NL91ABNA0417164300", bic="ABNANL2A"),
                    amount="99.95",
                    remittance="Multiplus II",
                    end_to_end_id="ARVE-2",
                ),
            ],
            requested_execution_date=date(2026, 9, 25),
        )
        self.root = ET.fromstring(to_xml(self.batch))

    def _text(self, path: str) -> str:
        el = self.root.find(path.replace("/", f"/{{{NS}}}").lstrip("."))
        return el.text if el is not None else ""

    def test_every_element_namespaced(self):
        self.assertTrue(all(e.tag.startswith(f"{{{NS}}}") for e in self.root.iter()))

    def test_control_sum_matches(self):
        sums = [e.text for e in self.root.iter(f"{{{NS}}}CtrlSum")]
        self.assertEqual(sums, ["1349.95", "1349.95"])

    def test_transaction_count(self):
        counts = [e.text for e in self.root.iter(f"{{{NS}}}NbOfTxs")]
        self.assertEqual(counts, ["2", "2"])
        self.assertEqual(len(self.root.findall(f".//{{{NS}}}CdtTrfTxInf")), 2)

    def test_structured_reference(self):
        refs = [e.text for e in self.root.iter(f"{{{NS}}}Ref")]
        self.assertEqual(refs, ["123453"])
        ustrd = [e.text for e in self.root.iter(f"{{{NS}}}Ustrd")]
        self.assertEqual(ustrd, ["Multiplus II"])

    def test_currency_attribute(self):
        amt = self.root.find(f".//{{{NS}}}InstdAmt")
        self.assertEqual(amt.get("Ccy"), "EUR")

    def test_execution_date(self):
        el = self.root.find(f".//{{{NS}}}ReqdExctnDt")
        self.assertEqual(el.text, "2026-09-25")

    def test_checksum_report(self):
        report = checksum_report(self.batch)
        self.assertEqual(report["kogusumma"], "1349.95")
        self.assertEqual(report["maksete_arv"], 2)


class TestBatchLoading(unittest.TestCase):
    def _csv(self, text: str) -> str:
        tmp = Path(tempfile.mkdtemp()) / "maksed.csv"
        tmp.write_text(text, encoding="utf-8")
        return str(tmp)

    def test_example_file(self):
        example = Path(__file__).resolve().parents[1] / "examples" / "payments.csv"
        batch = load_batch(example, debtor())
        self.assertEqual(batch.count, 3)
        self.assertEqual(batch.control_sum, Decimal("1830.45"))
        self.assertEqual(batch.requested_execution_date, date(2026, 9, 25))

    def test_semicolon_and_comma_decimals(self):
        path = self._csv(
            "saaja_nimi;saaja_iban;summa\n" f"Tarnija AS;{CREDITOR_IBAN};19,90\n"
        )
        batch = load_batch(path, debtor())
        self.assertEqual(batch.control_sum, Decimal("19.90"))

    def test_missing_column(self):
        with self.assertRaises(BatchError):
            load_batch(self._csv("nimi,summa\nX,1.00\n"), debtor())

    def test_all_errors_reported_together(self):
        path = self._csv(
            "saaja_nimi,saaja_iban,summa\n"
            "Vigane,EE382200221020145686,10.00\n"
            f"Ka vigane,{CREDITOR_IBAN},0.00\n"
        )
        with self.assertRaises(BatchError) as ctx:
            load_batch(path, debtor())
        self.assertIn("rida 2", str(ctx.exception))
        self.assertIn("rida 3", str(ctx.exception))

    def test_mixed_dates_rejected(self):
        path = self._csv(
            "saaja_nimi,saaja_iban,summa,kuupaev\n"
            f"A,{CREDITOR_IBAN},10.00,2026-09-25\n"
            f"B,{CREDITOR_IBAN_2},10.00,2026-09-26\n"
        )
        with self.assertRaises(BatchError):
            load_batch(path, debtor())


class TestSebBodies(unittest.TestCase):
    def test_single_payment_body(self):
        body = payment_body(
            payment(reference="123453", end_to_end_id="ARVE-1"), debtor(), date(2026, 9, 25)
        )
        self.assertEqual(body["instructedAmount"], {"currency": "EUR", "amount": "19.90"})
        self.assertEqual(body["debtorAccount"]["iban"], DEBTOR_IBAN)
        self.assertEqual(
            body["remittanceInformationStructured"],
            {"reference": "123453", "referenceType": "SCOR"},
        )
        self.assertNotIn("remittanceInformationUnstructured", body)

    def test_bulk_body(self):
        batch = PaymentBatch(
            debtor=debtor(),
            payments=[payment(), payment(creditor=Party("B", CREDITOR_IBAN_2))],
            requested_execution_date=date(2026, 9, 25),
        )
        body = bulk_body(batch)
        self.assertEqual(len(body["payments"]), 2)
        self.assertEqual(body["requestedExecutionDate"], "2026-09-25")

    def test_status_classification(self):
        self.assertIn("vastu votnud", classify_status("ACCP"))
        self.assertIn("TAGASI", classify_status("RJCT"))


class TestDryRunSafety(unittest.TestCase):
    """Koige tahtsam test: ilma loata ei lahe midagi valja."""

    def test_dry_run_writes_file_and_sends_nothing(self):
        from bankprep.config import SebConfig
        from bankprep.seb_xs2a import SebClient

        out = Path(tempfile.mkdtemp())
        client = SebClient(SebConfig(), dry_run=True, output_dir=out)
        result = client.initiate_payment(payment(), debtor(), date(2026, 9, 25))
        self.assertTrue(result["dry_run"])
        saved = Path(result["saved_to"])
        self.assertTrue(saved.exists())
        self.assertIn("sepa-credit-transfers", result["url"])

    def test_live_blocked_when_allow_live_false(self):
        from bankprep.config import SebConfig
        from bankprep.seb_xs2a import SebClient

        out = Path(tempfile.mkdtemp())
        client = SebClient(SebConfig(allow_live=False), dry_run=False, output_dir=out)
        result = client.initiate_payment(payment(), debtor(), date(2026, 9, 25))
        self.assertEqual(result["reason"], "allow_live=false")

    def test_secrets_are_redacted_in_saved_request(self):
        from bankprep.config import SebConfig
        from bankprep.seb_xs2a import SebClient

        out = Path(tempfile.mkdtemp())
        client = SebClient(
            SebConfig(), dry_run=True, output_dir=out, access_token="SALAJANE", psu_id="38001010000"
        )
        result = client.initiate_payment(payment(), debtor(), None)
        saved = Path(result["saved_to"]).read_text(encoding="utf-8")
        self.assertNotIn("SALAJANE", saved)
        self.assertNotIn("38001010000", saved)


if __name__ == "__main__":
    unittest.main()
