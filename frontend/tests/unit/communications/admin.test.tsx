import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { AccountAdministration } from "@/components/communications/admin-accounts";
import { TemplateAdministration } from "@/components/communications/admin-templates";
import AdminPage from "@/app/gaia/communications/page";
import { session, template } from "./fixtures";
const mocks = vi.hoisted(() => ({ api: vi.fn(), session: vi.fn() }));
vi.mock("@/lib/communications-api", () => ({ communications: mocks.api }));
vi.mock("@/lib/use-session-bootstrap", () => ({ useSessionBootstrap: mocks.session }));
vi.mock("@/components/app/protected-page", () => ({ ProtectedPage: ({ children }: { children: React.ReactNode }) => <main>{children}</main> }));
const stored = { id: "account", version: 1, health: "untested", last_test_at: null, last_sync_at: null, name: "Synthetic", channel: "pec", provider: "synthetic", sender: "sender@example.org", display_name: "Office", smtp_host: "smtp.example.org", smtp_port: 465, smtp_encryption: "tls", imap_host: "imap.example.org", imap_port: 993, imap_encryption: "tls", auth_method: "password", username: "synthetic", secret_ref: "synthetic", active: false, paused: true, allowed_modules: ["ruolo"], allowed_user_ids: [], default_modules: [], is_default: false, priority: 100, max_bytes: 10000, hourly_limit: 10 };
beforeEach(() => { vi.resetAllMocks(); mocks.session.mockReturnValue(session); mocks.api.mockImplementation((_token, path) => Promise.resolve(path === "/admin/accounts" ? [stored] : path === "/admin/templates" ? [{ ...template, status: "draft" }] : path === "/admin/monitor" ? { paused: true, transport_enabled: false, worker_seen_at: null, queues: { pending: 3 }, uncertain: 1, unmatched_receipts: 2 } : {})); });
afterEach(() => { cleanup(); vi.useRealTimers(); vi.restoreAllMocks(); });
it("guards administration before reading account settings", () => {
  for (const value of [{ status: "checking" }, { ...session, token: null }, { ...session, currentUser: null }, { ...session, currentUser: { role: "operator" } }]) {
    mocks.session.mockReturnValue(value); const view = render(<AdminPage />);
    expect(screen.getByText(/Verifica accesso|non autorizzata/)).toBeInTheDocument(); view.unmount();
  }
  expect(mocks.api).not.toHaveBeenCalled();
});
it("creates, edits and versions accounts, configures TLS/auth/routing and queues tests without secrets", async () => {
  render(<AccountAdministration token="token" />);
  await screen.findByText("Modifica");
  fireEvent.click(screen.getByText("Nuovo account", { selector: "summary" }));
  for (const [label, value] of [["Nome account", "Casella"], ["Provider", "Alternative"], ["Indirizzo mittente", "office@example.org"], ["Nome visualizzato", "Office"], ["Host SMTP verificato", "smtp.example.org"], ["Host IMAP verificato", "imap.example.org"], ["Username", "office"], ["Riferimento secret esterno", "external-file"], ["Porta SMTP", "587"], ["Porta IMAP", "143"], ["Priorità", "10"], ["Limite MIME in byte", "10000"], ["Invii massimi per ora", "10"], ["Canale", "email"], ["smtp_encryption", "starttls"], ["imap_encryption", "starttls"], ["Autenticazione", "oauth2"], ["ID utenti autorizzati (vuoto: tutti i gestori Tributi)", "1,2"]]) fireEvent.change(screen.getByLabelText(label), { target: { value } });
  fireEvent.change(screen.getByLabelText(/ID utenti/), { target: { value: "" } });
  for (const label of ["Account abilitato", "Invii in pausa", "Predefinito generale del canale", "Predefinito Ruolo per questo canale"]) fireEvent.click(screen.getByLabelText(label));
  fireEvent.click(screen.getByLabelText("Predefinito Ruolo per questo canale"));
  fireEvent.click(screen.getByText("Salva configurazione"));
  await screen.findByText(/Configurazione salvata/);
  const payload = mocks.api.mock.calls.find((call) => call[1] === "/accounts")?.[2];
  expect(payload).toMatchObject({ channel: "email", auth_method: "oauth2", secret_ref: "external-file", allowed_user_ids: [], default_modules: [] });
  expect(payload).not.toHaveProperty("password");
  fireEvent.click(screen.getByText("Modifica"));
  expect(screen.getByLabelText("Nome account")).toHaveValue("Synthetic");
  fireEvent.click(screen.getByText("Salva configurazione"));
  await waitFor(() => expect(mocks.api.mock.calls.some((call) => call[1] === "/accounts/account" && call[3] === "PATCH" && call[2].expected_version === 1)).toBe(true));
  await screen.findByText(/Configurazione salvata/);
  fireEvent.click(screen.getByText("Nuovo account", { selector: "button" }));
  for (const label of ["Test SMTP e IMAP", "Acquisisci ricevute", "Riprendi account"]) {
    fireEvent.click(screen.getByText(label)); await waitFor(() => expect(screen.getByText(label)).toBeEnabled());
  }
  expect(mocks.api.mock.calls.some((call) => call[1].endsWith("pause") && call[2].paused === false)).toBe(true);
});
it("shows enabled/live account metadata and pausing, and reports all account command failures", async () => {
  mocks.api.mockResolvedValue([{ ...stored, active: true, paused: false, last_test_at: "today", last_sync_at: "today" }]);
  render(<AccountAdministration token="token" />);
  await screen.findByText("Pausa account");
  fireEvent.click(screen.getByText("Nuovo account", { selector: "summary" }));
  for (const failure of [new Error("denied"), "error"]) {
    mocks.api.mockRejectedValue(failure);
    fireEvent.click(screen.getByText("Pausa account"));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(failure instanceof Error ? "denied" : "Operazione fallita"));
    fireEvent.click(screen.getByText("Salva configurazione"));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(failure instanceof Error ? "denied" : "Salvataggio fallito"));
  }
});
it("keeps account creation collapsed, preserves draft input on toggle, and opens existing accounts for editing", async () => {
  render(<AccountAdministration token="token" />);
  const edit = await screen.findByRole("button", { name: "Modifica" });
  const toggle = screen.getByText("Nuovo account", { selector: "summary" });
  const name = screen.getByLabelText("Nome account");
  expect(name).not.toBeVisible();
  expect(edit).toBeVisible();
  fireEvent.click(toggle);
  expect(name).toBeVisible();
  fireEvent.change(name, { target: { value: "Bozza account" } });
  fireEvent.click(toggle);
  expect(name).not.toBeVisible();
  fireEvent.click(toggle);
  expect(name).toBeVisible();
  expect(name).toHaveValue("Bozza account");
  fireEvent.click(toggle);
  fireEvent.click(edit);
  expect(screen.getByText("Modifica account", { selector: "summary" })).toBeVisible();
  expect(name).toBeVisible();
  expect(name).toHaveValue("Synthetic");
  expect(mocks.api).toHaveBeenCalledTimes(1);
});
it("creates a fresh version and approves only draft templates", async () => {
  render(<TemplateAdministration token="token" />);
  fireEvent.click(await screen.findByText("Modifica template"));
  for (const [label, value] of [["Codice template", "new-code"], ["Nome template", "New name"], ["Oggetto template", "New subject"], ["Canale template", "email"], ["Corpo template", "New body"]]) fireEvent.change(screen.getByLabelText(label), { target: { value } });
  fireEvent.click(screen.getByText("Salva nuova versione bozza"));
  await waitFor(() => expect(screen.getByText("Salva nuova versione bozza")).toBeEnabled());
  expect(mocks.api.mock.calls.find((call) => call[1] === "/templates")?.[2]).toMatchObject({ code: "new-code", channel: "email", body: "New body" });
  fireEvent.click(screen.getByText("Approva questa versione"));
  await waitFor(() => expect(mocks.api.mock.calls.some((call) => call[1] === "/templates/template/approve")).toBe(true));
  await waitFor(() => expect(screen.getByText("Approva questa versione")).toBeEnabled());
  for (const failure of [new Error("invalid"), "error"]) {
    mocks.api.mockRejectedValue(failure); fireEvent.click(screen.getByText("Salva nuova versione bozza"));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(failure instanceof Error ? "invalid" : "Operazione fallita"));
  }
});
it("opens an approved saved template in the editor and saves changes as a separate draft", async () => {
  const saved = { ...template, status: "approved" };
  mocks.api.mockResolvedValue([saved]);
  render(<TemplateAdministration token="token" />);
  fireEvent.click(await screen.findByRole("button", { name: `Modifica template ${saved.name}, ${saved.channel}, versione ${saved.version}` }));
  expect(screen.getByRole("heading", { name: `Editor template: ${saved.name}` })).toHaveFocus();
  expect(screen.getByLabelText("Codice template")).toHaveValue(saved.code);
  expect(screen.getByLabelText("Corpo template")).toHaveValue(saved.body);
  expect(mocks.api).toHaveBeenCalledTimes(1);
  fireEvent.change(screen.getByLabelText("Oggetto template"), { target: { value: "Oggetto aggiornato" } });
  fireEvent.change(screen.getByLabelText("Corpo template"), { target: { value: "Testo aggiornato" } });
  fireEvent.click(screen.getByText("Salva nuova versione bozza"));
  await waitFor(() => expect(mocks.api).toHaveBeenCalledWith("token", "/templates", {
    code: saved.code, name: saved.name, channel: saved.channel, module: "ruolo", subject: "Oggetto aggiornato", body: "Testo aggiornato",
  }));
  await waitFor(() => expect(screen.getByLabelText("Codice template")).toHaveValue(""));
  expect(saved.body).toBe(template.body);
  expect(saved.status).toBe("approved");
  expect(mocks.api.mock.calls.filter(call => call[2] !== undefined)).toHaveLength(1);
});
it("edits a saved clickable link with live preview and cancels without changing the saved template", async () => {
  const body = 'GAIA-BLOCKS/1\n[{"kind":"link","text":"Portale","url":"https://example.org/original"}]';
  mocks.api.mockResolvedValue([{ ...template, body, status: "draft" }]);
  render(<TemplateAdministration token="token" />);
  fireEvent.click(await screen.findByText("Modifica template"));
  expect(screen.getByLabelText("URL blocco 1")).toHaveValue("https://example.org/original");
  fireEvent.change(screen.getByLabelText("URL blocco 1"), { target: { value: "https://example.org/updated" } });
  expect(screen.getAllByRole("link", { name: "Portale" }).map(link => link.getAttribute("href"))).toEqual([
    "https://example.org/original", "https://example.org/updated",
  ]);
  fireEvent.click(screen.getByText("Annulla modifiche"));
  expect(screen.getByLabelText("Codice template")).toHaveValue("");
  expect(screen.getByLabelText("Corpo template")).toHaveValue("");
  expect(screen.getByRole("heading", { name: "Editor template: nuovo modello" })).toBeVisible();
  fireEvent.click(screen.getByText("Modifica template"));
  expect(screen.getByLabelText("URL blocco 1")).toHaveValue("https://example.org/original");
  expect(mocks.api).toHaveBeenCalledTimes(1);
});
it.each(["draft", "approved"])("asks confirmation before deleting a %s template and permits cancelling", async (status) => {
  mocks.api.mockResolvedValue([{ ...template, status }]);
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  render(<TemplateAdministration token="token" />);
  fireEvent.click(await screen.findByRole("button", { name: "Elimina Template sintetico, pec, versione 1" }));
  expect(confirm).toHaveBeenCalledOnce();
  expect(confirm).toHaveBeenCalledWith(expect.stringContaining("«Template sintetico» (PEC, codice synthetic, versione 1)"));
  expect(confirm).toHaveBeenCalledWith(expect.stringContaining("I messaggi già creati e lo storico resteranno conservati"));
  expect(mocks.api).toHaveBeenCalledTimes(1);
  expect(screen.getByText("Modifica template")).toBeEnabled();
});
it("deletes only the confirmed version, disables actions during deletion, and reloads the list", async () => {
  vi.spyOn(window, "confirm").mockReturnValue(true);
  const second = { ...template, id: "second", version: 2, status: "draft" };
  let remaining = [template, second];
  let resolveDelete!: (value: unknown) => void;
  mocks.api.mockImplementation((_token, path, _data, method) => {
    if (method === "DELETE") return new Promise((resolve) => { resolveDelete = resolve; });
    return Promise.resolve(remaining);
  });
  render(<TemplateAdministration token="token" />);
  fireEvent.click(await screen.findByRole("button", { name: "Elimina Template sintetico, pec, versione 1" }));
  expect(mocks.api).toHaveBeenCalledWith("token", "/templates/template", { confirmed: true }, "DELETE");
  for (const button of screen.getAllByRole("button")) expect(button).toBeDisabled();
  expect(screen.getByLabelText("Codice template")).toBeDisabled();
  remaining = [second];
  await act(async () => { resolveDelete({ ...template, status: "deleted" }); });
  await waitFor(() => expect(screen.queryByRole("button", { name: "Elimina Template sintetico, pec, versione 1" })).not.toBeInTheDocument());
  expect(screen.getByRole("button", { name: "Elimina Template sintetico, pec, versione 2" })).toBeEnabled();
  expect(mocks.api.mock.calls.filter((call) => call[1] === "/admin/templates")).toHaveLength(2);
});
it.each([new Error("Eliminazione non autorizzata"), "failure"])("keeps the template and reports a failed deletion: %s", async (failure) => {
  vi.spyOn(window, "confirm").mockReturnValue(true);
  render(<TemplateAdministration token="token" />);
  const button = await screen.findByRole("button", { name: "Elimina Template sintetico, pec, versione 1" });
  mocks.api.mockRejectedValueOnce(failure);
  fireEvent.click(button);
  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(failure instanceof Error ? failure.message : "Eliminazione fallita"));
  expect(button).toBeEnabled();
  expect(mocks.api.mock.calls.filter((call) => call[3] === "DELETE")).toHaveLength(1);
});
it("reports a failed reload after deletion and allows an idempotent retry", async () => {
  vi.spyOn(window, "confirm").mockReturnValue(true);
  render(<TemplateAdministration token="token" />);
  const button = await screen.findByRole("button", { name: "Elimina Template sintetico, pec, versione 1" });
  mocks.api.mockResolvedValueOnce({}).mockRejectedValueOnce(new Error("Elenco non disponibile"));
  fireEvent.click(button);
  await screen.findByText("Elenco non disponibile");
  expect(button).toBeEnabled();
  mocks.api.mockResolvedValueOnce({}).mockResolvedValueOnce([]);
  fireEvent.click(button);
  await waitFor(() => expect(screen.queryByText("Modifica template")).not.toBeInTheDocument());
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});
it("reports initial account and template load errors without hiding them", async () => {
  mocks.api.mockRejectedValue(new Error("offline"));
  render(<><AccountAdministration token="token" /><TemplateAdministration token="token" /></>);
  await waitFor(() => expect(screen.getAllByRole("alert")).toHaveLength(2));
});
it("distinguishes worker liveness, transport enablement and provider state; pause failures stay visible", async () => {
  const view = render(<AdminPage />);
  fireEvent.click(await screen.findByText("Riprendi coda invii"));
  await waitFor(() => expect(mocks.api.mock.calls.some((call) => call[1] === "/admin/pause" && call[2].paused === false)).toBe(true));
  mocks.api.mockImplementation((_token, path) => Promise.resolve(path === "/admin/monitor" ? { paused: false, transport_enabled: true, worker_seen_at: "today", queues: { done: 4 }, uncertain: 0, unmatched_receipts: 0 } : []));
  fireEvent.click(screen.getByText("Aggiorna monitoraggio"));
  await screen.findByText("Pausa globale invii");
  for (const failure of [new Error("offline"), "error"]) {
    mocks.api.mockRejectedValue(failure); fireEvent.click(screen.getByText("Pausa globale invii"));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(failure instanceof Error ? "offline" : "Pausa fallita"));
    fireEvent.click(screen.getByText("Aggiorna monitoraggio"));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(failure instanceof Error ? "offline" : "Monitoraggio non disponibile"));
  }
  view.unmount();
  mocks.api.mockImplementation((_token, path) => Promise.resolve(path === "/admin/monitor" ? { paused: true, transport_enabled: false, worker_seen_at: null, queues: {}, uncertain: 0, unmatched_receipts: 0 } : []));
  vi.useFakeTimers();
  const timed = render(<AdminPage />);
  await act(async () => { vi.advanceTimersByTime(10000); });
  timed.unmount();
});
