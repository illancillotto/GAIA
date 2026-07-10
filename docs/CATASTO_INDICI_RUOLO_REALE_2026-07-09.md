# Catasto Indici: importi ruolo reali, normalizzazione distretti e quadro distretti

Data intervento: 2026-07-09.

Interventi sulla pagina `/catasto/indici` e sui servizi collegati, a valle del
ripopolamento ruolo 2025 da inCASS (vedi `INCASS_RIPOPOLAMENTO_2025_ESITO_2026-07-03.md`).

## 1. Importo ruolo reale al posto della stima tariffaria

La pagina mostrava un "Importo stimato" calcolato da `build_irrigation_tariff_preview`
(tariffa teorica EUR/ha per gruppo coltura). Ora il servizio
`app/modules/catasto/services/indici_overview.py` aggrega gli importi reali del ruolo
(`importo_manut`, `importo_irrig`, `importo_ist` da `ruolo_particelle`) e li espone come
`importo_ruolo` (+ scomposizione nelle tre voci a livello indice) su indici, comuni,
distretti e colture. La stima tariffaria resta nell'API come campo secondario
(`importo_stimato`) ma non e piu il dato principale a FE.

## 2. Superficie irrigata: somma delle porzioni

Quando una particella compare in piu partite nello stesso anno, le superfici irrigate
sono porzioni distinte (verificato: 541 casi su 664 con valori diversi, mai oltre la
superficie catastale). L'aggregazione per particella ora somma le porzioni invece di
prendere il massimo.

## 3. Normalizzazione codici distretto

Nei dati sorgente lo stesso distretto compare con codifiche diverse:

- senza zero iniziale: `8` per `08` (tutti i distretti 1-9);
- suffissi numerici per le zone Terralba: `291/292/293` per `29a/29b/29c`;
- righe duplicate in `cat_distretti` per le zone Terralba (sia `29a` sia `291`).

Prima della normalizzazione tutti i distretti 1-9 finivano in "Non classificato"
(la canaletta mostrava 2 distretti invece di 3: mancava `08 Pauli Bingias`).

Fix in `app/modules/catasto/services/indici.py`:

- `normalize_num_distretto()`: zero-padding, alias `291->29a` ecc.;
- `get_indice_metadata()` normalizza prima del lookup nel catalogo;
- `expand_distretto_code_variants()` / `list_distretti_for_indice()` espandono le
  varianti per i filtri SQL (usati dalla route particelle);
- l'overview deduplica le righe `cat_distretti` per codice normalizzato e fonde le
  analytics per distretto sulla chiave normalizzata.

Verifica contro la tabella ufficiale (foto quadro distretti, 2026-07-09): 37/37 codici
presenti nel catalogo e nel DB, classificazioni tutte corrette
(26 alta pressione, 8 bassa pressione, 3 canaletta: 08, 11, 18).

## 4. Nomi distretto normalizzati in DB

Allineati al quadro ufficiale (update su `cat_distretti` + `cat_particelle`):

- distretto `2`: "Santa Maria Marefoghe" -> "Santa Maria Mare Foghe" (6.020 particelle);
- distretto `8`: "Zinnigas Lorissa Pauli Bingias Sud" -> "Pauli Bingias" (4.590 particelle).

Attenzione: un re-import shapefile puo reintrodurre i vecchi nomi/codici; la
normalizzazione runtime li riclassifica comunque. Restano varianti minori sui nomi di
19, 20, 28, 31, 34 (solo etichette).

## 5. Riconciliazione con la determina 2025

Codici tributo partitario: `0648` manutenzione, `0985` istituzionale, `0668` irriguo.

| Tributo | Determina | Ruolo emesso (avvisi) | Scomposto per particella |
|---|---:|---:|---:|
| Istituzionale | 900.000,00 | 904.767,61 | 792.510,72 |
| Manutenzione | 1.260.000,00 | 1.255.802,41 | 1.096.968,74 |
| Irriguo | 1.350.000,00 | 1.333.861,13 | 511.049,69 |
| Totale | 3.510.000,00 | 3.494.431,15 | 2.400.529,15 |

Il ruolo emesso quadra con la determina (-0,4%). La scomposizione per particella
(quella usata dalla pagina Indici) cattura il 69% del totale: il partitario non
dettaglia per particella circa 1,09 MEUR, quasi tutto tributo irriguo:

- ~407 kEUR ad Arborea (acqua a misura: quota a consumo su partita, non su particella);
- ~473 kEUR di cattura parziale su 3.825 partite (conguagli/righe non per-particella);
- ~270 kEUR su 327 partite con solo righe riepilogo;
- ~70 kEUR su 100 partite senza righe particella.

In piu, dei 2,40 MEUR scomposti, 2,23 MEUR arrivano nei totali per indice perche sono
attribuibili al catasto corrente Agenzia Entrate con distretto valorizzato. Il resto
resta fuori dagli indici e viene mostrato in pagina come riconciliazione separata, non
come attribuzione territoriale:

- 5.577 righe ruolo / 5.028 particelle ruolo distinte su particelle correnti senza
  distretto: 103.317,11 EUR;
- 2.922 righe ruolo / 2.815 particelle ruolo distinte non collegate a `cat_particelle`:
  65.890,58 EUR;
- totale escluso dagli indici: 8.499 righe ruolo / 7.843 particelle ruolo distinte,
  169.207,69 EUR.

Quadratura pagina (anno 2025, snapshot `v=6`):

