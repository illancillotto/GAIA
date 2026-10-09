# Fuel operator kilometre attribution — R14

## Responsibility

The slice simplifies only the nested `fuel_analytics._op_km` in
`backend/app/modules/operazioni/routes/analytics.py`. No helper relocation,
identity reconciliation, endpoint change or new matching rule is introduced.
Fuel queries, date filters, authorization, session consolidation, rankings,
weighted consumption targets, response mapping and anomaly analytics stay intact.

## Attribution contract

- Real UUID keys look up the WC operator. Missing operators return the original
  default; UUID text remains an ordinary legacy string, not a WC identifier.
- A truthy linked GAIA ID is converted to integer. Its strictly positive total
  distance wins; zero, negative or NaN linked totals fall back to textual variants.
- Variants preserve first-last, last-first, then username order. Full display
  strings are stripped only at their outer boundary; case, internal whitespace
  and username whitespace are not normalized.
- The first existing truthy textual variant wins even if its distance is zero,
  negative or NaN. A later positive variant must not override that first match.
- Ordinary strings except the no-operator sentinel retain exact map lookup,
  including the empty string. Unsupported keys use the original default.
- Returned vehicle maps are fresh shallow copies. Named direct indexing and
  linked/legacy `.get` defaults preserve insertion and exception semantics.
  Conversion, comparison and invalid-map exceptions remain unmodified.

The missing-operator guard executes before linked/textual attribution, removing
nested branching. Actual SQLAlchemy WC operators have stable default truthiness;
the change does not define semantics for arbitrary stateful truthiness doubles.
This existing Operazioni contract is not the canonical Presenze identity mapping.

## Characterization and measurement

The persistent R14 spec adds16 real SQLite ORM whole-route cases and40 bounded
actual-source nested-AST defensive cases. Whole-route cases assert the complete
response, five exact SELECT statements/binds/order, unchanged persisted objects
and no writes. Synthetic AST contracts cover invalid maps/keys/properties and
compile under a non-runtime filename, so they cannot inflate runtime coverage.
The full seven-suite union has204 cases. SQLite does not certify PostgreSQL or
external providers; those limits remain explicit in verification reports.

Target cognitive54→33, cyclomatic24→22, nesting4→2, effectiveLOC20 unchanged.
Outer fuel cognitive282→261, cyclomatic169→167, effectiveLOC350 unchanged;
whole file1255LOC unchanged. Genuine distinct weighted decisions23→21; enclosing
and nested scanner sums count this slice twice and must not be called four
independent decision removals. Twenty-nine non-target functions remain exact.

Source/characterization/review/final status and reproducible commands belong in
the R14 reports under `reports/code-quality/`. Dedicated Operazioni Graphify
maintenance is orientation, not proof of complexity or functional equivalence.
This bounded change does not complete the global complexity campaign.
