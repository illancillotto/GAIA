import { act, fireEvent, render, screen, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import type { Dui2026LayerResponse, ParticellaPopupData, ParticellaPopupRuoloSummary } from "@/types/gis";

const mocks = vi.hoisted(() => ({
  parcel: null as ParticellaPopupData | null,
  getStoredAccessToken: vi.fn(() => "r57-token"),
  listSavedSelections: vi.fn(async () => []),
  listDistretti: vi.fn(async () => []),
  latestAdeStatus: vi.fn(async () => null),
  latestDuiLayer: vi.fn(async (): Promise<Dui2026LayerResponse> => ({
    label: "DUI 2026",
    year: 2026,
    source_path: "r57-empty-dui.geojson",
    source_filename: "r57-empty-dui.geojson",
    source_date: "2026-10-12",
    source_updated_at: "2026-10-12T00:00:00Z",
    rendering_mode: "geojson_fallback",
    stats: {
      total_polygons: 0,
      in_ruolo_2025: 0,
      not_in_ruolo_2025: 0,
      with_contatore: 0,
      without_contatore: 0,
      with_telerilev: 0,
    },
    geojson: { type: "FeatureCollection", features: [] },
  })),
  whiteLayer: vi.fn(async () => ({
    generated_at: "2026-10-12T00:00:00Z",
    tipologie: [],
    operatori: [],
    stats: { total: 0, mapped: 0, unmapped: 0, truncated: false },
    geojson: { type: "FeatureCollection", features: [] },
  })),
}));

vi.mock("next/dynamic", () => ({
  default: () => function PopupMapBoundary({ onParticellaClick }: {
    onParticellaClick: (parcel: ParticellaPopupData | null) => void;
  }) {
    return <button onClick={() => onParticellaClick(mocks.parcel)}>Select GIS parcel</button>;
  },
}));
vi.mock("@/components/catasto/catasto-page", () => ({
  CatastoPage: ({ children }: { children: ReactNode }) => <main>{children}</main>,
}));
vi.mock("@/components/catasto/gis/GisWorkspace", () => ({
  default: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  GisBasemapControl: () => null,
}));
vi.mock("@/components/catasto/gis/AdeAlignmentPanel", () => ({ default: () => null }));
vi.mock("@/components/catasto/gis/AnalysisPanel", () => ({ default: () => null }));
vi.mock("@/components/catasto/gis/ArchiveList", () => ({ default: () => null }));
vi.mock("@/components/catasto/gis/DistrettiPanel", () => ({ default: () => null }));
vi.mock("@/components/catasto/gis/DeliveryPointQuickFilters", () => ({ default: () => null }));
vi.mock("@/components/catasto/gis/Dui2026LivePanel", () => ({ Dui2026LivePanel: () => null }));
vi.mock("@/components/catasto/gis/DrawingTools", () => ({ default: () => null }));
vi.mock("@/components/catasto/gis/GisLayerControls", () => ({ default: () => null }));
vi.mock("@/components/catasto/gis/SelectionPanel", () => ({ default: () => null }));
vi.mock("@/components/catasto/gis/WhiteCompanyReportsPanel", () => ({
  default: () => null,
  EMPTY_WHITECOMPANY_REPORT_FILTERS: { dateFrom: "", dateTo: "", tipologia: "", operatore: "" },
}));
vi.mock("@/components/catasto/anagrafica/ParticellaDetailDialog", () => ({ ParticellaDetailDialog: () => null }));
vi.mock("@/components/catasto/catasto-anomalia-explainer", () => ({ CatastoAnomaliaExplainer: () => null }));
vi.mock("@/components/utenze/utenze-subject-quick-view-dialog", () => ({ UtenzeSubjectQuickViewDialog: () => null }));
vi.mock("@/hooks/useGisSelection", () => ({
  useGisSelection: () => ({ result: null, isLoading: false, error: null, runSelection: vi.fn(), clearSelection: vi.fn() }),
}));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.getStoredAccessToken }));
vi.mock("@/lib/api", () => ({ searchAnagraficaSubjects: vi.fn() }));
vi.mock("@/lib/api/catasto", () => ({
  capacitasGetRptCertificatoLink: vi.fn(),
  catastoGetDistrettoGeojson: vi.fn(),
  catastoGisGetAdeAlignmentReport: vi.fn(),
  catastoGisGetDui2026DomandaDetail: vi.fn(),
  catastoGisGetDui2026LatestLayer: mocks.latestDuiLayer,
  catastoGisGetWhiteCompanyReportLayer: mocks.whiteLayer,
  catastoGisGetLatestAdeWfsRunStatus: mocks.latestAdeStatus,
  catastoGisGetAdeWfsRunStatus: vi.fn(),
  catastoGisCreateSavedSelection: vi.fn(),
  catastoGisDeleteSavedSelection: vi.fn(),
  catastoGisExport: vi.fn(),
  catastoGisGetSavedSelection: vi.fn(),
  catastoGisListSavedSelections: mocks.listSavedSelections,
  catastoGisResolveRefs: vi.fn(),
  catastoGisUpdateSavedSelection: vi.fn(),
  catastoRefreshDeliveryPointsGisCache: vi.fn(),
  catastoListDistretti: mocks.listDistretti,
}));

