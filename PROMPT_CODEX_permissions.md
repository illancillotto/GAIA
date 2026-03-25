# PROMPT_CODEX — GAIA Permission System
## Milestone 8: Gestione utenti, moduli e permessi granulari per sezione

> Prompt operativo per Codex. Da usare come system prompt o primo messaggio in una sessione dedicata.
> Repository: `github.com/illancillotto/GAIA`
> Branch di lavoro consigliato: `feature/permission-system`

---

## Contesto del progetto

Stai lavorando su **GAIA**, una piattaforma IT governance per il Consorzio di Bonifica dell'Oristanese.

Il repository è un monorepo con tre moduli:
- `modules/accessi/` — NAS Audit (backend + frontend completati, base di questa milestone)
- `modules/network/` — Network Monitor (in sviluppo, solo docs)
- `modules/inventory/` — IT Inventory (in sviluppo, solo docs)

Lo stack è: FastAPI + SQLAlchemy + Alembic + PostgreSQL per il backend, Next.js + React + TypeScript + TailwindCSS per il frontend. L'infrastruttura è Docker Compose + Nginx.

Il backend esistente si trova in `modules/accessi/backend/`. Il frontend in `modules/accessi/frontend/`. Tutte le modifiche di questa milestone vanno dentro questi due path, senza creare nuovi container o servizi.

---

## Stato attuale del repository

### Già implementato e funzionante

**Backend:**
- `ApplicationUser` con ruoli `admin`, `reviewer`, `viewer`
- JWT auth: `POST /auth/login`, `GET /auth/me`
- Dependency `require_active_user` in `app/api/deps.py`
- CRUD completo NAS: utenti, gruppi, share, review, permessi effettivi, snapshot, sync
- 59 test pytest verdi

**Frontend:**
- Login reale contro backend
- Dashboard collegata
- Viste NAS: utenti, gruppi, share, review, sync, effective permissions
- Sidebar con navigazione applicativa

### Da implementare in questa milestone

Tutto il codice per questa milestone va scritto da zero nei path indicati.
**Non toccare** i file esistenti salvo quelli indicati esplicitamente nella sezione "File da modificare".

---

## Obiettivo della milestone

Implementare un sistema di accesso a tre livelli:

1. **Moduli** — quali sezioni GAIA l'utente può usare (accessi / rete / inventario)
2. **Ruolo** — `super_admin` | `admin` | `reviewer` | `viewer` con permessi base diversi
3. **Sezioni** — controllo granulare per utente su ogni sezione configurabile nel DB

### Logica di risoluzione permessi (ordine di precedenza)

```
1. super_admin              → accesso totale, bypass di tutto
2. user_section_permissions → override esplicito per utente (granted / denied)
3. role_section_permissions → default del ruolo sulla sezione
4. section.min_role         → se rank(ruolo utente) >= rank(min_role)
5. fallback                 → denied
```

Gerarchia ruoli per confronto `min_role`:
```python
ROLE_HIERARCHY = {
    "super_admin": 4,
    "admin":       3,
    "reviewer":    2,
    "viewer":      1,
}
```

---

## Schema DB da creare

### Migration: `20260324_0008_section_permissions.py`
`down_revision = "20260323_0007"` (ultima migration esistente)

**Tabella `application_users` — modifiche** (migration separata `20260323_0007`):
```sql
ALTER TABLE application_users
  ADD COLUMN module_accessi    BOOLEAN NOT NULL DEFAULT TRUE,
  ADD COLUMN module_rete       BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN module_inventario BOOLEAN NOT NULL DEFAULT FALSE;
-- Il campo role deve accettare anche "super_admin" (già VARCHAR(32), nessuna modifica strutturale)
```

