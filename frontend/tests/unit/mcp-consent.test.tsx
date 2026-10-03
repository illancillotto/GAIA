import { act, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import MCPConsentPage, { metadata } from "@/app/mcp/consent/page";
import { MCPConsent, useMCPConsent } from "@/features/wiki/mcp-consent";
import { returnToMCPClient } from "@/features/wiki/mcp-consent-api";
import { ApiError } from "@/lib/api/core";

const mocks = vi.hoisted(() => ({
  request: vi.fn(), login: vi.fn(), stored: vi.fn(), save: vi.fn(), clear: vi.fn(),
  query: "synthetic-request-id-abcdefghijklmnopqrstuvwxyz", assign: vi.fn(),
}));
vi.mock("next/navigation", () => ({ useSearchParams: () => new URLSearchParams(mocks.query ? { request_id: mocks.query } : {}) }));
vi.mock("@/lib/api/core", async () => ({ ...await vi.importActual("@/lib/api/core"), request: mocks.request }));
vi.mock("@/lib/api/platform", () => ({ login: mocks.login }));
vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.stored, setStoredAccessToken: mocks.save, clearStoredAccessToken: mocks.clear,
  getStoredClientDeviceId: () => "synthetic-device", getClientDeviceLabel: () => "synthetic-platform",
}));

const details = { client_name: "Synthetic connector", resource: "https://synthetic.example/mcp",
  redirect_uri: "https://approved.example/callback", scopes: ["utenze.read", "catasto.read", "ruolo.read", "unknown.read"] };

beforeEach(() => {
  vi.clearAllMocks();
  vi.stubGlobal("location", { assign: mocks.assign });
  delete process.env.NEXT_PUBLIC_GAIA_MCP_CONNECTOR_ENABLED;
  mocks.query = "synthetic-request-id-abcdefghijklmnopqrstuvwxyz";
  mocks.stored.mockReturnValue(null);
  mocks.login.mockResolvedValue({ access_token: "gaia-session" });
  mocks.request.mockResolvedValue(details);
});

test("default page is disabled without credentials or connector requests", () => {
  render(<MCPConsentPage />);
  expect(screen.getByText("Connettore MCP non attivo")).toBeInTheDocument();
  expect(mocks.request).not.toHaveBeenCalled();
  expect(mocks.stored).not.toHaveBeenCalled();
  expect(metadata.referrer).toBe("no-referrer");
});

test.each(["", "bad", "x".repeat(129), "<script>" + "x".repeat(40)])("invalid request %s never authenticates or loads", query => {
  mocks.query = query;
  render(<MCPConsent enabled />);
  expect(screen.getByText("Richiesta di consenso non valida")).toBeInTheDocument();
  expect(mocks.request).not.toHaveBeenCalled();
});

test("existing GAIA session shows scopes but never approves automatically", async () => {
  process.env.NEXT_PUBLIC_GAIA_MCP_CONNECTOR_ENABLED = "true";
  mocks.stored.mockReturnValue("gaia-session");
  render(<MCPConsentPage />);
  expect(await screen.findByText("Synthetic connector")).toBeInTheDocument();
  expect(screen.getByText("unknown.read")).toBeInTheDocument();
  expect(screen.queryByLabelText("Password GAIA")).toBeNull();
  expect(mocks.request).toHaveBeenCalledTimes(1);
  expect(mocks.request).toHaveBeenCalledWith(expect.stringContaining("/wiki/mcp/connector/oauth/consent?request_id="), {
    headers: { Authorization: "Bearer gaia-session" },
  });
  expect(mocks.assign).not.toHaveBeenCalled();
});

test.each([true, false])("explicit decision %s returns only to registered callback", async allowed => {
  mocks.stored.mockReturnValue("gaia-session");
  render(<MCPConsent enabled />);
  await screen.findByText("Synthetic connector");
  const redirect = `https://approved.example/callback?${allowed ? "code=synthetic-code" : "error=access_denied"}&state=synthetic-state`;
  mocks.request.mockResolvedValueOnce({ redirect_url: redirect });
  fireEvent.click(screen.getByRole("button", { name: allowed ? "Autorizza" : "Rifiuta" }));
  expect(screen.getByRole("button", { name: "Autorizza" })).toBeDisabled();
  await waitFor(() => expect(mocks.assign).toHaveBeenCalledWith(redirect));
  expect(mocks.request).toHaveBeenLastCalledWith("/wiki/mcp/connector/oauth/consent", {
    method: "POST", headers: { Authorization: "Bearer gaia-session" },
    body: JSON.stringify({ request_id: mocks.query, allowed }),
  });
});

