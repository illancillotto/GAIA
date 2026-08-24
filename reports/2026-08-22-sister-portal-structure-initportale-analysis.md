# GAIA/SISTER — Analisi struttura portale e comportamento `initPortale` HTTP 501

Data: 2026-08-22 01:02 CEST circa  
Ambiente: locale `/home/cbo/CursorProjects/GAIA`  
Scope: analisi HAR/HTML/JS e probe Chromium read-only con credenziale importata localmente  
Server CED: non modificato  
Sicurezza: username, CF, password, token e cookie non riportati.

## Domanda

Ale ha chiesto di verificare come si comporta realmente il portale SISTER/Agenzia Entrate, perché il `501` su:

```text
https://portale.agenziaentrate.gov.it/portale-rest/rs/initPortale
```

sembra anomalo.

## Fonti analizzate

### Trace/HAR già acquisiti

```text
/home/cbo/CursorProjects/GAIA/tmp/sister-debug-artifacts/debug-runs/20260821T222858Z/sister-debug.har
/home/cbo/CursorProjects/GAIA/tmp/sister-debug-artifacts/debug-runs/20260821T223528Z/sister-debug.har
/home/cbo/CursorProjects/GAIA/tmp/sister-debug-artifacts/debug-runs/20260821T223644Z/sister-debug.har
```

### HTML finali già acquisiti

```text
/home/cbo/CursorProjects/GAIA/tmp/sister-debug-artifacts/connection-tests/20260821T222902Z/final-state.html
/home/cbo/CursorProjects/GAIA/tmp/sister-debug-artifacts/connection-tests/20260821T223531Z/final-state.html
/home/cbo/CursorProjects/GAIA/tmp/sister-debug-artifacts/connection-tests/20260821T223648Z/final-state.html
```

### Bundle JS portale estratti dal trace

```text
/home/cbo/CursorProjects/GAIA/tmp/sister-portal-analysis/app.bundle.80b7c9e9a69cce1da07f.js
/home/cbo/CursorProjects/GAIA/tmp/sister-portal-analysis/2.bundle.20b773e7df357d2f6e60.js
/home/cbo/CursorProjects/GAIA/tmp/sister-portal-analysis/10.bundle.5554c3f9172dd4022458.js
/home/cbo/CursorProjects/GAIA/tmp/sister-portal-analysis/11.bundle.7a4c07839ef6c5d6bc9d.js
/home/cbo/CursorProjects/GAIA/tmp/sister-portal-analysis/vendors.bundle.1d96816fc5aed16562b1.js
```

### Nuovo probe Chromium read-only

Script:

```text
/home/cbo/CursorProjects/GAIA/tmp/sister_portal_readonly_probe.py
```

Run:

```text
/home/cbo/CursorProjects/GAIA/tmp/sister-debug-artifacts/readonly-runs/20260821T225828Z/
```

Artefatti principali:

```text
summary.json
network.jsonl
readonly.har
readonly-trace.zip
01-login-page.html/png/json
02-post-login-stable.html/png/json
99-after-close-session.html/png/json
```

Il probe read-only ha fatto solo:

1. apertura login IAMPE;
2. submit credenziale SISTER importata in locale;
3. attesa stato post-login;
4. snapshot DOM/rete;
5. logout/close session.

Non ha cliccato menu visure, non ha confermato privacy SISTER, non ha compilato visure.

## Mappa reale del flusso osservato

La sequenza comune nei trace è:

```text
1. GET  https://iampe.agenziaentrate.gov.it/sam/UI/Login?realm=/agenziaentrate
2. POST https://iampe.agenziaentrate.gov.it/api/login/sister              -> 200
3. GET  https://portale.agenziaentrate.gov.it/PortaleWeb/home             -> 200
4. GET  https://portale.agenziaentrate.gov.it/portale-rest/rs/initPortale -> 501
5. GET  https://sp.agenziaentrate.gov.it/ret2sister3                     -> 302
6. GET  https://sister3.agenziaentrate.gov.it/Servizi/indexPI.jsp         -> 200
7. POST https://sister3.agenziaentrate.gov.it/Servizi/AccessoPortaleAE    -> 302
8a. GET https://sister3.agenziaentrate.gov.it/Servizi/                    -> 200 Home dei Servizi
oppure
8b. GET https://sister3.agenziaentrate.gov.it/Servizi/error_locked.jsp     -> 200 Utente bloccato
```

Quindi il `501` non è l'ultimo step e non decide da solo l'esito SISTER.

Il vero bivio operativo visto nei trace è il redirect di:

```text
POST /Servizi/AccessoPortaleAE
```

che può andare a:

```text
/Servizi/
```

oppure a:

```text
/Servizi/error_locked.jsp
```

