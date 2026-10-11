# R35 Bonifica results — source provenance

Disposition: **ADMIT ORIGINAL CHARACTERIZATION ONLY**. No runtime edit admission,
coverage certification, complexity reduction, historical terminal claim or native
gate PASS follows from this report. Fresh original full-file statement/branch
100 and coordinator admission remain required by the R35 registry.

## Scope and custody

Read-only census of every entry in `git worktree list --porcelain`, with
`GIT_OPTIONAL_LOCKS=0` and `GIT_NO_REPLACE_OBJECTS=1`. The sole repository write is
this NEW report in the assigned provenance worktree. Private evidence is the
sibling `provenance-evidence/`; no runtime, tests, baseline, config, Git history,
commit, cleanup or worktree registration mutation was performed. No native gate,
Graphify or tests were run. This source census changes no module structure.

Original source SHA256:
`e01d85f2cfbd726933819db1dc32b84b46cae37b443cfc4943a9b3ad843625e4`.
Main HEAD: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
Campaign and both current R35 worktree HEADs:
`0078b65ce48ba06e89c4fc3681cda1f8ae286da7`.
Merge-base for campaign/R35 against actual main is exactly main55a.
Both immutable Git sources and main/campaign/R35 checkout bytes match original.
`source-main-campaign.diff` is empty. Source path history is retained for both
main and campaign; latest original path-changing commit is
`a067a0780b247bc9de1b35e489ab78f676fd17af`.

`own-tracked-before.json` and `own-tracked-after.json` bind every preexisting
tracked path. Main and integration all-tracked manifests, plus selected existing
Bonifica tests/baseline/config custody, are retained separately. Main has unrelated
tracked changes (nine porcelain entries initially), preserved. Those manifests
are observed bytes, not a claim that main is globally clean or frozen.

## Census findings

153 registered entries: 138 present, 15 missing directories whose registrations
are prunable. Of the present entries, 137 contain this source: 126 exact-original
and 11 committed historical variants. One older HEAD lacks the source path.
All 137 target sources match their respective HEAD bytes; zero dirty target-source
snapshots exist in this census. A second observation confirms HEAD and source
identity for all 138 present entries; registrations are unchanged. First-observation
times are recorded in `census.json`; `repeat-check.json` retains second identities.
These repeated reads are not an atomic repository-wide lock. Initially 25 present trees have tracked changes elsewhere.
Full statuses including untracked paths are preserved on the second pass.

The historical variant has SHA256
`34ac565eadec7cf5b165cef781cbceea8e7702820185d1bb294909737706b078`.
All eleven variant target files are committed and stable; their exact snapshots
and histories are preserved separately. Their latest source-path change is
`aa3cf4f5b26ae13e15f5c2b0e549c04801a03ada`, preceding main's
`a067a078…` path change. They are **excluded from R35 original inputs**.
No claim is made that these external branches or actors are terminal.
`GAIA-quality-services-drift` has one untracked path elsewhere; its target source
remains clean. Clean source status does not imply complete-worktree cleanliness.

Historical B6 `GAIA-campaign-20261008-bonifica` is at main55a and exact-original
source. Its complete porcelain status including untracked files is empty in the
second observation. Global registry records B6 **BLOCKED**, read-only readiness,
14 tests and historical 34.34% statement / 28.13% branch coverage, with runtime
not authorized. These are historical recorded results, not rerun certifications.
Root explicitly declined to infer terminal status from cleanliness. Accordingly
there is no invented terminal/frozen assertion; there is no dirty B6 target
snapshot requiring lifecycle admission. Historical inputs remain untouched.

## Limitations and next admission

Missing/prunable registrations were enumerated, never pruned: their disk bytes
cannot be inspected. `gaia-agent-operazioni` is an existing older checkout with
no source at HEAD and no current target path, an explicit not-applicable result.
Source lifecycle of unrelated external branches was not audited. Stable repeated
reads prove observed identity only; they do not freeze external owners. A new
source/HEAD change invalidates admission and requires a fresh census of that input.
The R35 author remains ACTIVE/static under the registry; no runtime edit is
admitted here. Fresh complete-file metrics/coverage and original characterization
are separate serial responsibilities. No evidence permits global coverage or
campaign completion claims.

## Complete registered-worktree index

