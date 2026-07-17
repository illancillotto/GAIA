# GAIA - Data model per stampa e condivisione

Questa cartella contiene una vista divulgativa del modello dati GAIA.
I file sono generati con `scripts/generate_data_model_docs.py` leggendo la metadata SQLAlchemy del backend.

## File principali

- [Poster A0 HTML](GAIA_DATA_MODEL_A0_POSTER.html): versione pensata per stampa A0 orizzontale.
- [Poster A0 PDF](GAIA_DATA_MODEL_A0_POSTER.pdf): esportazione pronta per stampa, se Chrome/Chromium era disponibile durante la generazione.
- [Guida relazioni HTML](GAIA_TABLE_RELATIONSHIPS_GUIDE.html): nomi tabella, chiavi primarie e collegamenti spiegati in modo semplice.
- [Guida relazioni PDF](GAIA_TABLE_RELATIONSHIPS_GUIDE.pdf): versione A4 orizzontale multipagina della guida relazioni.
- [Catasto ERD A3 completo](gaia_erd_catasto_A3_fit.pdf): diagramma Catasto completo adattato su una pagina A3.
- [Catasto ERD A3 completo con bordi](gaia_erd_catasto_A3_borders.pdf): diagramma Catasto intero adattato su A3 con bordi di riferimento.
- [Catasto ERD poster 4 A3](a3-tiled/gaia_erd_catasto_A3_4up.pdf): diagramma Catasto ingrandito e diviso in 4 fogli A3.
- [Verifica stampa A3 ERD](GAIA_ERD_A3_PRINT_CHECK.md): controllo dimensioni SVG e leggibilita indicativa su A3.
- [Mappa A0 SVG](gaia_data_model_a0_map.svg): mappa macro tra domini funzionali.
- [Dizionario dati](GAIA_DATA_MODEL_DICTIONARY.md): descrizioni semplici, chiavi e collegamenti per ogni tabella.
- [Relazioni CSV](gaia_data_model_relationships.csv): elenco completo delle foreign key.

## Domini rilevati

| Dominio | Tabelle | Cosa racconta |
| --- | ---: | --- |
| Accessi e permessi | 10 | Gestisce utenti, ruoli, sezioni abilitate, inviti e accessi applicativi. |
| Organigramma | 10 | Rappresenta uffici, revisioni organizzative, assegnazioni e visibilita delle strutture. |
| Presenze | 21 | Raccoglie collaboratori, timbrature, giornaliere, squadre, turni e controlli operativi. |
| Catasto e GIS catastale | 55 | Collega particelle, utenze irrigue, distretti, intestatari, letture e dati cartografici. |
| Utenze e anagrafiche | 15 | Normalizza persone, aziende, documenti, import anagrafici, ANPR e fonti esterne. |
| Ruolo e incassi | 4 | Tiene traccia di partite, avvisi, particelle collegate e import del ruolo. |
| Operazioni sul campo | 37 | Descrive attivita, squadre, mezzi, segnalazioni, allegati, carburante e sincronizzazioni mobile. |
| Riordino fondiario | 16 | Gestisce pratiche, fasi, documenti, problemi, task, notifiche, ricorsi e collegamenti catastali. |
| Rete e dispositivi | 14 | Monitora dispositivi, scansioni, firewall, alert, planimetrie e soggetti tracciati. |
| Piattaforma GIS | 7 | Gestisce layer GIS, import shapefile, annotazioni, audit, permessi ed esportazioni. |
| Wiki e assistente | 13 | Conserva conversazioni, richieste, chunk documentali, eventi, metriche e audit degli strumenti. |
| Inventario e magazzino | 3 | Gestisce richieste di magazzino e collegamenti con segnalazioni operative. |
| Sincronizzazioni e audit | 6 | Registra job, esecuzioni, snapshot, revisioni e condivisioni trasversali. |
| Altro | 1 | Tabelle di supporto non assegnate a un dominio principale. |

## Diagrammi di dettaglio

- [Accessi e permessi](gaia_erd_accessi.svg)
- [Organigramma](gaia_erd_organigramma.svg)
- [Presenze](gaia_erd_presenze.svg)
- [Catasto e GIS catastale](gaia_erd_catasto.svg)
- [Utenze e anagrafiche](gaia_erd_utenze.svg)
- [Ruolo e incassi](gaia_erd_ruolo.svg)
- [Operazioni sul campo](gaia_erd_operazioni.svg)
- [Riordino fondiario](gaia_erd_riordino.svg)
- [Rete e dispositivi](gaia_erd_network.svg)
- [Piattaforma GIS](gaia_erd_gis.svg)
- [Wiki e assistente](gaia_erd_wiki.svg)
- [Inventario e magazzino](gaia_erd_inventario.svg)
- [Sincronizzazioni e audit](gaia_erd_sync.svg)

## PDF A3 con bordi

- [Accessi e permessi A3 con bordi](gaia_erd_accessi_A3_borders.pdf)
- [Organigramma A3 con bordi](gaia_erd_organigramma_A3_borders.pdf)
- [Presenze A3 con bordi](gaia_erd_presenze_A3_borders.pdf)
- [Catasto e GIS catastale A3 con bordi](gaia_erd_catasto_A3_borders.pdf)
- [Utenze e anagrafiche A3 con bordi](gaia_erd_utenze_A3_borders.pdf)
- [Ruolo e incassi A3 con bordi](gaia_erd_ruolo_A3_borders.pdf)
- [Operazioni sul campo A3 con bordi](gaia_erd_operazioni_A3_borders.pdf)
- [Riordino fondiario A3 con bordi](gaia_erd_riordino_A3_borders.pdf)
- [Rete e dispositivi A3 con bordi](gaia_erd_network_A3_borders.pdf)
- [Piattaforma GIS A3 con bordi](gaia_erd_gis_A3_borders.pdf)
- [Wiki e assistente A3 con bordi](gaia_erd_wiki_A3_borders.pdf)
- [Inventario e magazzino A3 con bordi](gaia_erd_inventario_A3_borders.pdf)
- [Sincronizzazioni e audit A3 con bordi](gaia_erd_sync_A3_borders.pdf)

## Rigenerazione

```bash
PYTHONPATH=backend python scripts/generate_data_model_docs.py
```

Il generatore usa `dot` se disponibile per produrre SVG. Se `dot` non e installato, restano comunque disponibili i file `.dot`, il CSV e il dizionario Markdown.
Se Chrome o Chromium e disponibile, viene generato anche il PDF A0.
