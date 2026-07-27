import { afterEach, describe, expect, test, vi } from "vitest";

import {
  classifyUtenzeDocumentContent,
  request,
} from "@/lib/api";
import { confirmPasswordReset, getPasswordResetInfo, requestPasswordReset } from "@/lib/password-reset-api";

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

  test("calls password reset endpoints", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ message: "mail inviata se account esistente" }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            username: "admin",
            email: "admin@example.local",
            full_name: null,
            expires_at: "2026-07-27T10:00:00+00:00",
          }),
          {
            status: 200,
            headers: { "content-type": "application/json" },
          },
        ),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ username: "admin", message: "Password aggiornata" }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await expect(requestPasswordReset("admin@example.local")).resolves.toEqual({
      message: "mail inviata se account esistente",
    });
    await expect(getPasswordResetInfo("token-1")).resolves.toEqual({
      username: "admin",
      email: "admin@example.local",
      full_name: null,
      expires_at: "2026-07-27T10:00:00+00:00",
    });
    await expect(confirmPasswordReset("token-1", "new-secret123")).resolves.toEqual({
      username: "admin",
      message: "Password aggiornata",
    });

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/auth/password-reset/request",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ identifier: "admin@example.local" }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/auth/password-reset/token-1", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "/api/auth/password-reset/token-1/confirm",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ password: "new-secret123" }),
      }),
    );
  });
});