import CatastoGisPage from "@/app/catasto/gis/page";

function parcelFixture(overrides: Partial<ParticellaPopupData> = {}): ParticellaPopupData {
  return {
    id: "r57-parcel",
    cfm: null,
    codice_catastale: "A001",
    nome_comune: "Marrubiu",
    foglio: "7",
    particella: "42",
    subalterno: null,
    is_current: true,
    suppressed: false,
    missing_fields: [],
    n_anomalie_aperte: 0,
    anomalie_aperte: [],
    titolare: { denominazione: "R57 holder", source: "intestatario" },
    ha_ruolo: false,
    ha_ruolo_inferito: false,
    ruolo_summary: null,
    ...overrides,
  };
}

function roleSummary(sourceMode?: string): ParticellaPopupRuoloSummary {
  return { anno_tributario_latest: 2025, n_righe: 0, n_subalterni: 0, items: [], source_mode: sourceMode };
}

async function mountPage() {
  await act(async () => { render(<CatastoGisPage />); });
  expect(mocks.listDistretti).toHaveBeenCalledWith("r57-token");
  expect(mocks.listSavedSelections).toHaveBeenCalledWith("r57-token");
  expect(mocks.whiteLayer).toHaveBeenCalled();
}

function selectParcel(parcel: ParticellaPopupData | null) {
  mocks.parcel = parcel;
  fireEvent.click(screen.getByRole("button", { name: "Select GIS parcel" }));
}

function parcelPanel() {
  const panel = document.querySelector("[data-gis-parcel-panel]");
  if (!(panel instanceof HTMLElement)) throw new Error("Mounted parcel popup missing");
  return panel;
}

function ownedPresentationReads(reads: string[]) {
  const start = reads.indexOf("source_mode");
  const end = reads.indexOf("source_mode", start + 1);
  expect(start).toBeGreaterThanOrEqual(0);
  expect(end).toBeGreaterThan(start);
  return reads.slice(start + 1, end);
}

function observedSummary(reads: string[]): ParticellaPopupRuoloSummary {
  return {
    ...roleSummary("exact"),
    get source_mode() { reads.push("source_mode"); return "exact"; },
  };
}

