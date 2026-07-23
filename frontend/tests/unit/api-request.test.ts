import { afterEach, describe, expect, test, vi } from "vitest";

import { classifyUtenzeDocumentContent, request } from "@/lib/api";

describe("api request helper", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("returns undefined for 204 no content responses", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(null, {
        status: 204,
        statusText: "No Content",
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(request<void>("/presenze/sync/jobs/job-1", { method: "DELETE" })).resolves.toBeUndefined();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  test("posts document content classification payload", async () => {
    const payload = {
      id: "document-1",
      filename: "ricevuta.eml",
      relative_path: "ricevuta.eml",
      nas_path: "/nas/ricevuta.eml",
      extension: ".eml",
      is_pdf: false,
      doc_type: "altro",
      classification_source: "auto",
      smart_category: "delivery_proof",
      smart_category_label: "Prove invio e PEC",
      smart_priority: 80,
      smart_confidence: 0.72,
      smart_reason: "nome file contiene riferimenti a ricevuta, PEC o email",
      content_classification_status: "classified",
      content_category: "delivery_proof",
      content_category_label: "Prove invio e PEC",
      content_confidence: 0.82,
      content_reason: "contenuto con riferimenti a PEC o prove di consegna",
      content_excerpt: "Ricevuta di avvenuta consegna PEC",
      content_classification_source: "provided_text",
      content_classified_at: "2026-07-23T12:00:00Z",
      content_classification_error: null,
      warnings: [],
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(classifyUtenzeDocumentContent("token", "document-1", "Ricevuta di avvenuta consegna PEC")).resolves.toEqual(payload);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/utenze/documents/document-1/content-classification",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ text: "Ricevuta di avvenuta consegna PEC" }),
        headers: expect.objectContaining({
          Authorization: "Bearer token",
          "Content-Type": "application/json",
        }),
      }),
    );
  });
});
