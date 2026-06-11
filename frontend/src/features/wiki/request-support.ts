import type { WikiRequestArtifactCreateInput } from "@/types/api";
import type { WikiChatMessage, WikiRequestCreate } from "./types";

export type WikiSupportIntent = "help_request" | "bug_report" | "feature_request";

type SupportDraftRecord = {
  id: string;
  createdAt: string;
  screenshotDataUrl: string | null;
  screenshotMeta: Record<string, unknown> | null;
  uiSnapshot: Record<string, unknown> | null;
};

const SUPPORT_DRAFT_STORAGE_KEY = "gaia:wiki-support-drafts";
const SUPPORT_DRAFT_TTL_MS = 15 * 60 * 1000;
const INPUT_NAME_DENYLIST = ["password", "token", "secret", "otp", "pin"];
const SENSITIVE_QUERY_PARAM_DENYLIST = ["token", "secret", "password", "otp", "pin", "email", "phone", "telefono", "cf", "codice_fiscale", "partita_iva"];
const SENSITIVE_LABEL_TOKENS = [
  "codice fiscale",
  "partita iva",
  "email",
  "pec",
  "telefono",
  "cellulare",
  "phone",
  "mail",
  "indirizzo",
  "residenza",
  "sede legale",
  "nas path",
  "percorso nas",
];
const REDACTED_PLACEHOLDER = "[redacted]";
const EMAIL_RE = /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi;
const PHONE_RE = /\b(?:\+?\d[\d\s().-]{7,}\d)\b/g;
const TAX_ID_RE = /\b[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]\b/gi;
const VAT_RE = /\b\d{11}\b/g;
const LONG_TOKEN_RE = /\b[a-z0-9]{24,}\b/gi;

export function inferModuleKeyFromPath(pathname: string): string | null {
  if (pathname.startsWith("/network")) return "rete";
  if (pathname.startsWith("/nas-control")) return "accessi";
  if (pathname.startsWith("/catasto")) return "catasto";
  if (pathname.startsWith("/inaz")) return "inaz";
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

function buildSupportHrefFromPayload(
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

function truncate(value: string, maxLength = 180): string {
  return value.length <= maxLength ? value : `${value.slice(0, maxLength - 1)}…`;
}

function normalizeLabel(value: string): string {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function isSensitiveLabelValue(value: string | null | undefined): boolean {
  const normalized = normalizeLabel(value ?? "");
  return SENSITIVE_LABEL_TOKENS.some((token) => normalized.includes(normalizeLabel(token)));
}

function sanitizeTextValue(value: string | null | undefined, options?: { forceRedact?: boolean }): string | null {
  if (value == null) {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return trimmed;
  }
  if (options?.forceRedact) {
    return REDACTED_PLACEHOLDER;
  }
  let next = trimmed
    .replace(EMAIL_RE, REDACTED_PLACEHOLDER)
    .replace(TAX_ID_RE, REDACTED_PLACEHOLDER)
    .replace(VAT_RE, REDACTED_PLACEHOLDER)
    .replace(LONG_TOKEN_RE, REDACTED_PLACEHOLDER);
  next = next.replace(PHONE_RE, (match) => {
    const digits = match.replace(/\D/g, "");
    return digits.length >= 8 ? REDACTED_PLACEHOLDER : match;
  });
  return truncate(next, 180);
}

function sanitizeUnknownValue(value: unknown): unknown {
  if (typeof value === "string") {
    return sanitizeTextValue(value);
  }
  if (Array.isArray(value)) {
    return value.map((item) => sanitizeUnknownValue(item));
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, nested]) => [
        key,
        isSensitiveLabelValue(key) && typeof nested === "string"
          ? REDACTED_PLACEHOLDER
          : sanitizeUnknownValue(nested),
      ]),
    );
  }
  return value;
}

function pickQueryParams(params: URLSearchParams, keys?: string[]): Record<string, string> {
  const entries = Array.from(params.entries()).filter(([key, value]) => {
    if (!value) return false;
    if (SENSITIVE_QUERY_PARAM_DENYLIST.some((token) => key.toLowerCase().includes(token))) return false;
    if (keys && !keys.includes(key)) return false;
    return true;
  });
  return Object.fromEntries(
    entries.slice(0, 12).map(([key, value]) => [key, sanitizeTextValue(value, { forceRedact: isSensitiveLabelValue(key) }) ?? ""]),
  );
}

function pathSegments(pathname: string): string[] {
  return pathname.split("/").filter(Boolean);
}

