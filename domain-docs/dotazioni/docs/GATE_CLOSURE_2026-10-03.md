# Dotazioni — chiusura della verifica della change, 2026-10-03

## Perimetro e risultato

Verifica del solo diff Dotazioni sul commit `e33d5c69`, esportato in un
worktree detached con indice temporaneo. Non comprende i lavori concorrenti
Presenze, GIS, Ruolo, Wiki/MCP, Elaborazioni o i loro documenti. Inventory
invariato; nessun push, deploy o intervento sui database operativi.

**Gate differenziale della change: PASS.** I precedenti report `VALIDATION.md`
e `CRUSCOTTO_VALIDATION.md` conservano evidenze storiche, non rappresentano
l'esito corrente del diff isolato. Questo risultato non certifica la suite
globale del working tree concorrente o la sincronizzazione globale baseline.

## Correzioni dei blocchi Dotazioni

- Repository utenti: usa direttamente il booleano gia validato dello schema,
  senza una conversione ridondante; persiste il flag Dotazioni.
- Bootstrap admin: un solo percorso di assegnazione e persistenza per utente
  nuovo/esistente, mantenendo password, ruolo, moduli e commit/refresh.
- Bootstrap sezioni: creazione e prima abilitazione della custodia operatore
  hanno una responsabilita esplicita. Sezioni gia esistenti e override non
  vengono sovrascritti nei successivi bootstrap.
- Editor utenti: mapping DTO/form puro, simmetrico al mapping di invio;
  password vuota, invito disabilitato e conversione del flag facoltativo invariati.
- Tipi API piattaforma: contratto comune `PlatformModuleAccess` elimina le
  dichiarazioni duplicate. Restano invariati campi obbligatori/facoltativi
  e differenze tra lettura, creazione e aggiornamento.

Metriche prima/dopo delle correzioni, non confronto tra tutte le feature del
branch e un vecchio remoto:

| Responsabilita | Cognitiva | Ciclomatica | LOC |
| --- | --- | --- | --- |
| `create_application_user` | 3 -> 3 | 4 -> 4 | 29 -> 28 |
| `ensure_bootstrap_admin` | 1 -> 1 | 2 -> 2 | 46 -> 25 |
| `ensure_default_sections` | 5 -> 3 | 4 -> 3 | 19 -> 12 |
| nuovo `create_default_section` | 1 | 2 | 8 |
| nuovo `formStateForUser` | 0 | 1 | 21 |
| file tipi piattaforma | nessun callable | nessun callable | 513 -> 491 |

Non viene dichiarata una riduzione globale del debito: editor legacy e altri
hotspot restano in baseline. Nessun wrapper artificiale, esclusione nuova,
indebolimento dei test o trasferimento di violation sopra soglia.

## Verifiche ripetute sullo snapshot isolato

- Backend: **102 test passati**, suite `backend/tests/dotazioni/` e bootstrap,
  sezioni, gestione utenti, auth e auth service. PostgreSQL 16 reale isolato:
  upgrade/downgrade/re-upgrade della migration e presa concorrente eseguiti,
  nessuno skip del test PostgreSQL. Cluster fermato al termine.
- Coverage full-file: tutti gli otto file dominio, migration e otto runtime
  piattaforma modificati al **100% statement e branch**, nessuna esclusione
  aggiunta. Dominio 447/447 statement e 78/78 branch; migration 27/27 e 6/6.
- Frontend: **115 test passati** in nove suite Dotazioni, utenti, cruscotto,
  navigazione e drawer. Coverage dei runtime dominio e delle tre integrazioni:
  **933/933 statement, 960/960 branch, 336/336 funzioni, 801/801 linee**, 100%.
- `make lint-backend BASE_REF=HEAD` sullo snapshot: PASS. Nuovi file Python
  controllati anche dal formatter; ESLint mirato e `tsc --noEmit
  --incremental false` sul checkout di lavoro: PASS.
- Scanner completo `complexity.py ratchet --base-ref HEAD` sullo snapshot:
  **exit 0, findings vuoti**, baseline autorevole del merge-base `e33d5c69`.
  Parser Babel disponibile, nuovi runtime registrati nell'indice isolato.
- Whitespace e revisione del perimetro: PASS. Artefatti generati, lockfile
  estraneo e hunk dei lavori concorrenti esclusi dal commit.

Le prove browser/build precedenti restano nei report storici: non sono state
ripetute in questa verifica e non si presentano come nuovi risultati. Non e
stata eseguita una nuova suite globale backend/frontend.

## Baseline globale: limite distinto e non assorbito

Dopo il ratchet verde, il comando esplicito `complexity.py baseline` sullo
snapshot rifiuta l'aggiornamento: **23 finding Wiki/MCP**, in sorgenti identiche
a HEAD e non toccate da Dotazioni. Nessun finding appartiene alla change.
La baseline versionata precede quelle modifiche gia committate. Non viene
rigenerata per assorbirle, ne si dichiara `baseline-verify` verde. La
riconciliazione globale resta una change separata come gia deciso dall'utente.

Ripetuto lo stesso comando sul worktree HEAD senza Dotazioni: 24 finding,
contro i 23 della change; nessun finding nuovo. L'unico finding eliminato e
la crescita LOC preesistente di `getModuleSections`. Le 23 voci residue sono
identiche alla prova sul commit base; baseline e scope restano invariati.

Log e coverage di questa verifica: `/tmp/gaia-dotazioni-gates-isolated-*`,
typecheck/ESLint `/tmp/gaia-dotazioni-gates-*`; metriche iniziali e dopo le
prime correzioni `/tmp/gaia-dotazioni-gates-{before,after}.{json,md}`.
Gli artefatti Graphify restano ignorati e non vengono versionati.

Graphify aggiornato tramite target dedicati Dotazioni/backend/frontend:
pruning force applicato ai grafi codice, poi refresh finale frontend dopo
la deduplicazione dei tipi. Docs dominio e piattaforma: `chunk 1/1 done`,
nessun warning di semantic chunk falliti. Costi stimati del primo refresh
docs di chiusura: $0.0092 dominio e $0.0062 piattaforma; report dominio
risincronizzato dopo l'aggiunta della prova sul commit base.