describe("R57 mounted GIS parcel popup identity and status", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.parcel = null;
    window.history.replaceState({}, "", "/catasto/gis");
  });

  test.each([
    { name: "exact overrides inferred flag", overrides: { ha_ruolo: true, ha_ruolo_inferito: true }, label: "A ruolo", color: "bg-emerald-100", textColor: "text-emerald-700" },
    { name: "exact overrides fallback summary", overrides: { ha_ruolo: true, ruolo_summary: roleSummary("subject_comune_fallback") }, label: "A ruolo", color: "bg-emerald-100", textColor: "text-emerald-700" },
    { name: "inferred flag without summary", overrides: { ha_ruolo_inferito: true }, label: "Ruolo inferito", color: "bg-amber-100", textColor: "text-amber-700" },
    { name: "fallback summary without inferred flag", overrides: { ruolo_summary: roleSummary("subject_comune_fallback") }, label: "Ruolo inferito", color: "bg-amber-100", textColor: "text-amber-700" },
    { name: "unknown nonempty source remains inferred", overrides: { ruolo_summary: roleSummary("future_mode") }, label: "Ruolo inferito", color: "bg-amber-100", textColor: "text-amber-700" },
    { name: "exact summary alone is not exact role", overrides: { ruolo_summary: roleSummary("exact") }, label: "Fuori ruolo", color: "bg-slate-100", textColor: "text-slate-600" },
    { name: "empty source is not inferred", overrides: { ruolo_summary: roleSummary("") }, label: "Fuori ruolo", color: "bg-slate-100", textColor: "text-slate-600" },
    { name: "absent source is not inferred", overrides: { ruolo_summary: roleSummary() }, label: "Fuori ruolo", color: "bg-slate-100", textColor: "text-slate-600" },
    { name: "absent summary is outside role", overrides: {}, label: "Fuori ruolo", color: "bg-slate-100", textColor: "text-slate-600" },
  ])("role precedence: $name", async ({ overrides, label, color, textColor }) => {
    await mountPage();
    selectParcel(parcelFixture(overrides));
    const badge = within(parcelPanel()).getByText(label, { selector: "span" });
    expect(badge).toHaveClass("rounded-full", "px-2", "py-0.5", "text-[10px]", "font-semibold", color, textColor);
    expect(within(parcelPanel()).getByText("7 / 42", { selector: "p" })).toBeInTheDocument();
  });

  test.each([
    { name: "CFM wins even for incomplete keys", overrides: { cfm: "CFM retained", foglio: null }, title: "CFM retained", location: "Riferimenti catastali non disponibili per questo poligono GIS.", incomplete: true },
    { name: "null code marks incomplete", overrides: { codice_catastale: null }, title: "Particella GIS incompleta", location: "Riferimenti catastali non disponibili per questo poligono GIS.", incomplete: true },
    { name: "empty code marks incomplete", overrides: { codice_catastale: "" }, title: "Particella GIS incompleta", location: "Riferimenti catastali non disponibili per questo poligono GIS.", incomplete: true },
    { name: "empty sheet marks incomplete", overrides: { foglio: "" }, title: "Particella GIS incompleta", location: "Riferimenti catastali non disponibili per questo poligono GIS.", incomplete: true },
    { name: "absent parcel marks incomplete", overrides: { particella: undefined }, title: "Particella GIS incompleta", location: "Riferimenti catastali non disponibili per questo poligono GIS.", incomplete: true },
    { name: "empty CFM falls back to complete key", overrides: { cfm: "" }, title: "7 / 42", location: "Marrubiu · Fg. 7 · Part. 42", incomplete: false },
    { name: "empty municipality is retained", overrides: { nome_comune: "" }, title: "7 / 42", location: " · Fg. 7 · Part. 42", incomplete: false },
    { name: "null municipality falls back to code", overrides: { nome_comune: null }, title: "7 / 42", location: "A001 · Fg. 7 · Part. 42", incomplete: false },
    { name: "zero-like string keys remain complete", overrides: { foglio: "0", particella: "0", subalterno: "0" }, title: "0 / 0", location: "Marrubiu · Fg. 0 · Part. 0 · Sub. 0", incomplete: false },
    { name: "empty subalterno adds no suffix", overrides: { subalterno: "" }, title: "7 / 42", location: "Marrubiu · Fg. 7 · Part. 42", incomplete: false },
    { name: "whitespace CFM stays truthy", overrides: { cfm: " ", subalterno: "2" }, title: " ", location: "Marrubiu · Fg. 7 · Part. 42 · Sub. 2", incomplete: false },
  ])("identity presentation: $name", async ({ overrides, title, location, incomplete }) => {
    await mountPage();
    selectParcel(parcelFixture(overrides));
    const panel = parcelPanel();
    expect(panel.querySelector("p.truncate")?.textContent).toBe(title);
    expect(panel.querySelector("p.mt-1")?.textContent).toBe(location);
    expect(Boolean(within(panel).queryByText("Record GIS incompleto"))).toBe(incomplete);
    expect(Boolean(within(panel).queryByText("Dati record cat_particella"))).toBe(incomplete);
  });

  test.each([
    { suppressed: true, is_current: true, expected: "Soppresso" },
    { suppressed: true, is_current: false, expected: "Soppresso" },
    { suppressed: false, is_current: true, expected: "Corrente" },
    { suppressed: false, is_current: false, expected: "Storico" },
  ])("record precedence suppressed=$suppressed current=$is_current", async ({ suppressed, is_current, expected }) => {
    await mountPage();
    selectParcel(parcelFixture({ codice_catastale: null, suppressed, is_current }));
    const stateLabel = within(parcelPanel()).getByText("Stato record");
    expect(stateLabel.parentElement).toHaveTextContent(expected);
    expect(stateLabel.nextElementSibling?.textContent).toBe(expected);
  });

  test("preserves the two independent badge ha_ruolo reads and fallback read ordering", async () => {
    await mountPage();
    const reads: string[] = [];
    let exactReads = 0;
    const summary: ParticellaPopupRuoloSummary = {
      ...roleSummary("exact"),
      get source_mode() { reads.push("source_mode"); return "exact"; },
    };
    const parcel: ParticellaPopupData = {
      ...parcelFixture({ ruolo_summary: summary }),
      get ha_ruolo() { exactReads += 1; reads.push(`ha_ruolo:${exactReads}`); return exactReads !== 3; },
      get ha_ruolo_inferito() { reads.push("ha_ruolo_inferito"); return false; },
    };
    selectParcel(parcel);
    const badge = within(parcelPanel()).getByText("Fuori ruolo", { selector: "span" });
    expect(badge).toHaveClass("bg-emerald-100", "text-emerald-700");
    expect(reads.slice(0, 5)).toEqual(["ha_ruolo:1", "source_mode", "ha_ruolo_inferito", "ha_ruolo:2", "ha_ruolo:3"]);
  });

  test("rereads ruolo_summary for fallback after reading the original source mode", async () => {
    await mountPage();
    const reads: string[] = [];
    let summaryReads = 0;
    const summary: ParticellaPopupRuoloSummary = {
      ...roleSummary("subject_comune_fallback"),
      get source_mode() { reads.push("source_mode"); return "subject_comune_fallback"; },
    };
    const parcel: ParticellaPopupData = {
      ...parcelFixture(),
      get ruolo_summary() {
        summaryReads += 1;
        reads.push(`summary:${summaryReads}`);
        return summaryReads === 2 ? null : summary;
      },
      get ha_ruolo_inferito() { reads.push("inferred"); return false; },
      get ha_ruolo() { reads.push("exact"); return false; },
    };
    selectParcel(parcel);
    expect(within(parcelPanel()).getByText("Fuori ruolo", { selector: "span" })).toHaveClass("bg-slate-100", "text-slate-600");
    const firstSummary = reads.indexOf("summary:1");
    expect(reads.slice(firstSummary, firstSummary + 6)).toEqual(["summary:1", "source_mode", "inferred", "summary:2", "exact", "exact"]);
  });

  test("inferred true skips the second fallback summary read but not the initial source mode", async () => {
    await mountPage();
    const reads: string[] = [];
    let summaryReads = 0;
    const summary = observedSummary(reads);
    const parcel: ParticellaPopupData = {
      ...parcelFixture(),
      get ruolo_summary() { summaryReads += 1; reads.push(`summary:${summaryReads}`); return summary; },
      get ha_ruolo_inferito() { reads.push("inferred"); return true; },
      get ha_ruolo() { reads.push("exact"); return false; },
    };
    selectParcel(parcel);
    expect(within(parcelPanel()).getByText("Ruolo inferito", { selector: "span" })).toHaveClass("bg-amber-100", "text-amber-700");
    const firstSummary = reads.indexOf("summary:1");
    expect(reads.slice(firstSummary, firstSummary + 6)).toEqual(["summary:1", "source_mode", "inferred", "exact", "exact", "summary:2"]);
  });

  test.each([
    { name: "missing code skips sheet and parcel", code: null, sheet: "7", parcelNumber: "42", expectedReads: ["code"] },
    { name: "missing sheet skips parcel", code: "A001", sheet: null, parcelNumber: "42", expectedReads: ["code", "sheet"] },
    { name: "missing parcel is checked last", code: "A001", sheet: "7", parcelNumber: null, expectedReads: ["code", "sheet", "parcel"] },
  ])("key getter short circuit: $name", async ({ code, sheet, parcelNumber, expectedReads }) => {
    await mountPage();
    const reads: string[] = [];
    const parcel: ParticellaPopupData = {
      ...parcelFixture({ cfm: "Named incomplete parcel", ruolo_summary: observedSummary(reads) }),
      get codice_catastale() { reads.push("code"); return code; },
      get foglio() { reads.push("sheet"); return sheet; },
      get particella() { reads.push("parcel"); return parcelNumber; },
    };
    selectParcel(parcel);
    const keyReads = ownedPresentationReads(reads).filter((read) => ["code", "sheet", "parcel"].includes(read));
    expect(keyReads).toEqual(expectedReads);
    expect(within(parcelPanel()).getByText("Named incomplete parcel", { selector: "p" })).toBeInTheDocument();
    expect(within(parcelPanel()).getByText("Record GIS incompleto")).toBeInTheDocument();
  });

  test.each([
    { cfm: "Named complete parcel", expectedTitle: "Named complete parcel", expectedReads: ["code", "sheet", "parcel", "cfm", "sheet", "parcel"] },
    { cfm: "", expectedTitle: "7 / 42", expectedReads: ["code", "sheet", "parcel", "cfm", "sheet", "parcel", "sheet", "parcel"] },
  ])("CFM title guard preserves key reads for '$cfm'", async ({ cfm, expectedTitle, expectedReads }) => {
    await mountPage();
    const reads: string[] = [];
    const parcel: ParticellaPopupData = {
      ...parcelFixture({ ruolo_summary: observedSummary(reads) }),
      get codice_catastale() { reads.push("code"); return "A001"; },
      get foglio() { reads.push("sheet"); return "7"; },
      get particella() { reads.push("parcel"); return "42"; },
      get cfm() { reads.push("cfm"); return cfm; },
    };
    selectParcel(parcel);
    const keyReads = ownedPresentationReads(reads).filter((read) => ["code", "sheet", "parcel", "cfm"].includes(read));
    expect(keyReads).toEqual(expectedReads);
    expect(parcelPanel().querySelector("p.truncate")?.textContent).toBe(expectedTitle);
    expect(parcelPanel().querySelector("p.mt-1")?.textContent).toBe("Marrubiu · Fg. 7 · Part. 42");
  });

  test("subalterno is read independently for suffix truthiness and suffix value", async () => {
    await mountPage();
    const reads: string[] = [];
    let sourceReads = 0;
    let ownedSubReads = 0;
    const summary: ParticellaPopupRuoloSummary = {
      ...roleSummary("exact"),
      get source_mode() { sourceReads += 1; reads.push("source_mode"); return "exact"; },
    };
    const parcel: ParticellaPopupData = {
      ...parcelFixture({ ruolo_summary: summary }),
      get subalterno() {
        reads.push("subalterno");
        if (sourceReads !== 1) return "3";
        ownedSubReads += 1;
        return ownedSubReads === 1 ? "2" : "3";
      },
    };
    selectParcel(parcel);
    expect(ownedPresentationReads(reads).filter((read) => read === "subalterno")).toEqual(["subalterno", "subalterno"]);
    expect(parcelPanel().querySelector("p.mt-1")?.textContent).toBe("Marrubiu · Fg. 7 · Part. 42 · Sub. 3");
  });

  test.each([
    { suppressed: true, expected: "Soppresso", expectedReads: ["suppressed"] },
    { suppressed: false, expected: "Corrente", expectedReads: ["suppressed", "current"] },
  ])("suppression short circuit suppressed=$suppressed", async ({ suppressed, expected, expectedReads }) => {
    await mountPage();
    const reads: string[] = [];
    const parcel: ParticellaPopupData = {
      ...parcelFixture({ codice_catastale: null, ruolo_summary: observedSummary(reads) }),
      get suppressed() { reads.push("suppressed"); return suppressed; },
      get is_current() { reads.push("current"); return true; },
    };
    selectParcel(parcel);
    const stateReads = ownedPresentationReads(reads).filter((read) => ["suppressed", "current"].includes(read));
    expect(stateReads).toEqual(expectedReads);
    expect(within(parcelPanel()).getByText("Stato record").nextElementSibling?.textContent).toBe(expected);
  });

  test("closes, reopens and clears the real popup without retaining the previous status", async () => {
    await mountPage();
    expect(document.querySelector("[data-gis-parcel-panel]")).not.toBeInTheDocument();
    selectParcel(parcelFixture({ cfm: "First parcel", ha_ruolo: true }));
    expect(within(parcelPanel()).getByText("A ruolo", { selector: "span" })).toBeInTheDocument();
    fireEvent.click(within(parcelPanel()).getByRole("button", { name: "Chiudi dettaglio particella GIS" }));
    expect(document.querySelector("[data-gis-parcel-panel]")).not.toBeInTheDocument();
    selectParcel(parcelFixture({ id: "second-parcel", foglio: null, ha_ruolo_inferito: true }));
    expect(within(parcelPanel()).getByText("Particella GIS incompleta", { selector: "p" })).toBeInTheDocument();
    expect(within(parcelPanel()).getByText("Ruolo inferito", { selector: "span" })).toHaveClass("bg-amber-100");
    expect(within(parcelPanel()).queryByText("First parcel")).not.toBeInTheDocument();
    selectParcel(null);
    expect(document.querySelector("[data-gis-parcel-panel]")).not.toBeInTheDocument();
    expect(mocks.listDistretti).toHaveBeenCalledTimes(1);
    expect(mocks.latestAdeStatus).toHaveBeenCalledTimes(1);
  });
});
