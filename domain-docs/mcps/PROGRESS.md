# Progress MCP — ciclo live 2026-10-07

## Completato

- Catalogo di 17 letture GAIA stdio separato dal connector sintetico.
- Opt-in, allowlist, HTTPS, identita/permessi freschi, projection, budget,
  provenance e audit metadata-only; nessuna scrittura/download/sync.
- Test per tutte le capability e integrazione SDK/route GAIA sintetiche.
- Matrice comportamento → test e audit finale in
  `FINAL_VALIDATION_2026-10-07.md`.
- Consolidamento del decoder JSON patologico e dei test failure/edge case.
- Verifiche frontend smoke/unit/type/lint/build isolata/E2E mockato,
  gateway TLS, release Compose e PKI.
- Ultimo rerun live: 117 test PASS, 187 statement/40 branch al 100%.
- Ultimo rerun MCP completo: 437 test PASS, 2319 statement/478 branch
  al 100%, zero righe escluse o non coperte.

## Residuo

- Lint backend globale: 19 errori legacy `mobile_sync.py`, riprodotti a HEAD;
  non corretti nel ciclo MCP.
- Ratchet globale: quattro finding nelle modifiche concorrenti worker,
  mobile sync, export Presenze e tributi; ratchet live senza finding.
- Sette warning di complessita live e annotazioni interne incomplete;
  warning frontend legacy distinti dal codice introdotto.
- HTTPS CED/client applicazioni/provider, ACL NAS e catalogo Trasparenza.
- Batch elaborazioni non esposti per side effect dei GET esistenti.
- Nessun commit, deploy o abilitazione live: stato finale FAIL, dettagli
  e risultati autorevoli nel report di verifica.