**Nuove tabelle** (migration `20260324_0008`):
```sql
CREATE TABLE sections (
    id          SERIAL PRIMARY KEY,
    module      VARCHAR(50)  NOT NULL,       -- "accessi" | "rete" | "inventario"
    key         VARCHAR(100) NOT NULL UNIQUE, -- es. "accessi.export"
    label       VARCHAR(200) NOT NULL,
    description TEXT,
    min_role    VARCHAR(32)  NOT NULL DEFAULT 'admin',
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    sort_order  INTEGER      NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE role_section_permissions (
    id             SERIAL PRIMARY KEY,
    section_id     INTEGER NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
    role           VARCHAR(32) NOT NULL,
    is_granted     BOOLEAN NOT NULL DEFAULT FALSE,
    updated_by_id  INTEGER REFERENCES application_users(id) ON DELETE SET NULL,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (section_id, role)
);

CREATE TABLE user_section_permissions (
    id             SERIAL PRIMARY KEY,
    user_id        INTEGER NOT NULL REFERENCES application_users(id) ON DELETE CASCADE,
    section_id     INTEGER NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
    is_granted     BOOLEAN NOT NULL,
    granted_by_id  INTEGER REFERENCES application_users(id) ON DELETE SET NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, section_id)
);
```

---

## File da creare — Backend

Tutti i file vanno in `modules/accessi/backend/`.

### `alembic/versions/20260323_0007_user_modules.py`
Aggiunge `module_accessi`, `module_rete`, `module_inventario` ad `application_users`.
`down_revision = "20260323_0006"`.

### `alembic/versions/20260324_0008_section_permissions.py`
Crea le tre tabelle sopra descritte.
`down_revision = "20260323_0007"`.

### `app/models/application_user.py` ← SOSTITUISCI
Aggiorna il modello esistente aggiungendo:
- `ApplicationUserRole.SUPER_ADMIN = "super_admin"`
- colonne `module_accessi`, `module_rete`, `module_inventario` (Boolean)
- property `is_super_admin: bool`
- property `enabled_modules: list[str]` che ritorna la lista dei moduli abilitati;
  per `super_admin` ritorna sempre `["accessi", "rete", "inventario"]` indipendentemente dai flag

### `app/models/section_permission.py` ← NUOVO
ORM models per `Section`, `RoleSectionPermission`, `UserSectionPermission`.
Relazioni SQLAlchemy con `relationship` e `cascade="all, delete-orphan"`.

### `app/core/security.py` ← SOSTITUISCI
`create_access_token(user_id, role, modules)` deve includere `role` e `modules` nel payload JWT.

### `app/services/auth.py` ← SOSTITUISCI
`issue_access_token(user)` chiama `create_access_token` passando `user.role` e `user.enabled_modules`.

### `app/services/permission_resolver.py` ← NUOVO
Contiene:
- `ROLE_HIERARCHY: dict[str, int]`
- `@dataclass ResolvedPermission(section_key, section_label, module, is_granted, source)`
  dove `source` è uno di: `"super_admin"` | `"user_override"` | `"role_default"` | `"min_role"` | `"denied"`
- `resolve_user_permissions(db, user) -> list[ResolvedPermission]`
  Ritorna permessi resolved per tutte le sezioni attive dei moduli abilitati
- `can_access_section(db, user, section_key) -> bool`
  Check singolo per dependency FastAPI

### `app/api/deps.py` ← SOSTITUISCI
Mantieni tutto il contenuto esistente, aggiungi:
- `require_section(section_key: str)` — factory dependency che chiama `can_access_section`
- `require_role(*roles: str)` — factory dependency per ruolo
- `RequireAdmin = Depends(require_role("super_admin", "admin"))`
- `RequireSuperAdmin = Depends(require_role("super_admin"))`

### `app/schemas/auth.py` ← SOSTITUISCI
`CurrentUserResponse` aggiunge:
```python
module_accessi: bool
module_rete: bool
module_inventario: bool
enabled_modules: list[str]
```

### `app/schemas/users.py` ← NUOVO
Schema CRUD per `ApplicationUser`:
- `ApplicationUserCreate` (include `password`, `role`, `is_active`, i tre `module_*`)
- `ApplicationUserUpdate` (tutti opzionali, include `password` opzionale)
- `ApplicationUserResponse` (include `enabled_modules: list[str]`)
- `ApplicationUserListResponse(items, total)`
- Validator: password >= 8 caratteri

