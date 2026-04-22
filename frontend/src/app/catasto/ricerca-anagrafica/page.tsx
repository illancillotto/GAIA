"use client";

import { useState } from "react";

import { CatastoPage } from "@/components/catasto/catasto-page";
import { AlertBanner } from "@/components/ui/alert-banner";
import { AnagraficaSingleSearchForm, type AnagraficaSingleSearchValues } from "@/components/catasto/anagrafica/AnagraficaSingleSearchForm";
import { AnagraficaResultPanel } from "@/components/catasto/anagrafica/AnagraficaResultPanel";
import { AnagraficaBulkPanel } from "@/components/catasto/anagrafica/AnagraficaBulkPanel";
import { catastoSearchAnagrafica } from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatAnagraficaMatch } from "@/types/catasto";

type TabKey = "single" | "bulk";

export default function CatastoRicercaAnagraficaPage() {
  const [tab, setTab] = useState<TabKey>("single");

  const [matches, setMatches] = useState<CatAnagraficaMatch[]>([]);
  const [searchedKey, setSearchedKey] = useState<{ comune?: string; foglio?: string; particella?: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runSingleSearch(values: AnagraficaSingleSearchValues): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setBusy(true);
    setError(null);
    setSearchedKey({ comune: values.comune || undefined, foglio: values.foglio, particella: values.particella });
    try {
      const res = await catastoSearchAnagrafica(token, {
        comune: values.comune || undefined,
        foglio: values.foglio,
        particella: values.particella,
      });
      setMatches(res.matches ?? []);
    } catch (e) {
      setMatches([]);
      setError(e instanceof Error ? e.message : "Errore ricerca anagrafica");
    } finally {
      setBusy(false);
    }
  }

  return (
    <CatastoPage
      title="Ricerca anagrafica"
      description="Recupero anagrafica e utenze a partire da riferimenti catastali (singola o massiva)."
      breadcrumb="Catasto / Ricerca anagrafica"
      requiredModule="catasto"
    >
      <div className="page-stack">
        <article className="panel-card">
          <p className="text-sm font-medium text-gray-900">Modalità</p>
          <p className="mt-1 text-sm text-gray-500">Scegli la modalità operativa più adatta: ricerca singola interattiva o elaborazione massiva da file.</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              className={tab === "single" ? "btn-primary" : "btn-secondary"}
              onClick={() => setTab("single")}
            >
              Ricerca singola
            </button>
            <button
              type="button"
              className={tab === "bulk" ? "btn-primary" : "btn-secondary"}
              onClick={() => setTab("bulk")}
            >
              Elaborazione massiva
            </button>
          </div>
        </article>

        {tab === "single" ? (
          <>
            {error ? (
              <AlertBanner variant="danger" title="Errore">
                {error}
              </AlertBanner>
            ) : null}

            <article className="panel-card">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-gray-900">Ricerca per riferimenti catastali</p>
                  <p className="mt-1 text-sm text-gray-500">Inserisci foglio e particella. Il comune è consigliato (codice Capacitas o nome) per ridurre match multipli.</p>
                </div>
              </div>
              <div className="mt-4">
                <AnagraficaSingleSearchForm
                  disabled={busy}
                  initialValues={{ comune: "", foglio: "", particella: "" }}
                  onSubmit={(values) => void runSingleSearch(values)}
                />
              </div>
            </article>

            <AnagraficaResultPanel matches={matches} isLoading={busy} error={error} searchedKey={searchedKey} />
          </>
        ) : (
          <AnagraficaBulkPanel />
        )}
      </div>
    </CatastoPage>
  );
}
