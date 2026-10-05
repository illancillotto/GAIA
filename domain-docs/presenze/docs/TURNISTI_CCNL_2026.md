# Turnisti: CCNL e accordo integrativo — 5 ottobre 2026

Implementazione locale coordinata GAIA/GATE. Nessun rilascio o ricalcolo di produzione.
Le precedenti regole locali `shift-v1` sono integrate dalle regole `shift-ccnl-v2`.

## Documenti verificati

- `FAI CISL - CCNL BONIFICA 2023 - 2026.pdf`, artt. 47–49, 80, 82–83 e 137.
  SHA256: `8f09770620642bc2d3179029ddacf84f7f5530831c5d5d5d6f854f2fb955c83a`.
- `Allegato_Accordo (1).pdf`, accordo sottoscritto il 25/08/2026: artt. 2, 3, 5, 7 e 10.
  Documento scansionato, letto con OCR; clausole determinanti delle pagine 2 e 3
  controllate anche visivamente.
- `D.C.A._n._104_del_26.08.2026 (3).pdf`: approvazione dell’accordo e decorrenza
  dal giorno successivo al visto di legittimità.
- `OdS_Maturazione_diritto_al_buono_pasto-signed.pdf`: visto n. 20015 del 04/09/2026;
  decorrenza favorevole **26/08/2026 per il solo buono pasto**. Le altre disposizioni
  dell’accordo entrano formalmente in vigore dal 05/09/2026.
- `TRASMISSIONE_ACCORDO_INTEGRATIVO (2).pdf`: comunicazione operativa della
  Direzione che dispone l’applicazione dell’accordo nella sua interezza da
  **lunedì 07/09/2026**. La successiva decorrenza favorevole del solo buono
  pasto resta il 26/08/2026. Documento letto con OCR.

I PDF originali restano nella cartella Downloads; non vengono versionati né
interpretati come configurazioni di singoli dipendenti.

## Regole applicate

| Fonte | Regola | Implementazione |
| --- | --- | --- |
| CCNL 47 | Sabato non festivo per il solo giorno della settimana | Calendario GAIA: sabato feriale salvo festività effettiva |
| CCNL 49/83/137 | Notturno 22:00–06:00 | Conteggio per minuto; soglie 22:00 e 06:00 esatte |
| CCNL 83 | Festivo/domenicale distinto dal feriale | Ogni minuto segue il giorno civile, anche dopo mezzanotte |
| Accordo 2.2.b | Buono per almeno 7 ore ordinarie in turno | 419 minuti: zero; 420 minuti: uno; timbrature incomplete/overlap: zero automatico |
| Accordo 3 | Valore nominale del buono €7 | Informazione contrattuale; nessuna conversione del diritto in denaro |
| Accordo 5.a | Nessun buono per giornata di assenza | Assenza e riposo senza lavoro non producono buono; giustificativi non diventano ore lavorate |
| Accordo 5.b | Escluso se il vitto in trasferta è rimborsato | Trasferta segnalata: diritto automatico sospeso in attesa di verifica; non si presume il rimborso dal solo numero di minuti |
| Accordo 7 | Personale in turno escluso dalla flessibilità | Nessuna tolleranza operaio/impiegato applicata; nota esplicita nelle giornaliere |
| OdS | Buoni dal 26/08/2026 | Nessun diritto automatico derivato dal nuovo accordo prima di tale data; manuali preservati |
| CCNL 80/137 | Straordinario preventivamente autorizzato | Eccedenza distinta e metadato di autorizzazione necessaria; nessun importo retributivo generato |

Il teorico locale preesistente di **420 minuti** viene mantenuto. Il requisito
“almeno sette ore” dell’accordo è una soglia per il buono, non la definizione
universale della durata del turno. CCNL 47 disciplina l’orario settimanale e le
medie: non si deduce che tutte le ore oltre sette in una singola giornata siano
automaticamente straordinario pagabile. L’export conserva l’eccedenza operativa
secondo la configurazione locale, da confrontare con il turno pianificato e
l’autorizzazione amministrativa.

## Maggiorazioni contrattuali

Percentuali alternative, non cumulative, riferite alle rispettive basi
retributive del contratto. Non si deduce avventizio dal tempo determinato,
dal tipo operaio o dal codice TELEC.

| Categoria | Titolo II, artt. 80/83 | Avventizi, art. 137 |
| --- | ---: | ---: |
| Ordinario feriale diurno | 0% | 0% |
| Ordinario festivo/domenicale diurno | 10% | 39% festivo |
| Ordinario feriale notturno in turno | 15% | 10% |
| Ordinario festivo notturno in turno | 20% | 15% |
| Straordinario feriale diurno | 25% | 25% |
| Straordinario festivo diurno | 50% | 50% |
| Straordinario feriale notturno | 50% | 38% |
| Straordinario festivo notturno | 75% | 66% |

