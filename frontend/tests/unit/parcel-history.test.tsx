import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { ParcelControlWorkspace } from "@/components/ruolo/parcel-control-workspace";
import { ParcelHistoryWorkspace, historyLink } from "@/components/ruolo/parcel-history-workspace";
import { ParcelHistoryTaxes, historyMoney } from "@/components/ruolo/parcel-history-taxes";
import { ParcelHistoryCadastre, historyDate } from "@/components/ruolo/parcel-history-cadastre";
import type { ParcelHistory, ParcelHistoryPage } from "@/types/parcel-history";

const mocks = vi.hoisted(() => ({ params: new URLSearchParams(), push: vi.fn(), request: vi.fn(), token: "token" as string | null }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: mocks.push }), useSearchParams: () => mocks.params }));
vi.mock("@/components/ruolo/module-page", () => ({ RuoloModulePage: ({ title, children }: { title: string; children: React.ReactNode }) => <main><h1>{title}</h1>{children}</main> }));
vi.mock("@/components/layout/app-shell-context", () => ({ useAppShellContext: () => ({ currentUser: { role: "viewer" }, grantedSectionKeys: [] }) }));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: () => mocks.token }));
vi.mock("@/lib/parcel-history-api", () => ({ parcelHistoryRequest: mocks.request }));

export function sampleHistory(): ParcelHistory {
  return { id: "parcel", reference: { comune_nome: "ORISTANO", comune_codice: "G113", foglio: "1", particella: "100", subalterno: "", sezione: null, catasto: null }, identity_incomplete: false,
    first_year: 2020, last_year: 2022, taxes: [{ id: "row-1", year: 2020, notice_id: "notice-1", notice_number: "001", name: "Mario Rossi", tax_code: "ROSSI", partita_tax_code: "PARTITA", co_holders: "Anna Rossi", maintenance: 12.34, irrigation: 0, institutional: 1, total: 13.34, area_ha: 1, irrigated_ha: 0, crop: "Mais", district: "1", catasto_id: null },
      { id: "row-2", year: 2022, notice_id: "notice-2", notice_number: "002", name: "Anna Bianchi", tax_code: "BIANCHI", partita_tax_code: "BIANCHI", co_holders: null, maintenance: null, irrigation: null, institutional: null, total: null, area_ha: null, irrigated_ha: null, crop: null, district: null, catasto_id: null }],
    cadastre: { documents: [], events: [], completeness: "not_certified", cessation: "not_documented" } };
}

const page: ParcelHistoryPage = { items: [{ id: "parcel", comune: "ORISTANO", comune_codice: "G113", foglio: "1", particella: "100", subalterno: "", first_year: 2020, last_year: 2022, years_count: 2 }], total: 26, page: 1, page_size: 25 };

beforeEach(() => {
  mocks.params = new URLSearchParams(); mocks.push.mockReset(); mocks.request.mockReset(); mocks.token = "token";
  mocks.request.mockResolvedValue(page);
});

test("default page offers direct history, labelled search, preserved filters and pagination", async () => {
  render(<ParcelControlWorkspace annualView={<p>Annual view</p>} />);
  expect(screen.getByRole("status")).toHaveTextContent("Caricamento");
  expect(await screen.findByRole("heading", { name: "26 particelle trovate" })).toBeInTheDocument();
  expect(mocks.request).toHaveBeenCalledWith("token", "?");
  expect(screen.getByRole("link", { name: /ORISTANO.*Apri storia/ })).toHaveAttribute("href", "/ruolo/particelle?vista=storia&storia=parcel");
  expect(screen.getByRole("link", { name: "Successiva" })).toHaveAttribute("href", expect.stringContaining("page=2"));
  expect(screen.queryByText("Apri pratica")).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Comune"), { target: { value: "  Oristano " } });
  fireEvent.change(screen.getByLabelText("Foglio"), { target: { value: "1" } });
  fireEvent.change(screen.getByLabelText("Contribuente o avviso"), { target: { value: "Rossi" } });
  fireEvent.submit(screen.getByRole("button", { name: "Cerca particella" }).closest("form")!);
  expect(mocks.push).toHaveBeenCalledWith("/ruolo/particelle?vista=storia&comune=Oristano&foglio=1&search=Rossi");
});

