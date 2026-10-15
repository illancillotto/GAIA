# R91 — Nuovo ambiente privato vincolato al candidato R90

## Scope e snapshot

Autorizzazione esplicita: «Autorizzo solo preparazione e review del nuovo ambiente
privato, senza servizi o E2E». Ambiente predisposto come sorgenti, manifest e piano
di attivazione ipotetico, **non stack attivato**. Nessun servizio/systemd action,
probe/socket/HTTP, browser, E2E/collection/test/build/scanner, DB API/apertura/copia/
mutazione, driver repair, commit o main edit. Global campaign INCOMPLETE.

Checkout `/home/cbo/CursorProjects/GAIA-campaign-20261008-integration`, branch
`refactor/complexity-campaign-20261008`, HEAD
`7f39510ab1ef1d4e531d8b12a4eb6b36f556cee4`, main/merge-base
`a51a48dc4caefbdd1aea82fe4d749054b9465970`. BASE_REF=main invariato;
originale55a1b1d storico. Residui concorrenti non adottati né committati.

## Identità nuova e provenienza

Root esterna durevole:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/r91-private-environment/`.
Preparazione in `preparation/`, nuova nonce
`5cc96152760d4c6da5421a7dbde0ed1b`, stem `gaiar915cc96152760d4c6da5421a7dbde0ed1b`.
Futuri `service-run` e `candidate-runs/native-r91` assenti; non riutilizzati run,
descriptor, failure DB o grant R89 consumati. Nessun working DB creato.

Nove contratti/proxy byte-exact dalla preparazione R89: containment, enter_owned,
cleanup, private_tmp, v4_contract, schema-original, activation_audit, proxy e
api-redirect-location. Wrapper cambia solo stem gaiar89→gaiar91. Runner cambia
solo futura identità native-r91 e custody esplicita spec/helper/unit/package closure.
Child originale e driver invariati: la secondary strict-drain failure non è riparata.

Sorgenti R90 correnti hash-exact rispetto alla review precedente, copiati soltanto
come evidenze test-source. Binding include import spec→readiness→@playwright/test.
Ricostruzione del digest R89 substituendo frozen spec precedente ed escludendo
soltanto helper/unit nuovi prova assenza di altri delta runtime: protected2732→2734.
Nuovo digest `389efdbb1187c01e0429b7866314c11908fbe5429ed5c54eee01dd497087a99d`.
HEAD/base, stato/diff/hash untracked main e dipendenze sono pin read-only; nessun
contenuto concorrente incorporato. Futuro drift deve fermare custody, non repinning.

Identità **statiche**, non raccolte con Playwright:
chromium/catasto-drilldown.spec.ts22:5 e58:5, titoli originali e ordine invariati.
Una eventuale futura collection deve confermarle prima dell'esecuzione; questa
preparazione non prova che la collection reale abbia successo.

## Invarianti e limiti preservati

Backend FastAPI/Next/proxy reali, rete isolata loopback, namespace PID, repo/build
read-only, lifecycle/cleanup esclusivi dopo successo e nessuna cleanup post-failure.
Fixture R83 originale hash529e7aa4 e DB origineebc902bd invariati, letti soltanto
come byte stream. Nessun dato runtime/auth/quota/schema modificato. Archived
R83 cat_import_batches0 prima/dopo è provenance statica, non futuro HTTP proof.

Piano ipotetico conserva3GiB,512tasks,2CPU, service900s/host930s, case360s/native150s,
test90000ms/expect20000ms, restartno/control-group/core0/fds2048. Parametri non
attivati; scrivere argv nel piano non autorizza né prova systemd operativo.
SKIP/error/drift fermano ammissione e casi successivi, senza retry automatici.

Limite R90 ordering preservato: il browser può avviare reload anno prima che Node
legga history, causando timeout conservativo; duplicati arbitrariamente tardivi
non sono identificati semanticamente come generazioni React. KPI header non è
body/render proof. R90 review è source preparation, non native admission.
Proxy R88 non prova parità nginx universale; coverage statement separata non
disponibile, non dichiarata100. R61 limite storico source1047/artifact200 preservato.

## Controlli

Preparer:1793 controlli iniziali,1817 finali AST/hash/Git, senza import operativo;
manifest19 membri e seal28 file verificati dal Coordinator. Numeri ispettivi,
**non test applicativi**. I programmi e receipts sono conservati integralmente.
Nessun ratchet/complexity scan o coverage nuovo; metriche runtime non cambiate.

Failure spiegate conservate: preparer read-only path R90 inesistente exit2 con
output troncato, non usato come evidenza completa e comando non ritentato;
Coordinator tool wait su handle inesistente `none` rifiutato prima di qualsiasi
script/processo. Nessuna failure applicativa o PASS fittizio derivato.

Review indipendente assegnata soltanto a `review/`, preparer fermo prima della
delega; fonti/pin/main read-only. Esito finale
**SOURCE_BINDING_ACCEPTED_NO_EXECUTION_AUTHORIZATION**,1913/1913 controlli
ispettivi e seal39 file verificato exit0, nessun test applicativo aggiuntivo.
Nessun overlap di scrittura
tra Coordinator, preparer e reviewer. Registry creato prima della delega.

## Evidenze e stop

Manifest `preparation/MANIFEST.json` SHA256
`012ede06b59583f6479c4af1faeeb1e79a596a1e34fbc54db166b4ad7dce5b01`.
Seal `preparation/SHA256SUMS` SHA256
`5b8a5989bbc4443ec06a4c24b4d15cf959bca96bef23aa3dc7fda1024571a669`.
`before-docs/` congela PROGRESS e registry prima degli aggiornamenti; precedenti
R89/R90 seals e malformed raw manifest storici preservati, nessuna riscrittura.

**NATIVE_EXECUTION_AUTHORIZED=false / NOT_ADMITTED**. HEAD conservato, nessun
commit/staging di cache/DB/dipendenze/build/graph. Prep/review non autorizzano
attivazione. Future decisioni separate: binding accettato, quiet slot e custodia
esatta, grant singola esecuzione; non proseguire automaticamente con altra slice.

Review `review/INDEPENDENT_REVIEW.md` SHA256
`f55587fb559f40d1bc65a43e3aa975efadae59a7f8af216961375e05593c3f9c`;
seal `review/REVIEW_SHA256SUMS` SHA256
`9857ab485e39a6c988501284607f300b6e1489a3cd12652455dd137ae76976e7`.
Entrambi gli agenti terminali; Coordinator si ferma alla closure documentale.

Graphify platform-docs **DEFERRED / NOT_RUN**: alla chiusura è osservato un
processo Jest shared concorrente1944509. Nessun target pesante avviato, processo
non interrotto. Vecchio refresh R90 resta storico, non certifica queste nuove docs.
Aggiornamento docs da fare nel prossimo slot quiet tramite target make dedicato.

Handoff finale esterno `HANDOFF.md`, manifest `FINAL_SHA256SUMS` senza self-entry;
documenti mutabili congelati prima degli aggiornamenti in `pre-closure-docs/`.
Verifiche finali custody/seals/diff-check e assenza future paths salvate in
`coordinator/`; nessun descriptor privato attivato o working DB creato.
Queste sono osservazioni puntuali source-only, non readiness nativa o leak audit.
