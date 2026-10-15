# Subject Audit log — R104 characterization

The exported subject detail page is mounted with real auth/layout/domain
children. Only API/auth/navigation boundaries are mocked. Audit disclosure
starts collapsed independently of whether the API returns events.

## Public behavior covered

- Empty collapsed copy and populated event count; event bodies are absent.
- Espandi/Riduci toggles through expand, collapse and reexpand.
- Expanded empty copy and populated action/date/body rendering.
- Events retain API response order, not date or action sorting.
- Dates use the existing Italian short date/time formatter.
- Nested object, array and null payloads render literal indented JSON, not HTML.
- Reexpansion preserves event identity/content and causes no reload, mutation
  or navigation requests.

Seven new cases in
`frontend/tests/unit/campaign-utenze-audit-log-r104.test.tsx` extend the unchanged
eight-spec256test union to nine-spec263PASS. No old test, runtime, config,
threshold, exclusion, coverage policy or timeout was changed.

Original full-page coverage is564/576statements,568/610branch arms,
173/176functions and526/536lines. Maps/denominators are unchanged and previously
covered counters remain covered. Full-file100 still FAILS:12statements,
42branch arms,3functions and10lines remain. This is not runtime refactor
admission or a complexity reduction; DetailContent remains391cognitive,
304cyclomatic and1908LOC. Archive metadata is a separate responsibility.

Gate receipts and separately assigned source admission belong to the R104
report and external root
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/r104-utenze-audit-log/`.
Global campaign remains ACTIVE/INCOMPLETE.
