---
name: gaia-graphify-maintenance
description: Keep Graphify outputs updated for GAIA module-level code and domain-doc corpora when code structure, routes, services, workflows, or docs change. Use this when working on GAIA modules such as catasto, inaz, network, operazioni, organigramma, riordino, ruolo, utenze, or wiki and you need to refresh graphify-out, run the correct make target, or query the right corpus without polluting the repo root graph.
---

# GAIA Graphify Maintenance

Use this skill when working in the GAIA repository and changes affect module structure, routes, services, workflows, frontend surfaces, or domain documentation.

## Supported corpora

- `backend/app/modules/catasto`
- `backend/app/modules/inaz`
- `backend/app/modules/ruolo`
- `backend/app/modules/utenze`
- `backend/app/modules/operazioni`
- `backend/app/modules/network`
- `backend/app/modules/organigramma`
- `backend/app/modules/riordino`
- `backend/app/modules/wiki`
- `domain-docs/catasto`
- `domain-docs/inaz`
- `domain-docs/ruolo`
- `domain-docs/utenze`
- `domain-docs/operazioni`
- `domain-docs/network`
- `domain-docs/organigramma`
- `domain-docs/riordino`
- `domain-docs/wiki`
- `backend/app`
- `frontend/src`
- `domain-docs`

## Required workflow

1. Identify the narrowest affected corpus.
2. Prefer module-specific targets over broad targets.
3. Refresh the graph before final handoff when structure or behavior changed materially.
4. Query the graph only from inside the corpus you want to inspect.

## Commands

Code graphs do not require an LLM key:

- `make graphify-refresh-core-code`
- `make graphify-catasto-code`
- `make graphify-inaz-code`
- `make graphify-network-code`
- `make graphify-operazioni-code`
- `make graphify-organigramma-code`
- `make graphify-riordino-code`
- `make graphify-ruolo-code`
- `make graphify-utenze-code`
- `make graphify-wiki-code`
- `make graphify-backend`
- `make graphify-frontend`

Docs graphs require a valid Graphify-supported API key in `.env.graphify`:

- `make graphify-refresh-core-docs`
- `make graphify-refresh-core`
- `make graphify-catasto-docs`
- `make graphify-inaz-docs`
- `make graphify-network-docs`
- `make graphify-operazioni-docs`
- `make graphify-organigramma-docs`
- `make graphify-riordino-docs`
- `make graphify-ruolo-docs`
- `make graphify-utenze-docs`
- `make graphify-wiki-docs`
- `make graphify-docs`

If `.env.graphify` points the `openai` backend to `codex-lb`, apply the local compatibility patch first:

- `make graphify-patch-openai-base-url`

## Query pattern

Run queries from inside the corpus directory, for example:

```bash
cd backend/app/modules/catasto
graphify query "Quali sono i flussi principali del modulo?"
```

## Constraints

- Do not run semantic extraction from the repo root.
- Do not commit `graphify-out/`.
- If docs extraction fails for missing or invalid API key, update the code graph anyway and report the limitation.
- Use `.graphifyignore` and the existing `Makefile` targets; do not invent ad hoc graph locations.
- On a fresh machine, a stock Graphify install does not honor `OPENAI_BASE_URL` for the `openai` backend until the local patch is applied.
