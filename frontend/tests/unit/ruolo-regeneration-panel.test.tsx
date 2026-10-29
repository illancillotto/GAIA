import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { RegenerationPanel } from "@/components/ruolo/solleciti/regeneration-panel";

const api = vi.hoisted(() => ({ listRegenerationTargets: vi.fn(), regenerateReminderItem: vi.fn() }));
vi.mock("@/lib/ruolo-regeneration-api", () => api);

const targets = {
  excluded_drafts: 2,
  items: [
    { item_id: "item-1", batch_id: "batch-1", display_name: "Mario Rossi", codice_fiscale: "RSSMRA80A01H501Z" },
    { item_id: "item-2", batch_id: "batch-1", display_name: null, codice_fiscale: "BNCLGU80A01H501Y" },
    { item_id: "item-3", batch_id: "batch-2", display_name: "Anna Verdi", codice_fiscale: "VRDNNA80A41H501X" },
  ],
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((yes) => { resolve = yes; });
  return { promise, resolve };
}

beforeEach(() => {
  vi.resetAllMocks();
  api.listRegenerationTargets.mockResolvedValue(targets);
});
afterEach(cleanup);

function openOptions() {
  fireEvent.click(screen.getByRole("button", { name: "Mostra opzioni" }));
}

it("regenerates every sollecito in order and reports skipped and failed ones", async () => {
  const finished = vi.fn();
  api.regenerateReminderItem
    .mockResolvedValueOnce({ item_id: "item-1", outcome: "regenerated", detail: null })
    .mockResolvedValueOnce({ item_id: "item-2", outcome: "skipped", detail: "Posizione cambiata o saldata" })
    .mockRejectedValueOnce(new Error("Chromium non trovato"));
  render(<RegenerationPanel token="t" batchId="batch-1" onFinished={finished} />);
  openOptions();
  fireEvent.click(screen.getByRole("radio", { name: /Ricalcola dati e regole/ }));
  fireEvent.click(screen.getByRole("radio", { name: "Solo il lotto selezionato" }));
  fireEvent.click(screen.getByRole("radio", { name: "Tutti i lotti" }));
  fireEvent.click(screen.getByRole("button", { name: "Rigenera PDF" }));
  expect(await screen.findByText("Completata: 3 di 3 · rigenerati 1 · saltati 1 · errori 1")).toBeVisible();
  expect(api.listRegenerationTargets).toHaveBeenCalledWith("t", null);
  expect(api.regenerateReminderItem.mock.calls.map((call) => call.slice(1))).toEqual([["item-1", "recompute"], ["item-2", "recompute"], ["item-3", "recompute"]]);
  expect(screen.getByText("Bozze 2022/2023 escluse: 2.")).toBeVisible();
  const report = screen.getByRole("status");
  expect(report).toHaveTextContent("BNCLGU80A01H501Y - saltato: Posizione cambiata o saldata");
  expect(report).toHaveTextContent("Anna Verdi - errore: Chromium non trovato");
  expect(finished).toHaveBeenCalledTimes(1);
});

it("limits the run to the selected batch and needs one", async () => {
  api.listRegenerationTargets.mockResolvedValue({ items: [], excluded_drafts: 0 });
  const { rerender } = render(<RegenerationPanel token="t" batchId={null} onFinished={vi.fn()} />);
  openOptions();
  fireEvent.click(screen.getByRole("radio", { name: "Solo il lotto selezionato" }));
  expect(screen.getByRole("button", { name: "Rigenera PDF" })).toBeDisabled();
  expect(screen.getByText("Seleziona prima un lotto.")).toBeVisible();
  rerender(<RegenerationPanel token="t" batchId="batch-2" onFinished={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Rigenera PDF" }));
  expect(await screen.findByText("Completata: 0 di 0 · rigenerati 0 · saltati 0 · errori 0")).toBeVisible();
  expect(api.listRegenerationTargets).toHaveBeenCalledWith("t", "batch-2");
  expect(api.regenerateReminderItem).not.toHaveBeenCalled();
  expect(screen.queryByText(/Bozze 2022\/2023 escluse/)).toBeNull();
});

it("stops between two PDFs and locks the choices while running", async () => {
  const first = deferred<unknown>();
  api.regenerateReminderItem.mockReturnValueOnce(first.promise);
  render(<RegenerationPanel token="t" batchId={null} onFinished={vi.fn()} />);
  openOptions();
  fireEvent.click(screen.getByRole("button", { name: "Rigenera PDF" }));
  expect(await screen.findByText("In corso: 0 di 3 · rigenerati 0 · saltati 0 · errori 0")).toBeVisible();
  expect(screen.getByRole("radio", { name: "Tutti i lotti" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Ferma" }));
  await act(async () => first.resolve({ item_id: "item-1", outcome: "regenerated", detail: null }));
  expect(screen.getByText("Fermata: 1 di 3 · rigenerati 1 · saltati 0 · errori 0")).toBeVisible();
  expect(api.regenerateReminderItem).toHaveBeenCalledTimes(1);
  expect(screen.getByRole("button", { name: "Rigenera PDF" })).toBeEnabled();
});

it.each([[new Error("Accesso negato"), "Accesso negato"], ["offline", "Elenco dei solleciti non caricato"]])("reports a target list that cannot be read (%s)", async (failure, message) => {
  api.listRegenerationTargets.mockRejectedValue(failure);
  render(<RegenerationPanel token="t" batchId={null} onFinished={vi.fn()} />);
  openOptions();
  fireEvent.click(screen.getByRole("button", { name: "Rigenera PDF" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(message);
});

it("reports a failed request without an error message", async () => {
  api.listRegenerationTargets.mockResolvedValue({ items: [targets.items[0]], excluded_drafts: 0 });
  api.regenerateReminderItem.mockRejectedValue("offline").mockResolvedValueOnce({ item_id: "item-1", outcome: "failed", detail: null });
  render(<RegenerationPanel token="t" batchId={null} onFinished={vi.fn()} />);
  openOptions();
  fireEvent.click(screen.getByRole("button", { name: "Rigenera PDF" }));
  expect(await screen.findByText(/Completata: 1 di 1/)).toBeVisible();
  expect(screen.getByRole("status")).toHaveTextContent("Mario Rossi - errore:");
  cleanup();
  render(<RegenerationPanel token="t" batchId={null} onFinished={vi.fn()} />);
  openOptions();
  fireEvent.click(screen.getByRole("button", { name: "Rigenera PDF" }));
  expect(await screen.findByText(/Completata: 1 di 1/)).toBeVisible();
  expect(screen.getByRole("status")).toHaveTextContent("Mario Rossi - errore: Rigenerazione non riuscita");
});

it("starts closed and keeps the report visible after hiding the options", async () => {
  api.regenerateReminderItem.mockResolvedValue({ item_id: "item-1", outcome: "regenerated", detail: null });
  render(<RegenerationPanel token="t" batchId={null} onFinished={vi.fn()} />);
  expect(screen.queryByRole("radio", { name: "Tutti i lotti" })).toBeNull();
  expect(screen.getByRole("button", { name: "Mostra opzioni" })).toHaveAttribute("aria-expanded", "false");
  openOptions();
  fireEvent.click(screen.getByRole("button", { name: "Rigenera PDF" }));
  expect(await screen.findByText(/Completata: 3 di 3/)).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Nascondi opzioni" }));
  expect(screen.queryByRole("radio", { name: "Tutti i lotti" })).toBeNull();
  expect(screen.getByText(/Completata: 3 di 3/)).toBeVisible();
});