function buildSanitizedSearch(params: URLSearchParams): string {
  const filtered = new URLSearchParams();
  for (const [key, value] of Object.entries(pickQueryParams(params))) {
    filtered.set(key, value);
  }
  const encoded = filtered.toString();
  return encoded ? `?${encoded}` : "";
}

function isVisibleElement(element: HTMLElement): boolean {
  const style = window.getComputedStyle(element);
  const rect = element.getBoundingClientRect();
  return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
}

function shouldCaptureInputValue(input: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement): boolean {
  const joined = `${input.name} ${input.id} ${input.getAttribute("aria-label") ?? ""}`.toLowerCase();
  return !INPUT_NAME_DENYLIST.some((token) => joined.includes(token));
}

function collectFormSnapshot(): Array<Record<string, unknown>> {
  const fields = Array.from(document.querySelectorAll<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>("input, textarea, select"));
  return fields
    .filter((field) => {
      if (!isVisibleElement(field)) return false;
      if (field instanceof HTMLInputElement && ["hidden", "password", "file"].includes(field.type)) return false;
      if (!shouldCaptureInputValue(field)) return false;
      return true;
    })
    .slice(0, 25)
    .map((field) => ({
      tag: field.tagName.toLowerCase(),
      type: field instanceof HTMLInputElement ? field.type : field.tagName.toLowerCase(),
      name: field.name || null,
      id: field.id || null,
      value: sanitizeTextValue(field.value ?? "", {
        forceRedact: isSensitiveLabelValue(field.name) || isSensitiveLabelValue(field.id) || isSensitiveLabelValue(field.getAttribute("aria-label")),
      }),
      checked: field instanceof HTMLInputElement ? field.checked : undefined,
    }));
}

function findDefinitionListValue(labels: string[]): string | null {
  const normalizedLabels = new Set(labels.map((label) => normalizeLabel(label)));
  const forceRedact = labels.some((label) => isSensitiveLabelValue(label));
  const candidates = Array.from(document.querySelectorAll<HTMLElement>("dt, p, span, div, label"));
  for (const candidate of candidates) {
    const text = candidate.textContent?.trim();
    if (!text || !normalizedLabels.has(normalizeLabel(text.replace(/:$/, "")))) {
      continue;
    }
    const nextElement = candidate.nextElementSibling;
    const nextText = nextElement?.textContent?.trim();
    if (nextText) {
      return sanitizeTextValue(nextText, { forceRedact });
    }
    const parentText = candidate.parentElement?.textContent?.trim();
    if (parentText && parentText !== text) {
      return sanitizeTextValue(parentText.replace(text, "").trim(), { forceRedact });
    }
  }
  return null;
}

function collectActiveTabs(): string[] {
  return Array.from(
    document.querySelectorAll<HTMLElement>("[role='tab'][aria-selected='true'], [data-state='active'], button[aria-pressed='true']"),
  )
    .map((item) => item.textContent?.trim() ?? "")
    .filter(Boolean)
    .map((item) => truncate(item, 60))
    .slice(0, 6);
}

function collectVisibleBadges(): string[] {
  return Array.from(document.querySelectorAll<HTMLElement>("[class*='badge'], [class*='pill']"))
    .filter(isVisibleElement)
    .map((item) => item.textContent?.trim() ?? "")
    .filter(Boolean)
    .map((item) => sanitizeTextValue(item) ?? "")
    .filter(Boolean)
    .slice(0, 8);
}

function extractOperazioniSnapshot(pathname: string, query: URLSearchParams): Record<string, unknown> {
  const segments = pathSegments(pathname);
  return {
    module: "operazioni",
    route_type: segments[1] ?? "dashboard",
    route_key: segments.slice(0, 3).join("/") || "operazioni",
    entity_id: segments[2] ?? null,
    context: query.get("context"),
    filters: pickQueryParams(query, ["status", "page", "page_size", "search", "from_date", "to_date", "granularity", "context"]),
    active_tabs: collectActiveTabs(),
    entity: {
      title: document.querySelector("h1")?.textContent?.trim() ?? null,
      case_number: findDefinitionListValue(["Numero pratica", "Case number", "ID pratica"]),
      status: findDefinitionListValue(["Stato", "Status"]),
      category: findDefinitionListValue(["Categoria"]),
      severity: findDefinitionListValue(["Gravita", "Gravità", "Severity"]),
      assigned_to: findDefinitionListValue(["Assegnata a", "Assegnato a", "Assigned to"]),
      source_report: findDefinitionListValue(["Segnalazione", "Segnalazione sorgente"]),
    },
  };
}

