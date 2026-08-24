# Frontend Session Bootstrap

Data di introduzione: `2026-08-24`.

## Obiettivo

Ridurre i tempi percepiti durante la navigazione frontend senza indebolire i
controlli di autenticazione e autorizzazione. Prima di questa modifica ogni
istanza di `ProtectedPage` ripeteva le richieste `/auth/me` e
`/auth/my-permissions`; inoltre la home attendeva il completamento dei riepiloghi
dei moduli prima di mostrare il contenuto.

## Disegno runtime

Il bootstrap condiviso vive in:

- `frontend/src/lib/session-bootstrap.ts`: cache in memoria e deduplicazione
  delle richieste;
- `frontend/src/lib/use-session-bootstrap.ts`: stato React, redirect e logout;
- `frontend/src/components/app/protected-page.tsx`: consumo del bootstrap nelle
  pagine protette;
- `frontend/src/app/page.tsx`: bootstrap della home e caricamento non bloccante
  dei widget.

La cache conserva una sola sessione, identificata dal token corrente. Le
proprieta operative sono:

- TTL di `60` secondi per decidere quando rivalidare la sessione;
- una sola coppia di richieste auth anche con consumer concorrenti;
- riuso immediato dello snapshot durante la navigazione client;
- stale-while-revalidate dopo il TTL, senza ripristinare il gate a schermo;
- invalidazione su logout, cambio token ed errore di autenticazione;
- nessuna persistenza aggiuntiva del profilo o dei permessi in `localStorage`.

Gli stati esposti dal hook sono `checking`, `ready`, `anonymous` ed `error`.
Una cache fredda usa `checking` finche identita e permessi non sono disponibili.
Una cache gia verificata usa subito `ready` e rivalida in background.

## Rendering e autorizzazione

Il primo accesso dopo login o refresh completo continua a richiedere la verifica
di identita e permessi. Questo round trip e intenzionale. Nei cambi pagina
successivi `ProtectedPage` puo renderizzare immediatamente usando lo snapshot
verificato.

La home non aspetta piu dashboard, Utenze, Presenze, Ruolo e Catasto per
mostrare la struttura principale. I riepiloghi vengono caricati in background e
un errore parziale non nasconde la pagina. Anche i badge dello shell sono
opzionali e non bloccano il contenuto.

I permessi memorizzati servono soltanto a comporre la UI. Gli endpoint backend
restano l'autorita per ogni operazione protetta. Un errore auth durante la
rivalidazione elimina cache e token e reindirizza a `/login`; un errore di rete
puo mantenere visibile lo snapshot precedente, ma non aggira i controlli server.

## Test e coverage

Il comportamento e caratterizzato da:

- `frontend/tests/unit/session-bootstrap.test.ts`;
- `frontend/tests/unit/use-session-bootstrap.test.tsx`;
- `frontend/tests/unit/protected-page.test.tsx`;
- `frontend/tests/unit/home-page-presence-widget.test.tsx`.

Il gate mirato sui runtime modificati si esegue con:

```bash
cd frontend
VITEST_COVERAGE_INCLUDE='src/app/page.tsx,src/components/app/protected-page.tsx,src/lib/session-bootstrap.ts,src/lib/use-session-bootstrap.ts' \
  npm run test:coverage
```

La soglia richiesta e `100%` per statement, branch, funzioni e righe. I test
coprono TTL, deduplicazione, concorrenza, fallback stale, unmount, logout,
errori auth, navigazione consecutiva e rendering della home con widget pendenti.

## Verifica operativa

Dopo il deploy:

1. aprire la home con una sessione valida e verificare che la struttura appaia
   prima del completamento dei riepiloghi;
2. passare tra due pagine protette e verificare l'assenza del gate "Verifica
   sessione";
3. eseguire il logout e verificare il redirect a `/login`;
4. verificare che una sessione scaduta venga rimossa alla rivalidazione.

La modifica non introduce variabili ambiente, endpoint o migrazioni database.
