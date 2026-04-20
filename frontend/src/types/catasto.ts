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
  id: UUID;
  national_code: string | null;
  cod_comune_istat: number;
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
  national_code: string | null;
  cod_comune_istat: number;
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
  cod_provincia: number | null;
  cod_comune_istat: number | null;
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

