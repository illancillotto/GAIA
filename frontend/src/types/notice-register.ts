export type NotificationState = "nessuna_evidenza" | "invio_in_corso" | "tentativo_senza_notifica" | "perfezionata" | "da_verificare";
export type RecoveryState = "da_verificare" | "non_affidato_verificato" | "affidato" | "revocato" | "chiuso";
export type RegisterView = "tutti" | "anomalie" | "affidamenti" | "riconciliati";
export type RegisterPage<T> = { items: T[]; total: number; page: number; page_size: number };
export type RegisterSummary = {
  id: string; source_system: string; source_key: string; document_number: string;
  tax_code: string | null; issued_on: string | null; version: number; created_at: string;
  reconciled_into_id: string | null;
  notification_state: NotificationState; position_count: number; unlinked_count: number;
  conflicting_count: number; recovery_review_count: number; anomalies: string[];
};
export type RegisterNotification = { state: NotificationState; notified_on: string | null; evidence_id: string | null };
export type RegisterRecovery = {
  state: RecoveryState; case_reference: string | null; verified_on: string | null;
  evidence_reference: string | null; amount: string | null;
};
export type RegisterCandidate = {
  id: string; codice_cnc: string; anno_tributario: number; codice_fiscale_raw: string | null;
  nominativo_raw: string | null; subject_id: string | null; importo_totale_euro: string | null;
};
export type RegisterPosition = {
  id: string; source_namespace: string; source_reference: string; tax_year: number;
  avviso_id: string | null; avviso: RegisterCandidate | null; recovery: RegisterRecovery | null;
};
export type RegisterDetail = RegisterSummary & {
  original_json: Record<string, unknown>; notification: RegisterNotification | null;
  positions: RegisterPosition[];
};
export type CandidateResult = RegisterCandidate & { already_linked: boolean };
export type RegisterEvidence = {
  id: string; source_system: string; source_key: string; attempt_id: string | null;
  kind: string; occurred_on: string | null; reference: string; original_json: Record<string, unknown>;
};
export type RegisterAttempt = {
  id: string; source_system: string; source_key: string; channel: string;
  tracking_code: string | null; sent_at: string | null; registered_mail_id: string | null;
};
export type RegisterAudit = {
  id: string; version: number; actor_id: number; action: string; reason: string;
  before_json: Record<string, unknown>; after_json: Record<string, unknown>; created_at: string;
};
export type RegisterMutationResult = { document_id: string; resource_id: string; version: number };
export type RegisterEligibility = {
  document_id: string; version: number; checked_at: string; eligible: boolean;
  reasons: string[]; authorizes_dispatch: false;
  positions: { position_id: string; avviso_id: string | null; tax_year: number; eligible: boolean; reasons: string[] }[];
};
