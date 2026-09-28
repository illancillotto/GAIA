import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { PresenzeCredentialVault } from "@/components/presenze/presenze-credential-vault";
import type { PresenzeCredential } from "@/types/api";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  listPresenzeCredentials: vi.fn(),
  createPresenzeCredential: vi.fn(),
  updatePresenzeCredential: vi.fn(),
  deletePresenzeCredential: vi.fn(),
  testPresenzeCredential: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", () => ({
  listPresenzeCredentials: mocks.listPresenzeCredentials,
  createPresenzeCredential: mocks.createPresenzeCredential,
  updatePresenzeCredential: mocks.updatePresenzeCredential,
  deletePresenzeCredential: mocks.deletePresenzeCredential,
  testPresenzeCredential: mocks.testPresenzeCredential,
}));

function credential(overrides: Partial<PresenzeCredential> = {}): PresenzeCredential {
  return {
    id: 4,
    application_user_id: 1,
    label: "Ufficio HR",
    username: "hr.inaz",
    active: true,
    last_used_at: "2026-07-06T15:44:35Z",
    last_authenticated_url: "https://serviziweb.inaz.it/portalecbo/default.aspx",
    last_error: null,
    consecutive_failures: 0,
    created_at: "2026-05-29T09:00:00Z",
    updated_at: "2026-05-29T09:00:00Z",
    ...overrides,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((next) => {
    resolve = next;
  });
  return { promise, resolve };
}

describe("PresenzeCredentialVault", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.listPresenzeCredentials.mockResolvedValue([credential()]);
    mocks.createPresenzeCredential.mockResolvedValue(credential({ id: 5, label: "Admin Presenze" }));
    mocks.updatePresenzeCredential.mockResolvedValue(credential());
    mocks.deletePresenzeCredential.mockResolvedValue(undefined);
    mocks.testPresenzeCredential.mockResolvedValue({ authenticated_url: "https://serviziweb.inaz.it/ok" });
  });

  test("creates a portal credential", async () => {
    render(<PresenzeCredentialVault />);
    await screen.findByText("Ufficio HR");

    fireEvent.change(screen.getByLabelText("Label"), { target: { value: "Admin Presenze" } });
    fireEvent.change(screen.getByLabelText("Username portale"), { target: { value: "admin.inaz" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret123" } });
    fireEvent.click(screen.getByLabelText("Credenziale attiva"));
    fireEvent.click(screen.getByText("Crea credenziale"));

    await waitFor(() => {
      expect(mocks.createPresenzeCredential).toHaveBeenCalledWith("token", {
        label: "Admin Presenze",
        username: "admin.inaz",
        password: "secret123",
        active: false,
      });
    });
    expect(await screen.findByText("Credenziale portale creata.")).toBeInTheDocument();
  });

  test("shows inactive credentials as recoverable and surfaces warnings", async () => {
    mocks.listPresenzeCredentials.mockResolvedValue([
      credential({ id: 4, active: false, last_error: null, last_authenticated_url: null }),
      credential({ id: 8, label: "Warning", active: true, last_error: "Login rifiutato" }),
    ]);

    render(<PresenzeCredentialVault />);

    expect(await screen.findByText("Disattiva")).toBeInTheDocument();
    expect(screen.getByText(/Non verra usata dalle sync/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Test e riattiva" })).toBeInTheDocument();
    expect(screen.getByText("Attiva con warning")).toBeInTheDocument();
    expect(screen.getByText("Login rifiutato")).toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  test("updates, cancels and deletes the selected credential", async () => {
    render(<PresenzeCredentialVault />);
    fireEvent.click(await screen.findByRole("button", { name: "Elimina" }));
    expect(await screen.findByText("Credenziale portale eliminata.")).toBeInTheDocument();
    expect(screen.getByText("Nuova credenziale portale")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Modifica" }));

    expect(screen.getByText("Modifica credenziale #4")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "rotated" } });
    fireEvent.click(screen.getByRole("button", { name: "Annulla modifica" }));
    expect(screen.getByText("Nuova credenziale portale")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Modifica" }));
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna credenziale" }));

    await waitFor(() => {
      expect(mocks.updatePresenzeCredential).toHaveBeenCalledWith("token", 4, {
        label: "Ufficio HR",
        username: "hr.inaz",
        password: undefined,
        active: true,
      });
    });

    fireEvent.click(screen.getByRole("button", { name: "Modifica" }));
    fireEvent.click(screen.getByRole("button", { name: "Elimina" }));

    await waitFor(() => {
      expect(mocks.deletePresenzeCredential).toHaveBeenCalledWith("token", 4);
    });
    expect(await screen.findByText("Credenziale portale eliminata.")).toBeInTheDocument();
    expect(screen.getByText("Nuova credenziale portale")).toBeInTheDocument();
  });

  test("verifies a portal login and reports a missing authenticated url", async () => {
    const pending = deferred<{ authenticated_url: string | null }>();
    mocks.testPresenzeCredential.mockReturnValueOnce(pending.promise);
    render(<PresenzeCredentialVault />);

    fireEvent.click(await screen.findByRole("button", { name: "Test" }));
    expect(screen.getByRole("button", { name: "Test..." })).toBeDisabled();
    pending.resolve({ authenticated_url: "https://serviziweb.inaz.it/ok" });

    expect(await screen.findByText(/Login portale verificato: https:\/\/serviziweb.inaz.it\/ok/)).toBeInTheDocument();

    mocks.testPresenzeCredential.mockResolvedValueOnce({ authenticated_url: null });
    fireEvent.click(screen.getByRole("button", { name: "Test" }));
    expect(await screen.findByText("Login portale verificato.")).toBeInTheDocument();
  });

  test("shows an empty vault and ignores actions without a token", async () => {
    mocks.listPresenzeCredentials.mockResolvedValueOnce([]);
    const view = render(<PresenzeCredentialVault />);

    expect(await screen.findByText("Nessuna credenziale portale")).toBeInTheDocument();

    mocks.getStoredAccessToken.mockReturnValue(null);
    fireEvent.click(screen.getByText("Crea credenziale"));
    expect(mocks.createPresenzeCredential).not.toHaveBeenCalled();

    view.unmount();
    render(<PresenzeCredentialVault />);
    expect(screen.getByText("Caricamento credenziali...")).toBeInTheDocument();
  });

  test("reports load, save, delete and test failures", async () => {
    mocks.listPresenzeCredentials.mockRejectedValueOnce(new Error("vault offline"));
    const view = render(<PresenzeCredentialVault />);
    expect(await screen.findByText("vault offline")).toBeInTheDocument();
    view.unmount();

    mocks.listPresenzeCredentials.mockRejectedValueOnce("boom");
    const stringFailure = render(<PresenzeCredentialVault />);
    expect(await screen.findByText("Errore caricamento credenziali portale")).toBeInTheDocument();
    stringFailure.unmount();

    mocks.listPresenzeCredentials.mockResolvedValue([credential()]);
    render(<PresenzeCredentialVault />);
    await screen.findByText("Ufficio HR");

    mocks.createPresenzeCredential.mockRejectedValueOnce(new Error("save failed"));
    fireEvent.change(screen.getByLabelText("Label"), { target: { value: "Nuova" } });
    fireEvent.change(screen.getByLabelText("Username portale"), { target: { value: "new.inaz" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret" } });
    fireEvent.click(screen.getByText("Crea credenziale"));
    expect(await screen.findByText("save failed")).toBeInTheDocument();

    mocks.updatePresenzeCredential.mockRejectedValueOnce("nope");
    fireEvent.click(screen.getByRole("button", { name: "Modifica" }));
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna credenziale" }));
    expect(await screen.findByText("Errore salvataggio credenziale portale")).toBeInTheDocument();

    mocks.deletePresenzeCredential.mockRejectedValueOnce(new Error("delete failed"));
    fireEvent.click(screen.getByRole("button", { name: "Elimina" }));
    expect(await screen.findByText("delete failed")).toBeInTheDocument();

    mocks.getStoredAccessToken.mockReturnValueOnce(null);
    fireEvent.click(screen.getByRole("button", { name: "Elimina" }));
    expect(mocks.deletePresenzeCredential).toHaveBeenCalledTimes(1);

    mocks.testPresenzeCredential.mockRejectedValueOnce("bad");
    fireEvent.click(screen.getByRole("button", { name: "Test" }));
    expect(await screen.findByText("Errore test credenziale portale")).toBeInTheDocument();

    mocks.getStoredAccessToken.mockReturnValueOnce(null);
    fireEvent.click(screen.getByRole("button", { name: "Test" }));
    expect(mocks.testPresenzeCredential).toHaveBeenCalledTimes(1);
  });

  test("keeps the saving label while the create request is in flight", async () => {
    const pending = deferred<PresenzeCredential>();
    mocks.createPresenzeCredential.mockReturnValueOnce(pending.promise);
    render(<PresenzeCredentialVault />);
    await screen.findByText("Ufficio HR");

    fireEvent.change(screen.getByLabelText("Label"), { target: { value: "Nuova" } });
    fireEvent.change(screen.getByLabelText("Username portale"), { target: { value: "new.inaz" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret" } });
    fireEvent.click(screen.getByText("Crea credenziale"));

    expect(screen.getByRole("button", { name: "Salvataggio..." })).toBeDisabled();
    pending.resolve(credential({ id: 9 }));
    expect(await screen.findByText("Credenziale portale creata.")).toBeInTheDocument();
  });
});
