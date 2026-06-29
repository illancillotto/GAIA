"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import { ProtectedPage } from "@/components/app/protected-page";
import { getPresenceSummary } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { UserPresenceSummary, UserPresenceSummaryItem } from "@/types/api";

const emptySummary: UserPresenceSummary = {
  window_minutes: 15,
  active_users: 0,
  visible_users: 0,
  items: [],
  by_module: [],
};

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("it-IT", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatRelativeLabel(minutes: number): string {
  if (minutes <= 0) return "adesso";
  if (minutes === 1) return "1 min fa";
  return `${minutes} min fa`;
}

function normalizeInternalPath(path: string): string {
  if (!path.startsWith("/")) {
    return "/";
  }
  return path;
}

function canOpenOperazioniDetail(item: UserPresenceSummaryItem): boolean {
  return item.module_key === "operazioni";
}

export default function GaiaUsersActivityPage() {
  const [summary, setSummary] = useState<UserPresenceSummary>(emptySummary);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [moduleFilter, setModuleFilter] = useState("all");
  const [routeFilter, setRouteFilter] = useState("all");
  const [visibilityFilter, setVisibilityFilter] = useState("all");

  async function loadSummary() {
    const token = getStoredAccessToken();
    if (!token) {
      setIsLoading(false);
      return;
    }

    try {
      const payload = await getPresenceSummary(token, { windowMinutes: 15 });
      setSummary(payload);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento attività utenti");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    let cancelled = false;

    const guardedLoadSummary = async () => {
      if (cancelled) return;
      await loadSummary();
    };

    void guardedLoadSummary();
    const intervalId = window.setInterval(() => void guardedLoadSummary(), 60_000);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

  const moduleOptions = useMemo(
    () => [
      { value: "all", label: "Tutti i moduli" },
      ...summary.by_module.map((bucket) => ({
        value: bucket.module_key,
        label: `${bucket.module_key} (${bucket.count})`,
      })),
    ],
    [summary.by_module],
  );

  const routeBuckets = useMemo(() => {
    const counts = new Map<string, { label: string; count: number }>();
    for (const item of summary.items) {
      const key = item.route_label || item.path;
      const existing = counts.get(key);
      if (existing) {
        existing.count += 1;
      } else {
        counts.set(key, { label: key, count: 1 });
      }
    }
    return Array.from(counts.values()).sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
  }, [summary.items]);

  const routeOptions = useMemo(
    () => [
      { value: "all", label: "Tutti i percorsi" },
      ...routeBuckets.map((bucket) => ({
        value: bucket.label,
        label: `${bucket.label} (${bucket.count})`,
      })),
    ],
    [routeBuckets],
  );

  const filteredItems = useMemo(() => {
    const normalizedQuery = searchTerm.trim().toLowerCase();
    return summary.items.filter((item) => {
      if (moduleFilter !== "all" && item.module_key !== moduleFilter) {
        return false;
      }
      if (routeFilter !== "all" && (item.route_label || item.path) !== routeFilter) {
        return false;
      }
      if (visibilityFilter === "visible" && !item.visible) {
        return false;
      }
      if (visibilityFilter === "hidden" && item.visible) {
        return false;
      }
      if (!normalizedQuery) {
        return true;
      }
      const haystack = [
        item.username,
        item.full_name,
        item.role,
        item.module_key,
        item.route_label,
        item.path,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(normalizedQuery);
    });
  }, [moduleFilter, routeFilter, searchTerm, summary.items, visibilityFilter]);

  const topRoute = routeBuckets[0] ?? null;
  const topModule = summary.by_module[0] ?? null;

  return (
    <ProtectedPage
      title="Attività utenti GAIA"
      description="Presenza applicativa recente degli utenti GAIA, con pagina/modulo visitato e finestra ultimi 15 minuti."
      breadcrumb="GAIA / Attività utenti"
      requiredModule="accessi"
      requiredSection="accessi.users"
      requiredRoles={["admin", "super_admin"]}
    >
      <section className="space-y-6">
        <article className="rounded-[28px] border border-gray-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">MVP presenza</p>
              <h3 className="mt-2 text-2xl font-semibold text-gray-900">Attivi negli ultimi {summary.window_minutes} minuti</h3>
              <p className="mt-2 max-w-3xl text-sm text-gray-600">
                Questa vista usa heartbeat client-side autenticato. Misura attività recente e pagina aperta, non una sessione live websocket.
              </p>
            </div>
            <Link
              href="/gaia/users"
              className="inline-flex items-center rounded-full border border-[#1D4E35]/20 px-4 py-2 text-sm font-medium text-[#1D4E35] transition hover:bg-[#EAF3E8]"
            >
              Torna a utenti GAIA
            </Link>
          </div>
        </article>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <article className="rounded-[24px] border border-gray-200 bg-white p-5 shadow-sm">
            <p className="text-xs uppercase tracking-[0.16em] text-gray-500">Attivi finestra corrente</p>
            <p className="mt-2 text-4xl font-semibold text-[#1D4E35]">{summary.active_users}</p>
          </article>
          <article className="rounded-[24px] border border-gray-200 bg-white p-5 shadow-sm">
            <p className="text-xs uppercase tracking-[0.16em] text-gray-500">Schede visibili</p>
            <p className="mt-2 text-4xl font-semibold text-[#1D4E35]">{summary.visible_users}</p>
          </article>
          <article className="rounded-[24px] border border-gray-200 bg-white p-5 shadow-sm">
            <p className="text-xs uppercase tracking-[0.16em] text-gray-500">Moduli con attività</p>
            <p className="mt-2 text-4xl font-semibold text-[#1D4E35]">{summary.by_module.length}</p>
            <p className="mt-2 text-xs text-gray-500">{topModule ? `Più usato: ${topModule.module_key}` : "Nessun modulo rilevato"}</p>
          </article>
          <article className="rounded-[24px] border border-gray-200 bg-white p-5 shadow-sm">
            <p className="text-xs uppercase tracking-[0.16em] text-gray-500">Percorso più frequente</p>
            <p className="mt-2 text-lg font-semibold text-[#1D4E35]">{topRoute?.label ?? "n/d"}</p>
            <p className="mt-2 text-xs text-gray-500">{topRoute ? `${topRoute.count} utenti nella finestra corrente` : "Nessun percorso rilevato"}</p>
          </article>
        </div>

        <article className="rounded-[28px] border border-gray-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Utenti recenti</h3>
              <p className="mt-1 text-sm text-gray-600">Chi sta usando GAIA e quale superficie ha aperto più di recente.</p>
            </div>
            <div className="flex items-center gap-3">
              {isLoading ? <p className="text-sm text-gray-500">Aggiornamento…</p> : null}
              <button
                type="button"
                onClick={() => {
                  setIsLoading(true);
                  void loadSummary();
                }}
                className="inline-flex items-center rounded-full border border-[#1D4E35]/20 px-4 py-2 text-sm font-medium text-[#1D4E35] transition hover:bg-[#EAF3E8]"
              >
                Aggiorna ora
              </button>
            </div>
          </div>

          {error ? (
            <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
          ) : null}

          {summary.by_module.length > 0 ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {summary.by_module.map((bucket) => (
                <span key={bucket.module_key} className="rounded-full bg-[#EAF3E8] px-3 py-1 text-xs font-medium text-[#1D4E35]">
                  {bucket.module_key}: {bucket.count}
                </span>
              ))}
            </div>
          ) : null}

          {routeBuckets.length > 0 ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {routeBuckets.slice(0, 6).map((bucket) => (
                <button
                  key={bucket.label}
                  type="button"
                  onClick={() => setRouteFilter(bucket.label)}
                  className="rounded-full border border-[#dfe7dc] bg-white px-3 py-1 text-xs font-medium text-[#1D4E35] transition hover:bg-[#EAF3E8]"
                >
                  {bucket.label} · {bucket.count}
                </button>
              ))}
              {routeFilter !== "all" ? (
                <button
                  type="button"
                  onClick={() => setRouteFilter("all")}
                  className="rounded-full border border-gray-200 bg-white px-3 py-1 text-xs font-medium text-gray-600 transition hover:bg-gray-50"
                >
                  Reset percorso
                </button>
              ) : null}
            </div>
          ) : null}

          <div className="mt-5 grid gap-3 rounded-[24px] border border-[#e4e8e2] bg-[#fcfcf9] p-4 md:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)]">
            <label className="block">
              <span className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Ricerca</span>
              <input
                className="mt-2 w-full rounded-2xl border border-gray-200 bg-white px-4 py-2.5 text-sm text-gray-900 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
                placeholder="Utente, ruolo, modulo o path"
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
              />
            </label>
            <label className="block">
              <span className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Modulo</span>
              <select
                className="mt-2 w-full rounded-2xl border border-gray-200 bg-white px-4 py-2.5 text-sm text-gray-900 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
                value={moduleFilter}
                onChange={(event) => setModuleFilter(event.target.value)}
              >
                {moduleOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Percorso</span>
              <select
                className="mt-2 w-full rounded-2xl border border-gray-200 bg-white px-4 py-2.5 text-sm text-gray-900 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
                value={routeFilter}
                onChange={(event) => setRouteFilter(event.target.value)}
              >
                {routeOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Visibilità scheda</span>
              <select
                className="mt-2 w-full rounded-2xl border border-gray-200 bg-white px-4 py-2.5 text-sm text-gray-900 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
                value={visibilityFilter}
                onChange={(event) => setVisibilityFilter(event.target.value)}
              >
                <option value="all">Tutte</option>
                <option value="visible">Solo visibili</option>
                <option value="hidden">Solo non visibili</option>
              </select>
            </label>
          </div>

          <div className="mt-5 overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-[0.16em] text-gray-500">
                  <th className="py-3 pr-4">Utente</th>
                  <th className="py-3 pr-4">Modulo</th>
                  <th className="py-3 pr-4">Pagina</th>
                  <th className="py-3 pr-4">Azione</th>
                  <th className="py-3 pr-4">Visibile</th>
                  <th className="py-3 pr-4">Ultimo segnale</th>
                  <th className="py-3 pr-4">Azioni</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredItems.length === 0 ? (
                  <tr>
                    <td className="py-6 text-sm text-gray-500" colSpan={7}>
                      {summary.items.length === 0
                        ? "Nessuna attività registrata nella finestra corrente."
                        : "Nessun utente corrisponde ai filtri correnti."}
                    </td>
                  </tr>
                ) : (
                  filteredItems.map((item) => (
                    <tr key={item.user_id}>
                      <td className="py-4 pr-4">
                        <p className="font-medium text-gray-900">{item.full_name || item.username}</p>
                        <p className="text-xs text-gray-500">{item.username} · {item.role}</p>
                      </td>
                      <td className="py-4 pr-4 text-gray-700">{item.module_key || "n/d"}</td>
                      <td className="py-4 pr-4">
                        <p className="font-medium text-gray-900">{item.route_label || item.path}</p>
                        <p className="text-xs text-gray-500">{item.path}</p>
                        {(item.recent_routes?.length ?? 0) > 1 ? (
                          <div className="mt-2 space-y-1">
                            {(item.recent_routes ?? []).slice(1, 4).map((route) => (
                              <p key={`${route.path}-${route.seen_at}`} className="truncate text-xs text-gray-400">
                                {route.route_label || route.path}
                              </p>
                            ))}
                          </div>
                        ) : null}
                      </td>
                      <td className="py-4 pr-4">
                        <p className="font-medium text-gray-900">{item.action_label || "Nessuna azione esplicita"}</p>
                        {(item.recent_actions?.length ?? 0) > 1 ? (
                          <div className="mt-2 space-y-1">
                            {(item.recent_actions ?? []).slice(1, 3).map((action) => (
                              <p key={`${action.action_label}-${action.occurred_at}`} className="truncate text-xs text-gray-400">
                                {action.action_label}
                              </p>
                            ))}
                          </div>
                        ) : null}
                      </td>
                      <td className="py-4 pr-4 text-gray-700">{item.visible ? "Si" : "No"}</td>
                      <td className="py-4 pr-4">
                        <p className="font-medium text-gray-900">{formatDateTime(item.last_seen_at)}</p>
                        <p className="text-xs text-gray-500">{formatRelativeLabel(item.minutes_since_last_seen)}</p>
                      </td>
                      <td className="py-4 pr-4">
                        <div className="flex flex-wrap gap-2">
                          <Link
                            href={normalizeInternalPath(item.path)}
                            className="inline-flex items-center rounded-full border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-700 transition hover:border-[#1D4E35] hover:text-[#1D4E35]"
                          >
                            Apri pagina
                          </Link>
                          {canOpenOperazioniDetail(item) ? (
                            <Link
                              href={`/operazioni/attivita?operator_user_id=${item.user_id}`}
                              className="inline-flex items-center rounded-full border border-[#1D4E35]/20 px-3 py-1.5 text-xs font-medium text-[#1D4E35] transition hover:bg-[#EAF3E8]"
                            >
                              Vedi attività operatore
                            </Link>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </article>
      </section>
    </ProtectedPage>
  );
}
