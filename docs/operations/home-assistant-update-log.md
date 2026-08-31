# Home Assistanti uuenduste logi — Garaaž HA

Üks kanne uuendussessiooni kohta. Protseduur:
`docs/operations/home-assistant-updates.md`.

Pane kirja, mis sai paigaldatud, mis jäi tagasi hoituks ja miks, ning mis läks
katki. Uuendust, mida ei ole logitud, ei ole toimunud.

Kande mall:

```
## AAAA-KK-PP

**Ootel:** <arv> — <loend>
**Paigaldatud:** <loend, järjekorras>
**Tagasi hoitud:** <loend + põhjus>
**Märkused:** <mis läks katki, mis sai kontrollitud, snapshot kustutatud jah/ei>
```

---

## 2026-08-31 — ootel, veel paigaldamata

Teavitus: *„🔧 Garaaž HA — uuendusi ootel — 11 uuendust"*.

**Ootel (11):**

| # | Uuendus | Kiht | Risk | Järjekord |
| --- | --- | --- | --- | --- |
| 1 | Home Assistant Core | Core | Kõrge — murdvad muudatused, kohandatud integratsioonid | Samm 1 |
| 2 | Home Assistant Operating System | OS | Keskmine — täielik alglaadimine, USB läbiandmine | Samm 2 |
| 3 | Zigbee2MQTT | Lisand | Kõrge — konfiguratsiooni migratsioonid, Zigbee võrk | Samm 3 |
| 4 | Grafana | Lisand | Madal | Samm 3 |
| 5 | Home Assistant MCP Server | Lisand | Madal — kontrolli enne Core'iga ühilduvust | Samm 3 |
| 6 | Better Thermostat | HACS kohandatud integratsioon | Kõrge — puruneb Core'i uuendustel | Samm 4 (kontrolli enne sammu 1) |
| 7 | `K1 Max – kapi vent` (Shelly 1 Mini) | Seadme püsivara | Keskmine | Samm 5 |
| 8 | `K1 Max – printeri toide` (Shelly 1PM) | Seadme püsivara | **Kõrge — printeri võrgutoide** | Samm 5, ainult jõude printeriga |
| 9 | `Kapi all lambid` (Shelly 1 Mini) | Seadme püsivara | Keskmine | Samm 5 |
| 10 | `shelly1minig3-54320468c06c` | Seadme püsivara | Tundmatu koormus | Samm 5, tuvasta enne |
| 11 | `shelly1minig3-dcda0ce25a78` | Seadme püsivara | Tundmatu koormus | Samm 5, tuvasta enne |

**Paigaldatud:** veel mitte ühtegi.

**Takistused / eeltingimused:**

- Varukoopia ja Proxmoxi snapshot tegemata (samm 0).
- Better Thermostati ühilduvus sihtversiooniga Core'ist kontrollimata.
  Kontrolli enne #1 paigaldamist.
- Seadmed #10 ja #11 kannavad endiselt tehase hostinimesid. Tuvasta ja nimeta
  need Home Assistantis, enne kui neid välgud.

**Planeeritud sessioonid:** mitte ühe korraga. Soovitatav jaotus — sessioon A:
#1–#2 (Core + OS, pikad; ainuüksi recorderi migratsiooniks arvesta pool päeva);
sessioon B: #3–#6 (lisandid + Better Thermostat); sessioon C: #7–#11 (Shelly
püsivara, kohapeal, üks seade korraga). Jaotamine teeb selgeks, milline muudatus
probleemi tekitas.

**Märkused:** Shelly püsivara uuendused (#7–#11) nõuavad füüsilist ligipääsu
garaažile. Ära alusta seda sammu eemalt. Arvesta pärast viimast muudatust kuni
24 tundi, enne kui partii valmiks loed — patareitoitel Zigbee seadmed
raporteerivad alles siis, kui nad järgmine kord ärkavad.
