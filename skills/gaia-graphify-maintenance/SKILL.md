---
name: gaia-graphify-maintenance
description: Keep Graphify outputs updated for GAIA module-level code and domain-doc corpora when code structure, routes, services, workflows, or docs change. Use this when working on GAIA modules such as catasto, presenze, network, operazioni, organigramma, riordino, ruolo, utenze, wiki, or cross-cutting elaborazioni workflows and you need to refresh graphify-out, run the correct make target, or query the right corpus without polluting the repo root graph.
---

# GAIA Graphify Maintenance

Le regole operative per Graphify (target `make` per corpus, query, gestione API key, `--force` su rimozioni strutturali, alias legacy `graphify-inaz-*`) sono definite in `AGENTS.md`, sezione "Graphify maintenance". Quel file e' la fonte autorevole: leggilo e applicalo prima di eseguire o modificare qualunque target Graphify.

Non duplicare qui le regole: se una regola Graphify cambia, aggiorna solo `AGENTS.md`.
