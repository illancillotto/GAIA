import { afterEach, describe, expect, test, vi } from "vitest";

import {
  clearStoredAccessToken,
  getStoredAccessToken,
  setStoredAccessToken,
} from "@/lib/auth";

const ACCESS_TOKEN_KEY = "gaia.access_token";

describe("auth token storage", () => {
  afterEach(() => {
    localStorage.clear();
    vi.unstubAllGlobals();
  });

  test("stores and reads access tokens", () => {
    setStoredAccessToken("token-123");
    expect(getStoredAccessToken()).toBe("token-123");
  });

  test("clears stored access tokens", () => {
    localStorage.setItem(ACCESS_TOKEN_KEY, "token-123");
    clearStoredAccessToken();
    expect(getStoredAccessToken()).toBeNull();
  });

  test("no-ops when window is unavailable", async () => {
    vi.resetModules();
    vi.stubGlobal("window", undefined);

    const module = await import("@/lib/auth");

    expect(module.getStoredAccessToken()).toBeNull();
    expect(() => module.setStoredAccessToken("token-123")).not.toThrow();
    expect(() => module.clearStoredAccessToken()).not.toThrow();
  });
});
