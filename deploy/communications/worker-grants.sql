-- Run only with explicit DBA authorization. Role creation and password provision are external.
-- Run after migration; public is the GAIA application schema. Review effective privileges first.
GRANT USAGE ON SCHEMA public TO communications_worker;
GRANT SELECT ON
    communication_accounts, communication_templates, communication_messages,
    communication_attachments, communication_authorizations, communication_reviews,
    communication_jobs, communication_attempts, communication_events,
    communication_receipts, communication_controls,
    application_users, sections, role_section_permissions, user_section_permissions,
    ana_subjects, ana_persons, ana_companies, ana_payment_notices,
    ruolo_avvisi, ruolo_partite, ruolo_particelle, ruolo_tributi_payments,
    ruolo_tributi_avviso_status, ruolo_tributi_notes, ruolo_tributi_special_notices,
    ruolo_tributi_special_allocations, ruolo_tributi_year_managers,
    ruolo_tributi_calculation_policies, ruolo_tributi_templates,
    ruolo_tributi_registered_mails, ruolo_tributi_payer_assignments,
    ruolo_tributi_reminder_batches, ruolo_tributi_reminder_batch_items,
    ruolo_tributi_notice_numbers, ruolo_poste_dispatch_items,
    ruolo_notice_documents, ruolo_notice_positions, ruolo_notice_attempts,
    ruolo_notice_evidence, ruolo_notice_notifications, ruolo_notice_recoveries,
    ruolo_notice_import_batches, ruolo_notice_import_rows,
    ruolo_notice_generation_revision, step_documenti, step_ruolo_links
TO communications_worker;
GRANT INSERT, UPDATE ON communication_accounts, communication_controls,
    communication_messages, communication_jobs, communication_attempts TO communications_worker;
GRANT UPDATE ON ruolo_notice_generation_revision TO communications_worker;
GRANT INSERT ON communication_events, communication_receipts,
    ruolo_notice_attempts, ruolo_notice_evidence TO communications_worker;
-- No DELETE, no DDL, no UPDATE of tax data or imported evidence.
-- SELECT is needed by the existing accounting/eligibility and RBAC queries.
-- Validate this dependency closure on the release schema before granting. No credential tables.
