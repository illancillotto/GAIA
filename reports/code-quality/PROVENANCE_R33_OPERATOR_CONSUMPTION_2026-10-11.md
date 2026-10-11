# R33 — Historical analytics ownership provenance

## Verdict and ownership

**ADMIT_HISTORICAL_TERMINAL.** All eight dirty analytics snapshots are preserved
previous campaign inputs, not active conflicting source owners. No application,
baseline, threshold, exclusion, test or historical evidence was modified. Only
this NEW report and NEW private provenance evidence were written. This admission
does not certify R33 behavior, coverage, complexity or integration.

Registry read before work: MULTI_AGENT_OWNERSHIP_R33_OPERATOR_CONSUMPTION_2026-10-11.
Dedicated provenance HEAD1613f2b56f0c8ef2dcf253dd1ee9bcee8299b380; main/merge-base
55a1b1d35911451e018b662c2acc450bf5994ea2. Initial dedicated status clean.
Coordinator's original census contains143 worktrees/eight dirty owned sources;
census SHA2567360c0e79dff398a76ab014f2139fd76dc8cbacda8c53c7088558e40f5152a36.
Each source was independently read/hashed and matches that census exactly.
The owned historical source is backend/app/modules/operazioni/routes/analytics.py.

## Eight preserved snapshots

