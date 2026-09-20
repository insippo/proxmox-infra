# SEB pangaliides – maksete ettevalmistamine

Staatus: **kood valmis, API-tee ootab lepingut ja sertifikaate.**
Kood: `payments/` · Kasutusjuhend: `payments/README.md`

## Miks see dokument olemas on

"Kas saab panga liidese teha?" on tegelikult kaks küsimust:

1. Kas tehniliselt saab? – **Jah.** SEB Baltics pakub XS2A API-t
   (Berlin Group NextGenPSD2 standard). Kood selle vastu on olemas.
2. Kas sina saad seda kohe kasutada? – **Ei, mitte enne kui paberid on
   korras.** Juurdepääs ei sõltu koodist, vaid lepingust ja
   sertifikaatidest.

Seetõttu on ehitatud kaks teed ühe andmemudeli peale.

## Kaks teed

### Tee A – pain.001 fail (töötab kohe)

```
CSV → kontroll → pain.001 XML → internetipank (import) → sinu allkiri → pank
```

ISO 20022 `pain.001.001.03` on SEPA maksekorralduse standardformaat.
Seda aktsepteerivad SEB, Swedbank, LHV ja Coop Pank.

**Ei vaja lepingut, API-võtit ega litsentsi.** Sa lood faili, impordid
selle internetipanka, vaatad summa üle ja allkirjastad.

See on see, mida 95% Eesti väikeettevõtetest tegelikult vajab.

### Tee B – SEB XS2A API (ootab sertifikaate)

```
CSV → kontroll → POST /v1/payments → paymentId + SCA link
    → Smart-ID / Mobiil-ID → GET .../status → ACCP
```

Vahe teega A: makse jõuab panka ilma failita ja staatust saab
programmaatiliselt küsida. Allkirjastamine (SCA) jääb ikka inimesele –
seda ei saa ega tohi automatiseerida.

## Mida tee B nõuab

| # | Nõue | Kust |
|---|------|------|
| 1 | Konto arendajaportaalis | developer.baltics.sebgroup.com |
| 2 | Registreeritud APP → `client_id` / `client_secret` | sama portaal |
| 3 | **QWAC** – eIDAS veebisertifikaat (mTLS kanal) | kvalifitseeritud usaldusteenuse pakkuja |
| 4 | **QSEALC** – eIDAS pitsersertifikaat (sõnumi allkiri) | sama pakkuja |
| 5 | Õiguslik alus – kas PSD2 PISP litsents või SEB ärikliendi API-leping | Finantsinspektsioon / SEB ärikliendihaldur |

Punkt 5 on see, mis enamasti otsustab. Kolmanda osapoolena (TPP) teiste
inimeste kontodele makseid algatada tohib ainult litsentsiga. **Oma
ettevõtte enda kontole** ligipääsuks ei ole vaja PSD2 litsentsi, vaid
ärikliendi lepingut – küsi see SEB-st, mitte portaalist.

Sandbox (testkeskkond) on kättesaadav enne punkte 3–5, testandmetega
kontodel. Sinna tasub päris koodiga ära käia enne, kui sertifikaatide
eest maksad.

## Mis koodis on

```
payments/
├── bankprep/
│   ├── models.py     – Payment / PaymentBatch + kõik SEPA piirangud
│   ├── iban.py       – IBAN mod-97, BIC, SEPA riigid
│   ├── reference.py  – viitenumber 7-3-1 ja RF (ISO 11649)
│   ├── batch.py      – CSV sisselugemine, kõik vead korraga
│   ├── pain001.py    – ISO 20022 XML generaator            ← tee A
│   ├── seb_xs2a.py   – Berlin Group klient + dry-run       ← tee B
│   ├── signing.py    – Digest + cavage HTTP Signature (QSEALC)
│   ├── config.py     – bank.toml lugemine, valmisoleku kontroll
│   └── cli.py        – käsurida
├── tests/            – 38 testi, ei vaja võrku
└── examples/         – näidis-CSV ja näidis-config
```

Andmemudel on ühine: sama `PaymentBatch` läheb kas XML-i või JSON-i.
Kontrollid tehakse enne mõlemat – vigane IBAN ei jõua kummalegi teele.

## Turvaotsused ja miks need nii on

**Dry-run on vaikimisi.** `submit` kirjutab päringu faili, mitte panka.
Päris saatmiseks peavad kokku langema kolm asja: `allow_live = true`
config-failis, `--confirm` käsureal ja kehtivad sertifikaadid. Üks neist
üksi ei tee midagi.

**Saladusi ei hoita config-failis.** Seal on ainult failitee või
keskkonnamuutuja nimi. `bank.toml`, `secrets/`, `*.pem` ja `*.key` on
`.gitignore`-s.

**Logides ei ole saladusi.** Salvestatud päringutes on `Authorization`,
`Signature`, `TPP-Signature-Certificate` ja `PSU-ID` maskeeritud.

**Float on keelatud.** Summa `19.90` float-ina ei ole `19.90`. Kood
viskab float-i puhul vea ja nõuab stringi või `Decimal`-it.

**Viitenumber võidab selgituse.** ISO 20022 ei luba mõlemat korraga.
Kui mõlemad on antud, jääb viitenumber – selle järgi seotakse arve.

**SCA-d ei automatiseerita.** Kui tööriist suudaks makse ise lõpuni
kinnitada, oleks murtud konto = tühi konto. Viimane samm jääb inimesele.

## Kontrollimata kohad

Selle töö tegemise ajal oli `developer.baltics.sebgroup.com` võrgufiltri
taga, nii et **täpseid endpoint-teid ei saanud portaalist üle kontrollida.**
Kood järgib Berlin Group NextGenPSD2 standardit ja kõik hostinimed ning
teed on seadistatavad (`bank.toml` → `base_url`, `payment_service`,
`payment_product`). Enne sandbox-katset võrdle need portaali
dokumentatsiooniga üle – see on 5 minuti töö ja säästab tunni
veaotsingut.

## Tagasipööramine

| Mida tagasi | Kuidas |
|-------------|--------|
| Kogu funktsionaalsus | `git rm -r payments/ docs/payments/` – midagi muud ei sõltu sellest |
| Üks jooks | kustuta `out/` kataloog |
| API-ligipääs | `allow_live = false` – kohe |
| Sertifikaadid | kustuta `secrets/` – kood langeb tagasi pain.001 teele |
| Pangas kinnitatud makse | **tarkvara ei tagasta** – helista panka enne täitmispäeva |

See kataloog ei puutu Proxmoxi, Ansible'i ega Terraformi. Selle
eemaldamine ei mõjuta ühtegi masinat.

## Edasi – järjekorras

1. Tee `bank.toml`, jooksuta `prepare` päris arvete peal, impordi
   internetipanka. **See annab kasu kohe.**
2. Tee konto arendajaportaalis, registreeri APP, katseta sandboxis
   (`allow_live = true` ainult sandbox-keskkonnas).
3. Räägi SEB ärikliendihalduriga: mis leping on vaja sinu enda konto
   API-ligipääsuks ja mis see maksab.
4. Alles siis sertifikaadid – need maksavad raha ja aeguvad.
