import { describe, expect, test } from "vitest";

import {
  buildSupportHrefFromPayload,
  buildWikiRequestPayload,
  buildWikiSupportHref,
  inferModuleKeyFromPath,
} from "@/features/wiki/request-support-payload";
import type { WikiChatMessage } from "@/features/wiki/types";

const messages: WikiChatMessage[] = [
  { id: "u1", role: "user", content: "Prima", timestamp: new Date(0) },
  { id: "u2", role: "user", content: " Ultima domanda ", timestamp: new Date(0) },
  { id: "a1", role: "assistant", content: "Risposta", timestamp: new Date(0) },
];

describe("wiki request payload contract", () => {
  test.each([
    ["/network", "rete"], ["/nas-control", "accessi"], ["/catasto", "catasto"],
    ["/elaborazioni", "elaborazioni"], ["/presenze", "presenze"],
    ["/organigramma", "organigramma"], ["/wiki", "wiki"],
    ["/operazioni", "operazioni"], ["/riordino", "riordino"],
    ["/ruolo", "ruolo"], ["/utenze", "utenze"], ["/inventory", "inventario"],
    ["/unknown", null], ["/NETWORK", null], ["/network-extra", "rete"],
  ])("preserves module prefix matching for %s", (path, expected) => {
    expect(inferModuleKeyFromPath(path!)).toBe(expected);
  });

  test.each([
    { intent: "bug_report", specific: {
      category: "bug_report", request_type: "bug_report", impact_scope: "single_user",
      observed_behavior: "Risposta",
      desired_outcome: "Capire e risolvere il problema segnalato dall'utente.",
    } },
    { intent: "help_request", specific: {
      category: "support_request", request_type: "help_request", impact_scope: "single_user",
      desired_outcome: "Ricevere supporto operativo sull'uso della funzione richiesta.",
    } },
    { intent: "feature_request", specific: {
      category: "feature_request", request_type: "feature_request", impact_scope: "team",
      desired_outcome: "Introdurre o migliorare una funzionalit\u00e0 richiesta dall'utente.",
      expected_behavior: "Disponibilit\u00e0 di una funzione o di un flusso pi\u00f9 adatto all'esigenza espressa.",
    } },
  ] as const)("preserves the complete %s payload", ({ intent, specific }) => {
    const original = [...messages];
    for (const context of [undefined, null, "", "context-1"]) {
      expect(buildWikiRequestPayload({
        intent, pathname: "/operazioni/123", messages, assistantAnswer: "Risposta",
        sourceChannel: "widget", conversationId: context, contextArticle: context,
      })).toEqual({
        user_question: "Ultima domanda", agent_response: "Risposta",
        module_key: "operazioni", page_path: "/operazioni/123", source_channel: "widget",
        severity: "medium", conversation_id: context ?? null, context_article: context ?? null,
        ...specific,
      });
    }
    expect(messages).toEqual(original);
  });

  test.each([{ inputMessages: [] }, { inputMessages: [messages[2]] }, { inputMessages: [{ ...messages[0], content: "   " }] }])(
    "uses an empty question without a nonblank last user message: %j",
    ({ inputMessages }) => {
      expect(buildWikiRequestPayload({
        intent: "help_request", pathname: "/", messages: inputMessages,
        assistantAnswer: "", sourceChannel: "support_page",
      })).toMatchObject({ user_question: "", module_key: null });
    },
  );

  test("serializes all optional support fields and encodes their values", () => {
    const href = buildSupportHrefFromPayload({ intent: "bug_report", draftId: "draft & 1" }, {
      user_question: "Perche?", agent_response: "A & B", category: "bug_report", request_type: "bug_report",
      module_key: "rete", page_path: "/network?a=1", context_article: "article/1",
      conversation_id: "conv-1", desired_outcome: "desired", observed_behavior: "observed", expected_behavior: "expected",
    });
    const url = new URL(href, "https://gaia.test");
    expect(url.pathname).toBe("/wiki/support");
    expect(Object.fromEntries(url.searchParams)).toEqual({
      intent: "bug_report", draft_id: "draft & 1", question: "Perche?", answer: "A & B",
      category: "bug_report", request_type: "bug_report", module_key: "rete", page_path: "/network?a=1",
      context_article: "article/1", conversation_id: "conv-1", desired_outcome: "desired",
      observed_behavior: "observed", expected_behavior: "expected",
    });
  });

  test("omits absent optional fields and retains query defaults", () => {
    const href = buildSupportHrefFromPayload({ intent: "help_request" }, {
      user_question: "", category: "support_request",
    });
    expect(Object.fromEntries(new URL(href, "https://gaia.test").searchParams)).toEqual({
      intent: "help_request", question: "", answer: "", category: "support_request", request_type: "help_request",
    });
  });

  test("composes a support link from the same payload contract", () => {
    const params = { intent: "help_request", pathname: "/wiki", messages, assistantAnswer: "Risposta", draftId: "draft-1" } as const;
    const payload = buildWikiRequestPayload({ ...params, sourceChannel: "support_page" });
    expect(buildWikiSupportHref(params)).toBe(buildSupportHrefFromPayload(params, payload));
  });
});