### `app/schemas/permissions.py` ← NUOVO
- `SectionCreate`, `SectionUpdate`, `SectionResponse`
- `RoleSectionPermissionResponse`
- `BulkRolePermissionsRequest(permissions: list[{role, is_granted}])`
- `UserSectionPermissionResponse`
- `BulkUserPermissionsRequest(permissions: list[{section_id, is_granted}])`
- `ResolvedPermissionResponse(section_key, section_label, module, is_granted, source)`
- `MyPermissionsResponse(sections, granted_keys: list[str])`
- `UserPermissionsAdminView(user_id, username, role, resolved, overrides)`

### `app/repositories/application_user.py` ← SOSTITUISCI
Aggiunge a quello esistente:
- `list_application_users(db, skip, limit, role, is_active) -> tuple[list, int]`
- `create_application_user(db, payload: ApplicationUserCreate) -> ApplicationUser`
- `update_application_user(db, user, payload: ApplicationUserUpdate) -> ApplicationUser`
- `delete_application_user(db, user) -> None`
- mantieni le funzioni `get_by_username` e `get_by_id` esistenti
- aggiungi `get_application_user_by_email`

### `app/repositories/section_permission.py` ← NUOVO
- CRUD per `Section`: `list_sections`, `get_section_by_id`, `get_section_by_key`, `create_section`, `update_section`, `deactivate_section`
- `create_section` deve chiamare `_seed_role_defaults` che popola automaticamente `role_section_permissions` in base a `min_role`: `super_admin` e tutti i ruoli con rank >= rank(min_role) ottengono `is_granted=True`
- `get_role_permissions_for_section`, `bulk_update_role_permissions` (upsert)
- `get_user_overrides(db, user_id)`, `bulk_update_user_permissions` (upsert), `delete_user_override`

### `app/api/routes/admin_users.py` ← NUOVO
Router con prefisso `/admin/users`, tag `admin — users`. Accesso riservato a `super_admin` e `admin`.

Endpoint:
- `GET /admin/users` — lista con filtri `role`, `is_active`, paginazione `skip`/`limit`
- `POST /admin/users` — crea utente; solo `super_admin` può creare altri `super_admin`
- `GET /admin/users/{id}` — dettaglio
- `PUT /admin/users/{id}` — aggiorna; protezione: `admin` non può modificare `super_admin`
- `DELETE /admin/users/{id}` — solo `super_admin`; non può eliminare se stesso
- `PATCH /admin/users/{id}/modules` — aggiorna solo i flag moduli via query params

### `app/api/routes/section_permissions.py` ← NUOVO
Tre sub-router:

**`auth_permissions_router`** (tag `auth`):
- `GET /auth/my-permissions` → `MyPermissionsResponse`

**`sections_router`** (prefisso `/sections`, tag `sections`):
- `GET /sections` — lista, accesso `admin+`, filtri `module`, `active_only`
- `POST /sections` — crea, solo `super_admin`; 409 se key duplicata
- `GET /sections/{id}` — dettaglio, `admin+`
- `PUT /sections/{id}` — aggiorna, solo `super_admin`
- `DELETE /sections/{id}` — soft delete (is_active=False), solo `super_admin`
- `GET /sections/{id}/role-permissions` — default ruoli, `admin+`
- `PUT /sections/{id}/role-permissions` — bulk upsert, solo `super_admin`

**`admin_permissions_router`** (prefisso `/admin/users`, tag `admin — permissions`):
- `GET /admin/users/{id}/permissions` → `UserPermissionsAdminView`
- `PUT /admin/users/{id}/permissions` — bulk upsert override; `admin` non può modificare `super_admin` o altri `admin`
- `DELETE /admin/users/{id}/permissions/{section_id}` — rimuove override, torna al default di ruolo

### `app/api/router.py` ← SOSTITUISCI
Registra i nuovi router nell'`api_router` esistente:
```python
from app.api.routes.admin_users import router as admin_users_router
from app.api.routes.section_permissions import (
    admin_permissions_router,
    auth_permissions_router,
    sections_router,
)
api_router.include_router(admin_users_router)
api_router.include_router(auth_permissions_router)
api_router.include_router(sections_router)
api_router.include_router(admin_permissions_router)
```

