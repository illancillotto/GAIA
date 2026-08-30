import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { ElaborazioneRequestWorkspace } from "@/components/elaborazioni/request-workspace";
import { AutoSyncActivityDashboard } from "@/components/elaborazioni/autosync-activity-dashboard";
import { ContinuousCatastoSyncPanel } from "@/components/elaborazioni/continuous-catasto-sync-panel";

const api = vi.hoisted(() => ({
  updateConfig: vi.fn(),
  refreshSource: vi.fn(),
  runNow: vi.fn(),
  getCredentials: vi.fn(),
  getStatus: vi.fn(),
  token: "token" as string | null,
  config: {
  enabled: false,
  credential_id: null,
  credential_ids: ["credential-a"],
  primary_enabled: true,
  secondary_enabled: false,
  role_parcel_refresh_hours: 24,
  role_subject_refresh_hours: 48,
  consortium_parcel_refresh_hours: 720,
  registry_subject_refresh_hours: 720,
  batch_size: 20,
  source_watermarks: { target_count: 12 },
  last_planner_at: null,
  last_source_refresh_at: null,
  last_batch_started_at: null,
  last_error_message: null,
  updated_by_user_id: null,
  created_at: "2026-08-28T10:00:00Z",
  updated_at: "2026-08-28T10:00:00Z",
  },
}));

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: () => api.token }));
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getCatastoComuni: vi.fn().mockResolvedValue([]),
  getElaborazioneBatches: vi.fn().mockResolvedValue([]),
  getElaborazioneCredentials: (...args: unknown[]) => api.getCredentials(...args),
  getElaborazioneRuoloAutoSyncStatus: (...args: unknown[]) => api.getStatus(...args),
  updateElaborazioneRuoloAutoSyncConfig: (...args: unknown[]) => api.updateConfig(...args),
  refreshElaborazioneRuoloAutoSyncSource: (...args: unknown[]) => api.refreshSource(...args),
  runElaborazioneRuoloAutoSyncNow: (...args: unknown[]) => api.runNow(...args),
}));

