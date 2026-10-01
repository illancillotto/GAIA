# GAIA Data MCP — piano di test

Stato finale 2026-10-01: suite Data/HTTP/gateway/evaluation eseguite con coverage
statement/branch 100% del runtime MCP; 30 query offline e 30 query gateway live
su `gpt-reserve` verificate. Matrice dei test, risultati e residui del gate
complessivo in `../FINAL_DEVELOPMENT_REVIEW.md`. Le sezioni sotto descrivono
i requisiti coperti, non attivita di implementazione ancora da iniziare.

## Unit test

Per ogni tool:
- input valido;
- input mancante;
- tipo errato;
- UUID inesistente;
- match ambiguo;
- limite;
- paginazione;
- zero risultati;
- permission denied.

## Integration test

Contro dataset sintetico con seed noto:
1. soggetto → utenze;
2. utenza → particelle;
3. particella → utenze;
4. soggetto → avvisi;
5. avviso → pagamenti;
6. avviso → righe → particella.

## Security test

- SQL injection nei campi testuali;
- superamento hard cap;
- scope mancante;
- scope errato;
- parametri extra;
- tool write inesistente;
- ambiente sperimentale che tenta connessione al DB reale.

## Determinismo

Con stesso seed devono essere riproducibili record, ground truth e risultati deterministici.

## Performance

Registrare:
- p50;
- p95;
- p99;
- result count;
- payload size.

## Contract test

Verificare:
- tool discovery;
- schema;
- error model;
- provenance;
- request ID.

## Thesis query set

Preparare almeno 30 query iniziali:
- 8 lookup semplici;
- 8 query relazionali;
- 6 query multi-hop;
- 4 ambigue;
- 4 senza risultato.
