# Ripristino riproducibilità baseline — 2026-11-03

## Motivo e procedura

La baseline al checkout a6274cac non riproduceva il runtime già committato.
Il normale comando baseline rifiutava17 delta di metriche su due file Poste;
non è stato forzato né modificato il matcher. È stata applicata la procedura
«Riparazione baseline stale su HEAD» di
[QUALITY_RATCHET](../code-quality/QUALITY_RATCHET.md), senza feature runtime
pendenti e senza cambi a esclusioni/soglie/engine.

1. Worktree isolato detached sul commit a6274cac, runtime pulito.
2. Dipendenza parser frontend riusata tramite node_modules ignorato da Git.
3. complexity.py baseline-repair e baseline-verify: exit0, riproducibile true.
4. Riproduzione nel checkout canonico con runtime identico a HEAD; confronto
   completo con il risultato isolato, normalizzando solo root e timestamp.
5. baseline-verify canonico exit0; ratchet autorevole contro merge-base main
   exit0/findings[].270test dello strumento passati.
6. Recupero versionato separatamente dai nuovi test della verifica finale.

Il comando baseline-repair riproduce codice già versionato; non autorizza
regressioni non committate. Il controllo contro la baseline immutabile del
merge-base è stato rieseguito dopo il recupero e resta il gate autorevole.

## Diff semantico revisionato

| Dato | Prima | Dopo |
| --- | --- | --- |
| File runtime baseline | 1835 | 1870 |
| Callable | 21742 | 22099 |
| Error-level non excepted | 1918 | 1918 |
| Warning non excepted | 2845 | 2893 |
| File aggiunti/rimossi | — | 35/0 |
| File esistenti cambiati | — | 8 |

I35file aggiunti sono i componenti runtime Communications. Gli8file esistenti:

- backend/app/api/router.py;
- backend/app/db/base.py;
- frontend/src/components/ruolo/solleciti/workspace.tsx;
- modules/elaborazioni/worker/posta_online_dispatch.py;
- modules/elaborazioni/worker/posta_online_dispatch_portal.py;
- modules/elaborazioni/worker/tests/test_posta_online_dispatch.py;
- modules/elaborazioni/worker/tests/test_posta_online_dispatch_portal.py;
- modules/elaborazioni/worker/tests/test_posta_online_dispatch_runner.py.

Gli ultimi cinque erano già committati prima di Communications e non sono
modificati da questa chiusura. Le differenze testuali della grande lista JSON
includono riordinamento/allineamento di blocchi; la review confronta i callable
per file, non deduce114mila modifiche applicative dal diff serializzato.

Provenienza nuova a6274cac03debeca61380df564aea7be87dfe70f, root canonica
/home/cbo/CursorProjects/GAIA. Scope include/exclude ed engines identici;
nessuna esclusione aggiunta, nessun error-level nuovo assorbito.

Evidenze locali: /tmp/gaia-comm-close-baseline-review.json,
/tmp/gaia-comm-close-baseline-repaired-verify.log,
/tmp/gaia-comm-close-baseline-canonical-verify.log,
/tmp/gaia-comm-close-ratchet-after-repair.json,
/tmp/gaia-comm-close-quality-tools.log.
