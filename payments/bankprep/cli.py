"""bankprep kasurealiides.

    python -m bankprep check                  - kas seadistus on valmis
    python -m bankprep validate maksed.csv    - kontrolli ilma faili tegemata
    python -m bankprep prepare  maksed.csv    - tee pain.001 XML + aruanne
    python -m bankprep submit   maksed.csv    - valmista SEB XS2A paring ette
    python -m bankprep status   <paymentId>   - kusi makse staatust
    python -m bankprep ref 2026001            - arvuta viitenumber

Ukski kask ei saada raha teele ilma inimese kinnituseta.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from bankprep import __version__
from bankprep.batch import BatchError, load_batch
from bankprep.config import Config, ConfigError, load_config
from bankprep.models import ValidationError
from bankprep.pain001 import checksum_report, write_file
from bankprep.reference import make_et_reference, make_rf_reference


def _load(args: argparse.Namespace) -> Config:
    return load_config(args.config)


def _exec_date(args: argparse.Namespace) -> date | None:
    return date.fromisoformat(args.date) if getattr(args, "date", None) else None


def _print_report(batch, title: str) -> None:
    report = checksum_report(batch)
    print(f"\n{title}")
    print("-" * len(title))
    print(f"  maksja      : {batch.debtor.name} / {batch.debtor.iban}")
    print(f"  makseid     : {report['maksete_arv']}")
    print(f"  kogusumma   : {report['kogusumma']} EUR")
    print(f"  kuupaev     : {report['kuupaev']}")
    print(f"  suurim makse: {report['suurim_makse']} EUR")
    if report["korduvad_e2e_id"]:
        print(f"  HOIATUS: korduvad viite-ID-d: {report['korduvad_e2e_id']}")
    print()
    for payment in batch.payments:
        ref = payment.reference or payment.remittance or "-"
        print(
            f"  {payment.amount_str:>12} EUR  {payment.creditor.iban:<24}"
            f"{payment.creditor.name[:28]:<30}{ref[:40]}"
        )
    print()


def cmd_check(args: argparse.Namespace) -> int:
    cfg = _load(args)
    print(f"seadistus  : {cfg.source}")
    print(f"maksja     : {cfg.debtor.name} / {cfg.debtor.iban}")
    print(f"keskkond   : {cfg.seb.environment}  ({cfg.seb.api_url('/')})")
    print(f"allow_live : {cfg.seb.allow_live}")
    missing = cfg.seb.check_ready()
    if missing:
        print("\nAPI-tee ei ole veel kasutatav. Puudu:")
        for item in missing:
            print(f"  - {item}")
        print("\npain.001 tee (prepare) tootab sellest hoolimata.")
    else:
        print("\nAPI-tee: koik komponendid olemas.")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    cfg = _load(args)
    batch = load_batch(args.csv, cfg.debtor, execution_date=_exec_date(args))
    _print_report(batch, f"Kontroll labitud: {args.csv}")
    return 0


def cmd_prepare(args: argparse.Namespace) -> int:
    cfg = _load(args)
    batch = load_batch(args.csv, cfg.debtor, execution_date=_exec_date(args))
    out_dir = Path(args.out or cfg.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    stamp = batch.requested_execution_date.isoformat()
    xml_path = out_dir / f"pain001-{stamp}-{batch.count}x.xml"
    msg_id = write_file(batch, str(xml_path))

    report_path = xml_path.with_suffix(".json")
    report = checksum_report(batch)
    report["msg_id"] = msg_id
    report["fail"] = str(xml_path)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    _print_report(batch, f"pain.001 valmis: {xml_path}")
    print(f"  MsgId     : {msg_id}")
    print(f"  aruanne   : {report_path}")
    print("\nJargmine samm: impordi XML internetipanka, vordle kogusummat")
    print("ja maksete arvu ulaltooduga, siis allkirjasta.")
    return 0


def cmd_submit(args: argparse.Namespace) -> int:
    from bankprep.seb_xs2a import SebClient, SebError

    cfg = _load(args)
    batch = load_batch(args.csv, cfg.debtor, execution_date=_exec_date(args))
    missing = cfg.seb.check_ready()
    live = args.confirm and cfg.seb.allow_live and not missing

    if args.confirm and not cfg.seb.allow_live:
        print("KATKESTATUD: bank.toml [seb] allow_live = false.", file=sys.stderr)
        return 2
    if args.confirm and missing:
        print("KATKESTATUD: seadistus on puudulik:", file=sys.stderr)
        for item in missing:
            print(f"  - {item}", file=sys.stderr)
        return 2

    client = SebClient(
        cfg.seb,
        access_token=args.token or "",
        dry_run=not live,
        output_dir=Path(args.out or cfg.output_dir) / "requests",
        psu_id=args.psu_id or "",
        psu_ip_address=args.psu_ip or "",
    )
    _print_report(batch, f"{'SAADAN PANKA' if live else 'DRY-RUN'}: {args.csv}")

    try:
        if args.bulk:
            results = [client.initiate_bulk(batch)]
        else:
            results = [
                client.initiate_payment(p, batch.debtor, batch.requested_execution_date)
                for p in batch.payments
            ]
    except SebError as exc:
        print(f"VIGA: {exc}", file=sys.stderr)
        return 1

    for result in results:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    if not live:
        print("\nMidagi ei saadetud. Paringud on failides ulal.")
        print("Paris saatmiseks: allow_live = true bank.toml-is JA --confirm.")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    from bankprep.seb_xs2a import SebClient, SebError, classify_status

    cfg = _load(args)
    client = SebClient(
        cfg.seb,
        access_token=args.token or "",
        dry_run=not (args.confirm and cfg.seb.allow_live),
        output_dir=Path(args.out or cfg.output_dir) / "requests",
    )
    try:
        result = client.payment_status(args.payment_id)
    except SebError as exc:
        print(f"VIGA: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    status = result.get("transactionStatus")
    if status:
        print(classify_status(status))
    return 0


def cmd_ref(args: argparse.Namespace) -> int:
    base = args.base
    if args.rf:
        print(make_rf_reference(base))
    else:
        print(make_et_reference(base))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bankprep", description="Maksete ettevalmistamine (SEPA / SEB XS2A)"
    )
    parser.add_argument("--version", action="version", version=f"bankprep {__version__}")
    parser.add_argument("-c", "--config", help="seadistusfail (vaikimisi bank.toml)")
    parser.add_argument("-o", "--out", help="valjundkataloog")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="kontrolli seadistust").set_defaults(func=cmd_check)

    for name, func, helptext in (
        ("validate", cmd_validate, "kontrolli CSV-d"),
        ("prepare", cmd_prepare, "tee pain.001 XML"),
    ):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("csv", help="maksete CSV")
        p.add_argument("--date", help="maksekuupaev YYYY-MM-DD")
        p.set_defaults(func=func)

    p = sub.add_parser("submit", help="valmista SEB XS2A paring ette")
    p.add_argument("csv", help="maksete CSV")
    p.add_argument("--date", help="maksekuupaev YYYY-MM-DD")
    p.add_argument("--bulk", action="store_true", help="uks bulk-paring mitme asemel")
    p.add_argument("--token", help="OAuth access_token")
    p.add_argument("--psu-id", help="maksja isikukood pangas")
    p.add_argument("--psu-ip", help="kasutaja IP (PSU-IP-Address)")
    p.add_argument(
        "--confirm",
        action="store_true",
        help="saada paris panka (nouab ka allow_live = true)",
    )
    p.set_defaults(func=cmd_submit)

    p = sub.add_parser("status", help="kusi makse staatust")
    p.add_argument("payment_id")
    p.add_argument("--token")
    p.add_argument("--confirm", action="store_true")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("ref", help="arvuta viitenumber")
    p.add_argument("base", help="alus, nt arve number")
    p.add_argument("--rf", action="store_true", help="RF-viide (ISO 11649)")
    p.set_defaults(func=cmd_ref)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (BatchError, ConfigError, ValidationError, ValueError) as exc:
        print(f"VIGA: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
