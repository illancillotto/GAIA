# Selected-day keyboard dispatch — R107

One behavior-preserving local simplification in the daily Presenze page;
exact runtime independently admitted after post-copy verification.

## Contract

1. Evaluate `target?.closest("input, textarea, select")` exactly once before
   key dispatch, preserving null handling and lookup failures.
2. Escape prevents the default action and closes the selected record even
   when focus is inside an input, textarea or select.
3. Other keys inside those editing controls do not navigate records.
4. Outside editing controls, ArrowLeft/ArrowRight navigate only when the
   corresponding neighbor exists, preserving preventDefault/setter order.
5. Other keys, listener lifecycle, effect dependencies, record selection,
   permissions, persistence and identity mapping remain unchanged.

The change removes a redundant nested non-Escape comparison, not a domain
validation guard. It adds no helper, new state or effect scheduling. The
contract concerns native stable KeyboardEvent keys, not adversarial getters.

## Evidence and limits

Fresh original and candidate runs each pass496tests/seven unchanged mounted
specs with full-file statement/branch/function/line100%. Candidate has1040
statements/1104branches/306functions/852lines; provider/native/tests maps
agree. Existing tests/configuration and all other runtime files are unchanged.
Supplemental480finite action/exception traces are not a replacement for the
mounted native suite, nor an independent raw coverage conversion replay.

Principal cognitive360→358/cyclomatic316→315; whole-file cognitive1048→1042.
Three nested scanner owners count the same removed physical decision;
308callables and existing findings remain. No debt relocation or policy
relaxation. This is local IMPROVED, not completion of the broader extreme-tail
campaign. Exact integration and fresh main ratchet/full AFTER report passed;
all671frontend runtime files match the validated author worktree. Independent
post-copy review accepted the runtime. Graph/custody receipts are tracked in
`reports/code-quality/R107_PRESENZE_KEYBOARD_DISPATCH_2026-10-15.md`.
