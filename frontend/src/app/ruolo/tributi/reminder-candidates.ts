import { listTributiReminderCandidates } from "@/lib/ruolo-api";
import type { RuoloTributiReminderCandidateResponse } from "@/types/ruolo";

const REMINDER_CANDIDATE_PAGE_SIZE = 80;

type CandidateFilters = Omit<
  NonNullable<Parameters<typeof listTributiReminderCandidates>[1]>,
  "page" | "page_size"
>;

export function reminderBatchTaxCodes(
  candidates: RuoloTributiReminderCandidateResponse[],
  selectedTaxCodes: string[],
): string[] {
  const allCandidatesSelected =
    candidates.length === selectedTaxCodes.length &&
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