test("filters query, second page, subalterno, empty list and reset stay in the URL", async () => {
  mocks.params = new URLSearchParams("vista=storia&comune=ORISTANO&foglio=1&particella=100&search=Rossi&page=2");
  mocks.request.mockResolvedValue({ ...page, page: 2, items: [{ ...page.items[0], comune: "", subalterno: "3" }] });
  const view = render(<ParcelHistoryWorkspace />);
  await screen.findByText("Comune non indicato");
  expect(mocks.request).toHaveBeenCalledWith("token", "?comune=ORISTANO&foglio=1&particella=100&search=Rossi&page=2");
  expect(screen.getByText(/Sub 3/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Precedente" })).toHaveAttribute("href", expect.stringContaining("page=1"));
  view.unmount(); mocks.request.mockResolvedValue({ ...page, items: [], total: 0 });
  render(<ParcelHistoryWorkspace />);
  expect(await screen.findByRole("heading", { name: "Nessuna particella trovata" })).toBeInTheDocument();
  expect(historyLink(new URLSearchParams("vista=storia&page=2&storia=abc"), { storia: null })).toBe("/ruolo/particelle?vista=storia&page=2");
});

test("history opens without a practice and distinguishes taxpayers, gaps, sources and cadastral ownership", async () => {
  mocks.params = new URLSearchParams("vista=storia&storia=parcel&search=Rossi&page=2");
  const history = sampleHistory(); history.reference.sezione = "A"; history.reference.subalterno = "3";
  mocks.request.mockResolvedValue(history);
  render(<ParcelHistoryWorkspace />);
  await screen.findByText("Mario Rossi");
  expect(mocks.request).toHaveBeenCalledWith("token", "/parcel");
  expect(screen.getByText("Anna Bianchi")).toBeInTheDocument();
  expect(screen.getByText(/Nessuna riga importata/)).toBeInTheDocument();
  expect(screen.getByText("Non documentata")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Apri tributo 001" })).toHaveAttribute("href", "/ruolo/tributi/notice-1");
  expect(screen.getByRole("link", { name: /Torna ai risultati/ })).toHaveAttribute("href", "/ruolo/particelle?vista=storia&search=Rossi&page=2");
  fireEvent.click(screen.getByRole("tab", { name: "Proprietà catastale" }));
  expect(screen.getByRole("tabpanel")).toHaveTextContent("Manca una visura storica collegata");
  expect(screen.getByRole("tab", { name: "Proprietà catastale" })).toHaveAttribute("aria-selected", "true");
  fireEvent.click(screen.getByRole("tab", { name: "Tributi nel tempo" }));
  expect(screen.getByRole("tabpanel")).toHaveTextContent("Mario Rossi");
  for (const key of ["ArrowRight", "ArrowRight", "ArrowLeft", "ArrowLeft", "End", "Home", "Escape"]) {
    fireEvent.keyDown(screen.getByRole("tab", { selected: true }), { key });
  }
  expect(screen.getByRole("tab", { name: "Tributi nel tempo" })).toHaveAttribute("aria-selected", "true");
});

test("incomplete identity and missing values are visible without inventing zeros or cessation", async () => {
  mocks.params = new URLSearchParams("storia=parcel");
  const history = sampleHistory(); history.identity_incomplete = true; history.reference.comune_codice = "";
  history.taxes[0] = { ...history.taxes[0], name: null, tax_code: null, partita_tax_code: null };
  mocks.request.mockResolvedValue(history);
  render(<ParcelHistoryWorkspace />);
  expect(await screen.findByText(/Identificativo incompleto/)).toBeInTheDocument();
  expect(screen.getByText("Contribuente non indicato")).toBeInTheDocument();
  expect(historyMoney(null)).toBe("Non disponibile");
  expect(historyMoney(0)).toMatch(/0,00/);
});

test("historical owners retain dates, rights, shares and original document links; ambiguous extractions stay explicit", () => {
  const history = sampleHistory();
  history.cadastre.events = [{ id: "event", name: "Proprietario storico", tax_code: "CF", right: "Proprietà", share: "1/2", from_date: "1990-01-01", act_date: "1989-12-01", act: "Successione", document_id: "doc" }, { id: "unknown", name: null, tax_code: null, right: null, share: null, from_date: null, act_date: null, act: null, document_id: "doc" }];
  history.cadastre.documents = [{ id: "doc", filename: "Visura storica.pdf", observed_at: "2026-11-12", recorded_at: "2026-11-12T10:00:00", type: "Storica", extraction_status: "completed", owners: [{ name: "Proprietario attuale", tax_code: "CF2", right: "Usufrutto", share: "1/1" }], ambiguous: false, suppressed: true, suppressed_at: "2022-04-01" }, { id: "doc2", filename: "Da verificare.pdf", observed_at: null, recorded_at: "2026-11-12", type: "Storica", extraction_status: "failed", owners: [], ambiguous: true, suppressed: false, suppressed_at: null }];
  render(<ParcelHistoryCadastre history={history} />);
  expect(screen.getByText("Proprietario storico")).toBeInTheDocument();
  expect(screen.getByText("Proprietario attuale")).toBeInTheDocument();
  expect(screen.getByText(/Decorrenza: 01\/01\/1990/)).toBeInTheDocument();
  expect(screen.getByText(/Soppressione catastale documentata/)).toHaveTextContent("Non equivale alla cessazione del tributo");
  expect(screen.getAllByRole("link", { name: "Apri visura originale" })[0]).toHaveAttribute("href", "/catasto/documents/doc");
  expect(screen.getByText(/riferimenti non univoci/)).toBeInTheDocument();
  expect(historyDate(null)).toBe("Data non disponibile");
});

test("retry and anonymous/error states never masquerade as zero results", async () => {
  mocks.params = new URLSearchParams("storia=parcel");
  mocks.request.mockRejectedValueOnce(new Error("Servizio non aggiornato")).mockResolvedValue(sampleHistory());
  const view = render(<ParcelHistoryWorkspace />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Servizio non aggiornato");
  expect(screen.queryByText(/particelle trovate/)).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Torna alla ricerca" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Riprova" }));
  await screen.findByText("Mario Rossi"); view.unmount();
  mocks.token = null; render(<ParcelHistoryWorkspace />);
  expect(screen.getByRole("alert")).toHaveTextContent("Accedi a GAIA");
});

test("stale success, stale failure and unexpected failures do not overwrite the current route", async () => {
  let resolve: (value: ParcelHistoryPage) => void = () => {};
  let reject: (reason: unknown) => void = () => {};
  mocks.request.mockImplementationOnce(() => new Promise<ParcelHistoryPage>(ok => { resolve = ok; }));
  const view = render(<ParcelHistoryWorkspace />);
  view.unmount(); await act(async () => resolve(page));
  mocks.request.mockImplementationOnce(() => new Promise<ParcelHistoryPage>((_, fail) => { reject = fail; }));
  const second = render(<ParcelHistoryWorkspace />); second.unmount();
  await act(async () => reject(new Error("stale")));
  mocks.request.mockRejectedValue("failure"); render(<ParcelHistoryWorkspace />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Caricamento non riuscito");
  await waitFor(() => expect(screen.queryByRole("status")).not.toBeInTheDocument());
});

test("plain tax timeline is usable independently", () => {
  render(<ParcelHistoryTaxes history={sampleHistory()} />);
  expect(screen.getByRole("heading", { name: /2020/ })).toBeInTheDocument();
});

test("navigation list to detail, another parcel and back never renders data from the previous URL", async () => {
  const view = render(<ParcelHistoryWorkspace />);
  await screen.findByRole("heading", { name: "26 particelle trovate" });
  let resolveDetail: (value: ParcelHistory) => void = () => {};
  mocks.request.mockImplementationOnce(() => new Promise<ParcelHistory>(resolve => { resolveDetail = resolve; }));
  mocks.params = new URLSearchParams("vista=storia&storia=parcel");
  view.rerender(<ParcelHistoryWorkspace />);
  expect(screen.queryByText("26 particelle trovate")).not.toBeInTheDocument();
  expect(screen.getByRole("status")).toBeInTheDocument();
  await act(async () => resolveDetail(sampleHistory()));
  await screen.findByText("Mario Rossi");
  const next = sampleHistory(); next.reference.particella = "200"; next.taxes[0].name = "Nuovo contribuente";
  mocks.request.mockResolvedValueOnce(next);
  mocks.params = new URLSearchParams("vista=storia&storia=second");
  view.rerender(<ParcelHistoryWorkspace />);
  await screen.findByText("Nuovo contribuente");
  expect(screen.queryByText("Mario Rossi")).not.toBeInTheDocument();
  mocks.request.mockResolvedValueOnce(page);
  mocks.params = new URLSearchParams("vista=storia");
  view.rerender(<ParcelHistoryWorkspace />);
  await screen.findByRole("heading", { name: "26 particelle trovate" });
  expect(screen.queryByText("Nuovo contribuente")).not.toBeInTheDocument();
});