| Indice | Distretti | Part. a ruolo | Sup. irrigata (ha) | Importo ruolo |
|---|---:|---:|---:|---:|
| Alta pressione | 26 | 61.563 | 5.389,77 | 1.810.887,19 |
| Bassa pressione | 8 | 6.565 | 1.609,10 | 320.124,77 |
| Canaletta | 3 | 9.112 | 784,66 | 92.608,43 |
| Non classificato | 10 | 454 | 73,80 | 7.701,07 |
| Totale | 47 | 77.694 | 7.857,32 | 2.231.321,46 |

## 6. Non classificato

Composizione: aree `FD`/`FD_1..FD_7` (fuori distretto: servite dai sistemi irrigui ma
non incluse in un distretto, tributo non dovuto formalmente - cfr. PRD catasto),
`50 Canali adduttori` e codici legacy. Le 454 particelle FD a ruolo (7,7 kEUR) sono
anomalie da verificare. A FE un banner spiega il blocco quando selezionato.

## 7. Frontend

- Card "Importo ruolo" (reale, con scomposizione manut/irrig/ist) al posto della stima;
  KPI EUR/ha e ranking su importo ruolo.
- Card "Distretti coperti" = 37 classificati, con nota sui raggruppamenti fuori quadro.
- "Colture prevalenti" e "Approfondimenti operativi" affiancati su una riga.
- Nuova sezione "Quadro distretti" al posto del drill-down particelle: tabella
  indice/numero/nome come il quadro ufficiale + dati ruolo per distretto, riga di
  totale, export Excel (`distretti-indici-<anno>.xlsx`, SheetJS).
- La tabella "Quadro distretti" espone anche gli ettari di riferimento e la
  scomposizione degli importi ruolo per distretto: `0648 Manut.`, `0668 Irrig.`,
  `0985 Ist.`. Le stesse colonne sono incluse nell'export Excel.
- Il filtro indice della tabella e un gruppo di chip selezionabili (`Tutti`, alta
  pressione, bassa pressione, canaletta, non classificato se presente), non una select.
  I totali e l'export seguono sempre il filtro corrente.
- Tutte le intestazioni della tabella sono ordinabili con stato ascendente/discendente
  e indicatori `▲/▼`; l'ordinamento conserva un fallback stabile sul numero distretto.
- Nuova sezione "Riconciliazione ruolo": parte da `ruolo_particelle`, confronta il
  totale ruolo particellare con la quota inclusa negli indici, mostra la quota esclusa
  e spiega i motivi (`non_collegata`, `catasto_non_corrente_o_assente`,
  `senza_distretto`). Il testo chiarisce che la differenza non modifica i totali per
  indice: gli indici restano basati sul catasto corrente AE.
- Dal 2026-07-10 la card "Escluso dagli indici" espone anche il dettaglio operativo:
  pulsante `Visualizza ed esporta`, modal con le particelle ruolo escluse aggregate per
  chiave catastale e motivo, e export Excel `particelle-ruolo-escluse-indici-<anno>.xlsx`.
  Il backend espone `GET /catasto/indici/ruolo-esclusi?anno=<anno>` e riusa le stesse
  regole della riconciliazione, cosi il conteggio della modal resta coerente con il KPI
  (2025: 7.843 particelle ruolo escluse).
- Dalla stessa modal si apre `/catasto/indici/anomalie-ruolo?anno=<anno>`, pagina
  operativa per lavorare i casi esclusi. Le anomalie `senza_distretto` sono correggibili
  direttamente assegnando un distretto verificato: il salvataggio aggiorna
  `cat_particelle.num_distretto` / `cat_particelle.nome_distretto` e scrive lo storico
  in `cat_particelle_history`, senza modificare il ruolo inCASS. Le anomalie
  `non_collegata` e `catasto_non_corrente_o_assente` restano code di indagine: richiedono
  aggancio catastale, verifica AdE/storico o nuova visura prima di attribuirle agli indici.
- La tabella e stata estratta nel componente
  `frontend/src/components/catasto/indici/distretti-table.tsx`: la logica di mapping
  distretti, alias `291/292/293`, filtro, ordinamento, totali ed export Excel e coperta
  da test unitari dedicati insieme alla pagina, alla pagina anomalie ruolo e alla card di riconciliazione
  (`catasto-indici-page.test.tsx`, `catasto-indici-distretti-table.test.tsx`,
  `catasto-indici-anomalie-ruolo-page.test.tsx`,
  `catasto-indici-ruolo-reconciliation-card.test.tsx`). La coverage frontend mirata sui
  file `page.tsx`, `distretti-table.tsx`, `anomalie-ruolo/page.tsx` e
  `ruolo-reconciliation-card.tsx` e al 100% per statements, branches, functions e lines.

## 8. Cache snapshot

`cat_indici_overview_snapshots` ora include una versione di payload nella
`source_signature` (`v=6`): bump di `_OVERVIEW_PAYLOAD_VERSION` in `indici_overview.py`
quando cambia struttura o semantica del payload, per invalidare le cache esistenti.
Il passaggio a `v=6` invalida le snapshot precedenti e aggiunge al payload
`ruolo_reconciliation`, oltre ai campi gia introdotti nei breakdown
`comuni`/`distretti_analytics` (`importo_ruolo_manutenzione`,
`importo_ruolo_irrigazione`, `importo_ruolo_istituzionale`).

## Follow-up aperti

- Normalizzare codici/nomi distretto al momento dell'import
  (`import_shapefile.py`, `import_distretti_excel.py`).
- Rimuovere le righe duplicate `291/292/293` da `cat_distretti` a valle di una
  verifica sulle geometrie collegate.
- Allineare le varianti minori dei nomi distretto (19, 20, 28, 31, 34).
- Verifica operativa delle 454 particelle FD a ruolo.
