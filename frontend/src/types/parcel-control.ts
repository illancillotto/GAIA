export type ControlView = "all" | "missing" | "cf" | "cases" | "closed" | "visure" | "recovered" | "proposals";
export type ControlReference = {
  comune_nome: string; comune_codice: string; foglio: string; particella: string;
  subalterno: string; sezione: string | null; catasto: string | null;
};
export type ControlOccurrence = {
  row_id: string; year: number; avviso_id: string; codice_cnc: string; subject_id: string | null;
  name: string | null; tax_code: { original: string | null; normalized: string; anomaly: string | null };
  cat_particella_id: string | null; catasto_status: string | null;
};
export type ControlRow = {
  id: string; label: string; reference: ControlReference; years: Record<string, string>;
  first_year: number | null; last_year: number | null; current_presence: string;
  cf_anomaly: boolean; identity_incomplete: boolean; territorial_status: string;
  occurrences: ControlOccurrence[]; case_id: string | null; case_status: string | null;
};
export type ControlProposal = {
  id: string; case_id?: string; status: string; label: string; year: number; kind: string;
  verified_tax_code: string; eligibility_rule: string; residual_doubts: string;
};
export type ControlPage = {
  items: ControlRow[]; total: number; current_year: number;
  coverage: Record<string, { source: string; certified_at: string }>; refreshed_at: string | null;
  notices?: ControlNotice[];
  sources_changed?: boolean;
};
export type ControlNotice = { id: string; year: number; codice_cnc: string; name: string | null;
  tax_code: { original: string | null; anomaly: string }; subject_id: string | null };
export type ControlEvidence = {
  id: string; kind: string; source?: string; reference?: string; result?: string;
  request_id?: string; scope?: string; version?: string; years?: number[];
};
export type ControlMatch = {
  id: string; status: string; name: string; tax_code: string; subject_kind: string;
  right: string; share: string; period: string;
};
export type ControlCase = {
  id: string; parcel_id: string | null; status: string; version: number; responsible_id: number;
  current: ControlRow; original: { occurrences: ControlOccurrence[]; notice?: ControlNotice }; evidence: ControlEvidence[];
  matches: ControlMatch[]; parcels: { id: string; reference: ControlReference; status: string }[];
  visure: { id: string; status: string; error: string | null; search_mode: string;
    batch_id: string; extraction: { owners?: { denominazione?: string; codice_fiscale?: string; diritto?: string; quota?: string }[] } | null }[];
  proposals: ControlProposal[];
  audit: { action: string; reason: string; actor_id: number; created_at: string }[];
};
