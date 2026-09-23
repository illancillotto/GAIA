# Giornaliera mensile individuale (Giornaliera2)

## Analisi del modello Excel

La schermata fornita rappresenta una persona per mese, con calendario orizzontale
(non la matrice persone/giorni della pagina Giornaliere). Le righe separano lavoro
ordinario e straordinario in feriale, festivo, notturno e festivo notturno;
seguono totale ore, chilometri, indennita, codici assenza, reperibilita e trasferta.
Il riepilogo comprende giornate lavorate/contributive e banca ore.

La schermata da sola non espone formule, macro o origine delle anagrafiche. Il
riferimento verificabile per i calcoli e il compilatore esistente
`apps/gateway-api/src/services/presenze-xlsm-export.ts`, soprattutto
`dayMinuteBreakdown`, `summarizeCollaborator` e `countPaidOperaioRestDays`.

## Pagine e fonti

- GaTe: `/admin/monthly-sheet`, menu **Giornaliera individuale**. Directory
  `/api/admin/presenze/collaborators`, poi giornaliere con mese e ID Presenze
  esplicito del solo dipendente. Identita da snapshot o mapping canonico;
  nessuna associazione tramite nome o uguaglianza fra namespace.
- GAIA: `/presenze/giornaliera-individuale`, stesso nome nel menu Presenze.
  Directory paginata e API giornaliere dettagliate per dipendente/mese, con
  timbrature per la regola del breve anticipo notturno.
- Sono viste di consultazione e stampa/PDF. Le rettifiche continuano nelle
  giornaliere esistenti. GaTe mantiene gli overlay delle azioni pendenti e lo
  scope area/squadra della sua API. Il fallback tecnico da eventi mobile non
  viene presentato come cartellino GAIA.
- Permesso console `monthly-sheet` per admin, viewer e responsabili squadra;
  le liste esplicite di pagine non vengono ampliate automaticamente. Abilitare
  la pagina nella configurazione dell'utente quando usa una lista esplicita.

## Regole implementate

1. Calendario reale del mese, inclusi anni bisestili; sabato/domenica evidenziati.
   L'evidenziazione non determina la categoria paghe: prevalgono i dati GAIA.
2. Minuti sommati come numeri interi. Durate giornaliere e totali in **h:mm**:
   40 minuti + 40 minuti = 1:20. Il foglio Excel usa anche totali decimali;
   non si sommano mai rappresentazioni numeriche ore.minuti.
3. Otto fasce senza sovrapposizione. `export_*` prevale sui campi della UI;
   zero e null espliciti non sono sostituiti da fallback. In assenza di una
   ripartizione, ordinario/extra vengono assegnati alla fascia feriale o
   festiva secondo il flag canonico. Le ripartizioni incoerenti bloccano il
   prospetto invece di produrre un totale apparentemente valido.
4. Per operai, meno di cinque minuti notturni tornano al feriale. Brevi anticipi
   prima delle 06:00 seguono i vincoli OPE0613/OPE0714 del compilatore GaTe:
   coppie complete, anticipo inferiore a 30 minuti, nessuna uscita oltre le
   22:00, turno OPE0714 effettivo completato fino alle 13:00.
5. KM come quantita; trasferta come durata o `M` per montana; reperibilita come
   numero di giornate con quantita positiva. Causali pubblicate prevalenti,
   fallback sui giustificativi noti e riposi DOM/SAB/RIPTURN. Le assenze parziali
   sono visibili ma non contano come giornate interamente assenti; RS escluso.
6. Giorni lavorati con minuti ordinari o extra positivi. Giorni contributivi
   calcolati come lavorati + giustificati senza lavoro + sabati operai maturati
   con cinque giorni ordinari lunedi-venerdi per almeno 38 ore e sabato non
   lavorato. Nessun credito implicito per settimane incomplete fuori mese.
7. Date mancanti restano `—`, distinte da zero. I totali sono riferiti ai soli
   dati disponibili, con conteggio delle date mancanti. Duplicati/date fuori
   mese e numeri negativi/non validi vengono segnalati.

## Limiti espliciti

