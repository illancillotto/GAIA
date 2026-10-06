import { beforeEach, expect, test, vi } from "vitest";

import { controlCommand, parcelControlRequest } from "@/lib/parcel-control-api";

vi.mock("@/lib/api", () => ({ getApiBaseUrl: () => "http://api.test" }));
const fetchMock = vi.fn();
beforeEach(() => { fetchMock.mockReset(); vi.stubGlobal("fetch", fetchMock); });

test("authenticated reads and idempotent versioned commands", async () => {
  fetchMock.mockResolvedValue({ ok: true, json: async () => ({ total: 1 }) });
  expect(await parcelControlRequest("token", "?view=all")).toEqual({ total: 1 });
  expect(fetchMock).toHaveBeenCalledWith("http://api.test/ruolo/particelle/controllo?view=all", expect.objectContaining({ method: "GET" }));
  const command = controlCommand("Verifica", {});
  expect(command.expected_version).toBe(1);
  expect(command.command_id).toMatch(/^[0-9a-f-]{36}$/);
  const changed = controlCommand("Modifica", { status: "open" }, 2);
  await parcelControlRequest("token", "/pratiche/case-1/status", changed);
  expect(fetchMock).toHaveBeenLastCalledWith(expect.any(String), expect.objectContaining({ method: "POST", body: JSON.stringify(changed) }));
});

test.each([
  [async () => ({ detail: "Conflitto concorrente" }), "Conflitto concorrente"],
  [async () => ({ detail: [] }), "Richiesta non valida"],
  [async () => { throw new Error("bad response"); }, "Errore di comunicazione"],
])("reports server and communication errors", async (json, message) => {
  fetchMock.mockResolvedValue({ ok: false, json });
  await expect(parcelControlRequest("token", "")).rejects.toThrow(message);
});
