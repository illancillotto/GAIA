# Dotazioni — requisiti, execution plan e PROGRESS

## Requisiti e perimetro

Beni del Consorzio con assegnazione a unita canonica e custodia temporanea
alla persona GAIA. Inventory invariato. Riferimenti Network e Vehicle senza
duplicarne l'operativita. Contratti/API e permessi in `README.md`;
matrice comportamento/test ed evidenze in `VALIDATION.md`.

## Stato del ciclo al 2026-10-03

- [x] Asset generico, codice immutabile normalizzato e tipo estensibile.
- [x] OrgUnit/ApplicationUser canonici, permessi granulari e flag modulo.
- [x] Presa, restituzione e passaggio atomici, storico e audit.
- [x] Vincoli FK, indice custodia aperta e prova concorrente PostgreSQL.
- [x] UI lista/dettaglio, filtri custode/unita, azioni e storico.
- [x] Link Network/Vehicle; niente custodia parallela veicoli.
- [x] Rotta autenticata stabile per QR.
- [x] Test dominio/UI/browser e correzione normalizzazione input.
- [x] Rifinitura UX: etichette italiane, date Europe/Rome, nomi nei passaggi,
  storico vuoto esplicito, tabelle scorrevoli/focalizzabili e azioni touch.
- [x] Build pulita via script repository, lint mirato e typecheck.
- [x] Gate della change isolata: ratchet piattaforma, lint e coverage superati;
  evidenze aggiornate in `GATE_CLOSURE_2026-10-03.md`.
- [ ] Baseline globale Wiki/MCP: riconciliazione separata, non assorbita qui.
- [x] Integrazione operatori-cruscotto: custodie via API Dotazioni e identita
  GAIA canonica; test full-file al 100%, branch inclusi.
- [x] E2E cruscotto: retry Chromium superato, inclusa assenza di richieste
  al cambio verso operatore senza mapping; dettagli in `CRUSCOTTO_VALIDATION.md`.
- [x] Change Dotazioni pronta al commit autorizzato; lavori concorrenti esclusi.

## Fuori scope o iterazione successiva

Policy gerarchica capi, etichette QR/PDF, UI audit dedicata, MDM, SIM/contratti,
contabilita cespiti, acquisti e ricambi. Nessuna feature nuova nella verifica.
