# R39 — independent positional matcher design review

## Ownership and scope

Read-only design/non-regression reviewer. Dedicated branch
`review/complexity-r39-positional-matcher`, HEAD
`114fbf7196382c6446a7963c34bd89e4c9795ef5`; main/merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Initial working tree clean.
Only this new report and private SSD `review-evidence` are writable.
No application, matcher, scanner, test, baseline or configuration was edited;
no native gate, scanner, coverage command, commit or candidate installation ran.
This is a design verdict, not a tooling/application acceptance certificate.

## Independent source evidence

Baseline JSON source commit is `11ed944a46ebdeb32ad50c14e7fca90b2c55f1fd`,
not the merge-base. Git `--no-replace-objects show` independently confirms:

| Source | Start/end | Source identity |
| --- | --- | --- |
| Historical selected-fraction handler |3165/3166 | `onChange={() =>` followed by selectedFrazioneId mutation |
| Admitted original selected-fraction handler |3157/3158 | same header, extracted transitionFractionResolution body |
| Frozen R37 handler |3182/3183 | byte-identical to admitted original handler |
| Wrong positional owner |3193/3193 | `onClick={() => setResolveModal(null)}` close button |

Independent zero-context Git diff, fully validated against both byte snapshots
using the existing mapping function, maps candidate header3182 to historical3165.
Candidate end3183 is unmapped because the historical body changed. Exterior
lines3174/3185 map3157/3168. The historical handler, not the close button,
occupies this unchanged source slot. Pure source diagnostics do not independently
re-scan the complete report: that whole-path AST binding is a required native gate.
Source-review script/result live under the R39 SSD `review-evidence` directory.

Frozen candidate SHA256:
`3ae8b186f2541dbc43902869c34213c0f0c35e6af748bf7a3d9abb5b59d94e75`.
R37 diagnosis SHA256:
`479f9708d7135ea318e41a9b0a948dcb63f4d58516639373912a55356e1ca7b7`.
R37 binding-diagnosis SHA256:
`9e579ef777911ad46f907989ba426bbce90fe9d28b539f99d6cd1c582d02b1d4`.

## Historical tooling ownership

Root census records two dirty historical copies, R16 reviewer and final verifier.
Both are byte-exact accepted matcher
`871ebffc4742c7bdf0a8847dfac7d91132d862953179599c2ce27531f0b99f43`.
Accepted R16 integration explicitly records all agents terminal/heavy RELEASED;
final terminal-verification independently records `heavy: RELEASED` and custody
exact. Current collaboration census has no R16 agent present.

Independent present-state rehash:
- Author coherent artifact manifest:10/10 members exact, no missing/drift.
- Final evidence manifest:63/63 members exact, no missing/drift.
- Reviewer terminal tracked manifest:3570/3570 exact, no missing/drift.
- Final terminal tracked manifest:3570/3570 exact, no missing/drift.

Tracked symlinks are hashed as link text, not their referent bytes. An initial
dereferencing diagnostic showed three fixture mismatches; git mode120000 and
readlink established the representation error. Correct link-aware rehash above
has zero drift. No old evidence/copy was rewritten. Historical dirty copies
are retained accepted snapshots, not evidence of a live overlapping editor.

## Design verdict

`CONDITIONAL_ACCEPT_NARROW_DESIGN_ONLY` for Coordinator's
`COORDINATOR_DESIGN_REVIEW.md`. Blanket replacement of all positional fallback
is rejected for this slice: it is broader migration and would invalidate
unmapped admitted callbacks. No runtime grant is made by this reviewer.

The narrow change may correct only a positively source-contradicted positional
selection in a duplicate-name, mismatched-fingerprint cohort. Preserve direct
resolver, exact/fingerprint matching, reservations, multiset checks, added-code
classification and strict R16 two-boundary proof. A validated mapped header
must contradict the raw owner before the new correction route is entered.

Required owner proof:
1. Immutable Git source at baseline.source_commit and a single current byte
   snapshot must reproduce each whole-path callable multiset, including kind,
   spans, fingerprint and every primary metric; caller diff is not trusted.
2. Header/start must be unchanged and mapped. Header cannot share the same
   line with the whole callable body. Unique unchanged exterior fences must
   surround it in both snapshots, preserve their order and remain exterior.
