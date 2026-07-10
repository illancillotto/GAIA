import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import CatastoIndiciAnomalieRuoloPage from "@/app/catasto/indici/anomalie-ruolo/page";
import type { CatIndiceRuoloExcludedParticella } from "@/types/catasto";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn<() => string | null>(),
  useSearchParams: vi.fn<() => URLSearchParams>(),
  catastoGetIndiciRuoloEsclusi: vi.fn(),
  catastoListDistretti: vi.fn(),
  catastoAssignIndiciRuoloEsclusoDistretto: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useSearchParams: () => mocks.useSearchParams(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: () => mocks.getStoredAccessToken(),
}));

vi.mock("@/lib/api/catasto", () => ({
  catastoGetIndiciRuoloEsclusi: (...args: unknown[]) => mocks.catastoGetIndiciRuoloEsclusi(...args),
  catastoListDistretti: (...args: unknown[]) => mocks.catastoListDistretti(...args),
  catastoAssignIndiciRuoloEsclusoDistretto: (...args: unknown[]) => mocks.catastoAssignIndiciRuoloEsclusoDistretto(...args),
}));

vi.mock("@/components/catasto/catasto-page", () => ({
  CatastoPage: ({ children, title, description }: { children: React.ReactNode; title: string; description: string }) => (
    <main>
      <h1>{title}</h1>
      <p>{description}</p>
      {children}
    </main>
  ),
}));

const rows: CatIndiceRuoloExcludedParticella[] = [
  {
    key: "senza_distretto|ARBOREA|70|200|",
    reason_key: "senza_distretto",
    reason_label: "Particella corrente senza distretto",
    comune_nome: "Arborea",
    foglio: "70",
    particella: "200",
    subalterno: null,
    righe_ruolo_count: 2,
    cat_particella_id: "00000000-0000-0000-0000-000000000001",
    catasto_is_current: true,
    catasto_num_distretto: null,
    superficie_irrigata_ha: "0.4",
    importo_ruolo: "30",
    importo_ruolo_manutenzione: "8",
    importo_ruolo_irrigazione: "10",
    importo_ruolo_istituzionale: "12",
    avvisi: ["CNC-1"],
    nominativi: ["Azienda agricola"],
    partite: ["P-1"],
  },
  {
    key: "non_collegata|ORISTANO|10|30|1",
    reason_key: "non_collegata",
    reason_label: "Ruolo non collegato al catasto corrente",
    comune_nome: "Oristano",
    foglio: "10",
    particella: "30",
    subalterno: "1",
    righe_ruolo_count: 1,
    cat_particella_id: null,
    catasto_is_current: null,
    catasto_num_distretto: null,
    superficie_irrigata_ha: "0",
    importo_ruolo: "0",
    importo_ruolo_manutenzione: "0",
    importo_ruolo_irrigazione: "0",
    importo_ruolo_istituzionale: "0",
    avvisi: [],
    nominativi: [],
    partite: [],
  },
  {
    key: "catasto_non_corrente_o_assente|CABRAS|11|31|",
    reason_key: "catasto_non_corrente_o_assente",
    reason_label: "Aggancio non corrente o non disponibile",
    comune_nome: null,
    foglio: "11",
    particella: "31",
    subalterno: null,
    righe_ruolo_count: 1,
    cat_particella_id: "00000000-0000-0000-0000-000000000002",
    catasto_is_current: false,
    catasto_num_distretto: "03",
    superficie_irrigata_ha: "0.25",
    importo_ruolo: "12.3456",
    importo_ruolo_manutenzione: "1.234",
    importo_ruolo_irrigazione: "2.345",
    importo_ruolo_istituzionale: "8.7666",
    avvisi: ["CNC-2"],
    nominativi: ["Soggetto non corrente"],
    partite: ["P-2"],
  },
];

function setupApi(): void {
  mocks.catastoGetIndiciRuoloEsclusi.mockResolvedValue({ anno_riferimento: 2025, total: rows.length, items: rows });
  mocks.catastoListDistretti.mockResolvedValue([
    { id: "distretto-01", num_distretto: "01", nome_distretto: "Distretto Uno", attivo: true },
    { id: "distretto-02", num_distretto: "02", nome_distretto: null, attivo: true },
    { id: "distretto-03", num_distretto: "03", nome_distretto: "Distretto Tre", attivo: false },
  ]);
  mocks.catastoAssignIndiciRuoloEsclusoDistretto.mockResolvedValue({
    updated: true,
    cat_particella_id: rows[0].cat_particella_id,
    distretto_id: "distretto-01",
    num_distretto: "01",
    nome_distretto: "Distretto Uno",
  });
}

