"use client";

import Link from "next/link";

import { EmptyState } from "@/components/ui/empty-state";
import { FolderIcon, SearchIcon } from "@/components/ui/icons";
import type { CatAnagraficaMatch } from "@/types/catasto";

function formatHaFromMq(value: string | number | null | undefined): string {
  if (value == null) return "—";
  const mq = typeof value === "number" ? value : Number(value);
  const ha = (Number.isFinite(mq) ? mq : 0) / 10_000;
  return `${new Intl.NumberFormat("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(ha)} ha`;
}

export function AnagraficaResultPanel({
  matches,
  isLoading,
  error,
  searchedKey,
}: {
  matches: CatAnagraficaMatch[];
  isLoading: boolean;
  error: string | null;
  searchedKey: { comune?: string; foglio?: string; particella?: string } | null;
}) {
  if (error) {
    return (
      <div className="rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-800">
        <p className="font-medium">Errore</p>
        <p className="mt-1">{error}</p>
      </div>
    );
  }

  if (isLoading) {
    return <div className="rounded-xl border border-gray-100 bg-gray-50 p-4 text-sm text-gray-500">Caricamento…</div>;
  }

  if (!searchedKey) {
    return <EmptyState icon={SearchIcon} title="Nessuna ricerca" description="Inserisci comune (opzionale), foglio e particella, poi avvia la ricerca." />;
  }

  if (matches.length === 0) {
    return (
      <EmptyState
        icon={SearchIcon}
        title="Nessun risultato"
        description="Non risultano particelle che corrispondono ai riferimenti catastali indicati."
      />
    );
  }

  return (
    <div className="space-y-3">
      {matches.length > 1 ? (
        <div className="rounded-xl border border-amber-100 bg-amber-50 p-4 text-sm text-amber-800">
          Trovati <span className="font-semibold">{matches.length}</span> match. Se possibile, specifica il comune per restringere.
        </div>
      ) : null}

      {matches.map((m) => {
        const ref = `Fg.${m.foglio} Part.${m.particella}${m.subalterno ? ` Sub.${m.subalterno}` : ""}`;
        const intestatari = m.intestatari ?? [];
        const utenza = m.utenza_latest;
        return (
          <article key={m.particella_id} className="panel-card">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm font-semibold text-gray-900">{ref}</p>
                <p className="mt-1 text-sm text-gray-500">
                  Comune: <span className="font-medium text-gray-800">{m.comune ?? "—"}</span>{" "}
                  <span className="text-gray-400">·</span> Codice Capacitas: <span className="font-medium text-gray-800">{m.cod_comune_capacitas ?? "—"}</span>{" "}
                  <span className="text-gray-400">·</span> Distretto: <span className="font-medium text-gray-800">{m.num_distretto ?? "—"}</span>
                </p>
              </div>

              <Link className="btn-secondary" href={`/catasto/particelle/${m.particella_id}`}>
                <FolderIcon className="h-4 w-4" />
                Apri particella
              </Link>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <div className="rounded-xl border border-gray-100 bg-white p-3">
                <p className="text-[10px] font-medium uppercase tracking-widest text-gray-400">Catasto</p>
                <div className="mt-2 space-y-1 text-sm text-gray-700">
                  <p>
                    <span className="text-gray-500">Superficie:</span> {formatHaFromMq(m.superficie_mq)}
                  </p>
                  <p>
                    <span className="text-gray-500">Nome distretto:</span> {m.nome_distretto ?? "—"}
                  </p>
                </div>
              </div>

              <div className="rounded-xl border border-gray-100 bg-white p-3">
                <p className="text-[10px] font-medium uppercase tracking-widest text-gray-400">Anagrafica</p>
                <div className="mt-2 space-y-2 text-sm text-gray-700">
                  {intestatari.length === 0 ? (
                    <p className="text-gray-500">Nessun intestatario disponibile (non presente in `cat_intestatari`).</p>
                  ) : (
                    <ul className="list-disc pl-5">
                      {intestatari.slice(0, 8).map((i) => (
                        <li key={i.id}>
                          <span className="font-medium">
                            {(i.denominazione ?? i.ragione_sociale ?? [i.cognome, i.nome].filter(Boolean).join(" ")) || "—"}
                          </span>{" "}
                          <span className="text-gray-500">({i.codice_fiscale})</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>

              <div className="rounded-xl border border-gray-100 bg-white p-3">
                <p className="text-[10px] font-medium uppercase tracking-widest text-gray-400">Utenza</p>
                <div className="mt-2 space-y-1 text-sm text-gray-700">
                  {!utenza ? (
                    <p className="text-gray-500">Nessuna utenza collegata trovata per la particella.</p>
                  ) : (
                    <>
                      <p>
                        <span className="text-gray-500">ID utenza:</span> {utenza.id}
                      </p>
                      <p>
                        <span className="text-gray-500">Anno:</span> {utenza.anno_campagna ?? "—"}
                      </p>
                      <p>
                        <span className="text-gray-500">Distretto:</span> {utenza.num_distretto ?? "—"} {utenza.nome_distretto ? `(${utenza.nome_distretto})` : ""}
                      </p>
                      <p>
                        <span className="text-gray-500">Sup. irrigabile:</span> {formatHaFromMq(utenza.sup_irrigabile_mq)}
                      </p>
                      <p>
                        <span className="text-gray-500">CF:</span> {utenza.codice_fiscale ?? "—"}
                      </p>
                      <p>
                        <span className="text-gray-500">Anomalie:</span>{" "}
                        <span className={utenza.ha_anomalie ? "font-medium text-amber-700" : "text-gray-700"}>
                          {utenza.ha_anomalie ? "Sì" : "No"}
                        </span>
                      </p>
                    </>
                  )}
                </div>
              </div>
            </div>

            <div className="mt-4 rounded-xl border border-gray-100 bg-gray-50 p-3 text-sm text-gray-700">
              <p className="font-medium text-gray-900">Controlli</p>
              <p className="mt-1">
                Anomalie collegate: <span className="font-semibold">{m.anomalie_count}</span>
                {m.anomalie_top?.length ? (
                  <span className="text-gray-500">
                    {" "}
                    · Top: {m.anomalie_top.map((a) => `${a.tipo} (${a.count})`).join(", ")}
                  </span>
                ) : null}
              </p>
            </div>
          </article>
        );
      })}
    </div>
  );
}
