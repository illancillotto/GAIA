export type OrgReferenceRow = {
  label: string;
  note?: string;
  expectedHeadcount: number;
};

export type OrgReferenceSheet = {
  title: string;
  sourceLabel: string;
  totalHeadcount: number;
  rows: OrgReferenceRow[];
};

// Estratto dal file del consorzio:
// /home/cbo/Downloads/Organigramma_2026_R2.xlsx
// Al momento contiene solo il blocco "Area Amministrativa - Settore Catasto (75)".
export const ORG_REFERENCE_BY_UNIT: Record<string, OrgReferenceSheet> = {
  "area catasto": {
    title: "Area Amministrativa - Settore Catasto",
    sourceLabel: "Organigramma consorzio 2026 · R2",
    totalHeadcount: 75,
    rows: [
      { label: "Catasto", expectedHeadcount: 7 },
      { label: "Tributi, Ruoli, Scarichi", expectedHeadcount: 2 },
      { label: "Riordino Fondiario", expectedHeadcount: 2 },
      { label: "SIT - Gis, App. Irrighiamo Insieme, Drone, Telerilevamento", expectedHeadcount: 5 },
      { label: "Patrimonio", expectedHeadcount: 2 },
      { label: "Contatori", note: "Manutenzione, Gestione, Misure", expectedHeadcount: 24 },
      { label: "Magazzino", expectedHeadcount: 4 },
      { label: "Officina", note: "145 automezzi", expectedHeadcount: 6 },
      { label: "Bonifica", expectedHeadcount: 20 },
      { label: "Progettazione", expectedHeadcount: 3 },
    ],
  },
};

export function getOrgReference(unitName: string | null | undefined): OrgReferenceSheet | null {
  if (!unitName) return null;
  return ORG_REFERENCE_BY_UNIT[unitName.trim().toLowerCase()] ?? null;
}
