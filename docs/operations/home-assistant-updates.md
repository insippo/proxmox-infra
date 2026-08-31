# Garaaži Home Assistanti uuendamine

Tööjuhend **Garaaž HA** instantsi (Proxmoxis VM-ina jooksev Home Assistant OS)
ja selle hallatavate Zigbee/Wi-Fi seadmete uuendamiseks.

Home Assistant teatab ootel uuendustest ühe teavitusega, näiteks:

> 🔧 Garaaž HA — uuendusi ootel
> 11 uuendust: Home Assistant Core, Home Assistant Operating System, Zigbee2MQTT, …

See teavitus **ei ole** korraldus vajutada „Uuenda kõik". Uuendused paigaldatakse
kindlas järjekorras, üks kiht korraga, ja taastetee peab olema paigas enne, kui
esimenegi neist algab.

## Reeglid

- **Mitte kunagi ei uuenda kõike korraga.** Üks kiht korraga, kontrolli, siis edasi.
- **Ära uuenda püsivara seadmel, milleni sa füüsiliselt ei ulatu.** Ebaõnnestunud
  Shelly välkimine võib nõuda voolu väljalülitamist või tehaseseadete taastamist
  seadme juures kohapeal.
- **Ära uuenda, kui koormus on kasutuses.** Printeri toitelülitit ei puututa
  printimise ajal.
- **Loe väljalaskemärkmeid enne Core'i ja Zigbee2MQTT-d.** Mõlemad toovad
  tavaväljalasetes murdvaid muudatusi.
- **Ära alusta uuendust, mida sa ei suuda lõpuni oodata.** Iga alljärgnev samm
  lõpeb omas tempos, mitte sinu omas. Vaata *Ajaeelarve*.
- **Üks uuendussessioon, üks logikanne.** Vaata
  `docs/operations/home-assistant-update-log.md`.

## Ajaeelarve

**Planeeri pool päeva, mitte tund.** Need uuendused on aeglased ja suurem osa
kuluvast ajast on ootamine, mitte klikkimine. Kiirustamine on see, mis muudab
rutiinse uuenduse rikkeks: tüüpiline ebaõnnestumine on operaator, kes otsustab,
et miski on kinni jooksnud, teeb keset operatsiooni restardi või võtab voolu ära
— ja lõhub asja päriselt.

| Samm | Reaalne aeg | Mis seda määrab |
| --- | --- | --- |
| 0 – Varukoopia + snapshot | 10–30 min | Varukoopia suurus, väljakopeerimine VM-ist |
| 1 – Core | 10–20 min, **pluss AB migratsioon** | Vaata allpool — migratsioon võib kesta tunde |
| 2 – OS | 15–30 min | Allalaadimine, alglaadimine, aeglasem esimene boot |
| 3 – Lisandid | 5–15 min igaüks | Z2M võrgu settimine tuleb lisaks, vaata allpool |
| 4 – Better Thermostat | 5 min, pluss üks küttetsükkel | Kalibratsioon taastub tasapisi |
| 5 – Shelly püsivara | 5–10 min seadme kohta | Alglaadimine ja Wi-Fi taasühendus iga seadme kohta |

Täielik settimine — kõik seadmed jälle normaalselt raporteerimas — võib pärast
viimast muudatust võtta **kuni 24 tundi**. Ära hinda tulemust esimese kümne
minuti järgi.

**Partii jagamine mitmele päevale on normaalne ja eelistatud.** Ei ole nõuet
kõiki ootel uuendusi ühe korraga ära teha. Core ja OS ühes sessioonis, lisandid
teises, seadmete püsivara kolmandas on täiesti korralik plaan — ja nii on ka
selgelt näha, milline muudatus probleemi tekitas.

Ära alusta õhtul, kui garaaži on järgmisel hommikul vaja, ja ära alusta
eemalt.

## Samm 0 – Taastetee (kohustuslik)

Tee see ära, enne kui midagi puutud.

1. **Home Assistanti varukoopia**: Seaded → Süsteem → Varukoopiad →
   *Loo varukoopia* (täielik). Veendu, et see lõppes edukalt, ja pane suurus kirja.
2. **Kopeeri varukoopia VM-ist välja.** Varukoopia, mis on olemas ainult selle
   VM-i sees, mida sa kohe lõhkuma hakkad, ei ole varukoopia.
3. **Proxmoxi hetktõmmis (snapshot)** HA VM-ist, tehtud töötava VM-i pealt:

   ```bash
   # Proxmoxi hostil, <vmid> = Home Assistanti VM
   qm snapshot <vmid> pre-ha-update-$(date +%Y%m%d) --description "enne HA uuenduste partiid"
   ```

4. **Zigbee2MQTT koordinaatori varukoopia**: Z2M kirjutab igal käivitusel oma
   andmekataloogi faili `coordinator_backup.json`. Veendu enne Z2M uuendamist,
   et see on olemas ja värske.

