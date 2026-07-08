"use client";

import { useEffect, useState } from "react";

import { CatastoPage } from "@/components/catasto/catasto-page";
import { AlertBanner } from "@/components/ui/alert-banner";
import {
  catastoGetDeliveryPointsImportJob,
  catastoGetDeliveryPointsImportConfig,
  catastoImportDeliveryPointsFromConfig,
  catastoRefreshDeliveryPointsGisCache,
  catastoUpdateDeliveryPointsImportConfig,
} from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import { storeDeliveryPointsTileRevision } from "@/lib/catasto-gis-cache";
import type { CatDeliveryPointsImportConfig, CatDeliveryPointsImportRunResponse } from "@/types/catasto";

function formatDateTime(value: string | null): string {
  if (!value) return "Mai";
  return new Intl.DateTimeFormat("it-IT", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-slate-950">{value}</p>
    </article>
  );
}

function isActiveImport(status: string | undefined): boolean {
  return status === "pending" || status === "running";
}

export default function CatastoDeliveryPointsConfigPage() {
  const [config, setConfig] = useState<CatDeliveryPointsImportConfig | null>(null);
  const [rootPath, setRootPath] = useState("");
  const [lastRun, setLastRun] = useState<CatDeliveryPointsImportRunResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [importing, setImporting] = useState(false);
  const [cacheRefreshing, setCacheRefreshing] = useState(false);
  const [cacheMessage, setCacheMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const token = getStoredAccessToken();
      if (!token) {
        setError("Sessione non disponibile.");
        setLoading(false);
        return;
      }
      try {
        const response = await catastoGetDeliveryPointsImportConfig(token);
        setConfig(response);
        setRootPath(response.root_path ?? "");
        setError(null);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Errore caricamento configurazione.");
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, []);

  useEffect(() => {
    if (!lastRun?.job_id || !isActiveImport(lastRun.status)) {
      return;
    }

    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile.");
      setImporting(false);
      return;
    }

    setImporting(true);
    const timeout = window.setTimeout(() => {
      void catastoGetDeliveryPointsImportJob(token, lastRun.job_id!)
        .then((response) => {
          setLastRun(response);
          if (response.status === "failed") {
            setError(response.error_message ?? "Errore import punti di consegna.");
            setImporting(false);
            return;
          }
          if (!isActiveImport(response.status)) {
            setError(null);
            setImporting(false);
          }
        })
        .catch((pollError) => {
          setError(pollError instanceof Error ? pollError.message : "Errore verifica stato import punti di consegna.");
          setImporting(false);
        });
    }, 3000);

    return () => window.clearTimeout(timeout);
  }, [lastRun]);

  async function handleSave() {
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile.");
      return;
    }
    try {
      setSaving(true);
      const response = await catastoUpdateDeliveryPointsImportConfig(token, {
        root_path: rootPath.trim() || null,
      });
      setConfig(response);
      setRootPath(response.root_path ?? "");
      setError(null);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Errore salvataggio configurazione.");
    } finally {
      setSaving(false);
    }
  }

  async function handleImport() {
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile.");
      return;
    }
    let keepImporting = false;
    try {
      setImporting(true);
      const response = await catastoImportDeliveryPointsFromConfig(token);
      keepImporting = isActiveImport(response.status);
      setLastRun(response);
      if (response.status === "failed") {
        setError(response.error_message ?? "Errore import punti di consegna.");
      } else {
        setError(null);
      }
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "Errore import punti di consegna.");
    } finally {
      setImporting(keepImporting);
    }
  }

  async function handleRefreshGisCache() {
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile.");
      return;
    }
    try {
      setCacheRefreshing(true);
      const response = await catastoRefreshDeliveryPointsGisCache(token);
      storeDeliveryPointsTileRevision(response.tile_revision);
      setCacheMessage(`${response.message} Revisione: ${response.tile_revision}.`);
      setError(null);
    } catch (refreshError) {
      setCacheMessage(null);
      setError(refreshError instanceof Error ? refreshError.message : "Errore aggiornamento cache GIS.");
    } finally {
      setCacheRefreshing(false);
    }
  }

  return (
    <CatastoPage
      title="Configurazione punti di consegna"
      description="Configura la cartella NAS degli shapefile dei punti di consegna e avvia l'import automatico nel GIS."
      breadcrumb="Catasto / Configurazione punti di consegna"
      requiredModule="catasto"
      requiredRoles={["admin", "super_admin"]}
    >
      <div className="page-stack">
        <section className="rounded-[2rem] border border-emerald-100 bg-[#f5faf7] p-6 shadow-sm">
          <div className="max-w-3xl">
            <div className="inline-flex rounded-full border border-emerald-200 bg-white px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">
              Import GIS da NAS
            </div>
            <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-950">Punti di consegna 2026</h1>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              Il backend legge la cartella configurata, importa gli shapefile divisi per distretto e ricollega automaticamente
              le letture contatori ai punti GIS quando trova un match.
            </p>
          </div>
        </section>

        {error ? (
          <AlertBanner title="Operazione non completata" variant="danger">
            {error}
          </AlertBanner>
        ) : null}

        <section className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px]">
            <div>
              <label className="block text-sm font-medium text-slate-700" htmlFor="delivery-points-root-path">
                Cartella sorgente NAS
              </label>
              <input
                id="delivery-points-root-path"
                className="form-control mt-2"
                disabled={loading || saving}
                onChange={(event) => setRootPath(event.target.value)}
                placeholder="/mnt/nas-catasto/PUNTI_CONSEGNA 2026_DEF"
                value={rootPath}
              />
              <p className="mt-3 text-xs text-slate-500">
                La cartella deve contenere le sottocartelle{" "}
                <code>{config?.expected_with_meter_dir ?? "Punti_Cons-Con_contatoti"}</code> e{" "}
                <code>{config?.expected_without_meter_dir ?? "Punti_Cons-Con_Senza_contatoti"}</code>.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
              <p className="font-semibold text-slate-900">Ultimo aggiornamento config</p>
              <p className="mt-2">
                {config?.updated_by ? `${config.updated_by} · ${formatDateTime(config.updated_at)}` : "Configurazione non ancora salvata."}
              </p>
            </div>
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            <button className="btn-primary" disabled={loading || saving} onClick={() => void handleSave()} type="button">
              {saving ? "Salvataggio..." : "Salva configurazione"}
            </button>
            <button
              className="btn-secondary"
              disabled={loading || importing || !((config?.root_path ?? rootPath).trim())}
              onClick={() => void handleImport()}
              type="button"
            >
              {importing ? "Import in corso..." : "Importa dal NAS"}
            </button>
          </div>
        </section>

        <section className="rounded-[2rem] border border-amber-100 bg-amber-50 p-6 shadow-sm">
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_240px]">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-700">Cache GIS</p>
              <h2 className="mt-2 text-xl font-semibold text-slate-950">Aggiorna le tile dei punti di consegna</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                Usa questa funzione dopo un import se la mappa continua a mostrare punti vecchi o incompleti. La mappa aperta in altre schede
                ricarichera le tile alla prossima apertura o refresh.
              </p>
              {cacheMessage ? <p className="mt-3 text-sm font-medium text-emerald-700">{cacheMessage}</p> : null}
            </div>
            <div className="flex items-center lg:justify-end">
              <button
                className="btn-secondary"
                disabled={loading || cacheRefreshing}
                onClick={() => void handleRefreshGisCache()}
                type="button"
              >
                {cacheRefreshing ? "Aggiornamento..." : "Aggiorna cache GIS"}
              </button>
            </div>
          </div>
        </section>

        {lastRun ? (
          <section className="space-y-4">
            {isActiveImport(lastRun.status) ? (
              <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 shadow-sm">
                Import punti di consegna in corso. Puoi lasciare aperta questa pagina: lo stato viene aggiornato automaticamente.
              </div>
            ) : null}
            {lastRun.status === "completed" ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <StatCard label="Punti processati" value={(lastRun.points_processed ?? 0).toLocaleString("it-IT")} />
                <StatCard label="Canali processati" value={(lastRun.canals_processed ?? 0).toLocaleString("it-IT")} />
                <StatCard label="Letture collegate" value={(lastRun.meter_readings_linked ?? 0).toLocaleString("it-IT")} />
                <StatCard label="Letture non collegate" value={(lastRun.meter_readings_unlinked ?? 0).toLocaleString("it-IT")} />
              </div>
            ) : null}
            <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600 shadow-sm">
              <p className="font-semibold text-slate-900">Origine elaborata</p>
              <p className="mt-2 break-all">{lastRun.root_path}</p>
            </div>
          </section>
        ) : null}
      </div>
    </CatastoPage>
  );
}
