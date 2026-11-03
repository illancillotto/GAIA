# Changelog

## 2026-11-03 — Implementazione iniziale e collaudo isolato

- Audit del checkout e individuazione dei contratti Ruolo/Registro/Poste.
- Outbox Communications, account e template versionati, snapshot binari privati.
- Autorizzazioni individuali, ricevute di rendering, API protette e job persistenti.
- Worker indipendente con trasporti TLS, IMAP readonly, parsing PEC/DSN e audit.
- Nuove pagine PEC/email e amministrazione; viewer PDF.js e checklist.
- Suite sintetica in ampliamento; nessun invio reale o rilascio.

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
- Fingerprint include tutti i metadati sorgente; errori PDF NAS normalizzati.\n- Failed prima di effetti irreversibili annullabili con audit per nuova revisione;\n  evidenze sending/submitted/uncertain impediscono comunque annullamento.\n