import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import {
  CapacitasTestDialog,
  ConfirmDeleteDialog,
  DetailCard,
  ElaborazioniSettingsWorkspace,
  StatCard,
  StatusBanner,
  type CapacitasTestDialogState,
  type ConfirmDeleteDialogState,
} from "@/components/elaborazioni/settings-workspace";
import { ApiError } from "@/lib/api";
import type {
  BonificaOristaneseCredential,
  CapacitasCredential,
  ElaborazioneCredential,
  ElaborazioneCredentialTestResult,
} from "@/types/api";

const apiMocks = vi.hoisted(() => ({
  createBonificaOristaneseCredential: vi.fn(),
  createCapacitasCredential: vi.fn(),
  createElaborazioneCredentialTestWebSocket: vi.fn(),
  deleteBonificaOristaneseCredential: vi.fn(),
  deleteCapacitasCredential: vi.fn(),
  deleteElaborazioneCredential: vi.fn(),
  getElaborazioneBatches: vi.fn(),
  getElaborazioneCredentialTest: vi.fn(),
  getElaborazioneCredentials: vi.fn(),
  listBonificaOristaneseCredentials: vi.fn(),
  listCapacitasCredentials: vi.fn(),
  releaseElaborazioneCredentials: vi.fn(),
  saveElaborazioneCredentials: vi.fn(),
  startElaborazioneBatch: vi.fn(),
  testBonificaOristaneseCredential: vi.fn(),
  testCapacitasCredential: vi.fn(),
  testElaborazioneCredentials: vi.fn(),
  updateBonificaOristaneseCredential: vi.fn(),
  updateCapacitasCredential: vi.fn(),
  updateElaborazioneCredential: vi.fn(),
}));

const authState = vi.hoisted(() => ({ token: "token" as string | null }));

vi.mock("@/lib/api", () => ({
  ApiError: class ApiError extends Error {
    status: number | null = null;
    detailData: unknown = null;
  },
  ...apiMocks,
}));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: () => authState.token }));
vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children, title }: { children: ReactNode; title: string }) => (
    <main>
      <h1>{title}</h1>
      {children}
    </main>
  ),
}));

function credential(id: string, overrides: Partial<ElaborazioneCredential> = {}): ElaborazioneCredential {
  return {
    id,
    user_id: 1,
    label: `Profilo ${id}`,
    sister_username: `user-${id}`,
    convenzione: "CONSORZIO DI BONIFICA DELL'ORISTANESE",
    codice_richiesta: `CODE-${id}`,
    ufficio_provinciale: "ORISTANO Territorio",
    active: true,
    is_default: false,
    schedule_enabled: false,
    availability_schedule: null,
    verified_at: null,
    created_at: "2026-08-20T08:00:00Z",
    updated_at: "2026-08-20T08:00:00Z",
    ...overrides,
  };
}

function testResult(id: string, credentialId: string): ElaborazioneCredentialTestResult {
  return {
    id,
    credential_id: credentialId,
    status: "completed",
    success: true,
    mode: "worker",
    reachable: true,
    authenticated: true,
    message: `Autenticazione ${credentialId} confermata`,
    verified_at: "2026-08-20T08:05:00Z",
    created_at: "2026-08-20T08:00:00Z",
    started_at: "2026-08-20T08:01:00Z",
    completed_at: "2026-08-20T08:05:00Z",
  };
}

function bonificaCredential(
  id: number,
  overrides: Partial<BonificaOristaneseCredential> = {},
): BonificaOristaneseCredential {
  return {
    id,
    label: `Bonifica ${id}`,
    login_identifier: `bonifica-${id}@example.test`,
    remember_me: false,
    active: true,
    last_used_at: null,
    last_authenticated_url: null,
    last_error: null,
    consecutive_failures: 0,
    created_at: "2026-08-20T08:00:00Z",
    updated_at: "2026-08-20T08:00:00Z",
    ...overrides,
  };
}