Tagasikerimine = taasta Proxmoxi snapshot (kogu seade) või taasta HA varukoopia
(ainult konfiguratsioon). Kustuta snapshot, kui oled veendunud, et kõik töötab —
kettale jäetud snapshotid kasvavad ja rikuvad `docs/storage-policy.md` reegleid.

## Samm 1 – Home Assistant Core

Loe väljalaskemärkmed **iga** versiooni kohta paigaldatu ja sihtversiooni vahel,
eriti jaotist „Breaking changes".

Seaded → Süsteem → Uuendused → *Home Assistant Core* → Uuenda.
Jäta „Loo enne uuendamist varukoopia" sisse lülitatuks.

**Enne Core'i uuendamist kontrolli kohandatud integratsioone.** Kohandatud
komponendid on tavaline põhjus, miks HA pärast Core'i uuendust ei käivitu.
Selles instantsis tähendab see **Better Thermostati** (HACS) ja **Home Assistant
MCP Serverit**: veendu, et versioon, kuhu liigud, toetab sihtversiooni Core'ist.
Kui ei toeta, uuenda kõigepealt integratsiooni või hoia Core tagasi.

**Recorderi andmebaasi migratsioon on aeglane osa.** Mõned Core'i väljalasked
muudavad recorderi skeemi ja migreerivad andmebaasi *pärast* seda, kui HA on
juba käivitunud. Migratsiooni ajal on HA kättesaadav, aga aeglane, ning ajalugu
ja logiraamat on puudulikud. Pikalt kasutusel olnud andmebaasi puhul kestab see
mõnest minutist mitme tunnini. **Ära tee HA-le restarti ega VM-ile
alglaadimist, kui see käib** — katkestatud migratsioon on see, kuidas andmebaas
rikutuks saab. Jälgi logist, kuni migratsioon teatab lõpetamisest; alles siis
hinda, kas uuendus õnnestus.

Kontroll: HA käivitub, Seaded → Süsteem → Parandused on puhas, garaaži
automaatikad on endiselt saadaval (`unavailable` olekus olemeid ei ole). Anna
olemitele paar minutit taastumiseks, enne kui pead `unavailable` olekut rikkeks.

## Samm 2 – Home Assistant Operating System

Seaded → Süsteem → Uuendused → *Home Assistant Operating System* → Uuenda.

See teeb kogu seadmele alglaadimise. Arvesta, et VM on mitu minutit
kättesaamatu — kõigepealt käib allalaadimine, siis alglaadimine, ja esimene boot
uue OS-i versiooniga on tavalisest aeglasem. **Ära peata VM-i Proxmoxist jõuga
sellepärast, et kasutajaliides pole veel tagasi tulnud** — anna vähemalt 15
minutit, enne kui pead seda kinnijooksnuks. Ära tee seda sammu eemalt, kui sa ei
pääse Proxmoxi konsoolile.

Kontroll: VM käivitub, HA kasutajaliides tuleb tagasi, Seaded → Süsteem →
Riistvara näitab endiselt Zigbee koordinaatorit (siin tuleb jälgida just seda,
et USB läbiandmine ei kaoks pärast alglaadimist märkamatult ära).

## Samm 3 – Lisandid

Uuenda ükshaaval, kontrollides iga uuenduse järel:

1. **Zigbee2MQTT** — kõige suurema riskiga lisand. Veendu, et
   `coordinator_backup.json` on värske (samm 0), loe Z2M väljalaskemärkmetest
   konfiguratsiooni migratsioonide kohta ja siis uuenda. Kontroll: lisand
   käivitub ja edasi-tagasi käsklus töötab (lülita HA-st mõnda võrgutoitel
   seadet ja vaata, kas olek tuleb tagasi).

   **Ära oota kogu Zigbee võrku kohe tagasi.** Võrgutoitel ruuterid liituvad
   uuesti mõne minutiga. Patareitoitel seadmed raporteerivad alles siis, kui nad
   järgmine kord ärkavad — see võib võtta tunde. Patareiandur, mis on samal
   õhtul veel `unavailable`, on normaalne ega tõenda, et uuendus ebaõnnestus.
   Ära seo esimesel päeval midagi uuesti: seadme uuesti sidumine, mis oleks
   niikuinii ise tagasi tulnud, ainult halvendab mesh-võrku.
2. **Grafana** — madal risk. Kontroll: töölauad renderduvad ja Prometheuse
   andmeallikas on endiselt ühendatud (vaata `monitoring/grafana/README.md`).
3. **Home Assistant MCP Server** — kontrolli, et MCP klient suudab pärast
   taaskäivitust endiselt tööriistu loetleda.

## Samm 4 – Kohandatud integratsioonid (HACS)

**Better Thermostat**: uuenda HACS-i kaudu, seejärel taaskäivita Home Assistant.
Kontrolli, et kliimaolemid on tagasi ega ole jäänud `unavailable` olekusse.

Better Thermostat hoiab kalibratsiooniolekut, mis taastub pärast taaskäivitust,
ja see võtab terve küttetsükli — ventiili asend võib esimestel minutitel pärast
taaskäivitust vale välja näha, ja see on ootuspärane, mitte rike. Kontrolli, et
seatud temperatuur jõuab tegelikult ventiilini, ja jäta siis üheks tsükliks
rahule, enne kui midagi järeldad.

