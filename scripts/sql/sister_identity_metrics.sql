-- Fixed-window, read-only comparison. Run with psql -X -qAt, supplying
-- -v user_id=1 -v window_start=... -v window_end=... . No personal data or secrets.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '30s';
WITH settings AS (
    SELECT :'window_start'::timestamptz AS start_at,
           :'window_end'::timestamptz AS end_at,
           :user_id::integer AS owner_id
), events AS MATERIALIZED (
    SELECT e.* FROM sister_portal_events e
    JOIN catasto_batches b ON b.id = e.batch_id
    CROSS JOIN settings s
    WHERE e.user_id = s.owner_id AND e.occurred_at >= s.start_at
      AND e.occurred_at < s.end_at
      AND b.batch_kind IN ('perpetual_sync', 'ruolo_autosync')
), accounts AS (
    SELECT credential_id,
           count(*) FILTER (WHERE event_type = 'download' AND outcome = 'success') AS downloads,
           count(DISTINCT request_id) FILTER (WHERE event_type = 'download' AND outcome = 'success') AS pdf_requests,
           count(*) FILTER (WHERE event_type = 'execution_start') AS execution_starts,
           count(*) FILTER (WHERE event_type = 'session_start') AS browser_starts,
           count(*) FILTER (WHERE event_type = 'polling') AS polling_events,
           count(DISTINCT request_id) FILTER (WHERE event_type = 'polling') AS polled_requests,
           count(*) FILTER (WHERE event_type = 'authentication_gate' AND outcome = 'error') AS authentication_errors,
           count(*) FILTER (WHERE event_type = 'retry' AND context_json->>'error_code' = 'SisterRequestCorrelationError') AS correlation_retries,
           count(DISTINCT request_id) FILTER (WHERE event_type = 'remote_identity') AS identity_observed_requests,
           count(DISTINCT request_id) FILTER (WHERE event_type = 'remote_identity' AND outcome = 'captured') AS identity_captured_requests,
           count(DISTINCT request_id) FILTER (WHERE event_type = 'remote_identity' AND outcome = 'captured'
               AND step = 'identity_v1_hidden_form') AS hidden_form_captured_requests,
           count(DISTINCT request_id) FILTER (WHERE event_type = 'remote_identity' AND outcome = 'captured'
               AND nullif(btrim(identity_request.sister_remote_request_id), '') IS NOT NULL) AS identity_present_at_report_requests,
           count(DISTINCT request_id) FILTER (WHERE event_type = 'remote_identity' AND outcome = 'missing') AS identity_missing_requests,
           count(*) FILTER (WHERE event_type = 'remote_identity' AND outcome = 'conflict') AS identity_conflicts,
           count(*) FILTER (WHERE event_type = 'recovery_navigation' AND outcome = 'error') AS recovery_page_errors
    FROM events LEFT JOIN catasto_visure_requests identity_request ON identity_request.id = events.request_id
    GROUP BY credential_id
), attempts AS (
    SELECT request_id, run_id,
           max(occurred_at) FILTER (WHERE event_type = 'execution_start') AS started,
           max(occurred_at) FILTER (WHERE event_type = 'execution_complete' AND outcome = 'success') AS completed
    FROM events WHERE event_type IN ('execution_start', 'execution_complete') GROUP BY request_id, run_id
), request_cohort AS (
    SELECT r.* FROM catasto_visure_requests r
    JOIN catasto_batches b ON b.id = r.batch_id CROSS JOIN settings s
    WHERE r.user_id = s.owner_id AND r.created_at >= s.start_at AND r.created_at < s.end_at
      AND b.batch_kind IN ('perpetual_sync', 'ruolo_autosync')
), config AS (
    SELECT a.enabled, a.batch_size, a.last_planner_at, a.credential_profiles,
           (SELECT jsonb_agg(jsonb_build_object('account', c.id, 'active', c.active))
            FROM catasto_credentials c WHERE c.user_id = a.user_id) AS accounts,
           (SELECT jsonb_agg(jsonb_build_object('batch_id', b.id, 'credential_ids', b.credential_ids,
               'total', b.total_items, 'completed', b.completed_items, 'failed', b.failed_items))
            FROM catasto_batches b WHERE b.user_id = a.user_id
              AND b.batch_kind = 'perpetual_sync' AND b.status = 'processing') AS active_batches
    FROM catasto_ruolo_autosync_config a CROSS JOIN settings s WHERE a.user_id = s.owner_id
)
SELECT jsonb_build_object(
    'schema_version', 2, 'source', 'gaia_ced_production',
    'captured_at', statement_timestamp(),
    'window_start', (SELECT start_at FROM settings), 'window_end', (SELECT end_at FROM settings),
    'campaign_kinds', jsonb_build_array('perpetual_sync', 'ruolo_autosync'),
    'accounts', coalesce((SELECT jsonb_agg(to_jsonb(a) ORDER BY credential_id) FROM accounts a), '[]'),
    'successful_execution_seconds', (SELECT jsonb_build_object(
        'sample', count(*), 'mean', avg(extract(epoch FROM completed - started)),
        'p50', percentile_cont(0.5) WITHIN GROUP (ORDER BY extract(epoch FROM completed - started)),
        'p95', percentile_cont(0.95) WITHIN GROUP (ORDER BY extract(epoch FROM completed - started)))
        FROM attempts WHERE completed >= started),
    'created_request_cohort', (SELECT jsonb_build_object(
        'total', count(*), 'remote_id_present', count(*) FILTER (WHERE sister_remote_request_id IS NOT NULL),
        'remote_state_present', count(*) FILTER (WHERE sister_remote_state IS NOT NULL),
        'remote_without_id', count(*) FILTER (WHERE sister_remote_state IN ('submitted','pending','ready')
            AND sister_remote_request_id IS NULL)) FROM request_cohort),
    'configuration_at_capture', (SELECT to_jsonb(c) FROM config c),
    'limitations', jsonb_build_array(
        'Configuration and request state are snapshots at capture, not historical reconstructions.',
        'Successful execution duration excludes preclaim authentication and queue time; both events must be in the window.',
        'Before identity_v1 deployment, zero identity events means not instrumented, not zero missing identities.',
        'Account availability is current calendar configuration; lease occupancy is not reconstructed.',
        'Event counts represent operations, not independent incidents; identity counts are distinct per request and outcome.',
        'Captured identity is DOM/URL evidence; presence in the request row is verified separately at report capture, including rejected stale claims.')
);
COMMIT;
