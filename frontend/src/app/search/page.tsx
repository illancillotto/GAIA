"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { ProtectedPage } from "@/components/app/protected-page";
import { getStoredAccessToken } from "@/lib/auth";
import { searchOperational } from "@/lib/operational-search-api";
import type { OperationalSearchModule, OperationalSearchResult } from "@/types/api";

const moduleLabels: Record<OperationalSearchModule, string> = {
  utenze: "Utenze",
  ruolo: "Ruolo",
  catasto: "Catasto",
};

function moduleTone(module: OperationalSearchModule): string {
  switch (module) {
    case "utenze":
      return "border-emerald-100 bg-emerald-50 text-emerald-800";
    case "ruolo":
      return "border-amber-100 bg-amber-50 text-amber-800";
    case "catasto":
      return "border-sky-100 bg-sky-50 text-sky-800";
  }
}

function groupResults(items: OperationalSearchResult[]): Record<OperationalSearchModule, OperationalSearchResult[]> {
  return items.reduce<Record<OperationalSearchModule, OperationalSearchResult[]>>(
    (groups, item) => {
      groups[item.module] = [...groups[item.module], item];
      return groups;
    },
    { utenze: [], ruolo: [], catasto: [] },
  );
}

function SearchContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryFromUrl = searchParams.get("q")?.trim() ?? "";
  const [query, setQuery] = useState(queryFromUrl);
  const [items, setItems] = useState<OperationalSearchResult[]>([]);
  const [activeModule, setActiveModule] = useState<OperationalSearchModule | "all">("all");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const canSearch = queryFromUrl.length >= 2;

  useEffect(() => {
    setQuery((current) => (current === queryFromUrl ? current : queryFromUrl));
    setActiveModule("all");
  }, [queryFromUrl]);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token || !canSearch) {
      setItems([]);
      setError(null);
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    setIsLoading(true);
    setError(null);
    searchOperational(token, queryFromUrl, { limit: 30 })
      .then((response) => {
        /* v8 ignore next -- defensive guard for stale in-flight searches after cleanup. */
        if (cancelled) return;
        setItems(response.items);
      })
      .catch((searchError) => {
        /* v8 ignore next -- defensive guard for stale in-flight searches after cleanup. */
        if (cancelled) return;
        setItems([]);
        setError(searchError instanceof Error ? searchError.message : "Ricerca non disponibile");
      })
      .finally(() => {
        /* v8 ignore next -- defensive guard for stale in-flight searches after cleanup. */
        if (!cancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [canSearch, queryFromUrl]);

  const groupedResults = useMemo(() => groupResults(items), [items]);
  const visibleItems = activeModule === "all" ? items : groupedResults[activeModule];
  const modulesWithCounts = (Object.keys(moduleLabels) as OperationalSearchModule[]).map((module) => ({
    module,
    count: groupedResults[module].length,
  }));

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    const normalized = query.trim();
    if (!normalized) {
      router.push("/search");
      return;
    }
    router.push(`/search?q=${encodeURIComponent(normalized)}`);
  }

  return (
    <div className="space-y-6">
      <section className="rounded-[32px] border border-emerald-100 bg-[linear-gradient(135deg,#F6FBF4_0%,#FFFFFF_55%,#EEF6F1_100%)] p-6 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-800">Ricerca operativa</p>
        <h2 className="mt-2 text-3xl font-semibold tracking-tight text-gray-950">Risultati GAIA</h2>
        <p className="mt-2 max-w-2xl text-sm text-gray-600">
          Cerca in Utenze, Ruolo e Catasto senza cambiare modulo. I risultati rispettano i permessi del tuo profilo.
        </p>
        <form className="mt-5 flex flex-col gap-3 md:flex-row" onSubmit={handleSubmit}>
          <label className="sr-only" htmlFor="serp-query">Query ricerca operativa</label>
          <input
            id="serp-query"
            className="min-h-12 flex-1 rounded-2xl border border-emerald-200 bg-white px-4 text-base font-medium text-gray-950 shadow-sm outline-none transition placeholder:text-emerald-900/45 focus:border-emerald-600 focus:ring-2 focus:ring-emerald-700/15"
            placeholder="Cerca utenza, codice fiscale, foglio, particella, avviso…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <button
            type="submit"
            className="rounded-2xl bg-emerald-900 px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-800"
          >
            Cerca
          </button>
        </form>
      </section>

      <section className="rounded-[28px] border border-gray-100 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm font-semibold text-gray-950">
              {canSearch ? `${visibleItems.length} risultati visibili` : "Inserisci almeno 2 caratteri"}
            </p>
            <p className="text-xs text-gray-500">
              {canSearch ? `Query: ${queryFromUrl}` : "La ricerca parte quando confermi una query valida."}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                activeModule === "all" ? "border-emerald-900 bg-emerald-900 text-white" : "border-gray-200 bg-white text-gray-600"
              }`}
              onClick={() => setActiveModule("all")}
            >
              Tutto {items.length}
            </button>
            {modulesWithCounts.map(({ module, count }) => (
              <button
                key={module}
                type="button"
                className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                  activeModule === module ? "border-emerald-900 bg-emerald-900 text-white" : "border-gray-200 bg-white text-gray-600"
                }`}
                onClick={() => setActiveModule(module)}
              >
                {moduleLabels[module]} {count}
              </button>
            ))}
          </div>
        </div>

        {isLoading ? (
          <div className="mt-5 rounded-2xl border border-dashed border-gray-200 bg-gray-50 px-4 py-8 text-sm text-gray-500">
            Ricerca in corso…
          </div>
        ) : null}
        {error ? (
          <div className="mt-5 rounded-2xl border border-red-100 bg-red-50 px-4 py-4 text-sm text-red-700">
            {error}
          </div>
        ) : null}
        {!isLoading && !error && canSearch && visibleItems.length === 0 ? (
          <div className="mt-5 rounded-2xl border border-dashed border-gray-200 bg-gray-50 px-4 py-8 text-sm text-gray-500">
            Nessun risultato trovato per i permessi correnti.
          </div>
        ) : null}
        {!canSearch ? (
          <div className="mt-5 rounded-2xl border border-dashed border-gray-200 bg-gray-50 px-4 py-8 text-sm text-gray-500">
            Usa la barra in alto per cercare soggetti, avvisi, fogli e particelle.
          </div>
        ) : null}

        <div className="mt-5 space-y-3">
          {visibleItems.map((item) => (
            <Link
              key={`${item.module}-${item.type}-${item.id}`}
              href={item.href}
              className="block rounded-2xl border border-gray-100 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:border-emerald-200 hover:shadow-md"
            >
              <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div className="min-w-0">
                  <span className={`inline-flex rounded-full border px-2.5 py-1 text-[11px] font-semibold ${moduleTone(item.module)}`}>
                    {moduleLabels[item.module]} · {item.type}
                  </span>
                  <h3 className="mt-2 text-base font-semibold text-gray-950">{item.title}</h3>
                  <p className="mt-1 text-sm text-gray-500">{item.subtitle}</p>
                  {item.description ? <p className="mt-1 text-sm text-gray-700">{item.description}</p> : null}
                </div>
                <span className="shrink-0 text-xs font-medium text-gray-400">Score {item.score}</span>
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}

export default function OperationalSearchPage() {
  return (
    <ProtectedPage
      title="Ricerca GAIA"
      description="Risultati operativi trasversali su utenze, ruolo e catasto."
      breadcrumb="Search"
      hideContentHeader
    >
      <SearchContent />
    </ProtectedPage>
  );
}
