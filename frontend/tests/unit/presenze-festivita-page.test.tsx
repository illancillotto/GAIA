import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import PresenzeFestivitaPage from "@/app/presenze/festivita/page";
import type { PresenzeHoliday } from "@/types/api";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  listPresenzeHolidays: vi.fn(),
  bootstrapPresenzeHolidays: vi.fn(),
  createPresenzeHoliday: vi.fn(),
  updatePresenzeHoliday: vi.fn(),
  deletePresenzeHoliday: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", () => ({
  bootstrapPresenzeHolidays: mocks.bootstrapPresenzeHolidays,
  createPresenzeHoliday: mocks.createPresenzeHoliday,
  deletePresenzeHoliday: mocks.deletePresenzeHoliday,
  listPresenzeHolidays: mocks.listPresenzeHolidays,
  updatePresenzeHoliday: mocks.updatePresenzeHoliday,
}));

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children, title }: { children: React.ReactNode; title: string }) => (
    <div>
      <h1>{title}</h1>
      {children}
    </div>
  ),
}));

function holiday(overrides: Partial<PresenzeHoliday>): PresenzeHoliday {
  return {
    id: 1,
    holiday_date: "2026-05-01",
    label: "Festa del lavoro",
    company_code: null,
    holiday_kind: "ordinary",
    is_workday_override: false,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

const holidaysFixture: PresenzeHoliday[] = [
  holiday({ id: 1, holiday_date: "2026-05-01T00:00:00Z", holiday_kind: "ordinary" }),
  holiday({
    id: 2,
    holiday_date: "2026-04-25",
    label: "Liberazione",
    company_code: "53",
    holiday_kind: "ordinary",
  }),
  holiday({
    id: 3,
    holiday_date: "2026-11-04",
    label: "Unita nazionale",
    holiday_kind: "suppressed",
  }),
  holiday({
    id: 4,
    holiday_date: "2026-12-08",
    label: "Immacolata lavorativa",
    holiday_kind: "working_override",
  }),
];

describe("Presenze festivita page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Element.prototype.scrollIntoView = vi.fn();
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.listPresenzeHolidays.mockResolvedValue(holidaysFixture);
    mocks.bootstrapPresenzeHolidays.mockResolvedValue({ year: 2026, created: 2, items: holidaysFixture });
    mocks.createPresenzeHoliday.mockResolvedValue(holidaysFixture[0]);
    mocks.updatePresenzeHoliday.mockResolvedValue(holidaysFixture[0]);
    mocks.deletePresenzeHoliday.mockResolvedValue(undefined);
  });

  test("shows empty states when no holidays are configured", async () => {
    mocks.listPresenzeHolidays.mockResolvedValue([]);
    render(<PresenzeFestivitaPage />);
    expect(await screen.findByText("Nessuna festivita configurata")).toBeInTheDocument();
    expect(screen.getByText("Nessuna festivita soppressa")).toBeInTheDocument();
    expect(screen.getByText("Nessun override lavorativo")).toBeInTheDocument();
  });

  test("does not load holidays without a session token", async () => {
    mocks.getStoredAccessToken.mockReturnValue(null);
    render(<PresenzeFestivitaPage />);
    expect(await screen.findByText("Caricamento festivita...")).toBeInTheDocument();
    expect(mocks.listPresenzeHolidays).not.toHaveBeenCalled();
  });

  test("shows a load error and reloads with the current year when the year is invalid", async () => {
    mocks.listPresenzeHolidays.mockRejectedValueOnce(new Error("rete ko"));
    render(<PresenzeFestivitaPage />);
    expect(await screen.findByText("rete ko")).toBeInTheDocument();

    mocks.listPresenzeHolidays.mockResolvedValue([]);
    fireEvent.change(screen.getByLabelText("Anno"), { target: { value: "abcd" } });
    await waitFor(() => {
      expect(mocks.listPresenzeHolidays).toHaveBeenLastCalledWith("token", new Date().getFullYear());
    });
    fireEvent.change(screen.getByLabelText("Anno"), { target: { value: "1999" } });
    await waitFor(() => {
      expect(mocks.listPresenzeHolidays).toHaveBeenLastCalledWith("token", new Date().getFullYear());
    });
    fireEvent.change(screen.getByLabelText("Anno"), { target: { value: "2101" } });
    await waitFor(() => {
      expect(mocks.listPresenzeHolidays).toHaveBeenLastCalledWith("token", new Date().getFullYear());
    });
    fireEvent.change(screen.getByLabelText("Anno"), { target: { value: "2025" } });
    await waitFor(() => {
      expect(mocks.listPresenzeHolidays).toHaveBeenLastCalledWith("token", 2025);
    });
  });

  test("uses a generic load error when listing fails without an Error instance", async () => {
    mocks.listPresenzeHolidays.mockRejectedValueOnce("boom");
    render(<PresenzeFestivitaPage />);
    expect(await screen.findByText("Errore caricamento festivita giornaliere")).toBeInTheDocument();
  });

  test("clicking Modifica fills the editor, scrolls it into view and highlights the row", async () => {
    render(<PresenzeFestivitaPage />);
    const editButtons = await screen.findAllByRole("button", { name: "Modifica" });
    fireEvent.click(editButtons[0]);

    expect(screen.getByText("Modifica festivita")).toBeInTheDocument();
    expect(screen.getByLabelText("Data")).toHaveValue("2026-05-01");
    expect(screen.getByLabelText("Etichetta")).toHaveValue("Festa del lavoro");
    expect(screen.getByRole("button", { name: "Salva modifica" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "In modifica" })).toBeInTheDocument();
    expect(document.getElementById("festivita-editor")?.scrollIntoView).toHaveBeenCalledWith({
      behavior: "smooth",
      block: "start",
    });
    expect(screen.getByLabelText("Data")).toHaveFocus();

    fireEvent.click(screen.getByRole("button", { name: "Annulla modifica" }));
    expect(screen.getByText("Calendario festivita")).toBeInTheDocument();
    expect(screen.getByLabelText("Etichetta")).toHaveValue("");
  });

  test("creates ordinary, suppressed and working override holidays", async () => {
    render(<PresenzeFestivitaPage />);
    await screen.findAllByRole("button", { name: "Modifica" });

    fireEvent.change(screen.getByLabelText("Data"), { target: { value: "2026-06-02" } });
    fireEvent.change(screen.getByLabelText("Etichetta"), { target: { value: "Patronale" } });
    fireEvent.change(screen.getByLabelText("Company code"), { target: { value: "53" } });
    fireEvent.click(screen.getByRole("button", { name: "Aggiungi voce" }));
    expect(await screen.findByText("Giornata festiva aggiunta.")).toBeInTheDocument();
    expect(mocks.createPresenzeHoliday).toHaveBeenCalledWith("token", {
      holiday_date: "2026-06-02",
      label: "Patronale",
      company_code: "53",
      holiday_kind: "ordinary",
    });

    fireEvent.change(screen.getByLabelText("Data"), { target: { value: "2026-06-03" } });
    fireEvent.change(screen.getByLabelText("Etichetta"), { target: { value: "Soppressa" } });
    fireEvent.change(screen.getByLabelText("Tipo giornata"), { target: { value: "suppressed" } });
    fireEvent.click(screen.getByRole("button", { name: "Aggiungi voce" }));
    expect(await screen.findByText("Festivita soppressa aggiunta.")).toBeInTheDocument();
    expect(mocks.createPresenzeHoliday).toHaveBeenLastCalledWith("token", {
      holiday_date: "2026-06-03",
      label: "Soppressa",
      company_code: null,
      holiday_kind: "suppressed",
    });

    fireEvent.change(screen.getByLabelText("Data"), { target: { value: "2026-06-04" } });
    fireEvent.change(screen.getByLabelText("Etichetta"), { target: { value: "Override" } });
    fireEvent.change(screen.getByLabelText("Tipo giornata"), { target: { value: "working_override" } });
    fireEvent.click(screen.getByRole("button", { name: "Aggiungi voce" }));
    expect(await screen.findByText("Override lavorativo aggiunto.")).toBeInTheDocument();
  });

  test("rejects submit without date or label and without a token", async () => {
    render(<PresenzeFestivitaPage />);
    await screen.findAllByRole("button", { name: "Modifica" });
    fireEvent.click(screen.getByRole("button", { name: "Aggiungi voce" }));
    expect(screen.getByText("Compila almeno data ed etichetta.")).toBeInTheDocument();

    mocks.getStoredAccessToken.mockReturnValue(null);
    fireEvent.change(screen.getByLabelText("Data"), { target: { value: "2026-06-02" } });
    fireEvent.change(screen.getByLabelText("Etichetta"), { target: { value: "Patronale" } });
    fireEvent.click(screen.getByRole("button", { name: "Aggiungi voce" }));
    expect(mocks.createPresenzeHoliday).not.toHaveBeenCalled();
  });

  test("updates each holiday kind from Modifica", async () => {
    render(<PresenzeFestivitaPage />);
    await screen.findAllByRole("button", { name: "Modifica" });

    fireEvent.click(screen.getAllByRole("button", { name: "Modifica" })[2]);
    fireEvent.click(screen.getByRole("button", { name: "Salva modifica" }));
    expect(await screen.findByText("Festivita soppressa aggiornata.")).toBeInTheDocument();
    expect(mocks.updatePresenzeHoliday).toHaveBeenCalledWith("token", 3, expect.objectContaining({ holiday_kind: "suppressed" }));

    fireEvent.click(screen.getAllByRole("button", { name: "Modifica" })[3]);
    fireEvent.click(screen.getByRole("button", { name: "Salva modifica" }));
    expect(await screen.findByText("Override lavorativo aggiornato.")).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Modifica" })[0]);
    fireEvent.click(screen.getByRole("button", { name: "Salva modifica" }));
    expect(await screen.findByText("Giornata festiva aggiornata.")).toBeInTheDocument();
  });

  test("shows typed and generic save errors", async () => {
    mocks.createPresenzeHoliday.mockRejectedValueOnce(new Error("duplicato"));
    render(<PresenzeFestivitaPage />);
    await screen.findAllByRole("button", { name: "Modifica" });
    fireEvent.change(screen.getByLabelText("Data"), { target: { value: "2026-06-02" } });
    fireEvent.change(screen.getByLabelText("Etichetta"), { target: { value: "Patronale" } });
    fireEvent.click(screen.getByRole("button", { name: "Aggiungi voce" }));
    expect(await screen.findByText("duplicato")).toBeInTheDocument();

    mocks.createPresenzeHoliday.mockRejectedValueOnce("fail");
    fireEvent.click(screen.getByRole("button", { name: "Aggiungi voce" }));
    expect(await screen.findByText("Errore salvataggio festivita")).toBeInTheDocument();
  });

  test("bootstraps the year and handles missing token plus errors", async () => {
    render(<PresenzeFestivitaPage />);
    await screen.findAllByRole("button", { name: "Modifica" });
    fireEvent.click(screen.getByRole("button", { name: "Bootstrap anno" }));
    expect(await screen.findByText("Bootstrap completato: 2 voci inserite o recuperate.")).toBeInTheDocument();

    mocks.getStoredAccessToken.mockReturnValue(null);
    fireEvent.click(screen.getByRole("button", { name: "Bootstrap anno" }));
    expect(mocks.bootstrapPresenzeHolidays).toHaveBeenCalledTimes(1);

    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.bootstrapPresenzeHolidays.mockRejectedValueOnce(new Error("bootstrap ko"));
    fireEvent.click(screen.getByRole("button", { name: "Bootstrap anno" }));
    expect(await screen.findByText("bootstrap ko")).toBeInTheDocument();

    mocks.bootstrapPresenzeHolidays.mockRejectedValueOnce("fail");
    fireEvent.click(screen.getByRole("button", { name: "Bootstrap anno" }));
    expect(await screen.findByText("Errore bootstrap festivita")).toBeInTheDocument();
  });

  test("deletes a holiday, resets the editor when that row is open, and handles errors", async () => {
    render(<PresenzeFestivitaPage />);
    await screen.findAllByRole("button", { name: "Modifica" });
    fireEvent.click(screen.getAllByRole("button", { name: "Elimina" })[0]);
    expect(await screen.findByText("Voce eliminata.")).toBeInTheDocument();

    let resolveDelete: (() => void) | undefined;
    mocks.deletePresenzeHoliday.mockImplementationOnce(
      () =>
        new Promise<void>((resolve) => {
          resolveDelete = resolve;
        }),
    );
    fireEvent.click(screen.getAllByRole("button", { name: "Modifica" })[1]);
    expect(screen.getByLabelText("Company code")).toHaveValue("53");

    fireEvent.click(screen.getAllByRole("button", { name: "Elimina" })[1]);
    expect(screen.getByRole("button", { name: "Eliminazione..." })).toBeDisabled();
    resolveDelete?.();
    expect(await screen.findByText("Voce eliminata.")).toBeInTheDocument();
    expect(screen.getByLabelText("Etichetta")).toHaveValue("");

    mocks.deletePresenzeHoliday.mockRejectedValueOnce(new Error("locked"));
    fireEvent.click(screen.getAllByRole("button", { name: "Elimina" })[0]);
    expect(await screen.findByText("locked")).toBeInTheDocument();

    mocks.deletePresenzeHoliday.mockRejectedValueOnce("fail");
    fireEvent.click(screen.getAllByRole("button", { name: "Elimina" })[0]);
    expect(await screen.findByText("Errore eliminazione festivita")).toBeInTheDocument();

    mocks.getStoredAccessToken.mockReturnValue(null);
    fireEvent.click(screen.getAllByRole("button", { name: "Elimina" })[0]);
    expect(mocks.deletePresenzeHoliday).toHaveBeenCalledTimes(4);
  });
});
