# Capacitas — monitor activity membership (R53)

Terreni, Particelle and Storico share two same-file typed pure policies:
`isCapacitasInFlightJob` checks pending, processing and queued_resume in that
exact order; `hasCapacitasInFlightJobs` short-circuits expired sessions before
calling the existing native `.some`. In-flight ID preparation retains native
`.filter`, `.map` and `Set`, preserving iteration order and duplicate-ID handling.

Four duplicated status chains and three session gates are genuinely deduplicated.
No status getter caching, broader status set, JSX relocation, new hook/state,
effect dependency, interval, API, authorization or INCASS change. Cancelling
rendering, completion selection and async lifecycle remain unchanged. Exact
source restoration and 624 unrelated JSX nodes are independently checked.

Fresh actual-root original and candidate runs each pass 604 assertions across
24 unchanged-bound specs: 559 legacy assertions plus 45 new mounted membership
cases. The descriptors contain 600 distinct keys, not 604: three legacy names
have multiplicities 2/3/2, exactly matching historical R41. The first mistaken
uniqueness audit remains failed and preserved; the distinct multiset audit
passes without rerunning tests, renaming old cases or inventing positional IDs.

Workspace full-file statement/branch/function/line coverage is 100% before and
after: statements 727→725, branch arms 746→733, functions 255→253, lines 634→633.
Unchanged fraction policy is also full-file 100%. Positive raw maps, source
locations, 50+1 implicit-else arms and negative validator countertests pass.
Project typing, strict new-spec typing, lint and actual-main ratchet pass;
baseline, matcher, thresholds, configurations and existing tests are unchanged.

Principal cognitive 307→298, cyclomatic 284→275, callable LOC 2404→2398.
File cognitive 778→762 and cyclomatic 924→906, effective LOC 3108 unchanged.
Physical decisions decrease by eight under both disclosed counting conventions.
The principal leaves the >300 tail; global >300 count becomes four, not zero.
Finding counts remain 1920 errors / 2735 warnings. This is a local improvement,
not campaign completion or certification of general frontend/build/E2E suites.

Complete report and native evidence are recorded in
`reports/code-quality/INTEGRATION_R53_CAPACITAS_ACTIVITY_2026-10-12.md`.