test("inline login reuses GAIA device-aware login and clears password", async () => {
  render(<MCPConsent enabled />);
  expect(screen.getByRole("button", { name: "Accedi a GAIA" }).closest("form")).toHaveAttribute("method", "post");
  fireEvent.change(screen.getByLabelText("Username GAIA"), { target: { value: "synthetic-user" } });
  fireEvent.change(screen.getByLabelText("Password GAIA"), { target: { value: "synthetic-password" } });
  fireEvent.submit(screen.getByRole("button", { name: "Accedi a GAIA" }).closest("form")!);
  await screen.findByText("Synthetic connector");
  expect(mocks.login).toHaveBeenCalledWith("synthetic-user", "synthetic-password", { deviceId: "synthetic-device", deviceLabel: "synthetic-platform" });
  expect(mocks.save).toHaveBeenCalledWith("gaia-session");
  expect(JSON.stringify(mocks.request.mock.calls)).not.toContain("synthetic-password");
  expect(mocks.assign).not.toHaveBeenCalled();
});

test("failed login hides private details and resets credentials", async () => {
  mocks.login.mockRejectedValueOnce(new Error("private password detail"));
  render(<MCPConsent enabled />);
  fireEvent.change(screen.getByLabelText("Password GAIA"), { target: { value: "synthetic-password" } });
  fireEvent.submit(screen.getByRole("button", { name: "Accedi a GAIA" }).closest("form")!);
  await screen.findByRole("alert");
  expect(screen.getByLabelText("Password GAIA")).toHaveValue("");
  expect(screen.queryByText("private password detail")).toBeNull();
  expect(mocks.save).not.toHaveBeenCalled();
  expect(mocks.request).not.toHaveBeenCalled();
});

test.each([new ApiError("expired", undefined, 401), new Error("private backend detail")])("load failure does not disclose data or autoapprove", async failure => {
  mocks.stored.mockReturnValue("gaia-session");
  mocks.request.mockRejectedValueOnce(failure);
  render(<MCPConsent enabled />);
  await screen.findByRole("alert");
  expect(screen.queryByText("Synthetic connector")).toBeNull();
  expect(screen.queryByRole("button", { name: "Autorizza" })).toBeNull();
  expect(mocks.clear).toHaveBeenCalledTimes(failure instanceof ApiError ? 1 : 0);
});

test.each([new Error("private response"), { redirect_url: "https://attacker.example/callback?code=x" }])("failed decision cannot redirect or expose private information", async failure => {
  mocks.stored.mockReturnValue("gaia-session");
  render(<MCPConsent enabled />);
  await screen.findByText("Synthetic connector");
  if (failure instanceof Error) mocks.request.mockRejectedValueOnce(failure);
  else mocks.request.mockResolvedValueOnce(failure);
  fireEvent.click(screen.getByRole("button", { name: "Autorizza" }));
  await screen.findByRole("alert");
  expect(screen.getByRole("button", { name: "Autorizza" })).not.toBeDisabled();
  expect(mocks.assign).not.toHaveBeenCalled();
  expect(screen.queryByText("private response")).toBeNull();
});

test("query change remounts consent, never mixing connector details", async () => {
  mocks.stored.mockReturnValue("gaia-session");
  const view = render(<MCPConsent enabled />);
  await screen.findByText("Synthetic connector");
  mocks.query = "new-request-id-abcdefghijklmnopqrstuvwxyz";
  mocks.request.mockResolvedValueOnce({ ...details, client_name: "Another approved connector" });
  view.rerender(<MCPConsent enabled />);
  await screen.findByText("Another approved connector");
  expect(screen.queryByText("Synthetic connector")).toBeNull();
  expect(mocks.assign).not.toHaveBeenCalled();
});

test("inactive hook cannot submit without a session and consent details", async () => {
  mocks.stored.mockReturnValue("gaia-session");
  const hook = renderHook(() => useMCPConsent(mocks.query, false));
  await act(() => hook.result.current.decide(true));
  expect(mocks.request).not.toHaveBeenCalled();
});

test.each([
  "http://approved.example/callback", "https://other.example/callback", "https://approved.example/wrong",
  "https://user@approved.example/callback", "https://:secret@approved.example/callback",
  "https://approved.example/callback#fragment", "invalid-url",
])("unregistered or unsafe callback %s is rejected", target => {
  expect(() => returnToMCPClient(target, details.redirect_uri)).toThrow();
  expect(mocks.assign).not.toHaveBeenCalled();
});
