import { StrictMode, type ComponentProps } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import type { ProtectedPageProps } from "@/components/app/protected-page";
import { ElaborazioniCapacitasWorkspace } from "@/components/elaborazioni/capacitas-workspace";
import type { CapacitasSection } from "@/components/elaborazioni/capacitas-workspace";
import type { ElaborazioneWorkspaceModal } from "@/components/elaborazioni/workspace-modal";
import type { CapacitasCredential } from "@/types/api";

const mocks = vi.hoisted(() => ({
  token: vi.fn(),
  credentials: vi.fn(),
  terreniJobs: vi.fn(),
  particelleJobs: vi.fn(),
  historyJobs: vi.fn(),
  incassJobs: vi.fn(),
  authError: vi.fn(),
  protectedProps: vi.fn(),
  modalProps: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));
vi.mock("@/lib/api", () => ({
  listCapacitasCredentials: mocks.credentials,
  listCapacitasTerreniJobs: mocks.terreniJobs,
  listCapacitasParticelleSyncJobs: mocks.particelleJobs,
  listCapacitasAnagraficaHistoryJobs: mocks.historyJobs,
  listCapacitasInCassSyncJobs: mocks.incassJobs,
  isAuthError: mocks.authError,
}));
vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: (props: ProtectedPageProps) => {
    mocks.protectedProps(props);
    return <section aria-label="Protected Capacitas frame">{props.children}</section>;
  },
}));
vi.mock("@/components/elaborazioni/workspace-modal", () => ({
  ElaborazioneWorkspaceModal: (props: ComponentProps<typeof ElaborazioneWorkspaceModal>) => {
    mocks.modalProps(props);
    return props.open ? (
      <section aria-label={props.title} role="dialog">
        <p>{props.description}</p>
        <a href={props.href ?? undefined}>Configurazione Capacitas</a>
        <button onClick={props.onClose} type="button">Chiudi credenziali</button>
      </section>
    ) : null;
  },
}));

const credentialSections: Array<{ id: CapacitasSection; tab: string; title: string }> = [
  { id: "particelle", tab: "Sync particelle", title: "Sincronizzazione progressiva particelle GAIA" },
  { id: "storico", tab: "Storico anagrafico", title: "Import storico anagrafiche Capacitas" },
  { id: "terreni", tab: "Terreni batch", title: "Lookup territorio e sync Terreni" },
  { id: "incass", tab: "Avvisi pagamenti", title: "Sincronizzazione avvisi di pagamento sugli utenti" },
];

function credential(id: number, active = true): CapacitasCredential {
  return {
    id,
    label: `Account ${id}`,
    username: `operator-${id}`,
    active,
    allowed_hours_start: 0,
    allowed_hours_end: 24,
    last_used_at: null,
    last_error: null,
    consecutive_failures: 0,
    created_at: "2026-10-08T12:00:00Z",
    updated_at: "2026-10-08T12:00:00Z",
  };
}

function deferred<Value>() {
  let resolve!: (value: Value) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<Value>((fulfill, fail) => {
    resolve = fulfill;
    reject = fail;
  });
  return { promise, resolve, reject };
}

function openSection(tab: string) {
  const navigation = screen.getByRole("navigation", { name: "Sezioni Capacitas" });
  fireEvent.click(within(navigation).getByRole("button", { name: new RegExp(`^${tab}`) }));
}

function primaryCredential(section: typeof credentialSections[number]) {
  openSection(section.tab);
  const panel = screen.getByText(section.title).closest("article");
  expect(panel).not.toBeNull();
  return within(panel!).getByRole("combobox", { name: "Credenziale" });
}

async function mountWorkspace(initialSection: CapacitasSection = "particelle") {
  const view = render(<ElaborazioniCapacitasWorkspace embedded initialSection={initialSection} />);
  await waitFor(() => expect(screen.getByText("Nessun job particelle registrato")).toBeInTheDocument());
  return view;
}

