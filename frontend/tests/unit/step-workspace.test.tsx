import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ElaborazioniStepPage from "@/app/elaborazioni/step/page";
import { StepContribuenteDetailPanel } from "@/components/elaborazioni/step/step-contribuente-detail";
import { StepContribuentiPanel } from "@/components/elaborazioni/step/step-contribuenti-panel";
import { StepCredentialsPanel } from "@/components/elaborazioni/step/step-credentials-panel";
import { StepJobsPanel } from "@/components/elaborazioni/step/step-jobs-panel";
import { StepLinkAnomaliesPanel } from "@/components/elaborazioni/step/step-link-anomalies-panel";
import { StepWorkspaceContent } from "@/components/elaborazioni/step/step-workspace";
import type { StepContribuenteDetail, StepCredential, StepSyncJob } from "@/types/step";

const apiMocks = vi.hoisted(() => ({
  cancelStepJob: vi.fn(),
  createStepCredential: vi.fn(),
  createStepJob: vi.fn(),
  deleteStepCredential: vi.fn(),
  deleteStepJob: vi.fn(),
  downloadStepDocumentoPdf: vi.fn(),
  getStepContribuente: vi.fn(),
  getStepOverview: vi.fn(),
  listStepContribuenti: vi.fn(),
  listStepCredentials: vi.fn(),
  listStepJobs: vi.fn(),
  listStepLinkAnomalies: vi.fn(),
  testStepCredential: vi.fn(),
  updateStepCredential: vi.fn(),
}));
const shell = vi.hoisted(() => ({ currentUser: { role: "super_admin" } as { role: string } | null }));
const auth = vi.hoisted(() => ({ token: "token" as string | null }));
const polling = vi.hoisted(() => ({ calls: [] as Array<{ callback: () => unknown; enabled: boolean }> }));

vi.mock("@/lib/api", () => apiMocks);
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: () => auth.token }));
vi.mock("@/components/layout/app-shell-context", () => ({ useAppShellContext: () => ({ currentUser: shell.currentUser }) }));
vi.mock("@/hooks/use-polling", () => ({
  usePolling: (callback: () => unknown, options: { enabled: boolean }) => polling.calls.push({ callback, enabled: options.enabled }),
}));
vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children, title }: { children: ReactNode; title: string }) => (
    <main>
      <h1>{title}</h1>
      {children}
    </main>
  ),
}));
vi.mock("next/link", () => ({ default: ({ children, href, className }: { children: ReactNode; href: string; className?: string }) => <a className={className} href={href}>{children}</a> }));

function credential(overrides: Partial<StepCredential> = {}): StepCredential {
  return {
    id: 1,
    label: "STEP Consorzio",
    username: "utente",
    portal_url: "https://step.example",
    active: true,
    min_delay_ms: 600,
    last_used_at: "2026-10-21T10:00:00Z",
    last_error: null,
    consecutive_failures: 0,
    created_at: "2026-10-21T10:00:00Z",
    updated_at: "2026-10-21T10:00:00Z",
    ...overrides,
  };
}

function job(overrides: Partial<StepSyncJob> = {}): StepSyncJob {
  return {
    id: 5,
    credential_id: null,
    requested_by_user_id: 1,
    status: "succeeded",
    mode: "archive_import",
    payload_json: null,
    result_json: { imported: 3354 },
    error_detail: null,
    started_at: null,
    completed_at: null,
    created_at: "2026-10-21T10:00:00Z",
    updated_at: "2026-10-21T10:00:00Z",
    ...overrides,
  };
}

const overview = {
  contribuenti: 3354,
  documenti: 3410,
  tributi: 21265,
  pagamenti: 3237,
  pdf_scaricati: 3410,
  residuo_totale: "1313193.06",
  ultimo_aggiornamento: "2026-10-21T10:00:00Z",
  links: { linked: 7000, not_found: 300, ambiguous: 2, unrecognized: 36 },
  import_archives: ["raccolta-completa.zip"],
};

const row = {
  id: "c1",
  cod_ent: "14215",
  codice_fiscale: "RSSMRA80A01H501U",
  denominazione: "ROSSI MARIO",
  numero_documenti: 1,
  importo: "100.00",
  pagato: "0.00",
  residuo: "100.00",
  stato_documenti: "Non Pagato",
  detail_synced_at: null,
};

