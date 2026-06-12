import type { WikiChatMessage, WikiRequestCreate } from "./types";

export type WikiSupportIntent = "help_request" | "bug_report" | "feature_request";

export function inferModuleKeyFromPath(pathname: string): string | null {
  if (pathname.startsWith("/network")) return "rete";
  if (pathname.startsWith("/nas-control")) return "accessi";
  if (pathname.startsWith("/catasto")) return "catasto";
  if (pathname.startsWith("/elaborazioni")) return "elaborazioni";
  if (pathname.startsWith("/inaz")) return "inaz";
  if (pathname.startsWith("/organigramma")) return "organigramma";
  if (pathname.startsWith("/wiki")) return "wiki";
  if (pathname.startsWith("/operazioni")) return "operazioni";
  if (pathname.startsWith("/riordino")) return "riordino";
  if (pathname.startsWith("/ruolo")) return "ruolo";
  if (pathname.startsWith("/utenze")) return "utenze";
  if (pathname.startsWith("/inventory")) return "inventario";
  return null;
}

export function buildWikiRequestPayload(params: {
  intent: WikiSupportIntent;
  pathname: string;
  contextArticle?: string | null;
  conversationId?: string | null;
  messages: WikiChatMessage[];
  assistantAnswer: string;
  sourceChannel: WikiRequestCreate["source_channel"];
}): WikiRequestCreate {
  const lastUserQuestion =
    [...params.messages].reverse().find((message) => message.role === "user")?.content?.trim() ?? "";
  const moduleKey = inferModuleKeyFromPath(params.pathname);

  if (params.intent === "bug_report") {
    return {
      user_question: lastUserQuestion,
      agent_response: params.assistantAnswer,
      category: "bug_report",
      request_type: "bug_report",
      module_key: moduleKey,
      page_path: params.pathname,
      source_channel: params.sourceChannel,
      severity: "medium",
      impact_scope: "single_user",
      conversation_id: params.conversationId ?? null,
      context_article: params.contextArticle ?? null,
      observed_behavior: params.assistantAnswer,
      desired_outcome: "Capire e risolvere il problema segnalato dall'utente.",
    };
  }

  if (params.intent === "help_request") {
    return {
      user_question: lastUserQuestion,
      agent_response: params.assistantAnswer,
      category: "support_request",
      request_type: "help_request",
      module_key: moduleKey,
      page_path: params.pathname,
      source_channel: params.sourceChannel,
      severity: "medium",
      impact_scope: "single_user",
      conversation_id: params.conversationId ?? null,
      context_article: params.contextArticle ?? null,
      desired_outcome: "Ricevere supporto operativo sull'uso della funzione richiesta.",
    };
  }

  return {
    user_question: lastUserQuestion,
    agent_response: params.assistantAnswer,
    category: "feature_request",
    request_type: "feature_request",
    module_key: moduleKey,
    page_path: params.pathname,
    source_channel: params.sourceChannel,
    severity: "medium",
    impact_scope: "team",
    conversation_id: params.conversationId ?? null,
    context_article: params.contextArticle ?? null,
    desired_outcome: "Introdurre o migliorare una funzionalità richiesta dall'utente.",
    expected_behavior: "Disponibilità di una funzione o di un flusso più adatto all'esigenza espressa.",
  };
}

export function buildSupportHrefFromPayload(
  params: {
    intent: WikiSupportIntent;
    draftId?: string | null;
  },
  payload: WikiRequestCreate,
): string {
  const query = new URLSearchParams();
  query.set("intent", params.intent);
  query.set("question", payload.user_question);
  query.set("answer", payload.agent_response ?? "");
  query.set("category", payload.category);
  query.set("request_type", payload.request_type ?? "help_request");
  if (payload.module_key) query.set("module_key", payload.module_key);
  if (payload.page_path) query.set("page_path", payload.page_path);
  if (payload.context_article) query.set("context_article", payload.context_article);
  if (payload.conversation_id) query.set("conversation_id", payload.conversation_id);
  if (payload.desired_outcome) query.set("desired_outcome", payload.desired_outcome);
  if (payload.observed_behavior) query.set("observed_behavior", payload.observed_behavior);
  if (payload.expected_behavior) query.set("expected_behavior", payload.expected_behavior);
  if (params.draftId) query.set("draft_id", params.draftId);
  return `/wiki/support?${query.toString()}`;
}

export function buildWikiSupportHref(params: {
  intent: WikiSupportIntent;
  pathname: string;
  contextArticle?: string | null;
  conversationId?: string | null;
  messages: WikiChatMessage[];
  assistantAnswer: string;
  draftId?: string | null;
}): string {
  const payload = buildWikiRequestPayload({
    ...params,
    sourceChannel: "support_page",
  });
  return buildSupportHrefFromPayload({ intent: params.intent, draftId: params.draftId }, payload);
}