Le tabelle sono esposte come `shift_ccnl.rate_candidates`, con minuti per
categoria in `premium_minutes`. Il campo `payroll_status` resta
`requires_hr_regime_and_overtime_authorization`: manca l’attestazione del regime,
della base retributiva e dell’autorizzazione. Non si generano compensi in euro né
si sceglie arbitrariamente una tabella. L’art. 82 sul notturno non in turno non
viene sommato alle maggiorazioni dell’art. 83. La domenica è inclusa esplicitamente
dall’art. 83; per gli avventizi occorre distinguere la domenica e il relativo
riposo compensativo secondo l’art. 137: i bucket festivi/domenicali comuni non
attestano da soli il diritto alla percentuale festiva dell’avventizio.

## Flusso e compatibilità

GAIA costruisce un calendario di due giorni, incluso il giorno successivo al
limite dell’esportazione, con priorità del calendario aziendale e le regole
festive già esistenti. Le giornaliere esportano `export_shift_calendar` e
`shift_ccnl`; lo schema di snapshot ammette già campi aggiuntivi. Entrambi i
trasporti, LAN e outbound, usano il builder autorevole esistente.

GATE ricalcola gli overlay turnista usando quel calendario; per snapshot legacy
privi di calendario mantiene la classificazione preesistente e imposta
`calendar_attested=false`, richiedendo uno snapshot nuovo per la valutazione
contrattuale. I turnisti non subiscono la rimozione di 1–4 minuti notturni
prevista per gli operai diurni, né nella vista mensile né nel file XLSM.

Le assegnazioni GATE, la loro precedenza, le revoche e gli inserimenti manuali
restano gestiti dai servizi esistenti. Una trasferta non prova il rimborso vitto:
il diritto va verificato prima di inserire un buono manuale. Il buono non viene
duplicato quando coesistono diritto automatico e inserimento manuale.

## Limiti che richiedono dati autorevoli

- Rotazione e orari pianificati: i documenti forniti non definiscono un calendario
  mattina/sera né attestano il turno assegnato a ciascuna persona. Non si generano
  ritardi inventati dalle sole timbrature.
- Riposi CCNL 48 e medie CCNL 47/49: la verifica richiede uno storico completo,
  i cambi turno, le eccezioni e i riposi compensativi; una sola giornaliera o un
  mese parziale non ne dimostra il rispetto.
- Profilo fisso/avventizio e relativa base retributiva: mancano nello snapshot
  corrente; le tabelle sono candidati per HR, non un motore paghe attivato.
- Rimborso vitto: manca un campo canonico affidabile. Le trasferte restano in
  verifica; non viene introdotto un dato HR inferito.
- Art. 2.2.a e 2.2.c dell’accordo riguardano rientri e straordinario autorizzato:
  questa modifica interviene sul percorso **turnisti**, senza attestare la
  conformità completa delle altre popolazioni alla nuova convenzione.

## Verifica

Le fixture `shift-ccnl.json` nei due repository sono identiche: confini del
notturno, sabato/domenica, festività oltre mezzanotte, turni spezzati, nessun
lavoro ed eccedenze. Test aggiuntivi verificano API, calendario aziendale oltre
il mese, soglia buono/decorrenza/trasferta, revoche e XLSM reale con due minuti
notturni. Le evidenze seguenti sono storiche della prima verifica CCNL;
non attestano il checkout finale. Risultati correnti e regressioni del ciclo:
[report coordinato](TURNISTI_COORDINATED_VERIFICATION_2026-10-05.md).

Evidenze storiche locali:

- GAIA: 141 test di classificazione, turnisti, assenze sindacali e timbrature
  pendenti superati; cinque file runtime modificati al 100% di statement e
  branch. Dopo la sola formattazione del modulo turnisti, ripetuta la suite
  specifica con copertura full-file.
- GATE: 66 test della suite classificazione/export/voucher superati; aggiunto
  il caso di preview con quantità nulle, distinguendo assenza, dato mancante e
  zero. Suite finale delle regole e preview nuovamente eseguita.
- Quattro servizi GATE modificati: 100% di statement, branch, funzioni e righe,
  combinando la suite completa dell’export, la suite delle regole finali e il
  caso di preview. I report dei servizi invariati tra queste esecuzioni sono
  aggregati con Istanbul; il report del modulo regole precedente è sostituito
  dalla verifica della sua versione finale. Non sono modificati soglie o
  esclusioni di repository.
- Typecheck gateway ed ESLint dei runtime modificati; Ruff e formatter del
  perimetro GAIA verificati. Ratchet GATE e ratchet GAIA sui cinque file runtime
  modificati superati senza aggiornare la baseline.
- `make lint-backend QUALITY_PYTHON=.venv/bin/python` evidenzia errori anche nei
  lavori concorrenti GIS/Ruolo e altri test, fuori da questa modifica. Il gate
  globale GAIA non è dichiarato superato; tali file non vengono corretti qui.
- Fixture dei due repository identiche; mappe Graphify codice aggiornate.
- Nessun deploy, migrazione produttiva, import/sync live, commit o push.

I report di coverage locali sono in `/tmp/gate-ccnl-final-coverage-summary.json`
(GATE), `/tmp/gate-ccnl-gaia-coverage-stable.json` e nel report successivo del
solo modulo GAIA formattato. I limiti HR e il calendario di rotazione indicati
sopra rimangono espliciti: questa verifica non attesta la conformità dell’intero
sistema paghe o il recupero di dati reali in produzione.
