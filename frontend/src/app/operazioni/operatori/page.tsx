"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  OperazioniCollectionHero,
  OperazioniCollectionPanel,
  OperazioniHeroNotice,
  OperazioniMetricStrip,
  OperazioniToolbar,
} from "@/components/operazioni/collection-layout";
import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { EmptyState } from "@/components/ui/empty-state";
import { MetricCard } from "@/components/ui/metric-card";
import { UsersIcon } from "@/components/ui/icons";
import { cn } from "@/lib/cn";
import { getAreas, getOperators } from "@/features/operazioni/api/client";

type OperatorItem = {
  id: string;
  wc_id: number;
  username: string | null;
  email: string | null;
  first_name: string | null;
  last_name: string | null;
  tax: string | null;
  role: string | null;
  enabled: boolean;
  gaia_user_id: number | null;
  wc_synced_at: string | null;
  created_at: string;
  updated_at: string;
};

type AreaItem = {
  id: string;
  wc_id: number;
  name: string;
  color: string | null;
  is_district: boolean;
  description: string | null;
};

const enabledTone = {
  true: "bg-emerald-50 text-emerald-700",
  false: "bg-gray-100 text-gray-600",
};

function displayName(operator: OperatorItem): string {
  const name = `${operator.first_name ?? ""} ${operator.last_name ?? ""}`.trim();
  return name || operator.username || operator.email || `Operatore ${operator.wc_id}`;
}

function operatorMeta(operator: OperatorItem): string {
  const parts = [
    operator.role ? operator.role.replaceAll("_", " ") : null,
    operator.email,
    operator.tax,
    operator.gaia_user_id ? `GAIA ${operator.gaia_user_id}` : null,
  ].filter(Boolean) as string[];
  return parts.join(" · ") || "—";
}

function initialsForOperator(operator: OperatorItem): string {
  const source = displayName(operator);
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }
  return `${parts[0][0] ?? ""}${parts[1][0] ?? ""}`.toUpperCase();
}

function operatorVisualTone(operator: OperatorItem): string {
  if (!operator.enabled) return "from-gray-50 via-white to-white";
  if (operator.role?.toLowerCase().includes("admin")) return "from-sky-50 via-white to-white";
  if (operator.role?.toLowerCase().includes("capo")) return "from-amber-50 via-white to-white";
  return "from-emerald-50 via-white to-white";
}

function roleLabel(role: string | null): string {
  return role ? role.replaceAll("_", " ") : "Senza ruolo";
}

