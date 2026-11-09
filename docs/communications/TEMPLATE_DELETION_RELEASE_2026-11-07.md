# Eliminazione template — rilascio CED del 7 novembre 2026

Rilascio mirato autorizzato dall'utente, attivato alle **09:42:21 CET**.
Il pulsante **Elimina** con conferma è disponibile in `/gaia/communications`.
Backend e frontend healthy; worker, credenziali, account e trasporti invariati.
Nessun template reale cancellato e nessun messaggio inviato durante il collaudo.

## Perimetro effettivamente pubblicato

| Servizio | Immagine precedente | Immagine attiva |
| --- | --- | --- |
| Backend | `3eba82eb04dc` | `b259894c1ad4` |
| Frontend | `d8dbf6a70ffd` | `bf73b599a3e8` |

Entrambe le immagini derivano dal runtime effettivamente in uso sul CED,
con build senza rete e dipendenze esistenti. Il frontend preserva anche
l'aggiornamento Avventizi pubblicato prima di questo rilascio. Non viene
distribuito l'intero checkout locale, che contiene lavoro concorrente.

Cambiano solo quattro file runtime, identici ai byte verificati durante
lo sviluppo:

- `backend/app/modules/communications/admin.py`;
- `backend/app/modules/communications/registry.py`;
- `backend/app/modules/communications/schemas.py`;
- `frontend/src/components/communications/admin-templates.tsx`.

Confronto integrale: **988 file Python backend e 770 file frontend preservati**;
196 route frontend invariate. Environment, mount, entrypoint, comandi,
healthcheck, risorse, policy e reti dei due servizi coincidono con i precedenti.
Ricreati solo backend e frontend, con `--no-deps --no-build --pull never`;
eseguiti `nginx -t` e reload. I 36 altri container permanenti sono invariati.
I container temporanei esterni al ciclo non sono inclusi in questo conteggio.

## Controlli realmente eseguiti

| Verifica | Esito |
| --- | --- |
| Collaudo locale del codice | 197 backend, inclusi dieci PostgreSQL, PASS; dettagli nel rapporto sviluppo |
| Suite nell'immagine backend candidata, rete disabilitata | 187 PASS, dieci PG skip già verificati localmente, zero failure/error |
| Unit frontend sulla sorgente candidata | 63 PASS; componente modificato 100% statement/branch/function/line |
| Typecheck e lint del componente candidato | PASS |
| Build immagini backend/frontend | PASS; route frontend preservate |
| Browser sulla candidata CED | Sei E2E PASS, zero skip/flaky/failure |
| Browser sulla versione pubblicata | Sei E2E PASS, zero skip/flaky/failure |
| Stato container e configurazione effettiva | Backend/frontend healthy; configurazioni precedenti preservate |
| HTTP attraverso nginx | Sette GET200; API amministrativa anonima401 |
| GET autenticati template/operatori, account e monitoraggio | Quattro endpoint200 |
| Nuovo DELETE senza cancellazione reale | UUID inesistente404; conferma falsa422; richiesta anonima401 |
| Stato dati Communications | Conteggi e hash integrale delle quattro righe template invariati |
| Schema e trasporto | Revisione `20261104_1400` invariata; pausa globale true, trasporto false |

Gli E2E usano Chromium reale, PDF sintetici e API intercettate: verificano
desktop/mobile, conferma, annullamento, errore/retry e regressione PEC/email.
Non sono test di provider reali e non cancellano template del Consorzio.
Il probe API effettivo usa GET e DELETE di un UUID verificato inesistente.

Stato Communications prima/dopo: due account, quattro template, zero messaggi,
cinque job, zero autorizzazioni e zero ricevute. Nessuna nuova migrazione,
modifica dei recapiti o dei dati tributari. Il worker Communications conserva
immagine `2879ad8d18a9` e lo stesso container.

Il primo test nell'immagine ha rilevato l'assenza del file SQL di supporto
al test dei grant. Aggiunto il solo mount readonly al container di test;
la seconda suite completa è passata, senza modificare codice o grant reali.
I warning runpy e i warning build nei moduli estranei restano documentati.

## Artefatti e rollback

Directory protetta CED: `/opt/gaia/releases/template-delete-20261107`.
Contiene manifest/hash, sorgenti congelati, immagini/tag, configurazioni
precedenti e nuove, risultati, script, `PREPARED.json`,
`CANDIDATE_CHECKED.json`, `ACTIVATED.json` e `POST_RELEASE.json`.

Backup mirato delle quattro righe template in formato PostgreSQL custom,
con checksum e indice archivio verificati. Non è un nuovo backup completo
e non è stato eseguito un restore di prova in questo ciclo; il rilascio
applicativo non richiede modifiche ai dati.

Rollback applicativo: dopo verifica dell'assenza di release successive,
usare `backend.rollback.json` e `frontend.rollback.json` dalla stessa directory
per i soli servizi omonimi, poi health e reload nginx. Le immagini precedenti
sono conservate. Non ripristinare il database né riattivare template eliminati
dagli operatori per annullare il solo rilascio software. Il vecchio selettore
operativo esclude già gli stati diversi da approved.

Evidenza versionata senza segreti:
[TEMPLATE_DELETION_RELEASE_2026-11-07.json](evidence/TEMPLATE_DELETION_RELEASE_2026-11-07.json).
Log e test locali: `/tmp/gaia-template-delete-release-20261107/`.
Nessun commit/push eseguito.

Il gate globale del checkout non viene riclassificato: restano i rilievi
Presenze estranei registrati nel [rapporto sviluppo](TEMPLATE_DELETION_2026-11-07.md).
Il rilascio applica solo la modifica richiesta sopra il runtime precedente.
