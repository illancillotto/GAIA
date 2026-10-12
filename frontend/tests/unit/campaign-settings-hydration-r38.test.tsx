import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { ElaborazioniSettingsWorkspace } from "@/components/elaborazioni/settings-workspace";
import type { ElaborazioneCredential, ElaborazioneCredentialStatus } from "@/types/api";

const apiMocks = vi.hoisted(() => ({
  getElaborazioneCredentials: vi.fn(),
  getElaborazioneBatches: vi.fn(),
  listBonificaOristaneseCredentials: vi.fn(),
  listCapacitasCredentials: vi.fn(),
  releaseElaborazioneCredentials: vi.fn(),
  updateElaborazioneCredential: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...await importOriginal<typeof import("@/lib/api")>(),
  ...apiMocks,
}));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: () => "r38-token" }));
vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children }: { children: ReactNode }) => <main>{children}</main>,
}));

function credential(id: string, overrides: Partial<ElaborazioneCredential> = {}): ElaborazioneCredential {
  return {
    id,
    user_id: 1,
    label: `Profilo ${id}`,
    sister_username: `user-${id}`,
    convenzione: `Convenzione ${id}`,
    codice_richiesta: `CODE-${id}`,
    ufficio_provinciale: "ORISTANO Territorio",
    active: true,
    is_default: false,
    schedule_enabled: false,
    availability_schedule: null,
    verified_at: null,
    created_at: "2026-10-11T08:00:00Z",
    updated_at: "2026-10-11T08:00:00Z",
    ...overrides,
  };
}

