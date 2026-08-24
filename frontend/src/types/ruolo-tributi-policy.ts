export type RuoloTributiCalculationPolicyResponse = {
  id: string;
  name: string;
  year_from: number | null;
  year_to: number | null;
  bonario_due_date: string | null;
  surcharge_rate_percent: number;
  surcharge_from: string | null;
  euribor_6m_rate_percent: number;
  euribor_source_url: string | null;
  euribor_reference_period: string | null;
  euribor_fetched_at: string | null;
  interest_rate_percent: number;
  effective_interest_rate_percent: number;
  interest_from: string | null;
  interest_start_mode: "fixed_date" | "notification_date";
  bollettino_causale: string | null;
  bollettino_esercizio: string | null;
  is_active: boolean;
  notes: string | null;
  updated_by: number | null;
  created_at: string;
  updated_at: string;
};

export type RuoloTributiCalculationPolicyUpsertRequest = {
  name: string;
  year_from?: number | null;
  year_to?: number | null;
  bonario_due_date?: string | null;
  surcharge_rate_percent?: number;
  surcharge_from?: string | null;
  euribor_6m_rate_percent?: number;
  euribor_source_url?: string | null;
  euribor_reference_period?: string | null;
  euribor_fetched_at?: string | null;
  interest_rate_percent?: number;
  interest_from?: string | null;
  interest_start_mode?: "fixed_date" | "notification_date";
  bollettino_causale?: string | null;
  bollettino_esercizio?: string | null;
  is_active?: boolean;
  notes?: string | null;
};

export type RuoloTributiCalculationPolicyListResponse = {
  items: RuoloTributiCalculationPolicyResponse[];
};

export type RuoloTributiEuriborRateResponse = {
  year: number;
  rate_percent: number;
  reference_period: string;
  source_url: string;
  verification_url: string;
  fetched_at: string;
  observations_count: number;
};
