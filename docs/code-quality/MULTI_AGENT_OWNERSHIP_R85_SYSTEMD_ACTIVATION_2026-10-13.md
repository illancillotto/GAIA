# R85 — Scoped systemd-managed activation

User authorizes only manager-controlled CPU/memory/pids activation as private
environment prerequisite. No shared manual writes, existing quota or process
membership changes, runtime/policy changes, native test launch or automatic retry.

| Agent | Domain | File/paths | Slice | Worktree | Branch | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Coordinator | Environment checkpoint | This registry, PROGRESS, R85 report; external r85-systemd-activation/ except preparation/review | Coordinate source review, once-only infrastructure preparation if accepted, terminal review; no native tests | GAIA-campaign-20261008-integration | refactor/complexity-campaign-20261008 | ACTIVE |
| R85 preparer | Private bounded environment | Exclusive external r85-systemd-activation/preparation/; everything else read-only | Source ready, manifestdebf46e4/source265070bc; no launch, preparer stopped | Shared read-only checkout | No new branch | READY_FOR_REVIEW |
| R85 independent reviewer | Infrastructure safety | Exclusive external r85-systemd-activation/review/; everything else read-only | 67/67 corrected inspection checks; one infrastructure probe conditionally accepted, no native readiness; reviewer stopped | Shared read-only checkout | No new branch | READY_FOR_REVIEW |
| R85 terminal reviewer | Observed infrastructure disposition | Exclusive external r85-systemd-activation/terminal-review/; everything else read-only | 1162/1162 checks accept observed infrastructure only, no native readiness; reviewer stopped | Shared read-only checkout | No new branch | READY_FOR_REVIEW |

HEADd1dc5a848886be321fa77f91ea5195c472670d5f;
main/merge-basea51a48dc4caefbdd1aea82fe4d749054b9465970, BASE_REF=main.
R83spec remains NOT_ADMITTED; failed native-r83 and R84rejected source/review
immutable. Prior docs archived before update. R85scope permits additive standard
manager controller activation only, never changed existing numeric limits, manual
shared subtree writes or unrelated process moves. New unit/evidence nonce required.
Infrastructure probe is not native readiness or test PASS. Source review before
any preparation launch; terminal review after. Retain3GiB/512pids/two-core bounds.

Independent source acceptance conditional on Coordinator fresh quiet guard,
exact input/source/executable custody and absent exclusive nonce/unit/evidence
paths. Coordinator may perform one infrastructure-only probe under user grant;
no native launch, failure retry or source admission. Reviewer key-parsing failure
and distinct corrected source checker preserved; no prepared source repair.

One infrastructure-only probe completed exit0 after fresh quiet/input custody.
CPU200000/100000, memory3221225472 and pids512 verified on empty owned child;
supervisor outside child, parent empty. Shared endpoint audits show zero observed
control/limit/membership violations and906surviving identities unchanged. Owned
child removed empty; transient service inactive/dead/MainPID0. No GAIA workload,
app/DB/native test launched. Terminal independent review pending before acceptance.

Terminal review accepted1162/1162checks,36sealed files exact; coordinator accepts
observed infrastructure only.58shared saved-endpoint groups/906original recorded
identities exact, one newPID disclosed; transient changes/attribution unproven.
Unit/child absent, residual slice empty/absent, owned PIDs terminal. No native
grant/readiness or source admission. Publication ratchet preflight refused fresh
external pytest; scanner NOT_RUN, no retry. Last R83measured ratchet remains PASS0.
