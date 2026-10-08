# Collegamenti delle presenze del Catasto — 07/10/2026

L’utente ha autorizzato il ripristino dei collegamenti mancanti e attestato che
15 nominativi sono personale del Catasto, precisando poi che i tipi contrattuali
sono misti. Tutti avevano già una relazione
canonica `presenze_collaborators.application_user_id -> application_users.id`.
Non è stato dedotto o modificato alcun mapping da nomi, email o matricole.

## Intervento applicato

Per i GAIA ID 346, 347, 348, 349, il servizio di manutenzione
`canonical_reference_repair.py` ha ripristinato il riferimento canonico in
239 giornaliere e 53 riepiloghi, precedentemente NULL. La procedura valida tutto
il batch prima di scrivere, rifiuta identità non canoniche, duplicati e riferimenti
non-null conflittuali, richiede un amministratore e un motivo audit esplicito.
Il chiamante mantiene la transazione; un secondo passaggio non modifica nulla.

Quattro righe audit, `source=canonical_references`, `action=map`, conservano lo
stesso ID canonico prima/dopo e indicano che si tratta di riferimenti derivati,
non di rimappatura del collaboratore. Invalidati gli snapshot dashboard GAIA.
Non sono state create schede operative WCOperator né account o permessi nuovi.

Un confronto transazionale verifica che tutti i valori dei record interessati,
tranne il riferimento riparato e il timestamp di aggiornamento, rimangano uguali;
account, schede operatori e collaboratori sono confrontati integralmente.
SHA256 prima/dopo: `0bb94ce34a8a2ea1d7e1a10d3da6988acc283f22bf1088a3984442c60f257471`.

## Verifiche e sincronizzazione

- 11 test reali su SQLite, coverage statement/branch 100% del nuovo servizio.
- Ruff e quality ratchet contro `main` passati, nessuna modifica a baseline/soglie.
- Backup mirato dati Presenze/anagrafiche/squadre/sync e schema completo:
  custom dump di 309.045.426 byte, lista pg_restore verificata, upload NAS e
  checksum remoto verificati. SHA256:
  `ce953ecfdaeff3048dd5bef04415e6a250d516f87769c65e9a68d0a0f73daee9`.
- Dry-run: 239 giornaliere, 53 riepiloghi; apply identico; dry-run successivo: zero.
- Audit globale: zero unmapped, duplicati, orfani e divergenze delle giornaliere
  e dei riepiloghi dal collaboratore canonico.
- Invio outbound con builder esistente per collaboratore/mese: 119 scope delle
  15 persone, 3.619 giornaliere e 332 anomalie. Run riuscito
  `fdb5e4be-7f73-4964-aa9f-13db89e99f5d`.

## Dati distinti da confermare

L’assenza di WCOperator per i 15 nominativi era stata presentata inizialmente
come incoerenza generale. WCOperator è l’anagrafica operativa usata da GATE;
la sola assenza non prova che un impiegato debba essere creato come operatore.
Gli account e i collegamenti Presenze esistono già. La richiesta non autorizza
l’attribuzione automatica di un’area AGRARIO/IMPIANTI o nuovi accessi operativi.

Nell’anagrafica Presenze, 7 nominativi hanno `contract_kind=impiegato`, 7 hanno
`operaio` e 1 ha tipo assente. Alla domanda sulla correzione del tipo contrattuale,
l’utente ha risposto «sono misti è vero scusami»: la classificazione esistente
resta conservata, compreso il tipo assente. L’utente ha attestato l’area CATASTO;
il contratto GAIA/GATE e i vincoli sono stati estesi per ammetterla come terza
area, senza dedurla dal dominio applicativo o cambiare i permessi esistenti.

## Estensione CATASTO e stato del completamento

La migrazione GATE `030_catasto_personnel_area.sql` è applicata e il gateway VPS
usa `gate-mobile-gateway-api:catasto-area-20261007`, con health HTTP 200.
Un backup mirato GATE, lista pg_restore e SHA256 sono conservati nel rilascio
privato `catasto-area-20261007/before`. La migrazione GAIA `20261007_1800`
estende tre check constraint; il suo downgrade rifiuta dati CATASTO esistenti.
Il backend nuovo è costruito come overlay dei soli otto file runtime coinvolti,
senza includere modifiche non correlate.

