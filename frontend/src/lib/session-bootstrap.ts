import {
  getCurrentUser,
  getMyPermissions,
  SESSION_BOOTSTRAP_TIMEOUT_MS,
} from "@/lib/api";
import type { CurrentUser, MyPermissionsResponse } from "@/types/api";

export const SESSION_BOOTSTRAP_CACHE_TTL_MS = 60_000;

export type SessionBootstrap = {
  currentUser: CurrentUser;
  permissions: MyPermissionsResponse;
};

type SessionBootstrapCacheEntry = {
  token: string;
  value: SessionBootstrap | null;
  expiresAt: number;
  promise: Promise<SessionBootstrap> | null;
};

let cacheEntry: SessionBootstrapCacheEntry | null = null;

function matchingEntry(token: string): SessionBootstrapCacheEntry | null {
  return cacheEntry?.token === token ? cacheEntry : null;
}

function requestSessionBootstrap(
  token: string,
  timeoutMs: number,
  previousValue: SessionBootstrap | null,
): Promise<SessionBootstrap> {
  const promise = Promise.all([
    getCurrentUser(token, { timeoutMs }),
    getMyPermissions(token, { timeoutMs }),
  ]).then(([currentUser, permissions]) => ({ currentUser, permissions }));
  const pendingEntry: SessionBootstrapCacheEntry = {
    token,
    value: previousValue,
    expiresAt: 0,
    promise,
  };

  cacheEntry = pendingEntry;
  void promise.then(
    (value) => {
      if (cacheEntry === pendingEntry) {
        cacheEntry = {
          token,
          value,
          expiresAt: Date.now() + SESSION_BOOTSTRAP_CACHE_TTL_MS,
          promise: null,
        };
      }
    },
    () => {
      if (cacheEntry === pendingEntry) {
        cacheEntry = { ...pendingEntry, promise: null };
      }
    },
  );

  return promise;
}

export function peekSessionBootstrap(token: string): SessionBootstrap | null {
  return matchingEntry(token)?.value ?? null;
}

export function getSessionBootstrap(
  token: string,
  options: { timeoutMs?: number } = {},
): Promise<SessionBootstrap> {
  const existingEntry = matchingEntry(token);

  if (existingEntry?.promise) {
    return existingEntry.promise;
  }
  if (existingEntry?.value && existingEntry.expiresAt > Date.now()) {
    return Promise.resolve(existingEntry.value);
  }

  return requestSessionBootstrap(
    token,
    options.timeoutMs ?? SESSION_BOOTSTRAP_TIMEOUT_MS,
    existingEntry?.value ?? null,
  );
}

export function clearSessionBootstrapCache(token?: string): void {
  if (token && cacheEntry?.token !== token) {
    return;
  }
  cacheEntry = null;
}
