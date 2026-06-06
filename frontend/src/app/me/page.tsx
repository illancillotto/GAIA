"use client";

import { useEffect, useMemo, useState } from "react";
import * as XLSX from "xlsx";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { ProtectedPage } from "@/components/app/protected-page";
import { Badge } from "@/components/ui/badge";
import { MetricCard } from "@/components/ui/metric-card";
import {
  getMeInazDailyRecord,
  getMeInazStatus,
  getMeInazSummary,
  getMeOperazioniSummary,
  getMeStatus,
  getMeSummary,
  isAuthError,
  listMeAssignedDevices,
  listMeInazDailyRecords,
  listMeOperazioniActivities,
  listMeOperazioniCases,
  listMeOperazioniReports,
  listMeVehicleAssignments,
  listMeVehicleSessions,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type {
  InazDailyRecord,
  InazEventSummary,
  MeAssignedDevice,
  MeInazStatusResponse,
  MeModuleStatusResponse,
  MeOperazioniActivity,
  MeOperazioniCase,
  MeOperazioniReport,
  MeOperazioniSummaryResponse,
  MeSummaryResponse,
  MeVehicleAssignment,
  MeVehicleUsageSession,
} from "@/types/api";

type MeTabKey = "overview" | "presenze" | "operativita" | "dotazioni" | "anomalie";
type PeriodPreset = "current" | "previous" | "quarter" | "year";
type OperativitaSectionFilter = "all" | "activities" | "reports" | "cases" | "vehicles";
type OperativitaDetailState =
  | { kind: "activity"; item: MeOperazioniActivity }
  | { kind: "report"; item: MeOperazioniReport }
  | { kind: "case"; item: MeOperazioniCase }
  | { kind: "vehicle"; item: MeVehicleUsageSession };

function monthBounds(offsetMonths = 0): { start: string; end: string } {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth() + offsetMonths, 1);
  const end = new Date(now.getFullYear(), now.getMonth() + offsetMonths + 1, 0);
  const format = (value: Date) =>
    `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
  return { start: format(start), end: format(end) };
}

function quarterBounds(): { start: string; end: string } {
  const now = new Date();
  const quarterStartMonth = Math.floor(now.getMonth() / 3) * 3;
  const start = new Date(now.getFullYear(), quarterStartMonth, 1);
  const end = new Date(now.getFullYear(), quarterStartMonth + 3, 0);
  const format = (value: Date) =>
    `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
  return { start: format(start), end: format(end) };
}

function yearBounds(): { start: string; end: string } {
  const now = new Date();
  return { start: `${now.getFullYear()}-01-01`, end: `${now.getFullYear()}-12-31` };
}

function formatHours(minutes: number): string {
  return `${(minutes / 60).toFixed(1)} h`;
}