### `app/scripts/bootstrap_admin.py` ← SOSTITUISCI
Crea un utente `super_admin` con tutti e tre i flag modulo `True`.
Legge `BOOTSTRAP_ADMIN_USERNAME`, `BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_PASSWORD` da env.

### `app/scripts/bootstrap_sections.py` ← NUOVO
Script idempotente che crea le sezioni di default se non esistono.

Sezioni da creare (key, label, module, min_role):

**accessi:**
- `accessi.dashboard` / "Dashboard Accessi" / viewer
- `accessi.users` / "Utenti NAS" / viewer
- `accessi.groups` / "Gruppi NAS" / viewer
- `accessi.shares` / "Cartelle condivise" / viewer
- `accessi.permissions` / "Permessi effettivi" / viewer
- `accessi.reviews` / "Review accessi" / reviewer
- `accessi.export` / "Export" / reviewer
- `accessi.sync` / "Sincronizzazione NAS" / admin
- `accessi.snapshots` / "Snapshot" / admin

**rete:**
- `rete.dashboard` / "Dashboard Rete" / viewer
- `rete.devices` / "Dispositivi" / viewer
- `rete.map` / "Mappa di rete" / viewer
- `rete.alerts` / "Alert" / viewer
- `rete.scan` / "Scansione manuale" / admin
- `rete.export` / "Export rete" / reviewer

**inventario:**
- `inventario.dashboard` / "Dashboard Inventario" / viewer
- `inventario.devices` / "Dispositivi IT" / viewer
- `inventario.warranties` / "Garanzie" / viewer
- `inventario.assignments` / "Assegnazioni" / viewer
- `inventario.import` / "Import CSV" / admin
- `inventario.export` / "Export inventario" / reviewer
- `inventario.locations` / "Sedi" / admin

Per ogni sezione creata, popola `role_section_permissions` con `is_granted=True` per tutti i ruoli con rank >= rank(min_role) e `False` per gli altri. `super_admin` è sempre `True`.

### `app/db/base.py` ← SOSTITUISCI
Aggiunge i nuovi modelli agli import:
```python
from app.models.section_permission import (
    RoleSectionPermission, Section, UserSectionPermission
)
```

### `app/models/__init__.py` ← SOSTITUISCI
Aggiunge ai re-export: `Section`, `RoleSectionPermission`, `UserSectionPermission`.

### `tests/test_user_management.py` ← NUOVO
Test per la gestione utenti. Copertura minima:
- login ritorna token
- `/auth/me` include `enabled_modules` e campi modulo
- lista utenti con `admin`
- creazione utente con moduli specifici
- login utente creato mostra solo i moduli abilitati
- PATCH moduli su utente esistente
- viewer non accede a `/admin/users` (403)
- username duplicato (409)
- non si può eliminare il proprio account (400)
- `super_admin` con flag modulo False ottiene comunque tutti i moduli

### `tests/test_section_permissions.py` ← NUOVO
Test per il sistema permessi. Copertura minima:
- `super_admin` accede a tutto con source `"super_admin"`
- viewer accede a sezione con `min_role=viewer` via source `"min_role"`
- viewer negato su sezione con `min_role=admin` via source `"denied"`
- `role_default` con `is_granted=False` nega accesso nonostante `min_role` favorevole; source `"role_default"`
- `user_override granted=True` sblocca sezione normalmente negata; source `"user_override"`
- `user_override granted=False` nega sezione normalmente accessibile; source `"user_override"`
- DELETE override ripristina accesso via `min_role`
- sezioni di modulo non abilitato non appaiono in `/auth/my-permissions`
- viewer non può creare sezioni (403)
- admin non può modificare permessi di altri admin (403)
- key duplicata (409)

---

## File da creare — Frontend

Tutti i file vanno in `modules/accessi/frontend/src/`.

