"use client";

import { useSearchParams } from "next/navigation";
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
import {
  autoLinkGaiaOperators,
  bulkImportOperatorsAsGaiaUsers,
  getAreas,
  getOperatorDetail,
  getOperators,
  getUnlinkedOperators,
  inviteOperator,
  type BulkImportedOperator,
  type BulkImportResult,
  type OperatorDetailResponse,
  type OperatorFuelCardSummary,
} from "@/features/operazioni/api/client";
import type { CurrentUser } from "@/types/api";

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
  current_fuel_cards: OperatorFuelCardSummary[];
};

type GaiaUserMin = {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
};

type UnlinkedOperatorItem = {
  id: string;
  wc_id: number;
  username: string | null;
  email: string | null;
  first_name: string | null;
  last_name: string | null;
  role: string | null;
  enabled: boolean;
  suggested_gaia_user: GaiaUserMin | null;
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

const integerFormatter = new Intl.NumberFormat("it-IT", { maximumFractionDigits: 0 });
const decimalFormatter = new Intl.NumberFormat("it-IT", { minimumFractionDigits: 0, maximumFractionDigits: 1 });
const currencyFormatter = new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 2 });

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

function fuelCardCodes(operator: Pick<OperatorItem, "current_fuel_cards">): string {
  const codes = operator.current_fuel_cards
    .map((card) => card.codice?.trim())
    .filter((value): value is string => Boolean(value));
  if (codes.length === 0) {
    return "Nessuna carta";
  }
  return codes.join(" · ");
}

function isAdminUser(user: CurrentUser): boolean {
  return user.role === "admin" || user.role === "super_admin";
}

