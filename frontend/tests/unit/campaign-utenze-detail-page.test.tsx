import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import UtenzeSubjectDetailPage from "@/app/utenze/[id]/page";
import type { AnagraficaSubjectDetail } from "@/types/api";

const mocks = vi.hoisted(() => ({
  router: { push: vi.fn(), replace: vi.fn() },
  getStoredAccessToken: vi.fn(),
  getCurrentUser: vi.fn(),
  getMyPermissions: vi.fn(),
  getUtenzeSubject: vi.fn(),
  getUtenzeSubjectPaymentNotices: vi.fn(),
  getUtenzeSubjectNasImportStatus: vi.fn(),
  updateUtenzeSubject: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "subject-1" }),
  useRouter: () => mocks.router,
  useSearchParams: () => new URLSearchParams(window.location.search),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
  clearStoredAccessToken: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getCurrentUser: mocks.getCurrentUser,
  getMyPermissions: mocks.getMyPermissions,
  getUtenzeSubject: mocks.getUtenzeSubject,
  getUtenzeSubjectPaymentNotices: mocks.getUtenzeSubjectPaymentNotices,
  getUtenzeSubjectNasImportStatus: mocks.getUtenzeSubjectNasImportStatus,
  updateUtenzeSubject: mocks.updateUtenzeSubject,
}));

vi.mock("@/components/layout/app-shell", () => ({
  AppShell: ({ children }: { children: ReactNode }) => <main>{children}</main>,
}));

vi.mock("@/components/layout/topbar", () => ({
  Topbar: ({ breadcrumb }: { breadcrumb: string }) => <header data-testid="breadcrumb">{breadcrumb}</header>,
}));

vi.mock("@/components/anagrafica/AnprStatusCard", () => ({
  AnprStatusCard: ({ subjectId }: { subjectId: string }) => <section data-testid="anpr">ANPR {subjectId}</section>,
}));

vi.mock("@/components/utenze/utenze-subject-visura-card", () => ({
  UtenzeSubjectVisuraCard: () => <section data-testid="visura" />,
}));

vi.mock("@/components/utenze/utenze-meter-readings-section", () => ({
  UtenzeMeterReadingsSection: ({ subjectId, token }: { subjectId: string; token: string }) => (
    <section data-testid="readings">{subjectId}:{token}</section>
  ),
}));

vi.mock("@/components/utenze/utenze-payment-notices-section", () => ({
  UtenzePaymentNoticesSection: ({ subjectId, token }: { subjectId: string; token: string }) => (
    <section data-testid="notices">{subjectId}:{token}</section>
  ),
}));

vi.mock("@/components/utenze/utenze-terreni-colture-section", () => ({
  UtenzeTerreniColtureSection: ({ subjectId, token }: { subjectId: string; token: string }) => (
    <section data-testid="land">{subjectId}:{token}</section>
  ),
}));

vi.mock("@/components/utenze/utenze-domande-irrigue-section", () => ({
  UtenzeDomandeIrrigueSection: ({ subjectId, token, utenzaId }: { subjectId: string; token: string; utenzaId: string | null }) => (
    <section data-testid="irrigation">{subjectId}:{token}:{utenzaId}</section>
  ),
}));

function subjectFixture(): AnagraficaSubjectDetail {
  return {
    id: "subject-1",
    subject_type: "person",
    status: "active",
    source_system: "campaign-fixture",
    source_external_id: null,
    source_name_raw: "Rossi Mario",
    nas_folder_path: null,
    nas_folder_letter: null,
    requires_review: false,
    imported_at: null,
    created_at: "2026-10-08T10:00:00Z",
    updated_at: "2026-10-08T10:00:00Z",
    person: {
      subject_id: "subject-1",
      cognome: "Rossi",
      nome: "Mario",
      codice_fiscale: "RSSMRA80A01H501U",
      anpr_id: null,
      stato_anpr: null,
      data_decesso: null,
      luogo_decesso_comune: null,
      last_anpr_check_at: null,
      last_c030_check_at: null,
      data_nascita: null,
      comune_nascita: null,
      indirizzo: null,
      comune_residenza: null,
      cap: null,
      email: null,
      telefono: null,
      note: null,
      created_at: "2026-10-08T10:00:00Z",
      updated_at: "2026-10-08T10:00:00Z",
    },
    company: null,
    documents: [],
    audit_log: [],
    catasto_documents: [],
  };
}

async function readyPage() {
  const view = render(<UtenzeSubjectDetailPage />);
  await screen.findByText("Rossi Mario");
  await screen.findByText("NAS senza cartella associata");
  return view;
}

