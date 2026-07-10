import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import CatastoDeliveryPointsConfigPage from "@/app/catasto/punti-consegna-configurazione/page";
import {
  DEFAULT_GIS_TILE_REVISION,
  GIS_TILE_REVISION_UPDATED_EVENT,
  getStoredGisTileRevision,
  storeGisTileRevision,
} from "@/lib/catasto-gis-cache";

const GIS_TILE_LAYERS = [
  "cat_distretti",
  "cat_distretti_boundaries",
  "cat_particelle_current",
  "cat_delivery_points_current",
  "cat_irrigation_canals_current",
  "cat_dui_2026_current",
];

const mocks = vi.hoisted(() => ({
  getConfig: vi.fn(),
  getImportJob: vi.fn(),
  refreshGisCache: vi.fn(),
  updateConfig: vi.fn(),
  runImport: vi.fn(),
  getStoredAccessToken: vi.fn(),
}));

vi.mock("@/lib/api/catasto", () => ({
  catastoGetDeliveryPointsImportJob: mocks.getImportJob,
  catastoGetDeliveryPointsImportConfig: mocks.getConfig,
  catastoRefreshDeliveryPointsGisCache: mocks.refreshGisCache,
  catastoUpdateDeliveryPointsImportConfig: mocks.updateConfig,
  catastoImportDeliveryPointsFromConfig: mocks.runImport,
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/components/catasto/catasto-page", () => ({
  CatastoPage: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));

vi.mock("@/components/ui/alert-banner", () => ({
  AlertBanner: ({ title, message, children }: { title: string; message?: string; children?: ReactNode }) => (
    <div>
      <span>{title}</span>
      <span>{message ?? children}</span>
    </div>
  ),
}));

describe("Catasto delivery points config page", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  beforeEach(() => {
    mocks.getConfig.mockReset();
    mocks.getImportJob.mockReset();
    mocks.refreshGisCache.mockReset();
    mocks.updateConfig.mockReset();
    mocks.runImport.mockReset();
    mocks.getStoredAccessToken.mockReset();
    mocks.getStoredAccessToken.mockReturnValue("token-123");
    window.localStorage.clear();
  });

  test("loads config and allows saving a new NAS path", async () => {
    mocks.getConfig.mockResolvedValue({
      root_path: "/mnt/nas/current",
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: "admin",
      updated_at: "2026-07-06T10:00:00Z",
    });
    mocks.updateConfig.mockResolvedValue({
      root_path: "/mnt/nas/updated",
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: "admin",
      updated_at: "2026-07-06T11:00:00Z",
    });

    render(<CatastoDeliveryPointsConfigPage />);

    const input = await screen.findByLabelText("Cartella sorgente NAS");
    expect(input).toHaveValue("/mnt/nas/current");

    fireEvent.change(input, { target: { value: "/mnt/nas/updated" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva configurazione" }));

    await waitFor(() => {
      expect(mocks.updateConfig).toHaveBeenCalledWith("token-123", { root_path: "/mnt/nas/updated" });
    });
    expect(screen.getByLabelText("Cartella sorgente NAS")).toHaveValue("/mnt/nas/updated");
  });

  test("runs import and renders returned stats", async () => {
    mocks.getConfig.mockResolvedValue({
      root_path: "/mnt/nas/current",
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: "admin",
      updated_at: "2026-07-06T10:00:00Z",
    });
    mocks.runImport.mockResolvedValue({
      job_id: "00000000-0000-0000-0000-000000000001",
      status: "completed",
      root_path: "/mnt/nas/current",
      requested_by: "admin",
      error_message: null,
      points_processed: 10,
      canals_processed: 2,
      meter_readings_linked: 8,
      meter_readings_unlinked: 3,
      started_at: "2026-07-06T10:00:00Z",
      completed_at: "2026-07-06T10:01:00Z",
      created_at: "2026-07-06T10:00:00Z",
      updated_at: "2026-07-06T10:01:00Z",
    });

    render(<CatastoDeliveryPointsConfigPage />);

    await screen.findByDisplayValue("/mnt/nas/current");
    fireEvent.click(screen.getByRole("button", { name: "Importa dal NAS" }));

    await screen.findByText("Punti processati");
    expect(screen.getByText("10")).toBeInTheDocument();
    expect(screen.getByText("Letture collegate")).toBeInTheDocument();
    expect(screen.getByText("/mnt/nas/current")).toBeInTheDocument();
  });

  test("refreshes GIS cache and stores GIS tile revision", async () => {
    mocks.getConfig.mockResolvedValue({
      root_path: "/mnt/nas/current",
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: "admin",
      updated_at: "2026-07-06T10:00:00Z",
    });
    mocks.refreshGisCache.mockResolvedValue({
      tile_revision: "20260708103000123456",
      refreshed_at: "2026-07-08T10:30:00Z",
      affected_layers: GIS_TILE_LAYERS,
      martin_restarted: true,
      restart_error: null,
      message: "Cache GIS aggiornata e Martin riavviato. Ricaricare la mappa se e gia aperta.",
    });

    render(<CatastoDeliveryPointsConfigPage />);

    await screen.findByDisplayValue("/mnt/nas/current");
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna cache GIS" }));

    await waitFor(() => {
      expect(mocks.refreshGisCache).toHaveBeenCalledWith("token-123");
    });
    expect(window.localStorage.getItem("gaia.catasto.gisTileRevision")).toBe("20260708103000123456");
    expect(screen.getByText(/Revisione: 20260708103000123456/)).toBeInTheDocument();
  });

  test("shows Martin restart errors returned by GIS cache refresh", async () => {
    mocks.getConfig.mockResolvedValue({
      root_path: "/mnt/nas/current",
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: "admin",
      updated_at: "2026-07-06T10:00:00Z",
    });
    mocks.refreshGisCache.mockResolvedValue({
      tile_revision: "20260708103000999999",
      refreshed_at: "2026-07-08T10:30:00Z",
      affected_layers: GIS_TILE_LAYERS,
      martin_restarted: false,
      restart_error: "docker socket assente",
      message: "Revisione cache GIS aggiornata, ma Martin non e stato riavviato.",
    });

    render(<CatastoDeliveryPointsConfigPage />);

    await screen.findByDisplayValue("/mnt/nas/current");
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna cache GIS" }));

    await screen.findByText(/docker socket assente/);
    expect(window.localStorage.getItem("gaia.catasto.gisTileRevision")).toBe("20260708103000999999");
  });

  test("shows session error when GIS cache refresh has no token", async () => {
    mocks.getStoredAccessToken.mockReset();
    mocks.getStoredAccessToken.mockReturnValueOnce("token-123").mockReturnValue(null);
    mocks.getConfig.mockResolvedValue({
      root_path: "/mnt/nas/current",
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: "admin",
      updated_at: "2026-07-06T10:00:00Z",
    });

    render(<CatastoDeliveryPointsConfigPage />);

    await screen.findByDisplayValue("/mnt/nas/current");
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna cache GIS" }));

    await screen.findByText("Sessione non disponibile.");
    expect(mocks.refreshGisCache).not.toHaveBeenCalled();
  });

  test("shows generic GIS cache refresh error for non-error failures", async () => {
    mocks.getConfig.mockResolvedValue({
      root_path: "/mnt/nas/current",
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: "admin",
      updated_at: "2026-07-06T10:00:00Z",
    });
    mocks.refreshGisCache.mockRejectedValue("failure");

    render(<CatastoDeliveryPointsConfigPage />);

    await screen.findByDisplayValue("/mnt/nas/current");
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna cache GIS" }));

    await screen.findByText("Errore aggiornamento cache GIS.");
  });

  test("shows explicit GIS cache refresh Error messages", async () => {
    mocks.getConfig.mockResolvedValue({
      root_path: "/mnt/nas/current",
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: "admin",
      updated_at: "2026-07-06T10:00:00Z",
    });
    mocks.refreshGisCache.mockRejectedValue(new Error("Martin non raggiungibile"));

    render(<CatastoDeliveryPointsConfigPage />);

    await screen.findByDisplayValue("/mnt/nas/current");
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna cache GIS" }));

    await screen.findByText("Martin non raggiungibile");
  });

  test("handles GIS tile revision storage helpers", () => {
    const events: string[] = [];
    window.addEventListener(GIS_TILE_REVISION_UPDATED_EVENT, ((event: CustomEvent<{ revision: string }>) => {
      events.push(event.detail.revision);
    }) as EventListener);

    expect(getStoredGisTileRevision()).toBe(DEFAULT_GIS_TILE_REVISION);

    storeGisTileRevision("rev-1");

    expect(getStoredGisTileRevision()).toBe("rev-1");
    expect(events).toEqual(["rev-1"]);
  });

  test("GIS tile revision storage helpers tolerate server runtime", () => {
    const originalWindow = globalThis.window;
    vi.stubGlobal("window", undefined);

    try {
      expect(getStoredGisTileRevision()).toBe(DEFAULT_GIS_TILE_REVISION);
      expect(() => storeGisTileRevision("rev-2")).not.toThrow();
    } finally {
      vi.stubGlobal("window", originalWindow);
    }
  });

  test("renders zero stats for completed imports with nullable counters", async () => {
    mocks.getConfig.mockResolvedValue({
      root_path: "/mnt/nas/current",
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: "admin",
      updated_at: "2026-07-06T10:00:00Z",
    });
    mocks.runImport.mockResolvedValue({
      job_id: "00000000-0000-0000-0000-000000000006",
      status: "completed",
      root_path: "/mnt/nas/current",
      requested_by: "admin",
      error_message: null,
      points_processed: null,
      canals_processed: null,
      meter_readings_linked: null,
      meter_readings_unlinked: null,
      started_at: "2026-07-06T10:00:00Z",
      completed_at: "2026-07-06T10:01:00Z",
      created_at: "2026-07-06T10:00:00Z",
      updated_at: "2026-07-06T10:01:00Z",
    });

    render(<CatastoDeliveryPointsConfigPage />);

    await screen.findByDisplayValue("/mnt/nas/current");
    fireEvent.click(screen.getByRole("button", { name: "Importa dal NAS" }));

    await screen.findByText("Punti processati");
    expect(screen.getAllByText("0")).toHaveLength(4);
  });

  test("polls a pending import job and renders completed stats", async () => {
    mocks.getConfig.mockResolvedValue({
      root_path: "/mnt/nas/current",
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: "admin",
      updated_at: "2026-07-06T10:00:00Z",
    });
    mocks.runImport.mockResolvedValue({
      job_id: "00000000-0000-0000-0000-000000000001",
      status: "pending",
      root_path: "/mnt/nas/current",
      requested_by: "admin",
      error_message: null,
      points_processed: null,
      canals_processed: null,
      meter_readings_linked: null,
      meter_readings_unlinked: null,
      started_at: null,
      completed_at: null,
      created_at: "2026-07-06T10:00:00Z",
      updated_at: "2026-07-06T10:00:00Z",
    });
    mocks.getImportJob.mockResolvedValue({
      job_id: "00000000-0000-0000-0000-000000000001",
      status: "completed",
      root_path: "/mnt/nas/current",
      requested_by: "admin",
      error_message: null,
      points_processed: 12,
      canals_processed: 4,
      meter_readings_linked: 7,
      meter_readings_unlinked: 1,
      started_at: "2026-07-06T10:00:00Z",
      completed_at: "2026-07-06T10:01:00Z",
      created_at: "2026-07-06T10:00:00Z",
      updated_at: "2026-07-06T10:01:00Z",
    });

    render(<CatastoDeliveryPointsConfigPage />);

    await screen.findByDisplayValue("/mnt/nas/current");
    fireEvent.click(screen.getByRole("button", { name: "Importa dal NAS" }));

    await screen.findByText(/Import punti di consegna in corso/);
    await waitFor(() => expect(screen.getByText("12")).toBeInTheDocument(), { timeout: 4500 });
    expect(mocks.getImportJob).toHaveBeenCalledWith("token-123", "00000000-0000-0000-0000-000000000001");
  }, 10000);

  test("shows fallback error when a polled import job fails without detail", async () => {
    mocks.getConfig.mockResolvedValue({
      root_path: "/mnt/nas/current",
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: "admin",
      updated_at: "2026-07-06T10:00:00Z",
    });
    mocks.runImport.mockResolvedValue({
      job_id: "00000000-0000-0000-0000-000000000002",
      status: "running",
      root_path: "/mnt/nas/current",
      requested_by: "admin",
      error_message: null,
      points_processed: null,
      canals_processed: null,
      meter_readings_linked: null,
      meter_readings_unlinked: null,
      started_at: "2026-07-06T10:00:00Z",
      completed_at: null,
      created_at: "2026-07-06T10:00:00Z",
      updated_at: "2026-07-06T10:00:00Z",
    });
    mocks.getImportJob.mockResolvedValue({
      job_id: "00000000-0000-0000-0000-000000000002",
      status: "failed",
      root_path: "/mnt/nas/current",
      requested_by: "admin",
      error_message: null,
      points_processed: null,
      canals_processed: null,
      meter_readings_linked: null,
      meter_readings_unlinked: null,
      started_at: "2026-07-06T10:00:00Z",
      completed_at: "2026-07-06T10:01:00Z",
      created_at: "2026-07-06T10:00:00Z",
      updated_at: "2026-07-06T10:01:00Z",
    });

    render(<CatastoDeliveryPointsConfigPage />);

    await screen.findByDisplayValue("/mnt/nas/current");
    fireEvent.click(screen.getByRole("button", { name: "Importa dal NAS" }));

    await waitFor(() => expect(screen.getByText("Errore import punti di consegna.")).toBeInTheDocument(), {
      timeout: 4500,
    });
  }, 10000);

  test("shows generic polling error for non-error failures", async () => {
    mocks.getConfig.mockResolvedValue({
      root_path: "/mnt/nas/current",
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: "admin",
      updated_at: "2026-07-06T10:00:00Z",
    });
    mocks.runImport.mockResolvedValue({
      job_id: "00000000-0000-0000-0000-000000000003",
      status: "running",
      root_path: "/mnt/nas/current",
      requested_by: "admin",
      error_message: null,
      points_processed: null,
      canals_processed: null,
      meter_readings_linked: null,
      meter_readings_unlinked: null,
      started_at: "2026-07-06T10:00:00Z",
      completed_at: null,
      created_at: "2026-07-06T10:00:00Z",
      updated_at: "2026-07-06T10:00:00Z",
    });
    mocks.getImportJob.mockRejectedValue("failure");

    render(<CatastoDeliveryPointsConfigPage />);

    await screen.findByDisplayValue("/mnt/nas/current");
    fireEvent.click(screen.getByRole("button", { name: "Importa dal NAS" }));

    await waitFor(
      () => expect(screen.getByText("Errore verifica stato import punti di consegna.")).toBeInTheDocument(),
      { timeout: 4500 },
    );
  }, 10000);

  test("keeps polling state when a polled import job is still running", async () => {
    mocks.getConfig.mockResolvedValue({
      root_path: "/mnt/nas/current",
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: "admin",
      updated_at: "2026-07-06T10:00:00Z",
    });
    mocks.runImport.mockResolvedValue({
      job_id: "00000000-0000-0000-0000-000000000007",
      status: "running",
      root_path: "/mnt/nas/current",
      requested_by: "admin",
      error_message: null,
      points_processed: null,
      canals_processed: null,
      meter_readings_linked: null,
      meter_readings_unlinked: null,
      started_at: "2026-07-06T10:00:00Z",
      completed_at: null,
      created_at: "2026-07-06T10:00:00Z",
      updated_at: "2026-07-06T10:00:00Z",
    });
    mocks.getImportJob.mockResolvedValue({
      job_id: "00000000-0000-0000-0000-000000000007",
      status: "running",
      root_path: "/mnt/nas/current",
      requested_by: "admin",
      error_message: null,
      points_processed: null,
      canals_processed: null,
      meter_readings_linked: null,
      meter_readings_unlinked: null,
      started_at: "2026-07-06T10:00:00Z",
      completed_at: null,
      created_at: "2026-07-06T10:00:00Z",
      updated_at: "2026-07-06T10:00:30Z",
    });

    render(<CatastoDeliveryPointsConfigPage />);

    await screen.findByDisplayValue("/mnt/nas/current");
    fireEvent.click(screen.getByRole("button", { name: "Importa dal NAS" }));

    await waitFor(() => expect(mocks.getImportJob).toHaveBeenCalled(), { timeout: 4500 });
    expect(screen.getByRole("button", { name: "Import in corso..." })).toBeDisabled();
  }, 10000);

  test("shows explicit polling Error messages", async () => {
    mocks.getConfig.mockResolvedValue({
      root_path: "/mnt/nas/current",
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: "admin",
      updated_at: "2026-07-06T10:00:00Z",
    });
    mocks.runImport.mockResolvedValue({
      job_id: "00000000-0000-0000-0000-000000000008",
      status: "running",
      root_path: "/mnt/nas/current",
      requested_by: "admin",
      error_message: null,
      points_processed: null,
      canals_processed: null,
      meter_readings_linked: null,
      meter_readings_unlinked: null,
      started_at: "2026-07-06T10:00:00Z",
      completed_at: null,
      created_at: "2026-07-06T10:00:00Z",
      updated_at: "2026-07-06T10:00:00Z",
    });
    mocks.getImportJob.mockRejectedValue(new Error("Job non trovato"));

    render(<CatastoDeliveryPointsConfigPage />);

    await screen.findByDisplayValue("/mnt/nas/current");
    fireEvent.click(screen.getByRole("button", { name: "Importa dal NAS" }));

    await waitFor(() => expect(screen.getByText("Job non trovato")).toBeInTheDocument(), { timeout: 4500 });
  }, 10000);

  test("shows session error when token expires before polling", async () => {
    mocks.getStoredAccessToken.mockReset();
    mocks.getStoredAccessToken.mockReturnValueOnce("token-123").mockReturnValueOnce("token-123").mockReturnValue(null);
    mocks.getConfig.mockResolvedValue({
      root_path: "/mnt/nas/current",
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: "admin",
      updated_at: "2026-07-06T10:00:00Z",
    });
    mocks.runImport.mockResolvedValue({
      job_id: "00000000-0000-0000-0000-000000000005",
      status: "running",
      root_path: "/mnt/nas/current",
      requested_by: "admin",
      error_message: null,
      points_processed: null,
      canals_processed: null,
      meter_readings_linked: null,
      meter_readings_unlinked: null,
      started_at: "2026-07-06T10:00:00Z",
      completed_at: null,
      created_at: "2026-07-06T10:00:00Z",
      updated_at: "2026-07-06T10:00:00Z",
    });

    render(<CatastoDeliveryPointsConfigPage />);

    await screen.findByDisplayValue("/mnt/nas/current");
    fireEvent.click(screen.getByRole("button", { name: "Importa dal NAS" }));

    await screen.findByText("Sessione non disponibile.");
    expect(mocks.getImportJob).not.toHaveBeenCalled();
  });

  test("shows a session error when config load has no token", async () => {
    mocks.getStoredAccessToken.mockReturnValue(null);

    render(<CatastoDeliveryPointsConfigPage />);

    await screen.findByText("Operazione non completata");
    expect(screen.getByText("Sessione non disponibile.")).toBeInTheDocument();
    expect(mocks.getConfig).not.toHaveBeenCalled();
  });

  test("shows load errors and keeps fallback directory labels", async () => {
    mocks.getConfig.mockRejectedValue(new Error("NAS non raggiungibile"));

    render(<CatastoDeliveryPointsConfigPage />);

    await screen.findByText("NAS non raggiungibile");
    expect(screen.getByText("Punti_Cons-Con_contatoti")).toBeInTheDocument();
    expect(screen.getByText("Punti_Cons-Con_Senza_contatoti")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Importa dal NAS" })).toBeDisabled();
  });

  test("shows generic load error for non-error failures", async () => {
    mocks.getConfig.mockRejectedValue("failure");

    render(<CatastoDeliveryPointsConfigPage />);

    await screen.findByText("Errore caricamento configurazione.");
  });

  test("saves a blank path as null and renders unsaved config metadata", async () => {
    mocks.getConfig.mockResolvedValue({
      root_path: null,
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: null,
      updated_at: null,
    });
    mocks.updateConfig.mockResolvedValue({
      root_path: null,
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: null,
      updated_at: null,
    });

    render(<CatastoDeliveryPointsConfigPage />);

    const input = await screen.findByLabelText("Cartella sorgente NAS");
    expect(input).toHaveValue("");
    expect(screen.getByText("Configurazione non ancora salvata.")).toBeInTheDocument();

    fireEvent.change(input, { target: { value: "   " } });
    fireEvent.click(screen.getByRole("button", { name: "Salva configurazione" }));

    await waitFor(() => {
      expect(mocks.updateConfig).toHaveBeenCalledWith("token-123", { root_path: null });
    });
  });

  test("shows save errors and handles missing token on save", async () => {
    mocks.getConfig.mockResolvedValue({
      root_path: "/mnt/nas/current",
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: "admin",
      updated_at: "2026-07-06T10:00:00Z",
    });
    mocks.updateConfig.mockRejectedValue("failure");

    render(<CatastoDeliveryPointsConfigPage />);

    await screen.findByDisplayValue("/mnt/nas/current");
    fireEvent.click(screen.getByRole("button", { name: "Salva configurazione" }));

    await screen.findByText("Errore salvataggio configurazione.");

    mocks.updateConfig.mockReset();
    mocks.getStoredAccessToken.mockReturnValue(null);
    fireEvent.click(screen.getByRole("button", { name: "Salva configurazione" }));

    await screen.findByText("Sessione non disponibile.");
    expect(mocks.updateConfig).not.toHaveBeenCalled();
  });

  test("shows explicit save Error messages and null update timestamps", async () => {
    mocks.getConfig.mockResolvedValue({
      root_path: "/mnt/nas/current",
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: "admin",
      updated_at: null,
    });
    mocks.updateConfig.mockRejectedValue(new Error("Path NAS non valido"));

    render(<CatastoDeliveryPointsConfigPage />);

    await screen.findByText("admin · Mai");
    fireEvent.click(screen.getByRole("button", { name: "Salva configurazione" }));

    await screen.findByText("Path NAS non valido");
  });

  test("shows import errors and handles missing token on import", async () => {
    mocks.getConfig.mockResolvedValue({
      root_path: "/mnt/nas/current",
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: "admin",
      updated_at: "2026-07-06T10:00:00Z",
    });
    mocks.runImport.mockRejectedValue(new Error("Credenziali NAS non valide"));

    render(<CatastoDeliveryPointsConfigPage />);

    await screen.findByDisplayValue("/mnt/nas/current");
    fireEvent.click(screen.getByRole("button", { name: "Importa dal NAS" }));

    await screen.findByText("Credenziali NAS non valide");

    mocks.runImport.mockReset();
    mocks.getStoredAccessToken.mockReturnValue(null);
    fireEvent.click(screen.getByRole("button", { name: "Importa dal NAS" }));

    await screen.findByText("Sessione non disponibile.");
    expect(mocks.runImport).not.toHaveBeenCalled();
  });

  test("shows generic import error for non-error failures", async () => {
    mocks.getConfig.mockResolvedValue({
      root_path: "/mnt/nas/current",
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: "admin",
      updated_at: "2026-07-06T10:00:00Z",
    });
    mocks.runImport.mockRejectedValue("failure");

    render(<CatastoDeliveryPointsConfigPage />);

    await screen.findByDisplayValue("/mnt/nas/current");
    fireEvent.click(screen.getByRole("button", { name: "Importa dal NAS" }));

    await screen.findByText("Errore import punti di consegna.");
  });

  test("shows fallback import error when start response is failed without detail", async () => {
    mocks.getConfig.mockResolvedValue({
      root_path: "/mnt/nas/current",
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: "admin",
      updated_at: "2026-07-06T10:00:00Z",
    });
    mocks.runImport.mockResolvedValue({
      job_id: "00000000-0000-0000-0000-000000000004",
      status: "failed",
      root_path: "/mnt/nas/current",
      requested_by: "admin",
      error_message: null,
      points_processed: null,
      canals_processed: null,
      meter_readings_linked: null,
      meter_readings_unlinked: null,
      started_at: null,
      completed_at: "2026-07-06T10:00:00Z",
      created_at: "2026-07-06T10:00:00Z",
      updated_at: "2026-07-06T10:00:00Z",
    });

    render(<CatastoDeliveryPointsConfigPage />);

    await screen.findByDisplayValue("/mnt/nas/current");
    fireEvent.click(screen.getByRole("button", { name: "Importa dal NAS" }));

    await screen.findByText("Errore import punti di consegna.");
  });
});
