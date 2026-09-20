"""Makse andmemudel ja valideerimine.

Koik piirangud siin tulevad SEPA / ISO 20022 pain.001 reeglitest:
  - nimi kuni 70 marki
  - selgitus (unstructured remittance) kuni 140 marki
  - EndToEndId kuni 35 marki, ilma tuhikuteta
  - summa taipselt 2 kohta parast koma, > 0
  - SEPA lubab ainult EUR-i
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from bankprep.iban import IbanError, validate_bic, validate_iban
from bankprep.reference import ReferenceError, validate_reference

MAX_NAME = 70
MAX_REMITTANCE = 140
MAX_END_TO_END_ID = 35

# SEPA ladina tahestik. Kaik muu tuleb translitereerida, muidu pank
# kas keeldub voi moonutab teksti.
_SEPA_ALLOWED = re.compile(r"^[A-Za-z0-9/\-?:().,'+ ]*$")
_TRANSLIT = {
    "Ä": "A", "Ö": "O", "Ü": "U", "Õ": "O", "Š": "S", "Ž": "Z",
    "ä": "a", "ö": "o", "ü": "u", "õ": "o", "š": "s", "ž": "z",
    "Å": "A", "å": "a", "Æ": "AE", "æ": "ae", "Ø": "O", "ø": "o",
    "ß": "ss", "€": "EUR", "&": "+", " ": " ",
}


class ValidationError(ValueError):
    """Makse ei labi valideerimist."""


def to_sepa_charset(text: str) -> str:
    """Teisendab teksti SEPA lubatud margistikku.

    Taptahtlikult kadudega: ä -> a. Parem etteaimatav teisendus meie pool
    kui panga pool tundmatu tulemus.
    """
    if not text:
        return ""
    out = []
    for ch in text:
        if ch in _TRANSLIT:
            out.append(_TRANSLIT[ch])
            continue
        if _SEPA_ALLOWED.match(ch):
            out.append(ch)
            continue
        decomposed = unicodedata.normalize("NFKD", ch)
        stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
        out.append(stripped if _SEPA_ALLOWED.match(stripped) else " ")
    return re.sub(r" {2,}", " ", "".join(out)).strip()


def parse_amount(value: object) -> Decimal:
    """Teeb summast Decimal-i 2 kohaga. Ei kasuta kunagi float-i."""
    if isinstance(value, float):
        # float ei ole rahas kunagi tapne - noua stringi voi Decimal-i.
        raise ValidationError(
            f"Summa {value!r} on float. Kasuta stringi voi Decimal-i (nt '19.90')."
        )
    text = str(value).strip().replace(" ", "").replace(" ", "")
    text = text.replace(",", ".")
    if not text:
        raise ValidationError("Summa puudub")
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise ValidationError(f"Summa {value!r} ei ole arv") from exc
    if amount <= 0:
        raise ValidationError(f"Summa peab olema positiivne, on {amount}")
    quantized = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if quantized != amount:
        raise ValidationError(
            f"Summa {amount} on rohkem kui 2 kumnendkohaga - umarda ise, "
            f"et vastutus oleks selge (oleks {quantized})"
        )
    return quantized


@dataclass
class Party:
    """Maksja voi saaja."""

    name: str
    iban: str
    bic: str | None = None
    country: str | None = None

    def __post_init__(self) -> None:
        clean = to_sepa_charset(self.name)
        if not clean:
            raise ValidationError("Osapoole nimi puudub")
        if len(clean) > MAX_NAME:
            raise ValidationError(
                f"Nimi on {len(clean)} marki, lubatud {MAX_NAME}: {clean!r}"
            )
        self.name = clean
        self.iban = validate_iban(self.iban)
        self.bic = validate_bic(self.bic)
        self.country = (self.country or self.iban[:2]).upper()


@dataclass
class Payment:
    """Uks maksekorraldus."""

    creditor: Party
    amount: Decimal
    currency: str = "EUR"
    remittance: str = ""
    reference: str | None = None
    end_to_end_id: str = "NOTPROVIDED"
    requested_execution_date: date | None = None

    def __post_init__(self) -> None:
        self.amount = parse_amount(self.amount)
        self.currency = (self.currency or "EUR").upper()
        if self.currency != "EUR":
            raise ValidationError(
                f"SEPA kreeditkorraldus on ainult EUR, anti {self.currency}"
            )
        self.reference = validate_reference(self.reference)

        self.remittance = to_sepa_charset(self.remittance)
        if len(self.remittance) > MAX_REMITTANCE:
            raise ValidationError(
                f"Selgitus on {len(self.remittance)} marki, lubatud {MAX_REMITTANCE}"
            )
        if self.reference and self.remittance:
            # ISO 20022: struktureeritud viide ja vaba tekst on teineteist
            # valistavad. Viitenumber voidab - selle jargi seotakse arve.
            self.remittance = ""

        e2e = to_sepa_charset(self.end_to_end_id or "NOTPROVIDED").replace(" ", "")
        if len(e2e) > MAX_END_TO_END_ID:
            raise ValidationError(
                f"EndToEndId on {len(e2e)} marki, lubatud {MAX_END_TO_END_ID}"
            )
        self.end_to_end_id = e2e or "NOTPROVIDED"

    @property
    def amount_str(self) -> str:
        return f"{self.amount:.2f}"


@dataclass
class PaymentBatch:
    """Maksepakk: uks maksja, uks kuupaev, mitu saajat."""

    debtor: Party
    payments: list[Payment] = field(default_factory=list)
    requested_execution_date: date | None = None
    batch_booking: bool = False
    message_id: str | None = None

    def __post_init__(self) -> None:
        if not self.payments:
            raise ValidationError("Maksepakk on tuhi")
        if self.requested_execution_date is None:
            self.requested_execution_date = date.today()
        for payment in self.payments:
            if payment.creditor.iban == self.debtor.iban:
                raise ValidationError(
                    f"Saaja IBAN on sama mis maksja oma: {payment.creditor.iban}"
                )

    @property
    def control_sum(self) -> Decimal:
        return sum((p.amount for p in self.payments), Decimal("0.00"))

    @property
    def count(self) -> int:
        return len(self.payments)

    def duplicate_end_to_end_ids(self) -> list[str]:
        """Korduvad EndToEndId-d - pank voib need topeltmakseks lugeda."""
        seen: dict[str, int] = {}
        for payment in self.payments:
            if payment.end_to_end_id == "NOTPROVIDED":
                continue
            seen[payment.end_to_end_id] = seen.get(payment.end_to_end_id, 0) + 1
        return sorted(k for k, v in seen.items() if v > 1)


__all__ = [
    "IbanError",
    "Party",
    "Payment",
    "PaymentBatch",
    "ReferenceError",
    "ValidationError",
    "parse_amount",
    "to_sepa_charset",
]