function detail(overrides: Partial<StepContribuenteDetail> = {}): StepContribuenteDetail {
  return {
    ...row,
    anagrafica_json: null,
    situazione_contabile_json: null,
    sections_json: null,
    document_reconciliation_json: null,
    last_seen_at: "2026-10-21T10:00:00Z",
    documenti: [
      {
        id: "d1",
        num_doc: "20241421500000003",
        prg_coo: "1",
        section: "Documenti Emessi",
        des_doc: "Consorzio - quote ordinarie",
        des_trib: null,
        anno_rif: "2019-2020",
        data_notifica: "2024-11-16",
        tot_dovuto: "100.00",
        imp_carico: "100.00",
        tot_pagato: "0.00",
        residuo: "100.00",
        pdf_status: "downloaded",
        pdf_original_filename: "doc.pdf",
        tributi: [
          { position: 1, partita: "1", cod_tributo: "0985", des_tributo: "Quote", tipo_tributo: "Imposta", anno_rif: 2019, imp_carico: "50.00", imp_carico_pagato: "0.00", imp_discaricato: "0.00", avviso_reference_raw: "020190006018040", codice_cnc: "020190006018040" },
          { position: 2, partita: "2", cod_tributo: "0966", des_tributo: "Somme", tipo_tributo: "Altro", anno_rif: null, imp_carico: "3.00", imp_carico_pagato: null, imp_discaricato: null, avviso_reference_raw: null, codice_cnc: null },
        ],
        links: [
          { id: "l1", documento_id: "d1", reference_key: "020190006018040", codice_cnc: "020190006018040", anno_rif: 2019, status: "linked", ruolo_avviso_id: "a1", candidate_avviso_ids: null, tributi_count: 1, imp_carico: "50.00", imp_carico_pagato: "0.00", imp_discaricato: "0.00" },
          { id: "l2", documento_id: "d1", reference_key: "PG13319", codice_cnc: null, anno_rif: null, status: "unrecognized", ruolo_avviso_id: null, candidate_avviso_ids: null, tributi_count: 1, imp_carico: "3.00", imp_carico_pagato: null, imp_discaricato: null },
        ],
      },
      {
        id: "d2",
        num_doc: "20241421500000004",
        prg_coo: "1",
        section: null,
        des_doc: null,
        des_trib: null,
        anno_rif: null,
        data_notifica: null,
        tot_dovuto: null,
        imp_carico: null,
        tot_pagato: null,
        residuo: null,
        pdf_status: "unavailable",
        pdf_original_filename: null,
        tributi: [],
        links: [],
      },
    ],
    pagamenti: [
      { num_quietanza: "q1", num_doc: "20241421500000003", data_pagamento: "2025-09-04", data_accredito: null, modalita: "PagoPA", importo: "258.27", importo_pagato: "178.63", annullato: false, stato: null, riferimento: "Rif" },
      { num_quietanza: "q2", num_doc: null, data_pagamento: null, data_accredito: null, modalita: null, importo: "-10.00", importo_pagato: null, annullato: true, stato: "STORNATO", riferimento: null },
    ],
    ...overrides,
  };
}

beforeEach(() => {
  Object.values(apiMocks).forEach((mock) => mock.mockReset());
  polling.calls = [];
  shell.currentUser = { role: "super_admin" };
  auth.token = "token";
  apiMocks.getStepOverview.mockResolvedValue(overview);
  apiMocks.listStepCredentials.mockResolvedValue([credential()]);
  apiMocks.listStepJobs.mockResolvedValue([job()]);
  apiMocks.listStepContribuenti.mockResolvedValue({ items: [row], total: 1, page: 1, page_size: 25 });
  apiMocks.listStepLinkAnomalies.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 });
});

