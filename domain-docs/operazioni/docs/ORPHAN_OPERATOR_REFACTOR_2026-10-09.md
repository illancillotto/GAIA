# Orphan-session operator identity annotations — R5

## Scope

The R5 slice reduces only operator indexing, name matching and identity
annotations in `anomalies_analytics`. Other anomaly phases and the fuel,
kilometre, work-hours and general session-attribution implementation are
unchanged. This is a behavior-preserving change, not an identity reconciliation
or a change to canonical GAIA/INAZ mappings.

## Query contract

The route keeps the original query order and conditional execution:

1. Open sessions with `started_at <= now_utc - 24h` and
   `started_at >= from_date`, without a `to_date` upper bound.
2. Vehicles, only if qualifying sessions provide vehicle IDs.
3. WC operators linked to qualifying non-None GAIA driver IDs, only if that
   set is nonempty. Integer zero belongs to this set.
4. Name candidates with `last_name IS NOT NULL`, only if at least one
   qualifying session has a nonempty normalized operator name.

SQL, bound parameters and ordering are unchanged. The identity helper performs
no queries or writes. SQL's last-name filter remains in the route; it is not
replaced by a generic attribution context with different candidate semantics.

## Matching and display contract

- Session names normalize through `(name or "").strip().lower()`. Internal
  whitespace is preserved; usernames are not additional name candidates.
- Candidate names join truthy first/last parts with one separator, then strip
  and lowercase for matching. Reverse order is evaluated after forward order.
  Null and empty parts contribute no separator, while whitespace-only parts
  remain truthy and can produce internal spaces before the outer strip.
- Name indexing retains the first candidate for each requested name using
  ordered variants and `setdefault`. No collision correction is introduced.
- GAIA indexing retains the last candidate for each GAIA ID. An explicit linked
  match takes precedence; a missing linked operator falls back to name matching.
  The driver-ID guard uses `is not None`, preserving ID zero.
- A matched label uses joined original name parts, preserving case and internal
  whitespace. A matched operator with empty names has an empty display string.
  An unmatched label is the original `session.operator_name or None`, preserving
  leading/trailing whitespace when the raw name is truthy.
- The annotation returns the narrow typed `OrphanOperatorIdentity(name,
  operator_id)` pair. Operator IDs remain strings; an unmatched ID stays None.

## Response and validation

Hours, severity thresholds, labels, IDs, WC IDs, timestamps, response fields,
aggregate counts and stable severity ordering remain in the route. Persisted
characterization covers nullable names, case, internal whitespace, collisions,
last-wins links, missing links, zero IDs, query conditions, the 24/48-hour
boundaries, absence of an upper date bound and mixed anomaly ordering. Every
new case asserts the entire response, exact SQL/binds/order and absence of
writes or changed persisted record attributes.

The detailed evidence and full callable metrics are in
`reports/code-quality/SLICE_R5_ORPHAN_OPERATORS_2026-10-09.md`. Graphify refresh
belongs to the Coordinator after accepted integration. Residual complexity,
historical global divergences and the separate Capacitas coverage gap remain
open; this slice does not complete the strategic campaign.
