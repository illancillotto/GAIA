# Istruzioni operative per Hermes

## Scelta dell'orchestrazione

Usa `/goal` per audit, implementazione del tooling e refactoring. Un goal ha un
contratto di completamento e viene rivalutato dopo ogni turno.

Non usare `/loop` per modificare ripetutamente il codice. Il loop e temporizzato
ed e adatto a polling, CI o attese esterne. Le istruzioni opzionali sono in
`HERMES_LOOP_MONITORING.md`.

## Preparazione della sessione

1. Apri Hermes dalla root del checkout GAIA.
2. Verifica che il progetto abbia caricato il `AGENTS.md` corretto.
3. Controlla `git status --short --branch`.
4. Non cambiare branch se ci sono modifiche non correlate non comprese.
5. Verifica che esista
   `skills/gaia-complexity-reduction/SKILL.md` nel checkout.
6. Non installare la skill in `~/.hermes/skills` e non modificare
   `~/.hermes/config.yaml`: i goal ordinano a Hermes di leggerla dal progetto.
7. Avvia il goal di fase appropriato dalla root di GAIA.

## Branch e Git

Nome suggerito per la fondazione:

```text
gaia/complexity-quality-ratchet
```

Nome suggerito per un hotspot:

```text
refactor/complexity-<module>-<short-name>
```

Hermes non deve:

- creare commit o push senza richiesta esplicita;
- fare force push;
- ripulire o ripristinare modifiche dell'utente;
- cambiare branch protection o secrets;
- accettare automaticamente una baseline piu permissiva.

## Quality gate Hermes

Dopo che la Fase 1 ha creato e verificato i target Make, aggiungi al goal di
refactoring:

```text
/goal gate add make quality-test
/goal gate add make complexity-ratchet BASE_REF=origin/main
/goal gate add make complexity-baseline-verify
```

Aggiungi il ratchet solo dopo che la baseline e presente nel branch base.
`complexity-check` da solo non e un gate anti-regressione autorevole. Aggiungi
solo comandi che esistono e passano localmente. Per un hotspot, aggiungi anche il
comando di test mirato realmente usato dal modulo. Non inserire un gate
placeholder e non puntare a una suite non disponibile. Il code style vive in
`docs/CODE_STYLE.md` e `make style-ratchet`; non e un sostituto di questi gate.

Comandi di controllo del goal:

```text
/goal status
/goal show
/goal pause
/goal resume
/goal clear
```

Usa `/goal pause` quando e necessaria una decisione umana. Non trasformare una
decisione architetturale o di dominio in una supposizione per far proseguire il
judge.

## Verifica prima di editare

Hermes deve sempre:

- leggere i file di contesto e la documentazione del programma;
- identificare la ownership del modulo;
- trovare test esistenti e invarianti;
- acquisire metriche prima;
- per un hotspot, descrivere la slice e i file previsti in `PROGRESS.md`;
- per il ratchet ordinario, registrare scope e metriche nel riepilogo della
  change senza ampliare il registro centrale;
- separare failure preesistenti da regressioni.

## Verifica dopo l'edit

Ordine minimo:

1. formatter/lint del solo perimetro;
2. test di caratterizzazione o unitari mirati;
3. coverage dei file runtime modificati;
4. ratchet contro la baseline del merge-base;
5. type-check/build per frontend quando applicabile;
6. suite piu ampia compatibile con tempo e servizi disponibili;
7. sincronizzazione e verifica della baseline corrente;
8. diff review con `git diff --check` e `git diff --stat`;
9. aggiornamento `PROGRESS.md` per tooling/hotspot o riepilogo della change per
   il ratchet ordinario.

Non dichiarare verde un comando non eseguito. Riporta esattamente comando,
risultato e limite.

## Stop condition

Fermati e chiedi indicazioni se:

- il comportamento atteso non e deducibile dai test o dalla documentazione;
- servirebbe cambiare API, schema DB, auth o semantica di dominio;
- le modifiche dell'utente si sovrappongono al lavoro;
- una dipendenza richiede un upgrade framework;
- la baseline ha matching ambiguo;
- una riduzione locale aumenta il debito aggregato;
- la copertura richiesta non e raggiungibile senza cambiare il perimetro;
- compare una nuova failure non spiegata;
- il goal supera una singola unita revisionabile.

## Configurazione Hermes opzionale

Nel profilo locale si puo abilitare `verify_on_stop` senza modificare GAIA:

```yaml
agent:
  verify_on_stop: auto
  max_verify_nudges: 3

goals:
  max_turns: 20

loops:
  max_ticks: 12
```

Non inserire questo frammento nel repository come configurazione attiva e non
sovrascrivere altre chiavi di `~/.hermes/config.yaml`.
