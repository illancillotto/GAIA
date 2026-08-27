# GAIA GIS Platform - Progress Territorio Esterno

> Ultimo aggiornamento: 2026-08-27.
> Branch corrente: `main`.
>
> Piano tecnico: `docs/GIS_PLATFORM_TERRITORIO_PLAN.md`.
> Riferimento dati: `docs/GIS_PLATFORM_TERRITORIO_CATALOGO.md`.
> Prompt operativi: `docs/GIS_PLATFORM_TERRITORIO_PROMPTS.md`.

## Stato Sintetico

Nessuna milestone del programma Territorio Esterno e implementata. Il lavoro e
in stato di piano approvato, con analisi delle sorgenti completata e catalogo
seed definito.

La base M1-M20 della GIS Platform e in esercizio e non richiede modifiche
preliminari: `source_type` e gia una colonna `String(32)` libera in `GisLayer` e
`metadata_json` e gia `JSON`, quindi M21 non necessita di migration dello
schema catalogo.

## Milestone

| milestone | contenuto | stato | branch |
| --- | --- | --- | --- |
| P0 | Verifica licenze e disponibilita sorgenti | da eseguire | - |
| M21 | Fondazione layer esterni: source type, proxy, cache, health | da implementare | `feature/gis-territorio-external-layers-m21` |
| M22a | Seed catalogo `territorio` e `GET /gis/territorio/layers` | da implementare | `feature/gis-territorio-catalog-seed-m22` |
| M22b | Pannello strati e ortofoto storiche in mappa | da implementare | `feature/gis-territorio-layer-panel-m22` |
| M23a | Interrogazione puntuale multi-sorgente, backend | da implementare | `feature/gis-territorio-interrogazione-m23` |
| M23b | Pannello interrogazione, frontend | da implementare | `feature/gis-territorio-interrogazione-ui-m23` |
| M24 | Scheda territoriale particella in PDF | da implementare | `feature/gis-territorio-scheda-m24` |
| M25 | Strumenti di campo e propagazione QGIS | da implementare | `feature/gis-territorio-strumenti-m25` |

## Analisi Preliminare Completata

Data: 2026-08-27.

Censimento sorgenti eseguito interrogando direttamente i documenti
GetCapabilities:

- RAS SITR GeoServer vettoriale: `379` layer nel namespace `dbu:`, WMS 1.3.0 e
  WFS 1.1.0 sullo stesso endpoint;
- RAS SITR GeoServer raster: ortofoto storiche dal volo 1940-45 al 2022, DTM e
  DSM da rilievo LiDAR a 1m e 10m, CTR, mosaici DBGT;
- Agenzia delle Entrate Cartografia Catastale INSPIRE: `CP.CadastralParcel`,
  `CP.CadastralZoning`, `fabbricati`, `acque`, `strade`, `vestizioni`,
  `province`, `codice_plla`, `simbolo_graffa`.

Layer del seed verificati esistenti con titolo confermato dalla sorgente. Il
dettaglio e in `docs/GIS_PLATFORM_TERRITORIO_CATALOGO.md`.

Constatazione rilevante per il dominio: il GeoServer RAS pubblica
`agr_consorzi_irrigui_bonif_comprensori`, `agr_consorzi_irrigui_bonif_distretti`
e `areebonifica`, cioe la delimitazione regionale degli stessi oggetti che GAIA
governa internamente. La sovrapposizione e utile come controllo, ma richiede una
decisione esplicita di autorevolezza prima del seed.

## Verifiche

Nessuna verifica di implementazione eseguita: non c'e ancora codice.

Verifiche di sorgente eseguite il 2026-08-27:

- GetCapabilities WMS RAS vettoriale: risposta valida, `379` layer.
- GetCapabilities WMS RAS raster: risposta valida, serie ortofoto e DTM
  presenti.
- GetCapabilities WMS AdE Cartografia Catastale: risposta valida, layer INSPIRE
  presenti.

Non ancora misurato:

- tempo di risposta di GetMap e GetFeature sui layer del seed;
- comportamento sotto richieste concorrenti;
- limiti di frequenza imposti dalle sorgenti.

Queste misure sono parte di P0 e servono a dimensionare i timeout di M21.

## Decisioni Aperte

- Licenza e attribuzione di ciascuna sorgente. Bloccante per M22: e l'unico
  vincolo che, se scoperto tardi, obbliga a smontare lavoro gia fatto.
- Autorevolezza in caso di divergenza tra distretti irrigui RAS e
  `cat_distretti` GAIA. Proposta: GAIA resta autorevole, la sovrapposizione e
  informativa, e la descrizione del layer lo dichiara. Da confermare.
- Se il programma Territorio Esterno debba essere numerato come continuazione
  della GIS Platform (M21-M25, ipotesi adottata nei documenti) o come modulo
  affiancato con numerazione propria.
- Se il precaricamento delle ortofoto sulla bounding box del comprensorio vada
  fatto subito o solo dopo aver misurato le prestazioni reali del proxy in
  esercizio.
- Se la scheda territoriale M24 debba essere accessibile anche dall'anagrafica
  particella oltre che dalla mappa.
- Politica di aggiunta di nuovi layer al catalogo dopo il seed: chi approva la
  richiesta e con quale evidenza di caso d'uso.

## Rischi

- Le sorgenti RAS e AdE non hanno SLA verso GAIA. Ogni funzione che le usa deve
  restare utile con le sorgenti irraggiungibili. Il criterio di accettazione di
  M23 lo verifica esplicitamente.
- I WMS raster storici sono pesanti. Senza cache con TTL lungo l'apertura della
  mappa puo diventare lenta e generare carico non necessario verso la Regione.
- Rischio di uso improprio da parte di utenti non tecnici: un operatore potrebbe
  credere di poter proporre una change request su un vincolo regionale. I
  divieti vanno applicati lato API, non solo nascondendo i controlli in UI.
- Le revisioni PAI cambiano nel tempo. Un aggiornamento di revisione va trattato
  come nuovo layer, non come modifica silenziosa di quello esistente, altrimenti
  le schede territoriali gia generate diventano non ricostruibili.
- Espansione incontrollata del catalogo: con `379` layer disponibili ogni
  ufficio ne vorra uno. Senza una regola di governo il catalogo diventa
  ingestibile e il pannello strati illeggibile.
- Crescita di file gia sopra soglia di complessita:
  `backend/app/modules/gis/services.py` a `3441` righe e
  `frontend/src/components/catasto/gis/MapContainer.tsx` a `1552` righe. Il
  piano prescrive package e hook dedicati; se questa regola viene aggirata il
  ratchet fallisce.
- Il disclaimer della scheda territoriale non e una formalita: senza, un
  documento istruttorio interno puo essere usato impropriamente come
  certificazione.

## Prossima Azione Raccomandata

Eseguire P0 di `docs/GIS_PLATFORM_TERRITORIO_PROMPTS.md`: accertare licenze,
attribuzioni e limiti d'uso delle tre sorgenti, riconfermare l'esistenza dei
layer del seed e misurare i tempi di risposta.

Non aprire P1 prima che P0 sia chiuso e registrato in questo documento: i valori
di timeout di M21 e l'ammissibilita dei layer del seed dipendono da quel
risultato.