describe("ElaborazioneRequestWorkspace continuous sync", () => {
  beforeEach(() => {
    api.token = "token";
    api.getCredentials.mockReset().mockResolvedValue({
      credentials: [
        { id: "credential-a", label: "Alessandro", sister_username: "ale", active: true },
        { id: "credential-b", label: "Marika", sister_username: "marika", active: true },
        { id: "credential-off", label: "Marco", sister_username: "marco", active: false },
      ],
      default_credential: null,
    });
    api.getStatus.mockReset().mockResolvedValue({
      config: api.config,
      counts: { total: 0, pending: 0, queued: 0, processing: 0, completed: 0, blocked_source: 0, blocked_runtime: 0 },
      running_batch: null,
      last_batch: null,
      error_items: [], recent_items: [],
      scope_counts: { ruolo_particella: { completed: 8, pending: 2 } },
      available_credential_ids: ["credential-a"],
      perpetual_error_items: [], perpetual_recent_items: [],
      dashboard: {
        summary: {
          period_hours: 24, batches_total: 4, batches_active: 1, batches_completed: 2, batches_failed: 1,
          requests_total: 40, requests_completed: 30, requests_failed: 3, requests_blocked: 2,
          documents_downloaded: 28, completed_per_hour: 6, average_batch_duration_seconds: 600,
          last_activity_at: "2026-08-30T09:00:00Z",
        },
        hourly: [{ hour: "2026-08-30T09:00:00Z", completed: 6, failed: 1, documents_downloaded: 5 }],
        recent_batches: [{
          id: "batch-1", user_id: 1, credential_id: null, credential_ids: ["credential-a"],
          name: "AutoSync operativo", batch_kind: "perpetual_sync", status: "processing", total_items: 20,
          completed_items: 12, failed_items: 1, skipped_items: 0, not_found_items: 0,
          source_filename: "perpetual_sync", current_operation: "Scaricamento visure", report_json_path: null,
          report_md_path: null, created_at: "2026-08-30T08:00:00Z", started_at: "2026-08-30T08:01:00Z", completed_at: null,
        }],
        events: [{
          timestamp: "2026-08-30T09:00:00Z", level: "error", title: "Visura bloccata",
          detail: "CAPTCHA richiesto", batch_id: "batch-1", request_id: "request-1",
        }],
      },
    });
    api.updateConfig.mockReset().mockResolvedValue({ ...api.config, enabled: true });
    api.refreshSource.mockReset().mockResolvedValue({ success: true, message: "Sorgenti aggiornate" });
    api.runNow.mockReset().mockResolvedValue({ success: true, message: "Micro-batch avviato" });
  });

  test("keeps configuration inputs disabled until the complete draft is loaded", () => {
    api.getCredentials.mockReturnValueOnce(new Promise(() => undefined));
    api.getStatus.mockReturnValueOnce(new Promise(() => undefined));

    render(<ContinuousCatastoSyncPanel />);

    const priorityInput = screen.getByRole("checkbox", { name: /Priorità 1/ });
    const roleParcelInput = screen.getByLabelText("Aggiorna particelle Ruolo ogni (ore)");
    expect(priorityInput).toBeDisabled();
    expect(roleParcelInput).toBeDisabled();
    fireEvent.change(roleParcelInput, { target: { value: "12" } });
    expect(roleParcelInput).toBeDisabled();
  });

  test("labels refresh intervals as hours and shows their duration in days", async () => {
    render(<ContinuousCatastoSyncPanel />);

    expect(await screen.findByText("Intervalli di aggiornamento")).toBeInTheDocument();
    expect(screen.getByLabelText("Aggiorna particelle Ruolo ogni (ore)")).toHaveValue(24);
    expect(screen.getByLabelText("Aggiorna soggetti Ruolo ogni (ore)")).toHaveValue(48);
    expect(screen.getByLabelText("Aggiorna particelle consorzio ogni (ore)")).toHaveValue(720);
    expect(screen.getByLabelText("Aggiorna soggetti anagrafe ogni (ore)")).toHaveValue(720);
    expect(screen.getByText("24 ore · 1 giorno")).toBeInTheDocument();
    expect(screen.getByText("48 ore · 2 giorni")).toBeInTheDocument();
    expect(screen.getAllByText("720 ore · 30 giorni")).toHaveLength(2);
  });

  test("shows the AutoSync operational dashboard above configuration", async () => {
    render(<ContinuousCatastoSyncPanel />);

    expect(await screen.findByText("Visure scaricate da SISTER")).toBeInTheDocument();
    expect(screen.getByText("Attività AutoSync")).toBeInTheDocument();
    expect(screen.getByText("Visure scaricate da SISTER").parentElement).toHaveTextContent("28");
    expect(screen.getByText("Velocità oraria").parentElement).toHaveTextContent("6");
    expect(screen.getByText("Andamento ultime 24 ore")).toBeInTheDocument();
    expect(screen.getByText("Ultimi batch AutoSync")).toBeInTheDocument();
    expect(screen.getByText("Blocchi ed errori")).toBeInTheDocument();
    expect(screen.getByText("CAPTCHA richiesto")).toBeInTheDocument();
    expect(screen.getByText("Configurazione AutoSync")).toBeInTheDocument();
    const dashboard = screen.getByText("Attività AutoSync").closest("section");
    const configuration = screen.getByText("Configurazione AutoSync").closest("section");
    expect(dashboard?.compareDocumentPosition(configuration as Node) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  test("covers empty, idle and informational dashboard states", async () => {
    const base = await api.getStatus();
    const empty = {
      ...base,
      config: { ...base.config, enabled: false, credential_ids: null, credential_id: "credential-a", last_source_refresh_at: null },
      dashboard: {
        summary: { ...base.dashboard.summary, batches_active: 0, average_batch_duration_seconds: null, last_activity_at: null },
        hourly: [], recent_batches: [], events: [],
      },
    };
    const { rerender } = render(<AutoSyncActivityDashboard credentials={[]} status={empty} />);
    expect(screen.getByText("Nessuna attività nelle ultime 24 ore.")).toBeInTheDocument();
    expect(screen.getByText("Nessun batch AutoSync presente.")).toBeInTheDocument();
    expect(screen.getByText("Durata media").parentElement).toHaveTextContent("—");
    expect(screen.getByText("Lock / concorrenza").parentElement).toHaveTextContent("Libero");

    const informative = {
      ...empty,
      config: { ...empty.config, credential_id: null, last_source_refresh_at: "2026-08-30T07:00:00Z" },
      running_batch: { ...base.dashboard.recent_batches[0], current_operation: null },
      dashboard: {
        ...empty.dashboard,
        summary: { ...empty.dashboard.summary, average_batch_duration_seconds: 7200 },
        recent_batches: [{ ...base.dashboard.recent_batches[0], name: null, current_operation: null, total_items: 0 }],
        events: [
          { timestamp: "2026-08-30T09:00:00Z", level: "warning", title: "Attesa", detail: null, batch_id: "batch-1", request_id: null },
          { timestamp: "2026-08-30T08:00:00Z", level: "info", title: "Planner eseguito", detail: null, batch_id: "batch-1", request_id: null },
        ],
      },
    };
    rerender(<AutoSyncActivityDashboard credentials={[]} status={informative} />);
    expect(screen.getByText("Durata media").parentElement).toHaveTextContent("2 h");
    expect(screen.getByText("Micro-batch AutoSync")).toBeInTheDocument();
    expect(screen.getByText("Planner eseguito")).toBeInTheDocument();

    rerender(<AutoSyncActivityDashboard credentials={[]} status={{ ...informative, dashboard: { ...informative.dashboard, summary: { ...informative.dashboard.summary, average_batch_duration_seconds: 30 } } }} />);
    expect(screen.getByText("Durata media").parentElement).toHaveTextContent("30s");
  });

  test("selects and deselects every active credential from the pool", async () => {
    render(<ContinuousCatastoSyncPanel />);

    expect(await screen.findByText("1 di 2 selezionate")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Seleziona tutte" }));
    expect(screen.getByRole("checkbox", { name: /Alessandro/ })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: /Marika/ })).toBeChecked();
    expect(screen.getByText("2 di 2 selezionate")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Deseleziona tutte" }));
    expect(screen.getByRole("checkbox", { name: /Alessandro/ })).not.toBeChecked();
    expect(screen.getByRole("checkbox", { name: /Marika/ })).not.toBeChecked();
    expect(screen.getByText("0 di 2 selezionate")).toBeInTheDocument();
  });

  test("configures a multi-credential pool and both priority levels", async () => {
    render(<ElaborazioneRequestWorkspace embedded initialMode="autosync" />);

    expect(await screen.findByText("Sincronizzazione catastale continua")).toBeInTheDocument();
    expect(screen.getByText("Particelle ruolo").parentElement).toHaveTextContent("8 / 10");
    fireEvent.click(screen.getByRole("checkbox", { name: /Marika/ }));
    fireEvent.click(screen.getByRole("checkbox", { name: /Priorità 2/ }));
    fireEvent.click(screen.getByRole("button", { name: "Metti su ON" }));

    await waitFor(() => expect(api.updateConfig).toHaveBeenCalled());
    expect(api.updateConfig.mock.calls[0][1]).toMatchObject({
      enabled: true,
      credential_ids: ["credential-a", "credential-b"],
      primary_enabled: true,
      secondary_enabled: true,
      batch_size: 20,
    });
  });

  test("re-enables refresh controls when the request exceeds the UI timeout", async () => {
    api.refreshSource.mockReturnValueOnce(new Promise(() => undefined));
    render(<ContinuousCatastoSyncPanel />);
    await screen.findByText("Sincronizzazione catastale continua");

    vi.useFakeTimers();
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna sorgente" }));
    expect(screen.getByRole("button", { name: "Aggiorna sorgente" })).toBeDisabled();
    await vi.advanceTimersByTimeAsync(30_000);
    vi.useRealTimers();

    expect(await screen.findByText(/tempo massimo/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aggiorna sorgente" })).not.toBeDisabled();
  });

  test("uses the continuous refresh and run endpoints", async () => {
    render(<ElaborazioneRequestWorkspace embedded initialMode="autosync" />);
    await screen.findByText("Sincronizzazione catastale continua");

    fireEvent.click(screen.getByRole("button", { name: "Aggiorna sorgente" }));
    await waitFor(() => expect(api.refreshSource).toHaveBeenCalledWith("token"));
    fireEvent.click(screen.getByRole("button", { name: "Esegui adesso" }));
    await waitFor(() => expect(api.runNow).toHaveBeenCalledWith("token"));
  });

  test("saves a changed pool without disabling an active sync", async () => {
    api.getStatus.mockResolvedValueOnce({
      ...(await api.getStatus()),
      config: { ...api.config, enabled: true },
    });
    render(<ContinuousCatastoSyncPanel />);
    await screen.findByText("Sincronizzazione catastale continua");
    fireEvent.click(screen.getByRole("checkbox", { name: /Marika/ }));
    fireEvent.click(screen.getByRole("button", { name: "Salva configurazione" }));
    await waitFor(() => expect(api.updateConfig).toHaveBeenCalledWith(
      "token",
      expect.objectContaining({ enabled: true, credential_ids: ["credential-a", "credential-b"] }),
    ));
  });

  test("renders active batch, subject and parcel items and disables the flow", async () => {
    api.getStatus.mockResolvedValue({
      ...(await api.getStatus()),
      config: { ...api.config, enabled: true, credential_ids: null, credential_id: "credential-a", last_source_refresh_at: "2026-08-28T10:00:00Z" },
      running_batch: { id: "batch", name: null, current_operation: null, status: "processing" },
      perpetual_error_items: [{ id: "subject", search_mode: "soggetto", subject_kind: null, subject_identifier: null, intestazione: null, attempt_count: 2, next_due_at: "2026-08-29T10:00:00Z", last_error_message: "timeout", status: "pending" }],
      perpetual_recent_items: [{ id: "parcel", search_mode: "immobile", comune: null, foglio: null, particella: null, attempt_count: 1, next_due_at: "2026-08-29T10:00:00Z", last_error_message: null, status: "completed" }],
    });
    render(<ContinuousCatastoSyncPanel />);
    expect(await screen.findByText("Micro-batch attivo")).toBeInTheDocument();
    expect(screen.getByText(/identificativo mancante/)).toBeInTheDocument();
    expect(screen.getByText(/Comune non risolto/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Metti su OFF" }));
    await waitFor(() => expect(api.updateConfig).toHaveBeenCalledWith("token", expect.objectContaining({ enabled: false })));
  });

  test("shows load and action failures", async () => {
    api.getCredentials.mockRejectedValueOnce(new Error("pool non disponibile"));
    const { unmount } = render(<ContinuousCatastoSyncPanel />);
    expect(await screen.findByText("pool non disponibile")).toBeInTheDocument();
    unmount();

    api.getCredentials.mockResolvedValue({ credentials: [{ id: "credential-a", label: "Alessandro", sister_username: "ale", active: true }] });
    api.refreshSource.mockRejectedValueOnce("errore generico");
    render(<ContinuousCatastoSyncPanel />);
    await screen.findByText("Sincronizzazione catastale continua");
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna sorgente" }));
    await waitFor(() => expect(screen.getAllByText("Errore sincronizzazione")).toHaveLength(2));
    api.refreshSource.mockRejectedValueOnce(new Error("errore specifico"));
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna sorgente" }));
    expect(await screen.findByText("errore specifico")).toBeInTheDocument();
  });

  test("handles empty token and edits SLA values", async () => {
    api.token = null;
    const { unmount } = render(<ContinuousCatastoSyncPanel />);
    expect(screen.getByText("Sincronizzazione catastale continua")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna sorgente" }));
    unmount();

    api.token = "token";
    render(<ContinuousCatastoSyncPanel />);
    await screen.findByText("Alessandro");
    fireEvent.click(screen.getByRole("checkbox", { name: /Priorità 1/ }));
    for (const label of ["Aggiorna particelle Ruolo ogni (ore)", "Aggiorna soggetti Ruolo ogni (ore)", "Aggiorna particelle consorzio ogni (ore)", "Aggiorna soggetti anagrafe ogni (ore)", "Righe per micro-batch"]) {
      fireEvent.change(screen.getByLabelText(label), { target: { value: "0" } });
    }
    fireEvent.change(screen.getByLabelText("Aggiorna particelle Ruolo ogni (ore)"), { target: { value: "12" } });
    fireEvent.click(screen.getByRole("checkbox", { name: /Alessandro/ }));
    expect(screen.getByRole("button", { name: "Esegui adesso" })).toBeDisabled();
  });

  test("supports an initially empty credential selection and non-error load rejection", async () => {
    api.getStatus.mockResolvedValueOnce({
      ...(await api.getStatus()),
      config: { ...api.config, credential_ids: null, credential_id: null },
      available_credential_ids: [],
    });
    const { unmount } = render(<ContinuousCatastoSyncPanel />);
    expect((await screen.findAllByText("Non disponibile")).length).toBeGreaterThan(0);
    unmount();
    api.getCredentials.mockRejectedValueOnce("load failure");
    render(<ContinuousCatastoSyncPanel />);
    expect(await screen.findByText("Errore caricamento sincronizzazione")).toBeInTheDocument();
  });

  test("ignores a late load failure after unmount", async () => {
    let rejectLoad: (reason: unknown) => void = () => undefined;
    api.getCredentials.mockImplementationOnce(() => new Promise((_resolve, reject) => { rejectLoad = reject; }));
    const { unmount } = render(<ContinuousCatastoSyncPanel />);
    unmount();
    rejectLoad(new Error("late failure"));
    await Promise.resolve();
  });
});
