import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import PostePage from "@/app/ruolo/tributi/solleciti/poste/page";
import { countsSummary, dateTime, errorMessage, euro, statusLabel } from "@/components/ruolo/poste-dispatch/labels";
import type { PosteDispatchItem, PosteDispatchLotDetail } from "@/types/ruolo-poste-dispatch";

const api = vi.hoisted(() => ({
  listPosteCandidates: vi.fn(),
  listPosteLots: vi.fn(),
  getPosteLot: vi.fn(),
  createPosteLot: vi.fn(),
  requestPosteJob: vi.fn(),
  updatePosteRecipient: vi.fn(),
  acceptPosteManualAddress: vi.fn(),
  cancelPosteItem: vi.fn(),
  getPosteItemDocument: vi.fn(),
}));
const session = vi.hoisted(() => vi.fn());
vi.mock("@/lib/ruolo-poste-dispatch-api", () => api);
vi.mock("@/lib/ruolo-api", () => ({ listTributiReminderBatches: vi.fn(async () => ({ items: [], total: 0 })), getTributiReminderBatch: vi.fn() }));
const pathname = vi.hoisted(() => vi.fn());
vi.mock("next/navigation", () => ({ usePathname: pathname }));
vi.mock("@/lib/use-session-bootstrap", () => ({ useSessionBootstrap: session }));
vi.mock("@/components/ruolo/module-page", () => ({ RuoloModulePage: ({ children }: { children: React.ReactNode }) => <main>{children}</main> }));

const recipient = { name: "ROSSI MARIO", name_extra: "", address: "VIA CAGLIARI 170", cap: "09170", city: "ORISTANO", province: "OR" };

function item(overrides: Partial<PosteDispatchItem> = {}): PosteDispatchItem {
  return {
    id: "item-1", batch_item_id: "b1", notice_number: "020217801062586", shipment_name: "GAIA 020217801062586",
    status: "address_review", recipient, poste_address: null,
    address_review: { reason: "Nessun indirizzo dello stradario", problems: ["cap: servono 5 cifre"], suggestions: ["VIA ROMA 1, ORISTANO (OR), 09170"] },
    artifact_sha256: "a".repeat(64), artifact_size: 10, poste_draft_id: null, poste_status: null, price_amount: null,
    draft_created_at: null, sent_at: null, tracking_number: null, registered_mail_id: null, error_detail: null, updated_at: "2026-10-28T10:00:00Z",
    ...overrides,
  };
}

function lot(overrides: Partial<PosteDispatchLotDetail> = {}): PosteDispatchLotDetail {
  return {
    id: "lot-1", title: "Solleciti 2021", status: "open", created_by: 1, created_at: "2026-10-28T10:00:00Z",
    counts: { address_review: 1 }, priced_total: 0, postal_options: {}, portal_snapshot: null, draft_expires_at: null,
    active_job: null, items: [item()], events: [], ...overrides,
  };
}

function grant(sections = ["ruolo.tributi.view", "ruolo.tributi.manage_status"], role = "admin", modules = ["ruolo"]) {
  session.mockReturnValue({ status: "ready", token: "token", currentUser: { role, enabled_modules: modules }, grantedSectionKeys: sections });
}

async function openLot(detail = lot()) {
  api.getPosteLot.mockResolvedValue(detail);
  render(<PostePage />);
  fireEvent.click(await screen.findByRole("button", { name: /Solleciti 2021/ }));
  return screen.findByRole("region", { name: "Dettaglio lotto Poste" });
}

beforeEach(() => {
  vi.resetAllMocks();
  pathname.mockReturnValue("/ruolo/tributi/solleciti/poste");
  grant();
  api.listPosteLots.mockResolvedValue({ items: [lot()], total: 1, page: 1, page_size: 50 });
  api.listPosteCandidates.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 });
});
afterEach(() => cleanup());

describe("access", () => {
  it("waits for the session and refuses users without the section", () => {
    session.mockReturnValue({ status: "loading" });
    const view = render(<PostePage />);
    expect(screen.getByRole("status")).toHaveTextContent("Verifica accesso");
    view.unmount();
    grant(["ruolo.tributi.view"], "admin", []);
    const second = render(<PostePage />);
    expect(screen.getByRole("alert")).toHaveTextContent("Accesso non autorizzato");
    second.unmount();
    grant([], "super_admin", []);
    render(<PostePage />);
    expect(screen.getByRole("alert")).toHaveTextContent("Accesso non autorizzato");
  });

  it("shows lots read-only to viewers", async () => {
    grant(["ruolo.tributi.view"]);
    api.listPosteLots.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 });
    render(<PostePage />);
    expect(await screen.findByText("Nessun lotto Poste.")).toBeVisible();
    expect(screen.getByText("Accesso in sola lettura.")).toBeVisible();
    expect(screen.queryByRole("region", { name: "Nuovo lotto Poste" })).not.toBeInTheDocument();
  });

  it("reports a failed load", async () => {
    api.listPosteLots.mockRejectedValue(new Error("Backend non raggiungibile"));
    render(<PostePage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Backend non raggiungibile");
  });
});

