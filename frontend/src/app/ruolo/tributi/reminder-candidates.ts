import { listTributiReminderCandidates } from "@/lib/ruolo-api";
import type { RuoloTributiReminderCandidateResponse } from "@/types/ruolo";

const REMINDER_CANDIDATE_PAGE_SIZE = 80;

type CandidateFilters = Omit<
  NonNullable<Parameters<typeof listTributiReminderCandidates>[1]>,
  "page" | "page_size"
>;

function validReminderTaxCode(code: string): boolean {
  // Presentation parity with Catasto's CF format and numeric tax-code check digit.
  if (/^[A-Z]{6}[0-9]{2}[ABCDEHLMPRST][0-9]{2}[A-Z][0-9][A-Z0-9][0-9][A-Z]$/.test(code)) return true;
  if (!/^[0-9]{11}$/.test(code)) return false;
  const checksum = [...code.slice(0, 10)].reduce((sum, digit, index) => {
    const value = Number(digit) * (index % 2 === 0 ? 1 : 2);
    return sum + (value > 9 ? value - 9 : value);
  }, 0);
  return (10 - checksum % 10) % 10 === Number(code[10]);
}

export function reminderCandidateKey(candidate: RuoloTributiReminderCandidateResponse): string {
  const code = candidate.codice_fiscale.trim().toUpperCase();
  return validReminderTaxCode(code) ? code : `avviso:${candidate.avvisi.map((avviso) => avviso.id).sort().join(",")}`;
}

export function reminderNeedsArchive(candidate: RuoloTributiReminderCandidateResponse): boolean {
  return !candidate.has_nas_folder && !reminderCandidateKey(candidate).startsWith("avviso:");
}

export function reminderSelectionCount(
  candidates: RuoloTributiReminderCandidateResponse[],
  selectedTaxCodes: string[],
): number {
  return selectedTaxCodes.reduce(
    (count, code) => count + Math.max(1, candidates.filter((candidate) => candidate.codice_fiscale === code).length),
    0,
  );
}

export function reminderBatchTaxCodes(
  candidates: RuoloTributiReminderCandidateResponse[],
  selectedTaxCodes: string[],
): string[] {
  const allCandidatesSelected =
    new Set(candidates.map((candidate) => candidate.codice_fiscale)).size === selectedTaxCodes.length &&
    candidates.every((candidate) => selectedTaxCodes.includes(candidate.codice_fiscale));
  return allCandidatesSelected ? [] : selectedTaxCodes;
}

export async function listAllReminderCandidatesForYear(
  token: string,
  filters: CandidateFilters,
): Promise<RuoloTributiReminderCandidateResponse[]> {
  const firstPage = await listTributiReminderCandidates(token, {
    ...filters,
    page: 1,
    page_size: REMINDER_CANDIDATE_PAGE_SIZE,
  });
  const pageCount = Math.ceil(firstPage.total / REMINDER_CANDIDATE_PAGE_SIZE);
  if (pageCount <= 1) return firstPage.items;
  const remainingPages = await Promise.all(
    Array.from({ length: pageCount - 1 }, (_, index) =>
      listTributiReminderCandidates(token, {
        ...filters,
        page: index + 2,
        page_size: REMINDER_CANDIDATE_PAGE_SIZE,
      }),
    ),
  );
  return [firstPage, ...remainingPages].flatMap((response) => response.items);
}
