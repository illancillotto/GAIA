"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { Topbar } from "@/components/layout/topbar";
import { clearStoredAccessToken, getStoredAccessToken } from "@/lib/auth";
import { getCurrentUser, getMyPermissions, isAuthError } from "@/lib/api";
import type { CurrentUser } from "@/types/api";

type NetworkModulePageProps = {
  title: string;
  description: string;
  breadcrumb?: string;
  actions?: ReactNode;
  children: (context: { token: string; currentUser: CurrentUser; grantedSectionKeys: string[] }) => ReactNode;
};

export function NetworkModulePage({
  title,
  description,
  breadcrumb,
  actions,
  children,
}: NetworkModulePageProps) {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [grantedSectionKeys, setGrantedSectionKeys] = useState<string[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isCheckingSession, setIsCheckingSession] = useState(true);

  useEffect(() => {
    async function loadSession() {
      const accessToken = getStoredAccessToken();

      if (!accessToken) {
        router.replace("/login");
        return;
      }

      try {
        const [user, permissionSummary] = await Promise.all([
          getCurrentUser(accessToken),
          getMyPermissions(accessToken),
        ]);
        setToken(accessToken);
        setCurrentUser(user);
        setGrantedSectionKeys(permissionSummary.granted_keys);
        setLoadError(null);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore imprevisto");
        if (isAuthError(error)) {
          clearStoredAccessToken();
          setCurrentUser(null);
          setGrantedSectionKeys([]);
          router.replace("/login");
        }
      } finally {
        setIsCheckingSession(false);
      }
    }

    void loadSession();
  }, [router]);

  function handleLogout(): void {
    clearStoredAccessToken();
    setToken(null);
    setCurrentUser(null);
    setGrantedSectionKeys([]);
    router.replace("/login");
  }

  if (isCheckingSession || !currentUser || !token) {
    return (
      <main className="auth-shell">
        <section className="auth-card">
          <p className="mb-2 inline-flex rounded-full bg-[#EAF3E8] px-3 py-1 text-xs font-medium text-[#1D4E35]">
            Accesso richiesto
          </p>
          <h1 className="page-heading">{title}</h1>
          <p className="mt-2 text-sm text-gray-500">{description}</p>
          <p className={`mt-4 text-sm ${loadError ? "text-red-600" : "text-gray-500"}`}>
            {loadError ?? "Controllo credenziali locali e modulo GAIA Rete."}
          </p>
          <Link className="btn-primary mt-6" href="/login">
            Vai al login
          </Link>
        </section>
      </main>
    );
  }

  if (!currentUser.enabled_modules.includes("rete")) {
    return (
      <AppShell currentUser={currentUser} onLogout={handleLogout} grantedSectionKeys={grantedSectionKeys}>
        <Topbar pageTitle={title} breadcrumb={breadcrumb} actions={actions} />
        <section className="page-body">
          <div className="mb-6">
            <h2 className="page-heading">{title}</h2>
            <p className="mt-1 text-sm text-gray-500">{description}</p>
          </div>
          <article className="panel-card">
            <p className="text-sm font-medium text-red-700">Accesso non autorizzato</p>
            <p className="mt-2 text-sm text-gray-600">
              Il tuo account non ha il modulo GAIA Rete abilitato.
            </p>
          </article>
        </section>
      </AppShell>
    );
  }

  return (
    <AppShell currentUser={currentUser} onLogout={handleLogout} grantedSectionKeys={grantedSectionKeys}>
      <Topbar pageTitle={title} breadcrumb={breadcrumb} actions={actions} />
      <section className="page-body">
        <div className="mb-6">
          <h2 className="page-heading">{title}</h2>
          <p className="mt-1 text-sm text-gray-500">{description}</p>
        </div>
        <div className="page-stack">{children({ token, currentUser, grantedSectionKeys })}</div>
      </section>
    </AppShell>
  );
}
