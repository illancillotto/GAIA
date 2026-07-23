import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { ElaborazioniPostaOnlineWorkspace } from "@/components/elaborazioni/posta-online-workspace";

const apiMocks = vi.hoisted(() => ({
  createPostaOnlineCredential: vi.fn(),
  createPostaOnlineRegisteredMailJob: vi.fn(),
  deletePostaOnlineCredential: vi.fn(),
  listPostaOnlineCredentials: vi.fn(),
  listPostaOnlineRegisteredMailJobs: vi.fn(),
  rerunPostaOnlineRegisteredMailJob: vi.fn(),
  testPostaOnlineCredential: vi.fn(),
  updatePostaOnlineCredential: vi.fn(),
}));

const authMocks = vi.hoisted(() => ({
  token: "token" as string | null,
}));

vi.mock("@/lib/api", () => apiMocks);
vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: () => authMocks.token,
}));
vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children, title }: { children: ReactNode; title: string }) => (
    <main data-testid="protected-page">
      <h1>{title}</h1>
      {children}
    </main>
  ),
}));

function createCredential(overrides: Record<string, unknown> = {}) {
  return {
    id: 7,
    label: "Poste Business",
    username: "poste-user",
    active: true,
    allowed_hours_start: 0,
    allowed_hours_end: 23,
    min_delay_ms: 3500,
    max_delay_ms: 9000,
    last_used_at: null,
    last_error: null,
    consecutive_failures: 0,
    created_at: "2026-07-23T10:00:00Z",
    updated_at: "2026-07-23T10:00:00Z",
    ...overrides,
  };
}

function createJob(overrides: Record<string, unknown> = {}) {
  return {
    id: 11,
    credential_id: 7,
    requested_by_user_id: 1,
    status: "succeeded",
    mode: "credential_test",
    payload_json: { credential_id: 7 },
    result_json: { ok: true, checked_at: "2026-07-23T10:05:00Z" },
    error_detail: null,
    started_at: "2026-07-23T10:04:00Z",
    completed_at: "2026-07-23T10:05:00Z",
    created_at: "2026-07-23T10:04:00Z",
    updated_at: "2026-07-23T10:05:00Z",
    ...overrides,
  };
}

