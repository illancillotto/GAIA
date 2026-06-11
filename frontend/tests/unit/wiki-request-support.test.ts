import { beforeEach, describe, expect, test, vi } from "vitest";

import {
  buildWikiRequestPayload,
  captureWikiRequestArtifacts,
  consumeWikiSupportDraft,
  prepareWikiSupportHref,
} from "@/features/wiki/request-support";

describe("wiki request support artifacts", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    window.sessionStorage.clear();
    window.history.replaceState({}, "", "/operazioni/pratiche/123?search=abc&codice_fiscale=RSSMRA80A01H501U&context=miniapp");
    Object.defineProperty(HTMLElement.prototype, "getBoundingClientRect", {
      configurable: true,
      value: () => ({
        width: 120,
        height: 24,
        top: 0,
        left: 0,
        bottom: 24,
        right: 120,
        x: 0,
        y: 0,
        toJSON: () => ({}),
      }),
    });
    Object.defineProperty(HTMLCanvasElement.prototype, "getContext", {
      configurable: true,
      value: vi.fn(() => null),
    });
  });

  test("builds request payload for feature request", () => {
    const payload = buildWikiRequestPayload({
      intent: "feature_request",
      pathname: "/operazioni/pratiche/123",
      conversationId: "conv-1",
      messages: [{ id: "u1", role: "user", content: "Serve una nuova azione massiva", timestamp: new Date() }],
      assistantAnswer: "Non trovo una funzione esistente.",
      sourceChannel: "wiki_page",
    });

    expect(payload.request_type).toBe("feature_request");
    expect(payload.module_key).toBe("operazioni");
    expect(payload.page_path).toBe("/operazioni/pratiche/123");
    expect(payload.user_question).toBe("Serve una nuova azione massiva");
  });

  test("captures sanitized ui snapshot with typed module details", async () => {
    document.body.innerHTML = `
      <main>
        <h1>Pratica operativa</h1>
        <div role="tab" aria-selected="true">Dettaglio</div>
        <dl>
          <dt>Numero pratica</dt><dd>CASE-123</dd>
          <dt>Stato</dt><dd>In lavorazione</dd>
          <dt>Categoria</dt><dd>Verifica</dd>
          <dt>Gravità</dt><dd>Alta</dd>
          <dt>Assegnata a</dt><dd>Mario Rossi</dd>
          <dt>Segnalazione sorgente</dt><dd>SR-9</dd>
          <dt>Email</dt><dd>mario.rossi@example.com</dd>
        </dl>
        <input name="codice_fiscale_operatore" value="RSSMRA80A01H501U" />
        <input name="search" value="ricerca pratica" />
      </main>
    `;

    const artifacts = await captureWikiRequestArtifacts();
    expect(artifacts.screenshotFile ?? null).toBeNull();
    expect(artifacts.uiSnapshot).toBeTruthy();

    const snapshot = artifacts.uiSnapshot as Record<string, unknown>;
    const queryParams = snapshot.query_params as Record<string, string>;
    const formState = snapshot.form_state as Array<Record<string, unknown>>;
    const moduleSnapshot = snapshot.module_snapshot as Record<string, unknown>;
    const entity = moduleSnapshot.entity as Record<string, unknown>;

    expect(queryParams.codice_fiscale).toBeUndefined();
    expect(queryParams.context).toBe("miniapp");
    expect(formState.some((item) => item.name === "codice_fiscale_operatore" && item.value === "[redacted]")).toBe(true);
    expect(formState.some((item) => item.name === "search" && item.value === "ricerca pratica")).toBe(true);
    expect(moduleSnapshot.module).toBe("operazioni");
    expect(moduleSnapshot.entity_id).toBe("123");
    expect(entity.case_number).toBe("CASE-123");
    expect(entity.status).toBe("In lavorazione");
    expect(entity.assigned_to).toBe("Mario Rossi");
    expect(entity.email).toBeUndefined();
  });

  test("stores and consumes support draft with sanitized snapshot", async () => {
    window.history.replaceState({}, "", "/utenze/abc-123?tab=scheda&email=mario@example.com");
    document.body.innerHTML = `
      <main>
        <h1>Dettaglio utenza</h1>
        <h2>Mario Rossi</h2>
        <dt>Tipo</dt><dd>persona</dd>
        <dt>Percorso NAS</dt><dd>/volume1/settore catasto/ARCHIVIO/Rossi</dd>
        <input name="email" value="mario@example.com" />
      </main>
    `;

    const href = await prepareWikiSupportHref({
      intent: "help_request",
      pathname: "/utenze/abc-123",
      conversationId: "conv-2",
      messages: [{ id: "u1", role: "user", content: "Mi serve aiuto sulla scheda", timestamp: new Date() }],
      assistantAnswer: "Serve supporto dedicato.",
    });

    const url = new URL(href, "http://localhost");
    const draftId = url.searchParams.get("draft_id");
    expect(draftId).toBeTruthy();

    const draftArtifacts = consumeWikiSupportDraft(draftId);
    expect(draftArtifacts).toBeTruthy();
    expect(consumeWikiSupportDraft(draftId)).toBeNull();

    const snapshot = draftArtifacts?.uiSnapshot as Record<string, unknown>;
    const moduleSnapshot = snapshot.module_snapshot as Record<string, unknown>;
    const entity = moduleSnapshot.entity as Record<string, unknown>;
    const formState = snapshot.form_state as Array<Record<string, unknown>>;

    expect(moduleSnapshot.module).toBe("utenze");
    expect(entity.nas_path_present).toBe(true);
    expect(formState[0]?.value).toBe("[redacted]");
  });
});
