"""Viitenumbrid: Eesti/Soome 7-3-1 ja rahvusvaheline RF (ISO 11649).

Viitenumbri vale kontrollnumber on uks sagedasemaid pohjuseid, miks makse
laheb "valesse kohta" - raha jouab kontole, aga arve jaab lahti. Seetottu
kontrollime seda enne pangale saatmist, mitte parast.
"""

from __future__ import annotations

import re
import string

_WEIGHTS = (7, 3, 1)
_LETTER_VALUES = {c: str(10 + i) for i, c in enumerate(string.ascii_uppercase)}


class ReferenceError(ValueError):
    """Vigane viitenumber."""


def normalize(value: str) -> str:
    return re.sub(r"\s+", "", (value or "")).upper()


def et_check_digit(base: str) -> str:
    """Eesti viitenumbri kontrollnumber (7-3-1, paremalt vasakule)."""
    if not base.isdigit():
        raise ReferenceError(f"Viitenumbri alus peab olema numbriline: {base!r}")
    total = 0
    for i, ch in enumerate(reversed(base)):
        total += int(ch) * _WEIGHTS[i % 3]
    return str((10 - total % 10) % 10)


def make_et_reference(base: str) -> str:
    """Lisab alusele (nt arve numbrile) kontrollnumbri."""
    base = normalize(base)
    return base + et_check_digit(base)


def is_valid_et_reference(value: str) -> bool:
    ref = normalize(value)
    if not ref.isdigit() or not 2 <= len(ref) <= 20:
        return False
    return et_check_digit(ref[:-1]) == ref[-1]


def is_valid_rf_reference(value: str) -> bool:
    """ISO 11649 RF-viide: mod-97 jaak peab olema 1."""
    ref = normalize(value)
    if not re.match(r"^RF[0-9]{2}[A-Z0-9]{1,21}$", ref):
        return False
    rearranged = ref[4:] + ref[:4]
    digits = "".join(_LETTER_VALUES.get(ch, ch) for ch in rearranged)
    return int(digits) % 97 == 1


def make_rf_reference(base: str) -> str:
    """Teeb alusest RF-viite (ISO 11649)."""
    base = normalize(base)
    if not re.match(r"^[A-Z0-9]{1,21}$", base):
        raise ReferenceError(f"RF-viite alus on vigane: {base!r}")
    digits = "".join(_LETTER_VALUES.get(ch, ch) for ch in base) + "2715" + "00"
    check = 98 - int(digits) % 97
    return f"RF{check:02d}{base}"


def validate_reference(value: str | None) -> str | None:
    """Valideerib viitenumbri, kui see on antud. Tagastab normaliseeritud kuju.

    Tuhi viitenumber on lubatud - kaik maksed ei kai viitenumbriga.
    """
    if not value:
        return None
    ref = normalize(value)
    if ref.startswith("RF"):
        if not is_valid_rf_reference(ref):
            raise ReferenceError(f"RF-viide {ref} ei labi mod-97 kontrolli")
        return ref
    if not is_valid_et_reference(ref):
        raise ReferenceError(
            f"Viitenumber {ref} ei labi 7-3-1 kontrolli "
            f"(oige kontrollnumber aluselt {ref[:-1]} oleks "
            f"{et_check_digit(ref[:-1]) if ref[:-1].isdigit() else '?'})"
        )
    return ref
