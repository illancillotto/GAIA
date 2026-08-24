import { beforeEach, describe, expect, test, vi } from "vitest";

import {
  clearSessionBootstrapCache,
  getSessionBootstrap,
  peekSessionBootstrap,
  SESSION_BOOTSTRAP_CACHE_TTL_MS,
} from "@/lib/session-bootstrap";

const apiMocks = vi.hoisted(() => ({
  getCurrentUser: vi.fn(),
  getMyPermissions: vi.fn(),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    getCurrentUser: apiMocks.getCurrentUser,
    getMyPermissions: apiMocks.getMyPermissions,
  };
});

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((promiseResolve, promiseReject) => {
    resolve = promiseResolve;
    reject = promiseReject;
  });
  return { promise, resolve, reject };
}

const user = {
  id: 1,
  username: "admin",
  email: "admin@example.local",
  role: "admin",
  enabled_modules: ["catasto"],
} as const;

const permissions = {
  sections: [],
  granted_keys: ["catasto.dashboard"],
};

describe("session bootstrap cache", () => {
  beforeEach(() => {
    clearSessionBootstrapCache();
    apiMocks.getCurrentUser.mockReset();
    apiMocks.getMyPermissions.mockReset();
    vi.useRealTimers();
  });

  test("loads identity and permissions once and serves the fresh cached value", async () => {
    apiMocks.getCurrentUser.mockResolvedValue(user);
    apiMocks.getMyPermissions.mockResolvedValue(permissions);

    const loaded = await getSessionBootstrap("token", { timeoutMs: 321 });
    const cached = await getSessionBootstrap("token", { timeoutMs: 654 });

    expect(loaded).toEqual({ currentUser: user, permissions });
    expect(cached).toBe(loaded);
    expect(peekSessionBootstrap("token")).toBe(loaded);
    expect(peekSessionBootstrap("another-token")).toBeNull();
    expect(apiMocks.getCurrentUser).toHaveBeenCalledTimes(1);
    expect(apiMocks.getCurrentUser).toHaveBeenCalledWith("token", { timeoutMs: 321 });
    expect(apiMocks.getMyPermissions).toHaveBeenCalledWith("token", { timeoutMs: 321 });
  });

  test("deduplicates concurrent bootstrap requests", async () => {
    const pendingUser = deferred<typeof user>();
    const pendingPermissions = deferred<typeof permissions>();
    apiMocks.getCurrentUser.mockReturnValue(pendingUser.promise);
    apiMocks.getMyPermissions.mockReturnValue(pendingPermissions.promise);

    const first = getSessionBootstrap("token");
    const second = getSessionBootstrap("token");
    expect(second).toBe(first);

    pendingUser.resolve(user);
    pendingPermissions.resolve(permissions);
    await expect(first).resolves.toEqual({ currentUser: user, permissions });
    expect(apiMocks.getCurrentUser).toHaveBeenCalledTimes(1);
    expect(apiMocks.getMyPermissions).toHaveBeenCalledTimes(1);
  });

  test("keeps stale data visible while refreshing after the ttl", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-24T10:00:00Z"));
    apiMocks.getCurrentUser.mockResolvedValueOnce(user);
    apiMocks.getMyPermissions.mockResolvedValueOnce(permissions);
    const initial = await getSessionBootstrap("token");

    const refreshedUser = { ...user, username: "updated-admin" };
    const pendingUser = deferred<typeof refreshedUser>();
    const pendingPermissions = deferred<typeof permissions>();
    apiMocks.getCurrentUser.mockReturnValueOnce(pendingUser.promise);
    apiMocks.getMyPermissions.mockReturnValueOnce(pendingPermissions.promise);
    vi.advanceTimersByTime(SESSION_BOOTSTRAP_CACHE_TTL_MS + 1);

    const refresh = getSessionBootstrap("token");
    expect(peekSessionBootstrap("token")).toBe(initial);

    pendingUser.resolve(refreshedUser);
    pendingPermissions.resolve(permissions);
    await expect(refresh).resolves.toEqual({ currentUser: refreshedUser, permissions });
    expect(peekSessionBootstrap("token")?.currentUser.username).toBe("updated-admin");
  });

  test("preserves a stale snapshot when refresh fails and can retry", async () => {
    apiMocks.getCurrentUser.mockResolvedValueOnce(user);
    apiMocks.getMyPermissions.mockResolvedValueOnce(permissions);
    const initial = await getSessionBootstrap("token");

    vi.useFakeTimers();
    vi.advanceTimersByTime(SESSION_BOOTSTRAP_CACHE_TTL_MS + 1);
    apiMocks.getCurrentUser.mockRejectedValueOnce(new Error("offline"));
    apiMocks.getMyPermissions.mockResolvedValueOnce(permissions);
    await expect(getSessionBootstrap("token")).rejects.toThrow("offline");
    expect(peekSessionBootstrap("token")).toBe(initial);

    apiMocks.getCurrentUser.mockResolvedValueOnce(user);
    apiMocks.getMyPermissions.mockResolvedValueOnce(permissions);
    await expect(getSessionBootstrap("token")).resolves.toEqual(initial);
    expect(apiMocks.getCurrentUser).toHaveBeenCalledTimes(3);
  });

  test("does not let an older token request replace the active token cache", async () => {
    const firstUser = deferred<typeof user>();
    const firstPermissions = deferred<typeof permissions>();
    apiMocks.getCurrentUser.mockReturnValueOnce(firstUser.promise).mockResolvedValueOnce(user);
    apiMocks.getMyPermissions.mockReturnValueOnce(firstPermissions.promise).mockResolvedValueOnce(permissions);

    const oldRequest = getSessionBootstrap("old-token");
    const active = await getSessionBootstrap("active-token");
    firstUser.resolve({ ...user, username: "old-admin" });
    firstPermissions.resolve(permissions);
    await oldRequest;

    expect(peekSessionBootstrap("active-token")).toBe(active);
    expect(peekSessionBootstrap("old-token")).toBeNull();
  });

  test("does not let an older failed request clear the active token cache", async () => {
    const firstUser = deferred<typeof user>();
    apiMocks.getCurrentUser.mockReturnValueOnce(firstUser.promise).mockResolvedValueOnce(user);
    apiMocks.getMyPermissions.mockResolvedValue(permissions);

    const oldRequest = getSessionBootstrap("old-token");
    const active = await getSessionBootstrap("active-token");
    firstUser.reject(new Error("old request failed"));
    await expect(oldRequest).rejects.toThrow("old request failed");

    expect(peekSessionBootstrap("active-token")).toBe(active);
  });

  test("clears only the requested token or the whole cache", async () => {
    apiMocks.getCurrentUser.mockResolvedValue(user);
    apiMocks.getMyPermissions.mockResolvedValue(permissions);
    await getSessionBootstrap("token");

    clearSessionBootstrapCache("another-token");
    expect(peekSessionBootstrap("token")).not.toBeNull();
    clearSessionBootstrapCache("token");
    expect(peekSessionBootstrap("token")).toBeNull();

    await getSessionBootstrap("token");
    clearSessionBootstrapCache();
    expect(peekSessionBootstrap("token")).toBeNull();
  });
});
