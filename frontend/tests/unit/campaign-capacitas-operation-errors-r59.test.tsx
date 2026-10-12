import type { ReactNode } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ElaborazioniCapacitasWorkspace } from "@/components/elaborazioni/capacitas-workspace";
import type { CapacitasSection } from "@/components/elaborazioni/capacitas-workspace";
import type * as CapacitasApi from "@/lib/api";
import type { CapacitasParticelleSyncJob, CapacitasParticelleSyncJobResult } from "@/types/api";

const mocks = vi.hoisted(() => ({
  token: vi.fn<() => string | null>(),
  credentials: vi.fn<typeof CapacitasApi.listCapacitasCredentials>(),
  terreniJobs: vi.fn<typeof CapacitasApi.listCapacitasTerreniJobs>(),
  particelleJobs: vi.fn<typeof CapacitasApi.listCapacitasParticelleSyncJobs>(),
  historyJobs: vi.fn<typeof CapacitasApi.listCapacitasAnagraficaHistoryJobs>(),
  incassJobs: vi.fn<typeof CapacitasApi.listCapacitasInCassSyncJobs>(),
  createParticelle: vi.fn<typeof CapacitasApi.createCapacitasParticelleSyncJob>(),
  speed: vi.fn<typeof CapacitasApi.patchCapacitasParticelleSyncJobSpeed>(),
  stop: vi.fn<typeof CapacitasApi.stopCapacitasParticelleSyncJob>(),
  createTerreni: vi.fn<typeof CapacitasApi.createCapacitasTerreniJob>(),
  createHistory: vi.fn<typeof CapacitasApi.createCapacitasAnagraficaHistoryJob>(),
  createIncass: vi.fn<typeof CapacitasApi.createCapacitasInCassSyncJob>(),
  harvest: vi.fn<typeof CapacitasApi.createCapacitasInCassRuoloHarvest>(),
  refetch: vi.fn<typeof CapacitasApi.refetchCapacitasCertificatiEmpty>(),
  anomalie: vi.fn<typeof CapacitasApi.listCapacitasParticelleAnomalie>(),
  authError: vi.fn<typeof CapacitasApi.isAuthError>(),
  fileRead: vi.fn<() => Promise<string>>(),
}));

vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));
vi.mock("@/lib/api", () => ({
  listCapacitasCredentials: mocks.credentials,
  listCapacitasTerreniJobs: mocks.terreniJobs,
  listCapacitasParticelleSyncJobs: mocks.particelleJobs,
  listCapacitasAnagraficaHistoryJobs: mocks.historyJobs,
  listCapacitasInCassSyncJobs: mocks.incassJobs,
  createCapacitasParticelleSyncJob: mocks.createParticelle,
  patchCapacitasParticelleSyncJobSpeed: mocks.speed,
  stopCapacitasParticelleSyncJob: mocks.stop,
  createCapacitasTerreniJob: mocks.createTerreni,
  createCapacitasAnagraficaHistoryJob: mocks.createHistory,
  createCapacitasInCassSyncJob: mocks.createIncass,
  createCapacitasInCassRuoloHarvest: mocks.harvest,
  refetchCapacitasCertificatiEmpty: mocks.refetch,
  listCapacitasParticelleAnomalie: mocks.anomalie,
  isAuthError: mocks.authError,
}));
vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children }: { children: ReactNode }) => <>{children}</>,
}));
vi.mock("@/components/elaborazioni/workspace-modal", () => ({
  ElaborazioneWorkspaceModal: () => null,
}));

function activeParticelleJob(): CapacitasParticelleSyncJob {
  const result: CapacitasParticelleSyncJobResult = {
    mode: "progressive",
    total_items: 10,
    processed_items: 2,
    success_items: 2,
    failed_items: 0,
    skipped_items: 0,
    progress_percent: 20,
    current_label: "Unchanged public row",
    throttle_ms: 900,
    aggressive_window: false,
    recheck_hours: 72,
    speed_multiplier: 1,
    parallel_workers: 1,
    recent_items: [],
  };
  return {
    id: 31,
    credential_id: null,
    requested_by_user_id: null,
    status: "processing",
    mode: "progressive",
    payload_json: null,
    result_json: result,
    error_detail: null,
    started_at: "2026-10-08T08:00:00Z",
    completed_at: null,
    created_at: "2026-10-08T07:59:00Z",
    updated_at: "2026-10-08T08:10:00Z",
  };
}

