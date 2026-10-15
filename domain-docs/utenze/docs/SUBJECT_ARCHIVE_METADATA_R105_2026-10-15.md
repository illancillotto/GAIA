# Subject archive metadata — R105 characterization

The real exported detail page starts Metadati archivio collapsed. With a NAS
path the summary reports a linked path; null and empty paths report none.
The field table is absent until the scoped Espandi control is clicked.

## Public behavior covered

- Expansion exposes exactly nine term/definition pairs, asserting each value
  in its own actual label group: subject type, archive letter, NAS path, import
  date, source, external source ID, updated date, created date and review flag.
- Present values retain their association, Italian short date/time formatting
  and both requires_review outputs Si/No.
- Null and empty letter/path/external-ID values use em dash; null imported_at
  uses the actual presentation formatter's em-dash fallback.
- Collapse/reexpand preserves metadata, subject serialization and references.
- Metadata and Audit log disclosure state are independent.
- Toggles cause no extra reads, mutation, download or navigation requests.

Eight new public mounted cases in
`frontend/tests/unit/campaign-utenze-archive-metadata-r105.test.tsx` extend the
unchanged nine-spec263union to ten-spec271PASS, with real wrappers/domain
children and only API/auth/navigation boundary mocks. No private state,
disabled handlers, invalid API types or formatter mocks are used.

Original full-page coverage is566/576statements,578/610branch arms,
175/176functions and527/536lines, with identical maps/denominators and no lost
coverage. Full-file100 remains FAIL:10statements32branch arms1function9lines.
This is test-only characterization, not runtime admission or complexity
improvement; DetailContent remains391cognitive/304cyclomatic/1908LOC.

Final review/gates/graphs/custody are indexed in the R105report and external
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/r105-utenze-archive-metadata/coordinator-evidence/HANDOFF.md`.
Global campaign remains ACTIVE/INCOMPLETE.