IDs join `census.json`, numbered status/diff artifacts and `repeat-check.json`.
`original` = exact e01d85 source; `historical` = committed34ac source; `absent` =
HEAD/current path missing; `missing` = worktree directory absent. Counts refer to
porcelain status entries, not line counts inside modified files.

| ID | Worktree | HEAD | Source | Tracked changes first | Full status second |
| --- | --- | --- | --- | --- | --- |
| 000 | `/home/cbo/CursorProjects/GAIA` | `55a1b1d35911451e018b662c2acc450bf5994ea2` | original | 9 | 23 |
| 001 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-analytics` | `218670c73b7abdcb0210e61ac04e15271c9ebc41` | original | 1 | 5 |
| 002 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-baseline` | `49a2b3a1491c0358be088c938bbf187a2d11533a` | original | 0 | 0 |
| 003 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-bonifica` | `55a1b1d35911451e018b662c2acc450bf5994ea2` | original | 0 | 0 |
| 004 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-c0-tests` | `49334bdd2497003bdee26747206f35eea677aba7` | original | 0 | 0 |
| 005 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-c1-tests` | `ce0b7c3ea3b9e23b463b7dfbf2f945386a1d8a62` | original | 1 | 4 |
| 006 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-c10-tests` | `c3d428f97e1dbb07a70d92c1e81a36d2a3d8f401` | original | 0 | 0 |
| 007 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-c11-tests` | `bab83acdf1d9ab3b472c061516bdb9d927795b1f` | original | 0 | 0 |
| 008 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-c12-tests` | `53e9405b2c929abd3f2951929c0e6164afd0b19c` | original | 0 | 0 |
| 009 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-c12-verification` | `9ea8f4fea121f59e5cd85b19ff4cf0f701b3c6dd` | original | 0 | 0 |
| 010 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-c2a-tests` | `28dfb7c5b37876f8560109f6594bea83e531aac3` | original | 0 | 0 |
| 011 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-c2b-tests` | `34ee63925ab851ed1f392f52a052ebd0a5821385` | original | 0 | 0 |
| 012 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-c3-tests` | `f70017eac72ff891a9983b8ad4a9b5f8b2179995` | original | 0 | 0 |
| 013 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-c4-tests` | `e9577559bd001a459d00282083ac9241bc295d8e` | original | 0 | 0 |
| 014 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-c5-tests` | `72cc29fa2a59f92edea5750545a76c539dc987b2` | original | 0 | 0 |
| 015 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-c5b-tests` | `d145971b213c96f515cdb152e87a35cfd31d79c6` | original | 0 | 0 |
| 016 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-c6-tests` | `7bc9ec173f8b42ee3332c8778bab0fe1b03f5da6` | original | 0 | 0 |
| 017 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-c7-tests` | `bc312caf70e08140ed1d3ae9a2601e9d0385d611` | original | 0 | 0 |
| 018 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-c8-tests` | `473f021ba1ea6187d1f2ef00eb79cd2d684ea8a0` | original | 0 | 0 |
| 019 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-c9-tests` | `65de921a6bd5695a75d0f18051d28951e2887065` | original | 0 | 0 |
| 020 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-capacitas` | `60d44529d9746e392150a7d5636df93b430f7291` | original | 0 | 1 |
| 021 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-catasto-backend` | `6e0536520764bc00c06155380b000bb81523e314` | original | 0 | 0 |
| 022 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-catasto-ui` | `a7c75dde9ec508e537f5ecc065ba2eebd102fea6` | original | 0 | 0 |
| 023 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-char-verification` | `7f0c6f0a3cdda9669ba7f724f77fe6edc07015d0` | original | 0 | 0 |
| 024 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-gis-baseline` | `55a1b1d35911451e018b662c2acc450bf5994ea2` | original | 0 | 0 |
| 025 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-gis-causality` | `febc7bfb51fc89bc46ba0dfdabbfa0ef7009ed61` | original | 0 | 0 |
| 026 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-gis-readiness` | `bf28b1d4ab079ff9da822b8e15cb0964e9377e61` | original | 0 | 1 |
| 027 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-integration` | `0078b65ce48ba06e89c4fc3681cda1f8ae286da7` | original | 0 | 1 |
| 028 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-modal-provenance` | `1d8c8411a573c2b0d5a2b6b371774eaf55576699` | original | 0 | 0 |
| 029 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-network` | `218670c73b7abdcb0210e61ac04e15271c9ebc41` | original | 1 | 5 |
| 030 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-presenze` | `c14eb8bd19d5645d1cb57442379c771d789730e2` | original | 0 | 0 |
| 031 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-r2-analytics` | `6909abd756567e48c501c8ef24d8d1a15b73ebdb` | original | 0 | 0 |
| 032 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-r2-presenze` | `5f1ba8400c716e818eb0fca47e24921badf0e094` | original | 0 | 0 |
| 033 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-r2-settings` | `9a01d35a08ccc02c6978d5be8d95b280df3395ef` | original | 0 | 0 |
| 034 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-r3-analytics` | `399825ab7118839d29e94d7106dd6569260f38ca` | original | 0 | 1 |
| 035 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-r3-presenze` | `471935ec0874ba92ff71ecec0208c05e28e00709` | original | 0 | 1 |
| 036 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-r3-settings` | `82ec7533e483e13b0e3e528e7911194605723b94` | original | 0 | 0 |
| 037 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-settings-ui` | `d92d39aa463ec998e26d83cbe01a25342c1cfeb7` | original | 0 | 0 |
| 038 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-terreni` | `55a1b1d35911451e018b662c2acc450bf5994ea2` | original | 0 | 0 |
| 039 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-utenze-ui` | `3cb1b6e379dadc4df84d08d957afaf8f2ea75843` | original | 0 | 0 |
| 040 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-wiki` | `4df202e70ddb74a0a4ced0a0a9dcaa86105b0487` | original | 0 | 0 |
| 041 | `/home/cbo/CursorProjects/GAIA-campaign-20261008-worker` | `55a1b1d35911451e018b662c2acc450bf5994ea2` | original | 0 | 0 |
| 042 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-capacitas-closure` | `ba8d23f79b016d52698d0ed12d000544db5e6632` | original | 0 | 0 |
| 043 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-gis-test-fix` | `13b6a8f2165ef6ddf0d6b64a092d1e710ed89743` | original | 0 | 0 |
| 044 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-gis-verification` | `9ec2dcac769cfb51451d5c07f2021c86a47393d5` | original | 0 | 0 |
| 045 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r10-capacitas` | `be3847888b8b859c2169636d02915131f1690968` | original | 0 | 0 |
| 046 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r10-capacitas-review` | `3be62f81cffbfeffc989bb7434aa2b513c61a38b` | original | 0 | 0 |
| 047 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r10-verification` | `43408282994e28442f838cbf76c6d76b3515d4be` | original | 0 | 0 |
| 048 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r11-capacitas-monitors` | `3b511b6da3c9d4c57dd4ef1130732fac459a613d` | original | 0 | 1 |
| 049 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r11-capacitas-monitors-final` | `5981be8da26b46b72e8961bb6fe5d10bac158820` | original | 0 | 0 |
| 050 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r11-capacitas-monitors-review` | `8da06a90fdeff20d0611bd2f3ae7492ebc4517c0` | original | 0 | 2 |
| 051 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r12-capacitas-final` | `bfe0b2d7b0324db397fd698d3aad16fc9b20a38f` | original | 0 | 0 |
| 052 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r13-capacitas-execution-controls` | `3a22f966c9b95feb908b4aef7c3250e28ec4136a` | original | 0 | 1 |
| 053 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r13-capacitas-execution-controls-final` | `ac922cb3df670685616f4166b4d4278056125410` | original | 0 | 0 |
| 054 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r13-capacitas-execution-controls-review` | `1a6aade17409cb835d95b30ae8007ef7ffdfc3e2` | original | 0 | 1 |
| 055 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r14-operazioni-operator-km` | `3881427aac609452050ce8aa0222073e41f1495c` | original | 0 | 1 |
| 056 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r14-operazioni-operator-km-final` | `c59cf85a3c4e6e0d5a1ef0908311180cab3aa067` | original | 0 | 0 |
| 057 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r14-operazioni-operator-km-review` | `b128e3963ca04176a4195be0b18f7d98784477e1` | original | 0 | 1 |
| 058 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r15-capacitas-create-jobs` | `995e3778cc6e71e6ca13780ba7b511a2dd4733f0` | original | 0 | 0 |
| 059 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r15-capacitas-create-jobs-review` | `c7bfb36ba030b5fea1329209497a488d0b83e78a` | original | 0 | 0 |
| 060 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r16-capacitas-credential-defaults` | `559f186663f15f261e9ccd0ca8f1afb17bc4c646` | original | 0 | 2 |
| 061 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r16-capacitas-credential-defaults-review` | `1d4bf80d82c71e23778069f2bcafc86461a9dff7` | original | 0 | 2 |
| 062 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r4-fuel-related` | `6b1bec8d98571240c809fdf39f82c65af1c8c04f` | original | 0 | 0 |
| 063 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r4-fuel-review` | `afcb2146d7a6a41016548924ef55b1d5bc4b7fd9` | original | 0 | 0 |
| 064 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r4-fuel-verification` | `716a53db8ca9e928db1c6bb636993fd9fe8d005e` | original | 0 | 0 |
| 065 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r5-orphan-operators` | `cd4b11457f2cb3848b87a5c41d110657d8d11d27` | original | 0 | 0 |
| 066 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r5-orphan-review` | `8730228ff3aa3edbd1d907967dd2a9d6a156742b` | original | 0 | 0 |
| 067 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r5-orphan-verification` | `c59791416973804a81f693da9b82e1ac542f8881` | original | 0 | 0 |
| 068 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r6-presenze-daily` | `56c46570f48c3281ba2db2b3e8220338b29c8e88` | original | 0 | 0 |
| 069 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r6-presenze-review` | `c1475bb2e31efd4e2d1173a3233983fab2be361c` | original | 0 | 0 |
| 070 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r6-presenze-verification` | `3486b24eb04cc08d15113d43ef2542fca9bff046` | original | 0 | 0 |
| 071 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r7-presenze-anomaly` | `d879d2681841f2bbab6b885648ed6cfa8e847c1c` | original | 0 | 0 |
| 072 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r7-presenze-review` | `a7341048abdd7a5b4877c1606dda675275d894dc` | original | 0 | 0 |
| 073 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r7-presenze-verification` | `e57120c53127715ed451e095b4b48221752b9870` | original | 0 | 0 |
| 074 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r8-presenze-presentation` | `79bc9969d17111a098d37bc22e4e15f7172feb7d` | original | 0 | 0 |
| 075 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r8-presenze-review` | `687a4a4928603664c61ea8b04cedf0e97f36e854` | original | 0 | 0 |
| 076 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r8-presenze-verification` | `8ab91f556afe6eac14092dc5a32635930d7d9a01` | original | 0 | 0 |
| 077 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r9-presenze-mutations` | `19197441f71e479d410edca5bc88c6fb9f26b091` | original | 1 | 1 |
| 078 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r9-presenze-review` | `47128b9dcf429fa4fb8c7a988221bd9322c127a2` | original | 0 | 2 |
| 079 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-r9-presenze-verification` | `0fa78703e9dea3c0d34d7b6a9812ba4e7a185c73` | original | 0 | 0 |
| 080 | `/home/cbo/CursorProjects/GAIA-campaign-20261009-suites-verification` | `34c13604f49de64ced59bf6846998556e7c873b9` | original | 0 | 3 |
| 081 | `/home/cbo/CursorProjects/GAIA-campaign-20261010-r16-matcher` | `b3d4377f8c999e2ac59d3a00e34f55cf4dae3818` | original | 0 | 0 |
| 082 | `/home/cbo/CursorProjects/GAIA-campaign-20261010-r16-matcher-final` | `392b0da7fc783a8c0cad8c822fadb9994c11f480` | original | 1 | 3 |
| 083 | `/home/cbo/CursorProjects/GAIA-campaign-20261010-r16-matcher-review` | `a7fae4d23069a7b1b9948f30cd83f9be5f5a17ca` | original | 1 | 3 |
| 084 | `/home/cbo/CursorProjects/GAIA-campaign-20261010-r20-capacitas-credentials` | `9660bfdeb72c276e52fd5c0c785d4d59d8607c61` | original | 1 | 3 |
| 085 | `/home/cbo/CursorProjects/GAIA-campaign-20261010-r20-capacitas-final` | `ff0394acfed26cc4ce3007c66996fd44f0c789de` | original | 1 | 1 |
| 086 | `/home/cbo/CursorProjects/GAIA-campaign-20261010-r20-capacitas-review` | `438df8e83ba5a0ee7f328deb565be460d7932c59` | original | 1 | 2 |
| 087 | `/home/cbo/CursorProjects/GAIA-campaign-20261010-r21-capacitas-final` | `330be6238552fd44e4f4ef9a56740dbd8018b6ca` | original | 1 | 2 |
| 088 | `/home/cbo/CursorProjects/GAIA-campaign-20261010-r21-capacitas-job-actions` | `0e1661d5d8b89d6f4c95bed6a6a43bccc0fc23d5` | original | 0 | 0 |
| 089 | `/home/cbo/CursorProjects/GAIA-campaign-20261010-r21-capacitas-review` | `1cd01a7949acb273edb30aa4dc9af27fd9e7d846` | original | 0 | 2 |
| 090 | `/home/cbo/CursorProjects/GAIA-campaign-20261011-r22-utenze-nas-review` | `2cf665054f5bb89e5438c347778ba0f2021cb1fb` | original | 0 | 1 |
| 091 | `/home/cbo/CursorProjects/GAIA-campaign-20261011-r23-utenze-preview-review` | `36e2fe0481891417458742eee050bb033559ec83` | original | 0 | 1 |
| 092 | `/home/cbo/CursorProjects/GAIA-campaign-20261011-r24-fuel-targets-review` | `34356f60c42b50674612161a8dc1bead783f09e7` | original | 1 | 2 |
| 093 | `/home/cbo/CursorProjects/GAIA-campaign-20261011-r25-capacitas-results-review` | `9660bfdeb72c276e52fd5c0c785d4d59d8607c61` | original | 0 | 2 |
| 094 | `/home/cbo/CursorProjects/GAIA-campaign-20261011-r26-presenze-review` | `388b052b8726aceeaa94df85cc76a3efe4c22521` | original | 0 | 1 |
| 095 | `/home/cbo/CursorProjects/GAIA-campaign-20261011-r26-utenze-review` | `fb0cf15c7c44e4e05a0f21885155f97ace678c21` | original | 0 | 1 |
| 096 | `/home/cbo/CursorProjects/GAIA-campaign-20261011-r27-inactive-vehicle` | `0f0abea13b47f4d9851909e64ae0c18e72523820` | original | 0 | 0 |
| 097 | `/home/cbo/CursorProjects/GAIA-campaign-20261011-r27-inactive-vehicle-review` | `d035d6559bb1ef66f0268faf33653f501395cc6d` | original | 0 | 1 |
| 098 | `/home/cbo/CursorProjects/GAIA-campaign-20261011-r28-fuel-operator-keys` | `fed2cc7d0f2ee1dd128b6d11f68655179b9711d7` | original | 1 | 3 |
| 099 | `/home/cbo/CursorProjects/GAIA-campaign-20261011-r28-fuel-operator-keys-final` | `fed2cc7d0f2ee1dd128b6d11f68655179b9711d7` | original | 1 | 3 |
| 100 | `/home/cbo/CursorProjects/GAIA-campaign-20261011-r28-fuel-operator-keys-review` | `fed2cc7d0f2ee1dd128b6d11f68655179b9711d7` | original | 0 | 1 |
| 101 | `/home/cbo/CursorProjects/GAIA-campaign-20261011-r29-catasto-particella` | `f3598577ddb8d681fa30ea4ed984a2fc4209f826` | original | 0 | 2 |
| 102 | `/home/cbo/CursorProjects/GAIA-code-complexity-align` | `60e37aed6c328a196f564a21360e92b14942d12c` | historical | 0 | 0 |
| 103 | `/home/cbo/CursorProjects/GAIA-complexity-baseline-reconcile` | `d67495c095d986c28b0f7a0a7e981832ff827f80` | original | 0 | 0 |
| 104 | `/home/cbo/CursorProjects/GAIA-complexity-capacitas` | `0efde6a965a76793b997f6c99443693d7df6e68d` | original | 0 | 0 |
| 105 | `/home/cbo/CursorProjects/GAIA-complexity-operazioni` | `eb59473cf550227e1bea7052687ba6b2bbc67da3` | original | 0 | 0 |
| 106 | `/home/cbo/CursorProjects/GAIA-complexity-ratchet` | `623ae160c5f8b97acc6dfe651e5c2cf9bc3c1975` | historical | 0 | 0 |
| 107 | `/home/cbo/CursorProjects/GAIA-complexity-swarm` | `e423a6e9aa69156243b71fe07966ed0488001d57` | original | 0 | 0 |
| 108 | `/home/cbo/CursorProjects/GAIA-gis-platform-complete` | `a9d2f35231a4bbea1724069cbf89c6729fd87f4c` | historical | 0 | 0 |
| 109 | `/home/cbo/CursorProjects/GAIA-perpetual-sync` | `19a5e9a12cb0ade6aad773b249412846b941f3a8` | historical | 0 | 0 |
| 110 | `/home/cbo/CursorProjects/GAIA-presenze-minuti-riconosciuti` | `8ca02298ff61976764cb211b5494d82142ab3b8f` | original | 0 | 0 |
| 111 | `/home/cbo/CursorProjects/GAIA-quality-services-drift` | `442f1ace81e40183de11c10f469b960ee4d4a8cf` | historical | 0 | 1 |
| 112 | `/home/cbo/CursorProjects/GAIA-territorio` | `b5e98a0eafa96f074ba2a8892200b3e3de8c8f7c` | historical | 0 | 0 |
| 113 | `/home/cbo/CursorProjects/GAIA-wiki-mcp-mainline` | `e54cb51cea6acd0e40c702099026c7de4a26936d` | original | 5 | 5 |
| 114 | `/home/cbo/CursorProjects/GAIA-wip-latest-integration` | `14eb8d7f2e963c852e760930764657f79140e30b` | historical | 0 | 0 |
| 115 | `/home/cbo/CursorProjects/gaia-agent-operazioni` | `5670d7caf9c3b2ff5128a7a07cc3d2bc38c89194` | absent | n/a | 0 |
| 116 | `/home/cbo/CursorProjects/gaia-inaz-ferie-main` | `565e2fd67032f01cb92d3bc9dced65af27cf152c` | historical | 0 | 0 |
| 117 | `/home/cbo/CursorProjects/gaia-thesis-experiment-v1` | `e8962ff70b9bd7d767bfda15c3db35d23fe8dcc3` | historical | 0 | 0 |
| 118 | `/home/cbo/CursorProjects/gaia-thesis-experiment-v2-refreeze` | `2575a6f1586891514b195b83fc8609a8e8ca664d` | historical | 0 | 0 |
| 119 | `/home/cbo/CursorProjects/gaia-thesis-experiment-v3-final-refreeze` | `aaaf2722ba210d7083c91aa8bf3f372497d2c0d7` | historical | 0 | 0 |
| 120 | `/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r29/review-worktree` | `f3598577ddb8d681fa30ea4ed984a2fc4209f826` | original | 0 | 2 |
| 121 | `/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r30-catasto-ade/author-worktree` | `3b99dea5981dabf2feac1611366ea7405f3a2bcc` | original | 0 | 2 |
| 122 | `/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r30-catasto-ade/review-worktree` | `3b99dea5981dabf2feac1611366ea7405f3a2bcc` | original | 0 | 2 |
| 123 | `/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r31-session-distance/author-worktree` | `6089b05e1c047f388badf8f9b53caa18a1babf6e` | original | 1 | 3 |
| 124 | `/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r31-session-distance/review-worktree` | `6089b05e1c047f388badf8f9b53caa18a1babf6e` | original | 1 | 4 |
| 125 | `/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r32-utenze-documents/author-worktree` | `2c9e9b64a9167ed122c9ac74141fae0f66eeb1dc` | original | 1 | 3 |
| 126 | `/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r32-utenze-documents/review-worktree` | `2c9e9b64a9167ed122c9ac74141fae0f66eeb1dc` | original | 1 | 4 |
| 127 | `/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r32-utenze-documents/verify-worktree` | `2c9e9b64a9167ed122c9ac74141fae0f66eeb1dc` | original | 1 | 5 |
| 128 | `/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r33-operator-consumption/author-worktree` | `1613f2b56f0c8ef2dcf253dd1ee9bcee8299b380` | original | 1 | 3 |
| 129 | `/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r33-operator-consumption/final-worktree` | `1613f2b56f0c8ef2dcf253dd1ee9bcee8299b380` | original | 1 | 5 |
| 130 | `/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r33-operator-consumption/provenance-worktree` | `1613f2b56f0c8ef2dcf253dd1ee9bcee8299b380` | original | 0 | 1 |
| 131 | `/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r33-operator-consumption/review-worktree` | `1613f2b56f0c8ef2dcf253dd1ee9bcee8299b380` | original | 1 | 4 |
| 132 | `/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r34-presenze-summary/author-worktree` | `3e4ad9f030370a2d21cd4c28a6f7cc569c287dde` | original | 1 | 2 |
| 133 | `/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r34-presenze-summary/final-worktree` | `3e4ad9f030370a2d21cd4c28a6f7cc569c287dde` | original | 1 | 2 |
| 134 | `/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r34-presenze-summary/provenance-worktree` | `3e4ad9f030370a2d21cd4c28a6f7cc569c287dde` | original | 0 | 1 |
| 135 | `/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r34-presenze-summary/review-worktree` | `3e4ad9f030370a2d21cd4c28a6f7cc569c287dde` | original | 0 | 1 |
| 136 | `/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r35-bonifica-results/author-worktree` | `0078b65ce48ba06e89c4fc3681cda1f8ae286da7` | original | 0 | 0 |
| 137 | `/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r35-bonifica-results/provenance-worktree` | `0078b65ce48ba06e89c4fc3681cda1f8ae286da7` | original | 0 | 0 |
| 138 | `/tmp/gaia-baseline-audit-20261003` | `fccd06b00dc88c31aa6b385a5b1d3c88cc6efae9` | missing | n/a | n/a |
| 139 | `/tmp/gaia-dotazioni-baseline-base` | `e33d5c69f6a9e19a81b9450389ac5f5b99fd1f19` | missing | n/a | n/a |
| 140 | `/tmp/gaia-dotazioni-validation` | `e33d5c69f6a9e19a81b9450389ac5f5b99fd1f19` | missing | n/a | n/a |
| 141 | `/tmp/gaia-meal-baseline-base` | `78558ede6ac8b099879e78072d278e541c1321c1` | missing | n/a | n/a |
| 142 | `/tmp/gaia-meal-release` | `6f97ca7f238486b60189091321426d00e4c81961` | missing | n/a | n/a |
| 143 | `/tmp/gaia-presenze-baseline-repair` | `60f3f32d98cc51ce0afd1ffc078ba4a1eb6aa5a9` | missing | n/a | n/a |
| 144 | `/tmp/gaia-presenze-canonical-daily-20260831` | `d5c0ed5ad115a6eac37351825ce5754a72583085` | missing | n/a | n/a |
| 145 | `/tmp/gaia-presenze-review` | `dc66972813970573ec5d1dd8d0b3426fa6c56116` | missing | n/a | n/a |
| 146 | `/tmp/gaia-release-all-20261007` | `703f8411871e88e10b1c45151ba035f6b1f35a8f` | missing | n/a | n/a |
| 147 | `/tmp/gaia-release-frozen-20261007` | `d6c34ba819d4c0ed103385e5a24cc6bc2ea1409d` | missing | n/a | n/a |
| 148 | `/tmp/gaia-sister-autosync-release-20260924` | `c42bea845fa0de39f8bd9d8f067747a32e237b5b` | missing | n/a | n/a |
| 149 | `/tmp/gaia-sister-autosync-release-20260927` | `57d9a4216547ad302916769c1c72e495ad37eb8b` | missing | n/a | n/a |
| 150 | `/tmp/gaia-w1-catasto` | `bfc8e68fd6d4acf373b23b7cc15693c80bd75f18` | missing | n/a | n/a |
| 151 | `/tmp/gaia-w1-organigramma` | `bfc8e68fd6d4acf373b23b7cc15693c80bd75f18` | missing | n/a | n/a |
| 152 | `/tmp/gaia-w1-utenze` | `bfc8e68fd6d4acf373b23b7cc15693c80bd75f18` | missing | n/a | n/a |

## Freeze and handoff

Exact report/evidence inventory: sibling `provenance-evidence/MANIFEST.sha256`,
using paths relative to the R35 SSD directory. Its detached digest is
`provenance-evidence/MANIFEST.digest`. Manifest excludes itself and its digest to
avoid recursion and includes the report. Agents must verify it with
`sha256sum -c MANIFEST.sha256` from the R35 SSD directory before reuse. All
inventoried evidence and this report are frozen after publication to root.
No subsequent alteration of this report or evidence is authorized by this census.
Coordinator owns any integration/governance update. No commit was created.
