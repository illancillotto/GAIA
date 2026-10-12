# Calendari attestati INAZ e diagnostica GATE — 2026-10-08

Il censimento iniziale rileva 196 collaboratori attivi: 168 operai, 26 impiegati e 2 tipi mancanti. Su conferma del responsabile, Deschino viene classificato operaio e Marazzi impiegato; Serusi è già impiegato e conserva lo standard configurato. Lo stato finale è 169 operai e 27 impiegati. Non vengono dedotti area del personale o gruppo HR.

## Assegnazioni da fonte INAZ

Dei 90 operai privi di gruppo, esclusi i 26 Tecnici/Turnisti, 89 hanno almeno una descrizione programmata INAZ esplicita «7 ore x 5 gg - 1^ e 3^ sab mese». Otto hanno già il calendario `OPE0714_1E3SAB`; 81 ricevono questo calendario dalla prima data attestata nel 2026, senza riscrivere assegnazioni esistenti. Il novantesimo ha un calendario distinto `OPE0736_STD`, già assegnato: teorico 456 minuti da verificare con il responsabile prima di correggere il calcolo.

La politica giornaliera riconosce ora il calendario individuale `OPE0714_1E3SAB`: sui sabati ordinari il fallback legacy da 420 minuti diventa 390 minuti nei sabati previsti e zero negli altri. I codici estivi con durata esplicita mantengono la propria durata. I Tecnici/Turnisti continuano a usare la politica dedicata, distinta dall'assegnazione mensile e dalle rotazioni quindicinali.

La presenza di un calendario mensile non rende automaticamente ogni ADD/IRR un turno. I gruppi HR rimangono distinti dalle assegnazioni orarie. I casi privi di regola applicabile restano soggetti agli altri percorsi di classificazione esistenti.

## Diagnostica ricevuta da GATE

Il builder condiviso del pull LAN e del push outbound pubblica:

- `stato`, `evidenze`, `detail_status` e `detail_anomalies`;
- richieste, orari programmati/effettivi, fasce, teorico, riepiloghi e totali INAZ;
- timbrature originali in `inaz_detail_punch_rows`, insieme alle coppie operative esistenti;
- `inaz_source`, proiezione della sorgente giornaliera che conserva i valori originali;
- `operational_status`, formula, teorico, mancanti, MPE e note GAIA; `status` resta l'alias dell'esito operativo;
- `has_inaz_anomaly`, calcolato con la stessa funzione usata da GAIA.

`detail_title` è escluso dalla proiezione: il fallback dello scraper può includere il testo dell'intera pagina del portale, estraneo al dettaglio della singola giornata. A settembre questo solo campo occupa 212 MB su 229 MB di sorgenti giornaliere. Il raw integrale rimane conservato in GAIA; la proiezione mantiene i dati della giornata senza quel contenuto.

Gli snapshot GATE conservano i nuovi campi senza una migrazione DB. La console distingue «Stato GAIA» e «Stato INAZ» nel dettaglio. L'esito operativo mantiene precedenza sul testo sorgente; un'anomalia INAZ può generare una verifica anche quando le ore GAIA quadrano. La validazione amministrativa conserva la precedenza esistente.

## Verifiche e reversibilità

- Backup mirato prima delle correzioni contrattuali e delle 81 assegnazioni, conservato sul server fuori dal repository.
- Manifest basato su UUID collaboratore e mapping canonico già presente; nessun collegamento per nome.
- Dry-run delle assegnazioni: 81 nuove, 8 invariate; nessuna assegnazione concorrente sovrascritta.
- Test dei sabati 1/3 e non previsti, validità profili, rotazioni esistenti, trasporti mobile-sync e persistenza dei campi INAZ.
- Coverage al 100% richiesta sui quattro file runtime GAIA modificati/aggiunti; ratchet contro HEAD, senza modificare le soglie.
- Build dello snapshot di produzione in transazione read-only e verifica della dimensione prima del rilascio.

Non correggere `OPE0736` senza l'esito della verifica richiesta al responsabile. I file di manifest, backup e payload con dati personali non sono versionati.

## Esito in produzione

Backend GAIA e gateway VPS sono stati rilasciati con tag `inaz-details-20261008`; backend `/health` HTTP 200, gateway healthy, worker Presenze e sync in esecuzione. Il rilascio GAIA deriva dall'immagine corrente e modifica soltanto i quattro file Presenze; conserva la correzione POSTE e gli altri rilasci concorrenti.

La cache GATE contiene 35.893 giornaliere 2026 con tutti i campi `stato`, `detail_status`, `detail_anomalies`, `inaz_source` e `operational_status`. Anche i contratti dei tre casi attestati risultano corretti negli snapshot. Verifica delle assegnazioni ripetuta: zero nuove e 89 invariate. Su 20 sabati campionati il calendario ordinario restituisce 390 minuti per 1°/3° e zero negli altri; le assegnazioni Acquaiolo esistenti mantengono la precedenza e il proprio teorico da 420 minuti.

Validazione: 263 test GAIA, coverage statement/branch 100% dei quattro runtime; 130 test GATE, typecheck gateway e Ruff del perimetro verdi. Ratchet GAIA contro HEAD senza findings. Il ratchet generale GATE segnala il debito della baseline precedente (incluse modifiche già rilasciate) e l'incremento di una riga nel template console: non viene dichiarato verde e non vengono cambiate soglie o baseline per assorbirlo. Nessun nuovo commit in questo intervento.
