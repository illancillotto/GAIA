"use client";

const STORAGE_KEY = "gaia.presence.action";
const ACTION_TTL_MS = 2 * 60 * 1000;
const EVENT_NAME = "gaia-presence-action-changed";

type PresenceActionPayload = {
  actionLabel: string;
  occurredAt: string;
};

function readStoredAction(): PresenceActionPayload | null {
  if (typeof window === "undefined") {
    return null;
  }
  const raw = window.sessionStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return null;
  }
  try {
    const payload = JSON.parse(raw) as PresenceActionPayload;
    if (!payload.actionLabel || !payload.occurredAt) {
      return null;
    }
    const occurredAtMs = Date.parse(payload.occurredAt);
    if (Number.isNaN(occurredAtMs) || Date.now() - occurredAtMs > ACTION_TTL_MS) {
      window.sessionStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return payload;
  } catch {
    window.sessionStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

function dispatchPresenceActionChanged() {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(new CustomEvent(EVENT_NAME));
}

export function recordPresenceAction(actionLabel: string) {
  if (typeof window === "undefined") {
    return;
  }
  const normalized = actionLabel.trim();
  if (!normalized) {
    return;
  }
  window.sessionStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      actionLabel: normalized,
      occurredAt: new Date().toISOString(),
    } satisfies PresenceActionPayload),
  );
  dispatchPresenceActionChanged();
}

export function clearPresenceAction() {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.removeItem(STORAGE_KEY);
  dispatchPresenceActionChanged();
}

export function getCurrentPresenceActionLabel(): string | null {
  return readStoredAction()?.actionLabel ?? null;
}

export function getPresenceActionChangedEventName(): string {
  return EVENT_NAME;
}