## Evidenza: stessi 501, due esiti diversi

### Run buono — 501 ma Home SISTER raggiunta

Trace:

```text
20260821T222858Z
```

Rete:

```text
501 GET /portale-rest/rs/initPortale
302 GET /ret2sister3 -> /Servizi/indexPI.jsp
302 POST /Servizi/AccessoPortaleAE -> /Servizi/
200 GET /Servizi/
```

Pagina finale:

```text
title: Home dei Servizi
body: Home dei Servizi, Consultazioni e Certificazioni, Esci
```

### Run bloccati — stesso 501 ma redirect SISTER a locked page

Trace:

```text
20260821T223528Z
20260821T223644Z
20260821T225828Z
```

Rete:

```text
501 GET /portale-rest/rs/initPortale
302 GET /ret2sister3 -> /Servizi/indexPI.jsp
302 POST /Servizi/AccessoPortaleAE -> /Servizi/error_locked.jsp
200 GET /Servizi/error_locked.jsp
```

Pagina finale:

```text
title: Utente bloccato
body: Utente gia' in sessione sulla stessa o altra postazione.
```

## Che cos'è `indexPI.jsp`

Il contenuto di `indexPI.jsp` è un ponte HTML minimo:

```html
<form name="accesso" method="post" action="AccessoPortaleAE">
  <input type="hidden" name="primoAccesso" value="1">
</form>
<script type="text/javascript">
  document.forms.accesso.submit();
</script>
```

Quindi `ret2sister3` non entra direttamente nella Home; passa da una POST server-side SISTER con:

```text
primoAccesso=1
```

È questa POST (`AccessoPortaleAE`) che valuta la sessione applicativa SISTER e decide se aprire `/Servizi/` o mandare a `error_locked.jsp`.

## Struttura della Home SISTER valida

Quando l'accesso riesce, la Home contiene:

```text
Home dei Servizi
Consultazioni e Certificazioni
Gestione Utenza
Assistenza
Esci
```

Link principali estratti dal DOM:

```text
Esci:
https://sister3.agenziaentrate.gov.it/Servizi/CloseSessionsSis

Consultazioni e Certificazioni:
/Servizi/SceltaServizio.do?area=Consultazioni e Certificazioni

Gestione Utenza:
/Servizi/SceltaServizio.do?area=Gestione Utenza
```

Nella Home valida è presente anche un form privacy:

```text
form name: PrivacyFB
method: POST
action: /Servizi/InformativaPrivacy.do
submit values: Conferma, Annulla
```

Testo rilevante:

```text
Informativa trattamento dei dati personali
La mancata conferma di presa visione non consentirà all'Agenzia l'erogazione del servizio richiesto.
```

Questo è un blocco funzionale successivo: per arrivare alle visure, il worker GAIA oggi clicca `Conferma` in `_maybe_accept_privacy_notice()`. Nel probe read-only non l'ho cliccato.

## Struttura della pagina locked

Quando SISTER blocca la sessione, la pagina contiene:

```text
Utente gia' in sessione sulla stessa o altra postazione.
```

Link presenti:

```text
Esci:
https://sister3.agenziaentrate.gov.it/Servizi/CloseSessionsSis

Chiudi:
https://sister3.agenziaentrate.gov.it/Servizi/CloseSessionsSis
```

Menu diverso dalla Home valida:

```text
Adesione ai servizi
Primo Accesso Responsabile
Servizi disponibili
Assistenza
```

Non contiene `Consultazioni e Certificazioni`.

## Analisi del bundle `PortaleWeb`

Nel bundle:

```text
2.bundle.20b773e7df357d2f6e60.js
```

`initPortale` è definito come path SPA:

```text
PATH_INIT = /rs/initPortale
```

Il componente principale fa una chiamata Ajax verso questo path all'avvio della SPA `/PortaleWeb/home`.

Il codice osservato tratta il `501` in modo speciale:

```text
200 != response.status -> error=true
501 == response.status && header X_RED presente -> init=false
```

In sintesi: il frontend PortaleWeb sa che un `501` può avere un significato applicativo specifico, ma si aspetta header come:

```text
X_RED
```

Nei nostri HAR il `501` arriva così:

```text
status: 501
content-type: application/json
body: vuoto
X_RED: assente
```

Quindi sì: il `501` è anomalo/incompleto rispetto alla logica prevista dal bundle. Però non impedisce automaticamente il redirect `ret2sister3` né la POST `AccessoPortaleAE`.

## Classificazione del 501

### Non va più classificato come sempre fatale

Evidenza: nel run `20260821T222858Z`, dopo il 501 il browser è arrivato a:

```text
https://sister3.agenziaentrate.gov.it/Servizi/
Home dei Servizi
Consultazioni e Certificazioni
```