function chooseFile() {
  const file = new File([], "operation.csv", { type: "text/csv" });
  Object.defineProperty(file, "text", { value: mocks.fileRead });
  fireEvent.change(screen.getByLabelText("File batch"), { target: { files: [file] } });
}

function clickButton(name: string) {
  fireEvent.click(screen.getByRole("button", { name }));
}

function assertEnabled(name: string) {
  expect(screen.getByRole("button", { name })).toBeEnabled();
}

function showIncassFeedback() {
  const navigation = screen.getByRole("navigation", { name: "Sezioni Capacitas" });
  fireEvent.click(within(navigation).getByRole("button", { name: /^Avvisi pagamenti/ }));
}

interface Operation {
  id: string;
  section: CapacitasSection;
  fallback: string;
  reject: (failure: unknown) => void;
  prepare?: () => Promise<void>;
  trigger?: () => void;
  assertSettled: () => void;
  showFeedback?: () => void;
}

let rejectCredentials: (() => void) | undefined;

const operations: Operation[] = [
  {
    id: "credential loading",
    section: "terreni",
    fallback: "Errore caricamento credenziali Capacitas",
    reject: (failure) => {
      const pending = new Promise<Awaited<ReturnType<typeof CapacitasApi.listCapacitasCredentials>>>((_resolve, reject) => {
        rejectCredentials = () => { reject(failure); };
      });
      mocks.credentials.mockReturnValueOnce(pending);
    },
    trigger: () => { rejectCredentials?.(); },
    assertSettled: () => {
      expect(mocks.credentials).toHaveBeenCalledExactlyOnceWith("session-token");
      expect(screen.getByText("Nessun job registrato")).toBeInTheDocument();
    },
  },
  {
    id: "Particelle creation",
    section: "particelle",
    fallback: "Errore avvio job particelle",
    reject: (failure) => { mocks.createParticelle.mockRejectedValueOnce(failure); },
    trigger: () => { clickButton("Avvia sync progressiva"); },
    assertSettled: () => {
      expect(mocks.createParticelle).toHaveBeenCalledTimes(1);
      assertEnabled("Avvia sync progressiva");
    },
  },
  {
    id: "Particelle speed",
    section: "particelle",
    fallback: "Errore cambio velocità job",
    reject: (failure) => { mocks.speed.mockRejectedValueOnce(failure); },
    trigger: () => { clickButton("Doppia velocità"); },
    assertSettled: () => {
      expect(mocks.speed).toHaveBeenCalledExactlyOnceWith("session-token", 31, true);
      assertEnabled("Doppia velocità");
      assertEnabled("Standard");
      expect(screen.getByText(/Unchanged public row/)).toBeInTheDocument();
    },
  },
  {
    id: "Particelle stop",
    section: "particelle",
    fallback: "Errore stop job",
    reject: (failure) => { mocks.stop.mockRejectedValueOnce(failure); },
    trigger: () => { clickButton("Stop"); },
    assertSettled: () => {
      expect(mocks.stop).toHaveBeenCalledExactlyOnceWith("session-token", 31);
      assertEnabled("Stop");
      expect(screen.getByText(/Unchanged public row/)).toBeInTheDocument();
    },
  },
  {
    id: "Terreni file parsing",
    section: "terreni",
    fallback: "Errore parsing file Terreni",
    reject: (failure) => { mocks.fileRead.mockRejectedValueOnce(failure); },
    trigger: chooseFile,
    assertSettled: () => {
      expect(mocks.fileRead).toHaveBeenCalledTimes(1);
      expect(screen.getByLabelText("File batch")).toBeEnabled();
      expect(screen.getByRole("button", { name: "Avvia job batch" })).toBeDisabled();
      expect(mocks.createTerreni).not.toHaveBeenCalled();
    },
  },
  {
    id: "Terreni batch creation",
    section: "terreni",
    fallback: "Errore avvio job batch Terreni",
    reject: (failure) => { mocks.createTerreni.mockRejectedValueOnce(failure); },
    prepare: async () => {
      await act(async () => { chooseFile(); });
      await waitFor(() => { assertEnabled("Avvia job batch"); });
    },
    trigger: () => { clickButton("Avvia job batch"); },
    assertSettled: () => {
      expect(mocks.createTerreni).toHaveBeenCalledTimes(1);
      assertEnabled("Avvia job batch");
    },
  },
  {
    id: "History file parsing",
    section: "storico",
    fallback: "Errore parsing file storico anagrafico",
    reject: (failure) => { mocks.fileRead.mockRejectedValueOnce(failure); },
    prepare: async () => { clickButton("Batch da file"); },
    trigger: chooseFile,
    assertSettled: () => {
      expect(mocks.fileRead).toHaveBeenCalledTimes(1);
      expect(screen.getByLabelText("File batch")).toBeEnabled();
      expect(screen.getByRole("button", { name: "Avvia import storico" })).toBeDisabled();
      expect(mocks.createHistory).not.toHaveBeenCalled();
    },
  },
  {
    id: "History import",
    section: "storico",
    fallback: "Errore import storico anagrafico",
    reject: (failure) => { mocks.createHistory.mockRejectedValueOnce(failure); },
    prepare: async () => {
      fireEvent.change(screen.getByLabelText("Lista subject_id"), {
        target: { value: "00000000-0000-4000-8000-000000000001" },
      });
    },
    trigger: () => { clickButton("Avvia import storico"); },
    assertSettled: () => {
      expect(mocks.createHistory).toHaveBeenCalledTimes(1);
      assertEnabled("Avvia import storico");
      expect(screen.getByLabelText("Lista subject_id")).toHaveValue("00000000-0000-4000-8000-000000000001");
    },
  },
  {
    id: "INCASS sync creation",
    section: "incass",
    fallback: "Errore avvio job avvisi",
    reject: (failure) => { mocks.createIncass.mockRejectedValueOnce(failure); },
    trigger: () => { clickButton("Avvia sync avvisi"); },
    assertSettled: () => {
      expect(mocks.createIncass).toHaveBeenCalledTimes(1);
      assertEnabled("Avvia sync avvisi");
    },
  },
  {
    id: "INCASS harvest creation",
    section: "storico",
    fallback: "Errore creazione job harvest inCass",
    reject: (failure) => { mocks.harvest.mockRejectedValueOnce(failure); },
    trigger: () => { clickButton("Crea batch job da ruolo"); },
    assertSettled: () => {
      expect(mocks.harvest).toHaveBeenCalledTimes(1);
      assertEnabled("Crea batch job da ruolo");
    },
    showFeedback: showIncassFeedback,
  },
  {
    id: "Certificati re-fetch",
    section: "certificati",
    fallback: "Errore durante il re-fetch.",
    reject: (failure) => { mocks.refetch.mockRejectedValueOnce(failure); },
    trigger: () => { clickButton("Avvia re-fetch"); },
    assertSettled: () => {
      expect(mocks.refetch).toHaveBeenCalledTimes(1);
      assertEnabled("Avvia re-fetch");
      expect(screen.queryByText("Ri-fetchati")).not.toBeInTheDocument();
      expect(mocks.authError).toHaveBeenCalledTimes(1);
    },
  },
  {
    id: "Anomalie refresh",
    section: "anomalie",
    fallback: "Errore caricamento anomalie",
    reject: (failure) => { mocks.anomalie.mockRejectedValueOnce(failure); },
    trigger: () => { clickButton("Aggiorna lista"); },
    assertSettled: () => {
      expect(mocks.anomalie).toHaveBeenCalledExactlyOnceWith("session-token");
      assertEnabled("Aggiorna lista");
      expect(screen.getByText("Nessuna anomalia")).toBeInTheDocument();
    },
  },
];

