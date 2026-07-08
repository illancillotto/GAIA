import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { AnprStatusCard } from "@/components/anagrafica/AnprStatusCard";
import type { AnprSubjectStatus } from "@/types/api";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  getCurrentUser: vi.fn(),
  getUtenzeAnprStatus: vi.fn(),
  verifyUtenzeAnprAlive: vi.fn(),
  verifyUtenzeAnprDeathDate: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", () => ({
  getCurrentUser: mocks.getCurrentUser,
  getUtenzeAnprStatus: mocks.getUtenzeAnprStatus,
  verifyUtenzeAnprAlive: mocks.verifyUtenzeAnprAlive,
  verifyUtenzeAnprDeathDate: mocks.verifyUtenzeAnprDeathDate,
}));

function buildStatus(overrides: Partial<AnprSubjectStatus> = {}): AnprSubjectStatus {
  return {
    subject_id: overrides.subject_id ?? "subject-1",
    anpr_id: overrides.anpr_id ?? "ANPR-123",
    stato_anpr: overrides.stato_anpr ?? "unknown",
    data_decesso: overrides.data_decesso ?? null,
    luogo_decesso_comune: overrides.luogo_decesso_comune ?? null,
    last_anpr_check_at: overrides.last_anpr_check_at ?? null,
    last_c030_check_at: overrides.last_c030_check_at ?? null,
    capacitas_deceduto: overrides.capacitas_deceduto ?? null,
    capacitas_last_check_at: overrides.capacitas_last_check_at ?? null,
  };
}

