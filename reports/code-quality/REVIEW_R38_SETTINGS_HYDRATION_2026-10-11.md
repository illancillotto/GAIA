# R38 — Independent original-source review

## Ownership and status

Reviewer owns this NEW report and private `review-evidence` only. Runtime,
tests, shared files, baseline, thresholds, configuration and tooling are not
owned. No native gates, dependency installation, source edits or commits run.
Status: **ANALYZE ORIGINAL ONLY**. Candidate acceptance is not granted.

Worktree:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r38-settings-hydration/review-worktree`.
HEAD `114fbf7196382c6446a7963c34bd89e4c9795ef5`; merge-base/main
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Initial tracked/untracked tree clean.
Original runtime SHA-256:
`ddb7113ba1586ffca6cb31de52f14dbba511d1f42fb9faec68dfb3ca98121a63`.

Responsibility: selected/default SISTER credential projection during
`loadCredentials`, not the other provider forms, save/delete commands or JSX.
R37 is excluded from this review; its FAIL is neither waived nor incorporated.
R38 integration remains withheld according to the Coordinator registry.

## Source-backed invariants

`frontend/src/components/elaborazioni/settings-workspace.tsx:475`:

1. Read the token when each load is called. No token means immediate return;
   no API call, credential/form/error mutation or loading state is introduced.
2. Await `getElaborazioneCredentials(token)`, then set the status to that exact
   result before scheduling the functional form updater. Clear the error after
   scheduling. Do not add extra requests, batching, cancellation or deduplication.
3. Evaluate selection using the updater's `current`, not render-time or
   request-start state. The guard is `current.id != null`, not truthiness.
   Lookup is strict equality and `find` selects the first matching credential.
4. A found selected credential always wins, even with a blank current username,
   a different default, or inactive selected credentials. Username `trim()` is
   not evaluated on this path. No extra eligibility test is present.
5. Selected refresh keeps `current.id`; it overwrites exactly label, username,
   convenzione, request code, provincial office, active and default status.
   The two nullable text fields use `?? ""`, not `||`, and no normalization is
   applied to the other fields.
6. When selection is absent/missing, default is considered only if
   `result.default_credential` is truthy AND `current.sister_username.trim()`
   is empty. Null/no default avoids even evaluating `trim()`. A whitespace-only
   username permits default; a nonblank username retains the draft.
7. Default refresh also overwrites the id, regardless of whether the default
   exists in the credentials array, or `configured`/legacy `credential` fields.
   It uses the identical seven-field projection described above.
8. Both successful projections spread current and retain password, scheduling
   enabled flag, availability schedule reference, and any extra own fields.
   Either projection returns a NEW object even when all values already match.
   No selection/default projection returns the exact current reference.
9. When neither projection applies, return current by identity; do not spread
   it or manufacture a new object. No scheduled form reset occurs.
10. Error objects retain `.message`; other failures use
    `Errore caricamento credenziali`. Failure before status/form scheduling
    leaves their existing values untouched. Do not move the projection outside
    the functional updater or change React's execution/error boundary.

The retained fields are defined in
`frontend/src/components/elaborazioni/sister-credential-form.ts:11`.
Its existing `sisterCredentialFormFromCredential` is NOT a substitute: that
function clears password and replaces schedule fields, unlike refresh.
Changing that other module is outside ownership and would change behavior.

## Async and lifecycle characterization

- Initial effect launches four loads through Promise.all with an empty
  dependency array. This responsibility does not change effect dependencies,
  cleanup, mount/unmount behavior or provider sequencing.
- A user may select another credential, type a draft, change password/schedule
  or reset the form while a request is pending. The resolving load must project
  onto the then-current state, not a captured request-start value.
- Multiple loads have no generation/cancellation guard. Later completion can
  replace an earlier response, including status and errors. Preserve this
  behavior, rather than introducing a functional race fix in a refactor.
- A reload cannot indiscriminately preserve all drafts: selected profile label,
  username and the other seven loaded fields are deliberately refreshed. Only
  fields outside that projection, or the entire no-projection branch, retain
  draft data. Assertions must distinguish these cases.
- Subsequent command handlers may reset/reapply the form after awaiting the
  load (for example save/delete). Tests must isolate reload effects through a
  mounted refresh action to avoid passing because of that later replacement.

## Existing test inventory and required proof

The inventory below is static, not a claim that these tests ran. Existing tests
must remain immutable. A new characterization file is author-owned only.

| Behavior | Existing test | Missing / required assertion | Added by reviewer | Result |
| --- | --- | --- | --- | --- |
| Initial default and selection | `elaborazioni-settings-sister.test.tsx:485` | Refresh selected with different default; selected precedence when username blank | No | Not run |
| Nullable text fields | `elaborazioni-settings-sister.test.tsx:923` | Selected/default null and empty values in reload, distinguish `??` from `||` | No | Not run |
| No token | `elaborazioni-settings-sister.test.tsx:1160` | Keep guard/APIs unchanged; existing suite suffices after rerun | No | Not run |
| Error and non-Error load failure | `elaborazioni-settings-sister.test.tsx:1174` and `:1190` | Reload error retains selected form/draft; later success clears error | No | Not run |
| Nonblank transient username | `elaborazioni-settings-sister.test.tsx:1526` | Explicit reload with default present leaves transient draft untouched | No | Not run |
| Selected missing | No targeted mounted assertion identified | Nonblank username keeps form; blank/whitespace permits default; no default keeps form | No | Not run |
| Selected found | Existing pool actions exercise reload | Password/schedule retained while loaded fields update; first strict id match | No | Not run |
| Pending request and user transition | No targeted mounted assertion identified | Deferred load resolves after selection, draft edit or reset; use latest current | No | Not run |
| Overlapping requests | No targeted mounted assertion identified | Two deferred reloads resolve in reverse order; preserve completion-order semantics | No | Not run |
| Referential identity / extra fields | Not a mounted UI assertion | Independent exact-AST extracted updater differential proof, no private helper mocked into runtime coverage | No | Not run |

Recommended mounted tests use the public refresh control with API-boundary
deferred promises, real React form behavior and observable inputs. Assert saved
payload password/schedule preservation where UI alone is insufficient, without
allowing save's later form reset to hide a reload difference. Avoid mock invocation
of private handlers/updaters as a substitute for mounted coverage.

For supplementary equivalence proof, compare ORIGINAL updater and candidate
projection extracted from their exact AST. Compare both own properties and
reference relationships, not JSON alone. Cover null/empty/nonblank ids, strict
id mismatches and duplicates, selected/default combinations, null/undefined/empty
optional fields, whitespace usernames, extra own fields and schedule/password
references. Preserve short-circuit behavior by checking throwing `trim()` only
where relevant; no-input/getter adversarial cases are supplementary, not a reason
to change typed application semantics. Raw proof must identify exact source
hashes and must not be reported as native tests or coverage.

## Prospective candidate review checklist

- Genuine common projection with typed domain inputs, not relocation of the
  unchanged 31-LOC callback or a broad generic context.
- All selection/default decisions remain inside the functional updater.
- Null-id and strict equality semantics, selected-first/default-only-on-empty
  rule and unchanged identity match the invariants above.
- No password/schedule reset, extra-field loss, request or error ordering change.
- No JSX, command, state/effect, test removal, baseline/config/tooling change.
- Complete native before/after metrics show aggregate cognitive/cyclomatic
  improvement, not only a smaller parent with transferred decisions.
- Runtime full-file statement/branch/function/line coverage 100%, types/lint and
  actual full-context main55a ratchet zero findings are required independently.
- Graphify refresh and source/main/evidence custody remain Coordinator gates.

## Baseline, metrics and classification

The registry cites prior native workspace296cognitive/265cyclomatic/1358LOC,
loadCredentials20cognitive/12cyclomatic/42LOC and updater16cognitive/9cyclomatic/
31LOC. These are not freshly measured by this reviewer and cannot certify the
candidate. Original metrics and coverage must be acquired by the token holder.

Candidate not yet provided. No metric delta, coverage PASS, ratchet PASS,
IMPROVED classification or merge recommendation is issued. The original
responsibility is sufficiently explicit for characterization and a bounded
deduplication proposal; exact-candidate review is still required.

## Tests and residual risks

Native commands executed: **none**. No gate token held.
Static evidence: git preflight, source SHA, targeted source and existing-test
inspection. No runtime/tests/config edits. Only this report is new.

Residual risks: request-start state capture, reuse of the reset mapper,
truthy-id guard, nullable-field normalization drift, no-op identity changes,
default-before-selected precedence, loaded-versus-retained draft confusion,
and untested async completion order. Prior full-file coverage cannot be assumed
to prove these semantics or candidate full-file coverage.

Next action: wait for Coordinator grant of exact candidate bytes and native
evidence; review read-only and issue a separately evidenced disposition.

## Exterior patch prospective review — separate read-only disposition

Coordinator granted this review after fresh provenance admission. The exterior
patch was read, NOT applied to this worktree. No heavy token or native command
was acquired. This section appends to the original report; the original first
10438 bytes have SHA-256
`359ad4d437127861b9f6e05024636bc7e34d3763c5d0a858ea267763ddaf7914`.

Exterior proposal:
`../author-evidence/candidate-proposal.patch`, SHA-256
`c4e48a8aff83e591e5067cac692e73a5a9b01311477a76f8a3d3630777835e7b`.
Original source remains the `ddb7113b` hash recorded above. A proposal patch is
not an exact installed candidate/native-evidence binding.

### Static disposition

**ACCEPTABLE PROPOSAL FOR CHARACTERIZATION**, not accepted runtime, native
certification, IMPROVED classification or integration permission.

- `loadedSisterCredentialFields` takes the existing domain credential type and
  returns a `Pick<SisterCredentialFormState, ...>` covering exactly the seven
  loaded properties. The object literally contains those seven properties and
  no id/password/schedule fields. Optional texts retain `?? ""` behavior.
  This is genuine deduplication of repeated field projection, not a generic
  manager/context or relocation of the original callback intact.
- `refreshSisterCredentialForm` takes existing typed form/status arguments. Its
  `current.id == null` ternary is exactly the inverse of original `!= null`:
  null/undefined skip lookup; empty string still looks up. It retains strict
  equality/find-first, and selected precedence regardless of default/username.
- Selected spread order preserves current id and nonprojected fields. Default
  spread order replaces only id plus the seven projected fields. Unknown own
  enumerable fields and schedule reference survive; password is never read or
  reset. Own-property order is preserved for the declared fields by the object
  spreads; neither mapping changes the order of credential property reads.
- `!status.default_credential || current.sister_username.trim()` returns current
  on the complement of the original fallback condition, retaining short-circuit
  evaluation. A present default plus blank/whitespace username is projected;
  nonblank username or missing default returns exact current by identity.
  Selected/default projection always returns a new object, even if equal values.
- The helper call occurs in `setFormState((current) => ...)`, retaining current
  updater-time state and response binding. Token/request/status/error ordering,
  effects, cleanup, command calls and request completion-order races are unchanged
  in the proposed diff. No render-time captured form snapshot is introduced.
- Two helper callables are added. Fewer duplicate mapping branches and flatter
  selection are structurally justified, but full-context metrics must prove
  aggregate reduction and no new/legacy file or callback violations. Static
  expectation alone is not a passing ratchet or a measured improvement.

### Malformed DTO boundary and limits

The API uses `request<ElaborazioneCredentialStatus>`; the shared request parser
returns JSON-parsed objects. Types alias `CatastoCredentialStatus` with required
array credentials, nullable default and string username/id fields. No dynamic
accessor/proxy DTO contract or mutation during projection exists in this code.

For plain data objects outside that typing, the candidate preserves these
conditional boundary behaviors: null status fails when first accessed; null or
missing credentials fail only when a non-null id causes lookup; null array
entries fail during strict-id lookup; missing/null/nonstring username `.trim()`
fails only after no selected credential and a truthy default. Missing/null
default short-circuits before username access. Missing/null optional texts
normalize to empty exactly as before. No additional validation/fallback is added.
These are static conclusions, not executed malformed DTO tests.

One deliberately limited claim: dynamic `default_credential` getters or proxies
could return different objects on repeated reads. Original code reads that
property separately for each field; the candidate reads it for guard/id and once
to pass the object to the projection. Such exotic objects are not generated by
the JSON API boundary, so no broader all-JavaScript-object equivalence is claimed.
Do not fix or expand that boundary as part of this responsibility; make the
supplementary differential input contract explicit instead.

### Still required

Mounted original characterization must precede editing, including default
fallback after missing selection, retained password/schedule, deferred user
transitions and overlap completion order. Exact installed source/patch hashes,
fresh before/after full-file four-dimension100 coverage, complete native metrics,
type/lint results and main55a ratchet zero findings remain pending. Existing tests
and config remain immutable. Re-review exact bytes and inspect evidence rather
than granting acceptance from this proposal's intent.

## Mounted characterization spec — distinct read-only review

Plain Coordinator grant permits reading the author's NEW spec only. No token,
test execution, runtime/test edit or proposal installation occurred here. The
preceding report first15501bytes have SHA-256
`7146c84ebb3429eb7026bc088944b72e3ac16f0267ec66c7e5e457e1d26b2f70`;
this section appends without changing those bytes.

Bindings inspected:

- NEW spec `../author-worktree/frontend/tests/unit/campaign-settings-hydration-r38.test.tsx`:
  `13d7bda46b449c286ab6f647fa6f46cf6ba158ac1bd51fcd6f8f32187f9da4d8`.
- Author ORIGINAL runtime:
  `ddb7113ba1586ffca6cb31de52f14dbba511d1f42fb9faec68dfb3ca98121a63`.
- Exterior proposal:
  `c4e48a8aff83e591e5067cac692e73a5a9b01311477a76f8a3d3630777835e7b`.

Disposition: **GENUINE MOUNTED CHARACTERIZATION; IDENTIFIED PROOF GAPS**.
Static review does not issue a test PASS or acceptance of future candidate bytes.
The spec has eight test declarations, nine cases including the two blank values.
It renders real `ElaborazioniSettingsWorkspace` and exercises actual form UI,
schedule editor and React state transitions. Mocks are confined to API calls,
access token and protected-page wrapper; the API partial mock preserves other
exports. No hook/helper/handler is mocked or privately invoked. No skip, coverage
override or disabled assertion is present in this spec. It cannot weaken existing
tests because it is a separate new file; immutability remains a custody gate.

### Assertions covered statically

| Behavior | Explicit mounted assertions | Remaining limitation |
| --- | --- | --- |
| Initial default | All seven loaded fields, nullable texts empty, active/default flags, empty password, schedule flag not adopted | Uses null schedule data; does not exercise richer loaded schedule replacement |
| Selected-first even blank username | All seven loaded fields, selected username remains empty despite present default | Id is not asserted through a later API payload |
| Retained password/schedule | Selected refresh retains password, custom schedule flag and Monday17:45 | Schedule reference identity is not observable in UI |
| Missing selected / nonblank draft | Label, username and password retained while selected card disappears | Other retained fields/identity not directly asserted |
| Missing selected / blank fallback | Empty and whitespace username adopt default label/username; password retained | Update button cannot distinguish primary id from stale secondary id |
| Missing selected / no default | Whitespace username and selected label retained | Other retained fields/identity not directly asserted |
| Initial request pending draft | User types username/label/password before response; all retained and create button enabled | Covers nonempty draft, not reset to blank during pending reload |
| Reload pending selection | Selection changes from primary to secondary after request starts; response updates secondary form | Latest selected field assertions focused on label/username |
| Reverse completion | Release response resolves before initial response; later initial response overwrites label/username and retains intervening password | No claim of race prevention; preserves legacy completion order |

`startRefresh` uses the public `Pausa e libera sessioni` workflow, including the
release API then real `loadCredentials`. That command does not reset/reapply the
form after awaiting loads, so the assertions are not masked by a save/delete
replacement. Deferred API promises bind user transitions to completion order.
Exact counts assume the two-load scenario per fresh reset; native execution must
still prove no scheduling/flakiness issue.

### Missing or supplementary proof

1. **Default id fallback:** both previous selected id and new default id enable
   `Aggiorna credenziale`. This assertion does not detect a mutant preserving
   stale selected id on fallback. Assert the subsequent update API receives the
   default id, or add supplementary exact-source property equality proof.
2. **Reload failure/recovery:** old tests cover initial Error/non-Error failure,
   but this new spec does not verify reload failure retaining selected draft and
   later successful reload clearing error. Add a mounted sequence if the proposed
   exact change touches those boundaries, or document unchanged AST plus rerun
   existing error tests as the error-orchestration evidence.
3. **Identity/unknown properties:** unchanged current identity, new-object
   selected/default identity, retained availability reference and extra own fields
   require supplementary original-versus-exact-candidate proof. JSON/UI alone
   cannot establish these properties. Do not mock private hooks to produce fake
   native coverage; supplemental extracted-AST proof is a separate evidence class.
4. **Selection boundary:** first duplicate match, empty-string id versus null,
   strict-id mismatch and conditional malformed DTO failures need supplementary
   exact-source proof if not naturally mounted. This spec does not assert them.

Author characterization session53987 is Coordinator-managed and was not polled,
restarted or executed by reviewer. No result is assumed from its handle. Root
R37 deactivation/custody/ratchet is a Coordinator fact, not a gate rerun here.
R38 source remains original; exact candidate/native metrics still pending.

## Exact V2 review and supplementary projection proof

Grant: `../COORDINATOR_V2_REVIEW.md`. No heavy token/native tests or runtime edits
by reviewer. Prior first20863bytes retain SHA-256
`54e1687e6331ef89367a4dcd51a05f4ef48ceeed9d31da69a75830681cf2cd02`.

### V2 mounted spec

Exact V2 SHA-256:
`eb1f1b6e28aa3207e1504ff6fb91350f30a6da289f558c6bd33b190e2c812d52`.
Original runtime `ddb7113b` and exterior proposal `c4e48a8a` remain exact full
hashes recorded above. All original mounted assertions remain. Two blank-fallback
cases now save through the actual public button and assert update API id `primary`
plus loaded label/username and retained password. This closes the id loophole:
retaining stale secondary id would now fail the assertion. The subsequent save
reset does not mask the earlier field assertions or the update call itself.

Two additional mounted failure/recovery cases cover Error and raw failure, retain
unsaved label/whitespace username/password and schedule17:45/18:15 transitions,
and retain the selected pool. Recovery updates via selected or default projection,
retains password/custom schedule/hour and removes the displayed load error. No
private hook mocks, skips/config override or old-test edits are introduced.

Observed author artifacts (read-only, not reviewer execution): launch/tests/types/
lint/audit exit files all0. Native JSON80PASS/0FAIL/0pending/0todo across3specs;
11new +64SISTER +5tab tests. Audit source/test hashes match originals/V2. Raw
coverage contains exactly the full settings runtime,455statement/556branch/
118function counters, all positive; author line audit402/100%. This is ORIGINAL
characterization evidence, not candidate acceptance.

Artifact bindings:

- `characterization-v2-tests.json`:
  `08799405273bd664a4f6cd69fd511b24779a9ba447b22c960731a8528a80c594`.
- `characterization-v2-audit.json`:
  `9dc6c6842c14557d01fbffab13213a4755daee1febc5c34eb74e9bea76ccea89`.
- `characterization-v2-coverage/coverage-final.json`:
  `316ee637631a1790d202baf5bb9302ab45410251c9c3c6705fc998689abc5631`.

### Supplementary executable proof — not native coverage

Reviewer-owned `../review-evidence/supplementary-projection.cjs`, SHA-256
`e8464572626e92584ef1b12c83a49fb86fee1fd4f7cb671ab3f47224adcbbd1c`.
Command `node ../review-evidence/supplementary-projection.cjs` ran once, exit0;
no native test/report/ratchet or dependency installation was invoked.
Output `supplementary-projection.json`, SHA-256
`6f88c599faf62250e994e7d80b61cb6e7f252295e5c1c1e7d80877d7e77ef4ab`.

The diagnostic requires exact original/patch hashes, reconstructs the proposal
in memory using all3unique context hunks, parses both with Babel TS/JSX, selects
the exact original loadCredentials functional updater and both proposed helper
ASTs, erases TS annotations only, and runs those expressions in one VM context.
No handwritten replica of the business logic is compared, no installed source
is changed and no private handler contributes to coverage. The in-memory full
candidate byte hash is
`ea946b881c5dd5b1cc613de91340d2645901bd8c7d93399532729b45e30a5a7d`.
Any installed source must later bind to this exact proposal or be reviewed anew.

4224combinations PASS:2040returning,2184throwing,1050exact-current no-op,
990new-object projections. Matrix includes null/undefined/empty/nonblank/numeric/
boolean/string-numeric ids; blank/whitespace/nonblank/null/undefined/nonstring
usernames; null/undefined/empty/string/numeric/boolean optional text fields;
missing/selected/duplicate/empty-id/strict-numeric credentials; missing/null
array, null entry, primitive default and null status plain DTO cases.

Each returning case compares all values with deep strict equality, own-key order,
return-current identity, retained extra-property reference, schedule reference,
password and schedule flag. Each throwing case compares both exception name AND
message exactly. No message differences, ignored mismatches or waived cases.
The diagnostic rejects6distinct mutants: truthy id, find-last, omitted default id,
cloned no-op, truthy optional normalization and reset password. This confirms the
matrix can distinguish the key accidental behavioral changes, not merely run
equivalent happy paths. Native React async/lifecycle proof remains the mounted
spec; this pure projection proof does not cover API scheduling by itself.

Limitations explicit in output: dynamic getters/proxies are not JSON DTOs and
are outside this supplementary contract; no native coverage/complexity or React
certification is inferred. In particular, credentials replaced with a nonarray
object and other unenumerated malformed shapes are not exhaustively proven by
this finite matrix. The earlier static boundary analysis is not broadened into
universal JavaScript-object equivalence.

### Disposition

**STATIC ADMIT FOR EXACT-CANDIDATE NATIVE TESTING ONLY**. The identified fallback
id, mounted reload failure/recovery, reference preservation, strict id and first
match gaps have direct, separately classified evidence. Runtime proposal remains
uninstalled in reviewer/author trees at inspection time. No IMPROVED/native
acceptance or integration claim is issued. Candidate needs actual before/after
full-file four-dimension100, types/lint, complete aggregate metrics and main55a
ratchet0 with source/custody bindings, then exact-candidate final review.