## Samm 5 – Shelly seadmete püsivara (viimasena, ükshaaval)

Seadmete püsivara uuendatakse **pärast** seda, kui platvormi tervis on
kinnitatud, mitte kunagi samas käigus. Ebaõnnestunud välkimine jätab seadme
võrgust välja, kuni sellel käsitsi voolu ei katkestata.

Iga seadme puhul: vaata, mida see juhib, veendu, et koormus on jõude, uuenda,
oota, kuni seade tagasi tuleb, kontrolli, et see HA-st vastab. Alles siis järgmine.

**Oota iga seade lõpuni ära, enne kui järgmisega alustad.** Shelly teeb pärast
välkimist alglaadimise ja ühendub Wi-Fi-ga uuesti, mis võtab mõne minuti;
Gen3 kaheastmeline uuendus võtab kauem ja võib vahepeal surnud välja näha.
**Ära kunagi katkesta voolu Shellyl, mille uuendus on pooleli** — see on ainus
kindel viis see ära rikkuda. Arvesta 5–10 minutit seadme kohta ja ära tee neid
partiidena.

Praegused garaaži seadmed:

| Seade | Mudel | Mida juhib | Eeltingimus |
| --- | --- | --- | --- |
| `K1 Max – kapi vent` | Shelly 1 Mini | Kapi ventilaator | Printer jõude ja jahtunud |
| `K1 Max – printeri toide` | Shelly 1PM | Printeri võrgutoide | **Ükski print ei tohi käia.** Voolu katkestamine keset printimist hävitab töö |
| `Kapi all lambid` | Shelly 1 Mini | Kapialused valgustid | Keegi ei tööta kapi juures |
| `shelly1minig3-54320468c06c` | Shelly 1 Mini Gen3 | Tuvastamata — **tuvasta enne uuendamist** | Koormus teada ja jõude |
| `shelly1minig3-dcda0ce25a78` | Shelly 1 Mini Gen3 | Tuvastamata — **tuvasta enne uuendamist** | Koormus teada ja jõude |

Kaks seadet kannavad endiselt tehase hostinimesid. Anna neile Home Assistantis
nimed, enne kui neid uuendad — nimetu relee on tundmatu koormus, ja tundmatu
koormuse uuendamine on täpselt see, kuidas printer keset tööd voolu kaotab.

## Samm 6 – Lõpetamine

1. Veendu, et Seaded → Süsteem → Uuendused on tühi (või et allesjäänu on
   teadlikult tagasi hoitud ja põhjus on logitud).
2. Vaata üle Seaded → Süsteem → Parandused ja vealogi.
3. Kustuta sammus 0 tehtud Proxmoxi snapshot.
4. Lisa kanne faili `docs/operations/home-assistant-update-log.md`.

## Aeglane ei tähenda katki

Enamik „uuendus lõhkus kõik ära" teateid on operaator, kes sekkus liiga vara.
Enne kui midagi ette võtad, vaata, kas see, mida sa näed, on siin nimekirjas:

| Mida sa näed | Kaua on normaalne oodata, enne kui see on probleem |
| --- | --- |
| HA aeglane, ajaloos augud pärast Core'i uuendust | Kuni recorderi migratsioon lõpeb — minutid kuni tunnid. Ära tee restarti |
| VM kättesaamatu pärast OS-i uuendust | ~15 min, sh allalaadimine ja aeglane esimene boot |
| Olemid `unavailable` kohe pärast taaskäivitust | Paar minutit, kuni need taastuvad |
| Patareitoitel Zigbee seadmed puudu pärast Z2M uuendust | Kuni nad järgmine kord ärkavad — sageli tunnid. Ära seo uuesti |
| Ventiili asend paistab vale pärast Better Thermostati | Üks täielik küttetsükkel |
| Shelly võrgust väljas kohe pärast välkimist | Mitu minutit. Ära vahepeal voolu katkesta |

Kui pärast ootamist on ikka valesti, siis on tegu rikkega — vaata allpool.

## Kui midagi läheb katki

| Sümptom | Tegevus |
| --- | --- |
| HA ei käivitu pärast Core'i uuendust | Taasta HA varukoopia või keri Core käsurealt tagasi: `ha core update --version <eelmine>` |
| Kogu seade kättesaamatu pärast OS-i uuendust | Proxmoxi konsool; kui ei taastu, taasta sammu 0 snapshot |
| Kõik Zigbee seadmed kadunud pärast Z2M uuendust | Taasta `coordinator_backup.json` ja fikseeri eelmine Z2M versioon |
| Zigbee koordinaator puudu pärast alglaadimist | Kontrolli Proxmoxis VM-i USB läbiandmist, enne kui midagi uuesti seod |
| Shelly võrgust väljas pärast püsivara uuendust | Katkesta kaitsmest vool; kui ikka surnud, tee tehaseseadete taastamine ja lisa uuesti |
