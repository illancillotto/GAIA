export type ParcelHistoryRow = {
  id: string; comune: string; comune_codice: string; foglio: string; particella: string;
  subalterno: string; first_year: number; last_year: number; years_count: number;
};
export type ParcelHistoryPage = { items: ParcelHistoryRow[]; total: number; page: number; page_size: number };
export type ParcelTaxEntry = {
  id: string; year: number; notice_id: string; notice_number: string;
  name: string | null; tax_code: string | null; partita_tax_code: string | null; co_holders: string | null;
  maintenance: number | null; irrigation: number | null; institutional: number | null; total: number | null;
  area_ha: number | null; irrigated_ha: number | null; crop: string | null; district: string | null;
  catasto_id: string | null;
};
export type ParcelOwner = { name: string | null; tax_code: string | null; right: string | null; share: string | null };
export type ParcelHistoryDocument = {
  id: string; filename: string; observed_at: string | null; recorded_at: string; type: string;
  extraction_status: string; owners: ParcelOwner[]; ambiguous: boolean;
  suppressed: boolean; suppressed_at: string | null;
};
export type ParcelHistory = {
  id: string; reference: { comune_nome: string; comune_codice: string; sezione: string | null;
    foglio: string; particella: string; subalterno: string; catasto: string | null };
  identity_incomplete: boolean; first_year: number; last_year: number; taxes: ParcelTaxEntry[];
  cadastre: { documents: ParcelHistoryDocument[]; events: (ParcelOwner & { id: string; from_date: string | null;
    act_date: string | null; act: string | null; document_id: string })[];
    completeness: string; cessation: string };
};
