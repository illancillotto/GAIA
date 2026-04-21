export type UUID = string;

export type CatImportBatchStatus = "processing" | "completed" | "failed" | "replaced";

export type CatImportBatch = {
  id: UUID;
  filename: string;
  tipo: string;
  anno_campagna: number | null;
  hash_file: string | null;
  righe_totali: number;
  righe_importate: number;
  righe_anomalie: number;
  status: CatImportBatchStatus | string;
  report_json: Record<string, unknown> | null;
  errore: string | null;
  created_at: string;
  completed_at: string | null;
  created_by: number | null;
};

export type CatImportStartResponse = {
  batch_id: UUID;
  status: string;
};

export type CatImportSummary = {
  tipo: string | null;
  totale_batch: number;
  processing_batch: number;
  completed_batch: number;
  failed_batch: number;
  replaced_batch: number;
  ultimo_completed_at: string | null;
};

export type CatAnomaliaSeverita = "error" | "warning" | "info";
export type CatAnomaliaStatus = "aperta" | "chiusa" | "ignora" | string;

export type CatAnomalia = {
  id: UUID;
  particella_id: UUID | null;
  utenza_id: UUID | null;
  anno_campagna: number | null;
  tipo: string;
  severita: CatAnomaliaSeverita | string;
  descrizione: string | null;
  dati_json: Record<string, unknown> | null;
  status: CatAnomaliaStatus;
  note_operatore: string | null;
  assigned_to: number | null;
  segnalazione_id: UUID | null;
  created_at: string;
  updated_at: string;
};

export type CatAnomaliaListResponse = {
  items: CatAnomalia[];
  total: number;
  page: number;
  page_size: number;
};

export type CatParticella = {
  comune_id: UUID | null;
  id: UUID;
  national_code: string | null;
  cod_comune_capacitas: number;
  codice_catastale: string | null;
  nome_comune: string | null;
  sezione_catastale: string | null;
  foglio: string;
  particella: string;
  subalterno: string | null;
  cfm: string | null;
  superficie_mq: string | null;
  num_distretto: string | null;
  nome_distretto: string | null;
  source_type: string;
  valid_from: string;
  valid_to: string | null;
  is_current: boolean;
  suppressed: boolean;
  created_at: string;
  updated_at: string;
};

export type CatParticellaDetail = CatParticella & {
  fuori_distretto: boolean;
};

export type CatParticellaHistory = {
  history_id: UUID;
  particella_id: UUID;
  comune_id: UUID | null;
  national_code: string | null;
  cod_comune_capacitas: number;
  codice_catastale: string | null;
  foglio: string;
  particella: string;
  subalterno: string | null;
  superficie_mq: string | null;
  num_distretto: string | null;
  valid_from: string;
  valid_to: string;
  changed_at: string;
  change_reason: string | null;
};

export type CatDistretto = {
  id: UUID;
  num_distretto: string;
  nome_distretto: string | null;
  decreto_istitutivo: string | null;
  data_decreto: string | null;
  attivo: boolean;
  note: string | null;
  created_at: string;
  updated_at: string;
};

export type CatDistrettoKpi = {
  distretto_id: UUID;
  anno: number | null;
  num_distretto: string;
  totale_particelle: number;
  totale_utenze: number;
  totale_anomalie: number;
  anomalie_error: number;
  importo_totale_0648: string;
  importo_totale_0985: string;
  superficie_irrigabile_mq: string;
};

export type CatSchemaContributo = {
  id: UUID;
  codice: string;
  descrizione: string | null;
  tipo_calcolo: string;
  attivo: boolean;
};

export type CatUtenzaIrrigua = {
  id: UUID;
  import_batch_id: UUID;
  anno_campagna: number;
  cco: string | null;
  comune_id: UUID | null;
  cod_provincia: number | null;
  cod_comune_capacitas: number | null;
  cod_frazione: number | null;
  num_distretto: number | null;
  nome_distretto_loc: string | null;
  nome_comune: string | null;
  sezione_catastale: string | null;
  foglio: string | null;
  particella: string | null;
  subalterno: string | null;
  particella_id: UUID | null;
  sup_catastale_mq: string | null;
  sup_irrigabile_mq: string | null;
  ind_spese_fisse: string | null;
  imponibile_sf: string | null;
  esente_0648: boolean;
  aliquota_0648: string | null;
  importo_0648: string | null;
  aliquota_0985: string | null;
  importo_0985: string | null;
  denominazione: string | null;
  codice_fiscale: string | null;
  codice_fiscale_raw: string | null;
  anomalia_superficie: boolean;
  anomalia_cf_invalido: boolean;
  anomalia_cf_mancante: boolean;
  anomalia_comune_invalido: boolean;
  anomalia_particella_assente: boolean;
  anomalia_imponibile: boolean;
  anomalia_importi: boolean;
  created_at: string;
};

export type GeoJSONFeature = {
  type: "Feature";
  geometry: unknown;
  properties: Record<string, unknown>;
};

export type CatIntestatario = {
  id: UUID;
  codice_fiscale: string;
  denominazione: string | null;
  tipo: string | null;
  cognome: string | null;
  nome: string | null;
  data_nascita: string | null;
  luogo_nascita: string | null;
  ragione_sociale: string | null;
  source: string | null;
  last_verified_at: string | null;
  deceduto: boolean | null;
};

export type CatAnagraficaUtenzaSummary = {
  id: UUID;
  cco: string | null;
  anno_campagna: number | null;
  stato: string | null;
  num_distretto: number | null;
  nome_distretto: string | null;
  sup_irrigabile_mq: string | null;
  denominazione: string | null;
  codice_fiscale: string | null;
  ha_anomalie: boolean | null;
};

export type CatAnagraficaMatch = {
  particella_id: UUID;
  comune_id: UUID | null;
  comune: string | null;
  cod_comune_capacitas: number | null;
  codice_catastale: string | null;
  foglio: string;
  particella: string;
  subalterno: string | null;
  num_distretto: string | null;
  nome_distretto: string | null;
  superficie_mq: string | null;
  utenza_latest: CatAnagraficaUtenzaSummary | null;
  intestatari: CatIntestatario[];
  anomalie_count: number;
  anomalie_top: { tipo: string; count: number }[];
};

export type CatAnagraficaSearchResponse = {
  matches: CatAnagraficaMatch[];
};

export type CatAnagraficaBulkRowInput = {
  row_index: number;
  comune?: string | null;
  foglio?: string | null;
  particella?: string | null;
};

export type CatAnagraficaBulkSearchRequest = {
  rows: CatAnagraficaBulkRowInput[];
};

export type CatAnagraficaBulkRowResult = {
  row_index: number;
  comune_input: string | null;
  foglio_input: string | null;
  particella_input: string | null;
  esito: "FOUND" | "NOT_FOUND" | "MULTIPLE_MATCHES" | "INVALID_ROW" | "ERROR" | string;
  message: string;
  particella_id: UUID | null;
  match: CatAnagraficaMatch | null;
  matches_count: number | null;
};

export type CatAnagraficaBulkSearchResponse = {
  results: CatAnagraficaBulkRowResult[];
};