describe("AnprStatusCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.getCurrentUser.mockResolvedValue({ id: 7, role: "reviewer", username: "reviewer" });
    mocks.getUtenzeAnprStatus.mockResolvedValue(buildStatus());
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  test("shows both verify actions for reviewer", async () => {
    render(<AnprStatusCard subjectId="subject-1" initialStatus={buildStatus()} />);

    expect(await screen.findByRole("button", { name: "Verifica se vivo" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Verifica data morte" })).toBeInTheDocument();
  });

  test("calls verify alive endpoint and refreshes status", async () => {
    const onStatusUpdated = vi.fn();
    mocks.verifyUtenzeAnprAlive.mockResolvedValue({
      subject_id: "subject-1",
      success: true,
      esito: "alive",
      data_decesso: null,
      anpr_id: "ANPR-123",
      calls_made: 1,
      message: "Soggetto presente in ANPR e non deceduto",
    });
    mocks.getUtenzeAnprStatus.mockResolvedValueOnce(buildStatus()).mockResolvedValueOnce(buildStatus({ stato_anpr: "alive" }));

    render(<AnprStatusCard subjectId="subject-1" initialStatus={buildStatus()} onStatusUpdated={onStatusUpdated} />);

    fireEvent.click(await screen.findByRole("button", { name: "Verifica se vivo" }));

    await waitFor(() => {
      expect(mocks.verifyUtenzeAnprAlive).toHaveBeenCalledWith("token", "subject-1");
    });
    expect(await screen.findByText("Soggetto presente in ANPR e non deceduto")).toBeInTheDocument();
    await waitFor(() => {
      expect(onStatusUpdated).toHaveBeenCalledWith(expect.objectContaining({ stato_anpr: "alive" }));
    });
  });

  test("calls verify death date endpoint and shows inferred date message", async () => {
    mocks.verifyUtenzeAnprDeathDate.mockResolvedValue({
      subject_id: "subject-1",
      success: true,
      esito: "deceased",
      data_decesso: "2025-08-20",
      anpr_id: "ANPR-123",
      calls_made: 4,
      message: "Data decesso determinata.",
    });
    mocks.getUtenzeAnprStatus
      .mockResolvedValueOnce(buildStatus({ stato_anpr: "deceased" }))
      .mockResolvedValueOnce(buildStatus({ stato_anpr: "deceased", data_decesso: "2025-08-20" }));

    render(<AnprStatusCard subjectId="subject-1" initialStatus={buildStatus({ stato_anpr: "deceased" })} />);

    fireEvent.click(await screen.findByRole("button", { name: "Verifica data morte" }));

    await waitFor(() => {
      expect(mocks.verifyUtenzeAnprDeathDate).toHaveBeenCalledWith("token", "subject-1");
    });
    expect(await screen.findByText("Data decesso determinata.")).toBeInTheDocument();
  });

  test("shows session error when no token is available", async () => {
    mocks.getStoredAccessToken.mockReturnValue("token");

    render(<AnprStatusCard subjectId="subject-1" initialStatus={buildStatus()} />);

    const button = await screen.findByRole("button", { name: "Verifica se vivo" });
    mocks.getStoredAccessToken.mockReturnValue(null);
    fireEvent.click(button);

    expect(await screen.findByText("Sessione non disponibile. Effettua di nuovo il login.")).toBeInTheDocument();
  });

  test("shows generic error toast when verification action fails", async () => {
    mocks.verifyUtenzeAnprDeathDate.mockRejectedValue("boom");

    render(<AnprStatusCard subjectId="subject-1" initialStatus={buildStatus({ stato_anpr: "deceased" })} />);

    fireEvent.click(await screen.findByRole("button", { name: "Verifica data morte" }));

    expect(await screen.findByText("Errore durante la verifica ANPR")).toBeInTheDocument();
  });

  test("shows error message from Error instances", async () => {
    mocks.verifyUtenzeAnprAlive.mockRejectedValue(new Error("Errore PDND esplicito"));

    render(<AnprStatusCard subjectId="subject-1" initialStatus={buildStatus()} />);

    fireEvent.click(await screen.findByRole("button", { name: "Verifica se vivo" }));

    expect(await screen.findByText("Errore PDND esplicito")).toBeInTheDocument();
  });

  test("keeps optimistic state when refresh after action fails", async () => {
    mocks.verifyUtenzeAnprAlive.mockResolvedValue({
      subject_id: "subject-1",
      success: false,
      esito: "error",
      data_decesso: null,
      anpr_id: "ANPR-123",
      calls_made: 1,
      message: "Errore ANPR operativo",
    });
    mocks.getUtenzeAnprStatus.mockResolvedValueOnce(buildStatus()).mockRejectedValueOnce(new Error("refresh failed"));

    render(<AnprStatusCard subjectId="subject-1" initialStatus={buildStatus()} />);

    fireEvent.click(await screen.findByRole("button", { name: "Verifica se vivo" }));

    expect(await screen.findByText("Errore ANPR operativo")).toBeInTheDocument();
    expect(screen.getByText("Errore ANPR")).toBeInTheDocument();
  });

  test("keeps the action buttons when status refresh fails but user fallback succeeds", async () => {
    mocks.getUtenzeAnprStatus.mockRejectedValueOnce(new Error("status failed"));
    mocks.getCurrentUser.mockRejectedValueOnce(new Error("parallel user failed")).mockResolvedValueOnce({
      id: 7,
      role: "reviewer",
      username: "reviewer",
    });

    render(<AnprStatusCard subjectId="subject-1" />);

    expect(await screen.findByRole("button", { name: "Verifica se vivo" })).toBeInTheDocument();
    expect(screen.getByText("Mai verificato")).toBeInTheDocument();
  });

  test("falls back to null current user when both status and user loading fail", async () => {
    mocks.getUtenzeAnprStatus.mockRejectedValueOnce(new Error("status failed"));
    mocks.getCurrentUser.mockRejectedValueOnce(new Error("user failed")).mockRejectedValueOnce(new Error("user failed"));

    render(<AnprStatusCard subjectId="subject-1" />);

    await waitFor(() => {
      expect(screen.queryByRole("button", { name: "Verifica se vivo" })).not.toBeInTheDocument();
    });
    expect(screen.getByText("Mai verificato")).toBeInTheDocument();
  });

  test("hides actions and stops loading when no token is available on mount", async () => {
    mocks.getStoredAccessToken.mockReturnValue(null);

    render(<AnprStatusCard subjectId="subject-1" />);

    await waitFor(() => {
      expect(screen.queryByRole("button", { name: "Verifica se vivo" })).not.toBeInTheDocument();
    });
    expect(screen.getByText("Mai verificato")).toBeInTheDocument();
  });

  test("renders warning and error badges for mapped ANPR states", async () => {
    const { rerender } = render(
      <AnprStatusCard subjectId="subject-1" initialStatus={buildStatus({ stato_anpr: "not_found_anpr" })} />,
    );

    expect(await screen.findByText("Non trovato in ANPR")).toBeInTheDocument();

    rerender(<AnprStatusCard subjectId="subject-1" initialStatus={buildStatus({ stato_anpr: "cancelled_anpr" })} />);
    expect(await screen.findByText("Cancellato in ANPR")).toBeInTheDocument();

    rerender(<AnprStatusCard subjectId="subject-1" initialStatus={buildStatus({ stato_anpr: "error" })} />);
    expect(await screen.findByText("Errore ANPR")).toBeInTheDocument();
  });

  test("maps sync results for not found and cancelled outcomes", async () => {
    mocks.verifyUtenzeAnprAlive
      .mockResolvedValueOnce({
        subject_id: "subject-1",
        success: false,
        esito: "not_found",
        data_decesso: null,
        anpr_id: null,
        calls_made: 1,
        message: "Soggetto non trovato in ANPR",
      })
      .mockResolvedValueOnce({
        subject_id: "subject-1",
        success: false,
        esito: "cancelled",
        data_decesso: null,
        anpr_id: null,
        calls_made: 1,
        message: "Soggetto cancellato in ANPR",
      });
    mocks.getUtenzeAnprStatus
      .mockResolvedValueOnce(buildStatus())
      .mockRejectedValueOnce(new Error("refresh failed"))
      .mockRejectedValueOnce(new Error("refresh failed"));

    render(<AnprStatusCard subjectId="subject-1" initialStatus={buildStatus()} />);

    fireEvent.click(await screen.findByRole("button", { name: "Verifica se vivo" }));
    expect(await screen.findByText("Non trovato in ANPR")).toBeInTheDocument();
    expect(screen.getByText("Non determinabile: soggetto non presente in ANPR.")).toBeInTheDocument();
    expect(screen.queryByText("Mai verificato")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Verifica se vivo" }));
    expect(await screen.findByText("Cancellato in ANPR")).toBeInTheDocument();
    expect(screen.getByText("Non determinabile: posizione ANPR cancellata.")).toBeInTheDocument();
  });

  test("keeps the current status when the sync result esito is unknown", async () => {
    mocks.verifyUtenzeAnprAlive.mockResolvedValue({
      subject_id: "subject-1",
      success: true,
      esito: "custom_unmapped",
      data_decesso: null,
      anpr_id: "ANPR-123",
      calls_made: 1,
      message: "Esito non standard",
    });
    mocks.getUtenzeAnprStatus.mockResolvedValueOnce(buildStatus({ stato_anpr: "deceased" })).mockRejectedValueOnce(new Error("refresh failed"));

    render(<AnprStatusCard subjectId="subject-1" initialStatus={buildStatus({ stato_anpr: "deceased" })} />);

    fireEvent.click(await screen.findByRole("button", { name: "Verifica se vivo" }));

    await waitFor(() => {
      expect(screen.getAllByText(/Attenzione: deceduto/).length).toBeGreaterThan(0);
    });
  });

  test("falls back to unknown status when the sync result esito is unmapped and no current status exists", async () => {
    mocks.getUtenzeAnprStatus.mockRejectedValueOnce(new Error("status failed")).mockRejectedValueOnce(new Error("refresh failed"));
    mocks.getCurrentUser.mockRejectedValueOnce(new Error("parallel user failed")).mockResolvedValueOnce({
      id: 7,
      role: "reviewer",
      username: "reviewer",
    });
    mocks.verifyUtenzeAnprAlive.mockResolvedValue({
      subject_id: "subject-1",
      success: true,
      esito: "custom_unmapped",
      data_decesso: null,
      anpr_id: "ANPR-123",
      calls_made: 1,
      message: "Esito non standard",
    });

    render(<AnprStatusCard subjectId="subject-1" />);

    fireEvent.click(await screen.findByRole("button", { name: "Verifica se vivo" }));

    expect(await screen.findByText("Stato ANPR sconosciuto")).toBeInTheDocument();
  });

  test("renders the death municipality when available", async () => {
    mocks.getUtenzeAnprStatus.mockResolvedValueOnce(
      buildStatus({ stato_anpr: "deceased", luogo_decesso_comune: "Roma", data_decesso: "2025-08-20" }),
    );

    render(
      <AnprStatusCard
        subjectId="subject-1"
        initialStatus={buildStatus({ stato_anpr: "deceased", luogo_decesso_comune: "Roma", data_decesso: "2025-08-20" })}
      />,
    );

    expect(await screen.findByText("Comune: Roma")).toBeInTheDocument();
  });

  test("shows the last c030 check when the ANPR status was not found", async () => {
    mocks.getUtenzeAnprStatus.mockResolvedValueOnce(
      buildStatus({
        stato_anpr: "not_found_anpr",
        last_c030_check_at: "2026-07-08T10:15:00.000Z",
      }),
    );

    render(
      <AnprStatusCard
        subjectId="subject-1"
        initialStatus={buildStatus({
          stato_anpr: "not_found_anpr",
          last_c030_check_at: "2026-07-08T10:15:00.000Z",
        })}
      />,
    );

    expect(await screen.findByText("Non trovato in ANPR")).toBeInTheDocument();
    expect(screen.getByText("Non determinabile: soggetto non presente in ANPR.")).toBeInTheDocument();
    expect(screen.queryByText("Mai verificato")).not.toBeInTheDocument();
  });

  test("auto clears the toast and runs timeout cleanup", async () => {
    mocks.verifyUtenzeAnprAlive.mockResolvedValue({
      subject_id: "subject-1",
      success: true,
      esito: "alive",
      data_decesso: null,
      anpr_id: "ANPR-123",
      calls_made: 1,
      message: "Toast temporaneo",
    });
    mocks.getUtenzeAnprStatus.mockResolvedValueOnce(buildStatus()).mockRejectedValueOnce(new Error("refresh failed"));

    const { unmount } = render(<AnprStatusCard subjectId="subject-1" initialStatus={buildStatus()} />);

    fireEvent.click(await screen.findByRole("button", { name: "Verifica se vivo" }));
    expect(await screen.findByText("Toast temporaneo")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.queryByText("Toast temporaneo")).not.toBeInTheDocument();
    }, { timeout: 4500 });

    unmount();
  }, 10000);
});
