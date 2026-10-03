import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, expect, test, vi } from "vitest";

import MCPConsolePage from "@/app/wiki/mcp/console/page";

const mocks = vi.hoisted(() => ({ request: vi.fn(), token: vi.fn() }));
vi.mock("@/lib/api/core", () => ({ request: mocks.request }));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));
vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children }: { children: ReactNode }) => <main>{children}</main>,
}));

const catalog = { dataset_version: "synthetic-v1", entities: [{ name: "subjects", count: 300 }], audit_enabled: true };
const history = { results: [{ id: 1, event: { timestamp: "today", tool_name: "search_subjects", status: "ok", duration_ms: 2, principal: "hash" }, filters: { query: "[omesso]" }, response: { source: "gaia_synthetic_db", provenance: [{ record_id: "synthetic-uuid" }] } }], next_before: 1, retention_limit: 1000, visibility: "own" };

beforeEach(() => {
  vi.clearAllMocks();
  mocks.token.mockReturnValue("synthetic-session");
  mocks.request.mockImplementation(async (path: string) => {
    if (path.endsWith("catalog")) return catalog;
    if (path.includes("calls")) return history;
    return { results: [{ id: "synthetic-uuid", display_name: "Soggetto sintetico" }], total: 300, next_offset: 25 };
  });
});

test("authenticated dataset, history and record pagination without model calls", async () => {
  render(<MCPConsolePage />);
  expect(screen.getByRole("link", { name: "Apri agente sintetico" })).toHaveAttribute("href", "/wiki/mcp");
  fireEvent.click(screen.getByRole("button", { name: "Carica dati e richieste" }));
  expect(screen.getByRole("button", { name: "Caricamento…" })).toBeDisabled();
  await screen.findByText(/Le tue chiamate/);
  expect(screen.getByText(/synthetic-uuid/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "subjects (300)" }));
  await screen.findByRole("region", { name: "Dati sintetici" });
  fireEvent.click(screen.getByRole("button", { name: "Record successivi" }));
  await waitFor(() => expect(mocks.request).toHaveBeenCalledWith("/wiki/mcp/console/subjects?offset=25", expect.anything()));
  await waitFor(() => expect(screen.getByRole("button", { name: "Aggiorna richieste" })).not.toBeDisabled());
  fireEvent.click(screen.getByRole("button", { name: "Richieste precedenti" }));
  await waitFor(() => expect(mocks.request).toHaveBeenCalledWith("/wiki/mcp/console/calls?before=1", expect.anything()));
  await waitFor(() => expect(screen.getByRole("button", { name: "Aggiorna richieste" })).not.toBeDisabled());
  fireEvent.click(screen.getByRole("button", { name: "Aggiorna richieste" }));
  await waitFor(() => expect(mocks.request).toHaveBeenCalledWith("/wiki/mcp/console/calls?before=0", expect.anything()));
  expect(mocks.request.mock.calls.every(([path, options]) => path.startsWith("/wiki/mcp/console/") && options.headers.Authorization === "Bearer synthetic-session")).toBe(true);
});

test("empty catalog and disabled audit do not request calls", async () => {
  mocks.request.mockResolvedValue({ dataset_version: "v1", entities: [], audit_enabled: false });
  render(<MCPConsolePage />);
  fireEvent.click(screen.getByRole("button", { name: "Carica dati e richieste" }));
  await screen.findByText("Nessuna entità autorizzata.");
  expect(screen.getByText("Storico non configurato sul server MCP.")).toBeInTheDocument();
  expect(mocks.request).toHaveBeenCalledTimes(1);
});

test("admin history and final empty record page", async () => {
  mocks.request.mockImplementation(async (path: string) => {
    if (path.endsWith("catalog")) return catalog;
    if (path.includes("calls")) return { ...history, visibility: "all_authorized", results: [], next_before: null };
    return { results: [], total: 0, next_offset: null };
  });
  render(<MCPConsolePage />);
  fireEvent.click(screen.getByRole("button", { name: "Carica dati e richieste" }));
  await screen.findByText("Nessuna chiamata registrata.");
  expect(screen.getByText(/Chiamate nei domini autorizzati/)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Richieste precedenti" })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "subjects (300)" }));
  await screen.findByRole("region", { name: "Dati sintetici" });
  expect(screen.queryByRole("button", { name: "Record successivi" })).toBeNull();
});

test("missing session and failures hide stale results and private details", async () => {
  mocks.token.mockReturnValue(null);
  render(<MCPConsolePage />);
  fireEvent.click(screen.getByRole("button", { name: "Carica dati e richieste" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Sessione assente");
  expect(mocks.request).not.toHaveBeenCalled();
  mocks.token.mockReturnValue("synthetic-session");
  fireEvent.click(screen.getByRole("button", { name: "Carica dati e richieste" }));
  await screen.findByText(/Le tue chiamate/);
  mocks.request.mockRejectedValueOnce(new Error("private-provider-key"));
  fireEvent.click(screen.getByRole("button", { name: "subjects (300)" }));
  await screen.findByRole("alert");
  expect(screen.queryByRole("region", { name: "Storico chiamate" })).toBeNull();
  expect(screen.queryByText("private-provider-key")).toBeNull();
  expect(screen.getByRole("button", { name: "Carica dati e richieste" })).not.toBeDisabled();
});
