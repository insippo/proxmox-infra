"""Maksepaki lugemine CSV-st.

CSV sellepast, et see tuleb valja igast raamatupidamisprogrammist
(Merit, SmartAccounts, e-arvete eksport) ja seda saab inimene enne
ule vaadata ilma eritooriistata.

Veerud (eesti voi inglise nimed, jarjekord ei loe):
    saaja_nimi / name          - kohustuslik
    saaja_iban / iban          - kohustuslik
    summa / amount             - kohustuslik, nt 19.90 voi 19,90
    saaja_bic / bic            - valikuline
    viitenumber / reference    - valikuline
    selgitus / remittance      - valikuline (ignoreeritakse, kui viide olemas)
    viide_id / end_to_end_id   - valikuline, vaikimisi arve number
    kuupaev / execution_date   - valikuline (YYYY-MM-DD)
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from bankprep.models import Party, Payment, PaymentBatch, ValidationError

COLUMN_ALIASES = {
    "name": {"saaja_nimi", "saaja", "nimi", "name", "creditor", "creditor_name"},
    "iban": {"saaja_iban", "iban", "konto", "creditor_iban", "account"},
    "bic": {"saaja_bic", "bic", "swift", "creditor_bic"},
    "amount": {"summa", "amount", "sum", "kogus"},
    "reference": {"viitenumber", "viide", "reference", "ref"},
    "remittance": {"selgitus", "kirjeldus", "remittance", "description", "message"},
    "end_to_end_id": {"viide_id", "e2e", "end_to_end_id", "endtoendid", "arve", "invoice"},
    "execution_date": {"kuupaev", "maksekuupaev", "execution_date", "date"},
}


class BatchError(ValueError):
    """Maksepakki ei saa failist lugeda."""


def _normalise_header(fieldnames: list[str] | None) -> dict[str, str]:
    """Seob CSV veerunimed sisemiste valjadega."""
    if not fieldnames:
        raise BatchError("CSV-l puudub paIsrida")
    mapping: dict[str, str] = {}
    for raw in fieldnames:
        key = (raw or "").strip().lower().replace(" ", "_").lstrip("﻿")
        for field, aliases in COLUMN_ALIASES.items():
            if key in aliases:
                mapping[raw] = field
                break
    missing = {"name", "iban", "amount"} - set(mapping.values())
    if missing:
        raise BatchError(
            "CSV-s puuduvad kohustuslikud veerud: "
            + ", ".join(sorted(missing))
            + f" (leitud: {sorted(set(mapping.values()))})"
        )
    return mapping


def _sniff_dialect(sample: str) -> type[csv.Dialect] | csv.Dialect:
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        return csv.excel


def read_rows(path: str | Path) -> list[dict[str, str]]:
    """Loeb CSV read sisemiste valjanimedega. Ei valideeri sisu."""
    raw = Path(path).read_text(encoding="utf-8-sig")
    if not raw.strip():
        raise BatchError(f"Fail {path} on tuhi")
    reader = csv.DictReader(raw.splitlines(), dialect=_sniff_dialect(raw[:2048]))
    mapping = _normalise_header(reader.fieldnames)
    rows: list[dict[str, str]] = []
    for row in reader:
        clean = {
            mapping[k]: (v or "").strip()
            for k, v in row.items()
            if k in mapping and v is not None
        }
        if not any(clean.values()):
            continue  # tuhi rida faili lopus
        rows.append(clean)
    if not rows:
        raise BatchError(f"Failis {path} ei ole uhtegi makserida")
    return rows


def load_batch(
    path: str | Path,
    debtor: Party,
    *,
    execution_date: date | None = None,
) -> PaymentBatch:
    """Loeb CSV-st maksepaki. Koik vead korraga, mitte esimene kaupa.

    Esimese vea peale katkestamine tahendab, et inimene parandab faili
    viis korda jarjest. Kogume vead kokku ja anname uhe nimekirjana.
    """
    rows = read_rows(path)
    payments: list[Payment] = []
    errors: list[str] = []
    dates: set[date] = set()

    for line_no, row in enumerate(rows, start=2):  # rida 1 on paIs
        try:
            if row.get("execution_date"):
                dates.add(date.fromisoformat(row["execution_date"]))
            payments.append(
                Payment(
                    creditor=Party(
                        name=row.get("name", ""),
                        iban=row.get("iban", ""),
                        bic=row.get("bic") or None,
                    ),
                    amount=row.get("amount", ""),
                    reference=row.get("reference") or None,
                    remittance=row.get("remittance", ""),
                    end_to_end_id=row.get("end_to_end_id")
                    or row.get("reference")
                    or "NOTPROVIDED",
                )
            )
        except (ValidationError, ValueError) as exc:
            errors.append(f"rida {line_no}: {exc}")

    if errors:
        raise BatchError(
            f"{len(errors)} viga failis {path}:\n  - " + "\n  - ".join(errors)
        )

    if execution_date is None:
        if len(dates) > 1:
            raise BatchError(
                "Failis on mitu erinevat maksekuupaeva: "
                + ", ".join(sorted(d.isoformat() for d in dates))
                + " - uks pain.001 plokk lubab uhte. Tee eraldi failid."
            )
        execution_date = dates.pop() if dates else date.today()

    return PaymentBatch(
        debtor=debtor, payments=payments, requested_execution_date=execution_date
    )