function parseNumeric(value: string | null | undefined): number | null {
  if (value == null || value === "") {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatNumeric(value: string | null | undefined, suffix?: string): string {
  const parsed = parseNumeric(value);
  if (parsed == null) {
    return "—";
  }
  const formatted = Number.isInteger(parsed) ? integerFormatter.format(parsed) : decimalFormatter.format(parsed);
  return suffix ? `${formatted} ${suffix}` : formatted;
}

function formatCurrencyValue(value: string | null | undefined): string {
  const parsed = parseNumeric(value);
  return parsed == null ? "—" : currencyFormatter.format(parsed);
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  return date.toLocaleString("it-IT", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function DesktopOperatorCard({
  operator,
  canOpenDetail,
  onOpenDetail,
}: {
  operator: OperatorItem;
  canOpenDetail: boolean;
  onOpenDetail: (operator: OperatorItem) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => (canOpenDetail ? onOpenDetail(operator) : undefined)}
      className={cn(
        "group overflow-hidden rounded-[22px] border border-[#e6ebe5] bg-white text-left shadow-panel transition hover:-translate-y-1 hover:border-[#c9d6cd] hover:shadow-lg",
        canOpenDetail ? "cursor-pointer" : "cursor-default",
      )}
    >
      <div className={cn("relative h-24 overflow-hidden bg-gradient-to-br", operatorVisualTone(operator))}>
        <div className="absolute inset-x-0 top-0 flex items-center justify-between p-2.5">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-white/80 bg-white/90 text-sm font-semibold text-[#1D4E35] shadow-sm">
            {initialsForOperator(operator)}
          </div>
          <span
            className={cn(
              "rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.16em]",
              enabledTone[String(Boolean(operator.enabled)) as "true" | "false"],
            )}
          >
            {operator.enabled ? "Abilitato" : "Disabilitato"}
          </span>
        </div>
        <div className="absolute inset-x-0 bottom-0 h-12 bg-gradient-to-t from-black/5 to-transparent" />
      </div>

      <div className="px-3.5 pb-3.5 pt-2.5">
        <div className="flex items-start justify-between gap-2.5">
          <div className="min-w-0">
            <p className="truncate text-[0.92rem] font-semibold uppercase tracking-tight text-gray-900">
              {displayName(operator)}
            </p>
            <p className="mt-0.5 text-xs text-gray-600">{roleLabel(operator.role)}</p>
          </div>
          <span className="text-base text-gray-300 transition group-hover:text-[#1D4E35]">⋮</span>
        </div>

        <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
          <span className="inline-flex rounded-full border border-[#e2e6e1] bg-[#f6f7f4] px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-[#5d695f]">
            WC {operator.wc_id}
          </span>
          {operator.gaia_user_id ? (
            <span className="inline-flex rounded-full border border-[#e2e6e1] bg-white px-2.5 py-1 text-[11px] font-semibold text-gray-700">
              GAIA {operator.gaia_user_id}
            </span>
          ) : null}
        </div>

        <div className="mt-2 rounded-[16px] border border-[#eef2ec] bg-[#fafbf8] px-2.5 py-2">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Fuel card</p>
          <p className="mt-1 truncate text-[11px] font-medium text-gray-700">{fuelCardCodes(operator)}</p>
        </div>

        <div className="mt-3 border-t border-dashed border-[#edf1eb] pt-2.5">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#667267]">Contatti</p>
          <div className="mt-2 grid gap-1 text-xs text-gray-600">
            <p>
              <span className="font-medium text-gray-900">Email:</span> {operator.email || "—"}
            </p>
            <p>
              <span className="font-medium text-gray-900">CF:</span> {operator.tax || "—"}
            </p>
          </div>
        </div>
      </div>
    </button>
  );
}

function MobileOperatorCard({
  operator,
  canOpenDetail,
  onOpenDetail,
}: {
  operator: OperatorItem;
  canOpenDetail: boolean;
  onOpenDetail: (operator: OperatorItem) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => (canOpenDetail ? onOpenDetail(operator) : undefined)}
      className={cn(
        "flex w-full items-center gap-2.5 rounded-[20px] border border-[#e6ebe5] bg-[linear-gradient(180deg,_#ffffff,_#fbfcfa)] px-3 py-2.5 text-left shadow-panel transition active:scale-[0.995]",
        canOpenDetail ? "cursor-pointer" : "cursor-default",
      )}
    >
      <div
        className={cn(
          "relative flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-[18px] bg-gradient-to-br text-sm font-semibold text-[#1D4E35]",
          operatorVisualTone(operator),
        )}
      >
        <span className="absolute inset-0 bg-white/25" />
        <span className="relative">{initialsForOperator(operator)}</span>
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-[10px] font-semibold uppercase tracking-[0.16em] text-[#667267]">{roleLabel(operator.role)}</p>
            <p className="truncate text-[0.95rem] font-semibold leading-tight text-gray-900">{displayName(operator)}</p>
          </div>
          <span className={cn("shrink-0 rounded-full px-2 py-1 text-[10px] font-semibold", enabledTone[String(Boolean(operator.enabled)) as "true" | "false"])}>
            {operator.enabled ? "Ok" : "Off"}
          </span>
        </div>
        <p className="mt-0.5 truncate text-[11px] text-gray-600">{operatorMeta(operator)}</p>
        <p className="mt-1 truncate text-[11px] font-medium text-[#516053]">Carta: {fuelCardCodes(operator)}</p>
        <div className="mt-2 flex items-center justify-between gap-3">
          <p className="truncate text-xs text-gray-500">
            WC {operator.wc_id}
            {operator.gaia_user_id ? ` · GAIA ${operator.gaia_user_id}` : ""}
          </p>
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-[#f6f7f4] text-xs text-gray-500">→</div>
        </div>
      </div>
    </button>
  );
}

const PREVIEW_COUNT = 6;

function OperatorDetailModal({
  open,
  operator,
  detail,
  isLoading,
  error,
  onClose,
}: {
  open: boolean;
  operator: OperatorItem | null;
  detail: OperatorDetailResponse | null;
  isLoading: boolean;
  error: string | null;
  onClose: () => void;
}) {
  useEffect(() => {
    if (!open) {
      return;
    }
    function handleKeyDown(event: KeyboardEvent): void {
      if (event.key === "Escape") {
        onClose();
      }
    }
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [open, onClose]);

  if (!open || !operator) {
    return null;
  }

  const effectiveDetail = detail?.operator.id === operator.id ? detail : null;
  const subject = effectiveDetail?.operator ?? operator;
  const cards = effectiveDetail?.current_fuel_cards ?? subject.current_fuel_cards ?? [];

  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/45 px-4 py-6 backdrop-blur-sm">
      <div className="flex max-h-[94vh] w-full max-w-5xl flex-col overflow-hidden rounded-[28px] border border-gray-200 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.24)]">
        <div className="border-b border-gray-100 px-6 py-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Dettaglio operatore</p>
              <h2 className="mt-2 text-2xl font-semibold text-gray-900">{displayName(subject)}</h2>
              <p className="mt-1 text-sm text-gray-500">
                {roleLabel(subject.role)} · WC {subject.wc_id}
                {subject.gaia_user_id ? ` · GAIA ${subject.gaia_user_id}` : ""}
              </p>
            </div>
            <button className="btn-secondary" type="button" onClick={onClose}>
              Chiudi
            </button>
          </div>
        </div>

        <div className="overflow-y-auto bg-[#f7faf7] px-6 py-6">
          {isLoading ? (
            <div className="rounded-[24px] border border-[#dfe7df] bg-white px-5 py-6 text-sm text-gray-500">Caricamento dettaglio operatore.</div>
          ) : error ? (
            <div className="rounded-[24px] border border-rose-200 bg-rose-50 px-5 py-6 text-sm text-rose-700">{error}</div>
          ) : !effectiveDetail ? (
            <div className="rounded-[24px] border border-[#dfe7df] bg-white px-5 py-6 text-sm text-gray-500">Nessun dettaglio disponibile.</div>
          ) : (
            <div className="space-y-6">
              <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
                <div className="rounded-[24px] border border-[#e4e8e2] bg-white p-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">KPI operativi</p>
                  <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                    <div className="rounded-[18px] border border-[#eef2ec] bg-[#fafbf8] px-4 py-3">
                      <p className="text-[11px] uppercase tracking-[0.16em] text-gray-500">Carte</p>
                      <p className="mt-2 text-2xl font-semibold text-gray-900">{effectiveDetail.stats.fuel_cards_count}</p>
                    </div>
                    <div className="rounded-[18px] border border-[#eef2ec] bg-[#fafbf8] px-4 py-3">
                      <p className="text-[11px] uppercase tracking-[0.16em] text-gray-500">Litri</p>
                      <p className="mt-2 text-2xl font-semibold text-gray-900">{formatNumeric(effectiveDetail.stats.total_liters, "L")}</p>
                    </div>
                    <div className="rounded-[18px] border border-[#eef2ec] bg-[#fafbf8] px-4 py-3">
                      <p className="text-[11px] uppercase tracking-[0.16em] text-gray-500">Costo</p>
                      <p className="mt-2 text-2xl font-semibold text-gray-900">{formatCurrencyValue(effectiveDetail.stats.total_fuel_cost)}</p>
                    </div>
                    <div className="rounded-[18px] border border-[#eef2ec] bg-[#fafbf8] px-4 py-3">
                      <p className="text-[11px] uppercase tracking-[0.16em] text-gray-500">Km percorsi</p>
                      <p className="mt-2 text-2xl font-semibold text-gray-900">{formatNumeric(effectiveDetail.stats.total_km_travelled, "km")}</p>
                    </div>
                  </div>
                  <div className="mt-3 grid gap-3 sm:grid-cols-2">
                    <div className="rounded-[18px] border border-[#eef2ec] bg-white px-4 py-3">
                      <p className="text-[11px] uppercase tracking-[0.16em] text-gray-500">Utilizzi mezzo</p>
                      <p className="mt-1 text-lg font-semibold text-gray-900">{effectiveDetail.stats.usage_sessions_count}</p>
                      <p className="mt-1 text-xs text-gray-500">Sessioni registrate per questo operatore.</p>
                    </div>
                    <div className="rounded-[18px] border border-[#eef2ec] bg-white px-4 py-3">
                      <p className="text-[11px] uppercase tracking-[0.16em] text-gray-500">Mezzo più usato</p>
                      <p className="mt-1 text-sm font-semibold text-gray-900">{effectiveDetail.stats.most_used_vehicle?.vehicle_label ?? "—"}</p>
                      <p className="mt-1 text-xs text-gray-500">
                        {effectiveDetail.stats.most_used_vehicle
                          ? `${effectiveDetail.stats.most_used_vehicle.usage_count} utilizzi · ${formatNumeric(effectiveDetail.stats.most_used_vehicle.km_travelled, "km")}`
                          : "Nessuna sessione mezzo disponibile."}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="rounded-[24px] border border-[#e4e8e2] bg-white p-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Profilo</p>
                  <div className="mt-4 space-y-3 text-sm text-gray-600">
                    <p><span className="font-medium text-gray-900">Email:</span> {subject.email || "—"}</p>
                    <p><span className="font-medium text-gray-900">Username:</span> {subject.username || "—"}</p>
                    <p><span className="font-medium text-gray-900">Codice fiscale:</span> {subject.tax || "—"}</p>
                    <p><span className="font-medium text-gray-900">Stato:</span> {subject.enabled ? "Abilitato" : "Disabilitato"}</p>
                    <p><span className="font-medium text-gray-900">Ultimo mezzo usato:</span> {effectiveDetail.stats.last_used_vehicle_label ?? "—"}</p>
                  </div>
                  <div className="mt-5 rounded-[18px] border border-[#eef2ec] bg-[#fafbf8] px-4 py-3">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#667267]">Fuel card correnti</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {cards.length > 0 ? cards.map((card) => (
                        <span key={card.id} className="rounded-full border border-[#d5e2d8] bg-white px-3 py-1 text-xs font-semibold text-[#1D4E35]">
                          {card.codice || card.pan}
                        </span>
                      )) : <span className="text-xs text-gray-500">Nessuna carta assegnata.</span>}
                    </div>
                  </div>
                </div>
              </div>

              <div className="grid gap-4 xl:grid-cols-2">
                <div className="rounded-[24px] border border-[#e4e8e2] bg-white p-5">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Ultimi rifornimenti</p>
                    <span className="text-xs text-gray-500">{effectiveDetail.recent_fuel_logs.length} record</span>
                  </div>
                  <div className="mt-4 space-y-3">
                    {effectiveDetail.recent_fuel_logs.length > 0 ? effectiveDetail.recent_fuel_logs.map((item) => (
                      <div key={item.id} className="rounded-[18px] border border-[#eef2ec] bg-[#fafbf8] px-4 py-3">
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div>
                            <p className="text-sm font-semibold text-gray-900">{item.vehicle_label}</p>
                            <p className="mt-0.5 text-xs text-gray-500">{formatDateTime(item.fueled_at)}{item.station_name ? ` · ${item.station_name}` : ""}</p>
                          </div>
                          <span className="rounded-full border border-[#d5e2d8] bg-white px-2.5 py-1 text-xs font-semibold text-[#1D4E35]">
                            {formatNumeric(item.liters, "L")}
                          </span>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-600">
                          <span>Costo {formatCurrencyValue(item.total_cost)}</span>
                          <span>Km {formatNumeric(item.odometer_km)}</span>
                        </div>
                      </div>
                    )) : <p className="text-sm text-gray-500">Nessun dato carburante disponibile.</p>}
                  </div>
                </div>

                <div className="rounded-[24px] border border-[#e4e8e2] bg-white p-5">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Ultimi utilizzi mezzo</p>
                    <span className="text-xs text-gray-500">{effectiveDetail.recent_usage_sessions.length} record</span>
                  </div>
                  <div className="mt-4 space-y-3">
                    {effectiveDetail.recent_usage_sessions.length > 0 ? effectiveDetail.recent_usage_sessions.map((item) => (
                      <div key={item.id} className="rounded-[18px] border border-[#eef2ec] bg-[#fafbf8] px-4 py-3">
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div>
                            <p className="text-sm font-semibold text-gray-900">{item.vehicle_label}</p>
                            <p className="mt-0.5 text-xs text-gray-500">Inizio {formatDateTime(item.started_at)} · Fine {formatDateTime(item.ended_at)}</p>
                          </div>
                          <span className={cn("rounded-full px-2.5 py-1 text-xs font-semibold", item.status === "open" ? "bg-amber-100 text-amber-800" : "bg-emerald-50 text-emerald-700")}>
                            {item.status}
                          </span>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-600">
                          <span>Km sessione {formatNumeric(item.km_travelled, "km")}</span>
                        </div>
                      </div>
                    )) : <p className="text-sm text-gray-500">Nessun utilizzo mezzo disponibile.</p>}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function CredentialsTable({ operators, onClose }: { operators: BulkImportedOperator[]; onClose: () => void }) {
  const [copied, setCopied] = useState(false);
  const created = operators.filter((op) => !op.skipped);

  const copyAll = useCallback(() => {
    const rows = created.map((op) => `${op.full_name}\t${op.username}\t${op.temp_password}`).join("\n");
    const header = "Nome\tUsername\tPassword temporanea\n";
    void navigator.clipboard.writeText(header + rows).then(() => {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    });
  }, [created]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-gray-900">
            {created.length} account creati
            {operators.length - created.length > 0 && (
              <span className="ml-2 text-xs font-normal text-gray-500">
                ({operators.length - created.length} saltati — nome/username mancanti)
              </span>
            )}
          </p>
          <p className="mt-0.5 text-xs text-gray-500">
            Copia la tabella e distribuisci le credenziali agli operatori. Le password temporanee devono essere cambiate al primo accesso.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={copyAll}
            className="rounded-full border border-[#1D4E35] bg-[#1D4E35] px-4 py-2 text-xs font-semibold text-white transition hover:bg-[#163d2a]"
          >
            {copied ? "Copiato!" : "Copia tutto"}
          </button>
          <button
            onClick={onClose}
            className="rounded-full border border-gray-200 bg-white px-4 py-2 text-xs font-semibold text-gray-700 transition hover:bg-gray-50"
          >
            Chiudi
          </button>
        </div>
      </div>

      <div className="overflow-x-auto rounded-[16px] border border-[#e6ebe5]">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#e6ebe5] bg-[#f9faf8]">
              <th className="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500">Nome</th>
              <th className="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500">Username</th>
              <th className="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500">Password temporanea</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#f0f3ef]">
            {created.map((op) => (
              <tr key={op.wc_operator_id} className="bg-white hover:bg-[#f9faf8]">
                <td className="px-4 py-2.5 text-gray-900">{op.full_name}</td>
                <td className="px-4 py-2.5 font-mono text-[13px] text-gray-700">{op.username}</td>
                <td className="px-4 py-2.5 font-mono text-[13px] text-emerald-700">{op.temp_password}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RiconciliazioneGaia() {
  const [unlinked, setUnlinked] = useState<UnlinkedOperatorItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [autoLinkStatus, setAutoLinkStatus] = useState<string | null>(null);
  const [invitingId, setInvitingId] = useState<string | null>(null);
  const [inviteLinks, setInviteLinks] = useState<Record<string, string>>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [bulkImporting, setBulkImporting] = useState(false);
  const [bulkResult, setBulkResult] = useState<BulkImportResult | null>(null);
  const [bulkError, setBulkError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await getUnlinkedOperators() as { items: UnlinkedOperatorItem[]; total: number };
      setUnlinked(data.items ?? []);
    } catch {
      // ignore
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const handleAutoLink = useCallback(async () => {
    setAutoLinkStatus("In corso...");
    try {
      const result = await autoLinkGaiaOperators();
      setAutoLinkStatus(`Collegati ${result.linked}, non abbinabili: ${result.skipped}.`);
      void load();
    } catch (error) {
      setAutoLinkStatus(error instanceof Error ? error.message : "Errore");
    }
  }, [load]);

  const handleBulkImport = useCallback(async () => {
    setBulkImporting(true);
    setBulkError(null);
    try {
      const result = await bulkImportOperatorsAsGaiaUsers();
      setBulkResult(result);
      void load();
    } catch (error) {
      setBulkError(error instanceof Error ? error.message : "Errore durante l'importazione");
    } finally {
      setBulkImporting(false);
    }
  }, [load]);

  const handleInvite = useCallback(async (operatorId: string) => {
    setInvitingId(operatorId);
    try {
      const result = await inviteOperator(operatorId);
      const url = `${window.location.origin}${result.activation_url_path}`;
      setInviteLinks((prev) => ({ ...prev, [operatorId]: url }));
    } catch {
      // ignore
    } finally {
      setInvitingId(null);
    }
  }, []);

  const handleCopy = useCallback((operatorId: string, url: string) => {
    void navigator.clipboard.writeText(url).then(() => {
      setCopiedId(operatorId);
      window.setTimeout(() => setCopiedId(null), 2000);
    });
  }, []);

  if (isLoading) return null;
  if (unlinked.length === 0 && !bulkResult) return null;

  const preview = unlinked.slice(0, PREVIEW_COUNT);

  return (
    <OperazioniCollectionPanel
      title="Riconciliazione GAIA"
      description={
        bulkResult
          ? `Importazione completata: ${bulkResult.created} account creati.`
          : `${unlinked.length} operatori WC senza account GAIA.`
      }
      count={bulkResult ? bulkResult.created : unlinked.length}
    >
      {bulkResult ? (
        <CredentialsTable
          operators={bulkResult.operators}
          onClose={() => { setBulkResult(null); void load(); }}
        />
      ) : (
        <>
          {/* primary CTA */}
          <div className="rounded-[20px] border border-amber-200 bg-gradient-to-br from-amber-50 to-white p-4">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold text-gray-900">
                  Importa tutti gli operatori come utenti GAIA
                </p>
                <p className="mt-1 text-xs text-gray-600">
                  Crea un account con ruolo <span className="font-mono font-semibold">operator</span> per ognuno dei {unlinked.length} operatori WC non collegati.
                  Verranno generate password temporanee che potrai distribuire manualmente.
                </p>
              </div>
              <button
                disabled={bulkImporting}
                onClick={() => void handleBulkImport()}
                className="shrink-0 rounded-full bg-[#1D4E35] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#163d2a] disabled:opacity-50"
              >
                {bulkImporting ? "Importazione in corso..." : `Importa tutti (${unlinked.length})`}
              </button>
            </div>
            {bulkError && (
              <p className="mt-3 rounded-[10px] border border-rose-100 bg-rose-50 px-3 py-2 text-xs text-rose-700">{bulkError}</p>
            )}
          </div>

          {/* secondary actions */}
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              onClick={() => void handleAutoLink()}
              className="rounded-full border border-gray-300 bg-white px-4 py-2 text-xs font-semibold text-gray-700 transition hover:bg-gray-50"
            >
              Auto-collega per email / username
            </button>
            {autoLinkStatus && (
              <span className="text-sm text-gray-600">{autoLinkStatus}</span>
            )}
          </div>

          {/* preview cards */}
          <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {preview.map((op) => {
              const name = [op.last_name, op.first_name].filter(Boolean).join(" ") || op.username || `WC ${op.wc_id}`;
              const initials = name.split(/\s+/).filter(Boolean).map((p) => p[0]).join("").slice(0, 2).toUpperCase();
              const inviteUrl = inviteLinks[op.id];
              return (
                <div
                  key={op.id}
                  className="flex flex-col gap-3 overflow-hidden rounded-[24px] border border-amber-100 bg-gradient-to-br from-amber-50 via-white to-white p-4 shadow-sm"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[14px] border border-amber-200 bg-white text-sm font-semibold text-amber-700 shadow-sm">
                      {initials}
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-[0.9rem] font-semibold text-gray-900">{name}</p>
                      <p className="truncate text-xs text-gray-500">{op.role ?? "—"} · WC {op.wc_id}</p>
                    </div>
                    <span className={cn(
                      "ml-auto shrink-0 rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide",
                      op.enabled ? "bg-emerald-50 text-emerald-700" : "bg-gray-100 text-gray-500"
                    )}>
                      {op.enabled ? "Attivo" : "Off"}
                    </span>
                  </div>

                  {op.email && <p className="truncate text-xs text-gray-500">{op.email}</p>}

                  {inviteUrl ? (
                    <div className="space-y-1.5">
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-emerald-700">Link di attivazione</p>
                      <div className="flex items-center gap-2 rounded-[10px] border border-emerald-100 bg-emerald-50 px-2.5 py-2">
                        <p className="min-w-0 flex-1 truncate text-[11px] text-emerald-800 font-mono">{inviteUrl}</p>
                        <button
                          onClick={() => handleCopy(op.id, inviteUrl)}
                          className="shrink-0 rounded-full border border-emerald-200 bg-white px-2.5 py-1 text-[10px] font-semibold text-emerald-700 transition hover:bg-emerald-100"
                        >
                          {copiedId === op.id ? "Copiato!" : "Copia"}
                        </button>
                      </div>
                      <p className="text-[10px] text-gray-400">Condividi questo link con l&apos;operatore. Scade in 7 giorni.</p>
                    </div>
                  ) : (
                    <button
                      disabled={invitingId === op.id}
                      onClick={() => void handleInvite(op.id)}
                      className="w-full rounded-full border border-amber-300 bg-amber-50 py-2 text-xs font-semibold text-amber-800 transition hover:bg-amber-100 disabled:opacity-50"
                    >
                      {invitingId === op.id ? "Generazione link..." : "Genera link di attivazione"}
                    </button>
                  )}
                </div>
              );
            })}
          </div>

          {unlinked.length > PREVIEW_COUNT && (
            <p className="mt-3 text-xs text-gray-400">
              Anteprima dei primi {PREVIEW_COUNT} su {unlinked.length}. Usa &quot;Importa tutti&quot; per creare account per tutti gli operatori in una volta sola.
            </p>
          )}
        </>
      )}
    </OperazioniCollectionPanel>
  );
}

function normalizeSearch(value: string): string {
  return value.trim();
}

function sortByCountThenLabel<T extends { label: string; count: number }>(items: T[]): T[] {
  return [...items].sort((a, b) => (b.count - a.count) || a.label.localeCompare(b.label, "it"));
}

function OperatoriContent({ currentUser }: { currentUser: CurrentUser }) {
  const searchParams = useSearchParams();
  const [operators, setOperators] = useState<OperatorItem[]>([]);
  const [operatorsTotal, setOperatorsTotal] = useState(0);
  const [areas, setAreas] = useState<AreaItem[]>([]);
  const [areasTotal, setAreasTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [enabledFilter, setEnabledFilter] = useState("");
  const [selectedOperator, setSelectedOperator] = useState<OperatorItem | null>(null);
  const [operatorDetail, setOperatorDetail] = useState<OperatorDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [autoOpenedOperatorId, setAutoOpenedOperatorId] = useState<string | null>(null);

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

  const canOpenAdminDetail = isAdminUser(currentUser);
  const requestedOperatorId = searchParams.get("operatorId");

  const handleOpenDetail = useCallback((operator: OperatorItem) => {
    if (!canOpenAdminDetail) {
      return;
    }
    setSelectedOperator(operator);
    setOperatorDetail(null);
    setDetailError(null);
    setDetailLoading(true);
    void getOperatorDetail(operator.id)
      .then((payload) => {
        setOperatorDetail(payload);
        setDetailError(null);
      })
      .catch((error) => {
        setDetailError(error instanceof Error ? error.message : "Errore nel caricamento dettaglio operatore");
      })
      .finally(() => setDetailLoading(false));
  }, [canOpenAdminDetail]);

  const handleCloseDetail = useCallback(() => {
    setSelectedOperator(null);
    setOperatorDetail(null);
    setDetailError(null);
    setDetailLoading(false);
  }, []);

  useEffect(() => {
    if (!canOpenAdminDetail || !requestedOperatorId || autoOpenedOperatorId === requestedOperatorId) {
      return;
    }
    const operator = operators.find((item) => item.id === requestedOperatorId);
    if (!operator) {
      return;
    }
    handleOpenDetail(operator);
    setAutoOpenedOperatorId(requestedOperatorId);
  }, [autoOpenedOperatorId, canOpenAdminDetail, handleOpenDetail, operators, requestedOperatorId]);

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

      <RiconciliazioneGaia />

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
              {canOpenAdminDetail
                ? "Usa il filtro ruolo e clicca una card per aprire il dettaglio admin con carte, consumi e utilizzo mezzi."
                : "Usa il filtro ruolo per costruire rapidamente l&apos;organigramma utenti qui sotto."}
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
              <div className="hidden gap-4 lg:grid xl:grid-cols-3">
                {operators.map((operator) => (
                  <DesktopOperatorCard
                    key={operator.id}
                    operator={operator}
                    canOpenDetail={canOpenAdminDetail}
                    onOpenDetail={handleOpenDetail}
                  />
                ))}
              </div>
              <div className="space-y-3 lg:hidden">
                {operators.map((operator) => (
                  <MobileOperatorCard
                    key={operator.id}
                    operator={operator}
                    canOpenDetail={canOpenAdminDetail}
                    onOpenDetail={handleOpenDetail}
                  />
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

      <OperatorDetailModal
        open={selectedOperator != null}
        operator={selectedOperator}
        detail={operatorDetail}
        isLoading={detailLoading}
        error={detailError}
        onClose={handleCloseDetail}
      />
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
      {({ currentUser }) => <OperatoriContent currentUser={currentUser} />}
    </OperazioniModulePage>
  );
}
