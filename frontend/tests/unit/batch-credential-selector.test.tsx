import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { BatchCredentialSelector } from "@/components/elaborazioni/batch-credential-selector";
import type { ElaborazioneCredential } from "@/types/api";

const apiMocks = vi.hoisted(() => ({
  getElaborazioneCredentials: vi.fn(),
}));
const authState = vi.hoisted(() => ({ token: "token" as string | null }));

vi.mock("@/lib/api", () => apiMocks);
vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: () => authState.token,
}));

function credential(id: string, overrides: Partial<ElaborazioneCredential> = {}): ElaborazioneCredential {
  return {
    id,
    user_id: 1,
    label: `Profilo ${id}`,
    sister_username: `user-${id}`,
    convenzione: null,
    codice_richiesta: null,
    ufficio_provinciale: "ORISTANO Territorio",
    active: true,
    is_default: false,
    schedule_enabled: false,
    availability_schedule: null,
    verified_at: null,
    created_at: "2026-08-27T08:00:00Z",
    updated_at: "2026-08-27T08:00:00Z",
    ...overrides,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

function selectionRef(current: string[] = []) {
  return { current };
}

describe("BatchCredentialSelector", () => {
  beforeEach(() => {
    authState.token = "token";
    apiMocks.getElaborazioneCredentials.mockReset();
  });

  test("uses the automatic pool when no token or active credential is available", async () => {
    authState.token = null;
    const view = render(<BatchCredentialSelector selectionRef={selectionRef()} />);
    expect(screen.getByText("Nessuna credenziale SISTER attiva disponibile.")).toBeInTheDocument();
    expect(apiMocks.getElaborazioneCredentials).not.toHaveBeenCalled();

    authState.token = "token";
    apiMocks.getElaborazioneCredentials.mockResolvedValue({
      configured: true,
      credentials: [credential("inactive", { active: false })],
      default_credential: null,
      credential: null,
    });
    view.unmount();
    render(<BatchCredentialSelector disabled selectionRef={selectionRef()} />);
    await waitFor(() => expect(apiMocks.getElaborazioneCredentials).toHaveBeenCalledWith("token"));
    expect(screen.getByRole("group", { name: "Credenziali SISTER del batch" })).toBeDisabled();
  });

  test("selects and deselects active credentials while exposing their schedule", async () => {
    apiMocks.getElaborazioneCredentials.mockResolvedValue({
      configured: true,
      credentials: [
        credential("always"),
        credential("scheduled", { schedule_enabled: true }),
        credential("inactive", { active: false }),
      ],
      default_credential: null,
      credential: null,
    });
    const selected = selectionRef();
    render(<BatchCredentialSelector selectionRef={selected} />);

    const scheduled = await screen.findByRole("checkbox", { name: /Profilo scheduled/ });
    expect(screen.getByText(/Sempre disponibile/)).toBeInTheDocument();
    expect(screen.getByText(/Fasce orarie attive/)).toBeInTheDocument();
    expect(screen.queryByText("Profilo inactive")).not.toBeInTheDocument();
    fireEvent.click(scheduled);
    expect(selected.current).toEqual(["scheduled"]);

    fireEvent.click(screen.getByRole("checkbox", { name: /Profilo scheduled/ }));
    expect(selected.current).toEqual([]);
  });

  test.each([
    [new Error("Portale non disponibile"), "Portale non disponibile"],
    ["failure", "Errore caricamento credenziali SISTER"],
  ])("renders credential loading errors", async (failure, message) => {
    apiMocks.getElaborazioneCredentials.mockRejectedValue(failure);
    render(<BatchCredentialSelector selectionRef={selectionRef()} />);
    expect(await screen.findByText(message)).toBeInTheDocument();
  });

  test("ignores completed requests after unmount", async () => {
    const completed = deferred<unknown>();
    apiMocks.getElaborazioneCredentials.mockReturnValue(completed.promise);
    const view = render(<BatchCredentialSelector selectionRef={selectionRef()} />);
    view.unmount();
    completed.resolve({ configured: false, credentials: [], default_credential: null, credential: null });
    await completed.promise;

    const failed = deferred<unknown>();
    apiMocks.getElaborazioneCredentials.mockReturnValue(failed.promise);
    const secondView = render(<BatchCredentialSelector selectionRef={selectionRef()} />);
    secondView.unmount();
    failed.reject(new Error("ignored"));
    await expect(failed.promise).rejects.toThrow("ignored");
  });
});
