# bankprep – maksete ettevalmistamine

Tööriist, mis võtab maksete nimekirja (CSV), kontrollib selle üle ja
valmistab panga jaoks ette. **Raha ei liigu kunagi ilma sinu allkirjata.**

Kaks teed, mõlemad sama andmemudeli peal:

| Tee | Mida vajad | Mida saad |
|-----|-----------|-----------|
| **pain.001 fail** | mitte midagi | XML, mille impordid internetipanka ja allkirjastad |
| **SEB XS2A API** | PSD2 leping + eIDAS sertifikaadid | makse läheb otse panka SCA-kinnitusele |

Alusta esimesest. Teine on koodis valmis ja ootab ainult sertifikaate.

## Kiire algus

```bash
cd /path/to/proxmox-infra
cp payments/examples/config.example.toml bank.toml
nano bank.toml          # pane sisse oma ettevõtte nimi ja IBAN

export PYTHONPATH=payments        # või: pip install -e payments

# kontrolli, mis on olemas ja mis puudu
python3 -m bankprep check

# kontrolli maksete faili ilma midagi tegemata
python3 -m bankprep validate payments/examples/payments.csv

# tee pain.001 XML
python3 -m bankprep prepare payments/examples/payments.csv
```

`pip install -e payments` järel töötab ka lihtsalt `bankprep <käsk>`.

Tulemus läheb `out/` kataloogi: XML + JSON-aruanne kontrollsummadega.

## CSV vorming

Veerunimed võivad olla eesti või inglise keeles, järjekord ei loe:

```csv
saaja_nimi,saaja_iban,saaja_bic,summa,viitenumber,selgitus,viide_id,kuupaev
Tarnija AS,EE471000001020145685,,1250.00,123453,,ARVE-2026-001,2026-09-25
```

Kohustuslikud on `saaja_nimi`, `saaja_iban`, `summa`. Ülejäänud on valikulised.

Eraldaja võib olla koma, semikoolon või tabulaator – tuvastatakse ise.
Summa võib olla `19.90` või `19,90`.

## Mida tööriist sinu eest kontrollib

- **IBAN** – mod-97 kontroll + riigi pikkus + SEPA piirkond
- **Viitenumber** – Eesti 7-3-1 kontrollnumber või RF-viide (ISO 11649)
- **Summa** – positiivne, täpselt 2 kohta, mitte kunagi float
- **Tähestik** – `õ ä ö ü š ž` → SEPA tähestik (pank ei võta muud vastu)
- **Pikkused** – nimi 70, selgitus 140, viite-ID 35 märki
- **Iseendale maksmine** – saaja IBAN ei tohi olla sama mis maksja oma
- **Topeltviited** – korduv viite-ID on hoiatus, mitte vaikiv viga

Vead kogutakse kokku ja antakse ühe nimekirjana – sa ei paranda faili
viis korda järjest.

## Käsud

```
python3 -m bankprep check                  seadistuse seis
python3 -m bankprep validate maksed.csv    ainult kontroll
python3 -m bankprep prepare  maksed.csv    pain.001 XML + aruanne
python3 -m bankprep submit   maksed.csv    SEB XS2A päring (dry-run)
python3 -m bankprep status   <paymentId>   makse staatus pangas
python3 -m bankprep ref 2026001            arvuta viitenumber
python3 -m bankprep ref 2026001 --rf       RF-viide
```

## Turvalukud

Neid on kolm ja nad on meelega tüütud:

1. `bank.toml` → `[seb] allow_live = false` – vaikimisi ei lähe ükski
   päring panka, vaid kirjutatakse faili `out/requests/`.
2. `--confirm` – ilma selleta on `submit` alati dry-run.
3. SCA – ka siis, kui mõlemad eelmised on läbitud, ootab makse pangas
   sinu Smart-ID/Mobiil-ID kinnitust. Tööriist ei saa seda asendada.

Saladused (`client_secret`, sertifikaadid) ei ole kunagi config-failis
endas – seal on ainult failitee või keskkonnamuutuja nimi. Salvestatud
päringutes on `Authorization`, `Signature` ja `PSU-ID` maskeeritud.

## Testid

```bash
python3 -m unittest discover -s payments/tests -t payments
```

38 testi, ei vaja võrku ega sertifikaate.

## Tagasipööramine

See kataloog ei puutu Proxmoxi, Ansible'i ega Terraformi. Kõik, mida ta
teeb, on failide lugemine ja kirjutamine `out/` kataloogi.

- **Kood maha:** `git rm -r payments/ docs/payments/` või lihtsalt jäta
  haru mergimata.
- **Ühe jooksu tagasi:** kustuta `out/` kataloog. Midagi muud ei muutunud.
- **API-tee kinni:** `allow_live = false` – kohe ja täielikult.
- **Pangas juba kinnitatud makse:** seda tarkvara ei tagasta. SEPA
  kreeditkorraldust saab tühistada ainult pank ja ainult enne
  täitmist – helista panka.

## Mis on veel vaja teha (API-tee)

Vt `docs/payments/seb-liides.md`. Lühidalt: SEB portaali konto, APP,
eIDAS sertifikaadid ja leping. Ilma nendeta on pain.001 tee täiesti
piisav – seda kasutavad enamik Eesti väikefirmasid.