beforeEach(() => {
  vi.resetAllMocks();
  mocks.token.mockReturnValue("session-token");
  mocks.credentials.mockResolvedValue([]);
  mocks.terreniJobs.mockResolvedValue([]);
  mocks.particelleJobs.mockResolvedValue([]);
  mocks.historyJobs.mockResolvedValue([]);
  mocks.incassJobs.mockResolvedValue([]);
  mocks.authError.mockReturnValue(false);
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe("Capacitas credentials and workspace shell", () => {
  test("keeps backend selection for an empty credential pool across all four job forms", async () => {
    await mountWorkspace();
    expect(mocks.credentials).toHaveBeenCalledExactlyOnceWith("session-token");
    expect(screen.getByText("0/0")).toBeInTheDocument();
    for (const section of credentialSections) {
      const control = primaryCredential(section);
      expect(control).toHaveValue("");
      expect(within(control).getAllByRole("option")).toHaveLength(1);
      expect(within(control).getByRole("option", { name: "Auto-selezione backend" })).toHaveValue("");
    }
  });

  test.each([true, false])("selects a sole credential even when active=%s and counts activity separately", async (active) => {
    mocks.credentials.mockResolvedValue([credential(7, active)]);
    await mountWorkspace();
    expect(screen.getByText(active ? "1/1" : "0/1")).toBeInTheDocument();
    for (const section of credentialSections) {
      const control = primaryCredential(section);
      expect(control).toHaveValue("7");
      expect(within(control).getByRole("option", { name: "Account 7 · operator-7" })).toBeEnabled();
      expect(within(control).getAllByRole("option")).toHaveLength(2);
    }
    openSection("Storico anagrafico");
    const harvest = screen.getByText("Crea job massivi inCass dai soggetti a ruolo").closest("article");
    expect(within(harvest!).getByRole("combobox", { name: "Credenziale" })).toHaveValue("");
  });

  test.each([
    { active: [true, false], pool: "1/2" },
    { active: [true, true], pool: "2/2" },
    { active: [false, false], pool: "0/2" },
  ])("does not auto-select from multiple accounts in pool $pool", async ({ active, pool }) => {
    mocks.credentials.mockResolvedValue([credential(7, active[0]), credential(8, active[1])]);
    await mountWorkspace();
    expect(screen.getByText(pool)).toBeInTheDocument();
    for (const section of credentialSections) {
      const control = primaryCredential(section);
      expect(control).toHaveValue("");
      expect(within(control).getAllByRole("option").map((option) => option.textContent)).toEqual([
        "Auto-selezione backend", "Account 7 · operator-7", "Account 8 · operator-8",
      ]);
      expect(within(control).getByRole("option", { name: "Account 8 · operator-8" })).toBeEnabled();
    }
  });

  test("preserves independent manual credentials and backend delegation across navigation", async () => {
    mocks.credentials.mockResolvedValue([credential(7), credential(8, false)]);
    await mountWorkspace();
    const selectedIds = ["7", "8", "7", "8"];
    for (const [index, section] of credentialSections.entries()) {
      fireEvent.change(primaryCredential(section), { target: { value: selectedIds[index] } });
    }
    for (const [index, section] of credentialSections.entries()) {
      expect(primaryCredential(section)).toHaveValue(selectedIds[index]);
    }
    fireEvent.change(primaryCredential(credentialSections[0]), { target: { value: "" } });
    expect(primaryCredential(credentialSections[1])).toHaveValue("8");
    expect(primaryCredential(credentialSections[0])).toHaveValue("");
    expect(mocks.credentials).toHaveBeenCalledTimes(1);
  });

  test("preserves manual choices when the delayed StrictMode effect-replay response arrives", async () => {
    const replay = deferred<CapacitasCredential[]>();
    mocks.credentials.mockResolvedValueOnce([credential(7), credential(8)]).mockReturnValueOnce(replay.promise);
    render(<StrictMode><ElaborazioniCapacitasWorkspace embedded /></StrictMode>);
    await waitFor(() => expect(screen.getByText("2/2")).toBeInTheDocument());
    expect(mocks.credentials).toHaveBeenCalledTimes(2);
    const selectedIds = ["7", "8", "7", "8"];
    for (const [index, section] of credentialSections.entries()) {
      fireEvent.change(primaryCredential(section), { target: { value: selectedIds[index] } });
    }
    await act(async () => replay.resolve([credential(7, false), credential(8)]));
    expect(screen.getByText("1/2")).toBeInTheDocument();
    for (const [index, section] of credentialSections.entries()) {
      expect(primaryCredential(section)).toHaveValue(selectedIds[index]);
    }
  });

  test("applies a delayed initial singleton to every job form after section navigation", async () => {
    const initial = deferred<CapacitasCredential[]>();
    mocks.credentials.mockReturnValueOnce(initial.promise);
    await mountWorkspace();
    for (const section of credentialSections) expect(primaryCredential(section)).toHaveValue("");
    await act(async () => initial.resolve([credential(9)]));
    expect(screen.getByText("1/1")).toBeInTheDocument();
    for (const section of credentialSections) expect(primaryCredential(section)).toHaveValue("9");
  });

  test.each([
    { failure: new Error("Credential service unavailable"), message: "Credential service unavailable" },
    { failure: "non-error credential rejection", message: "Errore caricamento credenziali Capacitas" },
  ])("renders credential load failure: $message", async ({ failure, message }) => {
    const initial = deferred<CapacitasCredential[]>();
    mocks.credentials.mockReturnValueOnce(initial.promise);
    await mountWorkspace();
    await act(async () => initial.reject(failure));
    expect((await screen.findAllByText(message)).length).toBeGreaterThan(0);
    expect(screen.getByText("Errore operativo")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Apri Credenziali" })).not.toBeInTheDocument();
    expect(screen.getByText("0/0")).toBeInTheDocument();
    expect(primaryCredential(credentialSections[0])).toHaveValue("");
    expect(mocks.credentials).toHaveBeenCalledTimes(1);
  });

  test("clears an earlier credential error when the pending Terreni monitor succeeds", async () => {
    const monitor = deferred<[]>();
    mocks.terreniJobs.mockReturnValueOnce(monitor.promise);
    mocks.credentials.mockRejectedValueOnce(new Error("Credential pool unavailable"));
    render(<ElaborazioniCapacitasWorkspace embedded />);
    expect((await screen.findAllByText("Credential pool unavailable")).length).toBeGreaterThan(0);
    expect(screen.getByText("Errore operativo")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Apri Credenziali" })).not.toBeInTheDocument();
    await act(async () => monitor.resolve([]));
    expect(screen.queryByText("Credential pool unavailable")).not.toBeInTheDocument();
    expect(screen.queryByText("Errore operativo")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Apri Credenziali" })).toBeInTheDocument();
    expect(screen.getByText("0/0")).toBeInTheDocument();
    expect(mocks.credentials).toHaveBeenCalledTimes(1);
  });

  test("does not query any credential or job list without a GAIA token", async () => {
    mocks.token.mockReturnValue(null);
    render(<ElaborazioniCapacitasWorkspace embedded />);
    await act(async () => {});
    for (const list of [mocks.credentials, mocks.terreniJobs, mocks.particelleJobs, mocks.historyJobs, mocks.incassJobs]) {
      expect(list).not.toHaveBeenCalled();
    }
    expect(screen.getByText("0/0")).toBeInTheDocument();
    expect(screen.getByText("Sessione GAIA scaduta: il monitor particelle si ferma, ma i job backend gia avviati possono continuare.")).toBeInTheDocument();
    expect(primaryCredential(credentialSections[0])).toHaveValue("");
  });

  test("navigates to all six distinct panels without reloading credentials or job lists", async () => {
    await mountWorkspace();
    const panels = [
      ...credentialSections,
      { id: "certificati", tab: "Certificati", title: "Re-fetch certificati senza intestatari" },
      { id: "anomalie", tab: "Anomalie", title: "Anomalie — frazioni ambigue" },
    ];
    for (const panel of panels) {
      openSection(panel.tab);
      expect(screen.getByText(panel.title, { selector: "p" })).toBeInTheDocument();
      for (const other of panels.filter((candidate) => candidate.id !== panel.id)) {
        expect(screen.queryByText(other.title, { selector: "p" })).not.toBeInTheDocument();
      }
    }
    for (const list of [mocks.credentials, mocks.terreniJobs, mocks.particelleJobs, mocks.historyJobs]) {
      expect(list).toHaveBeenCalledExactlyOnceWith("session-token");
    }
    expect(mocks.incassJobs).toHaveBeenCalledExactlyOnceWith("session-token", { limit: 300 });
  });

  test("changes initialSection on rerender but retains the form selection and mount-only loading", async () => {
    mocks.credentials.mockResolvedValue([credential(7), credential(8)]);
    const view = await mountWorkspace();
    fireEvent.change(primaryCredential(credentialSections[0]), { target: { value: "8" } });
    openSection("Terreni batch");
    view.rerender(<ElaborazioniCapacitasWorkspace embedded initialSection="storico" />);
    expect(screen.getByText("Import storico anagrafiche Capacitas")).toBeInTheDocument();
    expect(screen.queryByText("Lookup territorio e sync Terreni")).not.toBeInTheDocument();
    view.rerender(<ElaborazioniCapacitasWorkspace embedded initialSection="particelle" />);
    const panel = screen.getByText("Sincronizzazione progressiva particelle GAIA").closest("article");
    expect(within(panel!).getByRole("combobox", { name: "Credenziale" })).toHaveValue("8");
    expect(mocks.credentials).toHaveBeenCalledTimes(1);
    for (const list of [mocks.terreniJobs, mocks.particelleJobs, mocks.historyJobs, mocks.incassJobs]) {
      expect(list).toHaveBeenCalledTimes(1);
    }
  });

  test.each([true, false])("opens and closes settings without replacing the workspace, embedded=%s", async (embedded) => {
    mocks.credentials.mockResolvedValue([credential(7), credential(8)]);
    render(<ElaborazioniCapacitasWorkspace embedded={embedded} />);
    await waitFor(() => expect(screen.getByText("2/2")).toBeInTheDocument());
    expect(screen.getByRole("heading", { name: embedded ? "Capacitas" : "Moduli Capacitas per GAIA" })).toBeInTheDocument();
    if (embedded) {
      expect(mocks.protectedProps).not.toHaveBeenCalled();
      expect(screen.queryByRole("region", { name: "Protected Capacitas frame" })).not.toBeInTheDocument();
    } else {
      expect(screen.getByRole("region", { name: "Protected Capacitas frame" })).toBeInTheDocument();
      expect(mocks.protectedProps).toHaveBeenLastCalledWith(expect.objectContaining({
        title: "Moduli Capacitas",
        description: "Workspace operativo per sincronizzazioni particelle, storico anagrafico, avvisi pagamento e job Terreni sui moduli Capacitas.",
        breadcrumb: "Elaborazioni / Capacitas",
        requiredModule: "catasto",
      }));
    }
    fireEvent.change(primaryCredential(credentialSections[0]), { target: { value: "8" } });
    expect(screen.queryByRole("dialog", { name: "Credenziali" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Apri Credenziali" }));
    const dialog = screen.getByRole("dialog", { name: "Credenziali" });
    expect(within(dialog).getByRole("link", { name: "Configurazione Capacitas" })).toHaveAttribute("href", "/elaborazioni/settings");
    expect(within(dialog).getByText("Configurazione credenziali aperta in modale per mantenere il contesto della ricerca Capacitas.")).toBeInTheDocument();
    expect(screen.getByText("Sincronizzazione progressiva particelle GAIA")).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "Chiudi credenziali" }));
    expect(screen.queryByRole("dialog", { name: "Credenziali" })).not.toBeInTheDocument();
    expect(primaryCredential(credentialSections[0])).toHaveValue("8");
    expect(mocks.modalProps).toHaveBeenLastCalledWith(expect.objectContaining({ open: false }));
    expect(mocks.credentials).toHaveBeenCalledTimes(1);
    for (const list of [mocks.terreniJobs, mocks.particelleJobs, mocks.historyJobs, mocks.incassJobs]) {
      expect(list).toHaveBeenCalledTimes(1);
    }
  });
});
