import type { WikiRequestArtifactCreateInput } from "@/types/api";
import type { WikiChatMessage } from "./types";
import { buildSupportHrefFromPayload, buildWikiRequestPayload, type WikiSupportIntent } from "./request-support-payload";
import { captureWikiRequestArtifacts } from "./request-support-snapshot";

type SupportDraftRecord = {
  id: string;
  createdAt: string;
  screenshotDataUrl: string | null;
  screenshotMeta: Record<string, unknown> | null;
  uiSnapshot: Record<string, unknown> | null;
};

const SUPPORT_DRAFT_STORAGE_KEY = "gaia:wiki-support-drafts";
const SUPPORT_DRAFT_TTL_MS = 15 * 60 * 1000;

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