function capacitasCredential(id: number, overrides: Partial<CapacitasCredential> = {}): CapacitasCredential {
  return {
    id,
    label: `Capacitas ${id}`,
    username: `capacitas-${id}`,
    active: true,
    allowed_hours_start: 8,
    allowed_hours_end: 18,
    last_used_at: null,
    last_error: null,
    consecutive_failures: 0,
    created_at: "2026-08-20T08:00:00Z",
    updated_at: "2026-08-20T08:00:00Z",
    ...overrides,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

describe("ElaborazioniSettingsWorkspace SISTER integration", () => {
  beforeEach(() => {
    authState.token = "token";
    Object.values(apiMocks).forEach((mock) => mock.mockReset());
    const primary = credential("primary", { is_default: true, verified_at: "2026-08-19T10:00:00Z" });
    const secondary = credential("secondary", { active: false });
    apiMocks.getElaborazioneCredentials.mockResolvedValue({
      configured: true,
      credentials: [primary, secondary],
      default_credential: primary,
      credential: primary,
    });
    apiMocks.getElaborazioneBatches.mockResolvedValue([]);
    apiMocks.listBonificaOristaneseCredentials.mockResolvedValue([]);
    apiMocks.listCapacitasCredentials.mockResolvedValue([]);
    apiMocks.createElaborazioneCredentialTestWebSocket.mockReturnValue(null);
    apiMocks.updateElaborazioneCredential.mockImplementation(async (_token: string, id: string) =>
      id === "primary" ? primary : secondary,
    );
    apiMocks.deleteElaborazioneCredential.mockResolvedValue({ message: "deleted" });
    apiMocks.releaseElaborazioneCredentials.mockResolvedValue({ message: "Sessioni liberate" });
    apiMocks.testElaborazioneCredentials.mockImplementation(async (_token: string, payload: { credential_id: string }) =>
      testResult(`test-${payload.credential_id}`, payload.credential_id),
    );
  });

  test("covers the reusable status and dialog presentations", () => {
    const { rerender } = render(
      <>
        <StatCard eyebrow="Default" value="1" description="default" />
        <StatCard compact eyebrow="Success" value="2" description="success" tone="success" />
        <StatCard eyebrow="Warning" value="3" description="warning" tone="warning" />
        <StatusBanner tone="danger" title="Danger" description="danger" />
        <StatusBanner compact tone="success" title="Success" description="success" />
        <StatusBanner tone="warning" title="Warning banner" description="warning" />
        <StatusBanner tone="info" title="Info" description="info" />
        <DetailCard label="Missing" value={undefined} />
        <DetailCard label="Blank" value=" " />
        <DetailCard label="Value" value="present" />
      </>,
    );
    expect(screen.getByText("Info")).toBeInTheDocument();
    expect(screen.getByText("present")).toBeInTheDocument();

    const closedDelete: ConfirmDeleteDialogState = {
      open: false,
      kind: "sister",
      credentialId: null,
      label: null,
      busy: false,
      error: null,
    };
    rerender(<ConfirmDeleteDialog state={closedDelete} onCancel={vi.fn()} onConfirm={vi.fn()} />);
    expect(screen.queryByText("Conferma eliminazione")).not.toBeInTheDocument();

    const cancel = vi.fn();
    const confirm = vi.fn();
    rerender(
      <ConfirmDeleteDialog
        state={{ ...closedDelete, open: true, kind: "whitecompany", error: "delete error" }}
        onCancel={cancel}
        onConfirm={confirm}
      />,
    );
    expect(screen.getByText(/credenziale WhiteCompany/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Annulla" }));
    fireEvent.click(screen.getByRole("button", { name: "Elimina" }));
    expect(cancel).toHaveBeenCalled();
    expect(confirm).toHaveBeenCalled();

    rerender(
      <ConfirmDeleteDialog
        state={{ ...closedDelete, open: true, kind: "capacitas", credentialId: 1, label: "Account", busy: true }}
        onCancel={cancel}
        onConfirm={confirm}
      />,
    );
    expect(screen.getByText(/credenziale Capacitas/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Elimino..." })).toBeDisabled();

    const closedTest: CapacitasTestDialogState = {
      open: false,
      phase: "idle",
      credential: null,
      startedAt: null,
      finishedAt: null,
      statusCode: null,
      title: "Closed",
      summary: "closed",
      backendDetail: null,
      tokenPreview: null,
      diagnosis: null,
    };
    rerender(<CapacitasTestDialog state={closedTest} onClose={vi.fn()} />);
    expect(screen.queryByText("Test credenziale Capacitas")).not.toBeInTheDocument();

    rerender(<CapacitasTestDialog state={{ ...closedTest, open: true, phase: "error" }} onClose={vi.fn()} />);
    expect(screen.getByText("Nessun dettaglio aggiuntivo restituito dal backend.")).toBeInTheDocument();
    expect(screen.getByText("Nessuna diagnosi aggiuntiva disponibile.")).toBeInTheDocument();

    const close = vi.fn();
    rerender(
      <CapacitasTestDialog
        state={{
          ...closedTest,
          open: true,
          phase: "success",
          credential: capacitasCredential(1),
          statusCode: 200,
          backendDetail: "detail",
          tokenPreview: "token",
          diagnosis: "diagnosis",
        }}
        onClose={close}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    expect(close).toHaveBeenCalled();
  });

  test("loads the responsive pool and wires bulk, edit, default and delete actions", async () => {
    render(<ElaborazioniSettingsWorkspace embedded />);

    expect(await screen.findByText("Profilo primary")).toBeInTheDocument();
    expect(screen.getByText("Profilo secondary")).toBeInTheDocument();
    expect(screen.getByText("1/2 attive")).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Elenco credenziali SISTER" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Editor credenziale SISTER" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Testa tutte (2)" }));
    expect(await screen.findByText("Verifica del pool completata")).toBeInTheDocument();
    expect(apiMocks.testElaborazioneCredentials.mock.calls.map((call) => call[1])).toEqual([
      { credential_id: "primary" },
      { credential_id: "secondary" },
    ]);

    const primaryCard = screen.getByText("Profilo primary").closest("article");
    fireEvent.click(within(primaryCard!).getByRole("button", { name: "Testa" }));
    await waitFor(() => expect(apiMocks.testElaborazioneCredentials).toHaveBeenLastCalledWith("token", { credential_id: "primary" }));
    fireEvent.click(within(primaryCard!).getByRole("button", { name: "Pausa e libera" }));
    await waitFor(() => expect(apiMocks.updateElaborazioneCredential).toHaveBeenCalledWith("token", "primary", { active: false }));

    const secondaryCard = screen.getByText("Profilo secondary").closest("article");
    expect(secondaryCard).not.toBeNull();
    fireEvent.click(within(secondaryCard!).getByRole("button", { name: "Modifica" }));
    expect(screen.getByPlaceholderText("Codice fiscale / username")).toHaveValue("user-secondary");

    fireEvent.click(screen.getAllByRole("button", { name: "Elimina" })[0]);
    let dialog = screen.getByText("Conferma eliminazione").closest("div.fixed");
    fireEvent.click(within(dialog!).getByRole("button", { name: "Annulla" }));

    fireEvent.click(within(secondaryCard!).getByRole("button", { name: "Rendi default" }));
    await waitFor(() =>
      expect(apiMocks.updateElaborazioneCredential).toHaveBeenCalledWith("token", "secondary", {
        is_default: true,
        active: true,
      }),
    );

    fireEvent.click(within(secondaryCard!).getByRole("button", { name: "Elimina" }));
    expect(screen.getByText("Conferma eliminazione")).toBeInTheDocument();
    dialog = screen.getByText("Conferma eliminazione").closest("div.fixed");
    fireEvent.click(within(dialog!).getByRole("button", { name: "Elimina" }));
    await waitFor(() => expect(apiMocks.deleteElaborazioneCredential).toHaveBeenCalledWith("token", "secondary"));
  });

  test("keeps the page wrapper and individual form test connected", async () => {
    render(<ElaborazioniSettingsWorkspace />);

    expect(await screen.findByRole("heading", { name: "Credenziali" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Testa connessione" }));
    await waitFor(() =>
      expect(apiMocks.testElaborazioneCredentials).toHaveBeenCalledWith("token", { credential_id: "primary" }),
    );
    expect(await screen.findByText("Autenticazione confermata")).toBeInTheDocument();

    const resetButton = screen.getByRole("button", { name: "Nuova credenziale" });
    fireEvent.click(resetButton);
    fireEvent.change(screen.getByPlaceholderText("Codice fiscale / username"), { target: { value: "new-user" } });
    fireEvent.change(screen.getByPlaceholderText("Password SISTER"), { target: { value: "new-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Testa connessione" }));
    await waitFor(() =>
      expect(apiMocks.testElaborazioneCredentials).toHaveBeenLastCalledWith("token", {
        sister_username: "new-user",
        sister_password: "new-password",
        convenzione: undefined,
        codice_richiesta: undefined,
        ufficio_provinciale: "ORISTANO Territorio",
      }),
    );
  });

  test("prevents a second form test while the sequential pool test is active", async () => {
    vi.useFakeTimers();
    apiMocks.testElaborazioneCredentials.mockResolvedValue({
      ...testResult("pending", "primary"),
      status: "pending",
      success: null,
      authenticated: null,
    });
    render(<ElaborazioniSettingsWorkspace embedded />);
    await act(async () => Promise.resolve());

    fireEvent.click(screen.getByRole("button", { name: "Testa tutte (2)" }));
    await act(async () => Promise.resolve());
    expect(screen.getByRole("button", { name: "Testa connessione" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Interrompi" }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
    });
    vi.useRealTimers();
  });

  test("renders every Bonifica and Capacitas operational status", async () => {
    apiMocks.listBonificaOristaneseCredentials.mockResolvedValue([
      bonificaCredential(1, { active: false }),
      bonificaCredential(2, { last_error: "CSRF token mancante" }),
      bonificaCredential(3, { last_authenticated_url: "https://bonifica.test/home" }),
      bonificaCredential(4, { last_used_at: "2026-08-20T09:00:00Z" }),
      bonificaCredential(5),
    ]);
    apiMocks.listCapacitasCredentials.mockResolvedValue([
      capacitasCredential(1, { active: false }),
      capacitasCredential(2, { last_error: "Token non trovato" }),
      capacitasCredential(3, { last_used_at: "2026-08-20T10:00:00Z" }),
      capacitasCredential(4),
    ]);
    render(<ElaborazioniSettingsWorkspace />);
    await screen.findAllByText("Profilo primary");

    fireEvent.click(screen.getByRole("button", { name: "WhiteCompany" }));
    expect(await screen.findByText("Bonifica 1")).toBeInTheDocument();
    expect(screen.getByText("CSRF token mancante")).toBeInTheDocument();
    expect(screen.getByText("Autenticata")).toBeInTheDocument();
    expect(screen.getByText("Operativa")).toBeInTheDocument();
    expect(screen.getByText("Pronta")).toBeInTheDocument();
    expect(screen.getByText("4 account attivi, 1 disattivi.")).toBeInTheDocument();
    expect(screen.getByText("1 account richiedono controllo o nuovo test.")).toBeInTheDocument();
    expect(
      screen.getByText("Il login page parser non ha trovato il token CSRF Laravel. Verificare markup del form /login o selettori nel backend."),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Capacitas" }));
    expect(await screen.findByText("Capacitas 1")).toBeInTheDocument();
    expect(screen.getByText("Token non trovato")).toBeInTheDocument();
    expect(screen.getAllByText("Operativa").length).toBeGreaterThan(0);
    expect(screen.getByText("Pronta")).toBeInTheDocument();
    expect(screen.getByText("3 account attivi, 1 disattivi.")).toBeInTheDocument();
    expect(screen.getByText("1 account richiedono controllo o nuovo test di connessione.")).toBeInTheDocument();
    expect(screen.getAllByText("08:00 - 18:00").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "SISTER" }));
    expect(screen.getByText("Credenziali e test del canale visure")).toBeInTheDocument();
  });

  test("shows provider loading states before empty results", async () => {
    const bonificaLoad = deferred<BonificaOristaneseCredential[]>();
    const capacitasLoad = deferred<CapacitasCredential[]>();
    apiMocks.listBonificaOristaneseCredentials.mockReturnValue(bonificaLoad.promise);
    apiMocks.listCapacitasCredentials.mockReturnValue(capacitasLoad.promise);
    render(<ElaborazioniSettingsWorkspace />);
    await screen.findAllByText("Profilo primary");

    fireEvent.click(screen.getByRole("button", { name: "WhiteCompany" }));
    expect(screen.getByText("Caricamento credenziali Bonifica.")).toBeInTheDocument();
    bonificaLoad.resolve([]);
    expect(await screen.findByText("Nessuna credenziale Bonifica configurata.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Capacitas" }));
    expect(screen.getByText("Caricamento credenziali Capacitas.")).toBeInTheDocument();
    capacitasLoad.resolve([]);
    expect(await screen.findByText("Nessuna credenziale Capacitas configurata.")).toBeInTheDocument();
  });

  test("creates, updates, tests and deletes Bonifica credentials", async () => {
    const item = bonificaCredential(7, { remember_me: true, last_used_at: "2026-08-20T09:00:00Z" });
    apiMocks.listBonificaOristaneseCredentials.mockResolvedValue([item]);
    apiMocks.createBonificaOristaneseCredential.mockResolvedValue(item);
    apiMocks.updateBonificaOristaneseCredential.mockResolvedValue(item);
    apiMocks.deleteBonificaOristaneseCredential.mockResolvedValue(undefined);
    apiMocks.testBonificaOristaneseCredential.mockResolvedValue({
      ok: true,
      authenticated_url: "https://bonifica.test/dashboard",
      cookies: "cookie",
      error: null,
    });
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo primary");
    fireEvent.click(screen.getByRole("button", { name: "WhiteCompany" }));
    await screen.findByText("Bonifica 7");

    fireEvent.change(screen.getByPlaceholderText("Account Bonifica primario"), { target: { value: " Nuova Bonifica " } });
    fireEvent.change(screen.getByPlaceholderText("utente@example.local"), { target: { value: " login@example.test " } });
    fireEvent.change(screen.getByPlaceholderText("Password Bonifica"), { target: { value: "secret" } });
    const checkboxes = screen.getAllByRole("checkbox");
    fireEvent.click(checkboxes[0]);
    fireEvent.click(checkboxes[1]);
    fireEvent.click(screen.getByRole("button", { name: "Aggiungi account" }));
    await waitFor(() =>
      expect(apiMocks.createBonificaOristaneseCredential).toHaveBeenCalledWith("token", {
        label: "Nuova Bonifica",
        login_identifier: "login@example.test",
        password: "secret",
        remember_me: true,
        active: false,
      }),
    );

    const row = screen.getByText("Bonifica 7").closest("tr");
    fireEvent.click(within(row!).getByRole("button", { name: "Modifica" }));
    expect(screen.getByPlaceholderText("Lascia vuoto per non cambiarla")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna account" }));
    await waitFor(() =>
      expect(apiMocks.updateBonificaOristaneseCredential).toHaveBeenCalledWith("token", 7, expect.objectContaining({
        password: undefined,
        remember_me: true,
      })),
    );

    const refreshedBonificaRow = screen.getByText("Bonifica 7").closest("tr");
    fireEvent.click(within(refreshedBonificaRow!).getByRole("button", { name: "Test" }));
    expect(await screen.findByText("Connessione Bonifica confermata · https://bonifica.test/dashboard.")).toBeInTheDocument();

    fireEvent.click(within(screen.getByText("Bonifica 7").closest("tr")!).getByRole("button", { name: "Modifica" }));
    fireEvent.click(within(screen.getByText("Bonifica 7").closest("tr")!).getByRole("button", { name: "Elimina" }));
    const dialog = screen.getByText("Conferma eliminazione").closest("div.fixed");
    fireEvent.click(within(dialog!).getByRole("button", { name: "Elimina" }));
    await waitFor(() => expect(apiMocks.deleteBonificaOristaneseCredential).toHaveBeenCalledWith("token", 7));
  });

  test("creates, updates, tests and deletes Capacitas credentials", async () => {
    const item = capacitasCredential(9, { allowed_hours_start: 22, allowed_hours_end: 5 });
    apiMocks.listCapacitasCredentials.mockResolvedValue([item]);
    apiMocks.createCapacitasCredential.mockResolvedValue(item);
    apiMocks.updateCapacitasCredential.mockResolvedValue(item);
    apiMocks.deleteCapacitasCredential.mockResolvedValue(undefined);
    apiMocks.testCapacitasCredential.mockResolvedValue({ ok: true, token: "abc-token", error: null });
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo primary");
    fireEvent.click(screen.getByRole("button", { name: "Capacitas" }));
    await screen.findByText("Capacitas 9");

    fireEvent.change(screen.getByPlaceholderText("Account principale"), { target: { value: " Nuovo account " } });
    fireEvent.change(screen.getByPlaceholderText("capacitas-user"), { target: { value: " user-new " } });
    fireEvent.change(screen.getByPlaceholderText("Password Capacitas"), { target: { value: "secret" } });
    const numberInputs = screen.getAllByRole("spinbutton");
    fireEvent.change(numberInputs[0], { target: { value: "" } });
    fireEvent.change(numberInputs[1], { target: { value: "" } });
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "Aggiungi account" }));
    await waitFor(() =>
      expect(apiMocks.createCapacitasCredential).toHaveBeenCalledWith("token", {
        label: "Nuovo account",
        username: "user-new",
        password: "secret",
        active: false,
        allowed_hours_start: 0,
        allowed_hours_end: 23,
      }),
    );

    const row = screen.getByText("Capacitas 9").closest("tr");
    fireEvent.click(within(row!).getByRole("button", { name: "Modifica" }));
    fireEvent.change(screen.getByPlaceholderText("Lascia vuoto per non cambiarla"), { target: { value: "updated" } });
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna account" }));
    await waitFor(() =>
      expect(apiMocks.updateCapacitasCredential).toHaveBeenCalledWith("token", 9, expect.objectContaining({
        password: "updated",
        allowed_hours_start: 22,
        allowed_hours_end: 5,
      })),
    );

    const refreshedCapacitasRow = screen.getByText("Capacitas 9").closest("tr");
    fireEvent.click(within(refreshedCapacitasRow!).getByRole("button", { name: "Test" }));
    expect(await screen.findByText("Test Capacitas completato")).toBeInTheDocument();
    expect(screen.getByText("abc-token")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));

    fireEvent.click(within(screen.getByText("Capacitas 9").closest("tr")!).getByRole("button", { name: "Modifica" }));
    fireEvent.click(within(screen.getByText("Capacitas 9").closest("tr")!).getByRole("button", { name: "Elimina" }));
    const dialog = screen.getByText("Conferma eliminazione").closest("div.fixed");
    fireEvent.click(within(dialog!).getByRole("button", { name: "Elimina" }));
    await waitFor(() => expect(apiMocks.deleteCapacitasCredential).toHaveBeenCalledWith("token", 9));
  });

  test("updates and creates SISTER profiles and manages released batches", async () => {
    const primary = credential("primary", { is_default: true });
    const created = credential("created", { label: "Creato", is_default: false });
    apiMocks.updateElaborazioneCredential.mockResolvedValue(primary);
    apiMocks.saveElaborazioneCredentials.mockResolvedValue(created);
    apiMocks.getElaborazioneBatches.mockResolvedValue([
      {
        id: "old",
        name: null,
        status: "cancelled",
        current_operation: "Release requested by user",
        skipped_items: 2,
        created_at: "2026-08-19T08:00:00Z",
      },
      {
        id: "new",
        name: null,
        status: "cancelled",
        current_operation: "Release requested by user",
        skipped_items: 3,
        created_at: "2026-08-20T08:00:00Z",
      },
      {
        id: "ignored",
        name: "Non idoneo",
        status: "completed",
        current_operation: null,
        skipped_items: 0,
        created_at: "2026-08-21T08:00:00Z",
      },
    ]);
    apiMocks.startElaborazioneBatch.mockResolvedValue({});
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo primary");

    fireEvent.change(screen.getByPlaceholderText("SISTER principale"), { target: { value: "Label aggiornata" } });
    fireEvent.change(screen.getByPlaceholderText("Codice fiscale / username"), { target: { value: "updated-user" } });
    fireEvent.change(screen.getByPlaceholderText("Password SISTER"), { target: { value: "updated-password" } });
    fireEvent.change(screen.getByPlaceholderText("CONSORZIO DI BONIFICA DELL'ORISTANESE"), { target: { value: "Convenzione A" } });
    fireEvent.change(screen.getByPlaceholderText("C00024602008"), { target: { value: "CODE-A" } });
    fireEvent.change(screen.getByDisplayValue("ORISTANO Territorio"), { target: { value: "CAGLIARI Territorio" } });
    const sisterCheckboxes = screen.getAllByRole("checkbox");
    fireEvent.click(sisterCheckboxes[0]);
    fireEvent.click(sisterCheckboxes[1]);
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna credenziale" }));
    await waitFor(() =>
      expect(apiMocks.updateElaborazioneCredential).toHaveBeenCalledWith("token", "primary", {
        label: "Label aggiornata",
        sister_username: "updated-user",
        sister_password: "updated-password",
        convenzione: "Convenzione A",
        codice_richiesta: "CODE-A",
        ufficio_provinciale: "CAGLIARI Territorio",
        active: false,
        is_default: false,
        schedule_enabled: false,
        availability_schedule: expect.objectContaining({ timezone: "Europe/Rome" }),
      }),
    );

    fireEvent.click(screen.getByRole("button", { name: "Nuova credenziale" }));
    fireEvent.change(screen.getByPlaceholderText("SISTER principale"), { target: { value: "Creato" } });
    fireEvent.change(screen.getByPlaceholderText("Codice fiscale / username"), { target: { value: "created-user" } });
    fireEvent.change(screen.getByPlaceholderText("Password SISTER"), { target: { value: "created-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Aggiungi credenziale" }));
    await waitFor(() =>
      expect(apiMocks.saveElaborazioneCredentials).toHaveBeenCalledWith("token", {
        label: "Creato",
        sister_username: "created-user",
        sister_password: "created-password",
        convenzione: undefined,
        codice_richiesta: undefined,
        ufficio_provinciale: "ORISTANO Territorio",
        active: true,
        is_default: false,
        schedule_enabled: false,
        availability_schedule: expect.objectContaining({ timezone: "Europe/Rome" }),
      }),
    );

    fireEvent.click(screen.getByRole("button", { name: "Riprendi batch (2)" }));
    await waitFor(() => expect(apiMocks.startElaborazioneBatch).toHaveBeenCalledWith("token", "new"));
    expect(screen.getByText(/Restano 1 batch fermati/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Pausa e libera sessioni" }));
    await waitFor(() => expect(apiMocks.releaseElaborazioneCredentials).toHaveBeenCalledWith("token"));
  });

  test("enables and saves the weekly SISTER availability", async () => {
    const scheduled = credential("primary", {
      is_default: true,
      schedule_enabled: true,
      availability_schedule: {
        timezone: "Europe/Rome",
        weekly: Object.fromEntries(
          Array.from({ length: 7 }, (_, day) => [String(day), [{ start: "18:00", end: "08:00" }]]),
        ),
      },
    });
    apiMocks.getElaborazioneCredentials.mockResolvedValue({
      configured: true,
      credentials: [scheduled],
      default_credential: scheduled,
      credential: scheduled,
    });
    apiMocks.updateElaborazioneCredential.mockResolvedValue(scheduled);
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo primary");

    fireEvent.click(within(screen.getByText("Profilo primary").closest("article")!).getByRole("button", { name: "Modifica" }));
    fireEvent.click(screen.getByRole("checkbox", { name: /Usa solo fuori dall/ }));
    fireEvent.click(screen.getByRole("checkbox", { name: /Usa solo fuori dall/ }));
    fireEvent.change(await screen.findByLabelText("Lunedi dalle"), { target: { value: "19:00" } });
    fireEvent.click(screen.getByRole("button", { name: "Applica fuori orario ufficio" }));
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna credenziale" }));

    await waitFor(() => expect(apiMocks.updateElaborazioneCredential).toHaveBeenCalledWith(
      "token",
      "primary",
      expect.objectContaining({
        schedule_enabled: true,
        availability_schedule: expect.objectContaining({ timezone: "Europe/Rome" }),
      }),
    ));
  });

  test("shows immediate, scheduled and unavailable worker usage states", async () => {
    const lateWindow = {
      timezone: "Europe/Rome" as const,
      weekly: Object.fromEntries(Array.from({ length: 7 }, (_, day) => [String(day), [{ start: "23:59", end: "00:00" }]])),
    };
    const primary = credential("primary", { is_default: true });
    const scheduled = credential("scheduled", { schedule_enabled: true, availability_schedule: lateWindow });
    const closed = credential("closed", {
      schedule_enabled: true,
      availability_schedule: undefined as unknown as null,
    });
    apiMocks.getElaborazioneCredentials.mockResolvedValue({
      configured: true,
      credentials: [primary, scheduled, closed],
      default_credential: primary,
      credential: primary,
    });

    render(<ElaborazioniSettingsWorkspace embedded />);

    expect(await screen.findByText("Disponibile ora")).toBeInTheDocument();
    expect(screen.getAllByText(/^Disponibile /)).toHaveLength(2);
    expect(screen.getByText("Nessuna fascia disponibile")).toBeInTheDocument();
  });

  test("normalizes nullable SISTER fields across selection, update and create", async () => {
    const primary = credential("primary", {
      label: "",
      is_default: true,
      convenzione: null,
      codice_richiesta: null,
      schedule_enabled: undefined as unknown as boolean,
      availability_schedule: undefined as unknown as null,
    });
    const secondary = credential("secondary", { convenzione: null, codice_richiesta: null });
    const created = credential("created", { convenzione: null, codice_richiesta: null });
    apiMocks.getElaborazioneCredentials.mockResolvedValue({
      configured: true,
      credentials: [primary, secondary],
      default_credential: primary,
      credential: primary,
    });
    apiMocks.updateElaborazioneCredential.mockImplementation(async (_token: string, id: string) =>
      id === "primary" ? primary : secondary,
    );
    apiMocks.saveElaborazioneCredentials.mockResolvedValue(created);
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("user-primary");

    fireEvent.click(within(screen.getByText("user-primary").closest("article")!).getByRole("button", { name: "Modifica" }));
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna credenziale" }));
    await waitFor(() =>
      expect(apiMocks.updateElaborazioneCredential).toHaveBeenCalledWith("token", "primary", expect.objectContaining({
        sister_password: undefined,
        convenzione: null,
        codice_richiesta: null,
      })),
    );

    fireEvent.click(screen.getAllByRole("button", { name: "Elimina" })[0]);
    expect(screen.getByText("Conferma eliminazione").closest("div.fixed")).toHaveTextContent("(SISTER)");
    fireEvent.click(screen.getByRole("button", { name: "Annulla" }));

    const secondaryCard = screen.getByText("Profilo secondary").closest("article");
    fireEvent.click(within(secondaryCard!).getByRole("button", { name: "Modifica" }));
    fireEvent.click(within(secondaryCard!).getByRole("button", { name: "Rendi default" }));
    await waitFor(() => expect(screen.getByPlaceholderText("CONSORZIO DI BONIFICA DELL'ORISTANESE")).toHaveValue(""));

    fireEvent.click(screen.getByRole("button", { name: "Nuova credenziale" }));
    fireEvent.change(screen.getByPlaceholderText("Codice fiscale / username"), { target: { value: "new-user" } });
    fireEvent.change(screen.getByPlaceholderText("Password SISTER"), { target: { value: "password" } });
    fireEvent.click(screen.getByRole("button", { name: "Aggiungi credenziale" }));
    await waitFor(() => expect(screen.getByPlaceholderText("CONSORZIO DI BONIFICA DELL'ORISTANESE")).toHaveValue(""));
  });

  test("handles one released batch and Error instances from session actions", async () => {
    apiMocks.getElaborazioneBatches.mockResolvedValue([
      {
        id: "only-batch",
        name: null,
        status: "cancelled",
        current_operation: "Release requested by user",
        skipped_items: 1,
        created_at: "2026-08-20T08:00:00Z",
      },
    ]);
    apiMocks.startElaborazioneBatch.mockResolvedValueOnce({}).mockRejectedValueOnce(new Error("resume error"));
    apiMocks.releaseElaborazioneCredentials.mockRejectedValue(new Error("release error"));
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo primary");

    fireEvent.click(screen.getByRole("button", { name: "Riprendi batch" }));
    expect(await screen.findByText("Ripreso batch only-batch.")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Riprendi batch" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Riprendi batch" }));
    expect(await screen.findByText("resume error")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Pausa e libera sessioni" }));
    expect(await screen.findByText("release error")).toBeInTheDocument();
  });

  test("shows provider failure results and diagnostic fallbacks", async () => {
    const bonifica = bonificaCredential(1, { last_error: "Credenziali non valide" });
    const capacitas = capacitasCredential(1);
    apiMocks.listBonificaOristaneseCredentials.mockResolvedValue([bonifica]);
    apiMocks.listCapacitasCredentials.mockResolvedValue([capacitas]);
    apiMocks.testBonificaOristaneseCredential.mockResolvedValue({
      ok: false,
      authenticated_url: null,
      cookies: null,
      error: null,
    });
    apiMocks.testCapacitasCredential.mockResolvedValue({
      ok: false,
      token: null,
      error: "__VIEWSTATE mancante",
    });
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo primary");

    fireEvent.click(screen.getByRole("button", { name: "WhiteCompany" }));
    expect(screen.getByText(/form di login ancora attivo/)).toBeInTheDocument();
    fireEvent.click(within(screen.getByText("Bonifica 1").closest("tr")!).getByRole("button", { name: "Test" }));
    expect(await screen.findByText("Test Bonifica fallito")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Capacitas" }));
    fireEvent.click(within(screen.getByText("Capacitas 1").closest("tr")!).getByRole("button", { name: "Test" }));
    expect((await screen.findAllByText("Test Capacitas fallito")).length).toBeGreaterThan(0);
    expect(screen.getByText(/campi ASP.NET richiesti/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
  });

  test("handles realtime SISTER test updates and closes the socket on completion", async () => {
    const socket = {
      close: vi.fn(),
      onmessage: null as ((event: { data: string }) => void) | null,
      onerror: null as (() => void) | null,
    };
    apiMocks.createElaborazioneCredentialTestWebSocket.mockReturnValue(socket);
    apiMocks.testElaborazioneCredentials.mockResolvedValue({
      ...testResult("realtime", "primary"),
      status: "pending",
      success: null,
      reachable: null,
      authenticated: null,
      verified_at: null,
    });
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findAllByText("Profilo primary");
    fireEvent.click(screen.getByRole("button", { name: "Testa connessione" }));
    await waitFor(() => expect(apiMocks.createElaborazioneCredentialTestWebSocket).toHaveBeenCalledWith("realtime", "token"));

    act(() => socket.onmessage?.({ data: JSON.stringify({ type: "heartbeat" }) }));
    act(() => socket.onmessage?.({ data: "not-json" }));
    expect(screen.getByText(/Unexpected token|JSON/)).toBeInTheDocument();

    const completed = { ...testResult("realtime", "primary"), credential_id: null };
    act(() => socket.onmessage?.({ data: JSON.stringify({ type: "credentials_test", test: completed }) }));
    expect(await screen.findByText("Autenticazione confermata")).toBeInTheDocument();
    await waitFor(() => expect(socket.close).toHaveBeenCalled());
  });

  test("falls back to HTTP refresh when the realtime socket fails", async () => {
    const socket = {
      close: vi.fn(),
      onmessage: null as ((event: { data: string }) => void) | null,
      onerror: null as (() => void) | null,
    };
    apiMocks.createElaborazioneCredentialTestWebSocket.mockReturnValue(socket);
    apiMocks.testElaborazioneCredentials.mockResolvedValue({
      ...testResult("refresh", "primary"),
      status: "pending",
      success: null,
      authenticated: null,
      verified_at: null,
    });
    apiMocks.getElaborazioneCredentialTest.mockResolvedValue({
      ...testResult("refresh", "primary"),
      status: "processing",
      success: null,
      authenticated: null,
      verified_at: null,
    });
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo primary");
    fireEvent.click(screen.getByRole("button", { name: "Testa connessione" }));
    await waitFor(() => expect(socket.onerror).not.toBeNull());
    act(() => socket.onerror?.());
    await waitFor(() => expect(apiMocks.getElaborazioneCredentialTest).toHaveBeenCalledWith("token", "refresh"));
    expect(screen.getByText("Test in lavorazione")).toBeInTheDocument();
  });

  test("shows refresh errors returned after a socket failure", async () => {
    const socket = {
      close: vi.fn(),
      onmessage: null as ((event: { data: string }) => void) | null,
      onerror: null as (() => void) | null,
    };
    apiMocks.createElaborazioneCredentialTestWebSocket.mockReturnValue(socket);
    apiMocks.testElaborazioneCredentials.mockResolvedValue({
      ...testResult("refresh-error", "primary"),
      status: "pending",
      success: null,
      authenticated: null,
      verified_at: null,
    });
    apiMocks.getElaborazioneCredentialTest.mockRejectedValue("refresh error");
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo primary");
    fireEvent.click(screen.getByRole("button", { name: "Testa connessione" }));
    await waitFor(() => expect(socket.onerror).not.toBeNull());
    act(() => socket.onerror?.());
    expect(await screen.findByText("Errore refresh test connessione SISTER")).toBeInTheDocument();
  });

  test("does not call protected operations after the access token is removed", async () => {
    apiMocks.listBonificaOristaneseCredentials.mockResolvedValue([bonificaCredential(1)]);
    apiMocks.listCapacitasCredentials.mockResolvedValue([capacitasCredential(1)]);
    apiMocks.getElaborazioneBatches.mockResolvedValue([
      {
        id: "released",
        name: "Released",
        status: "cancelled",
        current_operation: "Release requested by user",
        skipped_items: 1,
        created_at: "2026-08-20T08:00:00Z",
      },
    ]);
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo primary");
    authState.token = null;

    fireEvent.click(screen.getByRole("button", { name: "Pausa e libera sessioni" }));
    fireEvent.click(screen.getByRole("button", { name: "Riprendi batch" }));
    fireEvent.click(screen.getByRole("button", { name: "Testa connessione" }));
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna credenziale" }));
    const secondaryCard = screen.getByText("Profilo secondary").closest("article");
    fireEvent.click(within(secondaryCard!).getByRole("button", { name: "Rendi default" }));
    fireEvent.click(within(secondaryCard!).getByRole("button", { name: "Elimina" }));
    fireEvent.click(within(screen.getByText("Conferma eliminazione").closest("div.fixed")!).getByRole("button", { name: "Elimina" }));

    fireEvent.click(screen.getByRole("button", { name: "WhiteCompany" }));
    const bonificaRow = screen.getByText("Bonifica 1").closest("tr");
    fireEvent.click(within(bonificaRow!).getByRole("button", { name: "Modifica" }));
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna account" }));
    fireEvent.click(within(bonificaRow!).getByRole("button", { name: "Test" }));
    fireEvent.click(within(bonificaRow!).getByRole("button", { name: "Elimina" }));
    fireEvent.click(within(screen.getByText("Conferma eliminazione").closest("div.fixed")!).getByRole("button", { name: "Elimina" }));

    fireEvent.click(screen.getByRole("button", { name: "Capacitas" }));
    const capacitasRow = screen.getByText("Capacitas 1").closest("tr");
    fireEvent.click(within(capacitasRow!).getByRole("button", { name: "Modifica" }));
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna account" }));
    fireEvent.click(within(capacitasRow!).getByRole("button", { name: "Test" }));
    fireEvent.click(within(capacitasRow!).getByRole("button", { name: "Elimina" }));
    fireEvent.click(within(screen.getByText("Conferma eliminazione").closest("div.fixed")!).getByRole("button", { name: "Elimina" }));

    expect(apiMocks.releaseElaborazioneCredentials).not.toHaveBeenCalled();
    expect(apiMocks.startElaborazioneBatch).not.toHaveBeenCalled();
    expect(apiMocks.updateBonificaOristaneseCredential).not.toHaveBeenCalled();
    expect(apiMocks.updateCapacitasCredential).not.toHaveBeenCalled();
  });

  test("skips all initial credential loads when unauthenticated", async () => {
    authState.token = null;
    render(<ElaborazioniSettingsWorkspace embedded />);
    await act(async () => Promise.resolve());

    expect(apiMocks.getElaborazioneCredentials).not.toHaveBeenCalled();
    expect(apiMocks.getElaborazioneBatches).not.toHaveBeenCalled();
    expect(apiMocks.listBonificaOristaneseCredentials).not.toHaveBeenCalled();
    expect(apiMocks.listCapacitasCredentials).not.toHaveBeenCalled();
    expect(screen.getByText("Non configurato")).toBeInTheDocument();
    fireEvent.change(screen.getByDisplayValue("ORISTANO Territorio"), { target: { value: "" } });
    expect(screen.getByText("ORISTANO Territorio")).toBeInTheDocument();
  });

  test("renders fallback messages when initial provider loads fail", async () => {
    apiMocks.getElaborazioneCredentials.mockRejectedValue("sister load");
    apiMocks.getElaborazioneBatches.mockRejectedValue("batch load");
    apiMocks.listBonificaOristaneseCredentials.mockRejectedValue("bonifica load");
    apiMocks.listCapacitasCredentials.mockRejectedValue("capacitas load");
    render(<ElaborazioniSettingsWorkspace embedded />);

    expect(await screen.findByText("Errore caricamento credenziali")).toBeInTheDocument();
    expect(screen.getByText("Errore caricamento credenziali Bonifica")).toBeInTheDocument();
    expect(screen.getByText("Errore caricamento credenziali Capacitas")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "WhiteCompany" }));
    expect(screen.getByText("Nessuna credenziale Bonifica configurata.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Capacitas" }));
    expect(screen.getByText("Nessuna credenziale Capacitas configurata.")).toBeInTheDocument();
  });

  test("preserves Error messages when initial provider loads fail", async () => {
    apiMocks.getElaborazioneCredentials.mockRejectedValue(new Error("sister unavailable"));
    apiMocks.getElaborazioneBatches.mockRejectedValue(new Error("batch unavailable"));
    apiMocks.listBonificaOristaneseCredentials.mockRejectedValue(new Error("bonifica unavailable"));
    apiMocks.listCapacitasCredentials.mockRejectedValue(new Error("capacitas unavailable"));
    render(<ElaborazioniSettingsWorkspace embedded />);

    expect(await screen.findByText("sister unavailable")).toBeInTheDocument();
    expect(screen.getByText("bonifica unavailable")).toBeInTheDocument();
    expect(screen.getByText("capacitas unavailable")).toBeInTheDocument();
  });

  test("surfaces failures from every SISTER pool action", async () => {
    apiMocks.getElaborazioneBatches.mockResolvedValue([
      {
        id: "released",
        name: null,
        status: "cancelled",
        current_operation: "Release requested by user",
        skipped_items: 1,
        created_at: "2026-08-20T08:00:00Z",
      },
    ]);
    apiMocks.releaseElaborazioneCredentials.mockRejectedValue("release");
    apiMocks.startElaborazioneBatch.mockRejectedValue("resume");
    apiMocks.updateElaborazioneCredential.mockRejectedValue("update");
    apiMocks.testElaborazioneCredentials.mockRejectedValue("test");
    apiMocks.deleteElaborazioneCredential.mockRejectedValue(new Error("delete sister"));
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo primary");

    fireEvent.click(screen.getByRole("button", { name: "Pausa e libera sessioni" }));
    expect(await screen.findByText("Errore rilascio utenze SISTER")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Riprendi batch" }));
    expect(await screen.findByText("Errore ripresa batch rilasciato")).toBeInTheDocument();

    const secondaryCard = screen.getByText("Profilo secondary").closest("article");
    fireEvent.click(within(secondaryCard!).getByRole("button", { name: "Rendi default" }));
    expect(await screen.findByText("Errore aggiornamento credenziale")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Testa connessione" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Testa connessione" }));
    expect(await screen.findByText("Errore test connessione SISTER")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Aggiorna credenziale" }));
    expect(await screen.findByText("Errore salvataggio credenziali")).toBeInTheDocument();
    fireEvent.click(within(secondaryCard!).getByRole("button", { name: "Elimina" }));
    const dialog = screen.getByText("Conferma eliminazione").closest("div.fixed");
    fireEvent.click(within(dialog!).getByRole("button", { name: "Elimina" }));
    expect(await within(dialog!).findByText("delete sister")).toBeInTheDocument();
    fireEvent.click(within(dialog!).getByRole("button", { name: "Annulla" }));
  });

  test("preserves Error objects and non-selected deletes in SISTER actions", async () => {
    const primary = credential("primary", { is_default: true });
    const secondary = credential("secondary");
    const blank = credential("blank", { label: "" });
    apiMocks.getElaborazioneCredentials.mockResolvedValue({
      configured: true,
      credentials: [primary, secondary, blank],
      default_credential: primary,
      credential: primary,
    });
    apiMocks.updateElaborazioneCredential.mockRejectedValue(new Error("update object"));
    apiMocks.testElaborazioneCredentials.mockRejectedValue(new Error("test object"));
    apiMocks.deleteElaborazioneCredential.mockResolvedValueOnce({}).mockRejectedValueOnce("delete raw");
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo primary");

    fireEvent.click(within(screen.getByText("Profilo secondary").closest("article")!).getByRole("button", { name: "Rendi default" }));
    expect(await screen.findByText("update object")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Testa connessione" }));
    expect(await screen.findByText("test object")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna credenziale" }));
    expect(await screen.findByText("update object")).toBeInTheDocument();

    fireEvent.click(within(screen.getByText("user-blank").closest("article")!).getByRole("button", { name: "Elimina" }));
    let dialog = screen.getByText("Conferma eliminazione").closest("div.fixed");
    fireEvent.click(within(dialog!).getByRole("button", { name: "Elimina" }));
    expect(await screen.findByText("Credenziale SISTER rimossa.")).toBeInTheDocument();

    fireEvent.click(within(screen.getByText("Profilo secondary").closest("article")!).getByRole("button", { name: "Elimina" }));
    dialog = screen.getByText("Conferma eliminazione").closest("div.fixed");
    fireEvent.click(within(dialog!).getByRole("button", { name: "Elimina" }));
    expect(await within(dialog!).findByText("Errore eliminazione credenziale")).toBeInTheDocument();
  });

  test("surfaces Bonifica and Capacitas save, delete and test errors", async () => {
    apiMocks.listBonificaOristaneseCredentials.mockResolvedValue([bonificaCredential(1)]);
    apiMocks.listCapacitasCredentials.mockResolvedValue([capacitasCredential(1)]);
    apiMocks.updateBonificaOristaneseCredential.mockRejectedValue("bonifica save");
    apiMocks.deleteBonificaOristaneseCredential.mockRejectedValue("bonifica delete");
    apiMocks.testBonificaOristaneseCredential.mockRejectedValue(new Error("bonifica test"));
    apiMocks.updateCapacitasCredential.mockRejectedValue("capacitas save");
    apiMocks.deleteCapacitasCredential.mockRejectedValue("capacitas delete");
    apiMocks.testCapacitasCredential.mockRejectedValue(new Error("capacitas test"));
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo primary");

    fireEvent.click(screen.getByRole("button", { name: "WhiteCompany" }));
    let row = screen.getByText("Bonifica 1").closest("tr");
    fireEvent.click(within(row!).getByRole("button", { name: "Modifica" }));
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna account" }));
    expect(await screen.findByText("Errore salvataggio credenziale Bonifica")).toBeInTheDocument();
    fireEvent.click(within(row!).getByRole("button", { name: "Test" }));
    expect(await screen.findByText("bonifica test")).toBeInTheDocument();
    row = screen.getByText("Bonifica 1").closest("tr");
    fireEvent.click(within(row!).getByRole("button", { name: "Elimina" }));
    fireEvent.click(within(screen.getByText("Conferma eliminazione").closest("div.fixed")!).getByRole("button", { name: "Elimina" }));
    expect(await screen.findByText("Errore eliminazione credenziale Bonifica")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Capacitas" }));
    let capacitasRow = screen.getByText("Capacitas 1").closest("tr");
    fireEvent.click(within(capacitasRow!).getByRole("button", { name: "Modifica" }));
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna account" }));
    expect(await screen.findByText("Errore salvataggio credenziale Capacitas")).toBeInTheDocument();
    fireEvent.click(within(capacitasRow!).getByRole("button", { name: "Test" }));
    expect(await screen.findByText("Test Capacitas interrotto")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    capacitasRow = screen.getByText("Capacitas 1").closest("tr");
    fireEvent.click(within(capacitasRow!).getByRole("button", { name: "Elimina" }));
    fireEvent.click(within(screen.getByText("Conferma eliminazione").closest("div.fixed")!).getByRole("button", { name: "Elimina" }));
    expect(await screen.findByText("Errore eliminazione credenziale Capacitas")).toBeInTheDocument();
  });

  test("renders an ApiError diagnosis for Capacitas HTTP 502", async () => {
    apiMocks.listCapacitasCredentials.mockResolvedValue([capacitasCredential(1)]);
    const error = new ApiError("gateway");
    error.status = 502;
    error.detailData = { reason: "upstream" };
    apiMocks.testCapacitasCredential.mockRejectedValue(error);
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo primary");
    fireEvent.click(screen.getByRole("button", { name: "Capacitas" }));
    fireEvent.click(within(screen.getByText("Capacitas 1").closest("tr")!).getByRole("button", { name: "Test" }));

    expect(await screen.findByText(/non completa la negoziazione/)).toBeInTheDocument();
    expect(screen.getByText(/"reason": "upstream"/)).toBeInTheDocument();
  });

  test("covers alternate Bonifica update, delete and test outcomes", async () => {
    const first = bonificaCredential(1);
    const second = bonificaCredential(2);
    apiMocks.listBonificaOristaneseCredentials.mockResolvedValue([first, second]);
    apiMocks.updateBonificaOristaneseCredential.mockResolvedValue(first);
    apiMocks.deleteBonificaOristaneseCredential.mockRejectedValue(new Error("delete object"));
    apiMocks.testBonificaOristaneseCredential
      .mockResolvedValueOnce({ ok: true, authenticated_url: null, cookies: null, error: null })
      .mockRejectedValueOnce("test raw");
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo primary");
    fireEvent.click(screen.getByRole("button", { name: "WhiteCompany" }));

    fireEvent.click(within(screen.getByText("Bonifica 1").closest("tr")!).getByRole("button", { name: "Modifica" }));
    fireEvent.change(screen.getByPlaceholderText("Lascia vuoto per non cambiarla"), { target: { value: "new secret" } });
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna account" }));
    await waitFor(() =>
      expect(apiMocks.updateBonificaOristaneseCredential).toHaveBeenCalledWith("token", 1, expect.objectContaining({
        password: "new secret",
      })),
    );

    fireEvent.click(within(screen.getByText("Bonifica 1").closest("tr")!).getByRole("button", { name: "Test" }));
    expect(await screen.findByText("Connessione Bonifica confermata.")).toBeInTheDocument();
    fireEvent.click(within(screen.getByText("Bonifica 2").closest("tr")!).getByRole("button", { name: "Test" }));
    expect(await screen.findByText("Errore test credenziale Bonifica")).toBeInTheDocument();

    fireEvent.click(within(screen.getByText("Bonifica 2").closest("tr")!).getByRole("button", { name: "Elimina" }));
    fireEvent.click(within(screen.getByText("Conferma eliminazione").closest("div.fixed")!).getByRole("button", { name: "Elimina" }));
    expect(await screen.findByText("delete object")).toBeInTheDocument();
  });

  test("covers alternate Capacitas success, failure and raw-error outcomes", async () => {
    const first = capacitasCredential(1);
    const second = capacitasCredential(2);
    apiMocks.listCapacitasCredentials.mockResolvedValue([first, second]);
    apiMocks.updateCapacitasCredential.mockResolvedValue(first);
    apiMocks.deleteCapacitasCredential.mockRejectedValue(new Error("capacitas delete object"));
    apiMocks.testCapacitasCredential
      .mockResolvedValueOnce({ ok: true, token: null, error: "sessione valida" })
      .mockResolvedValueOnce({ ok: false, token: "partial", error: "errore generico" })
      .mockRejectedValueOnce("capacitas raw");
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo primary");
    fireEvent.click(screen.getByRole("button", { name: "Capacitas" }));

    fireEvent.click(within(screen.getByText("Capacitas 1").closest("tr")!).getByRole("button", { name: "Modifica" }));
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna account" }));
    await waitFor(() =>
      expect(apiMocks.updateCapacitasCredential).toHaveBeenCalledWith("token", 1, expect.objectContaining({ password: undefined })),
    );

    fireEvent.click(within(screen.getByText("Capacitas 1").closest("tr")!).getByRole("button", { name: "Test" }));
    expect(await screen.findByText("Test Capacitas completato")).toBeInTheDocument();
    expect(screen.getByText("sessione valida")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));

    fireEvent.click(within(screen.getByText("Capacitas 2").closest("tr")!).getByRole("button", { name: "Test" }));
    expect((await screen.findAllByText("errore generico")).length).toBeGreaterThan(0);
    expect(screen.getByText("partial")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));

    await waitFor(() =>
      expect(within(screen.getByText("Capacitas 1").closest("tr")!).getByRole("button", { name: "Test" })).toBeEnabled(),
    );
    fireEvent.click(within(screen.getByText("Capacitas 1").closest("tr")!).getByRole("button", { name: "Test" }));
    await waitFor(() => expect(apiMocks.testCapacitasCredential).toHaveBeenCalledTimes(3));
    expect(await screen.findByText("Test Capacitas interrotto")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));

    fireEvent.click(within(screen.getByText("Capacitas 2").closest("tr")!).getByRole("button", { name: "Elimina" }));
    fireEvent.click(within(screen.getByText("Conferma eliminazione").closest("div.fixed")!).getByRole("button", { name: "Elimina" }));
    expect(await screen.findByText("capacitas delete object")).toBeInTheDocument();
  });

  test("covers provider Error saves, non-selected deletes and null test detail", async () => {
    const bonificaOne = bonificaCredential(1);
    const bonificaTwo = bonificaCredential(2);
    const capacitasOne = capacitasCredential(1);
    const capacitasTwo = capacitasCredential(2);
    apiMocks.listBonificaOristaneseCredentials.mockResolvedValue([bonificaOne, bonificaTwo]);
    apiMocks.listCapacitasCredentials.mockResolvedValue([capacitasOne, capacitasTwo]);
    apiMocks.updateBonificaOristaneseCredential.mockRejectedValue(new Error("bonifica save object"));
    apiMocks.updateCapacitasCredential.mockRejectedValue(new Error("capacitas save object"));
    apiMocks.deleteBonificaOristaneseCredential.mockResolvedValue(undefined);
    apiMocks.deleteCapacitasCredential.mockResolvedValue(undefined);
    apiMocks.testCapacitasCredential.mockResolvedValue({ ok: false, token: null, error: null });
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo primary");

    fireEvent.click(screen.getByRole("button", { name: "WhiteCompany" }));
    fireEvent.click(within(screen.getByText("Bonifica 1").closest("tr")!).getByRole("button", { name: "Modifica" }));
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna account" }));
    expect(await screen.findByText("bonifica save object")).toBeInTheDocument();
    fireEvent.click(within(screen.getByText("Bonifica 2").closest("tr")!).getByRole("button", { name: "Elimina" }));
    fireEvent.click(within(screen.getByText("Conferma eliminazione").closest("div.fixed")!).getByRole("button", { name: "Elimina" }));
    await waitFor(() => expect(apiMocks.deleteBonificaOristaneseCredential).toHaveBeenCalledWith("token", 2));

    fireEvent.click(screen.getByRole("button", { name: "Capacitas" }));
    fireEvent.click(within(screen.getByText("Capacitas 1").closest("tr")!).getByRole("button", { name: "Modifica" }));
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna account" }));
    expect(await screen.findByText("capacitas save object")).toBeInTheDocument();
    fireEvent.click(within(screen.getByText("Capacitas 2").closest("tr")!).getByRole("button", { name: "Test" }));
    expect((await screen.findAllByText("Test Capacitas fallito")).length).toBeGreaterThan(0);
    expect(screen.getByText("Nessun dettaglio aggiuntivo restituito dal backend.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    fireEvent.click(within(screen.getByText("Capacitas 2").closest("tr")!).getByRole("button", { name: "Elimina" }));
    fireEvent.click(within(screen.getByText("Conferma eliminazione").closest("div.fixed")!).getByRole("button", { name: "Elimina" }));
    await waitFor(() => expect(apiMocks.deleteCapacitasCredential).toHaveBeenCalledWith("token", 2));
  });

  test("keeps an unknown Bonifica issue visible without replacing it", async () => {
    apiMocks.listBonificaOristaneseCredentials.mockResolvedValue([
      bonificaCredential(1, { last_error: "Errore non classificato" }),
    ]);
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo primary");
    fireEvent.click(screen.getByRole("button", { name: "WhiteCompany" }));

    expect(screen.getAllByText("Errore non classificato").length).toBeGreaterThan(0);
  });

  test.each([
    ["string detail", "string detail"],
    [null, "gateway null"],
  ])("renders Capacitas ApiError detail variant %#", async (detailData, expectedDetail) => {
    apiMocks.listCapacitasCredentials.mockResolvedValue([capacitasCredential(1)]);
    const error = new ApiError("gateway null");
    error.status = null;
    error.detailData = detailData;
    apiMocks.testCapacitasCredential.mockRejectedValue(error);
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo primary");
    fireEvent.click(screen.getByRole("button", { name: "Capacitas" }));
    fireEvent.click(within(screen.getByText("Capacitas 1").closest("tr")!).getByRole("button", { name: "Test" }));

    expect((await screen.findAllByText(expectedDetail)).length).toBeGreaterThan(0);
  });

  test("handles Bonifica ApiError 502 and a zero credential id", async () => {
    apiMocks.listBonificaOristaneseCredentials.mockResolvedValue([
      bonificaCredential(0, { label: "Bonifica zero" }),
      bonificaCredential(1),
    ]);
    const error = new ApiError("bonifica gateway");
    error.status = 502;
    apiMocks.testBonificaOristaneseCredential.mockRejectedValue(error);
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo primary");
    fireEvent.click(screen.getByRole("button", { name: "WhiteCompany" }));

    fireEvent.click(within(screen.getByText("Bonifica 1").closest("tr")!).getByRole("button", { name: "Test" }));
    expect(await screen.findByText("bonifica gateway")).toBeInTheDocument();

    fireEvent.click(within(screen.getByText("Bonifica zero").closest("tr")!).getByRole("button", { name: "Elimina" }));
    const dialog = screen.getByText("Conferma eliminazione").closest("div.fixed");
    fireEvent.click(within(dialog!).getByRole("button", { name: "Elimina" }));
    expect(apiMocks.deleteBonificaOristaneseCredential).not.toHaveBeenCalled();
    fireEvent.click(within(dialog!).getByRole("button", { name: "Annulla" }));
  });

  test("refreshes a completed test with persisted verification data", async () => {
    const socket = {
      close: vi.fn(),
      onmessage: null as ((event: { data: string }) => void) | null,
      onerror: null as (() => void) | null,
    };
    apiMocks.createElaborazioneCredentialTestWebSocket.mockReturnValue(socket);
    apiMocks.testElaborazioneCredentials.mockResolvedValue({
      ...testResult("refresh-complete", "primary"),
      status: "pending",
      success: null,
      authenticated: null,
      verified_at: null,
    });
    apiMocks.getElaborazioneCredentialTest.mockResolvedValue({
      ...testResult("refresh-complete", "primary"),
      credential_id: null,
    });
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo primary");
    fireEvent.click(screen.getByRole("button", { name: "Testa connessione" }));
    await waitFor(() => expect(socket.onerror).not.toBeNull());
    act(() =>
      socket.onmessage?.({
        data: JSON.stringify({
          type: "credentials_test",
          test: { ...testResult("refresh-complete", "primary"), credential_id: null },
        }),
      }),
    );
    act(() => socket.onerror?.());

    expect(await screen.findByText("Autenticazione confermata")).toBeInTheDocument();
    await waitFor(() => expect(apiMocks.getElaborazioneCredentials.mock.calls.length).toBeGreaterThan(1));
  });

  test("refreshes verified transient tests when no default credential exists", async () => {
    const only = credential("only");
    apiMocks.getElaborazioneCredentials.mockResolvedValue({
      configured: true,
      credentials: [only],
      default_credential: null,
      credential: null,
    });
    const socket = {
      close: vi.fn(),
      onmessage: null as ((event: { data: string }) => void) | null,
      onerror: null as (() => void) | null,
    };
    apiMocks.createElaborazioneCredentialTestWebSocket.mockReturnValue(socket);
    apiMocks.testElaborazioneCredentials.mockResolvedValue({
      ...testResult("transient-refresh", "only"),
      credential_id: null,
      status: "pending",
      success: null,
      authenticated: null,
      verified_at: null,
    });
    apiMocks.getElaborazioneCredentialTest.mockResolvedValue({
      ...testResult("transient-refresh", "only"),
      credential_id: null,
    });
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo only");
    fireEvent.change(screen.getByPlaceholderText("Codice fiscale / username"), { target: { value: "transient" } });
    fireEvent.change(screen.getByPlaceholderText("Password SISTER"), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: "Testa connessione" }));
    await waitFor(() => expect(socket.onerror).not.toBeNull());
    act(() =>
      socket.onmessage?.({
        data: JSON.stringify({
          type: "credentials_test",
          test: { ...testResult("transient-refresh", "only"), credential_id: null },
        }),
      }),
    );
    act(() => socket.onerror?.());

    expect(await screen.findByText("Autenticazione confermata")).toBeInTheDocument();
  });

  test("handles pending websocket messages without persisted verification", async () => {
    const socket = {
      close: vi.fn(),
      onmessage: null as ((event: { data: string }) => void) | null,
      onerror: null as (() => void) | null,
    };
    apiMocks.createElaborazioneCredentialTestWebSocket.mockReturnValue(socket);
    apiMocks.testElaborazioneCredentials.mockResolvedValue({
      ...testResult("pending-message", "primary"),
      status: "pending",
      success: null,
      authenticated: null,
      verified_at: null,
    });
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo primary");
    fireEvent.click(screen.getByRole("button", { name: "Testa connessione" }));
    await waitFor(() => expect(socket.onmessage).not.toBeNull());

    const processing = {
      ...testResult("pending-message", "primary"),
      status: "processing" as const,
      success: null,
      authenticated: null,
      verified_at: null,
    };
    act(() => socket.onmessage?.({ data: JSON.stringify({ type: "credentials_test", test: processing }) }));
    expect(screen.getByText("Test in lavorazione")).toBeInTheDocument();
    act(() =>
      socket.onmessage?.({
        get data() {
          throw "raw socket parse";
        },
      }),
    );
    expect(await screen.findByText("Errore parsing aggiornamento realtime")).toBeInTheDocument();
  });

  test("handles verified HTTP refresh while credential state is unavailable", async () => {
    apiMocks.getElaborazioneCredentials.mockRejectedValue(new Error("initial credential error"));
    const socket = {
      close: vi.fn(),
      onmessage: null as ((event: { data: string }) => void) | null,
      onerror: null as (() => void) | null,
    };
    apiMocks.createElaborazioneCredentialTestWebSocket.mockReturnValue(socket);
    apiMocks.testElaborazioneCredentials.mockResolvedValue({
      ...testResult("refresh-without-state", "primary"),
      credential_id: null,
      status: "pending",
      success: null,
      authenticated: null,
      verified_at: null,
    });
    apiMocks.getElaborazioneCredentialTest.mockResolvedValue({
      ...testResult("refresh-without-state", "primary"),
      credential_id: null,
    });
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("initial credential error");
    fireEvent.change(screen.getByPlaceholderText("Codice fiscale / username"), { target: { value: "transient" } });
    fireEvent.change(screen.getByPlaceholderText("Password SISTER"), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: "Testa connessione" }));
    await waitFor(() => expect(socket.onerror).not.toBeNull());
    act(() =>
      socket.onmessage?.({
        data: JSON.stringify({
          type: "credentials_test",
          test: { ...testResult("refresh-without-state", "primary"), credential_id: null },
        }),
      }),
    );
    act(() => socket.onerror?.());

    expect(await screen.findByText("Autenticazione confermata")).toBeInTheDocument();
  });

  test("handles verified websocket updates without default or legacy credential aliases", async () => {
    const only = credential("only");
    apiMocks.getElaborazioneCredentials.mockResolvedValue({
      configured: true,
      credentials: [only],
      default_credential: null,
      credential: null,
    });
    const socket = {
      close: vi.fn(),
      onmessage: null as ((event: { data: string }) => void) | null,
      onerror: null as (() => void) | null,
    };
    apiMocks.createElaborazioneCredentialTestWebSocket.mockReturnValue(socket);
    apiMocks.testElaborazioneCredentials.mockResolvedValue({
      ...testResult("ws-without-default", "only"),
      status: "pending",
      success: null,
      authenticated: null,
      verified_at: null,
    });
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo only");
    fireEvent.change(screen.getByPlaceholderText("Codice fiscale / username"), { target: { value: "transient" } });
    fireEvent.change(screen.getByPlaceholderText("Password SISTER"), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: "Testa connessione" }));
    await waitFor(() => expect(socket.onmessage).not.toBeNull());
    act(() =>
      socket.onmessage?.({
        data: JSON.stringify({ type: "credentials_test", test: testResult("ws-without-default", "only") }),
      }),
    );

    expect(await screen.findByText("Autenticazione confermata")).toBeInTheDocument();
  });

  test("preserves Error details from HTTP test refresh", async () => {
    const socket = {
      close: vi.fn(),
      onmessage: null as ((event: { data: string }) => void) | null,
      onerror: null as (() => void) | null,
    };
    apiMocks.createElaborazioneCredentialTestWebSocket.mockReturnValue(socket);
    apiMocks.testElaborazioneCredentials.mockResolvedValue({
      ...testResult("refresh-object", "primary"),
      status: "pending",
      success: null,
      authenticated: null,
      verified_at: null,
    });
    apiMocks.getElaborazioneCredentialTest.mockRejectedValue(new Error("refresh object"));
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo primary");
    fireEvent.click(screen.getByRole("button", { name: "Testa connessione" }));
    await waitFor(() => expect(socket.onerror).not.toBeNull());
    act(() => socket.onerror?.());

    expect(await screen.findByText("refresh object")).toBeInTheDocument();
  });

  test("keeps polling state when realtime transport is unavailable", async () => {
    apiMocks.createElaborazioneCredentialTestWebSocket.mockReturnValue(null);
    apiMocks.testElaborazioneCredentials.mockResolvedValue({
      ...testResult("without-socket", "primary"),
      status: "pending",
      success: null,
      authenticated: null,
      verified_at: null,
    });
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo primary");
    fireEvent.click(screen.getByRole("button", { name: "Testa connessione" }));

    expect(await screen.findByText("Test in lavorazione")).toBeInTheDocument();
    expect(apiMocks.createElaborazioneCredentialTestWebSocket).toHaveBeenCalledWith("without-socket", "token");
  });

  test.each([
    ["gia' in sessione su SISTER", "Sessione SISTER gia' attiva"],
    ["gia in sessione su SISTER", "Sessione SISTER gia' attiva"],
    ["accesso da altra postazione", "Sessione SISTER gia' attiva"],
    ["sessione su altro browser", "Sessione SISTER gia' attiva"],
  ])("recognizes the existing-session message %s", async (message, expectedTitle) => {
    apiMocks.testElaborazioneCredentials.mockResolvedValue({
      ...testResult("session", "primary"),
      success: false,
      reachable: false,
      authenticated: false,
      message,
    });
    render(<ElaborazioniSettingsWorkspace embedded={!message.includes("altro browser")} />);
    await screen.findAllByText("Profilo primary");
    fireEvent.click(screen.getByRole("button", { name: "Testa connessione" }));

    expect(await screen.findByText(expectedTitle)).toBeInTheDocument();
    expect(screen.getByText(/Chiudi eventuali sessioni SISTER/)).toBeInTheDocument();
  });

  test.each([
    [
      { success: true, reachable: true, authenticated: false, message: "reachable", mode: null },
      "Portale raggiungibile",
    ],
    [
      { success: false, reachable: false, authenticated: false, message: null, mode: null },
      "Test connessione fallito",
    ],
    [
      { success: false, reachable: null, authenticated: null, message: null, mode: null },
      "Test connessione fallito",
    ],
  ])("renders non-authenticated test diagnostics %#", async (overrides, expectedTitle) => {
    apiMocks.testElaborazioneCredentials.mockResolvedValue({
      ...testResult("diagnostic", "primary"),
      ...overrides,
    });
    render(<ElaborazioniSettingsWorkspace />);
    await screen.findAllByText("Profilo primary");
    fireEvent.click(screen.getByRole("button", { name: "Testa connessione" }));

    expect(await screen.findByText(expectedTitle)).toBeInTheDocument();
    expect(screen.getByText(/Modalita': worker/)).toBeInTheDocument();
  });
});