function extractCatastoSnapshot(pathname: string, query: URLSearchParams): Record<string, unknown> {
  const segments = pathSegments(pathname);
  return {
    module: "catasto",
    route_type: segments[1] ?? "dashboard",
    entity_id: segments[2] ?? null,
    filters: pickQueryParams(query, ["anno", "selection", "embedded", "search", "tab", "tipo", "scope"]),
    active_tabs: collectActiveTabs(),
    entity: {
      title: document.querySelector("h1")?.textContent?.trim() ?? null,
      comune: findDefinitionListValue(["Comune"]),
      foglio: findDefinitionListValue(["Foglio"]),
      particella: findDefinitionListValue(["Particella"]),
      subalterno: findDefinitionListValue(["Subalterno"]),
      distretto: findDefinitionListValue(["Distretto"]),
      campaign_year: query.get("anno"),
      badges: collectVisibleBadges(),
    },
  };
}

function extractNetworkSnapshot(pathname: string, query: URLSearchParams): Record<string, unknown> {
  const segments = pathSegments(pathname);
  return {
    module: "rete",
    route_type: segments[1] ?? "dashboard",
    entity_id: segments[2] ?? null,
    filters: pickQueryParams(query, ["search", "status", "page", "page_size", "scan_id", "subject", "view"]),
    active_tabs: collectActiveTabs(),
    entity: {
      title: document.querySelector("h1")?.textContent?.trim() ?? null,
      ip_address: findDefinitionListValue(["IP"]),
      mac_address: findDefinitionListValue(["MAC"]),
      vendor: findDefinitionListValue(["Vendor"]),
      model_name: findDefinitionListValue(["Modello", "Model"]),
      device_type: findDefinitionListValue(["Tipo dispositivo", "Device type"]),
      assigned_user: findDefinitionListValue(["Utente associato", "Assigned user"]),
      lifecycle_state: findDefinitionListValue(["Ciclo di vita", "Lifecycle"]),
      badges: collectVisibleBadges(),
    },
  };
}

function extractUtenzeSnapshot(pathname: string, query: URLSearchParams): Record<string, unknown> {
  const segments = pathSegments(pathname);
  const routeType = segments[1] ?? "dashboard";
  const entityId = routeType !== "page" && routeType !== "subjects" && routeType !== "import" ? routeType : segments[2] ?? null;
  return {
    module: "utenze",
    route_type: routeType,
    entity_id: entityId,
    filters: pickQueryParams(query, ["embedded", "tab", "search", "status", "page"]),
    active_tabs: collectActiveTabs(),
    entity: {
      title: document.querySelector("h1")?.textContent?.trim() ?? null,
      subject_label: findDefinitionListValue(["Ragione sociale", "Utente", "Soggetto"]) ?? document.querySelector("h2")?.textContent?.trim() ?? null,
      subject_type: findDefinitionListValue(["Tipo"]),
      status: findDefinitionListValue(["Stato"]),
      nas_path_present: Boolean(findDefinitionListValue(["Percorso NAS"])),
      documents_count: findDefinitionListValue(["Documenti", "Numero documenti"]),
      audit_log_count: findDefinitionListValue(["Audit log"]),
      sensitive_fields_omitted: true,
    },
  };
}

function extractModuleSnapshot(pathname: string, query: URLSearchParams): Record<string, unknown> | null {
  const moduleKey = inferModuleKeyFromPath(pathname);
  if (moduleKey === "operazioni") return extractOperazioniSnapshot(pathname, query);
  if (moduleKey === "catasto") return extractCatastoSnapshot(pathname, query);
  if (moduleKey === "rete") return extractNetworkSnapshot(pathname, query);
  if (moduleKey === "utenze") return extractUtenzeSnapshot(pathname, query);
  return moduleKey ? { module: moduleKey, filters: pickQueryParams(query), active_tabs: collectActiveTabs() } : null;
}