async function enableEditing() {
  fireEvent.click(screen.getByRole("button", { name: "Modifica", exact: true }));
  expect(screen.getByText("Abilita modalità modifica")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Abilita modifica", exact: true }));
  expect(screen.getByText("Modalità modifica attiva")).toBeInTheDocument();
}

describe("campaign Utenze detail page characterization", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    window.history.replaceState(null, "", "/utenze/subject-1");
    mocks.getStoredAccessToken.mockReturnValue("campaign-token");
    mocks.getCurrentUser.mockResolvedValue({ enabled_modules: ["utenze"], role: "viewer" });
    mocks.getMyPermissions.mockResolvedValue({ granted_keys: [] });
    mocks.getUtenzeSubject.mockResolvedValue(subjectFixture());
    mocks.getUtenzeSubjectPaymentNotices.mockResolvedValue([]);
    mocks.getUtenzeSubjectNasImportStatus.mockResolvedValue({
      can_import_from_nas: false,
      missing_in_nas: true,
      matched_folder_path: null,
      matched_folder_name: null,
      total_files_in_nas: 0,
      pending_files_in_nas: 0,
      message: "NAS senza cartella associata",
    });
  });

  afterEach(() => cleanup());

  test("loads the authorized subject read-only and updates header identity", async () => {
    await readyPage();
    expect(mocks.getUtenzeSubject).toHaveBeenCalledWith("campaign-token", "subject-1");
    expect(mocks.getUtenzeSubjectPaymentNotices).toHaveBeenCalledWith("campaign-token", "subject-1");
    expect(screen.getByTestId("breadcrumb")).toHaveTextContent("RSSMRA80A01H501U");
    expect(screen.getByText("Sola lettura")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salva scheda" })).toBeDisabled();
    expect(screen.getByLabelText("Cognome / ragione sociale")).toHaveAttribute("readonly");
    expect(screen.getByTestId("anpr")).toHaveTextContent("subject-1");
  });

  test("shows subject loading until the outstanding API request completes", async () => {
    let resolveSubject!: (value: AnagraficaSubjectDetail) => void;
    mocks.getUtenzeSubject.mockReturnValue(new Promise<AnagraficaSubjectDetail>((resolve) => { resolveSubject = resolve; }));
    render(<UtenzeSubjectDetailPage />);
    expect(await screen.findByText("Caricamento scheda soggetto.")).toBeInTheDocument();
    await act(async () => resolveSubject(subjectFixture()));
    expect(await screen.findByText("Rossi Mario")).toBeInTheDocument();
  });

  test.each([
    [new Error("Soggetto non trovato"), "Soggetto non trovato"],
    ["opaque-failure", "Errore caricamento dettaglio soggetto"],
  ])("shows load error without edit controls", async (error, expectedMessage) => {
    mocks.getUtenzeSubject.mockRejectedValue(error);
    render(<UtenzeSubjectDetailPage />);
    expect(await screen.findByText("Dettaglio non disponibile")).toBeInTheDocument();
    expect(screen.getByText(expectedMessage)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Modifica", exact: true })).not.toBeInTheDocument();
  });

  test("anonymous users redirect without calling subject APIs", async () => {
    mocks.getStoredAccessToken.mockReturnValue(null);
    render(<UtenzeSubjectDetailPage />);
    await waitFor(() => expect(mocks.router.replace).toHaveBeenCalledWith("/login"));
    expect(mocks.getUtenzeSubject).not.toHaveBeenCalled();
  });

  test("module-denied users cannot load the subject", async () => {
    mocks.getCurrentUser.mockResolvedValue({ enabled_modules: [], role: "viewer" });
    render(<UtenzeSubjectDetailPage />);
    expect(await screen.findByText("Accesso non autorizzato")).toBeInTheDocument();
    expect(mocks.getUtenzeSubject).not.toHaveBeenCalled();
    expect(mocks.updateUtenzeSubject).not.toHaveBeenCalled();
  });

  test("editing requires confirmation and can be canceled or terminated", async () => {
    await readyPage();
    fireEvent.click(screen.getByRole("button", { name: "Modifica", exact: true }));
    fireEvent.click(screen.getByRole("button", { name: "Annulla", exact: true }));
    expect(screen.getByRole("button", { name: "Salva scheda" })).toBeDisabled();
    await enableEditing();
    expect(screen.getByLabelText("Cognome / ragione sociale")).not.toHaveAttribute("readonly");
    fireEvent.click(screen.getByRole("button", { name: "Termina modifica" }));
    expect(screen.getByRole("button", { name: "Salva scheda" })).toBeDisabled();
    expect(mocks.updateUtenzeSubject).not.toHaveBeenCalled();
  });

  test("saves edited person fields and returns to read-only on the refreshed subject", async () => {
    const updated = subjectFixture();
    updated.person!.cognome = "Bianchi";
    mocks.updateUtenzeSubject.mockResolvedValue(updated);
    await readyPage();
    await enableEditing();
    fireEvent.change(screen.getByLabelText("Cognome / ragione sociale"), { target: { value: "Bianchi" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva scheda" }));
    await waitFor(() => expect(mocks.updateUtenzeSubject).toHaveBeenCalledWith(
      "campaign-token", "subject-1", expect.objectContaining({
        source_name_raw: "Rossi Mario", requires_review: false, status: "active",
        person: expect.objectContaining({ cognome: "Bianchi", nome: "Mario", codice_fiscale: "RSSMRA80A01H501U", email: null, stato_anpr: null, data_decesso: null }),
      }),
    ));
    expect(await screen.findByText("Scheda soggetto aggiornata.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salva scheda" })).toBeDisabled();
    expect(screen.getByText("Bianchi Mario")).toBeInTheDocument();
  });

  test.each([
    [new Error("Salvataggio rifiutato"), "Salvataggio rifiutato"],
    [null, "Errore salvataggio soggetto"],
  ])("retains editing and reports failed saves", async (error, expectedMessage) => {
    mocks.updateUtenzeSubject.mockRejectedValue(error);
    await readyPage();
    await enableEditing();
    fireEvent.click(screen.getByRole("button", { name: "Salva scheda" }));
    expect(await screen.findByText(expectedMessage)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salva scheda" })).not.toBeDisabled();
    expect(screen.queryByText("Scheda soggetto aggiornata.")).not.toBeInTheDocument();
  });

  test.each([
    ["Letture contatori", "readings"],
    ["Avvisi di pagamento", "notices"],
    ["Terreni e colture", "land"],
    ["Domande irrigue", "irrigation"],
  ])("switches to %s and delegates identity/token without editing", async (label, testId) => {
    window.history.replaceState(null, "", "/utenze/subject-1?utenza_id=utenza-7");
    await readyPage();
    fireEvent.click(screen.getByRole("button", { name: label, exact: true }));
    expect(screen.getByTestId(testId)).toHaveTextContent("subject-1:campaign-token");
    if (testId === "irrigation") expect(screen.getByTestId(testId)).toHaveTextContent("utenza-7");
    expect(screen.queryByRole("button", { name: "Salva scheda" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Scheda soggetto", exact: true }));
    expect(screen.getByRole("button", { name: "Salva scheda" })).toBeDisabled();
  });

  test("navigates back to the subjects list", async () => {
    await readyPage();
    fireEvent.click(screen.getByRole("button", { name: "Torna alla lista" }));
    expect(mocks.router.push).toHaveBeenCalledWith("/utenze/import#utenze-soggetti");
  });

  test("embedded mode omits back navigation", async () => {
    window.history.replaceState(null, "", "/utenze/subject-1?embedded=1");
    await readyPage();
    expect(screen.queryByRole("button", { name: "Torna alla lista" })).not.toBeInTheDocument();
    expect(screen.queryByTestId("breadcrumb")).not.toBeInTheDocument();
  });

  test("a missing NAS status uses the error fallback without hiding the subject", async () => {
    mocks.getUtenzeSubjectNasImportStatus.mockRejectedValue(new Error("NAS irraggiungibile"));
    render(<UtenzeSubjectDetailPage />);
    expect(await screen.findByText("NAS irraggiungibile")).toBeInTheDocument();
    expect(screen.getByText("Rossi Mario")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Modifica", exact: true })).toBeInTheDocument();
  });

  test("company details use business identity and omit ANPR", async () => {
    const company = subjectFixture();
    company.subject_type = "company";
    company.person = null;
    company.company = {
      subject_id: "subject-1", ragione_sociale: "Acme SRL", partita_iva: "12345678901",
      codice_fiscale: null, forma_giuridica: "SRL", sede_legale: null, comune_sede: null,
      cap: null, email_pec: null, telefono: null, note: null,
      created_at: company.created_at, updated_at: company.updated_at,
    };
    mocks.getUtenzeSubject.mockResolvedValue(company);
    render(<UtenzeSubjectDetailPage />);
    expect(await screen.findByText("Acme SRL")).toBeInTheDocument();
    expect(screen.getByLabelText("Ragione sociale")).toHaveValue("Acme SRL");
    expect(screen.getByTestId("breadcrumb")).toHaveTextContent("12345678901");
    expect(screen.queryByTestId("anpr")).not.toBeInTheDocument();
  });

  test("merged subjects do not expose ANPR actions", async () => {
    const merged = subjectFixture();
    merged.source_name_raw = "Rossi Mario [MERGED->subject-2]";
    mocks.getUtenzeSubject.mockResolvedValue(merged);
    await readyPage();
    expect(screen.queryByTestId("anpr")).not.toBeInTheDocument();
  });

  test.each([
    [new Error("403 Module access denied"), false],
    [new Error("Service unavailable"), true],
  ])("payment failure does not prevent loading and distinguishes permission errors", async (error, visible) => {
    mocks.getUtenzeSubjectPaymentNotices.mockRejectedValue(error);
    await readyPage();
    await waitFor(() => {
      if (visible) expect(screen.getByText("Avvisi non disponibili")).toBeInTheDocument();
      else expect(screen.queryByText("Avvisi non disponibili")).not.toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Modifica", exact: true })).toBeInTheDocument();
  });
});
