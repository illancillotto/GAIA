# PROMPT CODEX — GAIA CED

Implementa `GAIA CED` come convergenza pianificata di `GAIA NAS Control` e
`GAIA Rete` dentro la piattaforma GAIA, rispettando questi vincoli:

## Obiettivo

Creare un nuovo modulo frontend `CED` che diventi l'entrypoint unico per le
funzionalita NAS e Rete, senza introdurre nella prima fase un nuovo backend
dedicato e senza rompere i path esistenti.

## Vincoli architetturali

- backend unico monolite modulare
- nessun nuovo backend `app/modules/ced` nella prima fase
- riuso dei backend esistenti:
  - NAS -> `accessi`
  - Rete -> `network`
- mantenere i permessi attuali:
  - `module_accessi`
  - `module_rete`

## Route target

- `/ced`
- `/ced/nas`
- `/ced/nas/sync`
- `/ced/nas/users`
- `/ced/nas/groups`
- `/ced/nas/shares`
- `/ced/nas/effective-permissions`
- `/ced/nas/reviews`
- `/ced/nas/reports`
- `/ced/rete`
- `/ced/rete/devices`
- `/ced/rete/alerts`
- `/ced/rete/scans`
- `/ced/rete/floor-plan`

## Strategia di implementazione richiesta

1. introdurre il namespace frontend `frontend/src/app/ced/*`
2. aggiornare home, login e sidebar per mostrare `GAIA CED`
3. aggiungere `currentModuleKey = "ced"` e la relativa module sidebar
4. riusare le viste esistenti di `nas-control` e `network`
5. mantenere in vita le route legacy finche non e definito esplicitamente un redirect
6. non cambiare le API backend se non strettamente necessario

## Regole di accesso richieste

- `/ced` accessibile se l'utente ha `accessi` o `rete`
- `/ced/nas/*` accessibile solo se l'utente ha il modulo/permessi NAS attuali
- `/ced/rete/*` accessibile solo se l'utente ha il modulo/permessi Rete attuali

## File che probabilmente saranno impattati

- `frontend/src/app/page.tsx`
- `frontend/src/app/login/page.tsx`
- `frontend/src/components/layout/platform-sidebar.tsx`
- `frontend/src/components/layout/sidebar.tsx`
- `frontend/src/components/layout/module-sidebar.tsx`
- `frontend/src/app/ced/*`

## Criteri di qualita

- non rompere `NAS Control` e `Rete`
- mantenere naming coerente tra piattaforma, sidebar e route
- introdurre il minimo cambiamento necessario per ogni fase
- aggiornare la documentazione impattata
- aggiungere test o smoke test dove ha senso

## Cosa evitare

- creare un backend `ced` solo per allineamento nominale
- fondere prematuramente `module_accessi` e `module_rete`
- eliminare i path legacy senza piano esplicito
- riscrivere da zero pagine stabili se basta un wrapper
