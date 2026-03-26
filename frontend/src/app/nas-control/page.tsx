"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { Topbar } from "@/components/layout/topbar";
import { AlertBanner } from "@/components/ui/alert-banner";
import { MetricCard } from "@/components/ui/metric-card";
import { SyncButton } from "@/components/ui/sync-button";
import { AlertTriangleIcon, ChevronRightIcon, FolderIcon, SearchIcon, UserIcon } from "@/components/ui/icons";
import {
  getCurrentUser,
  getDashboardSummary,
  getEffectivePermissions,
  getMyPermissions,
  getNasUsersForUsersSection,
  getShares,
  isAuthError,
} from "@/lib/api";
import { clearStoredAccessToken, getStoredAccessToken } from "@/lib/auth";
import { hasSectionAccess } from "@/lib/section-access";
import type { CurrentUser, DashboardSummary, EffectivePermission, NasUser, Share } from "@/types/api";

const emptySummary: DashboardSummary = {
  nas_users: 0,
  nas_groups: 0,
  shares: 0,
  reviews: 0,
  snapshots: 0,
  sync_runs: 0,
};

export default function AccessiPage() {
  const router = useRouter();
  const [summary, setSummary] = useState<DashboardSummary>(emptySummary);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [users, setUsers] = useState<NasUser[]>([]);
  const [shares, setShares] = useState<Share[]>([]);
  const [permissions, setPermissions] = useState<EffectivePermission[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isCheckingSession, setIsCheckingSession] = useState(true);
  const [grantedSectionKeys, setGrantedSectionKeys] = useState<string[]>([]);

  useEffect(() => {
    async function loadDashboard() {
      const token = getStoredAccessToken();

      if (!token) {
        router.replace("/login");
        return;
      }

      try {
        const [user, dashboardSummary, permissionSummary, shareItems, permissionItems] = await Promise.all([
          getCurrentUser(token),
          getDashboardSummary(token),
          getMyPermissions(token),
          getShares(token),
          getEffectivePermissions(token),
        ]);
        const canAccessUsersSection = hasSectionAccess(permissionSummary.granted_keys, "accessi.users");
        const nasUsers = canAccessUsersSection ? await getNasUsersForUsersSection(token) : [];

        setCurrentUser(user);
        setSummary(dashboardSummary);
        setGrantedSectionKeys(permissionSummary.granted_keys);
        setUsers(nasUsers);
        setShares(shareItems);
        setPermissions(permissionItems);
        setLoadError(null);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore imprevisto");
        if (isAuthError(error)) {
          clearStoredAccessToken();
          setCurrentUser(null);
          setSummary(emptySummary);
          setGrantedSectionKeys([]);
          router.replace("/login");
        }
      } finally {
        setIsCheckingSession(false);
      }
    }

    void loadDashboard();
  }, [router]);

  function handleLogout(): void {
    setCurrentUser(null);
    setSummary(emptySummary);
    setGrantedSectionKeys([]);
    router.replace("/login");
  }

  const recentUsers = useMemo(
    () =>
      [...users]
        .sort((left, right) => right.id - left.id)
        .slice(0, 5),
    [users],
  );

  const recentShares = useMemo(
    () =>
      [...shares]
        .sort((left, right) => left.name.localeCompare(right.name, "it"))
        .slice(0, 5),
    [shares],
  );

  const recentRootSharesWithUsers = useMemo(() => {
    const shareMap = new Map(shares.map((share) => [share.id, share]));
    const userMap = new Map(users.map((user) => [user.id, user]));

    return [...shares]
      .filter((share) => share.parent_id == null)
      .sort((left, right) => left.name.localeCompare(right.name, "it"))
      .slice(0, 6)
      .map((share) => {
        const accessibleUsers = Array.from(
          new Set(
            permissions
              .filter((permission) => {
                const permissionShare = shareMap.get(permission.share_id);

                if (!permissionShare) {
                  return false;
                }

                const isOnBranch =
                  permissionShare.id === share.id ||
                  permissionShare.path.startsWith(`${share.path}/`);

                if (!isOnBranch) {
                  return false;
                }

                return permission.can_read || permission.can_write;
              })
              .map((permission) => userMap.get(permission.nas_user_id)?.username)
              .filter((username): username is string => Boolean(username)),
          ),
        ).sort((left, right) => left.localeCompare(right, "it"));

        return {
          share,
          accessibleUsers,
        };
      });
  }, [permissions, shares, users]);
  const deniedCount = permissions.filter((item) => item.is_denied).length;
  const canAccessUsersSection = hasSectionAccess(grantedSectionKeys, "accessi.users");

  if (isCheckingSession || !currentUser) {
    return (
      <main className="auth-shell">
        <section className="auth-card">
          <p className="mb-2 inline-flex rounded-full bg-[#EAF3E8] px-3 py-1 text-xs font-medium text-[#1D4E35]">
            Reindirizzamento
          </p>
          <h1 className="page-heading">Verifica sessione</h1>
          <p className="mt-2 text-sm text-gray-500">
            Controllo credenziali locali e connessione al backend.
          </p>
          <p className={`mt-4 text-sm ${loadError ? "text-red-600" : "text-gray-500"}`}>
            {loadError ?? "Accedi per caricare i dati reali dal backend."}
          </p>
          <Link className="btn-primary mt-6" href="/login">
            Vai al login
          </Link>
        </section>
      </main>
    );
  }

  const hasNasModule = currentUser.enabled_modules.includes("accessi");

  if (!hasNasModule) {
    return (
      <AppShell
        currentUser={currentUser}
        onLogout={handleLogout}
        reviewBadge={summary.reviews}
        userBadge={summary.nas_users}
        grantedSectionKeys={grantedSectionKeys}
      >
        <Topbar pageTitle="Dashboard" />
        <section className="page-body">
          <article className="panel-card">
            <p className="text-sm font-medium text-red-700">Accesso non autorizzato</p>
            <p className="mt-2 text-sm text-gray-600">
              Il tuo account non ha il modulo NAS Control abilitato.
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
      <Topbar
        pageTitle="Dashboard"
        actions={<SyncButton label="Apri Sync" onClick={() => router.push("/nas-control/sync")} />}
      />

      <section className="page-body">
        <div className="page-stack">
          {summary.reviews > 0 ? (
            <AlertBanner
              icon={<AlertTriangleIcon className="h-4 w-4" />}
              title={`${summary.reviews} review in attesa`}
              action={
                <Link
                  href="/nas-control/reviews"
                  className="rounded-md bg-amber-100 px-3 py-1.5 text-xs font-medium text-amber-700 transition hover:bg-amber-200"
                >
                  Vai alle review
                </Link>
              }
            >
              Permessi da validare dai responsabili di settore. Lo stato corrente e pronto per il triage operativo.
            </AlertBanner>
          ) : null}

          <div>
            <h2 className="page-heading">Controllo centralizzato NAS</h2>
            <p className="mt-1 text-sm text-gray-500">
              Vista sintetica di utenti, cartelle condivise, permessi effettivi e review aperte.
            </p>
          </div>

          <div className="surface-grid">
            <MetricCard label="Utenti NAS" value={summary.nas_users} sub="Utenti sincronizzati dal dominio audit" />
            <MetricCard label="Cartelle" value={summary.shares} sub="Share presenti nell’ultimo snapshot" />
            <MetricCard label="Permessi calcolati" value={permissions.length} sub="Permessi effettivi persistiti" variant="success" />
            <MetricCard label="Permessi negati" value={deniedCount} sub="Regole con deny attivo" variant={deniedCount > 0 ? "danger" : "default"} />
          </div>

          <p className="text-sm text-gray-500">
            Gli snapshot mostrati in GAIA sono snapshot interni della piattaforma, generati durante la sincronizzazione, non snapshot nativi del NAS Synology.
          </p>

          <div className="grid gap-6 xl:grid-cols-2">
            <article className="panel-card">
              <div className="mb-4 flex items-center justify-between gap-3">
                <div>
                  <p className="section-title">Utenti recenti con accesso</p>
                  <p className="section-copy">Ultimi utenti presenti nel dominio sincronizzato.</p>
                </div>
                {canAccessUsersSection ? (
                  <Link href="/nas-control/users" className="text-sm font-medium text-[#1D4E35]">
                    Tutti gli utenti
                  </Link>
                ) : (
                  <span className="text-sm font-medium text-gray-400">Accesso riservato</span>
                )}
              </div>
              <div className="space-y-3">
                {canAccessUsersSection ? (
                  recentUsers.map((user) => (
                    <Link
                      key={user.id}
                      href={`/nas-control/users/${user.id}`}
                      className="flex items-center gap-3 rounded-lg border border-gray-100 px-3 py-3 transition hover:border-gray-200 hover:bg-gray-50"
                    >
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#D3EAD4] text-[#1D4E35]">
                        <UserIcon className="h-5 w-5" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-gray-900">{user.username}</p>
                        <p className="truncate text-xs text-gray-400">{user.full_name ?? "Nome non disponibile"}</p>
                      </div>
                      <ChevronRightIcon className="h-4 w-4 text-gray-300" />
                    </Link>
                  ))
                ) : (
                  <div className="rounded-lg border border-dashed border-gray-200 px-3 py-4 text-sm text-gray-500">
                    La sezione utenti e visibile solo per admin, super admin o utenti abilitati.
                  </div>
                )}
              </div>
            </article>

            <article className="panel-card">
              <div className="mb-4 flex items-center justify-between gap-3">
                <div>
                  <p className="section-title">Cartelle condivise</p>
                  <p className="section-copy">Share pronte per verifica permessi e review.</p>
                </div>
                <Link href="/nas-control/shares" className="text-sm font-medium text-[#1D4E35]">
                  Tutte le cartelle
                </Link>
              </div>
              <div className="space-y-3">
                {recentShares.map((share) => (
                  <Link
                    key={share.id}
                    href={`/nas-control/shares/${share.id}`}
                    className="flex items-center gap-3 rounded-lg border border-gray-100 px-3 py-3 transition hover:border-gray-200 hover:bg-gray-50"
                  >
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#D3EAD4] text-[#1D4E35]">
                      <FolderIcon className="h-5 w-5" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-gray-900">{share.name}</p>
                      <p className="truncate text-xs text-gray-400">{share.path}</p>
                    </div>
                    <ChevronRightIcon className="h-4 w-4 text-gray-300" />
                  </Link>
                ))}
              </div>
            </article>
          </div>

          <article className="panel-card">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <p className="section-title">Cartelle principali e utenti con accesso</p>
                <p className="section-copy">Share root dell’ultimo snapshot con utenti che possono accedere al ramo.</p>
              </div>
              <Link href="/nas-control/effective-permissions" className="text-sm font-medium text-[#1D4E35]">
                Apri vista completa
              </Link>
            </div>

            {recentRootSharesWithUsers.length === 0 ? (
              <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 p-8 text-center">
                <SearchIcon className="mx-auto h-5 w-5 text-gray-300" />
                <p className="mt-3 text-sm font-medium text-gray-900">Nessuna cartella disponibile</p>
                <p className="mt-1 text-sm text-gray-500">Esegui una sincronizzazione per popolare l’ultimo snapshot.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {recentRootSharesWithUsers.map(({ share, accessibleUsers }) => (
                  <div key={share.id} className="rounded-xl border border-gray-100 bg-white px-4 py-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-gray-900">{share.name}</p>
                        <p className="truncate text-xs text-gray-400">{share.path}</p>
                      </div>
                      <Link href={`/nas-control/shares/${share.id}`} className="text-sm font-medium text-[#1D4E35]">
                        Apri
                      </Link>
                    </div>

                    <div className="mt-3 flex flex-wrap gap-2">
                      {accessibleUsers.length > 0 ? (
                        accessibleUsers.slice(0, 8).map((username) => (
                          <span
                            key={`${share.id}-${username}`}
                            className="inline-flex items-center rounded-full bg-[#EAF3E8] px-2.5 py-1 text-xs font-medium text-[#1D4E35]"
                          >
                            {username}
                          </span>
                        ))
                      ) : (
                        <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-500">
                          Nessun accesso rilevato
                        </span>
                      )}
                      {accessibleUsers.length > 8 ? (
                        <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-500">
                          +{accessibleUsers.length - 8} altri
                        </span>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </article>
        </div>
      </section>
    </AppShell>
  );
}