describe("ElaborazioniPostaOnlineWorkspace", () => {
  beforeEach(() => {
    authMocks.token = "token";
    Object.values(apiMocks).forEach((mock) => mock.mockReset());
    apiMocks.listPostaOnlineCredentials.mockResolvedValue([createCredential()]);
    apiMocks.listPostaOnlineRegisteredMailJobs.mockResolvedValue([createJob()]);
    apiMocks.createPostaOnlineCredential.mockResolvedValue({});
    apiMocks.testPostaOnlineCredential.mockResolvedValue({});
    apiMocks.createPostaOnlineRegisteredMailJob.mockResolvedValue({});
    apiMocks.updatePostaOnlineCredential.mockResolvedValue({});
    apiMocks.deletePostaOnlineCredential.mockResolvedValue({});
    apiMocks.rerunPostaOnlineRegisteredMailJob.mockResolvedValue({});
  });

  test("loads credentials and queues login/import jobs", async () => {
    render(<ElaborazioniPostaOnlineWorkspace embedded />);

    expect(await screen.findByText("Poste Business")).toBeInTheDocument();
    expect(screen.getByText("poste-user")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Test login" }));
    await waitFor(() => {
      expect(apiMocks.testPostaOnlineCredential).toHaveBeenCalledWith("token", 7, {
        min_delay_ms: 3500,
        max_delay_ms: 9000,
      });
    });

    fireEvent.click(screen.getByRole("button", { name: "Avvia import" }));
    await waitFor(() => {
      expect(apiMocks.createPostaOnlineRegisteredMailJob).toHaveBeenCalledWith("token", {
        credential_id: 7,
        annualita: [2022, 2023],
        include_contacts: true,
        include_details: true,
        max_pages: null,
        max_details: null,
        continue_on_error: true,
      });
    });

    fireEvent.change(screen.getByPlaceholderText("Etichetta"), { target: { value: "Poste secondaria" } });
    fireEvent.change(screen.getByPlaceholderText("Username Poste"), { target: { value: "new-user" } });
    fireEvent.change(screen.getByPlaceholderText("Password"), { target: { value: "new-secret" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva credenziale" }));

    await waitFor(() => {
      expect(apiMocks.createPostaOnlineCredential).toHaveBeenCalledWith("token", {
        label: "Poste secondaria",
        username: "new-user",
        password: "new-secret",
        min_delay_ms: 3500,
        max_delay_ms: 9000,
      });
    });
  });

  test("renders empty states and page wrapper", async () => {
    apiMocks.listPostaOnlineCredentials.mockResolvedValue([]);
    apiMocks.listPostaOnlineRegisteredMailJobs.mockResolvedValue([]);

    render(<ElaborazioniPostaOnlineWorkspace />);

    expect(await screen.findByTestId("protected-page")).toBeInTheDocument();
    expect(screen.getByText("Nessuna credenziale Poste")).toBeInTheDocument();
    expect(screen.getByText("Nessun job Poste")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Avvia import" })).toBeDisabled();
  });

  test("shows generic load error for non-error failures", async () => {
    apiMocks.listPostaOnlineCredentials.mockRejectedValueOnce("bad load");

    render(<ElaborazioniPostaOnlineWorkspace embedded />);

    expect(await screen.findByText("Errore caricamento Poste Online")).toBeInTheDocument();
  });

  test("handles credential toggle delete and rerun actions", async () => {
    apiMocks.listPostaOnlineCredentials.mockResolvedValue([
      createCredential({
        active: false,
        last_error: "ultimo errore",
        last_used_at: "2026-07-23T10:10:00Z",
      }),
    ]);
    apiMocks.listPostaOnlineRegisteredMailJobs.mockResolvedValue([
      createJob({
        id: 21,
        mode: "registered_mails",
        status: "completed_with_errors",
        result_json: {
          records_matched: 2,
          records_unmatched: 1,
          records_ambiguous: 3,
        },
      }),
      createJob({
        id: 22,
        mode: "registered_mails",
        status: "failed",
        error_detail: "job fallito",
      }),
    ]);

    render(<ElaborazioniPostaOnlineWorkspace embedded />);

    expect(await screen.findByText("ultimo errore")).toBeInTheDocument();
    expect(screen.getByText("Disattiva")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Attiva" }));
    await waitFor(() => {
      expect(apiMocks.updatePostaOnlineCredential).toHaveBeenCalledWith("token", 7, { active: true });
    });

    fireEvent.click(screen.getByRole("button", { name: "Elimina" }));
    await waitFor(() => {
      expect(apiMocks.deletePostaOnlineCredential).toHaveBeenCalledWith("token", 7);
    });

    fireEvent.click(screen.getAllByRole("button", { name: "Rilancia" })[0]);
    await waitFor(() => {
      expect(apiMocks.rerunPostaOnlineRegisteredMailJob).toHaveBeenCalledWith("token", 21);
    });
    expect(screen.getByText("job fallito")).toBeInTheDocument();
  });

  test("shows loading labels and handles operation errors", async () => {
    apiMocks.testPostaOnlineCredential.mockImplementation(() => new Promise(() => undefined));
    apiMocks.createPostaOnlineRegisteredMailJob.mockRejectedValue(new Error("import ko"));

    render(<ElaborazioniPostaOnlineWorkspace embedded />);

    expect(await screen.findByText("Poste Business")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Test login" }));
    expect(await screen.findByRole("button", { name: "Accodo..." })).toBeDisabled();

    apiMocks.testPostaOnlineCredential.mockReset();
    apiMocks.testPostaOnlineCredential.mockResolvedValue({});
  });

  test("handles load create toggle delete test import and rerun errors", async () => {
    apiMocks.listPostaOnlineCredentials.mockRejectedValueOnce(new Error("load ko"));

    render(<ElaborazioniPostaOnlineWorkspace embedded />);

    expect(await screen.findByText("load ko")).toBeInTheDocument();

    apiMocks.listPostaOnlineCredentials.mockResolvedValue([createCredential()]);
    apiMocks.listPostaOnlineRegisteredMailJobs.mockResolvedValue([createJob({ mode: "registered_mails", status: "succeeded" })]);
    apiMocks.createPostaOnlineCredential.mockRejectedValueOnce(new Error("create ko"));
    apiMocks.updatePostaOnlineCredential.mockRejectedValueOnce(new Error("toggle ko"));
    apiMocks.deletePostaOnlineCredential.mockRejectedValueOnce(new Error("delete ko"));
    apiMocks.testPostaOnlineCredential.mockRejectedValueOnce(new Error("test ko"));
    apiMocks.createPostaOnlineRegisteredMailJob.mockRejectedValueOnce(new Error("import ko"));
    apiMocks.rerunPostaOnlineRegisteredMailJob.mockRejectedValueOnce(new Error("rerun ko"));

    fireEvent.click(screen.getByRole("button", { name: "Aggiorna" }));
    expect(await screen.findByText("Poste Business")).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("Etichetta"), { target: { value: "Poste err" } });
    fireEvent.change(screen.getByPlaceholderText("Username Poste"), { target: { value: "user" } });
    fireEvent.change(screen.getByPlaceholderText("Password"), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva credenziale" }));
    expect(await screen.findByText("create ko")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Disattiva" }));
    expect(await screen.findByText("toggle ko")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Elimina" }));
    expect(await screen.findByText("delete ko")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Test login" }));
    expect(await screen.findByText("test ko")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/Credenziale/i), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Avvia import" }));
    expect(await screen.findByText("import ko")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Rilancia" }));
    expect(await screen.findByText("rerun ko")).toBeInTheDocument();
  });

  test("does not call APIs when token is missing", async () => {
    authMocks.token = null;
    render(<ElaborazioniPostaOnlineWorkspace embedded />);

    await waitFor(() => {
      expect(apiMocks.listPostaOnlineCredentials).not.toHaveBeenCalled();
    });
  });

  test("renders defensive fallbacks for unknown job status and non-object result", async () => {
    apiMocks.listPostaOnlineRegisteredMailJobs.mockResolvedValue([
      createJob({
        id: 31,
        status: "mystery",
        mode: "registered_mails",
        result_json: null,
      }),
      createJob({
        id: 32,
        status: "other",
        mode: "credential_test",
        result_json: [],
      }),
      createJob({
        id: 33,
        status: "succeeded",
        mode: "registered_mails",
        result_json: { records_matched: 5 },
      }),
      createJob({
        id: 34,
        status: "pending",
        mode: "registered_mails",
      }),
      createJob({
        id: 35,
        status: "queued_resume",
        mode: "credential_test",
      }),
    ]);

    render(<ElaborazioniPostaOnlineWorkspace embedded />);

    expect((await screen.findAllByText("mystery")).length).toBeGreaterThan(1);
    expect(screen.getByText("other")).toBeInTheDocument();
    expect(screen.getByText("In coda")).toBeInTheDocument();
    expect(screen.getByText("Ripresa in coda")).toBeInTheDocument();
    expect(screen.getByText("5 match · 0 non associati · 0 ambigui")).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });

  test("guards credential actions without token and shows generic non-error credential failures", async () => {
    render(<ElaborazioniPostaOnlineWorkspace embedded />);
    expect(await screen.findByText("Poste Business")).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("Etichetta"), { target: { value: "Poste generic" } });
    fireEvent.change(screen.getByPlaceholderText("Username Poste"), { target: { value: "generic-user" } });
    fireEvent.change(screen.getByPlaceholderText("Password"), { target: { value: "generic-secret" } });

    authMocks.token = null;
    fireEvent.click(screen.getByRole("button", { name: "Salva credenziale" }));
    fireEvent.click(screen.getByRole("button", { name: "Disattiva" }));
    fireEvent.click(screen.getByRole("button", { name: "Elimina" }));
    fireEvent.click(screen.getByRole("button", { name: "Test login" }));
    expect(apiMocks.createPostaOnlineCredential).not.toHaveBeenCalled();
    expect(apiMocks.updatePostaOnlineCredential).not.toHaveBeenCalled();
    expect(apiMocks.deletePostaOnlineCredential).not.toHaveBeenCalled();
    expect(apiMocks.testPostaOnlineCredential).not.toHaveBeenCalled();

    authMocks.token = "token";
    apiMocks.createPostaOnlineCredential.mockRejectedValueOnce("bad create");
    apiMocks.updatePostaOnlineCredential.mockRejectedValueOnce("bad toggle");
    apiMocks.deletePostaOnlineCredential.mockRejectedValueOnce("bad delete");
    apiMocks.testPostaOnlineCredential.mockRejectedValueOnce("bad test");

    fireEvent.click(screen.getByRole("button", { name: "Salva credenziale" }));
    expect(await screen.findByText("Errore salvataggio credenziale Poste Online")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Disattiva" }));
    expect(await screen.findByText("Errore aggiornamento credenziale Poste Online")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Elimina" }));
    expect(await screen.findByText("Errore eliminazione credenziale Poste Online")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Test login" }));
    expect(await screen.findByText("Errore accodamento test Poste Online")).toBeInTheDocument();
  });

  test("guards import and rerun without token and shows generic non-error failures", async () => {
    apiMocks.listPostaOnlineRegisteredMailJobs.mockResolvedValue([
      createJob({ mode: "registered_mails", status: "succeeded" }),
    ]);

    render(<ElaborazioniPostaOnlineWorkspace embedded />);
    expect(await screen.findByText("Poste Business")).toBeInTheDocument();

    apiMocks.createPostaOnlineRegisteredMailJob.mockClear();
    apiMocks.rerunPostaOnlineRegisteredMailJob.mockClear();
    authMocks.token = null;
    fireEvent.click(screen.getByRole("button", { name: "Avvia import" }));
    fireEvent.click(screen.getByRole("button", { name: "Rilancia" }));
    expect(apiMocks.createPostaOnlineRegisteredMailJob).not.toHaveBeenCalled();
    expect(apiMocks.rerunPostaOnlineRegisteredMailJob).not.toHaveBeenCalled();

    authMocks.token = "token";
    apiMocks.createPostaOnlineRegisteredMailJob.mockRejectedValueOnce("bad import");
    apiMocks.rerunPostaOnlineRegisteredMailJob.mockRejectedValueOnce("bad rerun");
    fireEvent.click(screen.getByRole("button", { name: "Avvia import" }));
    expect(await screen.findByText("Errore accodamento import Poste Online")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Rilancia" }));
    expect(await screen.findByText("Errore rilancio job Poste Online")).toBeInTheDocument();
  });

  test("polls while jobs are active and clears the interval on unmount", async () => {
    apiMocks.listPostaOnlineRegisteredMailJobs.mockResolvedValue([
      createJob({ status: "processing", mode: "registered_mails" }),
    ]);
    let intervalCallback: (() => void) | null = null;
    const setIntervalSpy = vi.spyOn(window, "setInterval").mockImplementation((callback) => {
      intervalCallback = callback as () => void;
      return 123 as unknown as ReturnType<typeof setInterval>;
    });
    const clearIntervalSpy = vi.spyOn(window, "clearInterval");

    const { unmount } = render(<ElaborazioniPostaOnlineWorkspace embedded />);
    expect(await screen.findByText(/Worker in attività/i)).toBeInTheDocument();

    await act(async () => {
      intervalCallback?.();
    });
    expect(apiMocks.listPostaOnlineCredentials).toHaveBeenCalledTimes(2);

    unmount();
    expect(clearIntervalSpy).toHaveBeenCalled();
    setIntervalSpy.mockRestore();
    clearIntervalSpy.mockRestore();
  });

  test("uses edited delay values when saving credentials", async () => {
    render(<ElaborazioniPostaOnlineWorkspace embedded />);

    expect(await screen.findByText("Poste Business")).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("Etichetta"), { target: { value: "Poste delay" } });
    fireEvent.change(screen.getByPlaceholderText("Username Poste"), { target: { value: "delay-user" } });
    fireEvent.change(screen.getByPlaceholderText("Password"), { target: { value: "delay-secret" } });
    fireEvent.change(screen.getByLabelText(/Delay minimo ms/i), { target: { value: "4500" } });
    fireEvent.change(screen.getByLabelText(/Delay massimo ms/i), { target: { value: "9500" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva credenziale" }));

    await waitFor(() => {
      expect(apiMocks.createPostaOnlineCredential).toHaveBeenCalledWith("token", {
        label: "Poste delay",
        username: "delay-user",
        password: "delay-secret",
        min_delay_ms: 4500,
        max_delay_ms: 9500,
      });
    });
  });
});