Quindi se GAIA abortisce immediatamente appena vede il 501, può fermarsi prima di riconoscere una sessione SISTER operativa.

### Non va nemmeno ignorato sempre

Evidenza: nei run bloccati, dopo lo stesso 501 il portale arriva a:

```text
/Servizi/error_locked.jsp
Utente gia' in sessione sulla stessa o altra postazione.
```

Qui il problema è reale e non va bypassato.

### Classificazione corretta

```text
initPortale 501 + Home SISTER operativa = warning / non bloccante
initPortale 501 + error_locked.jsp = session lock / bloccante
initPortale 501 senza Home/menu SISTER = errore portale / global pause
```

## Perché il 501 sembra strano

È strano per due motivi:

1. Il bundle PortaleWeb prevede un caso speciale per `501` con header `X_RED`, ma il server risponde `501` senza quell'header.
2. Nonostante il `501`, il flusso prosegue su `sp.agenziaentrate.gov.it/ret2sister3`, quindi il 501 sembra appartenere alla SPA dell'Area Riservata Agenzia Entrate, non al vero gate applicativo SISTER.

Possibile spiegazione tecnica: `initPortale` è un'inizializzazione della SPA PortaleWeb che fallisce/parzialmente fallisce per sessione/utenza Sister, ma il meccanismo legacy `ret2sister3 -> indexPI.jsp -> AccessoPortaleAE` resta separato e continua.

## Implicazioni su GAIA

La patch locale già fatta è coerente ma va raffinata semanticamente:

```text
Non decidere sul solo status HTTP 501.
Decidere sullo stato finale SISTER e sul DOM operativo.
```

Il worker dovrebbe modellare stati distinti:

```text
portal_init_501_seen
sister_home_ready
sister_privacy_pending
sister_locked_session
sister_portal_unavailable
sister_visura_area_ready
```

Oggi GAIA ha già parte della logica:

```text
_wait_for_post_login_state()
_maybe_accept_privacy_notice()
_goto_visura_menu_with_retry()
_confirm_visura_informativa_if_present()
_select_convention_if_present()
```

Ma la telemetria e la classificazione errori dovrebbero separare meglio:

```text
initPortale 501 osservato
AccessoPortaleAE -> /Servizi/ OK
AccessoPortaleAE -> /Servizi/error_locked.jsp KO
privacy pending
visure menu opened
convenzione selected
```

## Probe read-only live del 20260821T225828Z

Esito:

```text
final post-login url: https://sister3.agenziaentrate.gov.it/Servizi/error_locked.jsp
title: Utente bloccato
body: Utente gia' in sessione sulla stessa o altra postazione.
```

Network:

```text
initPortale: 501
AccessoPortaleAE: 302 -> /Servizi/error_locked.jsp
```

Logout finale:

```text
https://iampe.agenziaentrate.gov.it/sam/UI/Logout?realm=/agenziaentrate
Logout effettuata con successo
```

Quindi il probe ha chiuso la sessione dopo l'ispezione.

## Conclusione operativa

Il `501` è reale e anomalo, ma non è necessariamente la causa terminale del blocco.

La causa terminale osservata nei run falliti è:

```text
POST /Servizi/AccessoPortaleAE -> /Servizi/error_locked.jsp
Utente gia' in sessione sulla stessa o altra postazione.
```

La causa del falso negativo GAIA invece è:

```text
GAIA vede initPortale 501 e lo tratta come fatal prima di controllare se SISTER è arrivato a Home dei Servizi.
```

## Raccomandazione tecnica

1. Mantenere il fix locale `initPortale 501 non bloccante solo con Home SISTER operativa`.
2. Migliorare la telemetria aggiungendo eventi separati:
   - `portal_init_501_seen`
   - `sister_access_portale_ae_redirect_home`
   - `sister_access_portale_ae_redirect_locked`
   - `sister_privacy_notice_pending`
   - `sister_home_ready`
3. Non riprendere un batch massivo finché un probe singolo non dimostra almeno:
   - login riuscito;
   - `AccessoPortaleAE -> /Servizi/`;
   - privacy gestita consapevolmente;
   - menu `Consultazioni e Certificazioni` raggiunto;
   - area visure pronta o convenzione selezionabile.
4. Se si vuole verificare l'accesso completo alle visure, serve consenso esplicito a confermare l'informativa privacy SISTER (`/Servizi/InformativaPrivacy.do`) perché è una presa visione lato portale.

## Stato finale

- Worker locale persistente: fermo.
- Probe read-only: completato.
- Sessione aperta dal probe: chiusa con logout.
- Server CED: non modificato.
- Patch locale precedente: ancora presente, non deployata.
