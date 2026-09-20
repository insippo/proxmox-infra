"""SEB Baltics XS2A klient (Berlin Group NextGenPSD2).

Vool, mida see moodul katab:

    1. POST /v1/payments/sepa-credit-transfers      -> paymentId + SCA link
    2. kasutaja kinnitab Smart-ID/Mobiil-IDga pangas (redirect SCA)
    3. GET  /v1/payments/sepa-credit-transfers/{id}/status -> ACCP / RJCT ...

TAHTIS. Kaks asja, mis ei ole tehnilised:
  - PIS API kasutamine kolmanda osapoolena nouab PSD2 litsentsi
    (Finantsinspektsioon) ja eIDAS sertifikaate. Oma ettevotte kontole
    ligipaasuks kusi SEB-lt arikliendi API-lepingut.
  - Ilma nendeta toimib ainult pain.001 tee (bankprep/pain001.py).
    See moodul on valmis, aga ootab sertifikaate.

Vaikimisi on klient DRY-RUN: paring kirjutatakse faili, mitte panka.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from bankprep.config import SebConfig
from bankprep.models import Party, Payment, PaymentBatch
from bankprep.signing import Signer, SigningError, digest_header, http_date

# Neid paIseid ei kirjutata kunagi logisse ega dry-run faili.
REDACTED_HEADERS = {"authorization", "signature", "tpp-signature-certificate", "psu-id"}

# Berlin Group tehingustaatused, mis tahendavad "raha liigub / liikus".
FINAL_OK = {"ACCC", "ACSC", "ACSP", "ACCP", "ACWC"}
FINAL_BAD = {"RJCT", "CANC", "EXPI"}


class SebError(RuntimeError):
    """Panga API tagastas vea voi klient ei ole kasutusvalmis."""


def _redact(headers: dict[str, str]) -> dict[str, str]:
    return {
        k: ("<peidetud>" if k.lower() in REDACTED_HEADERS else v)
        for k, v in headers.items()
    }


def payment_body(payment: Payment, debtor: Party, execution_date: date | None) -> dict[str, Any]:
    """Uks makse Berlin Group JSON-kujul."""
    body: dict[str, Any] = {
        "endToEndIdentification": payment.end_to_end_id,
        "instructedAmount": {"currency": payment.currency, "amount": payment.amount_str},
        "debtorAccount": {"iban": debtor.iban, "currency": payment.currency},
        "creditorAccount": {"iban": payment.creditor.iban, "currency": payment.currency},
        "creditorName": payment.creditor.name,
    }
    if payment.creditor.bic:
        body["creditorAgent"] = payment.creditor.bic
    if payment.reference:
        # SCOR = structured creditor reference (viitenumber).
        body["remittanceInformationStructured"] = {
            "reference": payment.reference,
            "referenceType": "SCOR",
        }
    elif payment.remittance:
        body["remittanceInformationUnstructured"] = payment.remittance
    if execution_date:
        body["requestedExecutionDate"] = execution_date.isoformat()
    return body


def bulk_body(batch: PaymentBatch) -> dict[str, Any]:
    """Maksepakk (bulk-payments) Berlin Group JSON-kujul."""
    return {
        "batchBookingPreferred": batch.batch_booking,
        "requestedExecutionDate": batch.requested_execution_date.isoformat(),
        "debtorAccount": {"iban": batch.debtor.iban, "currency": "EUR"},
        "payments": [payment_body(p, batch.debtor, None) for p in batch.payments],
    }


@dataclass
class PreparedRequest:
    """Valmis paring - kas saadetud voi failina ootel."""

    method: str
    url: str
    headers: dict[str, str]
    body: bytes
    request_id: str

    def to_json(self) -> str:
        return json.dumps(
            {
                "method": self.method,
                "url": self.url,
                "headers": _redact(self.headers),
                "body": json.loads(self.body) if self.body else None,
                "request_id": self.request_id,
            },
            indent=2,
            ensure_ascii=False,
        )


@dataclass
class SebClient:
    """SEB XS2A HTTP klient."""

    config: SebConfig
    access_token: str = ""
    dry_run: bool = True
    output_dir: Path = Path("out/requests")
    psu_ip_address: str = ""
    psu_id: str = ""
    _signer: Signer | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self.output_dir = Path(self.output_dir)
        if self.config.qseal_cert and self.config.qseal_key:
            try:
                self._signer = Signer(
                    self.config.qseal_cert,
                    self.config.qseal_key,
                    key_id=self.config.qseal_key_id,
                )
            except SigningError:
                # Sandbox ilma QSEALC-ta on lubatud - allkiri jaab lisamata.
                self._signer = None

    # ------------------------------------------------------------------ OAuth

    def authorize_url(self, *, state: str, scope: str = "payments") -> str:
        """Kasutaja suunatakse siia Smart-ID/Mobiil-ID kinnitusele."""
        params = {
            "response_type": "code",
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "scope": scope,
            "state": state,
        }
        return self.config.api_url("/auth/v1/authorize") + "?" + urlencode(params)

    def exchange_code(self, code: str) -> dict[str, Any]:
        """Vahetab SCA-jargse koodi access_token-i vastu."""
        self._require_live("token-vahetus")
        import requests

        response = requests.post(
            self.config.api_url("/auth/v1/token"),
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.config.redirect_uri,
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
            },
            cert=self._client_cert(),
            timeout=30,
        )
        if response.status_code >= 400:
            raise SebError(f"Token-vahetus ebaonnestus ({response.status_code}): {response.text}")
        token = response.json()
        self.access_token = token.get("access_token", "")
        return token

    # ---------------------------------------------------------------- Maksed

    def initiate_payment(
        self, payment: Payment, debtor: Party, execution_date: date | None = None
    ) -> dict[str, Any]:
        """Algatab uhe SEPA makse. Makse jaab SCA ootele, raha ei liigu veel."""
        body = payment_body(payment, debtor, execution_date)
        path = f"/v1/{self.config.payment_service}/{self.config.payment_product}"
        return self._send("POST", path, body, label=f"makse-{payment.end_to_end_id}")

    def initiate_bulk(self, batch: PaymentBatch) -> dict[str, Any]:
        """Algatab maksepaki (bulk-payments)."""
        path = f"/v1/bulk-payments/{self.config.payment_product}"
        return self._send("POST", path, bulk_body(batch), label="maksepakk")

    def payment_status(self, payment_id: str) -> dict[str, Any]:
        """Kusib makse staatust (ACCP, ACSC, RJCT, ...)."""
        path = (
            f"/v1/{self.config.payment_service}/{self.config.payment_product}"
            f"/{payment_id}/status"
        )
        return self._send("GET", path, None, label=f"staatus-{payment_id}")

    # ------------------------------------------------------------- Sisemine

    def _client_cert(self) -> tuple[str, str] | None:
        """QWAC mTLS sertifikaadipaar requests-ile."""
        if self.config.qwac_cert and self.config.qwac_key:
            return (str(self.config.qwac_cert), str(self.config.qwac_key))
        return None

    def _headers(self, body: bytes) -> dict[str, str]:
        request_id = str(uuid.uuid4())
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Request-ID": request_id,
            "Date": http_date(),
            "Digest": digest_header(body),
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        if self.psu_ip_address:
            headers["PSU-IP-Address"] = self.psu_ip_address
        if self.psu_id:
            headers["PSU-ID"] = self.psu_id
        if self.config.tpp_redirect_uri:
            headers["TPP-Redirect-Preferred"] = "true"
            headers["TPP-Redirect-URI"] = self.config.tpp_redirect_uri
        if self.config.tpp_nok_redirect_uri:
            headers["TPP-Nok-Redirect-URI"] = self.config.tpp_nok_redirect_uri
        if self._signer is not None:
            headers["Signature"] = self._signer.sign(headers)
            headers["TPP-Signature-Certificate"] = self._signer.certificate_b64()
        return headers

    def _require_live(self, what: str) -> None:
        if self.dry_run:
            raise SebError(f"{what} ei ole dry-run reziimis voimalik")
        if not self.config.allow_live:
            raise SebError(
                f"{what} on blokeeritud: bank.toml [seb] allow_live = false. "
                "See lukk on meelega - eemalda see alles siis, kui sertifikaadid "
                "ja leping on olemas."
            )

    def prepare(self, method: str, path: str, body: dict[str, Any] | None) -> PreparedRequest:
        """Koostab paringu ilma seda saatmata."""
        raw = json.dumps(body, ensure_ascii=False).encode() if body is not None else b""
        headers = self._headers(raw)
        return PreparedRequest(
            method=method,
            url=self.config.api_url(path),
            headers=headers,
            body=raw,
            request_id=headers["X-Request-ID"],
        )

    def _send(
        self, method: str, path: str, body: dict[str, Any] | None, *, label: str
    ) -> dict[str, Any]:
        prepared = self.prepare(method, path, body)

        if self.dry_run or not self.config.allow_live:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            target = self.output_dir / f"{label}-{prepared.request_id[:8]}.json"
            target.write_text(prepared.to_json(), encoding="utf-8")
            return {
                "dry_run": True,
                "saved_to": str(target),
                "request_id": prepared.request_id,
                "url": prepared.url,
                "reason": "dry-run" if self.dry_run else "allow_live=false",
            }

        import requests

        response = requests.request(
            prepared.method,
            prepared.url,
            headers=prepared.headers,
            data=prepared.body or None,
            cert=self._client_cert(),
            timeout=60,
        )
        if response.status_code >= 400:
            raise SebError(
                f"SEB {prepared.method} {path} -> {response.status_code}: {response.text[:800]}"
            )
        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text}
        payload["_http_status"] = response.status_code
        payload["_request_id"] = prepared.request_id
        return payload


def classify_status(status: str) -> str:
    """Tolgib Berlin Group staatuse eesti keelde."""
    status = (status or "").upper()
    if status in FINAL_OK:
        return f"{status}: pank on makse vastu votnud"
    if status in FINAL_BAD:
        return f"{status}: makse LUKATI TAGASI voi tuhistati"
    if status in {"RCVD", "PDNG", "ACTC"}:
        return f"{status}: ootab kinnitust/tootlust"
    return f"{status}: tundmatu staatus, vaata panga dokumentatsiooni"
