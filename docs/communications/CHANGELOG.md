# Changelog

## 2026-11-03 — Implementazione iniziale e collaudo isolato

- Audit del checkout e individuazione dei contratti Ruolo/Registro/Poste.
- Outbox Communications, account e template versionati, snapshot binari privati.
- Autorizzazioni individuali, ricevute di rendering, API protette e job persistenti.
- Worker indipendente con trasporti TLS, IMAP readonly, parsing PEC/DSN e audit.
- Nuove pagine PEC/email e amministrazione; viewer PDF.js e checklist.
- Suite sintetiche e regressioni descritte in TEST_REPORT; nessun invio reale o rilascio.

- Recovery: tentativi e Registro coerenti con uncertain dopo crash/eccezione;
  lease token mai restituito da dispatch.
- Health per processo, overlay senza privilegi/root filesystem scrivibile,
  grants allowlist e configurazioni prive di credenziali.
- Backend123PASS,100% statement/branch; frontend89PASS nel perimetro,100%;
  regressione frontend5468PASS e Ruolo1090PASS/407SKIP.
- Chromium reale: quattro flussi PEC/email desktop/mobile con PDF tre pagine.
- Guide provider ufficiali consultate; nessun test su casella reale.
- Documentazione completa: configurazione, operatore, collaudo, rilascio/rollback,
  decisioni esterne, integrazione Registro/Poste e limiti della conservazione.
- Fingerprint include tutti i metadati sorgente; errori PDF NAS normalizzati.
- Failed prima di effetti irreversibili annullabili con audit per nuova revisione;
  evidenze sending/submitted/uncertain impediscono comunque annullamento.
- Suite backend completa:8015PASS/471SKIP, nessuna failure; skip mantenuti visibili.
- Regressione worker Posta Online:166PASS su12file, incluse6 prove PG reali isolate.
- Ripetuti quattro flussi Chromium sull'ultima build; ESLint mirato senza errori.
- Fixture PDF classificata binaria con attributo Git specifico, senza modificarne i byte.
- Ratchet finale PASS; sincronizzazione baseline rifiutata per metriche Poste
  preesistenti fuori perimetro, senza modificare baseline o soglie.

## Commit locali

- 40b324ac: backend, migrazione, outbox, trasporti, worker e test sintetici.
- 599e1ccf: interfaccia PEC/email/amministrazione, PDF.js, test e documentazione.
- Chiusura: report finali, attributo binario fixture e limite baseline documentato.

Nessun push, PR, merge o deployment eseguito.