### `types/user.ts` ← NUOVO
```typescript
type ApplicationUserRole = "super_admin" | "admin" | "reviewer" | "viewer"
type GaiaModule = "accessi" | "rete" | "inventario"

interface ApplicationUser {
  id, username, email, role, is_active,
  module_accessi, module_rete, module_inventario,
  enabled_modules: GaiaModule[],
  created_at, updated_at
}
// + ApplicationUserCreate, ApplicationUserUpdate, ApplicationUserListResponse
// + ROLE_LABELS: Record<ApplicationUserRole, string>
// + MODULE_LABELS: Record<GaiaModule, string>
```

### `types/permissions.ts` ← NUOVO
```typescript
type PermissionSource = "super_admin" | "user_override" | "role_default" | "min_role" | "denied"

interface Section { id, module, key, label, description, min_role, is_active, sort_order, ... }
interface RoleSectionPermission { id, section_id, role, is_granted, updated_at }
interface UserSectionPermission { id, user_id, section_id, is_granted, granted_by_id, ... }
interface ResolvedPermission { section_key, section_label, module, is_granted, source }
interface MyPermissionsResponse { sections: ResolvedPermission[], granted_keys: string[] }
interface UserPermissionsAdminView { user_id, username, role, resolved, overrides }
// + SectionCreate, SectionUpdate, BulkRolePermissionsRequest, BulkUserPermissionsRequest
// + SOURCE_BADGE: Record<PermissionSource, { label: string, className: string }>
```

### `types/api.ts` ← MODIFICA
`CurrentUser` aggiunge:
```typescript
module_accessi: boolean
module_rete: boolean
module_inventario: boolean
enabled_modules: string[]
```

### `services/users.ts` ← NUOVO
Client API per tutti gli endpoint `/admin/users`:
`listUsers`, `getUser`, `createUser`, `updateUser`, `updateUserModules`, `deleteUser`.
Usa `getStoredAccessToken()` e `NEXT_PUBLIC_API_BASE_URL`.

### `services/permissions.ts` ← NUOVO
Client API per il sistema permessi:
- `fetchMyPermissions()` → `/auth/my-permissions`
- `listSections(params?)`, `createSection`, `updateSection`, `deactivateSection`
- `getSectionRolePermissions(sectionId)`, `updateSectionRolePermissions(sectionId, payload)`
- `getUserPermissions(userId)`, `updateUserPermissions(userId, payload)`, `deleteUserSectionOverride(userId, sectionId)`

### `hooks/useCurrentUser.ts` ← SOSTITUISCI
Aggiunge:
- `canAccessModule(module: GaiaModule) -> boolean`
- `hasRole(...roles: string[]) -> boolean`

### `hooks/usePermissions.ts` ← NUOVO
```typescript
function usePermissions(): {
  can: (sectionKey: string) => boolean,
  resolved: ResolvedPermission[],
  grantedKeys: string[],
  isLoading: boolean,
  error: string | null,
  refetch: () => Promise<void>,
}
```
Carica `GET /auth/my-permissions` al mount. `super_admin` ritorna `can()=true` immediatamente senza aspettare il caricamento.

### `components/UserForm.tsx` ← NUOVO
Form riutilizzabile per create e edit di `ApplicationUser`.
- Props: `existingUser?: ApplicationUser`
- In edit: username disabilitato, password opzionale
- Mostra toggle moduli visivi (tre bottoni con stato enabled/disabled) solo se ruolo != `super_admin`
- Se ruolo = `super_admin`: mostra banner "accesso completo a tutti i moduli"
- Dropdown ruoli: `super_admin` visibile solo se `currentUser.role === "super_admin"`

### `app/admin/layout.tsx` ← NUOVO
Layout per tutta la sezione `/admin`.
- Guard: se non autenticato → redirect `/login`; se ruolo non è `admin` o `super_admin` → redirect `/`
- Sub-header con breadcrumb: "← GAIA Home / Amministrazione / [link sezione corrente]"

