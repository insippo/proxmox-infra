"""bankprep - maksete ettevalmistamine (SEPA / ISO 20022 / SEB XS2A).

See pakett EI TEE makseid. Ta valmistab maksed ette:
  - valideerib (IBAN, viitenumber, summa, tekstipiirangud)
  - koostab pain.001.001.03 XML-i (panka importimiseks)
  - valmistab ette SEB XS2A (Berlin Group NextGenPSD2) paringu

Lopliku allkirja ja kinnituse annab alati inimene internetipangas.
"""

__version__ = "0.1.0"

from bankprep.models import Payment, PaymentBatch, Party  # noqa: F401
