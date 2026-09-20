"""Seadistus TOML-failist.

Reegel: saladused (sertifikaadid, votmed, client_secret) EI OLE kunagi
config-failis endas - failis on ainult viide failiteele voi
keskkonnamuutujale. Nii ei satu midagi kogemata gitti.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from bankprep.models import Party

DEFAULT_CONFIG = "bank.toml"

# SEB Baltics XS2A (Berlin Group NextGenPSD2). Tapsed hostinimed kontrolli
# uule developer.baltics.sebgroup.com portaalist - neid muudetakse harva,
# aga meie ei kirjuta neid koodi kovasti sisse.
ENVIRONMENTS = {
    "sandbox": "https://api.sandbox.baltics.sebgroup.com",
    "production": "https://api.baltics.sebgroup.com",
}


class ConfigError(ValueError):
    """Seadistus on puudulik voi vigane."""


def _resolve(base: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(os.path.expanduser(value))
    return path if path.is_absolute() else (base / path)


@dataclass
class SebConfig:
    """SEB XS2A juurdepaasu seaded."""

    environment: str = "sandbox"
    base_url: str = ""
    client_id: str = ""
    client_secret_env: str = "SEB_CLIENT_SECRET"
    redirect_uri: str = ""
    payment_product: str = "sepa-credit-transfers"
    payment_service: str = "payments"
    # eIDAS sertifikaadid: QWAC = mTLS kanal, QSEALC = sonumi allkiri.
    qwac_cert: Path | None = None
    qwac_key: Path | None = None
    qseal_cert: Path | None = None
    qseal_key: Path | None = None
    qseal_key_id: str = ""
    tpp_redirect_uri: str = ""
    tpp_nok_redirect_uri: str = ""
    # Turvalukk: paringu tegelik saatmine nouab, et see oleks true JA
    # kasutaja annaks --confirm. Vaikimisi kirjutame paringu ainult faili.
    allow_live: bool = False

    @property
    def client_secret(self) -> str:
        return os.environ.get(self.client_secret_env, "")

    def api_url(self, path: str) -> str:
        base = self.base_url or ENVIRONMENTS.get(self.environment, "")
        if not base:
            raise ConfigError(
                f"Tundmatu keskkond {self.environment!r} ja base_url on maaramata"
            )
        return f"{base.rstrip('/')}/{path.lstrip('/')}"

    def check_ready(self) -> list[str]:
        """Mis on API kasutamiseks veel puudu. Tuhi list = valmis."""
        missing: list[str] = []
        if not self.client_id:
            missing.append("seb.client_id (registreeri APP developer-portaalis)")
        if not self.client_secret:
            missing.append(f"keskkonnamuutuja {self.client_secret_env}")
        for name, path in (
            ("seb.qwac_cert", self.qwac_cert),
            ("seb.qwac_key", self.qwac_key),
            ("seb.qseal_cert", self.qseal_cert),
            ("seb.qseal_key", self.qseal_key),
        ):
            if path is None:
                missing.append(f"{name} (eIDAS sertifikaat puudub)")
            elif not path.exists():
                missing.append(f"{name}: faili {path} ei ole")
        if not self.redirect_uri:
            missing.append("seb.redirect_uri (SCA suunamise aadress)")
        return missing


@dataclass
class Config:
    debtor: Party
    seb: SebConfig = field(default_factory=SebConfig)
    output_dir: Path = Path("out")
    source: Path | None = None


def load_config(path: str | Path | None = None) -> Config:
    """Loeb bank.toml faili."""
    cfg_path = Path(path or os.environ.get("BANKPREP_CONFIG", DEFAULT_CONFIG))
    if not cfg_path.exists():
        raise ConfigError(
            f"Seadistusfaili {cfg_path} ei ole. Tee koopia: "
            f"cp payments/examples/config.example.toml {cfg_path}"
        )
    with cfg_path.open("rb") as fh:
        raw = tomllib.load(fh)

    base = cfg_path.resolve().parent
    debtor_raw = raw.get("debtor") or {}
    if not debtor_raw.get("iban"):
        raise ConfigError(f"{cfg_path}: [debtor] iban puudub")
    debtor = Party(
        name=debtor_raw.get("name", ""),
        iban=debtor_raw["iban"],
        bic=debtor_raw.get("bic") or None,
    )

    seb_raw = raw.get("seb") or {}
    seb = SebConfig(
        environment=seb_raw.get("environment", "sandbox"),
        base_url=seb_raw.get("base_url", ""),
        client_id=seb_raw.get("client_id", ""),
        client_secret_env=seb_raw.get("client_secret_env", "SEB_CLIENT_SECRET"),
        redirect_uri=seb_raw.get("redirect_uri", ""),
        payment_product=seb_raw.get("payment_product", "sepa-credit-transfers"),
        payment_service=seb_raw.get("payment_service", "payments"),
        qwac_cert=_resolve(base, seb_raw.get("qwac_cert")),
        qwac_key=_resolve(base, seb_raw.get("qwac_key")),
        qseal_cert=_resolve(base, seb_raw.get("qseal_cert")),
        qseal_key=_resolve(base, seb_raw.get("qseal_key")),
        qseal_key_id=seb_raw.get("qseal_key_id", ""),
        tpp_redirect_uri=seb_raw.get("tpp_redirect_uri", seb_raw.get("redirect_uri", "")),
        tpp_nok_redirect_uri=seb_raw.get("tpp_nok_redirect_uri", ""),
        allow_live=bool(seb_raw.get("allow_live", False)),
    )

    out = raw.get("output") or {}
    output_dir = _resolve(base, out.get("dir", "out")) or (base / "out")

    return Config(debtor=debtor, seb=seb, output_dir=output_dir, source=cfg_path)
