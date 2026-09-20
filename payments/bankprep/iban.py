"""IBAN ja BIC valideerimine.

IBAN kontroll on ISO 13616 mod-97 algoritm: riigikood ja kontrollnumber
tostetakse loppu, tahed asendatakse numbritega (A=10 ... Z=35) ja kogu
arvu jaak 97-ga peab olema 1.
"""

from __future__ import annotations

import re
import string

# Ainult need riigid, mida me tegelikult kasutame/kontrollime pikkuse jargi.
# Tundmatu riigi puhul kontrollime ainult mod-97 ja uldkuju.
IBAN_LENGTHS = {
    "EE": 20,
    "LV": 21,
    "LT": 20,
    "FI": 18,
    "SE": 24,
    "DK": 18,
    "NO": 15,
    "DE": 22,
    "NL": 18,
    "PL": 28,
    "AT": 20,
    "BE": 16,
    "FR": 27,
    "ES": 24,
    "IT": 27,
    "GB": 22,
    "IE": 22,
    "PT": 25,
    "CZ": 24,
    "SK": 24,
    "HU": 28,
    "BG": 22,
    "RO": 24,
    "HR": 21,
    "SI": 19,
    "GR": 27,
    "CY": 28,
    "MT": 31,
    "LU": 20,
    "CH": 21,
    "IS": 26,
}

_IBAN_RE = re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z0-9]{10,30}$")
_BIC_RE = re.compile(r"^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$")

# SEPA piirkond - pain.001 SEPA profiil lubab ainult neid.
SEPA_COUNTRIES = {
    "AT", "BE", "BG", "CH", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR",
    "GB", "GI", "GR", "HR", "HU", "IE", "IS", "IT", "LI", "LT", "LU", "LV",
    "MC", "MT", "NL", "NO", "PL", "PT", "RO", "SE", "SI", "SK", "SM", "VA",
}

_LETTER_VALUES = {c: str(10 + i) for i, c in enumerate(string.ascii_uppercase)}


class IbanError(ValueError):
    """Vigane IBAN."""


def normalize_iban(value: str) -> str:
    """Eemaldab tuhikud ja teeb suurtahed. Ei valideeri."""
    return re.sub(r"\s+", "", (value or "")).upper()


def _to_digits(iban: str) -> str:
    rearranged = iban[4:] + iban[:4]
    return "".join(_LETTER_VALUES.get(ch, ch) for ch in rearranged)


def iban_checksum_ok(iban: str) -> bool:
    """Mod-97 kontroll ilma erinditeta."""
    iban = normalize_iban(iban)
    if not _IBAN_RE.match(iban):
        return False
    return int(_to_digits(iban)) % 97 == 1


def validate_iban(value: str, *, sepa_only: bool = True) -> str:
    """Valideerib IBAN-i ja tagastab normaliseeritud kuju.

    Viskab IbanError, kui midagi on valesti. Pank keeldub sellistest
    maksetest niikuinii - parem katkestada siin kui pangas.
    """
    iban = normalize_iban(value)
    if not iban:
        raise IbanError("IBAN puudub")
    if not _IBAN_RE.match(iban):
        raise IbanError(f"IBAN-i kuju on vigane: {value!r}")

    country = iban[:2]
    expected = IBAN_LENGTHS.get(country)
    if expected is not None and len(iban) != expected:
        raise IbanError(
            f"IBAN {iban}: riigi {country} pikkus peab olema {expected}, on {len(iban)}"
        )
    if int(_to_digits(iban)) % 97 != 1:
        raise IbanError(f"IBAN {iban}: kontrollnumber ei klapi (mod-97)")
    if sepa_only and country not in SEPA_COUNTRIES:
        raise IbanError(f"IBAN {iban}: riik {country} ei ole SEPA piirkonnas")
    return iban


def validate_bic(value: str | None) -> str | None:
    """Valideerib BIC/SWIFT koodi. None ja tuhi string on lubatud."""
    if not value:
        return None
    bic = re.sub(r"\s+", "", value).upper()
    if not _BIC_RE.match(bic):
        raise IbanError(f"BIC {value!r} on vigane (oodatud 8 voi 11 tahemarki)")
    return bic


def format_iban(iban: str) -> str:
    """Inimloetav kuju: EE38 2200 2210 2014 5685."""
    iban = normalize_iban(iban)
    return " ".join(iban[i : i + 4] for i in range(0, len(iban), 4))