KM moto, indennita macchine, centro di costo, lavorazione e saldi banca ore non
sono esposti dal contratto giornaliero comune: la pagina li dichiara non
disponibili. Non deduce indennita macchine dai buoni pasto, anche se un template
Excel riutilizza quella riga. Qualifica, mansione e periodo contrattuale del
modello non vengono inventati dalla matricola. I giorni contributivi sono un
calcolo sui record ricevuti, non un certificato di elaborazione paghe.

La directory GaTe contiene i collaboratori disponibili nella cache/directory
operativa: persone storiche assenti da tale directory richiedono prima il
ripristino dello snapshot/mapping sorgente. Nessuna sync o scrittura dati viene
avviata dalla pagina. Nessuna modifica al contratto di sincronizzazione.

## Manutenzione e verifiche

`presenze-monthly-sheet.ts` e le fixture di test sono mantenuti identici nei due
repository (GaTe `services/`, GAIA `frontend/src/lib/`). Le due applicazioni non
condividono un package di distribuzione: aggiornare entrambe le copie quando
cambia una regola, confrontarle e rieseguire gli stessi test. I test verificano
somma dei minuti, otto fasce, riposi, causali, null/zero, bisestili, dati corrotti,
contributivi e corse fra richieste. Il browser non applica nuovi arrotondamenti
paghe o nuove soglie allo straordinario.

Validazione locale: suite mirate, coverage GAIA al 100% dei runtime modificati,
typecheck/lint, ratchet complessita GAIA e controllo Chromium su fixture anonima
per desktop/mobile e stampa A3 orizzontale. Il rilascio in produzione e separato.

### Gate di rilascio — 23 settembre 2026

- GaTe: `npm run test:coverage:monthly-sheet --workspace @gate-mobile/gateway-api`:
  24 test, 100% statements/branches/functions/lines su modello e assemblaggio
  script. Lo stesso comando instrumenta con Istanbul il controller/rendering JS
  emesso, con quattro soglie al 100% verificate da assertion: copre anche
  selezioni concorrenti, logout, errori, directory vuota, stampa e tabella.
  Report in `apps/gateway-api/coverage/monthly-sheet/` (non versionato).
- GaTe suite completa gateway: 421 test passati in 52 file.
  Regressione cache/autorizzazioni: 64 test passati; scope area/squadra e
  permessi espliciti restano applicati alle due API di consultazione.
- GAIA: `VITEST_COVERAGE_INCLUDE=src/lib/presenze-monthly-sheet.ts,src/app/presenze/giornaliera-individuale/page.tsx,src/app/presenze/giornaliera-individuale/table.tsx,src/app/presenze/giornaliera-individuale/use-monthly-sheet.ts,src/components/layout/presenze-navigation.ts npm run test:coverage -- tests/unit/presenze-monthly-sheet.test.ts tests/unit/presenze-monthly-page.test.tsx`
  dalla directory frontend: 12 test, 196/196 statement, 164/164 branch,
  60/60 funzioni, 140/140 linee.
- Questi denominatori riguardano la feature; non dichiarano copertura al 100%
  dell'intero monolite e dei router/asset legacy nei quali e registrata.
- GAIA quality ratchet contro HEAD pre-feature: nessun finding. La
  sincronizzazione della baseline globale non e stata applicata: il comando
  rileva regressioni storiche in file non modificati (fra cui Collaboratori);
  `baseline-verify` resta non riproducibile per quel debito preesistente.
  Non sono state ampliate esclusioni ne modificate soglie per assorbirlo.

### Rilascio

GaTe usa il deploy VPS canonico:

```bash
DOMAIN=static.186.92.233.167.clients.your-server.de DEPLOY_HOST=gate ENV_FILE=.env.vps CONFIGURE_NGINX=0 scripts/deploy-master.sh vps
```

GAIA mantiene il proprio target operativo `/opt/gaia` su `serverCed`; questa
feature richiede soltanto la nuova immagine frontend. Verificare checkout remoto
pulito e commit base, conservare l'immagine precedente per rollback, trasferire
il commit e l'immagine, ricreare solo `frontend` e verificare readiness/route
tramite il proxy. Questo non e un deploy di GaTe al CED. Nessuna migrazione DB,
backfill o modifica a credenziali/configurazione di GAIA e necessaria.