describe("new lot", () => {
  it("selects generated reminders and creates the lot", async () => {
    api.listPosteCandidates.mockResolvedValue({ items: [
      { batch_item_id: "b1", batch_title: "Lotto Cabras", display_name: "ROSSI MARIO", codice_fiscale: "RSS", notice_number: "0202", years: [2021], created_at: "2026-10-28T10:00:00Z" },
      { batch_item_id: "b2", batch_title: null, display_name: null, codice_fiscale: "BNC", notice_number: null, years: [], created_at: "2026-10-28T10:00:00Z" },
    ], total: 2, page: 1, page_size: 50 });
    api.createPosteLot.mockResolvedValue(lot());
    api.getPosteLot.mockResolvedValue(lot());
    render(<PostePage />);
    const picker = await screen.findByRole("region", { name: "Nuovo lotto Poste" });
    fireEvent.change(within(picker).getByLabelText("Cerca sollecito"), { target: { value: "rossi" } });
    await waitFor(() => expect(api.listPosteCandidates).toHaveBeenLastCalledWith("token", "rossi"));
    const boxes = await within(picker).findAllByRole("checkbox");
    fireEvent.click(boxes[0]);
    fireEvent.click(boxes[1]);
    fireEvent.click(boxes[1]);
    expect(within(picker).getByText(/Lotto senza titolo/)).toBeVisible();
    fireEvent.change(within(picker).getByLabelText("Titolo lotto"), { target: { value: "Solleciti 2021" } });
    fireEvent.click(within(picker).getByRole("button", { name: "Crea lotto (1)" }));
    await waitFor(() => expect(api.createPosteLot).toHaveBeenCalledWith("token", "Solleciti 2021", ["b1"]));
    expect(await screen.findByRole("region", { name: "Dettaglio lotto Poste" })).toBeVisible();
  });

  it("caps the selection at 50 and shows creation and loading errors", async () => {
    const candidates = Array.from({ length: 51 }, (_, index) => ({ batch_item_id: `b${index}`, batch_title: "L", display_name: `N${index}`, codice_fiscale: "X", notice_number: "1", years: [], created_at: "2026-10-28T10:00:00Z" }));
    api.listPosteCandidates.mockResolvedValue({ items: candidates, total: 51, page: 1, page_size: 50 });
    api.createPosteLot.mockRejectedValue(new Error("Un sollecito è già in un altro lotto Poste attivo"));
    render(<PostePage />);
    const picker = await screen.findByRole("region", { name: "Nuovo lotto Poste" });
    const boxes = await within(picker).findAllByRole("checkbox");
    boxes.forEach((box) => fireEvent.click(box));
    fireEvent.change(within(picker).getByLabelText("Titolo lotto"), { target: { value: "Pieno" } });
    fireEvent.click(within(picker).getByRole("button", { name: "Crea lotto (50)" }));
    expect(await within(picker).findByRole("alert")).toHaveTextContent("già in un altro lotto");
    api.listPosteCandidates.mockRejectedValue("offline");
    api.createPosteLot.mockRejectedValue("offline");
    fireEvent.change(within(picker).getByLabelText("Cerca sollecito"), { target: { value: "x" } });
    await waitFor(() => expect(within(picker).getByRole("alert")).toHaveTextContent("Solleciti non caricati"));
    fireEvent.click(within(picker).getByRole("button", { name: "Crea lotto (50)" }));
    await waitFor(() => expect(within(picker).getByRole("alert")).toHaveTextContent("Lotto non creato"));
  });

  it("ignores answers to a superseded search", async () => {
    let resolveFirst: (value: unknown) => void = () => undefined;
    let rejectSecond: (reason: unknown) => void = () => undefined;
    api.listPosteCandidates
      .mockReturnValueOnce(new Promise((resolve) => { resolveFirst = resolve; }))
      .mockReturnValueOnce(new Promise((_, reject) => { rejectSecond = reject; }))
      .mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 });
    render(<PostePage />);
    const picker = await screen.findByRole("region", { name: "Nuovo lotto Poste" });
    fireEvent.change(within(picker).getByLabelText("Cerca sollecito"), { target: { value: "a" } });
    fireEvent.change(within(picker).getByLabelText("Cerca sollecito"), { target: { value: "ab" } });
    resolveFirst({ items: [{ batch_item_id: "late", batch_title: "L", display_name: "TARDI", codice_fiscale: "X", notice_number: "1", years: [], created_at: "2026-10-28T10:00:00Z" }] });
    rejectSecond(new Error("stale"));
    await waitFor(() => expect(api.listPosteCandidates).toHaveBeenCalledTimes(3));
    expect(within(picker).queryByText("TARDI")).not.toBeInTheDocument();
    expect(within(picker).queryByRole("alert")).not.toBeInTheDocument();
  });
});

