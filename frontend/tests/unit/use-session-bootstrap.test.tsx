import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import {
  clearSessionBootstrapCache,
  getSessionBootstrap,
  SESSION_BOOTSTRAP_CACHE_TTL_MS,
} from "@/lib/session-bootstrap";
import { useSessionBootstrap } from "@/lib/use-session-bootstrap";
import type { CurrentUser, MyPermissionsResponse } from "@/types/api";

const mocks = vi.hoisted(() => {
  const replace = vi.fn();
  return {
    replace,
    router: { replace },
    getStoredAccessToken: vi.fn(),
    clearStoredAccessToken: vi.fn(),
    getCurrentUser: vi.fn(),
    getMyPermissions: vi.fn(),
    isAuthError: vi.fn(),
  };
});

vi.mock("next/navigation", () => ({
  useRouter: () => mocks.router,
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
  clearStoredAccessToken: mocks.clearStoredAccessToken,
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    getCurrentUser: mocks.getCurrentUser,
    getMyPermissions: mocks.getMyPermissions,
    isAuthError: mocks.isAuthError,
  };
});

const user: CurrentUser = {
  id: 1,
  username: "admin",
  email: "admin@example.local",
  role: "admin",
  is_active: true,
  module_accessi: true,
  module_rete: true,
  module_inventario: false,
  module_catasto: true,
  module_utenze: false,
  module_operazioni: false,
  module_riordino: false,
  module_ruolo: false,
  module_presenze: false,
  enabled_modules: ["accessi", "catasto"],
};

const permissions: MyPermissionsResponse = {
  sections: [],
  granted_keys: ["catasto.dashboard"],
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((promiseResolve, promiseReject) => {
    resolve = promiseResolve;
    reject = promiseReject;
  });
  return { promise, resolve, reject };
}

describe("useSessionBootstrap", () => {
  beforeEach(() => {
    clearSessionBootstrapCache();
    vi.useRealTimers();
    mocks.replace.mockReset();
    mocks.getStoredAccessToken.mockReset();
    mocks.clearStoredAccessToken.mockReset();
    mocks.getCurrentUser.mockReset();
    mocks.getMyPermissions.mockReset();
    mocks.isAuthError.mockReset();
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.getCurrentUser.mockResolvedValue(user);
    mocks.getMyPermissions.mockResolvedValue(permissions);
    mocks.isAuthError.mockReturnValue(false);
  });

  test("loads the session and clears it on logout", async () => {
    const { result } = renderHook(() => useSessionBootstrap());

    await waitFor(() => expect(result.current.status).toBe("ready"));
    expect(result.current.currentUser).toEqual(user);
    expect(result.current.grantedSectionKeys).toEqual(["catasto.dashboard"]);

    act(() => result.current.logout());
    expect(result.current.status).toBe("anonymous");
    expect(mocks.clearStoredAccessToken).toHaveBeenCalled();
    expect(mocks.replace).toHaveBeenCalledWith("/login");
  });

  test("redirects when there is no token and supports logout from anonymous state", async () => {
    mocks.getStoredAccessToken.mockReturnValue(null);
    const { result } = renderHook(() => useSessionBootstrap());

    await waitFor(() => expect(result.current.status).toBe("anonymous"));
    expect(result.current.error).toBe("Accesso richiesto. Effettua il login.");
    expect(result.current.currentUser).toBeNull();
    expect(result.current.grantedSectionKeys).toEqual([]);

    act(() => result.current.logout());
    expect(mocks.clearStoredAccessToken).toHaveBeenCalled();
  });

  test("clears an invalid token after an authentication error", async () => {
    const authError = new Error("session expired");
    mocks.getCurrentUser.mockRejectedValue(authError);
    mocks.isAuthError.mockReturnValue(true);
    const { result } = renderHook(() => useSessionBootstrap());

    await waitFor(() => expect(result.current.status).toBe("anonymous"));
    expect(result.current.error).toBe("session expired");
    expect(mocks.clearStoredAccessToken).toHaveBeenCalled();
    expect(mocks.replace).toHaveBeenCalledWith("/login");
  });

  test("reports an unexpected backend failure without clearing the token", async () => {
    mocks.getCurrentUser.mockRejectedValue("offline");
    const { result } = renderHook(() => useSessionBootstrap());

    await waitFor(() => expect(result.current.status).toBe("error"));
    expect(result.current.error).toBe("Errore imprevisto");
    expect(mocks.clearStoredAccessToken).not.toHaveBeenCalled();
  });

  test("keeps a stale session ready when background revalidation fails", async () => {
    const now = vi.spyOn(Date, "now").mockReturnValue(1_000);
    await getSessionBootstrap("token");
    now.mockReturnValue(1_000 + SESSION_BOOTSTRAP_CACHE_TTL_MS + 1);
    mocks.getCurrentUser.mockRejectedValueOnce(new Error("temporarily offline"));

    const { result } = renderHook(() => useSessionBootstrap());
    await waitFor(() => expect(result.current.error).toBe("temporarily offline"));

    expect(result.current.status).toBe("ready");
    expect(result.current.currentUser).toEqual(user);
    now.mockRestore();
  });

  test("does not update state when verification resolves after unmount", async () => {
    const pendingUser = deferred<CurrentUser>();
    const pendingPermissions = deferred<MyPermissionsResponse>();
    mocks.getCurrentUser.mockReturnValue(pendingUser.promise);
    mocks.getMyPermissions.mockReturnValue(pendingPermissions.promise);
    const { unmount } = renderHook(() => useSessionBootstrap());
    unmount();

    pendingUser.resolve(user);
    pendingPermissions.resolve(permissions);
    await act(async () => {});
  });

  test("does not handle a verification failure after unmount", async () => {
    const pendingUser = deferred<CurrentUser>();
    mocks.getCurrentUser.mockReturnValue(pendingUser.promise);
    const { unmount } = renderHook(() => useSessionBootstrap());
    unmount();

    pendingUser.reject(new Error("late failure"));
    await act(async () => {});
    expect(mocks.clearStoredAccessToken).not.toHaveBeenCalled();
  });
});