`HOME` below means `/home/cbo/CursorProjects`; `SSD` means
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r31-session-distance`.

| Worktree | Exact analytics SHA256 | Provenance | Terminal evidence | Status |
| --- | --- | --- | --- | --- |
| HOME/GAIA-campaign-20261008-analytics | 41c4fd196436c7bbbf0714622094356e3e323d338ffd8b9d2401ca5f2f6a29c5 | Rejected R19V1 author input | R19 rejection and R31 independently verified historical-input admission | HISTORICAL_TERMINAL |
| HOME/GAIA-campaign-20261008-network | 41c4fd196436c7bbbf0714622094356e3e323d338ffd8b9d2401ca5f2f6a29c5 | Rejected R19V1 independent reviewer input | Explicit completed reviewer/released token; surviving four diagnostic artifacts exact | HISTORICAL_TERMINAL |
| HOME/GAIA-campaign-20261008-c1-tests | 5246989341c71d6e16d81acdabef259e49b6ff0c11b318588deaf14e13000b80 | Accepted R19V2 reviewer input | Original static-audit source hash exact; final-audit preserved; independent report terminal/released | HISTORICAL_TERMINAL |
| HOME/GAIA-campaign-20261011-r24-fuel-targets-review | e877a34cc20b570306939f9f527048bf77584f6b1d3e78f9b4addf557fc46279 | Accepted R24 reviewer candidate | Review freeze69/69 members exact; ACCEPT/IMPROVED/heavy RELEASED; final report hash exact | HISTORICAL_TERMINAL |
| HOME/GAIA-campaign-20261011-r28-fuel-operator-keys | 49b9ffeef7851e12aa4e8a309fb63356d226a6526cffbdaef052d4c9d3fde0d7 | Accepted R28 author candidate | Frozen publication3/3 inputs exact; integration records author terminal/token released | HISTORICAL_TERMINAL |
| HOME/GAIA-campaign-20261011-r28-fuel-operator-keys-final | 49b9ffeef7851e12aa4e8a309fb63356d226a6526cffbdaef052d4c9d3fde0d7 | Accepted R28 final-verifier candidate | Recorded backend-cwd union13/13 inputs exact; candidate custody and final verification/integration terminal records preserved | HISTORICAL_TERMINAL |
| SSD/author-worktree | dd7a8bcd259efc1ef9853bef07a69b2123eb1cedfbcf78aa1eb0a8b645b48a2e | Accepted R31 author candidate | Author freeze140/140 exact; IMPROVED/READY_FOR_REVIEW/heavy RELEASED | HISTORICAL_TERMINAL |
| SSD/review-worktree | dd7a8bcd259efc1ef9853bef07a69b2123eb1cedfbcf78aa1eb0a8b645b48a2e | Accepted R31 independent reviewer candidate | Reviewer freeze106/106 exact; IMPROVED/ACCEPT/heavy RELEASED | HISTORICAL_TERMINAL |

## Source-bound records and manifests

- R19V1: `REJECTION_R19_DRIVER_MISMATCH_2026-10-10.md` explicitly rejects the
  functional ORM-lifetime regression, records the exact source and confirms the
  independent reviewer completed/released execution. ENOSPC prevented its final
  review report/protected-after/complete manifest: **no complete V1 freeze is
  claimed**. Surviving lifetime-results/log649ba839, diagnostic6be604ab and
  exit9a271f2a all match the report. Private directory:
  `/home/cbo/.cache/gaia-campaign/20261009-r19-independent-review/`.
- R19V2: `/tmp/gaia-r19-v2-review-20261010/static-audit.json` binds52469893,
  SHA43ef8712002720bb9ee344e94b045456197e89b8da73ad05fc6c4d927441a9c7;
  final-audit646409316bed880c01def0ad422e0b5e6b8adaad1e93bec5f134294d0ad7fda5.
  `REVIEW_R19_V2_ORM_LIFETIME_2026-10-10.md` explicitly declares gates terminal,
  heavy RELEASED and rejected V1 excluded. Accepted integration report binds
  the same candidate. Existing six-source R31 admission corroborates both R19
  author/reviewer dispositions; no new old-tree execution was performed.
- R24 reviewer `review-freeze.json`:
  2ed22c145436ab9f4f10e4620d82955d27bff83adb24400923d078e277ab611b,
 69 members exact, terminal ACCEPT/heavy RELEASED. Source e877a34c and report
 185e5d6032191f014329c370a57fffe163fedcf041e1100ee63c1f823df7810d exact.
  Related author candidate-freeze521a43e2e894e659c7b54a98525a78fec9a5c7b88479a85d369cef6f391b6d90:
 46 members exact. Files remain in
 `/home/cbo/.cache/gaia-campaign/20261011-r24-fuel-targets-{review,author}/`.
- R28 author frozen-publication-inputs.sha256:
 882017f365fbb3b04b2f071045320a99ed498181e89b91783df3e8de7954233a,
  source/spec/report3/3 exact. Final union-candidate-inputs.sha256:
 a118690fccc0fa1af31a1d724b184336122cdb2ee05077f54d1b6c614de13314,
  source/old11specs/NEWspec13/13 exact at its **backend command cwd**.
  Candidate custody SHA10dfc5b3a868d09390a4b9dda7386c4830cd7848787bf996a1c4d8d2f673f00c
  records only analytics changed, original specifications exact and baseline/main
  unchanged. Private directories20261011-r28-{author,final}; terminal disposition
  bound by FINAL_VERIFICATION and INTEGRATION_R28_FUEL_OPERATOR_KEYS.
- R31 author SSD/evidence/FREEZE.json:
 f33d8a4040d055fa0d3c30402c814d3433eed9c06d29ea0e5a3bf38adae08281,
 140 exact members, source dd7a8bcd and explicit heavy RELEASED.
- R31 reviewer SSD/review-evidence/FREEZE.json:
 73ccea3a6c22debc0847e86867eb3ea0fffbba64caf12d4501207781d70f55bf,
 106 exact members, source dd7a8bcd and explicit heavy RELEASED.
- R31 root SSD/root-evidence/FREEZE.json:
 13650c140d6dcf6bf22696448b67b4612eb396c506202fa3a305d13c5c9d59aa,
 169 members.167 match live references; two intentionally evolving governance
  references (global campaign report and PROGRESS) differ after R32. Both hashes
  match **exactly** their Git blobs at the manifest's recorded committed HEAD
 2c9e9b64a9167ed122c9ac74141fae0f66eeb1dc: ebee22f9 and bc320054 respectively.
  This is historical source custody, not a false claim of an all-live169 freeze.

## Active-owner and execution check

Live team snapshot shows only Coordinator/R33 author/R33 provenance running;
remaining visible R29/R30/R32 agents completed/token released. Historical agents'
terminal status is established by their above explicit reports/manifests, not
their absence from the live tree alone. Bounded native process census found no
codex exec/pytest/run-one or historical worktree process. No mtime is used as
terminal proof. No active or UNKNOWN historical owner was identified.

## Limits and final disposition

Static evidence only: no tests, coverage, complexity, ratchet, Graphify or native
gate executed, no commit/import/cleanup, no old evidence rewritten. An initial
static R28 final-manifest lookup assumed repository cwd and found missing paths;
its preserved command/spec paths establish backend cwd, where all13 match.
No native test was rerun. R31 evolving governance references are explicitly
resolved against its historical commit, never repaired in place.

R33 may proceed only under Coordinator's separate runtime/test gate admission.
R19V1 remains REJECTED, global30 baseline findings remain separate, and the
global campaign remains ACTIVE / INCOMPLETE. Provenance agent TERMINAL after
NEW report/evidence freeze; heavy token never acquired.
