export type RuoloPayerReason = "decesso" | "vendita" | "ufficio";

export type RuoloPayerAssignment = {
  id: string;
  reason: RuoloPayerReason;
  reason_label: string;
  notes: string | null;
  payer_subject_id: string;
  payer_tax_code: string | null;
  payer_name: string | null;
  payer_address: string | null;
  created_at: string;
  voided_at: string | null;
};

export type RuoloPayerAssignments = {
  active: RuoloPayerAssignment | null;
  history: RuoloPayerAssignment[];
};

export type RuoloPayerAssignmentRequest = {
  payer_tax_code: string;
  reason: RuoloPayerReason;
  notes: string | null;
};
