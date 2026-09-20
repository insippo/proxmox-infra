"""Berlin Group NextGenPSD2 sonumi allkirjastamine (QSEALC).

Pank nouab kahte asja lisaks mTLS-ile:
  Digest:    SHA-256=<base64(sha256(body))>
  Signature: cavage HTTP Signature (RFC draft), rsa-sha256

Signature keyId on QSEALC sertifikaadi seerianumber + valjaandja:
  keyId="SN=<serial hex>,CA=<issuer DN>"

Kui votmefaili ei ole, ei tee see moodul midagi - kutsuja peab siis
toole ilma allkirjata (sandbox lubab seda sageli) voi katkestama.
"""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from email.utils import formatdate
from pathlib import Path

# Need paIsed allkirjastatakse ja selles jarjekorras - jarjekord on
# osa allkirjast, seega seda ei tohi muuta.
SIGNED_HEADERS = ("digest", "x-request-id", "psu-id", "date")


class SigningError(RuntimeError):
    """Allkirjastamine ebaonnestus."""


def digest_header(body: bytes) -> str:
    """Digest paIse vaartus."""
    return "SHA-256=" + base64.b64encode(hashlib.sha256(body or b"").digest()).decode()


def http_date() -> str:
    """RFC 7231 kuupaev Date paIsele."""
    return formatdate(timeval=None, localtime=False, usegmt=True)


@dataclass
class Signer:
    """QSEALC allkirjastaja."""

    cert_path: Path
    key_path: Path
    key_id: str = ""
    key_password: bytes | None = None

    def __post_init__(self) -> None:
        self.cert_path = Path(self.cert_path)
        self.key_path = Path(self.key_path)
        for path in (self.cert_path, self.key_path):
            if not path.exists():
                raise SigningError(f"Sertifikaadifaili ei ole: {path}")

    def _load(self):
        from cryptography import x509
        from cryptography.hazmat.primitives.serialization import load_pem_private_key

        cert = x509.load_pem_x509_certificate(self.cert_path.read_bytes())
        key = load_pem_private_key(self.key_path.read_bytes(), password=self.key_password)
        return cert, key

    def certificate_b64(self) -> str:
        """TPP-Signature-Certificate: sertifikaat DER-kujul base64-s."""
        from cryptography import x509
        from cryptography.hazmat.primitives.serialization import Encoding

        cert = x509.load_pem_x509_certificate(self.cert_path.read_bytes())
        return base64.b64encode(cert.public_bytes(Encoding.DER)).decode()

    def compute_key_id(self) -> str:
        """keyId sertifikaadist, kui see ei ole seadistuses ette antud."""
        if self.key_id:
            return self.key_id
        cert, _ = self._load()
        serial = format(cert.serial_number, "x")
        issuer = cert.issuer.rfc4514_string()
        return f'SN={serial},CA={issuer}'

    def sign(self, headers: dict[str, str]) -> str:
        """Koostab Signature paIse vaartuse olemasolevatest paIsetest."""
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding, rsa, ec

        lower = {k.lower(): v for k, v in headers.items()}
        used = [h for h in SIGNED_HEADERS if lower.get(h)]
        if "digest" not in used:
            raise SigningError("Digest paIs peab enne allkirjastamist olemas olema")

        signing_string = "\n".join(f"{h}: {lower[h]}" for h in used).encode()
        _, key = self._load()

        if isinstance(key, rsa.RSAPrivateKey):
            algorithm = "rsa-sha256"
            signature = key.sign(signing_string, padding.PKCS1v15(), hashes.SHA256())
        elif isinstance(key, ec.EllipticCurvePrivateKey):
            algorithm = "ecdsa-sha256"
            signature = key.sign(signing_string, ec.ECDSA(hashes.SHA256()))
        else:
            raise SigningError(f"Toetamata votmetuup: {type(key).__name__}")

        return (
            f'keyId="{self.compute_key_id()}",'
            f'algorithm="{algorithm}",'
            f'headers="{" ".join(used)}",'
            f'signature="{base64.b64encode(signature).decode()}"'
        )


def signing_string_preview(headers: dict[str, str]) -> str:
    """Mida taipselt allkirjastatakse - silumiseks, kui pank utleb 'vale allkiri'."""
    lower = {k.lower(): v for k, v in headers.items()}
    return "\n".join(f"{h}: {lower[h]}" for h in SIGNED_HEADERS if lower.get(h))
