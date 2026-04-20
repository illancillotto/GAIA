"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { PropsWithChildren, type ReactNode, useEffect, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { Topbar } from "@/components/layout/topbar";
import { getCurrentUser, getDashboardSummary, getMyPermissions, isAuthError } from "@/lib/api";
import { clearStoredAccessToken, getStoredAccessToken } from "@/lib/auth";
import { hasSectionAccess } from "@/lib/section-access";
import type { CurrentUser, DashboardSummary } from "@/types/api";

export type ProtectedPageProps = PropsWithChildren<{
  title: string;
  description: string;
  breadcrumb?: string;
  topbarActions?: ReactNode;
  requiredSection?: string;
  requiredModule?: string;
  requiredRoles?: string[];
}>;

const emptySummary: DashboardSummary = {
  nas_users: 0,
  nas_groups: 0,
  shares: 0,
  reviews: 0,
  snapshots: 0,
  sync_runs: 0,
};

export function ProtectedPage({
  title,
  description,
  breadcrumb,
  topbarActions,
  requiredSection,
  requiredModule,
  requiredRoles,
  children,
}: ProtectedPageProps) {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [summary, setSummary] = useState<DashboardSummary>(emptySummary);
  const [statusMessage, setStatusMessage] = useState("Accedi per caricare dati dal backend.");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isCheckingSession, setIsCheckingSession] = useState(true);
  const [grantedSectionKeys, setGrantedSectionKeys] = useState<string[]>([]);

  useEffect(() => {
    async function loadSession() {
      const token = getStoredAccessToken();

      if (!token) {
        router.replace("/login");
        return;
      }

      try {
        const [user, dashboardSummary, permissionSummary] = await Promise.all([
          getCurrentUser(token),
          getDashboardSummary(token),
          getMyPermissions(token),
        ]);

        setCurrentUser(user);
        setSummary(dashboardSummary);
        setGrantedSectionKeys(permissionSummary.granted_keys);
        setLoadError(null);
        setStatusMessage("Sessione backend attiva.");
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore imprevisto");
        if (isAuthError(error)) {
          clearStoredAccessToken();
          setCurrentUser(null);
          setSummary(emptySummary);
          setGrantedSectionKeys([]);
          setStatusMessage("Sessione non valida.");
          router.replace("/login");
        } else {
          setStatusMessage("Backend non raggiungibile o richiesta scaduta.");
        }
      } finally {
        setIsCheckingSession(false);
      }
    }

    void loadSession();
  }, [router]);

  function handleLogout(): void {
    setCurrentUser(null);
    setLoadError(null);
    setSummary(emptySummary);
    setGrantedSectionKeys([]);
    setStatusMessage("Sessione chiusa. Effettua di nuovo il login.");
    router.replace("/login");
  }

  if (isCheckingSession || !currentUser) {
    return (
      <main className="auth-shell">
        <section className="auth-card">
          <p className="mb-2 inline-flex rounded-full bg-[#EAF3E8] px-3 py-1 text-xs font-medium text-[#1D4E35]">
            Accesso richiesto
          </p>
          <h1 className="page-heading">{title}</h1>
          <p className="mt-2 text-sm text-gray-500">{description}</p>
          <p className={`mt-4 text-sm ${loadError ? "text-red-600" : "text-gray-500"}`}>
            {loadError ?? statusMessage}
          </p>
          <Link className="btn-primary mt-6" href="/login">
            Vai al login
          </Link>
        </section>
      </main>
    );
  }

  const isSectionAllowed = requiredSection ? hasSectionAccess(grantedSectionKeys, requiredSection) : true;
  const isAdmin = currentUser.role === "admin" || currentUser.role === "super_admin";
  const isModuleAllowed = requiredModule ? isAdmin || currentUser.enabled_modules.includes(requiredModule) : true;
  const isRoleAllowed = requiredRoles ? requiredRoles.includes(currentUser.role) : true;

  if (!isSectionAllowed || !isModuleAllowed || !isRoleAllowed) {
    return (
      <AppShell
        currentUser={currentUser}
        onLogout={handleLogout}
        reviewBadge={summary.reviews}
        userBadge={summary.nas_users}
        grantedSectionKeys={grantedSectionKeys}
      >
        <Topbar pageTitle={title} breadcrumb={breadcrumb} actions={topbarActions} />
        <section className="page-body">
          <div className="mb-6">
            <h2 className="page-heading">{title}</h2>
            <p className="mt-1 text-sm text-gray-500">{description}</p>
          </div>
          <article className="panel-card">
            <p className="text-sm font-medium text-red-700">Accesso non autorizzato</p>
            <p className="mt-2 text-sm text-gray-600">
              {!isModuleAllowed
                ? "Questa sezione e disponibile solo per gli utenti abilitati al modulo richiesto."
                : requiredRoles
                ? "Questa sezione e disponibile solo per i ruoli autorizzati."
                : "Questa sezione e disponibile solo per admin, super admin o utenti esplicitamente abilitati."}
            </p>
          </article>
        </section>
      </AppShell>
    );
  }

  return (
    <AppShell
      currentUser={currentUser}
      onLogout={handleLogout}
      reviewBadge={summary.reviews}
      userBadge={summary.nas_users}
      grantedSectionKeys={grantedSectionKeys}
    >
      <Topbar pageTitle={title} breadcrumb={breadcrumb} actions={topbarActions} />
      <section className="page-body">
        <div className="mb-6">
          <h2 className="page-heading">{title}</h2>
          <p className="mt-1 text-sm text-gray-500">{description}</p>
        </div>
        <div className="page-stack">{children}</div>
      </section>
    </AppShell>
  );
}
