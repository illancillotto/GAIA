# Organigramma squadre Presenze e sezione HR GATE

Stato 07/11/2026: implementazione locale, nessun rilascio o collegamento reale
applicato in questa attività. Il report GATE è
`docs/PRESENZE_HR_VERIFICATION_20261107.md` nel checkout dedicato al ciclo HR.

## Contratto e autorizzazioni

Le squadre correnti sono `organization_teams`; il ponte legacy
`org_unit.legacy_team_id → team` non collega questa anagrafica. La nuova tabella
`presenze_team_organization` associa esplicitamente una squadra a un'unità
canonica dell'organigramma, conservando autore e data di aggiornamento.
Non si deducono associazioni da nomi, appartenenze o uguaglianze di ID.

GET `/gate/presenze/team-organizations` restituisce collegamenti e percorsi
canonici attivi. PUT `/gate/presenze/teams/{team_id}/organization` riceve:

```json
{"org_unit_id": null, "expected_org_unit_id": null}
```

I due valori possono essere UUID. `org_unit_id=null` scollega la squadra;
`expected_org_unit_id` confronta il collegamento letto dall'editor. Il salvataggio
blocca la squadra nella transazione e restituisce 409 se il legame è cambiato,
404 per squadra assente, 422 per unità assente/inattiva/non canonica.
Entrambe le route richiedono ruolo admin, super_admin o hr_manager e modulo
Presenze. L'editor si trova nel dettaglio squadra di Presenze → Squadre.

Il singolo builder `gate_mobile_team_snapshot.py`, condiviso da push e pull,
aggiunge `organization` al payload squadre esistente: `unit_id` e `path`, con
ID, nome, tipo e `leaders` di ciascun nodo. Gli incarichi provengono soltanto
da `position_code=capo_settore|capo_reparto`, sono attivi e riferiti a utenti
attivi. Le decorrenze `valid_from`/`valid_to` vengono conservate; GATE filtra
gli incarichi per il mese selezionato. Gerarchie cicliche o incomplete producono
un collegamento non disponibile, senza inferenze o crash del feed squadre.

Il ruolo console `hr_manager` è accettato dagli schemi operatori e dal percorso
pending action esistente, ed è selezionabile nella UI operatori. In GATE dà
accesso a tutte le aree, consultazione/rettifiche e download Excel/PDF.
L'organigramma non amplia le squadre autorizzate dei responsabili: l'invio
mensile resta limitato alle assegnazioni GATE esistenti.

## Migration e rilascio coordinato

La migration `20261107_0900`, successiva a `20261106_1000`, aggiunge la tabella
senza riscrivere squadre o anagrafiche. Team e unità hanno FK con CASCADE;
l'autore con SET NULL. Il downgrade rifiuta di perdere legami ancora presenti:
scollegare esplicitamente prima del rollback.

Distribuire prima il contratto aggiornato GATE/connector, poi migration e
backend/UI GAIA. Solo dopo abilitare HR e configurare i collegamenti reali.
Emettere `hr_manager` verso un vecchio consumer che lo rifiuta bloccherebbe
il ciclo completo operatori/Presenze. Nessun cambiamento all'invariante
outbound-only del connector o al fail-hard delle aree canoniche.

## Verifiche e limiti

Test di associazione/API/sync e migration PostgreSQL usano dati sintetici e
schemi isolati: `backend/tests/test_presenze_team_organization*.py` e suite
`test_gate_mobile_sync*` / `test_operazioni_mobile_sync*`. Frontend:
`presenze-team-organization.test.tsx`, `presenze-pages.test.tsx` e
`gate-console-roles.test.ts`. Test, coverage e ratchet del ciclo sono registrati
nel report GATE e nei log locali `/tmp/gate-hr-20261107/`.

DONE: editor esplicito, concorrenza, pipeline e contratto. PARTIAL: chiusura
dei gate globali dei repository. RESIDUAL: configurazione dei collegamenti e
abilitazioni reali. OUT OF SCOPE: deploy e modifiche ai dati sorgente INAZ.
