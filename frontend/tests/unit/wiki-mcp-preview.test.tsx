import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, expect, test, vi } from "vitest";

import WikiMCPPreview from "@/app/wiki/mcp/page";

const mocks = vi.hoisted(() => ({ request: vi.fn(), token: vi.fn() }));
vi.mock("@/lib/api/core", () => ({ request: mocks.request }));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));
vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children }: { children: ReactNode }) => <main>{children}</main>,
}));

beforeEach(() => {
  vi.clearAllMocks();
  mocks.token.mockReturnValue("synthetic-session-token");
  mocks.request.mockResolvedValue({ answer: "Solo dati sintetici", found: true, tool_calls: 1, evidence_tokens: 250,
    provenance: [{ source: "gaia_synthetic_db", entity: "subjects", record_id: "synthetic-uuid", dataset_version: "v1" }] });
});

test("preset-only authenticated request and provenance, no legacy endpoint", async () => {
  render(<WikiMCPPreview />);
  expect(screen.queryByRole("textbox")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Interroga Data MCP" }));
  expect(screen.getByRole("button", { name: "Ricerca in corso…" })).toBeDisabled();
  await screen.findByText("Solo dati sintetici");
  expect(screen.getByText(/gaia_synthetic_db \/ subjects \/ synthetic-uuid/)).toBeInTheDocument();
  expect(screen.getByText(/Evidenze trovate/)).toBeInTheDocument();
  expect(mocks.request).toHaveBeenCalledWith("/wiki/mcp/chat", expect.objectContaining({
    headers: { Authorization: "Bearer synthetic-session-token" },
    body: JSON.stringify({ question: "Cerca il soggetto sintetico con identificativo SYN-SUBJECT-0001." }),
  }));
});

test("absence preset and result reset on provider failure", async () => {
  mocks.request.mockResolvedValueOnce({ answer: "Assente", found: false, provenance: [], tool_calls: 1, evidence_tokens: 100 });
  render(<WikiMCPPreview />);
  fireEvent.change(screen.getByLabelText("Domanda sintetica"), { target: { value: "Cerca il soggetto sintetico con identificativo SYN-NOT-EXISTENT." } });
  fireEvent.click(screen.getByRole("button"));
  await screen.findByText("Assente");
  expect(screen.getByText(/Nessuna evidenza/)).toBeInTheDocument();
  mocks.request.mockRejectedValueOnce(new Error("private provider detail"));
  fireEvent.click(screen.getByRole("button"));
  await screen.findByRole("alert");
  expect(screen.queryByText("Assente")).toBeNull();
  expect(screen.queryByText("private provider detail")).toBeNull();
  await waitFor(() => expect(screen.getByRole("button")).not.toBeDisabled());
});

test("missing session prevents any request", async () => {
  mocks.token.mockReturnValue(null);
  render(<WikiMCPPreview />);
  fireEvent.click(screen.getByRole("button"));
  expect(await screen.findByRole("alert")).toHaveTextContent("Sessione assente");
  expect(mocks.request).not.toHaveBeenCalled();
});