type FailureKind = "Error getter" | "empty Error getter" | "non-Error message getter" | "null";
const failureKinds: FailureKind[] = ["Error getter", "empty Error getter", "non-Error message getter", "null"];

function failureCase(kind: FailureKind) {
  const message = vi.fn<() => string>().mockReturnValue(kind === "empty Error getter" ? "" : "R59 backend message");
  const failure: unknown = kind === "null" ? null : kind === "non-Error message getter" ? {} : new Error();
  if (failure !== null) Object.defineProperty(failure, "message", { get: message });
  return { failure, message };
}

async function mount(section: CapacitasSection) {
  await act(async () => { render(<ElaborazioniCapacitasWorkspace embedded initialSection={section} />); });
  expect(mocks.credentials).toHaveBeenCalledTimes(1);
  expect(mocks.terreniJobs).toHaveBeenCalledTimes(1);
  expect(mocks.particelleJobs).toHaveBeenCalledTimes(1);
  expect(mocks.historyJobs).toHaveBeenCalledTimes(1);
  expect(mocks.incassJobs).toHaveBeenCalledTimes(1);
}

beforeEach(() => {
  vi.resetAllMocks();
  rejectCredentials = undefined;
  mocks.token.mockReturnValue("session-token");
  mocks.credentials.mockResolvedValue([]);
  mocks.terreniJobs.mockResolvedValue([]);
  mocks.particelleJobs.mockResolvedValue([activeParticelleJob()]);
  mocks.historyJobs.mockResolvedValue([]);
  mocks.incassJobs.mockResolvedValue([]);
  mocks.authError.mockReturnValue(false);
  mocks.fileRead.mockResolvedValue("comune,foglio,particella\nUras,1,680");
});

