import { useEffect } from "react";
import { act, cleanup, fireEvent, render, renderHook, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { CommunicationsAccess } from "@/components/communications/workspace";
import { useCommunicationsWorkspace } from "@/components/communications/use-workspace";
import { SollecitiNavigation } from "@/components/communications/navigation";
import PecPage from "@/app/ruolo/tributi/solleciti/pec/page";
import EmailPage from "@/app/ruolo/tributi/solleciti/email/page";
import { candidate, message, account, template, session } from "./fixtures";
const mocks = vi.hoisted(() => ({ api: vi.fn(), session: vi.fn(), previewReady: true }));
vi.mock("@/lib/communications-api", () => ({ communications: mocks.api }));
vi.mock("@/lib/use-session-bootstrap", () => ({ useSessionBootstrap: mocks.session }));
vi.mock("@/components/ruolo/module-page", () => ({ RuoloModulePage: ({ children }: { children: React.ReactNode }) => <main>{children}</main> }));
vi.mock("@/components/communications/composer", () => ({ CommunicationComposer: ({ message: value }: { message: typeof message }) => <p>Composer {value.id}</p> }));
vi.mock("@/components/communications/source-preview", () => ({ SourcePreview: ({ onReady }: { onReady: (hash: string) => void }) => { useEffect(() => onReady(mocks.previewReady ? "a".repeat(64) : ""), [onReady]); return <><p>Anteprima immediata</p><button onClick={() => onReady("a".repeat(64))}>Completa rendering</button></>; } }));
beforeEach(() => {
  vi.resetAllMocks(); mocks.previewReady = true; mocks.session.mockReturnValue(session);
  mocks.api.mockImplementation((_token, path) => Promise.resolve(path.includes("candidates?") ? { items: [candidate], total: 26 } : path === "/accounts" ? [account, { ...account, channel: "email", id: "ordinary" }] : path === "/templates" ? [template, { ...template, id: "email-template", channel: "email" }] : message));
});
afterEach(cleanup);
it("checks session, module and read permissions before loading any protected data", () => {
  for (const value of [{ status: "checking" }, { ...session, token: null }, { ...session, currentUser: null }, { ...session, currentUser: { ...session.currentUser, enabled_modules: [] } }, { ...session, grantedSectionKeys: [] }]) {
    mocks.session.mockReturnValue(value);
    const view = render(<CommunicationsAccess channel="pec" />);
    expect(screen.getByText(/Verifica accesso|Accesso non autorizzato/)).toBeInTheDocument();
    view.unmount();
  }
  expect(mocks.api).not.toHaveBeenCalled();
});
it("uses server-side filters/pagination and builds an individual draft from a verified contact", async () => {
  render(<PecPage />);
  await screen.findByText(/Contribuente sintetico/);
  for (const [label, value] of [["Cerca nominativo, CF o avviso", "Synthetic"], ["Recapito", "false"], ["Presenza PEC", "true"], ["Presenza email", "false"], ["Stato", "draft"], ["Account", "account"], ["Dal", "2026-01-01"], ["Al", "2026-12-31"], ["Lotto (UUID)", "batch"], ["Pagamento", "unpaid"], ["Notifica", "nessuna_evidenza"]]) {
    fireEvent.change(screen.getByLabelText(label), { target: { value } });
  }
  await waitFor(() => expect(mocks.api.mock.calls.some((call) => call[1].includes("q=Synthetic") && call[1].includes("year=2021"))).toBe(true));
  fireEvent.click(screen.getByText("Successiva"));
  await waitFor(() => expect(screen.getByText("2 / 2")).toBeInTheDocument());
  fireEvent.click(screen.getByText("Precedente"));
  fireEvent.click(screen.getByText("Aggiorna stati"));
  fireEvent.click(screen.getByLabelText("Seleziona 1/2021"));
  expect(screen.getByLabelText("Recapito verificato")).toHaveValue("recipient@example.org");
  fireEvent.click(screen.getByLabelText("Seleziona 1/2021"));
  expect(screen.queryByLabelText("Nuova comunicazione")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("row", { name: "Apri avviso 1/2021" }));
  fireEvent.change(screen.getByLabelText("Account", { selector: "section select" }), { target: { value: "account" } });
  fireEvent.change(screen.getByLabelText("Recapito verificato"), { target: { value: "checked@example.org" } });
  fireEvent.change(screen.getByLabelText("Template approvato"), { target: { value: "template" } });
  fireEvent.change(screen.getByLabelText("Oggetto"), { target: { value: "Personalizzato" } });
  fireEvent.change(screen.getByLabelText("Testo"), { target: { value: "Testo" } });
  fireEvent.click(screen.getByText("Crea bozza e snapshot PDF"));
  await screen.findByText("Composer message");
  expect(mocks.api.mock.calls.find((call) => call[1] === "/messages")?.[2]).toMatchObject({ channel: "pec", purpose: "pec_notice", account_id: "account", template_id: "template", recipient: "checked@example.org", expected_source_sha256: "a".repeat(64) });
});
it("opens cancelled history and a fresh email revision, preserving ordinary email policy", async () => {
  mocks.api.mockImplementation((_token, path) => Promise.resolve(path.includes("candidates?") ? { items: [{ ...candidate, pec: null, message_id: "message", communication_state: "cancelled", last_event_at: "today" }], total: 1 } : path === "/accounts" ? [account] : path === "/templates" ? [template] : { ...message, channel: "email" }));
  render(<EmailPage />);
  fireEvent.click(await screen.findByRole("row", { name: "Apri avviso 1/2021" }));
  await screen.findByText("Composer message");
  fireEvent.click(screen.getByText("Aggiorna stati"));
  fireEvent.click(screen.getByText("Nuova revisione"));
  fireEvent.click(screen.getByText("Crea bozza e snapshot PDF"));
  await screen.findByText("Composer message");
  expect(mocks.api.mock.calls.find((call) => call[1] === "/messages")?.[2]).toMatchObject({ channel: "email", purpose: "courtesy", account_id: null, template_id: null, subject: null, body: null });
});
it("allows a read-only operator and super administrator to inspect history without composition", async () => {
  mocks.session.mockReturnValue({ ...session, currentUser: { role: "super_admin", enabled_modules: [] }, grantedSectionKeys: ["ruolo.tributi.view"] });
  const view = render(<PecPage />);
  await screen.findByText(/Contribuente sintetico/);
  expect(screen.getByRole("row", { name: "Apri avviso 1/2021" })).toHaveAttribute("aria-disabled", "true");
  expect(screen.getByLabelText("Seleziona 1/2021")).toBeDisabled();
  expect(mocks.api.mock.calls.some((call) => call[1] === "/accounts")).toBe(false);
  view.unmount();
  mocks.session.mockReturnValue({ ...session, currentUser: { role: "operator", enabled_modules: ["ruolo"] } });
  render(<PecPage />); await screen.findByText(/Contribuente sintetico/);
  expect(screen.queryByText("Amministrazione comunicazioni")).not.toBeInTheDocument();
});
it("reports loading and command failures, ignores stale responses and uses fallback error text", async () => {
  const { result, unmount } = renderHook(() => useCommunicationsWorkspace("token", "pec", true));
  await waitFor(() => expect(result.current.status.loading).toBe(false));
  await act(async () => result.current.create());
  for (const failure of [new Error("Denied"), "error"]) {
    mocks.api.mockRejectedValue(failure);
    await act(async () => result.current.open({ ...candidate, message_id: "message" }));
    expect(result.current.status.error).toBe(failure instanceof Error ? "Denied" : "Operazione fallita");
    await act(async () => result.current.open({ ...candidate, pec: null }));
    expect(result.current.compose.recipient).toBe("");
    await act(async () => result.current.create());
    expect(result.current.status.error).toBe(failure instanceof Error ? "Denied" : "Operazione fallita");
    act(() => result.current.setMessage(message));
    await act(async () => result.current.refresh());
  }
  unmount();
  let resolve!: (value: unknown) => void;
  mocks.api.mockImplementation(() => new Promise((done) => { resolve = done; }));
  const late = renderHook(() => useCommunicationsWorkspace("token", "pec", true));
  late.unmount(); await act(async () => resolve([]));
  mocks.api.mockRejectedValue(new Error("Unavailable"));
  const failed = render(<PecPage />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Unavailable"); failed.unmount();
  let reject!: (reason: unknown) => void;
  mocks.api.mockImplementation(() => new Promise((_done, fail) => { reject = fail; }));
  const lateFailure = renderHook(() => useCommunicationsWorkspace("token", "pec", false));
  lateFailure.unmount(); await act(async () => reject(new Error("late")));
});
it("keeps generated/Posta Online tab actions and both channel routes accessible", () => {
  const onChange = vi.fn();
  const { rerender } = render(<SollecitiNavigation tab="generati" onChange={onChange} />);
  fireEvent.click(screen.getByRole("tab", { name: "Posta Online" }));
  expect(onChange).toHaveBeenLastCalledWith("poste");
  rerender(<SollecitiNavigation tab="poste" onChange={onChange} />);
  fireEvent.click(screen.getByRole("tab", { name: "Solleciti generati" }));
  expect(onChange).toHaveBeenLastCalledWith("generati");
  expect(screen.getByText("Invio PEC")).toHaveAttribute("href", "/ruolo/tributi/solleciti/pec");
});
it("leaves missing contacts visible and requires an explicit verified address", async () => {
  mocks.api.mockImplementation((_token, path) => Promise.resolve(path.includes("candidates?") ? { items: [{ ...candidate, pec: null }], total: 1 } : []));
  render(<PecPage />);
  await screen.findByText("Da verificare");
  fireEvent.click(screen.getByLabelText("Seleziona 1/2021"));
  expect(screen.getByLabelText("Recapito verificato")).toHaveValue("");
  expect(screen.getByText("Crea bozza e snapshot PDF")).toBeDisabled();
});

it("keeps the selected notice and fields in the right panel while the candidate list remains available", async () => {
  const second = { ...candidate, id: "second", notice_number: "2/2021", pec: "second@example.org" };
  mocks.api.mockImplementation((_token, path) => Promise.resolve(path.includes("candidates?") ? { items: [candidate, second], total: 2 } : path === "/accounts" ? [account] : path === "/templates" ? [] : { ...message, source_entity_id: second.id, notice_number: second.notice_number }));
  render(<PecPage />);
  const list = screen.getByRole("region", { name: "Elenco avvisi" });
  const panel = screen.getByRole("complementary", { name: "Composizione avviso" });
  expect(within(panel).getByText("Composizione e documento")).toBeInTheDocument();
  await within(list).findByRole("row", { name: "Apri avviso 1/2021" });
  fireEvent.click(within(list).getByRole("row", { name: "Apri avviso 1/2021" }));
  expect(within(panel).getByRole("heading", { name: "Componi avviso 1/2021" })).toBeInTheDocument();
  fireEvent.change(within(panel).getByLabelText("Oggetto"), { target: { value: "Solo primo avviso" } });
  fireEvent.click(within(list).getByRole("row", { name: "Apri avviso 2/2021" }));
  expect(within(panel).getByRole("heading", { name: "Componi avviso 2/2021" })).toBeInTheDocument();
  expect(within(panel).getByLabelText("Recapito verificato")).toHaveValue("second@example.org");
  expect(within(panel).getByLabelText("Oggetto")).toHaveValue("");
  fireEvent.click(within(panel).getByRole("button", { name: "Crea bozza e snapshot PDF" }));
  await within(panel).findByText("Composer message");
  fireEvent.click(within(list).getByLabelText("Seleziona 1/2021"));
  expect(within(panel).queryByText("Composer message")).not.toBeInTheDocument();
  expect(within(panel).getByLabelText("Recapito verificato")).toHaveValue("recipient@example.org");
});

it("clears the old document during an existing-message load and releases busy after failure", async () => {
  const { result } = renderHook(() => useCommunicationsWorkspace("token", "pec", true));
  await waitFor(() => expect(result.current.status.loading).toBe(false));
  await act(async () => result.current.open({ ...candidate, message_id: message.id }));
  expect(result.current.message).toEqual(message);
  let rejectLoad!: (reason: Error) => void;
  mocks.api.mockImplementation(() => new Promise((_resolve, reject) => { rejectLoad = reject; }));
  let opening!: Promise<void>;
  act(() => { opening = result.current.open({ ...candidate, message_id: "unavailable" }); });
  expect(result.current.status.busy).toBe(true);
  expect(result.current.message).toBeNull();
  expect(result.current.selected).toBeNull();
  await act(async () => { rejectLoad(new Error("Documento non disponibile")); await opening; });
  expect(result.current.status.busy).toBe(false);
  expect(result.current.status.error).toBe("Documento non disponibile");
  expect(result.current.message).toBeNull();
  await act(async () => result.current.open(candidate));
  expect(result.current.selected).toEqual(candidate);
  expect(result.current.status.error).toBe("");
  expect(result.current.status.busy).toBe(false);
});

it.each(["pec", "email"] as const)("defaults %s to contacts present from the first request and allows changing the filter", async (channel) => {
  render(<CommunicationsAccess channel={channel} />);
  const label = channel === "pec" ? "Presenza PEC" : "Presenza email";
  const other = channel === "pec" ? "email" : "pec";
  expect(screen.getByLabelText(label)).toHaveValue("true");
  expect(screen.getByLabelText(other === "pec" ? "Presenza PEC" : "Presenza email")).toHaveValue("");
  await screen.findByText(/Contribuente sintetico/);
  const requests = () => mocks.api.mock.calls.filter((call) => call[1].includes("/ruolo/candidates?")).map((call) => new URL(call[1], "http://localhost").searchParams);
  expect(requests()[0].get(`has_${channel}`)).toBe("true");
  expect(requests()[0].get(`has_${other}`)).toBeNull();
  fireEvent.change(screen.getByLabelText(label), { target: { value: "" } });
  await waitFor(() => expect(requests().at(-1)?.get(`has_${channel}`)).toBeNull());
  fireEvent.change(screen.getByLabelText(label), { target: { value: "false" } });
  await waitFor(() => expect(requests().at(-1)?.get(`has_${channel}`)).toBe("false"));
});

it("opens preview on checkbox selection and row activation, blocking drafts until the selected PDF is rendered", async () => {
  mocks.previewReady = false;
  render(<PecPage />);
  fireEvent.click(await screen.findByLabelText("Seleziona 1/2021"));
  expect(screen.getByText("Anteprima immediata")).toBeInTheDocument();
  expect(screen.getByText("Crea bozza e snapshot PDF")).toBeDisabled();
  expect(mocks.api.mock.calls.some((call) => call[1] === "/messages")).toBe(false);
  fireEvent.click(screen.getByText("Completa rendering"));
  expect(screen.getByText("Crea bozza e snapshot PDF")).toBeEnabled();
  fireEvent.click(screen.getByLabelText("Seleziona 1/2021"));
  fireEvent.click(screen.getByRole("row", { name: "Apri avviso 1/2021" }));
  expect(screen.getByText("Anteprima immediata")).toBeInTheDocument();
  expect(screen.getByText("Crea bozza e snapshot PDF")).toBeDisabled();
});

it("activates notice rows with Enter or Space and keeps checkbox keys and clicks independent", async () => {
  render(<PecPage />);
  const row = await screen.findByRole("row", { name: "Apri avviso 1/2021" });
  expect(row).toHaveAttribute("tabindex", "0");
  expect(screen.queryByRole("button", { name: "Componi", exact: true })).not.toBeInTheDocument();
  fireEvent.keyDown(row, { key: "Escape" });
  expect(screen.queryByLabelText("Recapito verificato")).not.toBeInTheDocument();
  fireEvent.keyDown(row, { key: "Enter" });
  expect(screen.getByLabelText("Recapito verificato")).toHaveValue(candidate.pec);
  fireEvent.change(screen.getByLabelText("Oggetto"), { target: { value: "Da conservare" } });
  fireEvent.keyDown(screen.getByLabelText("Seleziona 1/2021"), { key: "Enter" });
  expect(screen.getByLabelText("Oggetto")).toHaveValue("Da conservare");
  fireEvent.keyDown(row, { key: " " });
  expect(screen.getByLabelText("Oggetto")).toHaveValue("");
  fireEvent.click(screen.getByLabelText("Seleziona 1/2021"));
  expect(screen.queryByLabelText("Recapito verificato")).not.toBeInTheDocument();
  fireEvent.click(within(row).getByText(/Contribuente sintetico/));
  expect(screen.getByLabelText("Recapito verificato")).toHaveValue(candidate.pec);
});

it("blocks row activation for read-only drafts but opens existing history", async () => {
  mocks.session.mockReturnValue({ ...session, grantedSectionKeys: ["ruolo.tributi.view"] });
  const history = { ...candidate, id: "history", notice_number: "2/2021", message_id: "message" };
  mocks.api.mockImplementation((_token, path) => Promise.resolve(path.includes("candidates?") ? { items: [candidate, history], total: 2 } : path === "/templates" ? [] : message));
  render(<PecPage />);
  const blocked = await screen.findByRole("row", { name: "Apri avviso 1/2021" });
  expect(blocked).toHaveAttribute("tabindex", "-1");
  fireEvent.click(blocked); fireEvent.keyDown(blocked, { key: "Enter" });
  expect(screen.queryByLabelText("Recapito verificato")).not.toBeInTheDocument();
  expect(mocks.api.mock.calls.some((call) => call[1].startsWith("/messages"))).toBe(false);
  const existing = screen.getByRole("row", { name: "Apri avviso 2/2021" });
  expect(existing).toHaveAttribute("aria-disabled", "false");
  fireEvent.click(existing);
  await screen.findByText("Composer message");
});

it("blocks additional row and revision actions while loading history and recovers after failure", async () => {
  const history = { ...candidate, message_id: "message", communication_state: "cancelled" };
  let rejectLoad!: (reason: Error) => void;
  mocks.api.mockImplementation((_token, path) => path.startsWith("/messages/") ? new Promise((_resolve, reject) => { rejectLoad = reject; }) : Promise.resolve(path.includes("candidates?") ? { items: [history], total: 1 } : []));
  render(<PecPage />);
  const row = await screen.findByRole("row", { name: "Apri avviso 1/2021" });
  fireEvent.click(row);
  expect(row).toHaveAttribute("aria-disabled", "true");
  expect(screen.getByRole("button", { name: "Nuova revisione" })).toBeDisabled();
  fireEvent.click(row); fireEvent.keyDown(row, { key: " " });
  expect(mocks.api.mock.calls.filter((call) => call[1].startsWith("/messages/"))).toHaveLength(1);
  await act(async () => rejectLoad(new Error("Storico non disponibile")));
  expect(screen.getByRole("alert")).toHaveTextContent("Storico non disponibile");
  expect(row).toHaveAttribute("aria-disabled", "false");
  fireEvent.click(screen.getByRole("button", { name: "Nuova revisione" }));
  expect(screen.getByLabelText("Recapito verificato")).toHaveValue(candidate.pec);
  expect(mocks.api.mock.calls.filter((call) => call[1].startsWith("/messages/"))).toHaveLength(1);
});