describe("StepWorkspace", () => {
  it("mostra overview, credenziali e job al super admin", async () => {
    render(<ElaborazioniStepPage />);
    expect(await screen.findByText("STEP Consorzio")).toBeInTheDocument();
    expect(screen.getByText("3354")).toBeInTheDocument();
    expect(screen.getByText("Worker pronto")).toBeInTheDocument();
    expect(polling.calls.at(-1)?.enabled).toBe(false);
  });

  it("nasconde credenziali e job agli altri ruoli e attiva il polling con job attivi", async () => {
    shell.currentUser = null;
    apiMocks.getStepOverview.mockResolvedValue({ ...overview, ultimo_aggiornamento: null });
    render(<StepWorkspaceContent />);
    await waitFor(() => expect(apiMocks.getStepOverview).toHaveBeenCalled());
    expect(screen.queryByText("Accesso portale STEP")).not.toBeInTheDocument();
    expect(screen.getByText("Mai")).toBeInTheDocument();
    expect(apiMocks.listStepJobs).not.toHaveBeenCalled();
  });

  it("aggiorna in automatico con job attivi e registra le notifiche", async () => {
    apiMocks.listStepJobs.mockResolvedValue([job({ status: "processing" })]);
    apiMocks.testStepCredential.mockResolvedValue({});
    render(<StepWorkspaceContent />);
    expect(await screen.findByText("Worker in attività")).toBeInTheDocument();
    expect(polling.calls.at(-1)?.enabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Test login" }));
    expect(await screen.findByText("Test login STEP accodato sul worker.")).toBeInTheDocument();
  });

  it("mostra gli errori di caricamento e non renderizza senza token", async () => {
    apiMocks.getStepOverview.mockRejectedValueOnce(new Error("offline"));
    const { unmount } = render(<StepWorkspaceContent />);
    expect(await screen.findByText("offline")).toBeInTheDocument();
    unmount();
    apiMocks.getStepOverview.mockRejectedValueOnce("x");
    const second = render(<StepWorkspaceContent />);
    expect(await screen.findByText("Errore caricamento STEP")).toBeInTheDocument();
    second.unmount();
    auth.token = null;
    const { container } = render(<StepWorkspaceContent />);
    expect(container).toBeEmptyDOMElement();
  });

  it("usa valori di default prima del caricamento dell'overview", async () => {
    let resolve: (value: unknown) => void = () => undefined;
    apiMocks.getStepOverview.mockReturnValue(new Promise((done) => (resolve = done)));
    render(<StepWorkspaceContent />);
    await waitFor(() => expect(apiMocks.getStepOverview).toHaveBeenCalled());
    expect(screen.getAllByText("0").length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText("Operazione"), { target: { value: "archive_import" } });
    expect(screen.getByText("Nessun archivio .zip nella cartella import STEP del server.")).toBeInTheDocument();
    await act(async () => resolve(overview));
    expect(await screen.findByText("3354")).toBeInTheDocument();
  });
});

describe("StepCredentialsPanel", () => {
  it("salva, testa, attiva e cancella le credenziali", async () => {
    const onChanged = vi.fn().mockResolvedValue(undefined);
    const onError = vi.fn();
    apiMocks.createStepCredential.mockResolvedValue({});
    apiMocks.updateStepCredential.mockResolvedValue({});
    apiMocks.deleteStepCredential.mockResolvedValue(undefined);
    render(
      <StepCredentialsPanel
        credentials={[credential({ active: false, last_used_at: null, last_error: "rifiutata" })]}
        onChanged={onChanged}
        onError={onError}
        token="token"
      />,
    );
    expect(screen.getByText("rifiutata")).toBeInTheDocument();
    fireEvent.submit(screen.getByRole("button", { name: "Salva credenziale" }).closest("form")!);
    expect(apiMocks.createStepCredential).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("Etichetta"), { target: { value: " STEP 2 " } });
    fireEvent.change(screen.getByLabelText("Utente STEP"), { target: { value: " user " } });
    fireEvent.change(screen.getByLabelText("Password STEP"), { target: { value: "pw" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva credenziale" }));
    expect(screen.getByRole("button", { name: "Salvataggio..." })).toBeDisabled();
    await waitFor(() => expect(onChanged).toHaveBeenCalledWith("Credenziale STEP salvata."));
    expect(apiMocks.createStepCredential).toHaveBeenCalledWith("token", { label: "STEP 2", username: "user", password: "pw" });
    expect(screen.getByLabelText("Password STEP")).toHaveValue("");

    fireEvent.click(screen.getByRole("button", { name: "Attiva" }));
    await waitFor(() => expect(apiMocks.updateStepCredential).toHaveBeenCalledWith("token", 1, { active: true }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Elimina" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Elimina" }));
    await waitFor(() => expect(apiMocks.deleteStepCredential).toHaveBeenCalledWith("token", 1));
    expect(onChanged).toHaveBeenCalledWith(null);
  });

  it("segnala gli errori e lo stato vuoto", async () => {
    const onError = vi.fn();
    apiMocks.testStepCredential.mockRejectedValueOnce(new Error("conflitto")).mockRejectedValueOnce("x");
    const { rerender } = render(<StepCredentialsPanel credentials={[credential()]} onChanged={vi.fn()} onError={onError} token="token" />);
    expect(screen.getByRole("button", { name: "Disattiva" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Test login" }));
    await waitFor(() => expect(onError).toHaveBeenCalledWith("conflitto"));
    await waitFor(() => expect(screen.getByRole("button", { name: "Test login" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Test login" }));
    await waitFor(() => expect(onError).toHaveBeenCalledWith("Operazione credenziale STEP non riuscita"));
    rerender(<StepCredentialsPanel credentials={[]} onChanged={vi.fn()} onError={onError} token="token" />);
    expect(screen.getByText("Nessuna credenziale STEP")).toBeInTheDocument();
  });
});

describe("StepJobsPanel", () => {
  it("accoda le diverse modalita con il payload corretto", async () => {
    const onChanged = vi.fn().mockResolvedValue(undefined);
    apiMocks.createStepJob.mockResolvedValue({});
    const { rerender } = render(<StepJobsPanel archives={["a.zip"]} jobs={[]} onChanged={onChanged} onError={vi.fn()} token="token" />);
    expect(screen.getByText("Nessun job STEP")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Avvia" }));
    expect(screen.getByRole("button", { name: "Accodamento..." })).toBeDisabled();
    await waitFor(() => expect(onChanged).toHaveBeenCalledWith("Job STEP accodato sul worker."));
    expect(apiMocks.createStepJob).toHaveBeenLastCalledWith("token", { mode: "sync", max_details: null, force_details: false });

    fireEvent.change(screen.getByLabelText("Massimo schede"), { target: { value: "5" } });
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "Avvia" }));
    await waitFor(() => expect(apiMocks.createStepJob).toHaveBeenLastCalledWith("token", { mode: "sync", max_details: 5, force_details: true }));

    fireEvent.change(screen.getByLabelText("Operazione"), { target: { value: "relink" } });
    await waitFor(() => expect(screen.getByRole("button", { name: "Avvia" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Avvia" }));
    await waitFor(() => expect(apiMocks.createStepJob).toHaveBeenLastCalledWith("token", { mode: "relink" }));

    fireEvent.change(screen.getByLabelText("Operazione"), { target: { value: "archive_import" } });
    expect(screen.getByRole("button", { name: "Avvia" })).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Archivio"), { target: { value: "a.zip" } });
    fireEvent.click(screen.getByRole("button", { name: "Avvia" }));
    await waitFor(() => expect(apiMocks.createStepJob).toHaveBeenLastCalledWith("token", { mode: "archive_import", archive_name: "a.zip" }));

    rerender(<StepJobsPanel archives={[]} jobs={[]} onChanged={onChanged} onError={vi.fn()} token="token" />);
    expect(screen.getByText("Nessun archivio .zip nella cartella import STEP del server.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Aggiorna/ }));
    expect(onChanged).toHaveBeenLastCalledWith(null);
  });

  it("annulla, elimina e segnala gli errori", async () => {
    const onChanged = vi.fn().mockResolvedValue(undefined);
    const onError = vi.fn();
    apiMocks.cancelStepJob.mockResolvedValue({});
    apiMocks.deleteStepJob.mockRejectedValueOnce(new Error("in uso")).mockRejectedValueOnce("x");
    render(
      <StepJobsPanel
        archives={[]}
        jobs={[job({ id: 1, status: "pending", mode: "sync" }), job({ id: 2, status: "processing" }), job({ id: 3, status: "failed", error_detail: "rifiutata" })]}
        onChanged={onChanged}
        onError={onError}
        token="token"
      />,
    );
    const rows = screen.getAllByRole("row");
    expect(within(rows[2]).queryByRole("button")).toBeNull();
    expect(screen.getByText("rifiutata")).toBeInTheDocument();
    fireEvent.click(within(rows[1]).getByRole("button", { name: "Annulla" }));
    await waitFor(() => expect(apiMocks.cancelStepJob).toHaveBeenCalledWith("token", 1));
    await waitFor(() => expect(within(rows[3]).getByRole("button", { name: "Elimina" })).toBeEnabled());
    fireEvent.click(within(rows[3]).getByRole("button", { name: "Elimina" }));
    await waitFor(() => expect(onError).toHaveBeenCalledWith("in uso"));
    await waitFor(() => expect(within(rows[3]).getByRole("button", { name: "Elimina" })).toBeEnabled());
    fireEvent.click(within(rows[3]).getByRole("button", { name: "Elimina" }));
    await waitFor(() => expect(onError).toHaveBeenCalledWith("Operazione job STEP non riuscita"));
  });
});

describe("StepContribuentiPanel", () => {
  it("cerca, pagina e apre la scheda", async () => {
    apiMocks.listStepContribuenti.mockResolvedValue({ items: [row, { ...row, id: "c2", denominazione: null, numero_documenti: null, stato_documenti: null }], total: 60, page: 2, page_size: 25 });
    apiMocks.getStepContribuente.mockResolvedValue(detail());
    render(<StepContribuentiPanel onError={vi.fn()} token="token" />);
    expect(await screen.findByText("ROSSI MARIO")).toBeInTheDocument();
    expect(screen.getByText("60 contribuenti · pagina 2 di 3")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Successiva" }));
    await waitFor(() => expect(apiMocks.listStepContribuenti).toHaveBeenLastCalledWith("token", { q: "", onlyResiduo: false, page: 3, pageSize: 25 }));
    fireEvent.click(screen.getByRole("button", { name: "Precedente" }));
    await waitFor(() => expect(apiMocks.listStepContribuenti).toHaveBeenLastCalledWith("token", { q: "", onlyResiduo: false, page: 1, pageSize: 25 }));
    fireEvent.change(screen.getByLabelText("Cerca contribuente"), { target: { value: " ROSSI " } });
    fireEvent.click(screen.getByRole("button", { name: "Cerca" }));
    await waitFor(() => expect(apiMocks.listStepContribuenti).toHaveBeenLastCalledWith("token", { q: "ROSSI", onlyResiduo: false, page: 1, pageSize: 25 }));
    fireEvent.click(screen.getByRole("checkbox"));
    await waitFor(() => expect(apiMocks.listStepContribuenti).toHaveBeenLastCalledWith("token", { q: "ROSSI", onlyResiduo: true, page: 1, pageSize: 25 }));
    fireEvent.click(screen.getByRole("button", { name: "ROSSI MARIO" }));
    expect(await screen.findByText("Documento 20241421500000003")).toBeInTheDocument();
    expect(screen.getAllByText("ROSSI MARIO")[0].closest("tr")).toHaveClass("bg-[#eef7f1]");
  });

  it("mostra stato vuoto ed errori", async () => {
    const onError = vi.fn();
    apiMocks.listStepContribuenti.mockRejectedValueOnce(new Error("offline")).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 25 });
    const { unmount } = render(<StepContribuentiPanel onError={onError} token="token" />);
    await waitFor(() => expect(onError).toHaveBeenCalledWith("offline"));
    expect(screen.getByText("Nessun contribuente")).toBeInTheDocument();
    unmount();
    apiMocks.listStepContribuenti.mockRejectedValueOnce("x");
    const second = render(<StepContribuentiPanel onError={onError} token="token" />);
    await waitFor(() => expect(onError).toHaveBeenCalledWith("Errore caricamento contribuenti STEP"));
    second.unmount();
    apiMocks.listStepContribuenti.mockResolvedValue({ items: [row], total: 1, page: 1, page_size: 25 });
    apiMocks.getStepContribuente.mockRejectedValueOnce(new Error("404")).mockRejectedValueOnce("x");
    render(<StepContribuentiPanel onError={onError} token="token" />);
    fireEvent.click(await screen.findByRole("button", { name: "ROSSI MARIO" }));
    await waitFor(() => expect(onError).toHaveBeenCalledWith("404"));
    fireEvent.click(screen.getByRole("button", { name: "ROSSI MARIO" }));
    await waitFor(() => expect(onError).toHaveBeenCalledWith("Errore caricamento scheda STEP"));
  });
});

describe("StepContribuenteDetailPanel", () => {
  it("mostra documenti, collegamenti, tributi e pagamenti e scarica i PDF", async () => {
    const onError = vi.fn();
    const createObjectURL = vi.fn(() => "blob:pdf");
    const revokeObjectURL = vi.fn();
    Object.assign(URL, { createObjectURL, revokeObjectURL });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    apiMocks.downloadStepDocumentoPdf.mockResolvedValue(new Blob(["%PDF"]));
    const value = detail();
    const { rerender } = render(<StepContribuenteDetailPanel detail={value} onError={onError} token="token" />);
    expect(screen.getByRole("link", { name: "Avviso 020190006018040 (2019)" })).toHaveAttribute("href", "/ruolo/avvisi/a1");
    expect(screen.getByText("PG13319 · Riferimento non riconosciuto")).toBeInTheDocument();
    expect(screen.getByText("PDF non disponibile")).toBeInTheDocument();
    expect(screen.getByText("STORNATO").closest("tr")).toHaveClass("line-through");
    fireEvent.click(screen.getByRole("button", { name: "PDF" }));
    await waitFor(() => expect(revokeObjectURL).toHaveBeenCalledWith("blob:pdf"));
    expect(click).toHaveBeenCalled();

    value.documenti[0].pdf_original_filename = null;
    apiMocks.downloadStepDocumentoPdf.mockRejectedValueOnce(new Error("404")).mockRejectedValueOnce("x").mockResolvedValueOnce(new Blob(["%PDF"]));
    rerender(<StepContribuenteDetailPanel detail={{ ...value, denominazione: null, stato_documenti: null, pagamenti: [] }} onError={onError} token="token" />);
    expect(screen.getByText("Nessun pagamento registrato su STEP.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "PDF" }));
    await waitFor(() => expect(onError).toHaveBeenCalledWith("404"));
    fireEvent.click(screen.getByRole("button", { name: "PDF" }));
    await waitFor(() => expect(onError).toHaveBeenCalledWith("Download PDF STEP non riuscito"));
    fireEvent.click(screen.getByRole("button", { name: "PDF" }));
    await waitFor(() => expect(revokeObjectURL).toHaveBeenCalledTimes(2));
    click.mockRestore();
  });

  it("mostra un collegamento senza avviso come anomalia", () => {
    const value = detail();
    value.documenti[0].links = [{ ...value.documenti[0].links[0], ruolo_avviso_id: null }];
    render(<StepContribuenteDetailPanel detail={value} onError={vi.fn()} token="token" />);
    expect(screen.getByText("020190006018040 (2019) · Collegati")).toBeInTheDocument();
  });
});

describe("StepLinkAnomaliesPanel", () => {
  it("filtra e pagina le anomalie", async () => {
    const anomaly = { id: "l2", documento_id: "d1", reference_key: "020190000000000", codice_cnc: "020190000000000", anno_rif: 2019, status: "not_found" as const, ruolo_avviso_id: null, candidate_avviso_ids: null, tributi_count: 3, imp_carico: "10.00", imp_carico_pagato: null, imp_discaricato: null, contribuente_id: "c1", codice_fiscale: "CF", denominazione: null, num_doc: "N1" };
    apiMocks.listStepLinkAnomalies.mockResolvedValue({ items: [anomaly, { ...anomaly, id: "l3", anno_rif: null, denominazione: "BIANCHI" }], total: 120, page: 1, page_size: 50 });
    render(<StepLinkAnomaliesPanel onError={vi.fn()} token="token" />);
    expect(await screen.findByText("BIANCHI")).toBeInTheDocument();
    expect(screen.getByText("020190000000000 (2019)")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Successiva" }));
    await waitFor(() => expect(apiMocks.listStepLinkAnomalies).toHaveBeenLastCalledWith("token", { status: "", page: 2, pageSize: 50 }));
    fireEvent.click(screen.getByRole("button", { name: "Precedente" }));
    await waitFor(() => expect(apiMocks.listStepLinkAnomalies).toHaveBeenLastCalledWith("token", { status: "", page: 1, pageSize: 50 }));
    fireEvent.change(screen.getByLabelText("Esito collegamento"), { target: { value: "ambiguous" } });
    await waitFor(() => expect(apiMocks.listStepLinkAnomalies).toHaveBeenLastCalledWith("token", { status: "ambiguous", page: 1, pageSize: 50 }));
  });

  it("mostra stato vuoto ed errori", async () => {
    const onError = vi.fn();
    apiMocks.listStepLinkAnomalies.mockRejectedValueOnce(new Error("offline"));
    const { unmount } = render(<StepLinkAnomaliesPanel onError={onError} token="token" />);
    await waitFor(() => expect(onError).toHaveBeenCalledWith("offline"));
    expect(screen.getByText("0 righe · pagina 1 di 1")).toBeInTheDocument();
    unmount();
    apiMocks.listStepLinkAnomalies.mockRejectedValueOnce("x");
    render(<StepLinkAnomaliesPanel onError={onError} token="token" />);
    await waitFor(() => expect(onError).toHaveBeenCalledWith("Errore caricamento anomalie STEP"));
  });
});
