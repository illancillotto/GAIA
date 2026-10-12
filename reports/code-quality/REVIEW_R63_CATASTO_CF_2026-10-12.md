# R63 independent Catasto CF review — FINAL STOP

Disposition: **STOP — NEW SPEC NOT_ADMITTED**. The sole native launch reached
**278 passing unit cases**, then required TypeScript gate **exit2**. Lint and
coverage are **NOT_RUN**. A separate reviewer metadata audit failed **exit1**;
its first traceback is retained without correction or retry. Campaign remains
ACTIVE/INCOMPLETE and R43 remains unrelated NOT_ADMITTED.

## Actual first native failure

Coordinator explicitly notified native session61219 terminal2. Preserved root
native-launch.argv/log/exit records `unit:0`, `types:2`. The author launcher
retains executable/argv/cwd/selected environment, complete logs, timing, signal
and exit for both gates. STOP.json records gate types, exit2 and
BLOCKED_NATIVE_FAILURE; no later gate receipt or COMPLETE marker exists.

The sole actual diagnostic is:

```text
tests/unit/campaign-catasto-cf-workflow-r63.test.tsx(106,17): error TS2345: Argument of type 'Element' is not assignable to parameter of type 'HTMLElement'.
```

The NEW test's row helper calls `.closest("div.rounded-2xl")`, checks only for
null and passes the resulting Element to `within(container)`. The null guard
does not establish HTMLElement. This is a NEW spec DOM typing failure, not a
runtime diagnostic or a malformed CF API DTO diagnosis. No fix, cast, assertion
change, threshold/config change or native retry was authorized or performed.

## Native unit evidence and its limits

Direct raw JUnit inspection observed seven suites, all with zero failures,
errors or skips:

| Native unit spec | Passed |
|---|---:|
| R30 AdE | 34 |
| Existing manual page | 27 |
| R17 CF | 34 |
| NEW R63 CF workflow | 9 |
| R18 Comune | 46 |
| R29 Particella | 39 |
| catasto-anomalie utility | 89 |

Total278 includes nine new passing mounted interaction cases. This does not
admit the spec after the failed required types gate. Complete unit stderr is
preserved; the automated historical JUnit/outcome/warning checks are
**NOT_REACHED** because the reviewer metadata auditor stopped earlier. This
report does not substitute guessed warning counts or a claimed historical
multiset certificate for that incomplete audit.

## Static review and custody

The immutable static review bound NEWspec SHA-256
0271376447dcf2260fbf62864067c237cd04b52821a84bff7914323f95cb0b33 and
launcher SHA-256
610d9a494cc4125957a0fd992384bd78c5c215356ce13999457e07de979569e6.
These bytes remain unchanged at native STOP. All1047 admitted frontend inputs
were checked in both author and reviewer trees; author custody-before and
custody-stop-types each record count1047 and zero mismatches. The failed final
auditor rechecked these inputs and the bound spec/launcher before its assertion
failure. The unchanged page SHA-256 is
855e3ef09296d8024f894118ef6e9c0d6bf13dc63b4f653c6ce6202407a732f7.

Static DTO/property/unsafe-syntax inspection and configuration parsing passed.
Nine tests exercise actual mounted public-page interactions, retain complete
API response/item types and six original specs/assertions. Parsed config kept
663 original source/Next root files, adding only NEWspec. Strict/noEmit and
configured vitest/globals resolution were retained, with explicit dependency
type roots and incrementalfalse. That readiness was **configuration parsing,
not native type checking**. I missed the semantic DOM narrowing constraint in
the row helper during static review; the actual required checker exposed it.

The first new test targets the genuine district-null fallback (R30 branch208,
line1519), distinguishing null from zero. An initial source-orientation label
mistake attributed it to adjacent error_code; the initial notes, raw mapping
and explicit correction are all retained. No inaccessible draft-map,
truthy-suggestion or disabled-pagination callback was synthesized for coverage.

## Separate reviewer metadata failure

The final metadata auditor audit_stop.py ran **once**. stop-audit.argv/log/exit1
preserves its AssertionError at line85:

```text
assert type_config == parsed['overlay']
```

Read-only diagnosis after STOP found that TypeScript's config parser mutated
the overlay object saved in types-metadata.json, adding inherited relative
include/exclude and compileOnSave=false. Launcher-generated JSON contains only
extends/compilerOptions/files. This bookkeeping mismatch is separate from the
native TS2345 diagnostic. The failed comparison and script remain untouched;
no adjusted matching, successful replacement auditor or blind retry is claimed.

Before this metadata failure, the auditor had checked static freeze integrity,
actual terminal/gate receipts, STOP, absence of lint/coverage, source custody,
bound new bytes and exact native type diagnostic. It did **not** reach automated
JUnit/history/warning validation. METADATA_FIRST_FAILURE.md records the precise
boundary. The final disposition remains STOP even though read-only diagnosis
explains the metadata mismatch.

## Immutable evidence and admission

Original static-freeze SHA-256 remains
f531f98b19d77dabdef6794e3be47abda16075959327be95fea455baf6b2bd28,
with1063 members checked by the failed auditor before its assertion. It has not
been rewritten. Native first-failure receipts, NEW failed spec bytes, generated
config, metadata traceback and diagnostics are separately archived under
reviewer-evidence/first-failure-objects with first-failure-snapshots.json mapping
original paths to exact private copies. First-failure-freeze SHA-256:
d78eed33e8fe35a6a4dfd857bf9f297b59cdcdfec828fe30b336eb66ec6d7569.
The snapshots mapping preserves originals named by that forensic manifest.

The new final-freeze binds this report and private evidence copies, avoiding
direct live integration source/document paths. Old freezes and failures are
preserved. Files are read-only with detached SHA-256 manifest digests; this is
not an OS immutable-attribute assertion.

Lint/coverage NOT_RUN means **no current R63 coverage measurement or covered
delta**. Historical R30 gaps remain historical, not a new runtime100 proof.
The unchanged four100 whole-page coverage gate was never reached. No runtime
refactor, architecture boundary, complexity improvement, full frontend suite,
live authorization/modal/external service, E2E or campaign completion follows.
Do not import/admit NEWspec or repair/relaunch this attempt without a separate
explicit decision. Reviewer performed no native tests/checker/lint/build/scans/
Graphify, commits or source edits.
