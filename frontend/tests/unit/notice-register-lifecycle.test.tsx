import { act, cleanup, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api/core";
import { registerError } from "@/components/ruolo/notice-register/client";
import { RecordForm } from "@/components/ruolo/notice-register/mutation-form";
import { RegisterTimeline } from "@/components/ruolo/notice-register/timeline";
import { useRegisterResource } from "@/components/ruolo/notice-register/use-register-resource";
import { evidenceFixture, jsonResponse } from "./notice-register-fixtures";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it("ignores both late successes and late failures after a request is replaced", async () => {
  const first = deferred<Response>(); const second = deferred<Response>();
  const fetchMock = vi.fn().mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise).mockResolvedValue(jsonResponse({ id: "current" }));
  vi.stubGlobal("fetch", fetchMock);
  const { result, rerender, unmount } = renderHook(({ path }) => useRegisterResource<{ id: string }>("token", path), { initialProps: { path: "/first" } });
  expect(result.current.loading).toBe(true);
  rerender({ path: "/second" });
  expect(fetchMock.mock.calls[0][1].signal.aborted).toBe(true);
  await act(async () => first.resolve(jsonResponse({ id: "stale" })));
  expect(result.current.data).toBeUndefined();
  rerender({ path: "/third" });
  await waitFor(() => expect(result.current.data).toEqual({ id: "current" }));
  await act(async () => second.reject(new Error("late network failure")));
  expect(result.current.error).toBeUndefined();
  expect(result.current.data).toEqual({ id: "current" });
  unmount();
  expect(fetchMock.mock.calls[2][1].signal.aborted).toBe(true);
});

it("does not duplicate a pending write and preserves the expected version", async () => {
  const pending = deferred<Response>(); const saved = vi.fn();
  const fetchMock = vi.fn().mockReturnValue(pending.promise);
  vi.stubGlobal("fetch", fetchMock);
  render(<RecordForm token="secret-token" version={7} onSaved={saved} path="/doc-1" method="PUT" title="Modify" kind="document" initial={{ document_number: "DOC" }} />);
  const form = screen.getByRole("form", { name: "Modify" });
  fireEvent.change(screen.getByLabelText("Motivo della registrazione o correzione"), { target: { value: "  Verifica  " } });
  fireEvent.submit(form); fireEvent.submit(form);
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(screen.getByRole("button", { name: "Salvataggio..." })).toBeDisabled();
  expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe("Bearer secret-token");
  expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ expected_version: 7, reason: "Verifica", data: { document_number: "DOC", tax_code: null, issued_on: null } });
  await act(async () => pending.resolve(jsonResponse({ document_id: "doc-1", resource_id: "doc-1", version: 8 })));
  expect(saved).toHaveBeenCalledWith({ document_id: "doc-1", resource_id: "doc-1", version: 8 });
});

it("reports unknown failures and retains entered values", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue("network"));
  render(<RecordForm token="token" version={1} onSaved={vi.fn()} path="" method="POST" title="Create" kind="document" initial={{ document_number: "ORIGINAL" }} />);
  fireEvent.submit(screen.getByRole("form", { name: "Create" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Operazione non riuscita. Riprova.");
  expect(screen.getByLabelText("Numero documento")).toHaveValue("ORIGINAL");
  expect(registerError(new ApiError("Forbidden", undefined, 403))).toBe("Forbidden");
});

it("shows undated evidence and attempts with known dates and tracking", async () => {
  vi.stubGlobal("fetch", vi.fn(async (path: string) => jsonResponse({
    items: path.includes("/invii") ? [{ id: "a", channel: "Posta", tracking_code: "TRACK-123", sent_at: "2024-06-29", source_system: "poste" }]
      : [{ ...evidenceFixture, occurred_on: null }], total: 1, page: 1, page_size: 10,
  })));
  render(<RegisterTimeline token="token" documentId="doc-1" />);
  expect(await screen.findByText("Ricevuta | Data assente | manual")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "invii" }));
  expect(await screen.findByText("Posta | TRACK-123")).toBeVisible();
  expect(screen.getByText("2024-06-29 | poste")).toBeVisible();
});
