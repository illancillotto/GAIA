import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { YearNoticesPanel } from "@/components/ruolo/solleciti/year-notices-panel";

const years = vi.hoisted(() => ({ getYearStatus: vi.fn(), generateYearNotices: vi.fn() }));
vi.mock("@/lib/ruolo-year-notices-api", () => years);
const regeneration = vi.hoisted(() => ({ regenerateReminderItem: vi.fn(), listRegenerationTargets: vi.fn() }));
vi.mock("@/lib/ruolo-regeneration-api", () => regeneration);

const missing = (index: number) => ({ label: `Utenza ${index}`, avviso_ids: [`a${index}`] });
const status = {
  year: 2021, total: 9, ready: 2,
  failed: [{ item_id: "item-1", label: "Sotgiu" }],
  missing: [1, 2, 3, 4, 5, 6].map(missing),
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((yes) => { resolve = yes; });
  return { promise, resolve };
}

beforeEach(() => {
  vi.resetAllMocks();
  years.getYearStatus.mockResolvedValue(status);
});
afterEach(cleanup);

it("retries the failed PDF, makes the missing ones a few at a time and lists what is still missing", async () => {
  const finished = vi.fn();
  regeneration.regenerateReminderItem.mockResolvedValue({ item_id: "item-1", outcome: "regenerated", detail: null });
  years.generateYearNotices
    .mockResolvedValueOnce({ batch_id: "b1", generated: 5, problems: [] })
    .mockResolvedValueOnce({ batch_id: "b2", generated: 0, problems: [{ label: "Utenza 6", detail: "Cartella archivio NAS mancante per l'utenza" }] });
  render(<YearNoticesPanel token="t" onFinished={finished} />);
  expect(screen.getByText("Conteggio degli avvisi del 2021...")).toBeVisible();
  expect(await screen.findByText("PDF pronti")).toHaveTextContent("2");
  expect(screen.getByText(/9 avvisi del 2021/)).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Crea i 7 PDF mancanti" }));
  expect(await screen.findByText("Finito: 7 di 7.")).toBeVisible();
  expect(regeneration.regenerateReminderItem).toHaveBeenCalledWith("t", "item-1", "template");
  expect(years.generateYearNotices.mock.calls).toEqual([["t", 2021, ["a1", "a2", "a3", "a4", "a5"]], ["t", 2021, ["a6"]]]);
  expect(screen.getByText("Questi avvisi non hanno il PDF (1):")).toBeVisible();
  expect(screen.getByText(/Cartella archivio NAS mancante/)).toBeVisible();
  expect(finished).toHaveBeenCalledTimes(1);
  await waitFor(() => expect(years.getYearStatus).toHaveBeenCalledTimes(2));
});

it("explains requests that fail and stops between two steps", async () => {
  const first = deferred<unknown>();
  years.getYearStatus.mockResolvedValue({ ...status, missing: [missing(1)], failed: [{ item_id: "item-1", label: "Sotgiu" }, { item_id: "item-2", label: "Rossi" }] });
  regeneration.regenerateReminderItem.mockReturnValueOnce(first.promise);
  render(<YearNoticesPanel token="t" onFinished={vi.fn()} />);
  fireEvent.click(await screen.findByRole("button", { name: "Crea i 3 PDF mancanti" }));
  expect(screen.getByText("Sto creando i PDF: 0 di 3. Lascia la pagina aperta.")).toBeVisible();
  expect(screen.getByRole("combobox")).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Ferma" }));
  await act(async () => first.resolve({ item_id: "item-1", outcome: "failed", detail: null }));
  expect(await screen.findByText("Fermato: 1 di 3.")).toBeVisible();
  expect(screen.getByText(/Sotgiu/).closest("li")).toHaveTextContent("Sotgiu: PDF non creato");
  expect(years.generateYearNotices).not.toHaveBeenCalled();
});

it.each([[new Error("Servizio non raggiungibile"), "Servizio non raggiungibile"], ["offline", "Richiesta non riuscita"]])("reports a step that cannot reach GAIA (%s)", async (failure, message) => {
  years.getYearStatus.mockResolvedValue({ ...status, failed: [], missing: [missing(1), missing(2)] });
  years.generateYearNotices.mockRejectedValue(failure);
  render(<YearNoticesPanel token="t" onFinished={vi.fn()} />);
  fireEvent.click(await screen.findByRole("button", { name: "Crea i 2 PDF mancanti" }));
  expect(await screen.findByText("Finito: 2 di 2.")).toBeVisible();
  expect(screen.getByText("Utenza 1, Utenza 2").closest("li")).toHaveTextContent(message);
});

it("says when the year is complete, offers a single PDF and changes year", async () => {
  years.getYearStatus.mockResolvedValueOnce({ ...status, failed: [], missing: [] }).mockResolvedValueOnce({ ...status, year: 2022, failed: [], missing: [missing(1)] });
  render(<YearNoticesPanel token="t" onFinished={vi.fn()} />);
  expect(await screen.findByText("Tutti i PDF del 2021 sono pronti.")).toBeVisible();
  expect(screen.queryByRole("button", { name: /Crea/ })).toBeNull();
  fireEvent.change(screen.getByRole("combobox"), { target: { value: "2022" } });
  expect(await screen.findByRole("button", { name: "Crea il PDF mancante" })).toBeVisible();
  expect(years.getYearStatus).toHaveBeenLastCalledWith("t", 2022);
  expect(screen.getByRole("option", { name: String(new Date().getFullYear()) })).toBeInTheDocument();
});

it("shows why the count failed and ignores answers for a year no longer shown", async () => {
  const late = deferred<typeof status>();
  years.getYearStatus.mockReturnValueOnce(late.promise).mockRejectedValueOnce(new Error("Accesso negato"));
  render(<YearNoticesPanel token="t" onFinished={vi.fn()} />);
  fireEvent.change(screen.getByRole("combobox"), { target: { value: "2022" } });
  expect(await screen.findByRole("alert")).toHaveTextContent("Accesso negato");
  await act(async () => late.resolve(status));
  expect(screen.queryByText("PDF pronti")).toBeNull();
});

it("ignores a failed count for a year no longer shown", async () => {
  let reject!: (reason: unknown) => void;
  years.getYearStatus.mockReturnValueOnce(new Promise((_, no) => { reject = no; })).mockResolvedValueOnce({ ...status, year: 2022 });
  render(<YearNoticesPanel token="t" onFinished={vi.fn()} />);
  fireEvent.change(screen.getByRole("combobox"), { target: { value: "2022" } });
  expect(await screen.findByText(/9 avvisi del 2022/)).toBeVisible();
  await act(async () => reject(new Error("tardi")));
  expect(screen.queryByRole("alert")).toBeNull();
});