3. Exactly one compatible historical owner starts at that mapped header and
   is wholly enclosed; exactly one compatible current consumer is enclosed.
   Nested/overlapping same-name/same-kind spans cannot be silently discarded.
4. The owner cannot be reserved by a sibling fingerprint, claimed by another
   resolver result, consumed by an equivalent group or reused in the local
   provenance ledger. Report order cannot turn duplicate claims into PASS.
5. Positively contradicted but unprovable ownership returns configuration
   exit2. Never retain that positively disproved nearest owner as fallback.
6. Corrected identity always runs the unchanged full metric comparison, even
   below thresholds. No metric tuple is used to pick a preferable baseline.

Residual limitation is explicit: absent/unmapped evidence retains the old
unsupported positional fallback; this slice does NOT prove all such identities
safe. Reject stale/forged proof for correction. Missing/damaged R37 evidence
must not convert its original FAIL into PASS. A general fail-closed migration
requires separate scope, not an undocumented compatibility exemption.

The author's global diagnostic reports25 mismatched-fingerprint positional
records across7 paths,13consistent/9unmapped/3contradicted. This is authored
diagnostic evidence, not independent native certification. The additional
GAIA-users/Organigramma contradictions require exact before/after owner and
finding accounting. Do not dismiss newly exposed historical metric failures
as campaign regressions or absorb them into baseline.

## Adversarial test matrix

All following are requirements, not claimed test results.

| Case | Required result |
| --- | --- |
| Real frozen R37 full-global report/bytes | rightful3165 owner; original false LOC finding eliminated |
| Multi-line changed final body, mapped header/fences | proven slot allowed; endline equality not required |
| Same-header neighboring close button becomes nearer | no ownership by raw distance or metric tuple |
| Real below-threshold metric increase on rightful body | native exit1 with rightful baseline, never looser neighbor |
| Each primary metric independently increased | genuine regression detected; provenance not a waiver |
| Missing current source / forged exterior source | no new correction; R37 cannot become PASS |
| Stale current or baseline span/fingerprint/metric/kind | whole-path binding rejected, no corrected ownership |
| Stale unrelated callable on same path | whole-path binding rejected, not just target validation |
| Missing/malformed/nonexistent source commit | no proof; no HEAD or merge-base source substitution |
| Replacement refs / textconv / external diff hooks | immutable/raw byte source remains authoritative |
| Forged hunk payload / hidden source edit | complete diff validation refuses mapping |
| Edited/missing/duplicated/crossed exterior fences | contradicted ownership stays exit2 |
| Duplicate enclosed same-name/kind owners or consumers | exit2, never filter by preferred metrics |
| Nested same-name/kind callback inside enclosure | no skipped competitor or ambiguous claim |
| Moved or reordered callback with header ambiguity | no inheritance based on nearest slot |
| Entirely added callback | normal new-code error checks; no old slot borrowing |
| Owner reserved by unique fingerprint sibling | contradiction cannot steal owner |
| Duplicate multiset already consumes owner | no reuse for corrected callable |
| Two corrections claim same owner, either report order | not PASS; local ledger enforces uniqueness |
| Same metrics, alternating source contexts within compare | one snapshot read, no mixed fence proof |
| Refused snapshot then repaired bytes within compare | refusal sticky; fresh compare may re-read |
| One-line header/body | no new proof; existing unsupported limitation explicit |
| Direct resolver and all old contracts | unchanged tests pass without edits/skip/config waiver |
| Full-global GAIA-users/Organigramma corrections | exact identity/finding changes explained, no baseline repair |

## Pending admission evidence

Before tooling acceptance: Coordinator grant, original repro, complete old/new
tooling suite, statement/branch full-file100 with subprocess coverage, Ruff and
new-test format, actual main55a ratchet, full-global exterior replay, real source
metric-negative, untouched baseline/config/application custody and independent
final verification. Coverage denominators and all skip/missing/partial/excluded
counters must be inspected. No sparse replay, manual finding removal or altered
BASE_REF is acceptable. Docs/Graphify maintenance remains Coordinator-owned.
Correcting tooling is not application complexity reduction, and matcher PASS
does not certify R37 runtime behavior/coverage or complete the global campaign.

## Status

Design review delivered; implementation/native acceptance PENDING.
No native heavy token held. No commit. Campaign ACTIVE/INCOMPLETE.
