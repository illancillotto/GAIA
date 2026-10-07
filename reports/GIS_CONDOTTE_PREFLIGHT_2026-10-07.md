# Condotte GIS: verifica preliminare del 2026-10-07

## Fonte e referenti

Percorso consegnato dall'utente:
`/run/user/1000/gvfs/smb-share:server=nas_cbo.local,share=settore%20catasto/SHP/SHP-CONDOTTE_CBO`.

Referenti indicati: Marco Cadoni, Fabrizio Podda e Alessandro Porcu.
La cartella e accessibile e contiene 11 shapefile con componenti SHP, SHX,
DBF, PRJ, CPG e metadati QMD. Il nome del file non costituisce conferma
della revisione ufficiale; resta da acquisire dai referenti.

## Verifiche eseguite

Lettura completa tramite pyshp e verifica geometrie con Shapely. I duplicati
sono calcolati sull'intera geometria normalizzata, non sul nome della condotta.
Le copie geometriche interne a ogni file hanno anche attributi identici.
OGR riconosce il PRJ di Arborea come Monte Mario / Italy zone 1, EPSG:3003.
Tutti gli 11 PRJ hanno SHA-256 identico:
`b15a8013aa977a900e18148413575d53f507ad4c135097c681e6c01cec761241`.
La destinazione GAIA e MULTILINESTRING EPSG:4326: serve una trasformazione
esplicita e revisionata, non una semplice assegnazione del nuovo SRID.

| File, senza estensione | Record | Geometrie distinte non nulle | Copie geometriche aggiuntive | Nomi vuoti | Diametri nulli |
| --- | ---: | ---: | ---: | ---: | ---: |
| D20_FenosuSanNicolo_Condotte-24-02-2025 | 271 | 271 | 0 | 0 | 0 |
| D24_Arborea_Lotto_Sud_Condotte-2026 | 404 | 210 | 194 | 168 | 4 |
| D24-Imp_1-Arborea_Lotto_Sud_Condotte-2026 | 96 | 50 | 46 | 3 | 2 |
| D24-Imp_2-Arborea_Lotto_Sud_Condotte-2026 | 114 | 60 | 54 | 86 | 0 |
| D24-Imp_3-Arborea_Lotto_Sud_Condotte-2026 | 189 | 101 | 88 | 80 | 2 |
| D26_Sassu_Condotte-2026 | 320 | 173 | 146 | 86 | 100 |
| D26-Imp_1-Sassu_Condotte-2026 | 40 | 25 | 15 | 2 | 6 |
| D26-Imp_2-Sassu_Condotte-2026 | 101 | 52 | 49 | 60 | 52 |
| D26-Imp_3-Sassu_Condotte-2026 | 52 | 27 | 25 | 0 | 2 |
| D26-Imp_4-Sassu_Condotte-2026 | 76 | 44 | 32 | 24 | 38 |
| D26-Imp_5-Sassu_Condotte-2026 | 50 | 25 | 25 | 0 | 2 |

Nessun diametro negativo o zero rilevato. Un diametro nullo resta sconosciuto,
non va convertito in zero.

Nel file generale Sassu, record 77 (indice umano da 1): geometria non valida
con troppo pochi punti, `Nome_Condo=38_1`. Record 237: geometria NULL con lo
stesso nome. Gli altri file non presentano geometrie nulle o invalide.

Gli shapefile per impianto ripetono in gran parte il file generale:
Arborea Imp_1 condivide 48 geometrie su 50 con il generale; Imp_2 60 su 60;
Imp_3 101 su 101. Quindi Imp_1 contiene anche due geometrie da confrontare,
non va considerato automaticamente una copia completa del generale.
Sassu Imp_1..5 condividono rispettivamente 25, 52, 27, 44 e 25 geometrie
con il generale; Imp_2 e Imp_5 condividono tra loro una geometria.
Non e stata effettuata alcuna eliminazione o fusione automatica.

SHA-256 dei tre SHP generali:

- D20: `52503c4adf1e640127869a85ff9de2c3cbeb4665d7d0d30d2587f1afd85ccac6`.
- D24: `6fcacfe1315332bdd4fa7156dbe209701ee07a505acf3ea1e0c6d7c17f531a15`.
- D26: `b7d82aa6208f8b736a224a8e6d4f409e366af9b38934c629e17fb42bf23b4727`.

## Mapping proposto, da revisionare

- `Nome_Condo` -> `descrizione`: non e un codice univoco, anche D20 ripete nomi.
- `Tipo_Mater` -> `materiale`, conservando sigle originali; vuoto -> NULL.
- `Diametro` -> `diametro_mm`, previa conferma che l'unita sorgente sia mm.
- `Distretto`, `Nume_Distr`, `Tipo_Condo`, `Classe_Pre`, `Portata`, `X`, `Y`
  -> provenienza conservata nelle note quando presenti, senza perdita degli attributi.
- `codice`: identificativo stabile di segmento da concordare; non usare
  automaticamente Nome_Condo o assegnare codici di dominio inventati.
- `stato`: da concordare; Tipo_Condo non e uno stato operativo. In Sassu i
  valori 1 e 2 non vengono interpretati senza conferma.
- geometria: trasformazione revisionata EPSG:3003 -> EPSG:4326 e
  normalizzazione MULTILINESTRING; nessuna riparazione silenziosa.

## Ambiente e accessi

Verifica read-only su serverCed, container gaia-backend:
`network.rete_condotte` contiene ancora 0 record. Il layer catalogo e
`8745559b-1e18-4b37-94e9-a86466d5232f`, workspace `rete`.

Account Alessandro Porcu: `porcu.alessandro`, id 329, attivo, role operator,
module_gis gia true. L'amministrazione completa GIS richiede attualmente il
ruolo generale admin GAIA; la scelta tra tale ruolo e permessi amministrativi
limitati ai layer e stata richiesta all'utente ed e in attesa di risposta.

Account Luca: `serusi.luca`, id 248, nome visualizzato Serusi Luca. Il
2026-10-07 e stato abilitato module_gis tramite il repository applicativo
`update_application_user`. Ruolo operator preservato. Per la consultazione
sono stati assegnati permessi individuali viewer sui 48 layer attivi,
con precedenza sui permessi di ruolo: verifica finale 48 layer visibili,
0 layer modificabili. Le 48 assegnazioni sono registrate in gis_audit_logs,
con actor_user_id NULL e origine operativa esplicita, senza impersonare
un amministratore. Il riallineamento QGIS e stato eseguito prima del commit
della transazione dati. Nessuna credenziale e stata generata o ruotata.

## Pacchetti preparati

Gli 11 ZIP sono disponibili in `/tmp/gaia-condotte-20261007`, uno per
shapefile. Contengono i componenti originali, incluso il QMD, senza
trasformazioni, deduplica o correzioni. `manifest.json` conserva il percorso
sorgente e SHA-256 di ogni archivio e componente. La verifica CRC di tutti
gli ZIP e passata. Sono artefatti locali preparatori, non import GAIA.

## Gate prima dell'import ufficiale

Confermare con i referenti versione autorevole dei file, trattamento delle
copie, due geometrie extra Arborea Imp_1, correzione/scarto dei due record
Sassu, mapping e codici stabili, unita diametri, stato e trasformazione CRS.
Poi preparare il pacchetto con manifest/checksum, validazione in staging
M13-M15 e anteprima del comprensorio. Solo dopo revisione di conteggi, scarti,
bbox e attributi creare le change request M17; approvazione e apply M20
restano successivi. Nessun import staging, change request o apply e stato
eseguito in questa verifica. I file NAS sono rimasti invariati.
