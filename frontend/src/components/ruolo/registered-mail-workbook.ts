import type { RegisteredMailCampaignItem } from "@/types/registered-mail-campaign";

export type OperatorWorkbookRow = {
  row: number;
  ref2022: string;
  ref2023: string;
  name: string;
  address: string;
  city: string;
  taxCode: string;
  cumulativeNumber: string;
};

export type OperatorWorkbook = { sha256: string; name: string; rows: OperatorWorkbookRow[] };

function cell(value: unknown): string {
  return value == null ? "" : String(value).trim();
}

export function normalizeIdentity(value: unknown): string {
  return cell(value).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase().replace(/[^A-Z0-9]/g, "");
}

function hasReference(value: string): boolean {
  return value !== "" && !/^[-\u2013\u2014]+$/.test(value);
}

export function parseOperatorRows(cells: unknown[][]): OperatorWorkbookRow[] {
  return cells.flatMap((values, index) => {
    if (index === 0 || !/^202[23]$/.test(cell(values[56])) || !cell(values[21])) return [];
    return [{
      row: index + 1,
      ref2022: cell(values[2]),
      ref2023: cell(values[3]),
      name: cell(values[13]),
      address: cell(values[14]),
      city: cell(values[16]),
      taxCode: cell(values[20]),
      cumulativeNumber: cell(values[21]),
    }];
  });
}

export function workbookEvidence(item: RegisteredMailCampaignItem, rows: OperatorWorkbookRow[]): OperatorWorkbookRow | null {
  const notices = item.candidate_notices;
  if (notices.length !== 2 || notices[0].tax_year === notices[1].tax_year) return null;
  const taxCodes = new Set(notices.map((notice) => normalizeIdentity(notice.codice_fiscale)));
  if (taxCodes.size !== 1 || taxCodes.has("")) return null;
  const taxCode = [...taxCodes][0];
  const matches = rows.filter((row) => normalizeIdentity(row.taxCode) === taxCode && hasReference(row.ref2022) && hasReference(row.ref2023));
  return matches.length === 1 ? matches[0] : null;
}
