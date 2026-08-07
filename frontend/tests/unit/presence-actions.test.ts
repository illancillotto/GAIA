import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import {
  clearPresenceAction,
  getCurrentPresenceActionLabel,
  getPresenceActionChangedEventName,
  recordPresenceAction,
} from "@/lib/presence-actions";

const STORAGE_KEY = "gaia.presence.action";

describe("presence actions", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-05-16T12:00:00.000Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  test("exposes the change event name", () => {
    expect(getPresenceActionChangedEventName()).toBe("gaia-presence-action-changed");
  });

  test("records trimmed action labels and dispatches change event", () => {
    const listener = vi.fn();
    window.addEventListener(getPresenceActionChangedEventName(), listener);

    recordPresenceAction("  Esportazione CSV  ");

    expect(getCurrentPresenceActionLabel()).toBe("Esportazione CSV");
    expect(JSON.parse(sessionStorage.getItem(STORAGE_KEY)!)).toEqual({
      actionLabel: "Esportazione CSV",
      occurredAt: "2026-05-16T12:00:00.000Z",
    });
    expect(listener).toHaveBeenCalledTimes(1);
  });

  test("ignores blank labels", () => {
    recordPresenceAction("   ");
    expect(getCurrentPresenceActionLabel()).toBeNull();
    expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  test("clears stored action and dispatches change event", () => {
    sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ actionLabel: "Sync", occurredAt: new Date().toISOString() }),
    );
    const listener = vi.fn();
    window.addEventListener(getPresenceActionChangedEventName(), listener);

    clearPresenceAction();

    expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull();
    expect(getCurrentPresenceActionLabel()).toBeNull();
    expect(listener).toHaveBeenCalledTimes(1);
  });

  test("drops expired or malformed stored payloads", () => {
    sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ actionLabel: "Sync", occurredAt: "2026-05-16T11:00:00.000Z" }),
    );
    expect(getCurrentPresenceActionLabel()).toBeNull();
    expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull();

    sessionStorage.setItem(STORAGE_KEY, "{broken");
    expect(getCurrentPresenceActionLabel()).toBeNull();
    expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull();

    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ actionLabel: "", occurredAt: "2026-05-16T12:00:00.000Z" }));
    expect(getCurrentPresenceActionLabel()).toBeNull();

    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ actionLabel: "Sync", occurredAt: "invalid-date" }));
    expect(getCurrentPresenceActionLabel()).toBeNull();
    expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  test("no-ops when window is unavailable", async () => {
    vi.resetModules();
    vi.stubGlobal("window", undefined);

    const module = await import("@/lib/presence-actions");

    expect(() => module.recordPresenceAction("Sync")).not.toThrow();
    expect(() => module.clearPresenceAction()).not.toThrow();
    expect(module.getCurrentPresenceActionLabel()).toBeNull();
  });
});