afterEach(() => { cleanup(); });

describe("Capacitas fixed-fallback operation feedback R59", () => {
  for (const operation of operations) {
    test.each(failureKinds)(`${operation.id} preserves %s feedback and settles without monitor refresh`, async (kind) => {
      const { failure, message } = failureCase(kind);
      operation.reject(failure);
      await mount(operation.section);
      await operation.prepare?.();
      await act(async () => { operation.trigger?.(); });
      await waitFor(operation.assertSettled);
      operation.showFeedback?.();

      if (kind === "Error getter") {
        const notices = screen.getAllByText("R59 backend message");
        for (const notice of notices) expect(notice).toBeVisible();
        expect(screen.queryByText(operation.fallback)).not.toBeInTheDocument();
        expect(message).toHaveBeenCalledTimes(1);
      } else if (kind === "empty Error getter") {
        expect(screen.queryByText(operation.fallback)).not.toBeInTheDocument();
        expect(screen.queryByText("R59 backend message")).not.toBeInTheDocument();
        expect(message).toHaveBeenCalledTimes(1);
      } else {
        const notices = screen.getAllByText(operation.fallback);
        for (const notice of notices) expect(notice).toBeVisible();
        expect(screen.queryByText("R59 backend message")).not.toBeInTheDocument();
        expect(message).not.toHaveBeenCalled();
      }

      expect(mocks.terreniJobs).toHaveBeenCalledTimes(1);
      expect(mocks.particelleJobs).toHaveBeenCalledTimes(1);
      expect(mocks.historyJobs).toHaveBeenCalledTimes(1);
      expect(mocks.incassJobs).toHaveBeenCalledTimes(1);
      if (operation.id !== "Certificati re-fetch") expect(mocks.authError).not.toHaveBeenCalled();
    });
  }

  test("re-fetch auth classification bypasses Error.message and literal fallback before busy cleanup", async () => {
    const { failure, message } = failureCase("Error getter");
    mocks.refetch.mockRejectedValueOnce(failure);
    mocks.authError.mockReturnValue(true);
    await mount("certificati");
    await act(async () => { clickButton("Avvia re-fetch"); });
    expect(screen.getByText("Sessione GAIA scaduta. Rientra per riprovare.")).toBeVisible();
    expect(screen.queryByText("Errore durante il re-fetch.")).not.toBeInTheDocument();
    expect(screen.queryByText("R59 backend message")).not.toBeInTheDocument();
    expect(message).not.toHaveBeenCalled();
    expect(mocks.authError).toHaveBeenCalledExactlyOnceWith(failure);
    assertEnabled("Avvia re-fetch");
  });
});
