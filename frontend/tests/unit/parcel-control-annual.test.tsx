import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import RuoloParticellePage from "@/app/ruolo/particelle/page";

const mocks = vi.hoisted(() => ({ params: new URLSearchParams("vista=annuale"), push: vi.fn(), list: vi.fn(),
  token: "token" as string | null, suspend: false, pending: new Promise(() => undefined) }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: mocks.push }), useSearchParams: () => {
  if (mocks.suspend) throw mocks.pending;
  return mocks.params;
} }));
vi.mock("@/components/ruolo/module-page", () => ({ RuoloModulePage: ({ children }: { children: React.ReactNode }) => <div>{children}</div> }));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: () => mocks.token }));
vi.mock("@/lib/ruolo-api", () => ({ listRuoloParticelle: mocks.list }));

function annualRow(overrides: Record<string, unknown> = {}) {
  return { id: "source-1", partita_id: "partita-1", anno_tributario: 2025, foglio: "1", particella: "100",
    comune_nome: "ORISTANO", comune_codice: "G113", subalterno: "2", distretto: "10",
    sup_catastale_ha: 2, sup_irrigata_ha: 1, importo_manut: 10, importo_irrig: 2, importo_ist: 1,
    cat_particella_id: "current-1", catasto_parcel_id: "legacy-1", cat_particella_match_status: "matched",
    cat_particella_match_reason: "exact", cat_particella_match_confidence: "high",
    ade_scan_status: "completed", ade_scan_classification: "current", ...overrides };
}

beforeEach(() => {
  mocks.params = new URLSearchParams("vista=annuale"); mocks.push.mockReset(); mocks.list.mockReset();
  mocks.token = "token"; mocks.suspend = false; mocks.list.mockResolvedValue([]);
});

test("annual consultation preserves all fields and opens linked parcel details", async () => {
  mocks.params = new URLSearchParams("vista=annuale&anno=2025&comune=ORISTANO&foglio=1&particella=100&match_status=matched&match_reason=exact&unmatched_only=false&page=2");
  mocks.list.mockResolvedValue([annualRow()]);
  render(<RuoloParticellePage />);
  await screen.findByText("Fg.1 Part.100 Sub.2");
  expect(mocks.list).toHaveBeenCalledWith("token", expect.objectContaining({ anno: 2025, page: 2, unmatched_only: false }));
  fireEvent.click(screen.getByText("Fg.1 Part.100 Sub.2"));
  expect(screen.getByText("Dettaglio particella ruolo")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Apri Catasto" })).toHaveAttribute("href", "/catasto/particelle/current-1");
  fireEvent.click(screen.getByText("Chiudi"));
  expect(screen.queryByText("Dettaglio particella ruolo")).not.toBeInTheDocument();
});

test("unlinked and suppressed records preserve incomplete historical references", async () => {
  const missing = annualRow({ id: "source-2", comune_nome: null, comune_codice: null, foglio: "2", particella: "200",
    subalterno: null, distretto: null, sup_catastale_ha: null, sup_irrigata_ha: null,
    importo_manut: null, importo_irrig: null, importo_ist: null, cat_particella_id: null, catasto_parcel_id: null,
    cat_particella_match_status: null, cat_particella_match_reason: null, cat_particella_match_confidence: null,
    ade_scan_status: null, ade_scan_classification: null });
  mocks.list.mockResolvedValue([missing, annualRow({ id: "source-3", particella: "300", cat_particella_id: null, ade_scan_classification: "suppressed" })]);
  render(<RuoloParticellePage />);
  await screen.findByText("Non collegata");
  expect(screen.getByText("Soppressa AdE")).toBeInTheDocument();
  fireEvent.click(screen.getByText("Fg.2 Part.200"));
  expect(screen.getByText("Comune non disponibile · Fg.2 Part.200")).toBeInTheDocument();
  expect(screen.queryByText("Apri Catasto")).not.toBeInTheDocument();
});

test("annual filters and reset keep their original consultation mode", async () => {
  render(<RuoloParticellePage />);
  await screen.findByText("Nessuna particella ruolo");
  const values = [["Es. Mogoro", "Mogoro"], ["Es. 19", "19"], ["Es. 1101", "1101"], ["Es. 2025", "2025"],
    ["Es. unmatched", "unmatched"], ["Es. no_cat_particella_match", "no_cat_particella_match"]];
  for (const [placeholder, value] of values) fireEvent.change(screen.getByPlaceholderText(placeholder), { target: { value } });
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.submit(screen.getByText("Applica filtri").closest("form")!);
  expect(mocks.push).toHaveBeenCalledWith(expect.stringContaining("vista=annuale&comune=Mogoro"));
  expect(mocks.push).toHaveBeenCalledWith(expect.stringContaining("unmatched_only=false"));
  fireEvent.click(screen.getByText("Reset"));
  expect(mocks.push).toHaveBeenLastCalledWith("/ruolo/particelle?vista=annuale");
  fireEvent.submit(screen.getByText("Applica filtri").closest("form")!);
  expect(mocks.push).toHaveBeenLastCalledWith("/ruolo/particelle?vista=annuale&page=1");
});

test("annual loading errors preserve an actionable message", async () => {
  mocks.list.mockRejectedValue(new Error("Errore sorgente"));
  const component = render(<RuoloParticellePage />);
  expect(await screen.findByText("Errore sorgente")).toBeInTheDocument();
  mocks.list.mockRejectedValue("unavailable");
  mocks.params = new URLSearchParams("vista=annuale&page=2");
  component.rerender(<RuoloParticellePage />);
  expect(await screen.findByText("Errore caricamento particelle")).toBeInTheDocument();
});

test("annual empty results and anonymous session do not launch unauthenticated queries", async () => {
  mocks.token = null;
  render(<RuoloParticellePage />);
  await act(async () => undefined);
  expect(mocks.list).not.toHaveBeenCalled();
  expect(screen.getByText("Caricamento...")).toBeInTheDocument();
});

test("the page provides a suspense fallback while navigation is loading", async () => {
  mocks.suspend = true;
  render(<RuoloParticellePage />);
  expect(screen.getByText("Caricamento...")).toBeInTheDocument();
});

test("changing URL filters refreshes the annual query", async () => {
  const component = render(<RuoloParticellePage />);
  await screen.findByText("Nessuna particella ruolo");
  mocks.params = new URLSearchParams("anno=2020&comune=Mogoro&foglio=2&particella=200&match_status=unmatched&match_reason=ambiguous&unmatched_only=false");
  component.rerender(<RuoloParticellePage />);
  await waitFor(() => expect(mocks.list).toHaveBeenCalledWith("token", expect.objectContaining({ anno: 2020, comune: "Mogoro", unmatched_only: false })));
  expect(screen.getByDisplayValue("ambiguous")).toBeInTheDocument();
});