describe("CatastoIndiciAnomalieRuoloPage", () => {
  beforeEach(() => {
    mocks.getStoredAccessToken.mockReturnValue("token-test");
    mocks.useSearchParams.mockReturnValue(new URLSearchParams("anno=2025"));
    mocks.catastoGetIndiciRuoloEsclusi.mockReset();
    mocks.catastoListDistretti.mockReset();
    mocks.catastoAssignIndiciRuoloEsclusoDistretto.mockReset();
    setupApi();
  });

  test("loads anomaly rows, filters them and shows non direct workflows", async () => {
    render(<CatastoIndiciAnomalieRuoloPage />);

    expect(screen.getByText("Caricamento anomalie ruolo...")).toBeInTheDocument();
    expect(await screen.findByText("Particelle fuori quadro indici")).toBeInTheDocument();
    expect(mocks.catastoGetIndiciRuoloEsclusi).toHaveBeenCalledWith("token-test", 2025);
    expect(mocks.catastoListDistretti).toHaveBeenCalledWith("token-test");
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("Correzione diretta disponibile")).toBeInTheDocument();
    expect(screen.getByText("02 · Distretto")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salva distretto" })).toBeEnabled();

    fireEvent.change(screen.getByPlaceholderText("Cerca comune, avviso, soggetto..."), { target: { value: "oristano" } });
    expect(screen.getByText("1 casi filtrati")).toBeInTheDocument();
    expect(screen.getByText(/Oristano/)).toBeInTheDocument();

    fireEvent.click(screen.getByText(/Oristano/));
    expect(screen.getByText("Serve aggancio catastale")).toBeInTheDocument();
    expect(screen.getByText(/non è correggibile/)).toBeInTheDocument();

    fireEvent.change(screen.getByDisplayValue("Tutte"), { target: { value: "catasto_non_corrente_o_assente" } });
    fireEvent.change(screen.getByPlaceholderText("Cerca comune, avviso, soggetto..."), { target: { value: "" } });
    expect(screen.getByText("1 casi filtrati")).toBeInTheDocument();
    fireEvent.click(screen.getByText((_, element) => element?.textContent === "— · F11 · P31 · S—"));
    expect(screen.getByText("Serve verifica storico/catasto")).toBeInTheDocument();
  });

  test("assigns a verified distretto to a fixable current particle", async () => {
    mocks.catastoAssignIndiciRuoloEsclusoDistretto.mockResolvedValueOnce({
      updated: true,
      cat_particella_id: rows[0].cat_particella_id,
      distretto_id: "distretto-02",
      num_distretto: "02",
      nome_distretto: null,
    });
    render(<CatastoIndiciAnomalieRuoloPage />);

    await screen.findByText("Correzione diretta disponibile");
    fireEvent.change(screen.getByLabelText(/Distretto/), { target: { value: "distretto-02" } });
    fireEvent.change(screen.getByLabelText(/Nota operatore/), { target: { value: "Verifica operatore" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva distretto" }));

    await waitFor(() =>
      expect(mocks.catastoAssignIndiciRuoloEsclusoDistretto).toHaveBeenCalledWith("token-test", {
        cat_particella_id: "00000000-0000-0000-0000-000000000001",
        distretto_id: "distretto-02",
        note: "Verifica operatore",
      }),
    );
    expect(await screen.findByText("Distretto assegnato: 02 · Distretto")).toBeInTheDocument();
    expect(mocks.catastoGetIndiciRuoloEsclusi).toHaveBeenCalledTimes(2);
  });

  test("shows already aligned and save error states", async () => {
    mocks.catastoAssignIndiciRuoloEsclusoDistretto.mockResolvedValueOnce({
      updated: false,
      cat_particella_id: rows[0].cat_particella_id,
      distretto_id: "distretto-01",
      num_distretto: "01",
      nome_distretto: null,
    });
    render(<CatastoIndiciAnomalieRuoloPage />);

    await screen.findByText("Correzione diretta disponibile");
    fireEvent.change(screen.getByLabelText(/Distretto/), { target: { value: "distretto-01" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva distretto" }));
    expect(await screen.findByText("La particella era già allineata al distretto selezionato.")).toBeInTheDocument();

    mocks.catastoAssignIndiciRuoloEsclusoDistretto.mockRejectedValueOnce("errore non standard");
    fireEvent.change(screen.getByLabelText(/Distretto/), { target: { value: "distretto-01" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva distretto" }));
    expect(await screen.findByText("Errore salvataggio distretto.")).toBeInTheDocument();

    mocks.catastoAssignIndiciRuoloEsclusoDistretto.mockRejectedValueOnce(new Error("Errore salvataggio API"));
    fireEvent.change(screen.getByLabelText(/Distretto/), { target: { value: "distretto-01" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva distretto" }));
    expect(await screen.findByText("Errore salvataggio API")).toBeInTheDocument();
  });

  test("handles missing token and loading failures", async () => {
    mocks.getStoredAccessToken.mockReturnValue(null);
    render(<CatastoIndiciAnomalieRuoloPage />);

    expect(await screen.findByText("Sessione non disponibile: effettua nuovamente l'accesso.")).toBeInTheDocument();
    expect(screen.getByText("Seleziona un caso dall'elenco.")).toBeInTheDocument();
    expect(mocks.catastoGetIndiciRuoloEsclusi).not.toHaveBeenCalled();
  });

  test("shows API loading errors and uses undefined anno when querystring is invalid", async () => {
    mocks.useSearchParams.mockReturnValue(new URLSearchParams("anno=abc"));
    mocks.catastoGetIndiciRuoloEsclusi.mockRejectedValue("errore non standard");

    render(<CatastoIndiciAnomalieRuoloPage />);

    expect(await screen.findByText("Errore caricamento anomalie ruolo.")).toBeInTheDocument();
    expect(mocks.catastoGetIndiciRuoloEsclusi).toHaveBeenCalledWith("token-test", undefined);
  });

  test("shows standard API loading error messages", async () => {
    mocks.catastoGetIndiciRuoloEsclusi.mockRejectedValue(new Error("Errore API"));

    render(<CatastoIndiciAnomalieRuoloPage />);

    expect(await screen.findByText("Errore API")).toBeInTheDocument();
  });

  test("handles empty payloads and missing anno querystring", async () => {
    mocks.useSearchParams.mockReturnValue(new URLSearchParams());
    mocks.catastoGetIndiciRuoloEsclusi.mockResolvedValueOnce({ anno_riferimento: 2025, total: 0, items: [] });

    render(<CatastoIndiciAnomalieRuoloPage />);

    expect(await screen.findByText("Seleziona un caso dall'elenco.")).toBeInTheDocument();
    expect(screen.getByText("0 casi filtrati")).toBeInTheDocument();
    expect(mocks.catastoGetIndiciRuoloEsclusi).toHaveBeenCalledWith("token-test", undefined);
  });

  test("handles missing token while saving", async () => {
    render(<CatastoIndiciAnomalieRuoloPage />);

    await screen.findByText("Correzione diretta disponibile");
    fireEvent.change(screen.getByLabelText(/Distretto/), { target: { value: "distretto-01" } });
    mocks.getStoredAccessToken.mockReturnValueOnce(null);
    fireEvent.click(screen.getByRole("button", { name: "Salva distretto" }));

    const detailPanel = screen.getByText("Dettaglio e azioni").closest("aside");
    expect(detailPanel).not.toBeNull();
    expect(await within(detailPanel as HTMLElement).findByText("Sessione non disponibile: effettua nuovamente l'accesso.")).toBeInTheDocument();
    expect(mocks.catastoAssignIndiciRuoloEsclusoDistretto).not.toHaveBeenCalled();
  });

  test("guards against save attempts without a selected distretto", async () => {
    render(<CatastoIndiciAnomalieRuoloPage />);

    await screen.findByText("Correzione diretta disponibile");
    fireEvent.click(screen.getByRole("button", { name: "Salva distretto" }));

    expect(await screen.findByText("Seleziona una particella correggibile e un distretto.")).toBeInTheDocument();
    expect(mocks.catastoAssignIndiciRuoloEsclusoDistretto).not.toHaveBeenCalled();
  });
});
