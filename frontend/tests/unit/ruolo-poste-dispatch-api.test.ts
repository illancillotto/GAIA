import { afterEach, beforeEach, expect, test, vi } from "vitest";

import {
  acceptPosteManualAddress,
  cancelPosteItem,
  createPosteLot,
  getPosteItemDocument,
  getPosteLot,
  listPosteCandidates,
  listPosteLots,
  requestPosteJob,
  updatePosteRecipient,
} from "@/lib/ruolo-poste-dispatch-api";

const fetchMock = vi.fn();
const BASE = "/ruolo/tributi/poste-dispatch";
const recipient = { name: "ROSSI MARIO", name_extra: "", address: "VIA ROMA 1", cap: "09170", city: "ORISTANO", province: "OR" };

beforeEach(() => {
  fetchMock.mockReset();
  fetchMock.mockImplementation(async () => new Response(JSON.stringify({ ok: true }), { status: 200, headers: { "content-type": "application/json" } }));
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => vi.unstubAllGlobals());

function call(index = 0): [string, RequestInit] {
  return fetchMock.mock.calls[index] as [string, RequestInit];
}

test("reads candidates, lots and a lot with the bearer token", async () => {
  await listPosteCandidates("t", "  rossi ");
  await listPosteCandidates("t", " ");
  await listPosteLots("t");
  await getPosteLot("t", "lot-1");
  expect(call(0)[0]).toContain(`${BASE}/candidates?page=1&page_size=50&q=rossi`);
  expect(call(1)[0]).toMatch(/candidates\?page=1&page_size=50$/);
  expect(call(2)[0]).toContain(`${BASE}/lots?page=1&page_size=50`);
  expect(call(3)[0]).toContain(`${BASE}/lots/lot-1`);
  expect(call(3)[1].headers).toMatchObject({ Authorization: "Bearer t" });
});

test("sends the operator commands", async () => {
  await createPosteLot("t", "Lotto", ["a", "b"]);
  await requestPosteJob("t", "lot-1", "drafts");
  await updatePosteRecipient("t", "lot-1", "item-1", recipient);
  await acceptPosteManualAddress("t", "lot-1", "item-1");
  await cancelPosteItem("t", "lot-1", "item-1");
  expect(JSON.parse(call(0)[1].body as string)).toEqual({ title: "Lotto", batch_item_ids: ["a", "b"] });
  expect(JSON.parse(call(1)[1].body as string)).toEqual({ kind: "drafts" });
  expect(call(2)[1].method).toBe("PUT");
  expect(call(3)[0]).toContain("/items/item-1/manual-address");
  expect(call(4)[0]).toContain("/items/item-1/cancel");
});

test("downloads the PDF snapshot as a blob", async () => {
  fetchMock.mockResolvedValueOnce(new Response(new Blob(["%PDF"]), { status: 200 }));
  const blob = await getPosteItemDocument("t", "lot-1", "item-1");
  expect(await blob.text()).toBe("%PDF");
  expect(call(0)[0]).toContain("/lots/lot-1/items/item-1/document");
});
