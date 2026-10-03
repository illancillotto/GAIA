# Guida utente HTTPS nella home

La home `/` e la pagina pubblica `/login` mostrano una guida espandibile
«Accedere a GAIA in HTTPS · Windows, macOS e Linux». E disponibile anche
senza autenticazione, tramite il layout principale. Non appare negli altri
moduli e non modifica sessioni, login, autorizzazioni o chat Wiki legacy.

La guida spiega rete aziendale/VPN, pacchetto CED e verifica dell'impronta,
installazione CA sui tre sistemi, riavvio browser, nuovo login HTTPS e
diagnosi di errori DNS/certificati. Non richiede dati sensibili ne chiavi.
Non consiglia di ignorare avvisi TLS, disattivare SmartScreen o protezioni.

## Stato corrente

La nuova CA GAIA e ancora da creare e approvare con il CED. L'indirizzo
previsto `https://gaia.lan` e mostrato come testo, non come collegamento
gia operativo. Nessun installer e pubblicato dalla guida: i pacchetti
preparati con la CA Kiosk sono sospesi e non vanno distribuiti.
La sola modifica UI non abilita HTTPS sul server e non esegue un deploy.

Per iniziare il login HTTPS reale occorrono nuova CA, distribuzione trust,
certificato server SAN gaia.lan, DNS, reverse proxy e collaudo CED.
Procedura: `domain-docs/mcps/CLIENT_CA_INSTALLERS.md`.
Dopo il collaudo, aggiornare lo stato nella guida con una change dedicata;
pubblicare solo pacchetti approvati, firma di release e impronta verificata.

La guida riguarda GAIA in rete interna, non il connettore remoto Claude.
La CA interna non rende gaia.lan raggiungibile o attendibile da Anthropic.

## Implementazione e test

- `frontend/src/components/security/https-access-guide.tsx`: guida per le
  sole route home/login, disclosure nativa, pass-through del contenuto pagina.
- `frontend/src/app/layout.tsx`: integrazione senza modifica delle pagine
  legacy home/login o degli hook di autenticazione.
- `frontend/tests/unit/https-access-guide.test.tsx`: visibilita delle route,
  tre sistemi, apertura/chiusura, contenuto di sicurezza, nessun download,
  mantenimento del contenuto e del widget Wiki nel layout.

```bash
cd frontend
VITEST_COVERAGE_INCLUDE=src/app/layout.tsx,src/components/security/https-access-guide.tsx npm run test:coverage -- tests/unit/https-access-guide.test.tsx tests/unit/home-page-presence-widget.test.tsx
```

Gate: 100% statement/branch/function/line dei due file runtime toccati;
lint frontend e ratchet mirato contro origin/main. Graphify frontend usa
il target Make AST locale; nessuna estrazione docs verso modelli esterni.
