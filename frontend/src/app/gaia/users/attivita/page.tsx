"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { ProtectedPage } from "@/components/app/protected-page";
import { getPresenceSummary } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { UserPresenceSummary } from "@/types/api";

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

export default function GaiaUsersActivityPage() {
  const [summary, setSummary] = useState<UserPresenceSummary>(emptySummary);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadSummary() {
      const token = getStoredAccessToken();
      if (!token) {
        if (!cancelled) {
          setIsLoading(false);
        }
        return;
      }

      try {
        const payload = await getPresenceSummary(token, { windowMinutes: 15 });
        if (!cancelled) {
          setSummary(payload);
          setError(null);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Errore caricamento attività utenti");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadSummary();
    const intervalId = window.setInterval(() => void loadSummary(), 60_000);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

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

        <div className="grid gap-4 md:grid-cols-3">
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
          </article>
        </div>

        <article className="rounded-[28px] border border-gray-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Utenti recenti</h3>
              <p className="mt-1 text-sm text-gray-600">Chi sta usando GAIA e quale superficie ha aperto più di recente.</p>
            </div>
            {isLoading ? <p className="text-sm text-gray-500">Aggiornamento…</p> : null}
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

          <div className="mt-5 overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-[0.16em] text-gray-500">
                  <th className="py-3 pr-4">Utente</th>
                  <th className="py-3 pr-4">Modulo</th>
                  <th className="py-3 pr-4">Pagina</th>
                  <th className="py-3 pr-4">Visibile</th>
                  <th className="py-3 pr-4">Ultimo segnale</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {summary.items.length === 0 ? (
                  <tr>
                    <td className="py-6 text-sm text-gray-500" colSpan={5}>
                      Nessuna attività registrata nella finestra corrente.
                    </td>
                  </tr>
                ) : (
                  summary.items.map((item) => (
                    <tr key={item.user_id}>
                      <td className="py-4 pr-4">
                        <p className="font-medium text-gray-900">{item.full_name || item.username}</p>
                        <p className="text-xs text-gray-500">{item.username} · {item.role}</p>
                      </td>
                      <td className="py-4 pr-4 text-gray-700">{item.module_key || "n/d"}</td>
                      <td className="py-4 pr-4">
                        <p className="font-medium text-gray-900">{item.route_label || item.path}</p>
                        <p className="text-xs text-gray-500">{item.path}</p>
                      </td>
                      <td className="py-4 pr-4 text-gray-700">{item.visible ? "Si" : "No"}</td>
                      <td className="py-4 pr-4">
                        <p className="font-medium text-gray-900">{formatDateTime(item.last_seen_at)}</p>
                        <p className="text-xs text-gray-500">{item.minutes_since_last_seen} min fa</p>
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
