import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { UtenzeSubjectDocumentsRefresh } from "@/components/utenze/utenze-subject-documents-refresh";
import type { UtenzeSubjectDetail } from "@/types/api";

const api = vi.hoisted(() => ({
  getUtenzeSubject: vi.fn(),
  importUtenzeSubjectFromNas: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getUtenzeSubject: api.getUtenzeSubject,
  importUtenzeSubjectFromNas: api.importUtenzeSubjectFromNas,
}));

const subjectDetail = {
  id: "subject-1",
} as unknown as UtenzeSubjectDetail;

describe("UtenzeSubjectsSection document refresh", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getUtenzeSubject.mockResolvedValue(subjectDetail);
    api.importUtenzeSubjectFromNas.mockResolvedValue({
      subject_id: "subject-1",
      matched_folder_path: "/archive/R/Rossi_Mario",
      matched_folder_name: "Rossi_Mario",
      warning_count: 0,
      created_documents: 2,
      updated_documents: 1,
      imported_at: "2026-09-22T18:06:00Z",
    });
  });

  test("updates one subject and reloads its detail", async () => {
    const onRefreshed = vi.fn();
    render(<UtenzeSubjectDocumentsRefresh token="token" subjectId="subject-1" onRefreshed={onRefreshed} />);

    fireEvent.click(screen.getByRole("button", { name: "Aggiorna documenti" }));
    expect(screen.getByRole("button", { name: "Aggiornamento..." })).toBeDisabled();

    await waitFor(() => {
      expect(api.importUtenzeSubjectFromNas).toHaveBeenCalledWith("token", "subject-1");
      expect(api.getUtenzeSubject).toHaveBeenCalledWith("token", "subject-1");
      expect(onRefreshed).toHaveBeenCalledWith(subjectDetail);
    });
    expect(await screen.findByText("Documenti aggiornati: 2 nuovi, 1 gia presenti aggiornati.")).toBeInTheDocument();
  });

  test.each([
    [new Error("NAS non raggiungibile"), "NAS non raggiungibile"],
    ["invalid error", "Errore aggiornamento documenti dal NAS"],
  ])("shows refresh errors without reloading the detail", async (refreshError, expectedMessage) => {
    api.importUtenzeSubjectFromNas.mockRejectedValue(refreshError);

    render(<UtenzeSubjectDocumentsRefresh token="token" subjectId="subject-1" onRefreshed={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna documenti" }));

    expect(await screen.findByText(expectedMessage)).toBeInTheDocument();
    expect(api.getUtenzeSubject).not.toHaveBeenCalled();
  });
});
