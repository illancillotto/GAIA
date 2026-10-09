# Daily-record label policy consolidation

The daily workspace retains its matrix, collaborator modal and day detail DOM,
commands, permissions, React lifecycle and API interactions. This local cleanup
only consolidates the finite vocabulary used by daily-cell primary/secondary
labels, the detail status badge and the Formula GAIA badge.

## Policy boundaries

- `classifyCell` remains the canonical existing classifier, unchanged.
- Known absence causes share a primary-label map; unknown causes remain unknown,
  including inherited-object-key strings such as `constructor` and `__proto__`.
- Textual status matching preserves the ordered precedence `perm`, `fer`,
  `anom`, `malatt`, `rich`, then the existing four-character abbreviation.
- Worked/special, absence and critical cells use explicit finite kind sets.
  Specialized secondary-label helpers retain their existing priority: authorized
  punch, extra, travel, KM, then request; critical cells prefer missing minutes
  over absence minutes and requests. Unworked holidays suppress secondary labels.
- The detail badge still gives a `regolare` status precedence over classification.
  Formula GAIA has its own vocabulary: blocking/danger/Da sistemare,
  in_analysis/warning/In analisi, otherwise success/Quadrata. These badges are
  intentionally not interchangeable.

Numeric calculations, nullish versus truthy fallbacks, empty status handling,
NaN/negative/zero behavior, formatting and request parsing stay unchanged. There
is no new hook, component, API abstraction or exported domain service.

## Evidence

Original characterization: 424 focused tests pass with full-page 100% statement
and branch coverage; 44 additional rendered characterization cases pass before
runtime changes. After consolidation all 468 focused tests pass. Complete-page
coverage is 1033/1033 statements and 1143/1143 branches, with no configuration or
threshold changes.

The complete page aggregate decreases from 1172 to 1109 cognitive complexity and
1249 to 1230 cyclomatic complexity, counting every new helper/callback. Primary
and secondary policy callable cognitive complexity decreases from 53 to 11 and
40 to 8 respectively. The still-monolithic principal remains extreme at 399;
this slice does not claim to eliminate that hotspot or finish the campaign.

Exact slice results, residual risks and dedicated validation evidence live in
`reports/code-quality/SLICE_R8_PRESENZE_PRESENTATION_2026-10-09.md`.
