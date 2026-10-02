import type { WikiChatMessage, WikiRequestCreate } from "./types";

export type WikiSupportIntent = "help_request" | "bug_report" | "feature_request";

const MODULE_PATH_PREFIXES = [
  ["/network", "rete"],
  ["/nas-control", "accessi"],
  ["/catasto", "catasto"],
  ["/elaborazioni", "elaborazioni"],
  ["/presenze", "presenze"],
  ["/organigramma", "organigramma"],
  ["/wiki", "wiki"],
  ["/operazioni", "operazioni"],
  ["/riordino", "riordino"],
  ["/ruolo", "ruolo"],
  ["/utenze", "utenze"],
  ["/inventory", "inventario"],
] as const;

const OPTIONAL_SUPPORT_FIELDS = [
  "module_key",
  "page_path",
  "context_article",
  "conversation_id",
  "desired_outcome",
  "observed_behavior",
  "expected_behavior",
] as const;

export function inferModuleKeyFromPath(pathname: string): string | null {
  return MODULE_PATH_PREFIXES.find(([prefix]) => pathname.startsWith(prefix))?.[1] ?? null;
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
  const common = {
    user_question: lastUserQuestion,
    agent_response: params.assistantAnswer,
    module_key: inferModuleKeyFromPath(params.pathname),
    page_path: params.pathname,
    source_channel: params.sourceChannel,
    severity: "medium",
    conversation_id: params.conversationId ?? null,
    context_article: params.contextArticle ?? null,
  } satisfies Omit<WikiRequestCreate, "category">;

  if (params.intent === "bug_report") {
    return {
      ...common,
      category: "bug_report",
      request_type: "bug_report",
      impact_scope: "single_user",
      observed_behavior: params.assistantAnswer,
      desired_outcome: "Capire e risolvere il problema segnalato dall'utente.",
    };
  }

  if (params.intent === "help_request") {
    return {
      ...common,
      category: "support_request",
      request_type: "help_request",
      impact_scope: "single_user",
      desired_outcome: "Ricevere supporto operativo sull'uso della funzione richiesta.",
    };
  }

  return {
    ...common,
    category: "feature_request",
    request_type: "feature_request",
    impact_scope: "team",
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
  OPTIONAL_SUPPORT_FIELDS.forEach((key) => {
    const value = payload[key];
    if (value) {
      query.set(key, value);
    }
  });
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