Il dry-run delle 15 schede, sulla nuova immagine GAIA e sul database corrente,
è passato: 15 schede mancanti, 15 aree da assegnare, zero rimappature.
La procedura crea esclusivamente WCOperator con identità GAIA già canoniche,
login mobile e console disabilitati, nessun account o profilo operativo nuovo.
Una guardia prima del commit confronta integralmente account, collaboratori e
operatori preesistenti. Ogni creazione avrà audit `canonical_operator_link`.

La scrittura definitiva è ancora in attesa: il dump generale indipendente
`20261007-all-release/database.dump.partial`, aperto da oltre un’ora, trattiene
un lock incompatibile con ALTER TABLE. È stato annullato esclusivamente il
tentativo di schema in attesa, con rollback; nessuna scheda è stata creata.
Chiesta una scelta all’utente fra attendere la fine del dump generale e
interromperlo. Il dump non è stato interrotto senza risposta; il backup mirato
già verificato NAS rimane disponibile. Il prossimo tentativo imposta timeout
di lock e statement, senza marcare migrazioni Ruolo estranee come eseguite.

Verifiche dell’estensione: 260 + 34 test GAIA passati, coverage statement/branch
100% degli otto runtime modificati; migrazione e form squadre GAIA 100%;
Ruff e ratchet GAIA passati. GATE: 91 test mirati passati, compresa segregazione
CATASTO/AGRARIO, coverage del risolutore area 100%; 37 test shared passati.
Typecheck GAIA/GATE e build gateway passati. Il primo giro completo GATE aveva
768 test passati e una sola asserzione sul vecchio testo del renderer: corretta
e verificata nel giro mirato. Il ratchet GATE segnala esclusivamente incrementi
LOC per la nuova categoria; baseline e soglie non sono state indebolite.

Artefatti personali e backup restano fuori da Git. Nessun deploy o restart
richiesto per eseguire il servizio di manutenzione verificato; la procedura è
stata caricata temporaneamente nel container e il sorgente è versionabile nel
repository. Nessuna modifica alle identità o agli accessi.

## Completamento del 08/10/2026

Il backup generale è terminato il 07/10 alle 20:26, senza essere interrotto.
Alla richiesta «verifica ora» il database è risultato libero. Applicati i tre
vincoli CATASTO con timeout e senza cambiare Alembic `20261005_1500`.
Backend `gaia-backend:catasto-area-20261007` e runtime worker/sync aggiornati;
servizi verificati healthy.

Dry-run ripetuto: 15 creazioni, 15 aree, zero rimappature. Applicazione atomica:
15 WCOperator e 15 audit `canonical_operator_link`; account, contratti e
operatori preesistenti verificati invariati dalla guardia prima del commit.
SHA256 protetto nella transazione:
`e592110df742f5b2cad15c7981d2096ec47b55e801c3fa614cd7bfcaae95b0f3`.
Secondo dry-run: zero creazioni/modifiche, 15 invariati.

Le schede sono collegate alle identità esistenti e hanno area CATASTO;
mobile/console rimangono disabilitati per le nuove schede, senza nuovi accessi.
Registri canonici privati locale/server estesi da 39 a 54 coppie, conservando
integralmente le precedenti. Push operatori limitato alle 15 schede riuscito:
`77cda0e1-5ea4-492a-9037-70cc4432dba9`.
Audit GAIA globale: zero unmapped, duplicati, divergenze giornaliere/riepiloghi e
collaboratori senza un solo WCOperator canonico.

Verifica finale GATE: 15 operatori canonici CATASTO ricevuti, console disabilitata,
nessuna password e stato DISABLED. Tutte le 3.619 giornaliere delle 15 persone
mantengono identità, UUID collaboratore e data corretti. Gateway health HTTP 200.

La verifica ha rilevato che l’import GATE ignorava `status` e forzava ACTIVE
anche per personale inviato come DISABLED. Corretto il repository PostgreSQL e
in-memory per rispettare lo stato canonico; conservata la regola preesistente
per chi ha già inviato rapporti di lavoro GAIA. Aggiunto test per CATASTO
DISABLED su push ripetuti e conservato il caso di primo accesso per operatori
inviati ACTIVE: 93 test mirati e typecheck passati. Rilascio gateway finale
`gate-mobile-gateway-api:catasto-area-20261008`; secondo push operatori riuscito,
verifica del database reale passata. Le schede nuove non hanno acquisito accessi.
