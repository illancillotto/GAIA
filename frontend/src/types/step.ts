export type StepJobMode = "sync" | "list_only" | "archive_import" | "relink";

export type StepLinkStatus = "linked" | "not_found" | "ambiguous" | "unrecognized";

export interface StepCredential {
  id: number;
  label: string;
  username: string;
  portal_url: string;
  active: boolean;
  min_delay_ms: number;
  last_used_at: string | null;
  last_error: string | null;
  consecutive_failures: number;
  created_at: string;
  updated_at: string;
}

export interface StepCredentialCreateInput {
  label: string;
  username: string;
  password: string;
  portal_url?: string;
  active?: boolean;
  min_delay_ms?: number;
}

export type StepCredentialUpdateInput = Partial<StepCredentialCreateInput>;

export interface StepSyncJobCreateInput {
  mode: StepJobMode;
  credential_id?: number | null;
  max_details?: number | null;
  force_details?: boolean;
  archive_name?: string | null;
}

export interface StepSyncJob {
  id: number;
  credential_id: number | null;
  requested_by_user_id: number | null;
  status: string;
  mode: string;
  payload_json: Record<string, unknown> | null;
  result_json: Record<string, unknown> | null;
  error_detail: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface StepOverview {
  contribuenti: number;
  documenti: number;
  tributi: number;
  pagamenti: number;
  pdf_scaricati: number;
  residuo_totale: string;
  ultimo_aggiornamento: string | null;
  links: Record<StepLinkStatus, number>;
  import_archives: string[];
}

export interface StepContribuenteRow {
  id: string;
  cod_ent: string;
  codice_fiscale: string;
  denominazione: string | null;
  numero_documenti: number | null;
  importo: string | null;
  pagato: string | null;
  residuo: string | null;
  stato_documenti: string | null;
  detail_synced_at: string | null;
}

export interface StepPage<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface StepRuoloLink {
  id: string;
  documento_id: string;
  reference_key: string;
  codice_cnc: string | null;
  anno_rif: number | null;
  status: StepLinkStatus;
  ruolo_avviso_id: string | null;
  candidate_avviso_ids: string[] | null;
  tributi_count: number;
  imp_carico: string | null;
  imp_carico_pagato: string | null;
  imp_discaricato: string | null;
}

export interface StepTributo {
  position: number;
  partita: string | null;
  cod_tributo: string | null;
  des_tributo: string | null;
  tipo_tributo: string | null;
  anno_rif: number | null;
  imp_carico: string | null;
  imp_carico_pagato: string | null;
  imp_discaricato: string | null;
  avviso_reference_raw: string | null;
  codice_cnc: string | null;
}

export interface StepDocumento {
  id: string;
  num_doc: string;
  prg_coo: string;
  section: string | null;
  des_doc: string | null;
  des_trib: string | null;
  anno_rif: string | null;
  data_notifica: string | null;
  tot_dovuto: string | null;
  imp_carico: string | null;
  tot_pagato: string | null;
  residuo: string | null;
  pdf_status: string;
  pdf_original_filename: string | null;
  tributi: StepTributo[];
  links: StepRuoloLink[];
}

export interface StepPagamento {
  num_quietanza: string | null;
  num_doc: string | null;
  data_pagamento: string | null;
  data_accredito: string | null;
  modalita: string | null;
  importo: string | null;
  importo_pagato: string | null;
  annullato: boolean;
  stato: string | null;
  riferimento: string | null;
}

export interface StepContribuenteDetail extends StepContribuenteRow {
  anagrafica_json: Record<string, unknown> | null;
  situazione_contabile_json: Record<string, unknown> | null;
  sections_json: Array<Record<string, unknown>> | null;
  document_reconciliation_json: Record<string, unknown> | null;
  last_seen_at: string;
  documenti: StepDocumento[];
  pagamenti: StepPagamento[];
}

export interface StepLinkAnomaly extends StepRuoloLink {
  contribuente_id: string;
  codice_fiscale: string;
  denominazione: string | null;
  num_doc: string;
}

export interface StepAvvisoLink {
  contribuente_id: string;
  codice_fiscale: string;
  denominazione: string | null;
  documento_id: string;
  num_doc: string;
  data_notifica: string | null;
  pdf_status: string;
  link: StepRuoloLink;
}
