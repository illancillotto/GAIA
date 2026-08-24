"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { isAuthError, SESSION_BOOTSTRAP_TIMEOUT_MS } from "@/lib/api";
import { clearStoredAccessToken, getStoredAccessToken } from "@/lib/auth";
import {
  clearSessionBootstrapCache,
  getSessionBootstrap,
  peekSessionBootstrap,
  type SessionBootstrap,
} from "@/lib/session-bootstrap";

type SessionStatus = "checking" | "ready" | "anonymous" | "error";

type SessionState = {
  token: string | null;
  session: SessionBootstrap | null;
  status: SessionStatus;
  error: string | null;
};

function initialSessionState(): SessionState {
  const token = getStoredAccessToken();
  const session = token ? peekSessionBootstrap(token) : null;
  return {
    token,
    session,
    status: session ? "ready" : "checking",
    error: null,
  };
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Errore imprevisto";
}

export function useSessionBootstrap() {
  const router = useRouter();
  const [state, setState] = useState(initialSessionState);

  useEffect(() => {
    let isActive = true;

    async function verifySession() {
      const token = getStoredAccessToken();
      if (!token) {
        setState({ token: null, session: null, status: "anonymous", error: "Accesso richiesto. Effettua il login." });
        router.replace("/login");
        return;
      }

      try {
        const session = await getSessionBootstrap(token, { timeoutMs: SESSION_BOOTSTRAP_TIMEOUT_MS });
        if (isActive) {
          setState({ token, session, status: "ready", error: null });
        }
      } catch (error) {
        if (!isActive) {
          return;
        }
        if (isAuthError(error)) {
          clearSessionBootstrapCache(token);
          clearStoredAccessToken();
          setState({ token: null, session: null, status: "anonymous", error: errorMessage(error) });
          router.replace("/login");
          return;
        }

        const staleSession = peekSessionBootstrap(token);
        setState({
          token,
          session: staleSession,
          status: staleSession ? "ready" : "error",
          error: errorMessage(error),
        });
      }
    }

    void verifySession();
    function deactivateSessionVerification(): void {
      isActive = false;
    }
    return deactivateSessionVerification;
  }, [router]);

  function logout(): void {
    clearSessionBootstrapCache(state.token ?? undefined);
    clearStoredAccessToken();
    setState({ token: null, session: null, status: "anonymous", error: null });
    router.replace("/login");
  }

  return {
    token: state.token,
    currentUser: state.session?.currentUser ?? null,
    grantedSectionKeys: state.session?.permissions.granted_keys ?? [],
    status: state.status,
    error: state.error,
    logout,
  };
}