### `app/admin/users/page.tsx` ← NUOVO
Lista utenti applicativi. Funzionalità:
- tabella con colonne: username, email, ruolo (badge), stato (badge), moduli abilitati, azioni
- filtri: ruolo, stato attivo/disabilitato
- moduli abilitati: per utenti non `super_admin`, mostrare badge cliccabili per ogni modulo che fanno toggle immediato via `PATCH /admin/users/{id}/modules`; per `super_admin` mostrare "Tutti i moduli"
- azioni: "Modifica" → `/admin/users/{id}/edit`, "Permessi" → `/admin/users/{id}/permissions`, "Elimina" (solo `super_admin`, non sul proprio account)
- pulsante "+ Nuovo utente" → `/admin/users/new`

### `app/admin/users/new/page.tsx` ← NUOVO
Render di `<UserForm />` senza props.

### `app/admin/users/[id]/edit/page.tsx` ← NUOVO
Carica `getUser(id)`, poi render di `<UserForm existingUser={user} />`.

### `app/admin/users/[id]/permissions/page.tsx` ← NUOVO
Gestione override permessi per un utente specifico.

Layout:
- breadcrumb: Utenti / {username} / Permessi
- header con: nome utente, ruolo base, numero override attivi
- se ci sono modifiche pendenti: banner con contatore + pulsanti "Annulla" e "Salva modifiche"
- sezioni raggruppate per modulo, ogni modulo in una card

Per ogni sezione nella card:
- label + key (monospace, piccolo)
- badge sorgente (colorato, da `SOURCE_BADGE`)
- toggle on/off
- se la sezione ha modifiche pendenti: badge "modificato" in amber

Comportamento toggle:
- prima click: aggiunge pending override con valore opposto all'attuale
- click su pending esistente con override nel DB: segna per cancellazione (torna al default)
- click su pending esistente senza override nel DB: rimuove il pending

Al salvataggio: upsert i pending non-null, DELETE i pending null, poi reload.

Per `super_admin`: toggle disabilitato, mostra "Sempre attivo" al posto del toggle.
Per `admin` che modifica altro `admin`: toggle disabilitato (protezione).

### `app/admin/sections/page.tsx` ← NUOVO
Gestione sezioni configurabili.

Layout:
- header con titolo, contatore sezioni attive/totali, pulsante "+ Nuova sezione" (solo `super_admin`)
- sezioni raggruppate per modulo in card espandibili

Per ogni sezione nella card:
- label, key (monospace), `min_role`
- badge "disattiva" se `is_active=False`
- pulsante "Default ruoli" (espande inline)
- pulsante "Disattiva" (solo `super_admin`, solo se `is_active=True`)

Pannello "Default ruoli" (inline, caricato on-demand):
- griglia 4 colonne, una per ruolo
- ogni cella: label ruolo + toggle
- `super_admin`: mostra "Sempre" (non modificabile)
- gli altri ruoli: toggle che chiama `PUT /sections/{id}/role-permissions`
- toggle disabilitato se l'utente non è `super_admin`

Form "Nuova sezione" (inline, visibile solo se `super_admin` e form aperto):
- campi: modulo (select), key, label, ruolo minimo (select, senza `super_admin`)
- submit chiama `POST /sections`

### `components/layout/sidebar.tsx` ← SOSTITUISCI
Usa `usePermissions()` per la navigazione adattiva.

Struttura navigazione:
```
← GAIA Home

[se hasModule("accessi")]
  ACCESSI NAS
  can("accessi.dashboard")   → Dashboard
  can("accessi.users")       → Utenti
  can("accessi.groups")      → Gruppi
  can("accessi.shares")      → Cartelle condivise
  can("accessi.permissions") → Permessi effettivi
  can("accessi.reviews")     → Review accessi  [badge reviewBadge]
  can("accessi.export")      → Export
  can("accessi.sync")        → Sincronizzazione

[se hasModule("rete")]
  RETE
  can("rete.dashboard")  → Dashboard
  can("rete.devices")    → Dispositivi
  can("rete.map")        → Mappa di rete
  can("rete.scan")       → Scansione
  can("rete.export")     → Export

[se hasModule("inventario")]
  INVENTARIO
  can("inventario.dashboard")  → Dashboard
  can("inventario.devices")    → Dispositivi IT
  can("inventario.warranties") → Garanzie
  can("inventario.import")     → Import CSV
  can("inventario.export")     → Export

[se isAdmin]
  AMMINISTRAZIONE
  → Gestione utenti      (/admin/users)
  → Sezioni e permessi   (/admin/sections)
```