function status(
  credentials: ElaborazioneCredential[],
  defaultCredential: ElaborazioneCredential | null,
): ElaborazioneCredentialStatus {
  return {
    configured: credentials.length > 0,
    credentials,
    default_credential: defaultCredential,
    credential: defaultCredential,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

function editor() {
  return within(screen.getByRole("group", { name: "Editor credenziale SISTER" }));
}

function username() {
  return editor().getByPlaceholderText("Codice fiscale / username");
}

function selectCredential(label: string) {
  const card = screen.getByText(label).closest("article");
  expect(card).not.toBeNull();
  fireEvent.click(within(card!).getByRole("button", { name: "Modifica" }));
}

async function startRefresh(result: ReturnType<typeof deferred<ElaborazioneCredentialStatus>>) {
  apiMocks.getElaborazioneCredentials.mockReturnValueOnce(result.promise);
  fireEvent.click(screen.getByRole("button", { name: "Pausa e libera sessioni" }));
  await waitFor(() => expect(apiMocks.getElaborazioneCredentials).toHaveBeenCalledTimes(2));
  expect(apiMocks.releaseElaborazioneCredentials).toHaveBeenCalledWith("r38-token");
}

async function resolveRefresh(
  result: ReturnType<typeof deferred<ElaborazioneCredentialStatus>>,
  response: ElaborazioneCredentialStatus,
) {
  await act(async () => {
    result.resolve(response);
    await result.promise;
  });
}

describe("R38 mounted SISTER credential refresh", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    window.history.replaceState(null, "", "/elaborazioni/settings");
    const primary = credential("primary", { is_default: true });
    apiMocks.getElaborazioneCredentials.mockResolvedValue(status([primary, credential("secondary")], primary));
    apiMocks.getElaborazioneBatches.mockResolvedValue([]);
    apiMocks.listBonificaOristaneseCredentials.mockResolvedValue([]);
    apiMocks.listCapacitasCredentials.mockResolvedValue([]);
    apiMocks.releaseElaborazioneCredentials.mockResolvedValue({ message: "Sessioni liberate R38" });
  });

  test("projects all loaded default fields without adopting its schedule", async () => {
    const primary = credential("primary", {
      label: "Default aggiornato",
      sister_username: "account-default",
      convenzione: null,
      codice_richiesta: null,
      ufficio_provinciale: "NUORO Territorio",
      active: false,
      is_default: true,
      schedule_enabled: true,
    });
    apiMocks.getElaborazioneCredentials.mockResolvedValue(status([primary], primary));
    render(<ElaborazioniSettingsWorkspace embedded />);
    await waitFor(() => expect(username()).toHaveValue("account-default"));
    expect(editor().getByPlaceholderText("SISTER principale")).toHaveValue("Default aggiornato");
    expect(editor().getByPlaceholderText("CONSORZIO DI BONIFICA DELL'ORISTANESE")).toHaveValue("");
    expect(editor().getByPlaceholderText("C00024602008")).toHaveValue("");
    expect(editor().getByRole("textbox", { name: "Ufficio provinciale" })).toHaveValue("NUORO Territorio");
    expect(editor().getByRole("checkbox", { name: "Credenziale attiva per i batch automatici" })).not.toBeChecked();
    expect(editor().getByRole("checkbox", { name: "Usa come profilo predefinito del worker" })).toBeChecked();
    expect(editor().getByRole("button", { name: "Sempre disponibile" })).toHaveAttribute("aria-pressed", "true");
    expect(editor().getByPlaceholderText("Password SISTER")).toHaveValue("");
    expect(screen.getByRole("button", { name: "Aggiorna credenziale" })).toBeEnabled();
  });

  test("selected blank username wins over the default and preserves password and schedule drafts", async () => {
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo secondary");
    selectCredential("Profilo secondary");
    fireEvent.change(username(), { target: { value: "" } });
    fireEvent.change(editor().getByPlaceholderText("Password SISTER"), { target: { value: "password-in-bozza" } });
    fireEvent.click(editor().getByRole("button", { name: "Fasce personalizzate" }));
    fireEvent.change(editor().getByLabelText("Lunedi dalle"), { target: { value: "17:45" } });
    const reload = deferred<ElaborazioneCredentialStatus>();
    await startRefresh(reload);
    const selected = credential("secondary", {
      label: "Selezionata aggiornata",
      sister_username: "",
      convenzione: null,
      codice_richiesta: "SELECTED-CODE",
      ufficio_provinciale: "CAGLIARI Territorio",
      active: false,
      is_default: false,
      schedule_enabled: false,
    });
    const primary = credential("primary", { is_default: true });
    await resolveRefresh(reload, status([primary, selected], primary));
    expect(editor().getByPlaceholderText("SISTER principale")).toHaveValue("Selezionata aggiornata");
    expect(username()).toHaveValue("");
    expect(editor().getByPlaceholderText("CONSORZIO DI BONIFICA DELL'ORISTANESE")).toHaveValue("");
    expect(editor().getByPlaceholderText("C00024602008")).toHaveValue("SELECTED-CODE");
    expect(editor().getByRole("textbox", { name: "Ufficio provinciale" })).toHaveValue("CAGLIARI Territorio");
    expect(editor().getByRole("checkbox", { name: "Credenziale attiva per i batch automatici" })).not.toBeChecked();
    expect(editor().getByRole("checkbox", { name: "Usa come profilo predefinito del worker" })).not.toBeChecked();
    expect(editor().getByPlaceholderText("Password SISTER")).toHaveValue("password-in-bozza");
    expect(editor().getByRole("button", { name: "Fasce personalizzate" })).toHaveAttribute("aria-pressed", "true");
    expect(editor().getByLabelText("Lunedi dalle")).toHaveValue("17:45");
  });

  test("keeps a removed selection and its nonempty unsaved fields instead of applying default", async () => {
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo secondary");
    selectCredential("Profilo secondary");
    fireEvent.change(username(), { target: { value: "username-in-bozza" } });
    fireEvent.change(editor().getByPlaceholderText("SISTER principale"), { target: { value: "Label in bozza" } });
    fireEvent.change(editor().getByPlaceholderText("Password SISTER"), { target: { value: "password-in-bozza" } });
    const reload = deferred<ElaborazioneCredentialStatus>();
    await startRefresh(reload);
    const primary = credential("primary", { is_default: true });
    await resolveRefresh(reload, status([primary], primary));
    expect(screen.queryByText("Profilo secondary")).not.toBeInTheDocument();
    expect(username()).toHaveValue("username-in-bozza");
    expect(editor().getByPlaceholderText("SISTER principale")).toHaveValue("Label in bozza");
    expect(editor().getByPlaceholderText("Password SISTER")).toHaveValue("password-in-bozza");
    expect(screen.getByRole("button", { name: "Aggiorna credenziale" })).toBeEnabled();
  });

  test.each(["", " \t "])("falls back from a removed selection with blank username %j", async (blank) => {
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo secondary");
    selectCredential("Profilo secondary");
    fireEvent.change(username(), { target: { value: blank } });
    fireEvent.change(editor().getByPlaceholderText("Password SISTER"), { target: { value: "password-preservata" } });
    const reload = deferred<ElaborazioneCredentialStatus>();
    await startRefresh(reload);
    const primary = credential("primary", { label: "Nuovo default", is_default: true });
    await resolveRefresh(reload, status([primary], primary));
    expect(username()).toHaveValue("user-primary");
    expect(editor().getByPlaceholderText("SISTER principale")).toHaveValue("Nuovo default");
    expect(editor().getByPlaceholderText("Password SISTER")).toHaveValue("password-preservata");
    expect(screen.getByRole("button", { name: "Aggiorna credenziale" })).toBeEnabled();
    apiMocks.updateElaborazioneCredential.mockResolvedValueOnce(primary);
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna credenziale" }));
    await waitFor(() => expect(apiMocks.updateElaborazioneCredential).toHaveBeenCalledWith(
      "r38-token",
      "primary",
      expect.objectContaining({ label: "Nuovo default", sister_username: "user-primary", sister_password: "password-preservata" }),
    ));
    expect(await screen.findByText("Credenziale SISTER aggiornata.")).toBeInTheDocument();
  });

  test("preserves the removed selection when there is no default, even with a blank username", async () => {
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo secondary");
    selectCredential("Profilo secondary");
    fireEvent.change(username(), { target: { value: "   " } });
    const reload = deferred<ElaborazioneCredentialStatus>();
    await startRefresh(reload);
    await resolveRefresh(reload, status([credential("other")], null));
    expect(username()).toHaveValue("   ");
    expect(editor().getByPlaceholderText("SISTER principale")).toHaveValue("Profilo secondary");
    expect(screen.getByRole("button", { name: "Nuova credenziale" })).toBeEnabled();
  });

  test.each([
    { name: "selected", failure: new Error("Reload R38 non disponibile"), keepSelected: true },
    { name: "default", failure: "reload raw R38", keepSelected: false },
  ])("preserves drafts on failed reload, then recovers through $name projection", async ({ failure, keepSelected }) => {
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo secondary");
    selectCredential("Profilo secondary");
    fireEvent.change(username(), { target: { value: "   " } });
    fireEvent.change(editor().getByPlaceholderText("SISTER principale"), { target: { value: "Label non salvata" } });
    fireEvent.change(editor().getByPlaceholderText("Password SISTER"), { target: { value: "password-dopo-failure" } });
    fireEvent.click(editor().getByRole("button", { name: "Fasce personalizzate" }));
    fireEvent.change(editor().getByLabelText("Lunedi dalle"), { target: { value: "18:15" } });
    apiMocks.getElaborazioneCredentials.mockRejectedValueOnce(failure);
    fireEvent.click(screen.getByRole("button", { name: "Pausa e libera sessioni" }));
    const errorMessage = failure instanceof Error ? failure.message : "Errore caricamento credenziali";
    expect(await screen.findByText(errorMessage)).toBeInTheDocument();
    expect(username()).toHaveValue("   ");
    expect(editor().getByPlaceholderText("SISTER principale")).toHaveValue("Label non salvata");
    expect(editor().getByPlaceholderText("Password SISTER")).toHaveValue("password-dopo-failure");
    expect(editor().getByRole("button", { name: "Fasce personalizzate" })).toHaveAttribute("aria-pressed", "true");
    expect(editor().getByLabelText("Lunedi dalle")).toHaveValue("18:15");
    expect(screen.getByText("Profilo secondary")).toBeInTheDocument();
    const recovery = deferred<ElaborazioneCredentialStatus>();
    apiMocks.getElaborazioneCredentials.mockReturnValueOnce(recovery.promise);
    await waitFor(() => expect(screen.getByRole("button", { name: "Pausa e libera sessioni" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Pausa e libera sessioni" }));
    await waitFor(() => expect(apiMocks.getElaborazioneCredentials).toHaveBeenCalledTimes(3));
    const primary = credential("primary", { label: "Default ripristinato", sister_username: "default-recovery", is_default: true });
    const secondary = credential("secondary", { label: "Selezionata ripristinata", sister_username: "selected-recovery" });
    await resolveRefresh(recovery, status(keepSelected ? [primary, secondary] : [primary], primary));
    expect(screen.queryByText(errorMessage)).not.toBeInTheDocument();
    expect(username()).toHaveValue(keepSelected ? "selected-recovery" : "default-recovery");
    expect(editor().getByPlaceholderText("SISTER principale")).toHaveValue(keepSelected ? "Selezionata ripristinata" : "Default ripristinato");
    expect(editor().getByPlaceholderText("Password SISTER")).toHaveValue("password-dopo-failure");
    expect(editor().getByRole("button", { name: "Fasce personalizzate" })).toHaveAttribute("aria-pressed", "true");
    expect(editor().getByLabelText("Lunedi dalle")).toHaveValue("18:15");
  });

  test("preserves a new nonempty draft typed while the initial credentials request is pending", async () => {
    const initial = deferred<ElaborazioneCredentialStatus>();
    apiMocks.getElaborazioneCredentials.mockReturnValueOnce(initial.promise);
    render(<ElaborazioniSettingsWorkspace embedded />);
    fireEvent.change(username(), { target: { value: "nuovo-username" } });
    fireEvent.change(editor().getByPlaceholderText("Password SISTER"), { target: { value: "nuova-password" } });
    fireEvent.change(editor().getByPlaceholderText("SISTER principale"), { target: { value: "Nuovo profilo in bozza" } });
    const primary = credential("primary", { is_default: true });
    await resolveRefresh(initial, status([primary], primary));
    expect(username()).toHaveValue("nuovo-username");
    expect(editor().getByPlaceholderText("Password SISTER")).toHaveValue("nuova-password");
    expect(editor().getByPlaceholderText("SISTER principale")).toHaveValue("Nuovo profilo in bozza");
    expect(screen.getByRole("button", { name: "Aggiungi credenziale" })).toBeEnabled();
  });

  test("reads the selection made during a pending refresh rather than the request-start selection", async () => {
    render(<ElaborazioniSettingsWorkspace embedded />);
    await screen.findByText("Profilo secondary");
    const reload = deferred<ElaborazioneCredentialStatus>();
    await startRefresh(reload);
    selectCredential("Profilo secondary");
    const primary = credential("primary", { label: "Primary aggiornato", is_default: true });
    const secondary = credential("secondary", { label: "Secondary aggiornato", sister_username: "secondario-refresh" });
    await resolveRefresh(reload, status([primary, secondary], primary));
    expect(editor().getByPlaceholderText("SISTER principale")).toHaveValue("Secondary aggiornato");
    expect(username()).toHaveValue("secondario-refresh");
  });

  test("applies reverse-completion responses in completion order without losing the current password", async () => {
    const initial = deferred<ElaborazioneCredentialStatus>();
    apiMocks.getElaborazioneCredentials.mockReturnValueOnce(initial.promise);
    render(<ElaborazioniSettingsWorkspace embedded />);
    const release = deferred<ElaborazioneCredentialStatus>();
    await startRefresh(release);
    const newer = credential("shared", { label: "Release completata prima", is_default: true });
    await resolveRefresh(release, status([newer], newer));
    expect(editor().getByPlaceholderText("SISTER principale")).toHaveValue("Release completata prima");
    fireEvent.change(editor().getByPlaceholderText("Password SISTER"), { target: { value: "password-tra-risposte" } });
    const older = credential("shared", { label: "Iniziale completata dopo", sister_username: "risposta-iniziale", is_default: true });
    await resolveRefresh(initial, status([older], older));
    expect(editor().getByPlaceholderText("SISTER principale")).toHaveValue("Iniziale completata dopo");
    expect(username()).toHaveValue("risposta-iniziale");
    expect(editor().getByPlaceholderText("Password SISTER")).toHaveValue("password-tra-risposte");
    expect(apiMocks.getElaborazioneCredentials).toHaveBeenNthCalledWith(1, "r38-token");
    expect(apiMocks.getElaborazioneCredentials).toHaveBeenNthCalledWith(2, "r38-token");
  });
});
