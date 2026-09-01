# GAIA — hotfix produzione Sync continua Catasto

**Data:** 2026-08-29 20:32 CEST  
**Stato:** PASS — correzione distribuita e verificata su `serverCed`

## Cosa è noto

La pagina Elaborazioni mostrava il runtime error:

```text
TypeError: Cannot read properties of undefined (reading 'length')
```

Posizione osservata:

```text
frontend/src/components/elaborazioni/continuous-catasto-sync-panel.tsx
SyncConfiguration, riga 210 circa
```

L'espressione interessata leggeva `draft?.credentialIds.length`.

## Causa verificata

Durante il caricamento asincrono della configurazione, i checkbox e i campi SLA erano già interattivi anche se `state.draft` era ancora `null`.

Un'interazione anticipata poteva creare un draft parziale tramite lo spread non sicuro di `current.draft!`. Il render successivo trovava quindi un oggetto `draft` esistente ma senza `credentialIds`, provocando l'accesso a `.length` su `undefined`.

Il test regressivo aggiunto ha riprodotto il difetto come controllo attivo prima del completamento del caricamento ed è risultato rosso prima della correzione.

## Correzione

File runtime:

```text
frontend/src/components/elaborazioni/continuous-catasto-sync-panel.tsx
```

Interventi delimitati:

1. `setDraft` non crea più oggetti parziali quando il draft non è ancora disponibile;
2. la verifica delle credenziali selezionate tollera anche draft legacy/parziali;
3. checkbox priorità e campi SLA restano disabilitati fino al caricamento del draft completo;
4. nessuna modifica a API, database, autenticazione o worker.

Test regressivo:

```text
frontend/tests/unit/elaborazioni-request-workspace-continuous-sync.test.tsx
```

## Verifiche locali

### TDD mirato

Prima della correzione:

```text
1 failed, 8 passed
keeps configuration inputs disabled until the complete draft is loaded: FAIL
```

Dopo la correzione:

```text
9 passed
```

### Coverage file runtime modificato

```text
Statements: 100%
Branches:   100%
Functions:  100%
Lines:      100%
```

### Regressione frontend completa

```text
Test Files: 184 passed
Tests:      1656 passed
```

Sono rimasti warning React `act(...)` già presenti in test non correlati; nessuna failure.

### Altri gate

```text
TypeScript typecheck: PASS
Docker production build frontend: PASS
Next.js optimized production build: PASS
Quality tooling: 46 passed
Complexity ratchet BASE_REF=origin/main: PASS, findings=[]
git diff --check: PASS
```

Complessità del file:

```text
Prima: callables=42, errors=0, cyclomatic_max=12, cognitive_max=14
Dopo:  callables=43, errors=0, cyclomatic_max=13, cognitive_max=15
```

Nessuna violation error-level e nessun aggiornamento di baseline o eccezioni.

## Deploy su serverCed

È stato confrontato il file live con quello locale prima della copia. Le sole differenze erano quelle della correzione descritta.

È stato distribuito esclusivamente:

```text
/opt/gaia/frontend/src/components/elaborazioni/continuous-catasto-sync-panel.tsx
```

Checksum locale e live:

```text
SHA256 84da5720495eac06d873086acf5ac904e9b08d6b67750d9316c503e2d129f592
```

È stato riavviato soltanto il servizio:

```text
gaia-frontend
```

## Verifica produzione

Verifica finale differita:

```text
gaia-frontend: healthy
GET http://127.0.0.1:3000/elaborazioni: 200
Compilazione Next.js /elaborazioni: PASS
TypeError / Cannot read properties nei log recenti: nessuno
```

Backup rollback:

```text
/opt/gaia/backups/hotfixes/2026-08-29-continuous-sync/continuous-catasto-sync-panel.tsx.bak-20260829-203055
```

## Attenzione operativa

Il frontend CED è attualmente eseguito con `next dev` e bind mount del sorgente, non con `next start` su immagine production. Questo spiega la presenza dell'overlay di sviluppo nello screenshot e rende possibile la conservazione di stato Fast Refresh incompatibile durante modifiche live. Non è stato cambiato in questo hotfix per evitare di ampliare lo scope.

## Stato Git

Nessun commit e nessun push eseguiti. Il working tree locale conteneva già modifiche non correlate, preservate integralmente.

## Prossima verifica utente

Ricaricare la pagina Elaborazioni sul telefono e aprire nuovamente la sezione Auto Sync. I controlli devono apparire senza runtime overlay; durante il caricamento iniziale restano temporaneamente disabilitati e diventano interattivi quando la configurazione è disponibile.