function collectUiSnapshot(): Record<string, unknown> {
  const query = new URLSearchParams(window.location.search);
  const pathname = window.location.pathname;
  const sanitizedSearch = buildSanitizedSearch(query);
  const heading = document.querySelector("h1, [data-page-title='true']")?.textContent?.trim() ?? null;
  const breadcrumb = Array.from(document.querySelectorAll("nav[aria-label='breadcrumb'] a, [data-breadcrumb]"))
    .map((node) => node.textContent?.trim() ?? "")
    .filter(Boolean)
    .slice(0, 8);
  const selectedText = window.getSelection?.()?.toString().trim() ?? "";

  return {
    captured_at: new Date().toISOString(),
    page_title: sanitizeTextValue(document.title),
    heading: sanitizeTextValue(heading),
    breadcrumb: breadcrumb.map((item) => sanitizeTextValue(item) ?? "").filter(Boolean),
    location: {
      href: `${window.location.origin}${pathname}${sanitizedSearch}${window.location.hash}`,
      pathname,
      search: sanitizedSearch,
      hash: window.location.hash,
    },
    viewport: {
      width: window.innerWidth,
      height: window.innerHeight,
      device_pixel_ratio: window.devicePixelRatio || 1,
    },
    scroll: {
      x: window.scrollX,
      y: window.scrollY,
    },
    selected_text: selectedText ? sanitizeTextValue(selectedText) : null,
    active_tabs: collectActiveTabs().map((item) => sanitizeTextValue(item) ?? "").filter(Boolean),
    query_params: pickQueryParams(query),
    form_state: collectFormSnapshot(),
    module_snapshot: sanitizeUnknownValue(extractModuleSnapshot(pathname, query)),
  };
}

function syncFormValues(root: HTMLElement): void {
  const originalInputs = document.querySelectorAll<HTMLInputElement>("input");
  const clonedInputs = root.querySelectorAll<HTMLInputElement>("input");
  originalInputs.forEach((input, index) => {
    const clone = clonedInputs[index];
    if (!clone) return;
    clone.value = input.value;
    clone.setAttribute("value", input.value);
    if (input.checked) {
      clone.setAttribute("checked", "checked");
    } else {
      clone.removeAttribute("checked");
    }
  });

  const originalTextareas = document.querySelectorAll<HTMLTextAreaElement>("textarea");
  const clonedTextareas = root.querySelectorAll<HTMLTextAreaElement>("textarea");
  originalTextareas.forEach((input, index) => {
    const clone = clonedTextareas[index];
    if (!clone) return;
    clone.value = input.value;
    clone.textContent = input.value;
  });

  const originalSelects = document.querySelectorAll<HTMLSelectElement>("select");
  const clonedSelects = root.querySelectorAll<HTMLSelectElement>("select");
  originalSelects.forEach((input, index) => {
    const clone = clonedSelects[index];
    if (!clone) return;
    clone.value = input.value;
    Array.from(clone.options).forEach((option) => {
      option.selected = option.value === input.value;
    });
  });
}

function collectCssText(): string {
  const chunks: string[] = [];
  for (const stylesheet of Array.from(document.styleSheets)) {
    try {
      const rules = stylesheet.cssRules;
      for (const rule of Array.from(rules)) {
        chunks.push(rule.cssText);
      }
    } catch {
      // Ignore cross-origin or unreadable stylesheets.
    }
  }
  return chunks.join("\n");
}

function sanitizeClonedScreenshot(root: HTMLElement): void {
  const textNodes = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const pendingTextNodes: Text[] = [];
  while (textNodes.nextNode()) {
    if (textNodes.currentNode instanceof Text) {
      pendingTextNodes.push(textNodes.currentNode);
    }
  }
  for (const node of pendingTextNodes) {
    const original = node.textContent ?? "";
    const sanitized = sanitizeTextValue(original);
    if (sanitized !== original) {
      node.textContent = sanitized ?? "";
    }
  }

  for (const field of Array.from(root.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>("input, textarea"))) {
    const fieldLabel = `${field.name} ${field.id} ${field.getAttribute("aria-label") ?? ""}`;
    const sanitized = sanitizeTextValue(field.value, { forceRedact: isSensitiveLabelValue(fieldLabel) });
    field.value = sanitized ?? "";
    if (field instanceof HTMLInputElement) {
      field.setAttribute("value", sanitized ?? "");
    } else {
      field.textContent = sanitized ?? "";
    }
  }
}