---

## Applicare `require_section` agli endpoint esistenti

Modifica i seguenti endpoint nel backend esistente:

```python
# app/api/routes/sync.py
@router.post("/sync/live-apply")
def live_apply(user = Depends(require_section("accessi.sync"))):

# app/api/routes/audit.py (o dove si trovano le review)
@router.post("/reviews")
def create_review(user = Depends(require_section("accessi.reviews"))):

@router.put("/reviews/{id}")
def update_review(user = Depends(require_section("accessi.reviews"))):

# app/api/routes/... (exports)
@router.get("/exports/effective-permissions.csv")
def export_csv(user = Depends(require_section("accessi.export"))):

@router.get("/exports/effective-permissions.xlsx")
def export_xlsx(user = Depends(require_section("accessi.export"))):
```

Tutti gli altri endpoint di lettura NAS restano con `require_active_user` — il filtraggio avviene lato frontend tramite `can()`. Solo le operazioni di scrittura e le azioni sensibili richiedono `require_section`.

---

## Aggiungere target Makefile

Nel `Makefile` esistente alla radice, aggiungere:

```makefile
bootstrap-sections:
	docker compose exec backend python -m app.scripts.bootstrap_sections

bootstrap-admin:
	docker compose exec backend python -m app.scripts.bootstrap_admin
```

(Se `bootstrap-admin` esiste già, aggiornare il target per usare il nuovo script che crea `super_admin`.)

---

## Convenzioni da rispettare

- **Nessun hardcoding** di credenziali, URL o segreti
- **Nessun Redux** — usare React state e custom hooks
- **Stile UI** coerente con il resto del frontend: TailwindCSS, colore primario `#1D4E35`, border-radius `rounded-xl` / `rounded-2xl`, font size `text-sm`
- **Errori HTTP** coerenti: 400 per bad request, 401 per non autenticato, 403 per non autorizzato, 404 per not found, 409 per conflict
- **Logging** delle operazioni critiche (creazione utenti, modifiche permessi) con il logger esistente
- **Type hints** completi in Python, TypeScript strict nel frontend
- **Test** per ogni nuovo service/repository — usare `sqlite:///:memory:` per i test backend
- **Idempotenza** per tutti gli script di bootstrap
- **Soft delete** per le sezioni (campo `is_active`), hard delete solo per gli utenti (con protezione)

---

## Checklist di completamento

- [ ] Migration `20260323_0007` crea le tre colonne modulo su `application_users`
- [ ] Migration `20260324_0008` crea `sections`, `role_section_permissions`, `user_section_permissions`
- [ ] `ApplicationUser` ha `super_admin`, i flag modulo e la property `enabled_modules`
- [ ] JWT include `role` e `modules` nel payload
- [ ] `require_section("accessi.sync")` blocca utenti senza accesso alla sezione
- [ ] `/auth/my-permissions` ritorna `sections` e `granted_keys`
- [ ] Bootstrap sections crea le 23 sezioni di default con auto-grant corretto
- [ ] CRUD `/admin/users` completo con protezioni ruolo
- [ ] Override utente ha precedenza su default ruolo
- [ ] Default ruolo ha precedenza su `min_role`
- [ ] `super_admin` bypassa tutto
- [ ] Sezioni di modulo non abilitato non appaiono nei permessi resolved
- [ ] Sidebar mostra solo le voci a cui l'utente ha accesso
- [ ] Pagina permessi utente mostra badge sorgente e toggle funzionanti
- [ ] Pagina sezioni permette gestione default per ruolo
- [ ] Test backend verdi (aggiungono a 59 esistenti, non rompono nulla)
- [ ] `make bootstrap-sections` funziona dopo `make migrate`
- [ ] `PROGRESS.md` e `EXECUTION_PLAN.md` aggiornati con stato Milestone 8