function DesktopOperatorCard({ operator }: { operator: OperatorItem }) {
  return (
    <div className="group overflow-hidden rounded-[24px] border border-[#e6ebe5] bg-white shadow-panel transition hover:-translate-y-1 hover:border-[#c9d6cd] hover:shadow-lg">
      <div className={cn("relative h-28 overflow-hidden bg-gradient-to-br", operatorVisualTone(operator))}>
        <div className="absolute inset-x-0 top-0 flex items-center justify-between p-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-[18px] border border-white/80 bg-white/90 text-base font-semibold text-[#1D4E35] shadow-sm">
            {initialsForOperator(operator)}
          </div>
          <span
            className={cn(
              "rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em]",
              enabledTone[String(Boolean(operator.enabled)) as "true" | "false"],
            )}
          >
            {operator.enabled ? "Abilitato" : "Disabilitato"}
          </span>
        </div>
        <div className="absolute inset-x-0 bottom-0 h-14 bg-gradient-to-t from-black/5 to-transparent" />
      </div>

      <div className="px-4 pb-4 pt-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-[0.98rem] font-semibold uppercase tracking-tight text-gray-900">
              {displayName(operator)}
            </p>
            <p className="mt-1 text-[13px] text-gray-600">{roleLabel(operator.role)}</p>
          </div>
          <span className="text-lg text-gray-300 transition group-hover:text-[#1D4E35]">⋮</span>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="inline-flex rounded-full border border-[#e2e6e1] bg-[#f6f7f4] px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-[#5d695f]">
            WC {operator.wc_id}
          </span>
          {operator.gaia_user_id ? (
            <span className="inline-flex rounded-full border border-[#e2e6e1] bg-white px-3 py-1 text-xs font-semibold text-gray-700">
              GAIA {operator.gaia_user_id}
            </span>
          ) : null}
        </div>

        <div className="mt-4 border-t border-dashed border-[#edf1eb] pt-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#667267]">Contatti</p>
          <div className="mt-2.5 grid gap-1.5 text-[13px] text-gray-600">
            <p>
              <span className="font-medium text-gray-900">Email:</span> {operator.email || "—"}
            </p>
            <p>
              <span className="font-medium text-gray-900">CF:</span> {operator.tax || "—"}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function MobileOperatorCard({ operator }: { operator: OperatorItem }) {
  return (
    <div className="flex items-center gap-3 rounded-[22px] border border-[#e6ebe5] bg-[linear-gradient(180deg,_#ffffff,_#fbfcfa)] px-3 py-3 shadow-panel transition active:scale-[0.995]">
      <div
        className={cn(
          "relative flex h-[52px] w-[52px] shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-gradient-to-br text-sm font-semibold text-[#1D4E35]",
          operatorVisualTone(operator),
        )}
      >
        <span className="absolute inset-0 bg-white/25" />
        <span className="relative">{initialsForOperator(operator)}</span>
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">{roleLabel(operator.role)}</p>
            <p className="truncate text-[1rem] font-semibold leading-tight text-gray-900">{displayName(operator)}</p>
          </div>
          <span className={cn("shrink-0 rounded-full px-2.5 py-1 text-[11px] font-semibold", enabledTone[String(Boolean(operator.enabled)) as "true" | "false"])}>
            {operator.enabled ? "Ok" : "Off"}
          </span>
        </div>
        <p className="mt-1 text-xs text-gray-600">{operatorMeta(operator)}</p>
        <div className="mt-2.5 flex items-center justify-between gap-3">
          <p className="truncate text-xs text-gray-500">
            WC {operator.wc_id}
            {operator.gaia_user_id ? ` · GAIA ${operator.gaia_user_id}` : ""}
          </p>
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-[#f6f7f4] text-gray-500">→</div>
        </div>
      </div>
    </div>
  );
}

function normalizeSearch(value: string): string {
  return value.trim();
}

function sortByCountThenLabel<T extends { label: string; count: number }>(items: T[]): T[] {
  return [...items].sort((a, b) => (b.count - a.count) || a.label.localeCompare(b.label, "it"));
}

function OperatoriContent() {
  const [operators, setOperators] = useState<OperatorItem[]>([]);
  const [operatorsTotal, setOperatorsTotal] = useState(0);
  const [areas, setAreas] = useState<AreaItem[]>([]);
  const [areasTotal, setAreasTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [enabledFilter, setEnabledFilter] = useState("");

  const loadData = useCallback(async () => {
    try {
      const operatorParams: Record<string, string> = { page_size: "50" };
      const normalized = normalizeSearch(search);
      if (normalized) operatorParams.search = normalized;
      if (roleFilter) operatorParams.role = roleFilter;
      if (enabledFilter) operatorParams.enabled = enabledFilter;

      const areaParams: Record<string, string> = { page_size: "100" };

      const [opData, areaData] = await Promise.all([getOperators(operatorParams), getAreas(areaParams)]);

      setOperators((opData.items ?? []) as OperatorItem[]);
      setOperatorsTotal((opData.total ?? opData.items?.length ?? 0) as number);
      setAreas((areaData.items ?? []) as AreaItem[]);
      setAreasTotal((areaData.total ?? areaData.items?.length ?? 0) as number);
      setLoadError(null);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore nel caricamento operatori");
    } finally {
      setIsLoading(false);
    }
  }, [enabledFilter, roleFilter, search]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const metrics = useMemo(() => {
    const enabledCount = operators.filter((op) => op.enabled).length;
    const disabledCount = operators.length - enabledCount;
    const roles = sortByCountThenLabel(
      Object.entries(
        operators.reduce<Record<string, number>>((acc, operator) => {
          const key = operator.role?.trim() || "Senza ruolo";
          acc[key] = (acc[key] ?? 0) + 1;
          return acc;
        }, {}),
      ).map(([label, count]) => ({ label, count })),
    );

    return {
      enabledCount,
      disabledCount,
      topRole: roles[0]?.label ?? "—",
      roleCount: roles.length,
    };
  }, [operators]);

  const roleOptions = useMemo(() => {
    const uniqueRoles = Array.from(
      new Set(operators.map((op) => op.role).filter((value): value is string => Boolean(value?.trim()))),
    ).sort((a, b) => a.localeCompare(b, "it"));

    return [
      { value: "", label: "Tutti i ruoli" },
      ...uniqueRoles.map((role) => ({ value: role, label: role.replaceAll("_", " ") })),
    ];
  }, [operators]);

  const districts = useMemo(() => areas.filter((area) => area.is_district), [areas]);
  const nonDistrictAreas = useMemo(() => areas.filter((area) => !area.is_district), [areas]);

  const orgUsersByRole = useMemo(() => {
    const grouped = operators.reduce<Record<string, OperatorItem[]>>((acc, operator) => {
      const key = operator.role?.trim() || "Senza ruolo";
      acc[key] = acc[key] ?? [];
      acc[key].push(operator);
      return acc;
    }, {});
    return Object.entries(grouped)
      .map(([role, items]) => ({
        role,
        items: items.sort((a, b) => displayName(a).localeCompare(displayName(b), "it")),
      }))
      .sort((a, b) => b.items.length - a.items.length || a.role.localeCompare(b.role, "it"));
  }, [operators]);

  return (
    <div className="page-stack">
      <OperazioniCollectionHero
        eyebrow="Anagrafica e organigramma"
        icon={<UsersIcon className="h-3.5 w-3.5" />}
        title="Operatori e struttura: ruoli, abilitazioni e aree operative sempre leggibili."
        description="Una pagina unica per consultare la lista operatori, l'organigramma per ruolo e la struttura delle aree (distretti e sotto-aree)."
      >
        {loadError ? (
          <OperazioniHeroNotice title="Caricamento non riuscito" description={loadError} tone="danger" />
        ) : (
          <OperazioniHeroNotice
            title="Sintesi"
            description={`${metrics.enabledCount} operatori abilitati, ${metrics.disabledCount} disabilitati · ${areasTotal} aree · ruolo principale: ${metrics.topRole}.`}
          />
        )}
        <div className="rounded-2xl border border-white/80 bg-white/75 px-4 py-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">Filtro attivo</p>
          <p className="mt-2 text-sm font-medium text-gray-900">
            {roleFilter ? roleFilter.replaceAll("_", " ") : "Tutti i ruoli"}
          </p>
          <p className="mt-1 text-sm text-gray-600">
            {normalizeSearch(search) ? `Ricerca: ${normalizeSearch(search)}` : "Nessuna ricerca testuale applicata."}
          </p>
        </div>
      </OperazioniCollectionHero>

      <OperazioniMetricStrip>
        <MetricCard label="Operatori" value={operatorsTotal} sub="in anagrafica" />
        <MetricCard label="Abilitati" value={metrics.enabledCount} sub="attivi" variant="success" />
        <MetricCard label="Disabilitati" value={metrics.disabledCount} sub="non attivi" />
        <MetricCard label="Ruoli" value={metrics.roleCount} sub="raggruppamenti" variant="info" />
      </OperazioniMetricStrip>

      <OperazioniCollectionPanel
        title="Operatori"
        description="Ricerca per nome, email, username o CF; filtri rapidi per ruolo e abilitazione."
        count={operators.length}
      >
        <OperazioniToolbar
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder="Cerca per nome, email, username o CF"
          filterValue={roleFilter}
          onFilterChange={setRoleFilter}
          filterOptions={roleOptions}
        />
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <label className="block">
            <span className="label-caption">Abilitazione</span>
            <select
              className="form-control mt-2"
              value={enabledFilter}
              onChange={(event) => setEnabledFilter(event.target.value)}
            >
              <option value="">Tutti</option>
              <option value="true">Solo abilitati</option>
              <option value="false">Solo disabilitati</option>
            </select>
          </label>
          <div className="rounded-[24px] border border-[#e4e8e2] bg-[#fcfcf9] p-3">
            <p className="label-caption">Suggerimento</p>
            <p className="mt-2 text-sm text-gray-600">
              Usa il filtro ruolo per costruire rapidamente l&apos;organigramma utenti qui sotto.
            </p>
          </div>
        </div>

        <div className="mt-4">
          {isLoading ? (
            <p className="text-sm text-gray-500">Caricamento operatori in corso.</p>
          ) : operators.length === 0 ? (
            <EmptyState icon={UsersIcon} title="Nessun operatore trovato" description="Non risultano operatori con i filtri correnti." />
          ) : (
            <>
              <div className="hidden gap-5 lg:grid xl:grid-cols-3">
                {operators.map((operator) => (
                  <DesktopOperatorCard key={operator.id} operator={operator} />
                ))}
              </div>
              <div className="space-y-3 lg:hidden">
                {operators.map((operator) => (
                  <MobileOperatorCard key={operator.id} operator={operator} />
                ))}
              </div>
            </>
          )}
        </div>
      </OperazioniCollectionPanel>

      <div className="grid gap-6 xl:grid-cols-2">
        <OperazioniCollectionPanel
          title="Organigramma aree"
          description="Struttura per distretti (se presenti) e lista aree operative."
          count={areas.length}
        >
          {isLoading ? (
            <p className="text-sm text-gray-500">Caricamento aree in corso.</p>
          ) : areas.length === 0 ? (
            <EmptyState icon={UsersIcon} title="Nessuna area trovata" description="Non risultano aree censite nel modulo." />
          ) : (
            <div className="space-y-5">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#5f6d61]">Distretti</p>
                <div className="mt-3 grid gap-2">
                  {districts.length === 0 ? (
                    <p className="text-sm text-gray-500">Nessun distretto marcato (`is_district=false` per tutte le aree).</p>
                  ) : (
                    districts.map((area) => (
                      <div
                        key={area.id}
                        className="flex items-start justify-between gap-3 rounded-[22px] border border-[#e6ebe5] bg-[linear-gradient(180deg,_#ffffff,_#fbfcfa)] px-4 py-3"
                      >
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold text-gray-900">{area.name}</p>
                          <p className="mt-1 truncate text-xs leading-5 text-gray-500">{area.description || "—"}</p>
                        </div>
                        <span
                          className={cn(
                            "mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-[#e2e6e1] text-[10px] font-semibold text-gray-700",
                            area.color ? "bg-white" : "bg-[#f6f7f4]",
                          )}
                          style={area.color ? { backgroundColor: `${area.color}20`, borderColor: `${area.color}55` } : undefined}
                          aria-label={area.color ? `Colore area ${area.color}` : "Colore non definito"}
                          title={area.color ?? undefined}
                        >
                          {area.color ? "●" : "—"}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#5f6d61]">Aree operative</p>
                <div className="mt-3 grid gap-2">
                  {nonDistrictAreas.map((area) => (
                    <div
                      key={area.id}
                      className="flex items-start justify-between gap-3 rounded-[22px] border border-[#e6ebe5] bg-[linear-gradient(180deg,_#ffffff,_#fbfcfa)] px-4 py-3"
                    >
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-gray-900">{area.name}</p>
                        <p className="mt-1 truncate text-xs leading-5 text-gray-500">{area.description || "—"}</p>
                      </div>
                      <span className="rounded-full border border-[#d5e2d8] bg-[#edf5f0] px-2.5 py-1 text-xs font-semibold text-[#1D4E35]">
                        WC {area.wc_id}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </OperazioniCollectionPanel>

        <OperazioniCollectionPanel
          title="Organigramma utenti"
          description="Operatori raggruppati per ruolo (ordinati per numerosità)."
          count={orgUsersByRole.length}
        >
          {isLoading ? (
            <p className="text-sm text-gray-500">Calcolo organigramma in corso.</p>
          ) : operators.length === 0 ? (
            <EmptyState icon={UsersIcon} title="Nessun operatore" description="Carica prima la lista operatori per visualizzare l'organigramma." />
          ) : (
            <div className="space-y-4">
              {orgUsersByRole.map((group) => (
                <div key={group.role} className="rounded-[24px] border border-[#e6ebe5] bg-[#fbfcfa] p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="text-sm font-semibold text-gray-900">{group.role.replaceAll("_", " ")}</p>
                    <span className="rounded-full border border-[#d5e2d8] bg-white px-3 py-1 text-xs font-semibold text-[#1D4E35]">
                      {group.items.length}
                    </span>
                  </div>
                  <div className="mt-3 grid gap-2">
                    {group.items.slice(0, 12).map((operator) => (
                      <div
                        key={operator.id}
                        className="flex items-center justify-between gap-3 rounded-[18px] border border-[#e6ebe5] bg-white px-3 py-2"
                      >
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-gray-900">{displayName(operator)}</p>
                          <p className="mt-0.5 truncate text-xs text-gray-500">{operator.email ?? operator.username ?? "—"}</p>
                        </div>
                        <span className={cn("rounded-full px-2.5 py-1 text-xs font-semibold", operator.enabled ? enabledTone.true : enabledTone.false)}>
                          {operator.enabled ? "Ok" : "Off"}
                        </span>
                      </div>
                    ))}
                    {group.items.length > 12 ? (
                      <p className="pt-2 text-xs text-gray-500">
                        Mostrati i primi 12 utenti (totale {group.items.length}). Applica filtri sopra per restringere.
                      </p>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          )}
        </OperazioniCollectionPanel>
      </div>
    </div>
  );
}

export default function OperatoriPage() {
  return (
    <OperazioniModulePage
      title="Operatori"
      description="Anagrafica operatori, ruoli, abilitazioni e organigramma aree/utenti."
      breadcrumb="Lista"
    >
      {() => <OperatoriContent />}
    </OperazioniModulePage>
  );
}

