import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { RuoloCoIntestatari } from "@/components/ruolo/co-intestatari";
import type { AnagraficaSubjectListItem } from "@/types/api";

const mocks = vi.hoisted(() => ({ search: vi.fn(), token: vi.fn() }));
vi.mock("@/lib/api", () => ({ searchUtenzeSubjects: mocks.search }));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));

function subject(overrides: Partial<AnagraficaSubjectListItem> = {}): AnagraficaSubjectListItem {
  return {
    id: "subject-1", subject_type: "person", status: "active", source_system: "manual",
    source_external_id: null, source_name_raw: "Porru Ernestina", display_name: "Porru Ernestina",
    codice_fiscale: "PRRRST00A00G113A", partita_iva: null, nas_folder_path: null,
    nas_folder_letter: null, requires_review: false, imported_at: null, document_count: 0,
    created_at: "2026-10-06", updated_at: "2026-10-06", ...overrides,
  };
}

beforeEach(() => {
  vi.resetAllMocks();
  mocks.token.mockReturnValue("token");
});

test.each([null, "", " ; , \n "])("hides empty co-intestatari: %s", (names) => {
  const { container } = render(<RuoloCoIntestatari names={names} />);
  expect(container).toBeEmptyDOMElement();
});

test("opens the unique exact subject in the existing modal and closes it", async () => {
  let resolveSearch!: (value: { items: AnagraficaSubjectListItem[]; total: number }) => void;
  mocks.search.mockReturnValue(new Promise((resolve) => { resolveSearch = resolve; }));
  render(<RuoloCoIntestatari names={" Porru   Ernestina; Rossi Mario, Porru   Ernestina\nVerdi Anna "} />);
  expect(screen.getAllByRole("button")).toHaveLength(3);
  fireEvent.click(screen.getByRole("button", { name: "Porru Ernestina" }));
  expect(screen.getByRole("status")).toHaveTextContent("Ricerca soggetto...");
  expect(screen.getByRole("button", { name: "Rossi Mario" })).toBeDisabled();
  expect(mocks.search).toHaveBeenCalledWith("token", "Porru   Ernestina", 20);
  resolveSearch({ items: [subject({ display_name: "PORRU ERNESTINA" })], total: 1 });
  expect(await screen.findByRole("dialog")).toBeInTheDocument();
  expect(screen.getByTitle("Dettaglio soggetto")).toHaveAttribute("src", "/utenze/subject-1?embedded=1");
  fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

test("lets the operator distinguish homonyms by tax identifiers", async () => {
  mocks.search.mockResolvedValue({ items: [
    subject(),
    subject({ id: "subject-2", codice_fiscale: null, partita_iva: "12345678901" }),
    subject({ id: "subject-3", codice_fiscale: null }),
  ], total: 3 });
  render(<RuoloCoIntestatari names="Porru Ernestina" />);
  fireEvent.click(screen.getByRole("button", { name: "Porru Ernestina" }));
  expect(await screen.findByText("Seleziona il soggetto corretto:")).toBeInTheDocument();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: /CF\/P.IVA non disponibile/ })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /12345678901/ }));
  expect(screen.getByTitle("Dettaglio soggetto")).toHaveAttribute("src", "/utenze/subject-2?embedded=1");
});

test("requires selection for partial names even with a single result", async () => {
  mocks.search.mockResolvedValue({ items: [subject({ display_name: "Porru Ernestina Maria" })], total: 1 });
  render(<RuoloCoIntestatari names="Porru Ernestina" />);
  fireEvent.click(screen.getByRole("button", { name: "Porru Ernestina" }));
  expect(await screen.findByText("Seleziona il soggetto corretto:")).toBeInTheDocument();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

test("reports missing subjects and allows another lookup", async () => {
  mocks.search.mockResolvedValueOnce({ items: [], total: 0 })
    .mockResolvedValueOnce({ items: [subject()], total: 1 });
  render(<RuoloCoIntestatari names="Porru Ernestina" />);
  fireEvent.click(screen.getByRole("button", { name: "Porru Ernestina" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Nessun soggetto GAIA trovato per Porru Ernestina.");
  fireEvent.click(screen.getByRole("button", { name: "Porru Ernestina" }));
  expect(await screen.findByRole("dialog")).toBeInTheDocument();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

test.each([
  [new Error("Ricerca non disponibile"), "Ricerca non disponibile"],
  ["failure", "Errore ricerca soggetto"],
])("reports lookup errors: %s", async (cause, message) => {
  mocks.search.mockRejectedValue(cause);
  render(<RuoloCoIntestatari names="Porru Ernestina" />);
  fireEvent.click(screen.getByRole("button", { name: "Porru Ernestina" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(message);
  await waitFor(() => expect(screen.getByRole("button", { name: "Porru Ernestina" })).toBeEnabled());
});

test("requires an authenticated session", () => {
  mocks.token.mockReturnValue(null);
  render(<RuoloCoIntestatari names="Porru Ernestina" />);
  fireEvent.click(screen.getByRole("button", { name: "Porru Ernestina" }));
  expect(screen.getByRole("alert")).toHaveTextContent("Sessione non disponibile");
  expect(mocks.search).not.toHaveBeenCalled();
});
