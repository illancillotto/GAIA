# Cancellazione squadre richiesta da GATE

Il job outbound `gate-mobile-sync` elabora la pending action
`propose_team_delete`, con `payload.operation=delete_team`, autore canonico
`gaia_user_id` e riferimenti `team.team_id` / `team.personnel_area`.

`gate_mobile_team_actions.apply_presenze_team_proposal` verifica che l'autore
sia attivo e amministratore Presenze (`admin` o `hr_manager` abilitato al
modulo, oppure `super_admin`). E ammesso anche il ruolo console
`console_admin` attestato da un unico `WCOperator` canonico attivo, abilitato
alla console, con utente attivo e modulo Presenze abilitato. Risolve la squadra per UUID o per
`gate_mobile_team_id`, verifica l'area e cancella squadra, membership e
assegnazioni dei responsabili nella stessa transazione. Utenti, collaboratori,
timbrature e giornaliere restano conservati.

Se la squadra e gia assente, GAIA restituisce comunque l'ACK: la riconsegna
dopo un errore di rete non deve fallire una cancellazione gia eseguita.
Gli errori vengono riportati tramite il normale endpoint fail delle pending
action e restano visibili in GATE, dove l'amministratore puo riprovare.

Distribuire questo supporto GAIA prima della versione GATE che accoda la nuova
azione. GATE mantiene un marcatore locale per impedire la ricomparsa causata
da snapshot tardivi e non consente il ripristino locale dopo l'invio a GAIA.
Le vecchie cancellazioni solo locali richiedono un nuovo comando esplicito;
non viene eseguita alcuna cancellazione retroattiva automatica.

Verifica GAIA 2026-10-01: inclusa nei 136 test backend del riesame refresh/sync.
Coperti UUID e ID esterno, riconsegna idempotente, area incoerente, permessi
admin/HR/super-admin e console-admin canonico unico, preservazione di persone
e giornaliere. Coverage intero servizio team-actions 100% statement e branch;
style e complexity ratchet passati. Nessuna cancellazione produttiva eseguita.
