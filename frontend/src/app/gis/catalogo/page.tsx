"use client";

import Link from "next/link";
import { startTransition, useEffect, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { RefreshIcon } from "@/components/ui/icons";
import { getStoredAccessToken } from "@/lib/auth";
import { listGisCatalogLayers } from "@/lib/api/gis";
import type { GisCatalogLayer, GisCatalogLayerFilters } from "@/types/gis";

type ActiveFilter = "all" | "active" | "inactive";

type FilterState = {
  workspace: string;
  domainModule: string;
  sourceType: string;
  officialSource: string;
  active: ActiveFilter;
};

const initialFilters: FilterState = {
  workspace: "",
  domainModule: "",
  sourceType: "",
  officialSource: "",
  active: "all",
};

function toApiFilters(filters: FilterState): GisCatalogLayerFilters {
  const apiFilters: GisCatalogLayerFilters = {};
  if (filters.workspace.trim()) apiFilters.workspace = filters.workspace.trim();
  if (filters.domainModule.trim()) apiFilters.domainModule = filters.domainModule.trim();
  if (filters.sourceType.trim()) apiFilters.sourceType = filters.sourceType.trim();
  if (filters.officialSource.trim()) apiFilters.officialSource = filters.officialSource.trim();
  if (filters.active === "active") apiFilters.isActive = true;
  if (filters.active === "inactive") apiFilters.isActive = false;
  return apiFilters;
}

function formatValue(value: string | number | null | undefined): string {
  if (value == null || value === "") return "Non configurato";
  return String(value);
}

function metadataObject(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function metadataLabel(value: unknown): string {
  if (value == null || value === "") return "Non configurato";
  return String(value);
}

function qgisMode(layer: GisCatalogLayer): string {
  const qgis = metadataObject(layer.metadata.qgis);
  return metadataLabel(qgis?.mode);
}

function tileProvider(layer: GisCatalogLayer): string {
  const tiles = metadataObject(layer.metadata.tiles);
  return metadataLabel(tiles?.provider);
}

function domainWorkspaceHref(layer: GisCatalogLayer): string | null {
  if (layer.workspace === "catasto" || layer.domain_module === "catasto") return "/catasto/gis";
  return null;
}

function updateFilterValue(filters: FilterState, key: keyof FilterState, value: string): FilterState {
  return { ...filters, [key]: value } as FilterState;
}

export function GisCatalogWorkspace({ token }: { token: string | null }) {
  const [filters, setFilters] = useState<FilterState>(initialFilters);
  const [layers, setLayers] = useState<GisCatalogLayer[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setIsLoading(false);
      return;
    }

    let isCancelled = false;
    const currentToken = token;
    async function loadInitialCatalog() {
      setIsLoading(true);
      try {
        const response = await listGisCatalogLayers(currentToken);
        /* v8 ignore next -- defensive cleanup guard for unmounted requests */
        if (isCancelled) return;
        setLayers(response.items);
        setLoadError(null);
      } catch (error) {
        /* v8 ignore next -- defensive cleanup guard for unmounted requests */
        if (isCancelled) return;
        setLoadError(error instanceof Error ? error.message : "Errore caricamento catalogo GIS");
      } finally {
        /* v8 ignore next -- defensive cleanup guard for unmounted requests */
        if (!isCancelled) setIsLoading(false);
      }
    }

    void loadInitialCatalog();
    return () => {
      isCancelled = true;
    };
  }, [token]);

  async function loadCatalog(nextFilters: FilterState) {
    const currentToken = token as string;
    setIsLoading(true);
    try {
      const response = await listGisCatalogLayers(currentToken, toApiFilters(nextFilters));
      setLayers(response.items);
      setLoadError(null);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore caricamento catalogo GIS");
    } finally {
      setIsLoading(false);
    }
  }

  function setFilter(key: keyof FilterState, value: string) {
    startTransition(() => {
      setFilters((currentFilters) => updateFilterValue(currentFilters, key, value));
    });
  }

  function resetFilters() {
    startTransition(() => {
      setFilters(initialFilters);
    });
    void loadCatalog(initialFilters);
  }

  const workspaces = new Set<string>();
  let inactiveCount = 0;
  let officialPostgisCount = 0;
  for (const layer of layers) {
    workspaces.add(layer.workspace);
    if (!layer.is_active) inactiveCount += 1;
    if (layer.official_source === "postgis") officialPostgisCount += 1;
  }

  if (!token) {
    return (
      <article className="rounded-[28px] border border-[#d8e4db] bg-white p-6 shadow-sm">
        <p className="text-sm font-semibold text-[#1D4E35]">Sessione catalogo in caricamento.</p>
        <p className="mt-2 text-sm text-gray-500">Il catalogo GIS viene caricato dopo la verifica della sessione GAIA.</p>
      </article>
    );
  }

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-[32px] border border-[#c9d8cd] bg-[#10251d] text-white shadow-[0_22px_60px_rgba(16,37,29,0.22)]">
        <div className="grid gap-6 p-6 lg:grid-cols-[1.5fr_0.8fr] lg:p-8">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[#9fc5ad]">GAIA GIS Platform</p>
            <h2 className="mt-4 text-3xl font-semibold tracking-tight lg:text-4xl">Catalogo operativo GIS</h2>
            <p className="mt-4 max-w-2xl text-sm leading-6 text-[#d9e6dd]">
              Vista centrale read-only dei layer pubblicati: PostGIS resta sorgente ufficiale, Martin e QGIS sono
              esposti come metadati governati, Catasto resta nel proprio workspace operativo.
            </p>
          </div>
          <div className="rounded-[28px] border border-white/15 bg-white/10 p-5 backdrop-blur">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#bcd8c6]">Contratto dati</p>
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div>
                <p className="text-3xl font-semibold">{layers.length}</p>
                <p className="text-[#cbdccf]">Layer visibili</p>
              </div>
              <div>
                <p className="text-3xl font-semibold">{workspaces.size}</p>
                <p className="text-[#cbdccf]">Workspace</p>
              </div>
              <div>
                <p className="text-3xl font-semibold">{officialPostgisCount}</p>
                <p className="text-[#cbdccf]">PostGIS ufficiali</p>
              </div>
              <div>
                <p className="text-3xl font-semibold">{inactiveCount}</p>
                <p className="text-[#cbdccf]">Inattivi</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="rounded-[28px] border border-[#d9dfd6] bg-white p-5 shadow-sm">
        <div className="grid gap-3 md:grid-cols-5">
          <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
            Workspace
            <input
              className="form-control mt-2"
              value={filters.workspace}
              onChange={(event) => setFilter("workspace", event.target.value)}
              placeholder="catasto"
            />
          </label>
          <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
            Dominio
            <input
              className="form-control mt-2"
              value={filters.domainModule}
              onChange={(event) => setFilter("domainModule", event.target.value)}
              placeholder="catasto"
            />
          </label>
          <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
            Source
            <input
              className="form-control mt-2"
              value={filters.sourceType}
              onChange={(event) => setFilter("sourceType", event.target.value)}
              placeholder="postgis"
            />
          </label>
          <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
            Ufficiale
            <input
              className="form-control mt-2"
              value={filters.officialSource}
              onChange={(event) => setFilter("officialSource", event.target.value)}
              placeholder="postgis"
            />
          </label>
          <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
            Stato
            <select
              className="form-control mt-2"
              value={filters.active}
              onChange={(event) => setFilter("active", event.target.value)}
            >
              <option value="all">Tutti</option>
              <option value="active">Solo attivi</option>
              <option value="inactive">Solo inattivi</option>
            </select>
          </label>
        </div>
        <div className="mt-4 flex flex-wrap gap-3">
          <button className="btn-primary" type="button" disabled={isLoading} onClick={() => void loadCatalog(filters)}>
            {isLoading ? "Caricamento..." : "Applica filtri"}
          </button>
          <button className="btn-secondary" type="button" disabled={isLoading} onClick={resetFilters}>
            Reset
          </button>
        </div>
      </section>

      {loadError ? (
        <article className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-700">
          {loadError}
        </article>
      ) : null}

      {layers.length === 0 && !isLoading ? (
        <article className="rounded-[28px] border border-dashed border-[#b8cabb] bg-[#f7faf7] p-8 text-center">
          <p className="text-lg font-semibold text-gray-900">Nessun layer nel filtro corrente</p>
          <p className="mt-2 text-sm text-gray-500">Modifica i filtri o verifica i permessi GIS del tuo account.</p>
        </article>
      ) : (
        <div className="grid gap-4">
          {layers.map((layer) => {
            const workspaceHref = domainWorkspaceHref(layer);
            return (
              <article key={layer.id} className="rounded-[28px] border border-[#d9dfd6] bg-white p-5 shadow-sm">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full bg-[#EAF3E8] px-3 py-1 text-xs font-semibold text-[#1D4E35]">
                        {layer.workspace}
                      </span>
                      <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold text-gray-600">
                        {layer.is_active ? "attivo" : "inattivo"}
                      </span>
                      <span className="rounded-full bg-[#eef3f9] px-3 py-1 text-xs font-semibold text-[#315d80]">
                        {layer.effective_access_level}
                      </span>
                    </div>
                    <h3 className="mt-3 text-xl font-semibold text-gray-950">{layer.title}</h3>
                    <p className="mt-1 text-sm text-gray-500">{formatValue(layer.description)}</p>
                    <p className="mt-2 font-mono text-xs text-gray-400">{layer.name}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {workspaceHref ? (
                      <Link className="btn-secondary" href={workspaceHref}>
                        Apri workspace Catasto
                      </Link>
                    ) : null}
                    <button className="btn-secondary cursor-default" type="button" disabled>
                      Read-only
                    </button>
                  </div>
                </div>

                <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  <CatalogFact label="PostGIS" value={`${formatValue(layer.postgis_schema)}.${formatValue(layer.postgis_table)}`} />
                  <CatalogFact label="Geometry" value={`${formatValue(layer.geometry_type)} - SRID ${formatValue(layer.srid)}`} />
                  <CatalogFact label="Martin layer" value={formatValue(layer.martin_layer_id)} />
                  <CatalogFact label="Feature id" value={formatValue(layer.feature_id_column)} />
                  <CatalogFact label="Source type" value={layer.source_type} />
                  <CatalogFact label="Official source" value={layer.official_source} />
                  <CatalogFact label="QGIS mode" value={qgisMode(layer)} />
                  <CatalogFact label="Tile provider" value={tileProvider(layer)} />
                </div>
              </article>
            );
          })}
        </div>
      )}

      {isLoading ? (
        <div className="flex items-center gap-2 rounded-2xl border border-[#d9dfd6] bg-white px-4 py-3 text-sm text-gray-500">
          <RefreshIcon className="h-4 w-4 animate-spin" />
          Caricamento catalogo GIS...
        </div>
      ) : null}
    </div>
  );
}

function CatalogFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-400">{label}</p>
      <p className="mt-2 break-words text-sm font-semibold text-gray-800">{value}</p>
    </div>
  );
}

export default function GisCatalogPage() {
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

  return (
    <ProtectedPage
      title="GIS Platform"
      description="Catalogo centrale read-only dei layer GIS governati da GAIA."
      breadcrumb="GIS Platform / Catalogo"
      requiredModule="catasto"
      hideContentHeader
    >
      <GisCatalogWorkspace token={token} />
    </ProtectedPage>
  );
}