async function renderPageScreenshotBlob(): Promise<{ blob: Blob; meta: Record<string, unknown> } | null> {
  const rootClone = document.documentElement.cloneNode(true);
  if (!(rootClone instanceof HTMLElement)) {
    return null;
  }
  syncFormValues(rootClone);
  sanitizeClonedScreenshot(rootClone);
  const styleTag = document.createElement("style");
  styleTag.textContent = collectCssText();
  rootClone.querySelector("head")?.appendChild(styleTag);

  const width = Math.max(document.documentElement.clientWidth, window.innerWidth);
  const height = Math.max(document.documentElement.clientHeight, window.innerHeight);
  const scale = width > 1600 ? 1600 / width : 1;
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(width * scale));
  canvas.height = Math.max(1, Math.round(height * scale));
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return null;
  }

  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
      <foreignObject width="100%" height="100%">${new XMLSerializer().serializeToString(rootClone)}</foreignObject>
    </svg>
  `;
  const svgBlob = new Blob([svg], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(svgBlob);

  try {
    const image = await new Promise<HTMLImageElement>((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error("Impossibile renderizzare lo screenshot della pagina."));
      img.src = url;
    });
    ctx.scale(scale, scale);
    ctx.drawImage(image, 0, 0);
  } finally {
    URL.revokeObjectURL(url);
  }

  const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.72));
  if (!blob) {
    return null;
  }
  return {
    blob,
    meta: {
      format: "image/jpeg",
      capture_method: "svg_foreign_object",
      width,
      height,
      scale,
    },
  };
}

async function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(typeof reader.result === "string" ? reader.result : "");
    reader.onerror = () => reject(new Error("Impossibile convertire lo screenshot."));
    reader.readAsDataURL(blob);
  });
}

function dataUrlToFile(dataUrl: string, filename: string): File | null {
  const match = dataUrl.match(/^data:([^;]+);base64,(.+)$/);
  if (!match) {
    return null;
  }
  const [, mimeType, encoded] = match;
  const binary = atob(encoded);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return new File([bytes], filename, { type: mimeType });
}

function readDraftMap(): Record<string, SupportDraftRecord> {
  if (typeof window === "undefined") {
    return {};
  }
  try {
    const raw = window.sessionStorage.getItem(SUPPORT_DRAFT_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as Record<string, SupportDraftRecord>;
    if (!parsed || typeof parsed !== "object") return {};
    return parsed;
  } catch {
    return {};
  }
}

function writeDraftMap(nextDrafts: Record<string, SupportDraftRecord>): void {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.setItem(SUPPORT_DRAFT_STORAGE_KEY, JSON.stringify(nextDrafts));
}

function cleanupDraftMap(drafts: Record<string, SupportDraftRecord>): Record<string, SupportDraftRecord> {
  const now = Date.now();
  return Object.fromEntries(
    Object.entries(drafts).filter(([, draft]) => now - new Date(draft.createdAt).getTime() < SUPPORT_DRAFT_TTL_MS),
  );
}

export async function captureWikiRequestArtifacts(): Promise<WikiRequestArtifactCreateInput> {
  const uiSnapshot = collectUiSnapshot();
  try {
    const rendered = await renderPageScreenshotBlob();
    if (!rendered) {
      return { uiSnapshot };
    }
    const screenshotFile = new File([rendered.blob], "wiki-request-screenshot.jpg", { type: rendered.blob.type || "image/jpeg" });
    return {
      screenshotFile,
      screenshotMeta: rendered.meta,
      uiSnapshot,
    };
  } catch {
    return { uiSnapshot };
  }
}

export async function prepareWikiSupportHref(params: {
  intent: WikiSupportIntent;
  pathname: string;
  contextArticle?: string | null;
  conversationId?: string | null;
  messages: WikiChatMessage[];
  assistantAnswer: string;
}): Promise<string> {
  const payload = buildWikiRequestPayload({
    ...params,
    sourceChannel: "support_page",
  });
  const artifacts = await captureWikiRequestArtifacts();
  const screenshotDataUrl = artifacts.screenshotFile ? await blobToDataUrl(artifacts.screenshotFile) : null;
  const draftId = typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}`;
  const nextDrafts = cleanupDraftMap(readDraftMap());
  nextDrafts[draftId] = {
    id: draftId,
    createdAt: new Date().toISOString(),
    screenshotDataUrl,
    screenshotMeta: artifacts.screenshotMeta ?? null,
    uiSnapshot: artifacts.uiSnapshot ?? null,
  };
  writeDraftMap(nextDrafts);
  return buildSupportHrefFromPayload({ intent: params.intent, draftId }, payload);
}

export function consumeWikiSupportDraft(draftId: string | null): WikiRequestArtifactCreateInput | null {
  if (!draftId) {
    return null;
  }
  const drafts = cleanupDraftMap(readDraftMap());
  const draft = drafts[draftId];
  if (!draft) {
    writeDraftMap(drafts);
    return null;
  }
  delete drafts[draftId];
  writeDraftMap(drafts);
  return {
    screenshotFile: draft.screenshotDataUrl ? dataUrlToFile(draft.screenshotDataUrl, "wiki-request-screenshot.jpg") : null,
    screenshotMeta: draft.screenshotMeta,
    uiSnapshot: draft.uiSnapshot,
  };
}