describe("lot detail", () => {
  it("queues portal jobs and reports conflicts", async () => {
    api.requestPosteJob.mockResolvedValueOnce({}).mockRejectedValueOnce(new Error("C'è già un'operazione")).mockRejectedValueOnce("x");
    const detail = await openLot();
    fireEvent.click(within(detail).getByRole("button", { name: "Crea bozze su Poste" }));
    await waitFor(() => expect(api.requestPosteJob).toHaveBeenCalledWith("token", "lot-1", "drafts"));
    fireEvent.click(within(detail).getByRole("button", { name: "Controlla Poste" }));
    expect(await within(detail).findByText("C'è già un'operazione")).toBeVisible();
    fireEvent.click(within(detail).getByRole("button", { name: "Verifica indirizzi" }));
    expect(await within(detail).findByText("Operazione non avviata")).toBeVisible();
    fireEvent.click(within(detail).getByRole("button", { name: "Aggiorna" }));
    await waitFor(() => expect(api.getPosteLot).toHaveBeenCalledTimes(3));
  });

  it("warns about foreign or duplicate drafts and shows the running job and expiry", async () => {
    const detail = await openLot(lot({
      priced_total: 10.86,
      draft_expires_at: "2026-11-04T10:00:00Z",
      active_job: { id: 4, mode: "poste_dispatch_reconcile", status: "processing", error_detail: "In attesa di una credenziale", created_at: "2026-10-28T10:00:00Z" },
      portal_snapshot: { foreign_drafts: [{ draft_id: "1", name: "BIANCHI ANNA", status: "PREZZATO" }], duplicate_names: ["GAIA 1"] },
    }));
    expect(within(detail).getByRole("status")).toHaveTextContent("Controllo Poste (processing) - In attesa di una credenziale");
    expect(within(detail).getByText(/INVIA potrebbe spedire anche quelle. BIANCHI ANNA/)).toBeVisible();
    expect(within(detail).getByText(/Bozze doppie su Poste: GAIA 1/)).toBeVisible();
    expect(within(detail).getByText(/Le bozze scadono su Poste/)).toBeVisible();
    expect(within(detail).getByRole("link", { name: /Verifica e invia/ })).toHaveAttribute("href", "https://corrispondenza.poste.it/col/incorso.do");
    expect(within(detail).getByRole("button", { name: "Crea bozze su Poste" })).toBeDisabled();
  });

  it("shows only duplicates or an unknown job mode", async () => {
    const detail = await openLot(lot({
      active_job: { id: 4, mode: "poste_dispatch_other", status: "pending", error_detail: null, created_at: "2026-10-28T10:00:00Z" },
      portal_snapshot: { duplicate_names: ["GAIA 1"] },
      items: [item({ address_review: { reason: "Più indirizzi dello stradario coincidono" } })],
    }));
    expect(within(detail).getByText("Più indirizzi dello stradario coincidono")).toBeVisible();
    expect(within(detail).getByRole("status")).toHaveTextContent("In corso: poste_dispatch_other (pending)");
    expect(within(detail).queryByText(/non sono di questo lotto/)).not.toBeInTheDocument();
  });
});

