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
  superficie_grafica_mq: string | null;
  num_distretto: string | null;
  nome_distretto: string | null;
  source_type: string;
  valid_from: string;
  valid_to: string | null;
  is_current: boolean;
  suppressed: boolean;
  created_at: string;
  updated_at: string;
  utenza_cf: string | null;
  utenza_denominazione: string | null;
};

export type CatParticellaDetail = CatParticella & {
  fuori_distretto: boolean;
};

export type CatConsorzioOccupancy = {
  id: UUID;
  unit_id: UUID;
  segment_id: UUID | null;
  utenza_id: UUID | null;
  cco: string | null;
  fra: string | null;
  ccs: string | null;
  pvc: string | null;
  com: string | null;
  source_type: string;
  relationship_type: string;
  valid_from: string | null;
  valid_to: string | null;
  is_current: boolean;
  confidence: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type CatCapacitasIntestatario = {
  id: UUID;
  subject_id: UUID | null;
  idxana: string | null;
  idxesa: string | null;
  codice_fiscale: string | null;
  denominazione: string | null;
  data_nascita: string | null;
  luogo_nascita: string | null;
  residenza: string | null;
  comune_residenza: string | null;
  cap: string | null;
  titoli: string | null;
  deceduto: boolean;
  collected_at: string;
  person: {
    subject_id: string;
    cognome: string;
    nome: string;
    codice_fiscale: string;
    data_nascita: string | null;
    comune_nascita: string | null;
    indirizzo: string | null;
    comune_residenza: string | null;
    cap: string | null;
    email: string | null;
    telefono: string | null;
    note: string | null;
    created_at: string;
    updated_at: string;
  } | null;
  person_snapshots: Array<{
    id: string;
    subject_id: string;
    source_system: string;
    source_ref: string | null;
    cognome: string;
    nome: string;
    codice_fiscale: string;
    data_nascita: string | null;
    comune_nascita: string | null;
    indirizzo: string | null;
    comune_residenza: string | null;
    cap: string | null;
    email: string | null;
    telefono: string | null;
    note: string | null;
    valid_from: string | null;
    collected_at: string;
  }>;
};

export type CatConsorzioUnit = {
  id: UUID;
  particella_id: UUID | null;
  comune_id: UUID | null;
  cod_comune_capacitas: number | null;
  source_comune_id: UUID | null;
  source_cod_comune_capacitas: number | null;
  source_codice_catastale: string | null;
  source_comune_label: string | null;
  comune_resolution_mode: string | null;
  sezione_catastale: string | null;
  foglio: string | null;
  particella: string | null;
  subalterno: string | null;
  descrizione: string | null;
  source_first_seen: string | null;
  source_last_seen: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  comune_label: string | null;
  source_comune_resolved_label: string | null;
  occupancies: CatConsorzioOccupancy[];
  intestatari_proprietari: CatCapacitasIntestatario[];
};

export type CatParticellaConsorzio = {
  particella_id: UUID;
  units: CatConsorzioUnit[];
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
  superficie_grafica_mq: string | null;
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
  superficie_grafica_mq: string | null;
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
  sezione?: string | null;
  foglio?: string | null;
  particella?: string | null;
  sub?: string | null;
  codice_fiscale?: string | null;
  partita_iva?: string | null;
};

export type CatAnagraficaBulkSearchRequest = {
  kind?: "CF_PIVA_PARTICELLE" | "COMUNE_FOGLIO_PARTICELLA_INTESTATARI";
  rows: CatAnagraficaBulkRowInput[];
};

export type CatAnagraficaBulkRowResult = {
  row_index: number;
  comune_input: string | null;
  sezione_input: string | null;
  foglio_input: string | null;
  particella_input: string | null;
  sub_input: string | null;
  codice_fiscale_input: string | null;
  partita_iva_input: string | null;
  esito: "FOUND" | "NOT_FOUND" | "MULTIPLE_MATCHES" | "INVALID_ROW" | "ERROR" | string;
  message: string;
  particella_id: UUID | null;
  match: CatAnagraficaMatch | null;
  matches: CatAnagraficaMatch[] | null;
  matches_count: number | null;
};

export type CatAnagraficaBulkSearchResponse = {
  results: CatAnagraficaBulkRowResult[];
};