function formatDateLabel(value: string): string {
  return new Intl.DateTimeFormat("it-IT", {
    weekday: "short",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(new Date(`${value}T00:00:00`));
}

function formatDateTimeLabel(value: string | null): string {
  if (!value) return "n/d";
  return new Intl.DateTimeFormat("it-IT", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatMonthLabel(isoDate: string): string {
  return new Intl.DateTimeFormat("it-IT", { month: "long", year: "numeric" }).format(new Date(`${isoDate}T00:00:00`));
}

function formatPeriodLabel(periodPreset: PeriodPreset, start: string): string {
  if (periodPreset === "current" || periodPreset === "previous") return formatMonthLabel(start);
  if (periodPreset === "quarter") {
    const date = new Date(`${start}T00:00:00`);
    const quarter = Math.floor(date.getMonth() / 3) + 1;
    return `Q${quarter} ${date.getFullYear()}`;
  }
  return new Intl.DateTimeFormat("it-IT", { year: "numeric" }).format(new Date(`${start}T00:00:00`));
}

function requestBadgeLabel(record: InazDailyRecord): string | null {
  if (record.resolved_absence_cause) return record.resolved_absence_cause.replaceAll("_", " ");
  if (record.request_description) return record.request_description;
  return null;
}

function detailTone(record: InazDailyRecord): "danger" | "warning" | "success" | "neutral" {
  if ((record.detail_anomalies?.length ?? 0) > 0 || record.special_day) return "warning";
  if ((record.effective_extra_minutes ?? 0) > 0) return "success";
  return "neutral";
}

function buildCsv(rows: string[][]): string {
  return rows
    .map((row) =>
      row
        .map((value) => `"${String(value ?? "").replaceAll('"', '""')}"`)
        .join(","),
    )
    .join("\n");
}

function downloadCsv(filename: string, rows: string[][]): void {
  const csv = buildCsv(rows);
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function downloadWorkbook(filename: string, sheets: Array<{ name: string; rows: Record<string, string | number | null>[] }>): void {
  const workbook = XLSX.utils.book_new();
  sheets.forEach((sheet) => {
    const worksheet = XLSX.utils.json_to_sheet(sheet.rows);
    XLSX.utils.book_append_sheet(workbook, worksheet, sheet.name);
  });
  const out = XLSX.write(workbook, { bookType: "xlsx", type: "array" });
  const blob = new Blob([out], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function exportPresenzeCsv(records: InazDailyRecord[]): void {
  downloadCsv("me-presenze.csv", [
    ["Data", "Ordinarie minuti", "Extra minuti", "Assenza minuti", "KM", "Stato", "Richiesta"],
    ...records.map((record) => [
      record.work_date,
      String(record.ordinary_minutes ?? 0),
      String(record.effective_extra_minutes ?? 0),
      String(record.absence_minutes ?? 0),
      String(record.km_value ?? 0),
      record.detail_status || record.stato || "",
      requestBadgeLabel(record) || "",
    ]),
  ]);
}

function exportPresenzeXlsx(records: InazDailyRecord[]): void {
  downloadWorkbook("me-presenze.xlsx", [
    {
      name: "presenze",
      rows: records.map((record) => ({
        data: record.work_date,
        stato: record.detail_status || record.stato || "",
        ordinarie_minuti: record.ordinary_minutes ?? 0,
        extra_minuti: record.effective_extra_minutes ?? 0,
        assenza_minuti: record.absence_minutes ?? 0,
        km: record.km_value ?? 0,
        richiesta: requestBadgeLabel(record) || "",
      })),
    },
  ]);
}

function exportOperativitaCsv(
  activities: MeOperazioniActivity[],
  reports: MeOperazioniReport[],
  cases: MeOperazioniCase[],
  vehicleSessions: MeVehicleUsageSession[],
): void {
  downloadCsv("me-operativita.csv", [
    ["Sezione", "Riferimento", "Titolo", "Stato", "Data", "Dettaglio"],
    ...activities.map((item) => [
      "Attivita",
      item.id,
      item.activity_name || "",
      item.status,
      item.started_at,
      `${item.duration_minutes ?? 0} min`,
    ]),
    ...reports.map((item) => ["Segnalazioni", item.report_number, item.title, item.status, item.created_at, item.category_name || ""]),
    ...cases.map((item) => ["Pratiche", item.case_number, item.title, item.status, item.created_at, item.source_report_number || ""]),
    ...vehicleSessions.map((item) => ["Mezzi", item.id, item.vehicle_name || "", item.status, item.started_at, `${item.km} km`]),
  ]);
}

function exportOperativitaXlsx(
  activities: MeOperazioniActivity[],
  reports: MeOperazioniReport[],
  cases: MeOperazioniCase[],
  vehicleSessions: MeVehicleUsageSession[],
): void {
  downloadWorkbook("me-operativita.xlsx", [
    {
      name: "attivita",
      rows: activities.map((item) => ({
        nome: item.activity_name || "",
        categoria: item.activity_category || "",
        stato: item.status,
        inizio: item.started_at,
        minuti: item.duration_minutes ?? 0,
        mezzo: item.vehicle_name || "",
      })),
    },
    {
      name: "segnalazioni",
      rows: reports.map((item) => ({
        numero: item.report_number,
        titolo: item.title,
        stato: item.status,
        categoria: item.category_name || "",
        creata_il: item.created_at,
      })),
    },
    {
      name: "pratiche",
      rows: cases.map((item) => ({
        numero: item.case_number,
        titolo: item.title,
        stato: item.status,
        priorita: item.priority_rank ?? "",
        report_origine: item.source_report_number || "",
      })),
    },
    {
      name: "mezzi",
      rows: vehicleSessions.map((item) => ({
        mezzo: item.vehicle_name || "",
        targa: item.vehicle_plate_number || "",
        stato: item.status,
        inizio: item.started_at,
        km: item.km,
      })),
    },
  ]);
}

function exportDotazioniCsv(devices: MeAssignedDevice[], assignments: MeVehicleAssignment[]): void {
  downloadCsv("me-dotazioni.csv", [
    ["Sezione", "Etichetta", "Riferimento", "Stato", "Dettaglio"],
    ...devices.map((item) => ["Dispositivo", item.resolved_label, item.ip_address, item.status, item.device_type || ""]),
    ...assignments.map((item) => ["Mezzo", item.vehicle_name, item.vehicle_plate_number || "", item.is_active ? "attivo" : "chiuso", item.vehicle_type]),
  ]);
}

function exportDotazioniXlsx(devices: MeAssignedDevice[], assignments: MeVehicleAssignment[]): void {
  downloadWorkbook("me-dotazioni.xlsx", [
    {
      name: "dispositivi",
      rows: devices.map((item) => ({
        etichetta: item.resolved_label,
        ip: item.ip_address,
        stato: item.status,
        tipo: item.device_type || "",
        sistema_operativo: item.operating_system || "",
        ultimo_visto: item.last_seen_at,
      })),
    },
    {
      name: "mezzi_assegnati",
      rows: assignments.map((item) => ({
        mezzo: item.vehicle_name,
        targa: item.vehicle_plate_number || "",
        tipo: item.vehicle_type,
        attiva: item.is_active ? "si" : "no",
        start_at: item.start_at,
        end_at: item.end_at || "",
      })),
    },
  ]);
}

function getTabFromHash(hash: string): MeTabKey {
  if (hash === "#presenze") return "presenze";
  if (hash === "#operativita") return "operativita";
  if (hash === "#dotazioni") return "dotazioni";
  if (hash === "#anomalie") return "anomalie";
  return "overview";
}

export default function MePage() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [activeTab, setActiveTab] = useState<MeTabKey>("overview");
  const [periodPreset, setPeriodPreset] = useState<PeriodPreset>("current");
  const [meStatus, setMeStatus] = useState<MeModuleStatusResponse | null>(null);
  const [summary, setSummary] = useState<MeSummaryResponse | null>(null);
  const [inazStatus, setInazStatus] = useState<MeInazStatusResponse | null>(null);
  const [inazRecords, setInazRecords] = useState<InazDailyRecord[]>([]);
  const [inazSummaryRows, setInazSummaryRows] = useState<InazEventSummary[]>([]);
  const [operazioniSummary, setOperazioniSummary] = useState<MeOperazioniSummaryResponse | null>(null);
  const [activities, setActivities] = useState<MeOperazioniActivity[]>([]);
  const [reports, setReports] = useState<MeOperazioniReport[]>([]);
  const [cases, setCases] = useState<MeOperazioniCase[]>([]);
  const [vehicleSessions, setVehicleSessions] = useState<MeVehicleUsageSession[]>([]);
  const [assignedDevices, setAssignedDevices] = useState<MeAssignedDevice[]>([]);
  const [vehicleAssignments, setVehicleAssignments] = useState<MeVehicleAssignment[]>([]);
  const [operativitaSectionFilter, setOperativitaSectionFilter] = useState<OperativitaSectionFilter>("all");
  const [operativitaStatusFilter, setOperativitaStatusFilter] = useState("all");
  const [operativitaQuery, setOperativitaQuery] = useState("");
  const [selectedOperativitaDetail, setSelectedOperativitaDetail] = useState<OperativitaDetailState | null>(null);
  const [selectedDailyRecord, setSelectedDailyRecord] = useState<InazDailyRecord | null>(null);
  const [isDailyRecordLoading, setIsDailyRecordLoading] = useState(false);
  const [dailyRecordError, setDailyRecordError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const bounds = useMemo(() => {
    if (periodPreset === "current") return monthBounds(0);
    if (periodPreset === "previous") return monthBounds(-1);
    if (periodPreset === "quarter") return quarterBounds();
    return yearBounds();
  }, [periodPreset]);
  const monthLabel = useMemo(() => formatPeriodLabel(periodPreset, bounds.start), [bounds.start, periodPreset]);
  const deltaExtraVsActivitiesMinutes = useMemo(
    () => Math.abs((summary?.extra_minutes ?? 0) - (summary?.activity_minutes ?? 0)),
    [summary?.activity_minutes, summary?.extra_minutes],
  );
  const deltaKmMinutes = useMemo(
    () => Math.abs((summary?.km_from_inaz ?? 0) - (summary?.vehicle_km ?? 0)),
    [summary?.km_from_inaz, summary?.vehicle_km],
  );

  useEffect(() => {
    const syncTab = () => {
      if (typeof window === "undefined") return;
      setActiveTab(getTabFromHash(window.location.hash));
    };
    syncTab();
    window.addEventListener("hashchange", syncTab);
    return () => window.removeEventListener("hashchange", syncTab);
  }, []);

  useEffect(() => {
    const period = searchParams.get("period");
    const section = searchParams.get("section");
    const status = searchParams.get("status");
    const query = searchParams.get("q");

    if (period === "current" || period === "previous" || period === "quarter" || period === "year") {
      setPeriodPreset(period);
    }
    if (section === "all" || section === "activities" || section === "reports" || section === "cases" || section === "vehicles") {
      setOperativitaSectionFilter(section);
    }
    if (status) {
      setOperativitaStatusFilter(status);
    }
    if (query !== null) {
      setOperativitaQuery(query);
    }
  }, [searchParams]);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    const authToken = token;

    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const statusPayload = await getMeStatus(authToken);
        setMeStatus(statusPayload);

        const summaryPromise = getMeSummary(authToken, { periodStart: bounds.start, periodEnd: bounds.end });
        const inazStatusPromise = statusPayload.capabilities.inaz ? getMeInazStatus(authToken) : Promise.resolve(null);
        const inazRecordsPromise = statusPayload.capabilities.inaz
          ? listMeInazDailyRecords(authToken, { dateFrom: bounds.start, dateTo: bounds.end, page: 1, pageSize: 200 })
          : Promise.resolve(null);
        const inazSummaryPromise = statusPayload.capabilities.inaz
          ? getMeInazSummary(authToken, bounds.start, bounds.end)
          : Promise.resolve(null);
        const operazioniSummaryPromise = statusPayload.capabilities.operazioni
          ? getMeOperazioniSummary(authToken, { periodStart: bounds.start, periodEnd: bounds.end })
          : Promise.resolve(null);
        const activitiesPromise = statusPayload.capabilities.operazioni
          ? listMeOperazioniActivities(authToken, { periodStart: bounds.start, periodEnd: bounds.end, page: 1, pageSize: 50 })
          : Promise.resolve(null);
        const reportsPromise = statusPayload.capabilities.operazioni
          ? listMeOperazioniReports(authToken, { periodStart: bounds.start, periodEnd: bounds.end, page: 1, pageSize: 50 })
          : Promise.resolve(null);
        const casesPromise = statusPayload.capabilities.operazioni
          ? listMeOperazioniCases(authToken, { periodStart: bounds.start, periodEnd: bounds.end, page: 1, pageSize: 50 })
          : Promise.resolve(null);
        const vehicleSessionsPromise = statusPayload.capabilities.operazioni
          ? listMeVehicleSessions(authToken, { periodStart: bounds.start, periodEnd: bounds.end, page: 1, pageSize: 50 })
          : Promise.resolve(null);
        const devicesPromise = statusPayload.capabilities.network ? listMeAssignedDevices(authToken) : Promise.resolve(null);
        const vehicleAssignmentsPromise = statusPayload.capabilities.operazioni ? listMeVehicleAssignments(authToken) : Promise.resolve(null);

        const [
          summaryPayload,
          inazStatusPayload,
          inazRecordsPayload,
          inazSummaryPayload,
          operazioniSummaryPayload,
          activitiesPayload,
          reportsPayload,
          casesPayload,
          vehicleSessionsPayload,
          devicesPayload,
          vehicleAssignmentsPayload,
        ] = await Promise.all([
          summaryPromise,
          inazStatusPromise,
          inazRecordsPromise,
          inazSummaryPromise,
          operazioniSummaryPromise,
          activitiesPromise,
          reportsPromise,
          casesPromise,
          vehicleSessionsPromise,
          devicesPromise,
          vehicleAssignmentsPromise,
        ]);

        setSummary(summaryPayload);
        setInazStatus(inazStatusPayload);
        setInazRecords(inazRecordsPayload?.items ?? []);
        setInazSummaryRows(inazSummaryPayload?.items ?? []);
        setOperazioniSummary(operazioniSummaryPayload);
        setActivities(activitiesPayload?.items ?? []);
        setReports(reportsPayload?.items ?? []);
        setCases(casesPayload?.items ?? []);
        setVehicleSessions(vehicleSessionsPayload?.items ?? []);
        setAssignedDevices(devicesPayload?.items ?? []);
        setVehicleAssignments(vehicleAssignmentsPayload?.items ?? []);
      } catch (loadError) {
        if (isAuthError(loadError)) {
          setError("Sessione non valida. Effettua nuovamente il login.");
        } else {
          setError(loadError instanceof Error ? loadError.message : "Errore caricamento modulo personale");
        }
      } finally {
        setIsLoading(false);
      }
    }

    void load();
  }, [bounds.end, bounds.start]);

  const topSummaryRows = useMemo(() => inazSummaryRows.slice(0, 8), [inazSummaryRows]);
  const recentRecords = useMemo(() => [...inazRecords].sort((a, b) => b.work_date.localeCompare(a.work_date)).slice(0, 8), [inazRecords]);
  const recentActivities = useMemo(() => activities.slice(0, 8), [activities]);
  const recentReports = useMemo(() => reports.slice(0, 6), [reports]);
  const activeAssignments = useMemo(() => vehicleAssignments.filter((item) => item.is_active), [vehicleAssignments]);
  const anomalyRecords = useMemo(
    () =>
      inazRecords.filter(
        (item) =>
          (item.detail_anomalies?.length ?? 0) > 0 ||
          Boolean(item.special_day) ||
          Boolean((item.detail_status || item.stato || "").toLowerCase().includes("anom")),
      ),
    [inazRecords],
  );
  const openOrCriticalCases = useMemo(
    () => cases.filter((item) => item.status !== "closed" && item.status !== "resolved"),
    [cases],
  );
  const operativitaStatuses = useMemo(() => {
    const values = new Set<string>();
    activities.forEach((item) => values.add(item.status));
    reports.forEach((item) => values.add(item.status));
    cases.forEach((item) => values.add(item.status));
    vehicleSessions.forEach((item) => values.add(item.status));
    return Array.from(values).sort((left, right) => left.localeCompare(right));
  }, [activities, reports, cases, vehicleSessions]);
  const filteredActivities = useMemo(() => {
    const query = operativitaQuery.trim().toLowerCase();
    return activities.filter((item) => {
      if (operativitaStatusFilter !== "all" && item.status !== operativitaStatusFilter) return false;
      if (!query) return true;
      return [
        item.activity_name,
        item.activity_category,
        item.vehicle_name,
        item.text_note,
      ].some((value) => value?.toLowerCase().includes(query));
    });
  }, [activities, operativitaQuery, operativitaStatusFilter]);
  const filteredReports = useMemo(() => {
    const query = operativitaQuery.trim().toLowerCase();
    return reports.filter((item) => {
      if (operativitaStatusFilter !== "all" && item.status !== operativitaStatusFilter) return false;
      if (!query) return true;
      return [item.report_number, item.title, item.category_name, item.vehicle_name].some((value) => value?.toLowerCase().includes(query));
    });
  }, [reports, operativitaQuery, operativitaStatusFilter]);
  const filteredCases = useMemo(() => {
    const query = operativitaQuery.trim().toLowerCase();
    return cases.filter((item) => {
      if (operativitaStatusFilter !== "all" && item.status !== operativitaStatusFilter) return false;
      if (!query) return true;
      return [item.case_number, item.title, item.source_report_number, item.category_name].some((value) => value?.toLowerCase().includes(query));
    });
  }, [cases, operativitaQuery, operativitaStatusFilter]);
  const filteredVehicleSessions = useMemo(() => {
    const query = operativitaQuery.trim().toLowerCase();
    return vehicleSessions.filter((item) => {
      if (operativitaStatusFilter !== "all" && item.status !== operativitaStatusFilter) return false;
      if (!query) return true;
      return [item.vehicle_name, item.vehicle_plate_number, item.operator_name, item.notes].some((value) => value?.toLowerCase().includes(query));
    });
  }, [vehicleSessions, operativitaQuery, operativitaStatusFilter]);

  const setHashTab = (tab: MeTabKey) => {
    const hash = tab === "overview" ? "" : `#${tab}`;
    const query = new URLSearchParams(searchParams.toString());
    const target = hash ? `${pathname}?${query.toString()}${hash}` : `${pathname}${query.toString() ? `?${query.toString()}` : ""}`;
    router.replace(target, { scroll: false });
    setActiveTab(tab);
  };

  useEffect(() => {
    const query = new URLSearchParams(searchParams.toString());
    query.set("period", periodPreset);

    if (operativitaSectionFilter !== "all") {
      query.set("section", operativitaSectionFilter);
    } else {
      query.delete("section");
    }

    if (operativitaStatusFilter !== "all") {
      query.set("status", operativitaStatusFilter);
    } else {
      query.delete("status");
    }

    if (operativitaQuery.trim()) {
      query.set("q", operativitaQuery.trim());
    } else {
      query.delete("q");
    }

    const hash = activeTab === "overview" ? "" : `#${activeTab}`;
    const target = `${pathname}?${query.toString()}${hash}`;
    const current = `${pathname}?${searchParams.toString()}${typeof window !== "undefined" ? window.location.hash : ""}`;
    if (target !== current) {
      router.replace(target, { scroll: false });
    }
  }, [activeTab, operativitaQuery, operativitaSectionFilter, operativitaStatusFilter, pathname, periodPreset, router, searchParams]);

  async function openDailyRecordDetail(recordId: string): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;
    setSelectedDailyRecord(null);
    setDailyRecordError(null);
    setIsDailyRecordLoading(true);
    try {
      const detail = await getMeInazDailyRecord(token, recordId);
      setSelectedDailyRecord(detail);
    } catch (loadError) {
      setDailyRecordError(loadError instanceof Error ? loadError.message : "Errore caricamento dettaglio giornata");
    } finally {
      setIsDailyRecordLoading(false);
    }
  }

  const closeOperativitaDetail = () => setSelectedOperativitaDetail(null);

  return (
    <ProtectedPage
      title="La mia attività"
      description="Presenze, operatività sul territorio, utilizzo mezzi e dotazioni personali in un unico spazio self-service."
      breadcrumb="La mia attività"
    >
      <div className="page-stack">
        <article className="panel-card overflow-hidden">
          <div className="rounded-[28px] border border-[#dbe8de] bg-[linear-gradient(135deg,#f4fbf5_0%,#fbf8ef_100%)] p-6">
            <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
              <div className="space-y-3">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#5b7861]">Self service utente</p>
                <div>
                  <h2 className="text-3xl font-semibold tracking-tight text-[#173527]">Dossier personale operativo</h2>
                  <p className="mt-2 max-w-2xl text-sm leading-6 text-[#58705f]">
                    Unifica giornaliere Inaz, straordinari, segnalazioni, pratiche, mezzi utilizzati e dispositivi assegnati.
                  </p>
                </div>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl border border-white/70 bg-white/80 p-4 shadow-sm">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#7b8f7f]">Periodo storico</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button className={periodPreset === "current" ? "btn-primary" : "btn-secondary"} type="button" onClick={() => setPeriodPreset("current")}>
                      Mese corrente
                    </button>
                    <button className={periodPreset === "previous" ? "btn-primary" : "btn-secondary"} type="button" onClick={() => setPeriodPreset("previous")}>
                      Mese precedente
                    </button>
                    <button className={periodPreset === "quarter" ? "btn-primary" : "btn-secondary"} type="button" onClick={() => setPeriodPreset("quarter")}>
                      Trimestre
                    </button>
                    <button className={periodPreset === "year" ? "btn-primary" : "btn-secondary"} type="button" onClick={() => setPeriodPreset("year")}>
                      Anno
                    </button>
                  </div>
                  <p className="mt-3 text-xs text-[#6b7d70]">{monthLabel} · {bounds.start} / {bounds.end}</p>
                </div>
                <div className="rounded-2xl border border-white/70 bg-white/80 p-4 shadow-sm">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#7b8f7f]">Capacità attive</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {meStatus?.capabilities.inaz ? <Badge variant="success">Inaz</Badge> : <Badge>Inaz off</Badge>}
                    {meStatus?.capabilities.operazioni ? <Badge variant="info">Operazioni</Badge> : <Badge>Operazioni off</Badge>}
                    {meStatus?.capabilities.network ? <Badge variant="info">Rete</Badge> : <Badge>Rete off</Badge>}
                  </div>
                  <p className="mt-3 text-xs text-[#6b7d70]">{meStatus?.username || "Utente corrente"}</p>
                </div>
              </div>
            </div>
          </div>
        </article>

        {error ? <article className="panel-card border border-red-200 bg-red-50/80 text-sm text-red-700">{error}</article> : null}

        <article className="panel-card">
          <div className="flex flex-wrap items-center gap-3">
            <button className={activeTab === "overview" ? "btn-primary" : "btn-secondary"} type="button" onClick={() => setHashTab("overview")}>
              Panoramica
            </button>
            <button className={activeTab === "presenze" ? "btn-primary" : "btn-secondary"} type="button" onClick={() => setHashTab("presenze")}>
              Presenze
            </button>
            <button className={activeTab === "operativita" ? "btn-primary" : "btn-secondary"} type="button" onClick={() => setHashTab("operativita")}>
              Operatività
            </button>
            <button className={activeTab === "dotazioni" ? "btn-primary" : "btn-secondary"} type="button" onClick={() => setHashTab("dotazioni")}>
              Dotazioni
            </button>
            <button className={activeTab === "anomalie" ? "btn-primary" : "btn-secondary"} type="button" onClick={() => setHashTab("anomalie")}>
              Anomalie
            </button>
            {isLoading ? <Badge variant="warning">Caricamento</Badge> : null}
          </div>
        </article>

        {activeTab === "overview" ? (
          <>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
              <MetricCard label="Ore ordinarie" value={formatHours(summary?.ordinary_minutes ?? 0)} sub="Periodo selezionato" variant="success" />
              <MetricCard label="Extra effettivi" value={formatHours(summary?.extra_minutes ?? 0)} sub="Straordinario + MPE" variant="warning" />
              <MetricCard label="Attività" value={summary?.activities_count ?? 0} sub={`${formatHours(summary?.activity_minutes ?? 0)} registrate`} />
              <MetricCard label="Segnalazioni" value={summary?.reports_count ?? 0} sub={`${summary?.assigned_cases_count ?? 0} pratiche assegnate`} />
              <MetricCard label="KM mezzi" value={summary?.vehicle_km ?? 0} sub={`${summary?.vehicle_sessions_count ?? 0} sessioni`} />
              <MetricCard label="Dotazioni" value={summary?.assigned_devices_count ?? 0} sub={`${summary?.active_vehicle_assignments_count ?? 0} mezzi attivi`} />
            </div>

            <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
              <article className="panel-card">
                <div className="mb-4 flex items-center justify-between gap-3">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-gray-400">Presenze recenti</p>
                    <h3 className="mt-1 text-lg font-semibold text-gray-900">Ultime giornate disponibili</h3>
                  </div>
                  {meStatus?.capabilities.inaz ? (
                    <button className="btn-secondary" type="button" onClick={() => exportPresenzeCsv(inazRecords)}>
                      Export CSV
                    </button>
                  ) : null}
                </div>
                <div className="space-y-3">
                  {recentRecords.length === 0 ? (
                    <p className="text-sm text-gray-500">
                      {meStatus?.capabilities.inaz ? "Nessuna giornaliera disponibile nel periodo selezionato." : "Il modulo Inaz non è attivo per questo utente."}
                    </p>
                  ) : (
                    recentRecords.map((record) => (
                      <div key={record.id} className="rounded-2xl border border-gray-100 bg-gray-50/80 p-4">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <p className="text-sm font-semibold text-gray-900">{formatDateLabel(record.work_date)}</p>
                            <p className="mt-1 text-xs text-gray-500">{record.detail_programmed_schedule || record.schedule_code || "Orario non disponibile"}</p>
                          </div>
                          <Badge variant={detailTone(record)}>{record.detail_status || record.stato || "Regolare"}</Badge>
                        </div>
                        <div className="mt-3 flex flex-wrap gap-2 text-xs text-gray-600">
                          <span className="rounded-full bg-white px-2.5 py-1">Ordinarie {formatHours(record.ordinary_minutes ?? 0)}</span>
                          <span className="rounded-full bg-white px-2.5 py-1">Extra {formatHours(record.effective_extra_minutes ?? 0)}</span>
                          <span className="rounded-full bg-white px-2.5 py-1">KM {record.km_value ?? 0}</span>
                        </div>
                        <button className="mt-3 text-xs font-medium text-[#1D4E35] transition hover:text-[#173527]" type="button" onClick={() => void openDailyRecordDetail(record.id)}>
                          Apri dettaglio giornata
                        </button>
                        {requestBadgeLabel(record) ? <p className="mt-3 text-xs text-gray-500">{requestBadgeLabel(record)}</p> : null}
                      </div>
                    ))
                  )}
                </div>
              </article>

              <article className="panel-card">
                <div className="mb-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-gray-400">Segnali principali</p>
                  <h3 className="mt-1 text-lg font-semibold text-gray-900">Sintesi personale del periodo</h3>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <MetricCard label="Anomalie Inaz" value={summary?.anomaly_days ?? 0} sub="Giornate da verificare" variant={(summary?.anomaly_days ?? 0) > 0 ? "warning" : "default"} />
                  <MetricCard label="Assenze" value={formatHours(summary?.absence_minutes ?? 0)} sub="Tempo assenza totale" variant="warning" />
                  <MetricCard label="Pratiche aperte" value={summary?.open_cases_count ?? 0} sub="Attualmente in carico" />
                  <MetricCard label="Pratiche chiuse" value={summary?.closed_cases_count ?? 0} sub="Nel periodo" variant="success" />
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-gray-400">Delta extra vs attività</p>
                    <p className="mt-2 text-2xl font-semibold text-gray-900">{formatHours(deltaExtraVsActivitiesMinutes)}</p>
                    <p className="mt-1 text-xs text-gray-500">Scostamento tra extra Inaz e minuti attività Operazioni.</p>
                  </div>
                  <div className="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-gray-400">Delta KM Inaz vs mezzi</p>
                    <p className="mt-2 text-2xl font-semibold text-gray-900">{deltaKmMinutes.toFixed(1)} km</p>
                    <p className="mt-1 text-xs text-gray-500">Scostamento tra KM annotati in Inaz e sessioni mezzo.</p>
                  </div>
                </div>
                <div className="mt-4 rounded-2xl border border-gray-100 bg-gray-50/80 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-gray-400">Stato mapping Inaz</p>
                  {meStatus?.capabilities.inaz ? (
                    inazStatus?.mapped ? (
                      <>
                        <p className="mt-2 text-sm font-semibold text-gray-900">{inazStatus.collaborator_name}</p>
                        <p className="mt-1 text-xs text-gray-500">Matricola {inazStatus.employee_code}</p>
                      </>
                    ) : (
                      <p className="mt-2 text-sm text-amber-800">Nessun collaboratore Inaz associato al tuo utente GAIA.</p>
                    )
                  ) : (
                    <p className="mt-2 text-sm text-gray-500">Modulo Inaz non abilitato.</p>
                  )}
                </div>
              </article>
            </div>
          </>
        ) : null}

        {activeTab === "presenze" ? (
          <div id="presenze" className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
            <article className="panel-card">
              <div className="mb-4 flex items-center justify-between gap-3">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-gray-400">Riepilogo periodo</p>
                  <h3 className="mt-1 text-lg font-semibold text-gray-900">Eventi e saldi Inaz</h3>
                </div>
                <div className="flex gap-2">
                  <button className="btn-secondary" type="button" onClick={() => exportPresenzeCsv(inazRecords)}>
                    Export CSV
                  </button>
                  <button className="btn-secondary" type="button" onClick={() => exportPresenzeXlsx(inazRecords)}>
                    Export XLSX
                  </button>
                </div>
              </div>
              {topSummaryRows.length === 0 ? (
                <p className="text-sm text-gray-500">Nessun riepilogo Inaz disponibile per il periodo selezionato.</p>
              ) : (
                <div className="space-y-3">
                  {topSummaryRows.map((row) => (
                    <div key={row.id} className="rounded-2xl border border-gray-100 bg-gray-50/80 p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-gray-900">{row.description}</p>
                          <p className="mt-1 text-xs text-gray-500">{row.event_code || "Voce riepilogo"}</p>
                        </div>
                        {row.unitamisura ? <Badge>{row.unitamisura}</Badge> : null}
                      </div>
                      <div className="mt-3 grid gap-2 sm:grid-cols-2">
                        <div className="rounded-xl bg-white px-3 py-2 text-xs text-gray-600">Fruito <div className="mt-1 text-sm font-semibold text-gray-900">{formatHours(row.fruito_minutes ?? 0)}</div></div>
                        <div className="rounded-xl bg-white px-3 py-2 text-xs text-gray-600">Saldo <div className="mt-1 text-sm font-semibold text-gray-900">{formatHours(row.saldo_minutes ?? 0)}</div></div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </article>

            <article className="panel-card">
              <div className="mb-4 flex items-center justify-between gap-3">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-gray-400">Calendario operativo</p>
                  <h3 className="mt-1 text-lg font-semibold text-gray-900">Giornaliere del mese</h3>
                </div>
                <Badge variant="info">{inazRecords.length} righe</Badge>
              </div>
              <div className="mb-4 rounded-2xl border border-gray-100 bg-gray-50/80 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-gray-400">Dettaglio self-service</p>
                <p className="mt-1 text-sm text-gray-600">Ogni giornata apre il dettaglio completo con timbrature, richieste, anomalie e riepiloghi di cartellino.</p>
              </div>
              {inazRecords.length === 0 ? (
                <p className="text-sm text-gray-500">Nessuna giornaliera disponibile.</p>
              ) : (
                <div className="space-y-3">
                  {inazRecords.map((record) => (
                    <div key={record.id} className="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-gray-900">{formatDateLabel(record.work_date)}</p>
                          <p className="mt-1 text-xs text-gray-500">{record.detail_programmed_schedule || record.schedule_code || "Orario non disponibile"}</p>
                        </div>
                        <Badge variant={detailTone(record)}>{record.detail_status || record.stato || "Regolare"}</Badge>
                      </div>
                      <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                        <div className="rounded-xl bg-gray-50 px-3 py-2 text-xs text-gray-600">Ordinarie <div className="mt-1 text-sm font-semibold text-gray-900">{formatHours(record.ordinary_minutes ?? 0)}</div></div>
                        <div className="rounded-xl bg-gray-50 px-3 py-2 text-xs text-gray-600">Extra <div className="mt-1 text-sm font-semibold text-gray-900">{formatHours(record.effective_extra_minutes ?? 0)}</div></div>
                        <div className="rounded-xl bg-gray-50 px-3 py-2 text-xs text-gray-600">Assenza <div className="mt-1 text-sm font-semibold text-gray-900">{formatHours(record.absence_minutes ?? 0)}</div></div>
                        <div className="rounded-xl bg-gray-50 px-3 py-2 text-xs text-gray-600">KM <div className="mt-1 text-sm font-semibold text-gray-900">{record.km_value ?? 0}</div></div>
                      </div>
                      {record.punches.length > 0 ? (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {record.punches.map((punch) => (
                            <span key={punch.id} className="rounded-full border border-gray-200 bg-gray-50 px-2.5 py-1 text-xs text-gray-600">
                              {punch.entry_time || "--:--"} → {punch.exit_time || "--:--"}
                            </span>
                          ))}
                        </div>
                      ) : null}
                      <button className="mt-3 text-xs font-medium text-[#1D4E35] transition hover:text-[#173527]" type="button" onClick={() => void openDailyRecordDetail(record.id)}>
                        Visualizza scheda completa
                      </button>
                      {requestBadgeLabel(record) ? <p className="mt-3 text-xs text-gray-500">{requestBadgeLabel(record)}</p> : null}
                    </div>
                  ))}
                </div>
              )}
            </article>
          </div>
        ) : null}

        {activeTab === "operativita" ? (
          <div id="operativita" className="space-y-6">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
              <MetricCard label="Attività" value={operazioniSummary?.activities_count ?? 0} sub={formatHours(operazioniSummary?.activity_minutes ?? 0)} />
              <MetricCard label="Segnalazioni" value={operazioniSummary?.reports_count ?? 0} sub="Inserite da te" />
              <MetricCard label="Pratiche assegnate" value={operazioniSummary?.assigned_cases_count ?? 0} sub={`${operazioniSummary?.open_cases_count ?? 0} aperte`} />
              <MetricCard label="Sessioni mezzo" value={operazioniSummary?.vehicle_sessions_count ?? 0} sub={`${operazioniSummary?.distinct_vehicles_count ?? 0} mezzi`} />
              <MetricCard label="KM percorsi" value={operazioniSummary?.vehicle_km ?? 0} sub="Somma periodo" variant="success" />
            </div>

            <article className="panel-card">
              <div className="mb-4 flex items-center justify-between gap-3">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-gray-400">Export e storico</p>
                  <h3 className="mt-1 text-lg font-semibold text-gray-900">Esporta operatività personale</h3>
                </div>
                <div className="flex gap-2">
                  <button className="btn-secondary" type="button" onClick={() => exportOperativitaCsv(activities, reports, cases, vehicleSessions)}>
                    Export CSV
                  </button>
                  <button className="btn-secondary" type="button" onClick={() => exportOperativitaXlsx(activities, reports, cases, vehicleSessions)}>
                    Export XLSX
                  </button>
                </div>
              </div>
              <div className="grid gap-3 lg:grid-cols-[0.9fr_0.55fr_0.55fr]">
                <label className="space-y-2">
                  <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-gray-400">Ricerca operativa</span>
                  <input
                    className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#8CB39D]"
                    placeholder="attività, report, mezzo, pratica"
                    value={operativitaQuery}
                    onChange={(event) => setOperativitaQuery(event.target.value)}
                  />
                </label>
                <label className="space-y-2">
                  <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-gray-400">Sezione</span>
                  <select
                    className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#8CB39D]"
                    value={operativitaSectionFilter}
                    onChange={(event) => setOperativitaSectionFilter(event.target.value as OperativitaSectionFilter)}
                  >
                    <option value="all">Tutte</option>
                    <option value="activities">Attività</option>
                    <option value="reports">Segnalazioni</option>
                    <option value="cases">Pratiche</option>
                    <option value="vehicles">Mezzi</option>
                  </select>
                </label>
                <label className="space-y-2">
                  <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-gray-400">Stato</span>
                  <select
                    className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#8CB39D]"
                    value={operativitaStatusFilter}
                    onChange={(event) => setOperativitaStatusFilter(event.target.value)}
                  >
                    <option value="all">Tutti</option>
                    {operativitaStatuses.map((statusValue) => (
                      <option key={statusValue} value={statusValue}>{statusValue}</option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="grid gap-4 lg:grid-cols-2">
                <div className="rounded-2xl border border-gray-100 bg-gray-50/80 p-4">
                  <p className="text-sm font-semibold text-gray-900">Stati attività</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {(operazioniSummary?.activity_statuses ?? []).map((item) => (
                      <span key={item.status} className="rounded-full bg-white px-3 py-1 text-xs text-gray-600">
                        {item.status}: <span className="font-semibold text-gray-900">{item.count}</span>
                      </span>
                    ))}
                  </div>
                </div>
                <div className="rounded-2xl border border-gray-100 bg-gray-50/80 p-4">
                  <p className="text-sm font-semibold text-gray-900">Categorie attività</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {(operazioniSummary?.activity_categories ?? []).map((item) => (
                      <span key={item.category} className="rounded-full bg-white px-3 py-1 text-xs text-gray-600">
                        {item.category}: <span className="font-semibold text-gray-900">{item.count}</span>
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </article>

            <div className="grid gap-6 xl:grid-cols-2">
              <article className="panel-card">
                <div className="mb-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-gray-400">Attività recenti</p>
                  <h3 className="mt-1 text-lg font-semibold text-gray-900">Lavorazioni e tempi</h3>
                </div>
                <div className="space-y-3">
                  {filteredActivities.length === 0 || operativitaSectionFilter === "reports" || operativitaSectionFilter === "cases" || operativitaSectionFilter === "vehicles" ? (
                    operativitaSectionFilter === "all" || operativitaSectionFilter === "activities" ? (
                    <p className="text-sm text-gray-500">Nessuna attività personale nel periodo selezionato.</p>
                    ) : (
                      <p className="text-sm text-gray-500">Filtro sezione attivo su un’altra area.</p>
                    )
                  ) : (
                    filteredActivities.slice(0, 12).map((item) => (
                      <div key={item.id} className="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <p className="text-sm font-semibold text-gray-900">{item.activity_name || "Attività"}</p>
                            <p className="mt-1 text-xs text-gray-500">{item.activity_category || "Senza categoria"} · {formatDateTimeLabel(item.started_at)}</p>
                          </div>
                          <Badge variant="info">{item.status}</Badge>
                        </div>
                        <div className="mt-3 flex flex-wrap gap-2 text-xs text-gray-600">
                          <span className="rounded-full bg-gray-50 px-2.5 py-1">{item.duration_minutes ?? 0} min</span>
                          {item.vehicle_name ? <span className="rounded-full bg-gray-50 px-2.5 py-1">{item.vehicle_name}</span> : null}
                        </div>
                        {item.text_note ? <p className="mt-3 text-xs text-gray-500">{item.text_note}</p> : null}
                        <button
                          className="mt-3 text-xs font-medium text-[#1D4E35] transition hover:text-[#173527]"
                          type="button"
                          onClick={() => setSelectedOperativitaDetail({ kind: "activity", item })}
                        >
                          Apri scheda attività
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </article>

              <article className="panel-card">
                <div className="mb-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-gray-400">Segnalazioni e pratiche</p>
                  <h3 className="mt-1 text-lg font-semibold text-gray-900">Produzione e presa in carico</h3>
                </div>
                <div className="space-y-3">
                  {(operativitaSectionFilter === "all" || operativitaSectionFilter === "reports") ? filteredReports.slice(0, 8).map((item) => (
                    <div key={item.id} className="rounded-2xl border border-gray-100 bg-gray-50/80 p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-gray-900">{item.title}</p>
                          <p className="mt-1 text-xs text-gray-500">{item.report_number} · {item.category_name || "Categoria"} · {formatDateTimeLabel(item.created_at)}</p>
                        </div>
                        <Badge>{item.status}</Badge>
                      </div>
                      <button
                        className="mt-3 text-xs font-medium text-[#1D4E35] transition hover:text-[#173527]"
                        type="button"
                        onClick={() => setSelectedOperativitaDetail({ kind: "report", item })}
                      >
                        Apri scheda segnalazione
                      </button>
                    </div>
                  )) : null}
                  {(operativitaSectionFilter === "all" || operativitaSectionFilter === "cases") ? filteredCases.slice(0, 8).map((item) => (
                    <div key={item.id} className="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-gray-900">{item.title}</p>
                          <p className="mt-1 text-xs text-gray-500">{item.case_number} · {item.source_report_number || "Senza report"} · {formatDateTimeLabel(item.created_at)}</p>
                        </div>
                        <Badge variant={item.status === "closed" ? "success" : "warning"}>{item.status}</Badge>
                      </div>
                      <button
                        className="mt-3 text-xs font-medium text-[#1D4E35] transition hover:text-[#173527]"
                        type="button"
                        onClick={() => setSelectedOperativitaDetail({ kind: "case", item })}
                      >
                        Apri scheda pratica
                      </button>
                    </div>
                  )) : null}
                  {(operativitaSectionFilter === "all" || operativitaSectionFilter === "reports" || operativitaSectionFilter === "cases") && filteredReports.length === 0 && filteredCases.length === 0 ? (
                    <p className="text-sm text-gray-500">Nessuna segnalazione o pratica personale coerente con i filtri selezionati.</p>
                  ) : null}
                </div>
              </article>
            </div>

            <article className="panel-card">
              <div className="mb-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-gray-400">Utilizzo mezzi</p>
                <h3 className="mt-1 text-lg font-semibold text-gray-900">Sessioni con km percorsi</h3>
              </div>
              <div className="grid gap-3">
                {operativitaSectionFilter === "all" || operativitaSectionFilter === "vehicles" ? (
                  filteredVehicleSessions.length === 0 ? (
                  <p className="text-sm text-gray-500">Nessuna sessione mezzo personale nel periodo selezionato.</p>
                  ) : (
                  filteredVehicleSessions.map((item) => (
                    <div key={item.id} className="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-gray-900">{item.vehicle_name || "Mezzo"}</p>
                          <p className="mt-1 text-xs text-gray-500">{item.vehicle_plate_number || "Targa n/d"} · {formatDateTimeLabel(item.started_at)}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-lg font-semibold text-[#173527]">{item.km} km</p>
                          <p className="text-xs text-gray-500">{item.status}</p>
                        </div>
                      </div>
                      <button
                        className="mt-3 text-xs font-medium text-[#1D4E35] transition hover:text-[#173527]"
                        type="button"
                        onClick={() => setSelectedOperativitaDetail({ kind: "vehicle", item })}
                      >
                        Apri scheda sessione
                      </button>
                    </div>
                  ))
                  )
                ) : (
                  <p className="text-sm text-gray-500">Filtro sezione attivo su un’altra area.</p>
                )}
              </div>
            </article>
          </div>
        ) : null}

        {activeTab === "dotazioni" ? (
          <div id="dotazioni" className="space-y-6">
            <article className="panel-card">
              <div className="mb-4 flex items-center justify-between gap-3">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-gray-400">Export e asset personali</p>
                  <h3 className="mt-1 text-lg font-semibold text-gray-900">Dispositivi e mezzi assegnati</h3>
                </div>
                <div className="flex gap-2">
                  <button className="btn-secondary" type="button" onClick={() => exportDotazioniCsv(assignedDevices, vehicleAssignments)}>
                    Export CSV
                  </button>
                  <button className="btn-secondary" type="button" onClick={() => exportDotazioniXlsx(assignedDevices, vehicleAssignments)}>
                    Export XLSX
                  </button>
                </div>
              </div>
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <MetricCard label="Dispositivi" value={assignedDevices.length} sub="Assegnati al profilo" />
                <MetricCard label="Mezzi attivi" value={activeAssignments.length} sub="Assegnazioni correnti" variant="success" />
                <MetricCard label="Mezzi storici" value={vehicleAssignments.length} sub="Storico assegnazioni" />
                <MetricCard label="Ultimo storico" value={monthLabel} sub="Periodo consultato" />
              </div>
            </article>

            <div className="grid gap-6 xl:grid-cols-2">
              <article className="panel-card">
                <div className="mb-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-gray-400">Dispositivi assegnati</p>
                  <h3 className="mt-1 text-lg font-semibold text-gray-900">Dotazione ICT personale</h3>
                </div>
                <div className="space-y-3">
                  {assignedDevices.length === 0 ? (
                    <p className="text-sm text-gray-500">Nessun dispositivo assegnato.</p>
                  ) : (
                    assignedDevices.map((item) => (
                      <div key={item.id} className="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-sm font-semibold text-gray-900">{item.resolved_label}</p>
                            <p className="mt-1 text-xs text-gray-500">{item.ip_address} · {item.device_type || "Tipo n/d"} · {item.operating_system || "OS n/d"}</p>
                          </div>
                          <Badge variant={item.status === "online" ? "success" : "warning"}>{item.status}</Badge>
                        </div>
                        <p className="mt-3 text-xs text-gray-500">Ultimo visto {formatDateTimeLabel(item.last_seen_at)}</p>
                      </div>
                    ))
                  )}
                </div>
              </article>

              <article className="panel-card">
                <div className="mb-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-gray-400">Assegnazioni mezzi</p>
                  <h3 className="mt-1 text-lg font-semibold text-gray-900">Dotazione veicoli</h3>
                </div>
                <div className="space-y-3">
                  {vehicleAssignments.length === 0 ? (
                    <p className="text-sm text-gray-500">Nessuna assegnazione mezzi registrata.</p>
                  ) : (
                    vehicleAssignments.map((item) => (
                      <div key={item.id} className="rounded-2xl border border-gray-100 bg-gray-50/80 p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-sm font-semibold text-gray-900">{item.vehicle_name}</p>
                            <p className="mt-1 text-xs text-gray-500">{item.vehicle_plate_number || "Targa n/d"} · {item.vehicle_type} · dal {formatDateTimeLabel(item.start_at)}</p>
                          </div>
                          <Badge variant={item.is_active ? "success" : "neutral"}>{item.is_active ? "attiva" : "chiusa"}</Badge>
                        </div>
                        {item.notes ? <p className="mt-3 text-xs text-gray-500">{item.notes}</p> : null}
                      </div>
                    ))
                  )}
                </div>
              </article>
            </div>
          </div>
        ) : null}

        {activeTab === "anomalie" ? (
          <div id="anomalie" className="space-y-6">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <MetricCard label="Giornate anomale" value={anomalyRecords.length} sub="Presenze da verificare" variant={anomalyRecords.length > 0 ? "warning" : "default"} />
              <MetricCard label="Pratiche aperte" value={openOrCriticalCases.length} sub="Ancora in carico" variant={openOrCriticalCases.length > 0 ? "warning" : "default"} />
              <MetricCard label="Assenze" value={formatHours(summary?.absence_minutes ?? 0)} sub="Nel periodo" variant="warning" />
              <MetricCard label="Extra" value={formatHours(summary?.extra_minutes ?? 0)} sub="Da confrontare con attività" />
            </div>

            <div className="grid gap-6 xl:grid-cols-2">
              <article className="panel-card">
                <div className="mb-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-gray-400">Anomalie presenze</p>
                  <h3 className="mt-1 text-lg font-semibold text-gray-900">Giornate da controllare</h3>
                </div>
                <div className="space-y-3">
                  {anomalyRecords.length === 0 ? (
                    <p className="text-sm text-gray-500">Nessuna anomalia Inaz nel periodo selezionato.</p>
                  ) : (
                    anomalyRecords.map((record) => (
                      <div key={record.id} className="rounded-2xl border border-amber-200 bg-amber-50/80 p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-sm font-semibold text-amber-950">{formatDateLabel(record.work_date)}</p>
                            <p className="mt-1 text-xs text-amber-800">{record.detail_status || record.stato || "Anomalia"}</p>
                          </div>
                          <Badge variant="warning">Inaz</Badge>
                        </div>
                        <p className="mt-3 text-xs text-amber-900">{requestBadgeLabel(record) || record.evidenze || "Controllo richiesto sul cartellino"}</p>
                        <button className="mt-3 text-xs font-medium text-[#8a5a00] transition hover:text-[#6b4500]" type="button" onClick={() => void openDailyRecordDetail(record.id)}>
                          Apri dettaglio
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </article>

              <article className="panel-card">
                <div className="mb-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-gray-400">Anomalie operative</p>
                  <h3 className="mt-1 text-lg font-semibold text-gray-900">Pratiche e carichi aperti</h3>
                </div>
                <div className="space-y-3">
                  {openOrCriticalCases.length === 0 ? (
                    <p className="text-sm text-gray-500">Nessuna pratica aperta da seguire nel periodo selezionato.</p>
                  ) : (
                    openOrCriticalCases.map((item) => (
                      <div key={item.id} className="rounded-2xl border border-rose-200 bg-rose-50/70 p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-rose-950">{item.title}</p>
                          <p className="mt-1 text-xs text-rose-800">{item.case_number} · {item.source_report_number || "Senza report"} · {formatDateTimeLabel(item.created_at)}</p>
                        </div>
                        <Badge variant="danger">{item.status}</Badge>
                      </div>
                      <button
                        className="mt-3 text-xs font-medium text-rose-700 transition hover:text-rose-900"
                        type="button"
                        onClick={() => setSelectedOperativitaDetail({ kind: "case", item })}
                      >
                        Apri scheda pratica
                      </button>
                    </div>
                  ))
                  )}
                </div>
              </article>
            </div>
          </div>
        ) : null}

        {(isDailyRecordLoading || selectedDailyRecord || dailyRecordError) ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0f172aaa] p-4">
            <button aria-label="Chiudi dettaglio giornata" className="absolute inset-0" type="button" onClick={() => { setSelectedDailyRecord(null); setDailyRecordError(null); setIsDailyRecordLoading(false); }} />
            <article className="relative z-10 max-h-[85vh] w-full max-w-4xl overflow-y-auto rounded-[28px] border border-gray-200 bg-white p-6 shadow-2xl">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-gray-400">Dettaglio giornata</p>
                  <h3 className="mt-1 text-xl font-semibold text-gray-900">
                    {selectedDailyRecord ? formatDateLabel(selectedDailyRecord.work_date) : "Caricamento scheda"}
                  </h3>
                </div>
                <button className="btn-secondary" type="button" onClick={() => { setSelectedDailyRecord(null); setDailyRecordError(null); setIsDailyRecordLoading(false); }}>
                  Chiudi
                </button>
              </div>
              {isDailyRecordLoading ? <p className="mt-6 text-sm text-gray-500">Caricamento dettaglio in corso.</p> : null}
              {dailyRecordError ? <p className="mt-6 text-sm text-red-600">{dailyRecordError}</p> : null}
              {selectedDailyRecord ? (
                <div className="mt-6 space-y-6">
                  <div className="grid gap-3 md:grid-cols-4">
                    <MetricCard label="Ordinarie" value={formatHours(selectedDailyRecord.ordinary_minutes ?? 0)} sub={selectedDailyRecord.detail_programmed_schedule || "Programma"} />
                    <MetricCard label="Extra" value={formatHours(selectedDailyRecord.effective_extra_minutes ?? 0)} sub="Straordinario + MPE" variant="success" />
                    <MetricCard label="Assenza" value={formatHours(selectedDailyRecord.absence_minutes ?? 0)} sub={requestBadgeLabel(selectedDailyRecord) || "Nessuna"} variant="warning" />
                    <MetricCard label="KM" value={selectedDailyRecord.km_value ?? 0} sub="Registrati" />
                  </div>
                  <div className="grid gap-6 lg:grid-cols-2">
                    <section className="rounded-2xl border border-gray-100 bg-gray-50/80 p-4">
                      <h4 className="text-sm font-semibold text-gray-900">Timbrature</h4>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {selectedDailyRecord.punches.length > 0 ? selectedDailyRecord.punches.map((punch) => (
                          <span key={punch.id} className="rounded-full bg-white px-3 py-1 text-xs text-gray-600">
                            {punch.entry_time || "--:--"} → {punch.exit_time || "--:--"}
                          </span>
                        )) : <span className="text-xs text-gray-500">Nessuna timbratura disponibile.</span>}
                      </div>
                    </section>
                    <section className="rounded-2xl border border-gray-100 bg-gray-50/80 p-4">
                      <h4 className="text-sm font-semibold text-gray-900">Stato e orario</h4>
                      <div className="mt-3 space-y-2 text-sm text-gray-600">
                        <p>Stato: <span className="font-semibold text-gray-900">{selectedDailyRecord.detail_status || selectedDailyRecord.stato || "Regolare"}</span></p>
                        <p>Programma: <span className="font-semibold text-gray-900">{selectedDailyRecord.detail_programmed_schedule || selectedDailyRecord.schedule_code || "n/d"}</span></p>
                        <p>Fasce: <span className="font-semibold text-gray-900">{selectedDailyRecord.detail_time_slots || "n/d"}</span></p>
                        <p>Ore teoriche: <span className="font-semibold text-gray-900">{selectedDailyRecord.detail_theoretical_hours || "n/d"}</span></p>
                      </div>
                    </section>
                  </div>
                  <div className="grid gap-6 lg:grid-cols-2">
                    <section className="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm">
                      <h4 className="text-sm font-semibold text-gray-900">Riepilogo cartellino</h4>
                      <div className="mt-3 space-y-2">
                        {Object.entries(selectedDailyRecord.detail_day_totals).length > 0 ? Object.entries(selectedDailyRecord.detail_day_totals).map(([key, value]) => (
                          <div key={key} className="flex items-center justify-between gap-3 rounded-xl bg-gray-50 px-3 py-2 text-xs text-gray-600">
                            <span>{key}</span>
                            <span className="font-semibold text-gray-900">{value}</span>
                          </div>
                        )) : <p className="text-xs text-gray-500">Nessun totale disponibile.</p>}
                      </div>
                    </section>
                    <section className="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm">
                      <h4 className="text-sm font-semibold text-gray-900">Richieste e anomalie</h4>
                      <div className="mt-3 space-y-3">
                        {selectedDailyRecord.detail_requests.map((item, index) => (
                          <div key={`request-${index}`} className="rounded-xl bg-gray-50 px-3 py-2 text-xs text-gray-600">{Object.values(item).join(" · ")}</div>
                        ))}
                        {selectedDailyRecord.detail_anomalies.map((item, index) => (
                          <div key={`anomaly-${index}`} className="rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-800">{Object.values(item).join(" · ")}</div>
                        ))}
                        {selectedDailyRecord.detail_requests.length === 0 && selectedDailyRecord.detail_anomalies.length === 0 ? (
                          <p className="text-xs text-gray-500">Nessuna richiesta o anomalia registrata.</p>
                        ) : null}
                      </div>
                    </section>
                  </div>
                </div>
              ) : null}
            </article>
          </div>
        ) : null}

        {selectedOperativitaDetail ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0f172aaa] p-4">
            <button aria-label="Chiudi dettaglio operatività" className="absolute inset-0" type="button" onClick={closeOperativitaDetail} />
            <article className="relative z-10 max-h-[85vh] w-full max-w-3xl overflow-y-auto rounded-[28px] border border-gray-200 bg-white p-6 shadow-2xl">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-gray-400">Scheda operatività</p>
                  <h3 className="mt-1 text-xl font-semibold text-gray-900">
                    {selectedOperativitaDetail.kind === "activity" ? selectedOperativitaDetail.item.activity_name || "Attività" : null}
                    {selectedOperativitaDetail.kind === "report" ? selectedOperativitaDetail.item.title : null}
                    {selectedOperativitaDetail.kind === "case" ? selectedOperativitaDetail.item.title : null}
                    {selectedOperativitaDetail.kind === "vehicle" ? selectedOperativitaDetail.item.vehicle_name || "Sessione mezzo" : null}
                  </h3>
                </div>
                <button className="btn-secondary" type="button" onClick={closeOperativitaDetail}>
                  Chiudi
                </button>
              </div>

              {selectedOperativitaDetail.kind === "activity" ? (
                <div className="mt-6 space-y-6">
                  <div className="grid gap-3 md:grid-cols-4">
                    <MetricCard label="Stato" value={selectedOperativitaDetail.item.status} sub="Workflow attività" />
                    <MetricCard label="Durata" value={`${selectedOperativitaDetail.item.duration_minutes ?? 0} min`} sub="Tempo registrato" variant="success" />
                    <MetricCard label="Inizio" value={formatDateTimeLabel(selectedOperativitaDetail.item.started_at)} sub="Timestamp" />
                    <MetricCard label="Fine" value={formatDateTimeLabel(selectedOperativitaDetail.item.ended_at)} sub="Chiusura" />
                  </div>
                  <div className="grid gap-6 lg:grid-cols-2">
                    <section className="rounded-2xl border border-gray-100 bg-gray-50/80 p-4">
                      <h4 className="text-sm font-semibold text-gray-900">Contesto attività</h4>
                      <div className="mt-3 space-y-2 text-sm text-gray-600">
                        <p>Categoria: <span className="font-semibold text-gray-900">{selectedOperativitaDetail.item.activity_category || "n/d"}</span></p>
                        <p>Mezzo: <span className="font-semibold text-gray-900">{selectedOperativitaDetail.item.vehicle_name || "nessuno"}</span></p>
                        <p>Targa: <span className="font-semibold text-gray-900">{selectedOperativitaDetail.item.vehicle_plate_number || "n/d"}</span></p>
                        <p>Inviata il: <span className="font-semibold text-gray-900">{formatDateTimeLabel(selectedOperativitaDetail.item.submitted_at)}</span></p>
                      </div>
                    </section>
                    <section className="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm">
                      <h4 className="text-sm font-semibold text-gray-900">Revisione</h4>
                      <div className="mt-3 space-y-2 text-sm text-gray-600">
                        <p>Esito: <span className="font-semibold text-gray-900">{selectedOperativitaDetail.item.review_outcome || "non disponibile"}</span></p>
                        <p>Nota revisione:</p>
                        <p className="rounded-xl bg-gray-50 px-3 py-2 text-xs text-gray-600">{selectedOperativitaDetail.item.review_note || "Nessuna nota di revisione."}</p>
                      </div>
                    </section>
                  </div>
                  <section className="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm">
                    <h4 className="text-sm font-semibold text-gray-900">Nota operatore</h4>
                    <p className="mt-3 rounded-xl bg-gray-50 px-3 py-3 text-sm text-gray-600">
                      {selectedOperativitaDetail.item.text_note || "Nessuna nota testuale registrata."}
                    </p>
                  </section>
                </div>
              ) : null}

              {selectedOperativitaDetail.kind === "report" ? (
                <div className="mt-6 space-y-6">
                  <div className="grid gap-3 md:grid-cols-4">
                    <MetricCard label="Numero" value={selectedOperativitaDetail.item.report_number} sub="Riferimento" />
                    <MetricCard label="Stato" value={selectedOperativitaDetail.item.status} sub="Workflow segnalazione" variant="warning" />
                    <MetricCard label="Creata" value={formatDateTimeLabel(selectedOperativitaDetail.item.created_at)} sub="Inserimento" />
                    <MetricCard label="Aggiornata" value={formatDateTimeLabel(selectedOperativitaDetail.item.updated_at)} sub="Ultimo update" />
                  </div>
                  <div className="grid gap-6 lg:grid-cols-2">
                    <section className="rounded-2xl border border-gray-100 bg-gray-50/80 p-4">
                      <h4 className="text-sm font-semibold text-gray-900">Classificazione</h4>
                      <div className="mt-3 space-y-2 text-sm text-gray-600">
                        <p>Categoria: <span className="font-semibold text-gray-900">{selectedOperativitaDetail.item.category_name || "n/d"}</span></p>
                        <p>Severità: <span className="font-semibold text-gray-900">{selectedOperativitaDetail.item.severity_name || "n/d"}</span></p>
                        <p>Mezzo: <span className="font-semibold text-gray-900">{selectedOperativitaDetail.item.vehicle_name || "non associato"}</span></p>
                        <p>Targa: <span className="font-semibold text-gray-900">{selectedOperativitaDetail.item.vehicle_plate_number || "n/d"}</span></p>
                      </div>
                    </section>
                    <section className="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm">
                      <h4 className="text-sm font-semibold text-gray-900">Descrizione</h4>
                      <p className="mt-3 rounded-xl bg-gray-50 px-3 py-3 text-sm text-gray-600">
                        {selectedOperativitaDetail.item.description || "Nessuna descrizione disponibile."}
                      </p>
                    </section>
                  </div>
                </div>
              ) : null}

              {selectedOperativitaDetail.kind === "case" ? (
                <div className="mt-6 space-y-6">
                  <div className="grid gap-3 md:grid-cols-4">
                    <MetricCard label="Numero" value={selectedOperativitaDetail.item.case_number} sub="Riferimento pratica" />
                    <MetricCard label="Stato" value={selectedOperativitaDetail.item.status} sub="Workflow pratica" variant={selectedOperativitaDetail.item.status === "closed" ? "success" : "warning"} />
                    <MetricCard label="Priorità" value={selectedOperativitaDetail.item.priority_rank ?? "n/d"} sub="Rank priorità" />
                    <MetricCard label="Report origine" value={selectedOperativitaDetail.item.source_report_number || "n/d"} sub="Collegamento" />
                  </div>
                  <div className="grid gap-6 lg:grid-cols-2">
                    <section className="rounded-2xl border border-gray-100 bg-gray-50/80 p-4">
                      <h4 className="text-sm font-semibold text-gray-900">Cronologia pratica</h4>
                      <div className="mt-3 space-y-2 text-sm text-gray-600">
                        <p>Categoria: <span className="font-semibold text-gray-900">{selectedOperativitaDetail.item.category_name || "n/d"}</span></p>
                        <p>Severità: <span className="font-semibold text-gray-900">{selectedOperativitaDetail.item.severity_name || "n/d"}</span></p>
                        <p>Creata il: <span className="font-semibold text-gray-900">{formatDateTimeLabel(selectedOperativitaDetail.item.created_at)}</span></p>
                        <p>Presa in carico: <span className="font-semibold text-gray-900">{formatDateTimeLabel(selectedOperativitaDetail.item.started_at)}</span></p>
                        <p>Risolta il: <span className="font-semibold text-gray-900">{formatDateTimeLabel(selectedOperativitaDetail.item.resolved_at)}</span></p>
                        <p>Chiusa il: <span className="font-semibold text-gray-900">{formatDateTimeLabel(selectedOperativitaDetail.item.closed_at)}</span></p>
                      </div>
                    </section>
                    <section className="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm">
                      <h4 className="text-sm font-semibold text-gray-900">Stato di presidio</h4>
                      <p className="mt-3 rounded-xl bg-gray-50 px-3 py-3 text-sm text-gray-600">
                        {selectedOperativitaDetail.item.status === "closed"
                          ? "La pratica risulta chiusa nel periodo selezionato."
                          : "La pratica richiede ancora presidio operativo o verifica dello stato finale."}
                      </p>
                    </section>
                  </div>
                </div>
              ) : null}

              {selectedOperativitaDetail.kind === "vehicle" ? (
                <div className="mt-6 space-y-6">
                  <div className="grid gap-3 md:grid-cols-4">
                    <MetricCard label="KM" value={selectedOperativitaDetail.item.km} sub="Percorrenza sessione" variant="success" />
                    <MetricCard label="Stato" value={selectedOperativitaDetail.item.status} sub="Stato sessione" />
                    <MetricCard label="Inizio" value={formatDateTimeLabel(selectedOperativitaDetail.item.started_at)} sub="Partenza" />
                    <MetricCard label="Fine" value={formatDateTimeLabel(selectedOperativitaDetail.item.ended_at)} sub="Chiusura" />
                  </div>
                  <div className="grid gap-6 lg:grid-cols-2">
                    <section className="rounded-2xl border border-gray-100 bg-gray-50/80 p-4">
                      <h4 className="text-sm font-semibold text-gray-900">Mezzo e operatore</h4>
                      <div className="mt-3 space-y-2 text-sm text-gray-600">
                        <p>Mezzo: <span className="font-semibold text-gray-900">{selectedOperativitaDetail.item.vehicle_name || "n/d"}</span></p>
                        <p>Targa: <span className="font-semibold text-gray-900">{selectedOperativitaDetail.item.vehicle_plate_number || "n/d"}</span></p>
                        <p>Operatore: <span className="font-semibold text-gray-900">{selectedOperativitaDetail.item.operator_name || "n/d"}</span></p>
                        <p>Creata il: <span className="font-semibold text-gray-900">{formatDateTimeLabel(selectedOperativitaDetail.item.created_at)}</span></p>
                      </div>
                    </section>
                    <section className="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm">
                      <h4 className="text-sm font-semibold text-gray-900">Note sessione</h4>
                      <p className="mt-3 rounded-xl bg-gray-50 px-3 py-3 text-sm text-gray-600">
                        {selectedOperativitaDetail.item.notes || "Nessuna nota registrata sulla sessione mezzo."}
                      </p>
                    </section>
                  </div>
                </div>
              ) : null}
            </article>
          </div>
        ) : null}
      </div>
    </ProtectedPage>
  );
}
