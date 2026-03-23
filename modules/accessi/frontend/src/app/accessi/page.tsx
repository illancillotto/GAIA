"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { Topbar } from "@/components/layout/topbar";
import { AlertBanner } from "@/components/ui/alert-banner";
import { MetricCard } from "@/components/ui/metric-card";
import { PermissionBadge } from "@/components/ui/permission-badge";
import { SourceTag } from "@/components/ui/source-tag";
import { SyncButton } from "@/components/ui/sync-button";
import { AlertTriangleIcon, ChevronRightIcon, FolderIcon, SearchIcon, UserIcon } from "@/components/ui/icons";
import {
  getCurrentUser,
  getDashboardSummary,
  getEffectivePermissions,
  getNasUsers,
  getShares,
} from "@/lib/api";
import { clearStoredAccessToken, getStoredAccessToken } from "@/lib/auth";
import { getPermissionLevel } from "@/lib/presentation";
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

  useEffect(() => {
    async function loadDashboard() {
      const token = getStoredAccessToken();

      if (!token) {
        router.replace("/login");
        return;
      }

      try {
        const [user, dashboardSummary, nasUsers, shareItems, permissionItems] = await Promise.all([
          getCurrentUser(token),
          getDashboardSummary(token),
          getNasUsers(token),
          getShares(token),
          getEffectivePermissions(token),
        ]);

        setCurrentUser(user);
        setSummary(dashboardSummary);
        setUsers(nasUsers);
        setShares(shareItems);
        setPermissions(permissionItems);
        setLoadError(null);
      } catch (error) {
        clearStoredAccessToken();
        setCurrentUser(null);
        setSummary(emptySummary);
        setLoadError(error instanceof Error ? error.message : "Errore imprevisto");
        router.replace("/login");
      } finally {
        setIsCheckingSession(false);
      }
    }

    void loadDashboard();
  }, [router]);

  function handleLogout(): void {
    setCurrentUser(null);
    setSummary(emptySummary);
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

  const latestPermissions = useMemo(() => permissions.slice(0, 8), [permissions]);
  const deniedCount = permissions.filter((item) => item.is_denied).length;

  function getUserLabel(userId: number): string {
    return users.find((user) => user.id === userId)?.username ?? String(userId);
  }

  function getShareLabel(shareId: number): string {
    return shares.find((share) => share.id === shareId)?.name ?? String(shareId);
  }

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

  return (
    <AppShell
      currentUser={currentUser}
      onLogout={handleLogout}
      reviewBadge={summary.reviews}
      userBadge={summary.nas_users}
    >
      <Topbar
        pageTitle="Dashboard"
        actions={<SyncButton label="Apri Sync" onClick={() => router.push("/sync")} />}
      />

      <section className="page-body">
        <div className="page-stack">
          {summary.reviews > 0 ? (
            <AlertBanner
              icon={<AlertTriangleIcon className="h-4 w-4" />}
              title={`${summary.reviews} review in attesa`}
              action={
                <Link
                  href="/reviews"
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
            <h2 className="page-heading">Controllo centralizzato degli accessi NAS</h2>
            <p className="mt-1 text-sm text-gray-500">
              Vista sintetica di utenti, cartelle condivise, permessi effettivi e review aperte.
            </p>
          </div>

          <div className="surface-grid">
            <MetricCard label="Utenti NAS" value={summary.nas_users} sub="Utenti sincronizzati dal dominio audit" />
            <MetricCard label="Cartelle" value={summary.shares} sub="Share presenti nell’ultimo snapshot" />
            <MetricCard label="Permessi calcolati" value={permissions.length} sub="Permessi effettivi persistiti" variant="success" />
            <MetricCard label="Accessi negati" value={deniedCount} sub="Regole con deny attivo" variant={deniedCount > 0 ? "danger" : "default"} />
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <article className="panel-card">
              <div className="mb-4 flex items-center justify-between gap-3">
                <div>
                  <p className="section-title">Utenti recenti con accesso</p>
                  <p className="section-copy">Ultimi utenti presenti nel dominio sincronizzato.</p>
                </div>
                <Link href="/users" className="text-sm font-medium text-[#1D4E35]">
                  Tutti gli utenti
                </Link>
              </div>
              <div className="space-y-3">
                {recentUsers.map((user) => (
                  <Link
                    key={user.id}
                    href={`/users/${user.id}`}
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
                ))}
              </div>
            </article>

            <article className="panel-card">
              <div className="mb-4 flex items-center justify-between gap-3">
                <div>
                  <p className="section-title">Cartelle condivise</p>
                  <p className="section-copy">Share pronte per verifica permessi e review.</p>
                </div>
                <Link href="/shares" className="text-sm font-medium text-[#1D4E35]">
                  Tutte le cartelle
                </Link>
              </div>
              <div className="space-y-3">
                {recentShares.map((share) => (
                  <Link
                    key={share.id}
                    href={`/shares/${share.id}`}
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
                <p className="section-title">Permessi effettivi recenti</p>
                <p className="section-copy">Estratto dell’ultimo snapshot persistito.</p>
              </div>
              <Link href="/effective-permissions" className="text-sm font-medium text-[#1D4E35]">
                Apri vista completa
              </Link>
            </div>

            {latestPermissions.length === 0 ? (
              <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 p-8 text-center">
                <SearchIcon className="mx-auto h-5 w-5 text-gray-300" />
                <p className="mt-3 text-sm font-medium text-gray-900">Nessun permesso disponibile</p>
                <p className="mt-1 text-sm text-gray-500">Esegui una sincronizzazione per popolare l’ultimo snapshot.</p>
              </div>
            ) : (
              <div className="overflow-hidden rounded-xl border border-gray-100">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Utente</th>
                      <th>Cartella</th>
                      <th>Permesso</th>
                      <th>Origine</th>
                    </tr>
                  </thead>
                  <tbody>
                    {latestPermissions.map((permission) => (
                      <tr key={permission.id}>
                        <td>{getUserLabel(permission.nas_user_id)}</td>
                        <td>{getShareLabel(permission.share_id)}</td>
                        <td>
                          <PermissionBadge level={getPermissionLevel(permission)} />
                        </td>
                        <td>
                          <SourceTag source={permission.source_summary} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </article>
        </div>
      </section>
    </AppShell>
  );
}