describe("items", () => {
  it("corrects a recipient, accepts a manual address and cancels", async () => {
    api.updatePosteRecipient.mockRejectedValueOnce(new Error("cap: servono 5 cifre")).mockResolvedValueOnce(item());
    api.acceptPosteManualAddress.mockRejectedValueOnce("x").mockResolvedValueOnce(item());
    api.cancelPosteItem.mockResolvedValue(item({ status: "cancelled" }));
    const detail = await openLot();
    expect(within(detail).getByText(/Nessun indirizzo dello stradario: cap: servono 5 cifre/)).toBeVisible();
    expect(within(detail).getByText(/Proposte Poste: VIA ROMA 1/)).toBeVisible();
    fireEvent.click(within(detail).getByRole("button", { name: "Correggi destinatario" }));
    fireEvent.change(within(detail).getByLabelText("CAP"), { target: { value: "091" } });
    fireEvent.click(within(detail).getByRole("button", { name: "Salva e riverifica" }));
    expect(await within(detail).findByText("cap: servono 5 cifre")).toBeVisible();
    fireEvent.change(within(detail).getByLabelText("CAP"), { target: { value: "09170" } });
    fireEvent.click(within(detail).getByRole("button", { name: "Salva e riverifica" }));
    await waitFor(() => expect(api.updatePosteRecipient).toHaveBeenLastCalledWith("token", "lot-1", "item-1", recipient));
    fireEvent.click(within(detail).getByRole("button", { name: "Usa indirizzo manuale" }));
    expect(await within(detail).findByText("Indirizzo non accettato")).toBeVisible();
    fireEvent.click(within(detail).getByRole("button", { name: "Usa indirizzo manuale" }));
    fireEvent.click(within(detail).getByRole("button", { name: "Annulla" }));
    await waitFor(() => expect(api.cancelPosteItem).toHaveBeenCalledWith("token", "lot-1", "item-1"));
  });

  it("closes the editor and handles a non-Error save failure", async () => {
    api.updatePosteRecipient.mockRejectedValue("offline");
    const detail = await openLot();
    fireEvent.click(within(detail).getByRole("button", { name: "Correggi destinatario" }));
    fireEvent.click(within(detail).getByRole("button", { name: "Salva e riverifica" }));
    expect(await within(detail).findByText("Destinatario non salvato")).toBeVisible();
    fireEvent.click(within(detail).getByRole("button", { name: "Chiudi" }));
    expect(within(detail).queryByLabelText("CAP")).not.toBeInTheDocument();
  });

  it("opens the PDF snapshot in a new tab", async () => {
    const open = vi.spyOn(window, "open").mockReturnValue(null);
    URL.createObjectURL = vi.fn(() => "blob:pdf");
    api.getPosteItemDocument.mockResolvedValueOnce(new Blob(["%PDF"])).mockRejectedValueOnce(new Error("PDF non più conservato"));
    const detail = await openLot();
    fireEvent.click(within(detail).getByRole("button", { name: "Apri PDF" }));
    await waitFor(() => expect(open).toHaveBeenCalledWith("blob:pdf", "_blank", "noopener"));
    fireEvent.click(within(detail).getByRole("button", { name: "Apri PDF" }));
    expect(await within(detail).findByText("PDF non più conservato")).toBeVisible();
  });

  it("shows sent shipments without actions", async () => {
    const detail = await openLot(lot({ items: [item({ status: "sent", address_review: null, price_amount: 5.43, tracking_number: "619591492509", poste_draft_id: "12269236", error_detail: "Registro non aggiornato" })] }));
    expect(within(detail).getByText(/raccomandata 619591492509/)).toBeVisible();
    expect(within(detail).getByText("Spedito")).toBeVisible();
    expect(within(detail).getByText("Registro non aggiornato")).toBeVisible();
    expect(within(detail).queryByRole("button", { name: "Apri PDF" })).not.toBeInTheDocument();
    expect(within(detail).queryByRole("button", { name: "Annulla" })).not.toBeInTheDocument();
  });

  it("lets viewers only open documents", async () => {
    grant(["ruolo.tributi.view"]);
    const detail = await openLot(lot({ items: [item({ status: "mystery", address_review: { suggestions: [] } })] }));
    expect(within(detail).getByText("mystery")).toBeVisible();
    expect(within(detail).getByRole("button", { name: "Apri PDF" })).toBeVisible();
    expect(within(detail).queryByRole("button", { name: "Correggi destinatario" })).not.toBeInTheDocument();
  });
});

it("formats labels with fallbacks", () => {
  expect(statusLabel("draft_priced")).toBe("Bozza prezzata");
  expect(euro(null)).toBe("-");
  expect(euro(5.43)).toContain("5,43");
  expect(dateTime(null)).toBe("-");
  expect(countsSummary({})).toBe("Nessun avviso");
  expect(countsSummary({ sent: 2 })).toBe("2 spedito");
  expect(errorMessage("x", "fallback")).toBe("fallback");
});
