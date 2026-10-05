import { beforeEach, expect, test, vi } from "vitest";

import { downloadRegisteredMailCard, listRegisteredMailCards, uploadRegisteredMailCard } from "@/lib/registered-mail-documents-api";

const mocks = vi.hoisted(() => ({ request: vi.fn(), requestBlob: vi.fn() }));
vi.mock("@/lib/api/core", () => mocks);
beforeEach(() => vi.clearAllMocks());

test("list, upload multipart and authenticated download use the mail-scoped routes", async () => {
  mocks.request.mockResolvedValue([]);
  await listRegisteredMailCards("token", "mail");
  expect(mocks.request).toHaveBeenLastCalledWith("/ruolo/tributi/raccomandate/mail/cartoline", { headers: { Authorization: "Bearer token" } });
  const file = new File(["%PDF-"], "card.pdf", { type: "application/pdf" });
  await uploadRegisteredMailCard("token", "mail", file, "619592000378", "2025-09-12");
  const [path, options] = mocks.request.mock.calls.at(-1)!;
  expect(path).toBe("/ruolo/tributi/raccomandate/mail/cartoline");
  expect(options.method).toBe("POST");
  expect(options.headers).toEqual({ Authorization: "Bearer token" });
  expect(options.body.get("file")).toBe(file);
  expect(options.body.get("tracking_number")).toBe("619592000378");
  expect(options.body.get("scanned_on")).toBe("2025-09-12");
  expect(options.body.get("source_reference")).toBe("card.pdf");
  mocks.requestBlob.mockResolvedValue(new Blob(["pdf"]));
  await downloadRegisteredMailCard("token", "mail", "card");
  expect(mocks.requestBlob).toHaveBeenCalledWith("/ruolo/tributi/raccomandate/mail/cartoline/card/download", { headers: { Authorization: "Bearer token" } });
});
