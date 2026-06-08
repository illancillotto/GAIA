"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";

import { CatastoPage } from "@/components/catasto/catasto-page";
import { AnomaliaStatusBadge } from "@/components/catasto/AnomaliaStatusBadge";
import { AnomaliaStatusPill } from "@/components/catasto/AnomaliaStatusPill";
import { CatastoAnomaliaExplainer } from "@/components/catasto/catasto-anomalia-explainer";
import { CatastoWorkspaceModal } from "@/components/catasto/workspace-modal";
import { ElaborazioneWorkspaceModal } from "@/components/elaborazioni/workspace-modal";
import { ElaborazioneOperationMessage } from "@/components/elaborazioni/operation-message";
import { ElaborazioneStatusBadge } from "@/components/elaborazioni/status-badge";
import { DataTable } from "@/components/table/data-table";
import { Pagination } from "@/components/table/pagination";
import { AlertBanner } from "@/components/ui/alert-banner";
import { EmptyState } from "@/components/ui/empty-state";
import { SearchIcon } from "@/components/ui/icons";
import {
  catastoApplyComuneWizard,
  catastoApplyCfWizard,
  catastoApplyParticellaWizard,
  catastoGetAdeStatusScanCandidates,
  catastoGetAdeStatusScanSummary,
  catastoGetAnomalieSummary,
  catastoGetComuneWizardItems,
  catastoGetCfWizardItems,
  catastoGetParticellaWizardItems,
  catastoListAnomalie,
  catastoRunAdeStatusScan,
  catastoUpdateAnomalia,
} from "@/lib/api/catasto";
import { createReport, getReportCategories, getReportSeverities } from "@/features/operazioni/api/client";
import { getElaborazioneBatches, listApplicationUsers } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";
import type { ApplicationUser, ElaborazioneBatch } from "@/types/api";
import type {
  CatAnomalia,
  CatAdeStatusScanCandidate,
  CatAdeStatusScanSummary,
  CatAnomaliaComuneWizardItem,
  CatAnomaliaCfWizardItem,
  CatAnomaliaParticellaWizardItem,
  CatAnomaliaSortField,
  CatAnomaliaSummaryBucket,
} from "@/types/catasto";

type FiltersState = {
  tipo: string;
  severita: string;
  status: string;
  anno: string;
  distretto: string;
};

type CfDraftState = Record<string, string>;
type ComuneDraftState = Record<string, string>;
type ParticellaDraftState = Record<string, string>;
type ParticellaFilterMode = "all" | "without_candidates";
type ManualQueueFilterMode = "all" | "without_wizard" | "unworked";
type SortDirection = "asc" | "desc";
type WorkspaceMode = "cf" | "comune" | "particella" | null;
type TabId = "manuale" | "cf" | "comune" | "particella" | "ade";
type BatchWorkspaceState = {
  href: string;
  title: string;
  description?: string | null;
};
type ManualAnomaliaWorkspaceState = {
  href: string;
  title: string;
  description?: string | null;
};
type LookupItem = { id: string; code?: string; name?: string };
type WorkQueueCard = {
  id: "cf" | "comune" | "particella" | "manual";
  title: string;
  description: string;
  count: number;
  severity: string;
  cta: string;
  tipo: string | null;
  mode: "cf" | "comune" | "particella" | null;
  available: boolean;
};

const CF_WIZARD_TYPES = new Set(["VAL-02-cf_invalido", "VAL-03-cf_mancante"]);
const COMUNE_WIZARD_TYPES = new Set(["VAL-04-comune_invalido"]);
const PARTICELLA_WIZARD_TYPES = new Set(["VAL-05-particella_assente"]);
const ADE_SCAN_BATCH_NAME_PREFIX = "Visure storiche AdE particelle non collegate";
const OVERVIEW_PAGE_SIZE = 50;
const WIZARD_PAGE_SIZE = 25;

function buildDefaultFilters(): FiltersState {
  return {
    tipo: "",
    severita: "",
    status: "aperta",
    anno: "",
    distretto: "",
  };
}

function canOpenCfWizard(tipo: string): boolean {
  return CF_WIZARD_TYPES.has(tipo);
}

function canOpenComuneWizard(tipo: string): boolean {
  return COMUNE_WIZARD_TYPES.has(tipo);
}

function canOpenParticellaWizard(tipo: string): boolean {
  return PARTICELLA_WIZARD_TYPES.has(tipo);
}

function resolveWizardMode(tipo: string): "cf" | "comune" | "particella" | null {
  if (canOpenCfWizard(tipo)) {
    return "cf";
  }
  if (canOpenComuneWizard(tipo)) {
    return "comune";
  }
  if (canOpenParticellaWizard(tipo)) {
    return "particella";
  }
  return null;
}

function parseWorkspaceMode(value: string | null): WorkspaceMode {
  if (value === "cf" || value === "comune" || value === "particella") {
    return value;
  }
  return null;
}

function parseManualFilterMode(value: string | null): ManualQueueFilterMode {
  if (value === "without_wizard" || value === "unworked") {
    return value;
  }
  return "all";
}

function parseSortField(value: string | null): CatAnomaliaSortField {
  if (
    value === "created_at"
    || value === "updated_at"
    || value === "tipo"
    || value === "status"
    || value === "severita"
    || value === "anno_campagna"
  ) {
    return value;
  }
  return "created_at";
}

function getPageCount(total: number, pageSize: number): number {
  if (total <= 0) {
    return 0;
  }
  return Math.ceil(total / pageSize);
}

export default function CatastoAnomaliePage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-gray-500">Caricamento anomalie...</div>}>
      <CatastoAnomaliePageContent />
    </Suspense>
  );
}

function CatastoAnomaliePageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [filters, setFilters] = useState<FiltersState>(() => {
    const defaults = buildDefaultFilters();
    return {
      tipo: searchParams.get("tipo") ?? defaults.tipo,
      severita: searchParams.get("severita") ?? defaults.severita,
      status: searchParams.get("status") ?? defaults.status,
      anno: searchParams.get("anno") ?? defaults.anno,
      distretto: searchParams.get("distretto") ?? defaults.distretto,
    };
  });
  const [items, setItems] = useState<CatAnomalia[]>([]);
  const [total, setTotal] = useState(0);
  const [overviewPage, setOverviewPage] = useState(() => {
    const raw = Number(searchParams.get("page") ?? "1");
    return Number.isFinite(raw) && raw >= 1 ? raw : 1;
  });
  const [selectedManualAnomaliaId, setSelectedManualAnomaliaId] = useState<string | null>(null);
  const [manualSearch, setManualSearch] = useState(() => searchParams.get("q") ?? "");
  const [manualFilterMode, setManualFilterMode] = useState<ManualQueueFilterMode>(() => parseManualFilterMode(searchParams.get("manual")));
  const [manualSortBy, setManualSortBy] = useState<CatAnomaliaSortField>(() => parseSortField(searchParams.get("sort_by")));
  const [manualSortDir, setManualSortDir] = useState<SortDirection>(() => searchParams.get("sort_dir") === "asc" ? "asc" : "desc");
  const [manualNoteDraft, setManualNoteDraft] = useState("");
  const [manualAssignedToDraft, setManualAssignedToDraft] = useState<string>("");
  const [manualNoteBusy, setManualNoteBusy] = useState(false);
  const [manualNoteMessage, setManualNoteMessage] = useState<string | null>(null);
  const [assignableUsers, setAssignableUsers] = useState<ApplicationUser[]>([]);
  const [reportCategories, setReportCategories] = useState<LookupItem[]>([]);
  const [reportSeverities, setReportSeverities] = useState<LookupItem[]>([]);
  const [reportCategoryId, setReportCategoryId] = useState("");
  const [reportSeverityId, setReportSeverityId] = useState("");
  const [reportTitleDraft, setReportTitleDraft] = useState("");
  const [reportDescriptionDraft, setReportDescriptionDraft] = useState("");
  const [reportCreateBusy, setReportCreateBusy] = useState(false);
  const [summaryBuckets, setSummaryBuckets] = useState<CatAnomaliaSummaryBucket[]>([]);
  const [summaryTotal, setSummaryTotal] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<TabId>(() => {
    const fromTab = searchParams.get("tab");
    if (
      fromTab === "manuale"
      || fromTab === "cf"
      || fromTab === "comune"
      || fromTab === "particella"
      || fromTab === "ade"
    ) {
      return fromTab;
    }
    return parseWorkspaceMode(searchParams.get("workspace")) ?? "cf";
  });
  const wizardMode: WorkspaceMode = tab === "cf" || tab === "comune" || tab === "particella" ? tab : null;
  const [cfItems, setCfItems] = useState<CatAnomaliaCfWizardItem[]>([]);
  const [cfTotal, setCfTotal] = useState(0);
  const [cfPage, setCfPage] = useState(1);
  const [cfBusy, setCfBusy] = useState(false);
  const [cfDrafts, setCfDrafts] = useState<CfDraftState>({});
  const [cfError, setCfError] = useState<string | null>(null);
  const [cfMessage, setCfMessage] = useState<string | null>(null);
  const [applyingAnomaliaId, setApplyingAnomaliaId] = useState<string | null>(null);
  const [comuneItems, setComuneItems] = useState<CatAnomaliaComuneWizardItem[]>([]);
  const [comuneTotal, setComuneTotal] = useState(0);
  const [comunePage, setComunePage] = useState(1);
  const [comuneBusy, setComuneBusy] = useState(false);
  const [comuneError, setComuneError] = useState<string | null>(null);
  const [comuneMessage, setComuneMessage] = useState<string | null>(null);
  const [applyingComuneAnomaliaId, setApplyingComuneAnomaliaId] = useState<string | null>(null);
  const [comuneDrafts, setComuneDrafts] = useState<ComuneDraftState>({});
  const [comuneBatchNote, setComuneBatchNote] = useState("Correzione comune batch da console anomalie");
  const [particellaItems, setParticellaItems] = useState<CatAnomaliaParticellaWizardItem[]>([]);
  const [particellaTotal, setParticellaTotal] = useState(0);
  const [particellaPage, setParticellaPage] = useState(1);
  const [particellaBusy, setParticellaBusy] = useState(false);
  const [particellaError, setParticellaError] = useState<string | null>(null);
  const [particellaMessage, setParticellaMessage] = useState<string | null>(null);
  const [applyingParticellaAnomaliaId, setApplyingParticellaAnomaliaId] = useState<string | null>(null);
  const [particellaDrafts, setParticellaDrafts] = useState<ParticellaDraftState>({});
  const [particellaFilterMode, setParticellaFilterMode] = useState<ParticellaFilterMode>("all");
  const [particellaBatchNote, setParticellaBatchNote] = useState("Collegamento particella batch da console anomalie");
  const [adeScanSummary, setAdeScanSummary] = useState<CatAdeStatusScanSummary | null>(null);
  const [adeScanCandidates, setAdeScanCandidates] = useState<CatAdeStatusScanCandidate[]>([]);
  const [adeScanBusy, setAdeScanBusy] = useState(false);
  const [adeScanMessage, setAdeScanMessage] = useState<string | null>(null);
  const [adeScanError, setAdeScanError] = useState<string | null>(null);
  const [adeScanBatches, setAdeScanBatches] = useState<ElaborazioneBatch[]>([]);
  const [adeScanWorkspace, setAdeScanWorkspace] = useState<BatchWorkspaceState | null>(null);
  const [manualAnomaliaWorkspace, setManualAnomaliaWorkspace] = useState<ManualAnomaliaWorkspaceState | null>(null);

  const loadOverview = useCallback(async (): Promise<void> => {
    const token = getStoredAccessToken();
    if (!token) {
      return;
    }

    setBusy(true);
    try {
      const [listData, summaryData] = await Promise.all([
        catastoListAnomalie(token, {
          tipo: filters.tipo || undefined,
          severita: filters.severita || undefined,
          status: filters.status || undefined,
          anno: filters.anno ? Number(filters.anno) : undefined,
          distretto: filters.distretto || undefined,
          q: manualSearch.trim() || undefined,
          sortBy: manualSortBy,
          sortDir: manualSortDir,
          page: overviewPage,
          pageSize: OVERVIEW_PAGE_SIZE,
        }),
        catastoGetAnomalieSummary(token, {
          status: filters.status || undefined,
          severita: filters.severita || undefined,
          anno: filters.anno ? Number(filters.anno) : undefined,
          distretto: filters.distretto || undefined,
        }),
      ]);
      if (listData.items.length === 0 && listData.total > 0 && overviewPage > 1) {
        setOverviewPage(1);
        return;
      }
      setItems(listData.items);
      setTotal(listData.total);
      setSummaryBuckets(summaryData.buckets);
      setSummaryTotal(summaryData.total);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento anomalie");
    } finally {
      setBusy(false);
    }
  }, [
    filters.anno,
    filters.distretto,
    filters.severita,
    filters.status,
    filters.tipo,
    manualSearch,
    manualSortBy,
    manualSortDir,
    overviewPage,
  ]);

  const loadCfWizard = useCallback(async (): Promise<void> => {
    if (wizardMode !== "cf") {
      return;
    }

    const token = getStoredAccessToken();
    if (!token) {
      return;
    }

    setCfBusy(true);
    try {
      const data = await catastoGetCfWizardItems(token, {
        status: "aperta",
        anno: filters.anno ? Number(filters.anno) : undefined,
        distretto: filters.distretto || undefined,
        page: cfPage,
        pageSize: WIZARD_PAGE_SIZE,
      });
      if (data.items.length === 0 && data.total > 0 && cfPage > 1) {
        setCfPage(1);
        return;
      }
      setCfItems(data.items);
      setCfTotal(data.total);
      setCfDrafts((current) => {
        const next = { ...current };
        for (const item of data.items) {
          if (!next[item.anomalia_id]) {
            next[item.anomalia_id] = item.suggested_codice_fiscale ?? item.codice_fiscale ?? "";
          }
        }
        return next;
      });
      setCfError(null);
    } catch (loadError) {
      setCfError(loadError instanceof Error ? loadError.message : "Errore caricamento workspace CF");
    } finally {
      setCfBusy(false);
    }
  }, [cfPage, filters.anno, filters.distretto, wizardMode]);

  const loadComuneWizard = useCallback(async (): Promise<void> => {
    if (wizardMode !== "comune") {
      return;
    }

    const token = getStoredAccessToken();
    if (!token) {
      return;
    }

    setComuneBusy(true);
    try {
      const data = await catastoGetComuneWizardItems(token, {
        status: "aperta",
        anno: filters.anno ? Number(filters.anno) : undefined,
        distretto: filters.distretto || undefined,
        page: comunePage,
        pageSize: WIZARD_PAGE_SIZE,
      });
      if (data.items.length === 0 && data.total > 0 && comunePage > 1) {
        setComunePage(1);
        return;
      }
      setComuneItems(data.items);
      setComuneTotal(data.total);
      setComuneDrafts((current) => {
        const next = { ...current };
        for (const item of data.items) {
          if (!next[item.anomalia_id] && item.candidates[0]) {
            next[item.anomalia_id] = item.candidates[0].id;
          }
        }
        return next;
      });
      setComuneError(null);
    } catch (loadError) {
      setComuneError(loadError instanceof Error ? loadError.message : "Errore caricamento workspace comuni");
    } finally {
      setComuneBusy(false);
    }
  }, [comunePage, filters.anno, filters.distretto, wizardMode]);

  const loadParticellaWizard = useCallback(async (): Promise<void> => {
    if (wizardMode !== "particella") {
      return;
    }

    const token = getStoredAccessToken();
    if (!token) {
      return;
    }

    setParticellaBusy(true);
    try {
      const data = await catastoGetParticellaWizardItems(token, {
        status: "aperta",
        anno: filters.anno ? Number(filters.anno) : undefined,
        distretto: filters.distretto || undefined,
        page: particellaPage,
        pageSize: WIZARD_PAGE_SIZE,
      });
      if (data.items.length === 0 && data.total > 0 && particellaPage > 1) {
        setParticellaPage(1);
        return;
      }
      setParticellaItems(data.items);
      setParticellaTotal(data.total);
      setParticellaDrafts((current) => {
        const next = { ...current };
        for (const item of data.items) {
          if (!next[item.anomalia_id] && item.candidates[0]) {
            next[item.anomalia_id] = item.candidates[0].id;
          }
        }
        return next;
      });
      setParticellaError(null);
    } catch (loadError) {
      setParticellaError(loadError instanceof Error ? loadError.message : "Errore caricamento workspace particelle");
    } finally {
      setParticellaBusy(false);
    }
  }, [filters.anno, filters.distretto, particellaPage, wizardMode]);

  const loadAdeScan = useCallback(async (): Promise<void> => {
    const token = getStoredAccessToken();
    if (!token) {
      return;
    }

    setAdeScanBusy(true);
    try {
      const [summaryData, candidateData, batchData] = await Promise.all([
        catastoGetAdeStatusScanSummary(token),
        catastoGetAdeStatusScanCandidates(token, { limit: 8 }),
        getElaborazioneBatches(token),
      ]);
      setAdeScanSummary(summaryData);
      setAdeScanCandidates(candidateData.items);
      setAdeScanBatches(
        batchData
          .filter((batch) => (batch.name ?? "").startsWith(ADE_SCAN_BATCH_NAME_PREFIX))
          .sort((left, right) => Date.parse(right.created_at) - Date.parse(left.created_at))
          .slice(0, 6),
      );
      setAdeScanError(null);
    } catch (loadError) {
      setAdeScanError(loadError instanceof Error ? loadError.message : "Errore caricamento scansione AdE");
    } finally {
      setAdeScanBusy(false);
    }
  }, []);

  const loadAssignableUsers = useCallback(async (): Promise<void> => {
    const token = getStoredAccessToken();
    if (!token) {
      return;
    }

    try {
      const response = await listApplicationUsers(token);
      setAssignableUsers(
        response.items.filter((user) => user.is_active && user.module_catasto),
      );
    } catch {
      setAssignableUsers([]);
    }
  }, []);

  const loadReportLookups = useCallback(async (): Promise<void> => {
    try {
      const [categoryData, severityData] = await Promise.all([
        getReportCategories(),
        getReportSeverities(),
      ]);
      setReportCategories(Array.isArray(categoryData) ? (categoryData as LookupItem[]) : []);
      setReportSeverities(Array.isArray(severityData) ? (severityData as LookupItem[]) : []);
    } catch {
      setReportCategories([]);
      setReportSeverities([]);
    }
  }, []);

  useEffect(() => {
    void loadOverview();
  }, [loadOverview]);

  useEffect(() => {
    void loadCfWizard();
  }, [loadCfWizard]);

  useEffect(() => {
    void loadComuneWizard();
  }, [loadComuneWizard]);

  useEffect(() => {
    void loadParticellaWizard();
  }, [loadParticellaWizard]);

  useEffect(() => {
    void loadAdeScan();
  }, [loadAdeScan]);

  useEffect(() => {
    void loadAssignableUsers();
  }, [loadAssignableUsers]);

  useEffect(() => {
    void loadReportLookups();
  }, [loadReportLookups]);

  const handleUpdateStatus = useCallback(async (id: string, status: string): Promise<void> => {
    const token = getStoredAccessToken();
    if (!token) {
      return;
    }
    await catastoUpdateAnomalia(token, id, { status });
    await Promise.all([loadOverview(), loadCfWizard(), loadComuneWizard(), loadParticellaWizard()]);
  }, [loadCfWizard, loadComuneWizard, loadOverview, loadParticellaWizard]);

  async function handleApplyCf(item: CatAnomaliaCfWizardItem): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) {
      return;
    }

    const draft = (cfDrafts[item.anomalia_id] ?? "").trim().toUpperCase();
    if (!draft) {
      setCfError("Inserisci un codice fiscale o una partita IVA valida prima di applicare la correzione.");
      setCfMessage(null);
      return;
    }

    setApplyingAnomaliaId(item.anomalia_id);
    setCfError(null);
    setCfMessage(null);
    try {
      const response = await catastoApplyCfWizard(token, [
        {
          anomalia_id: item.anomalia_id,
          codice_fiscale: draft,
          note_operatore: `Correzione da console anomalie per ${item.tipo}`,
        },
      ]);
      setCfMessage(
        `Correzione applicata: ${response.updated_utenze} utenza aggiornata, ${response.closed_anomalies} anomalie CF chiuse.`,
      );
      await Promise.all([loadOverview(), loadCfWizard(), loadComuneWizard(), loadParticellaWizard()]);
    } catch (applyError) {
      setCfError(applyError instanceof Error ? applyError.message : "Errore applicazione correzione CF");
    } finally {
      setApplyingAnomaliaId(null);
    }
  }

  async function handleApplyComune(anomaliaId: string, comuneId: string): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) {
      return;
    }

    setApplyingComuneAnomaliaId(anomaliaId);
    setComuneError(null);
    setComuneMessage(null);
    try {
      const response = await catastoApplyComuneWizard(token, [
        {
          anomalia_id: anomaliaId,
          comune_id: comuneId,
          note_operatore: comuneBatchNote.trim() || "Correzione comune da console anomalie",
        },
      ]);
      setComuneMessage(
        `Correzione applicata: ${response.updated_utenze} utenza aggiornata, ${response.closed_anomalies} anomalie comune chiuse.`,
      );
      await Promise.all([loadOverview(), loadCfWizard(), loadComuneWizard(), loadParticellaWizard()]);
    } catch (applyError) {
      setComuneError(applyError instanceof Error ? applyError.message : "Errore correzione comune");
    } finally {
      setApplyingComuneAnomaliaId(null);
    }
  }

  async function handleApplyComuneBatch(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) {
      return;
    }

    const selectedItems = comuneItems
      .map((item) => ({
        anomalia_id: item.anomalia_id,
        comune_id: comuneDrafts[item.anomalia_id] ?? "",
      }))
      .filter((item) => item.comune_id);

    if (selectedItems.length === 0) {
      setComuneError("Seleziona almeno un comune candidato prima di applicare il batch.");
      setComuneMessage(null);
      return;
    }

    setApplyingComuneAnomaliaId("__batch__");
    setComuneError(null);
    setComuneMessage(null);
    try {
      const response = await catastoApplyComuneWizard(
        token,
        selectedItems.map((item) => ({
          ...item,
          note_operatore: comuneBatchNote.trim() || "Correzione comune batch da console anomalie",
        })),
      );
      setComuneMessage(
        `Batch applicato: ${response.updated_utenze} utenze aggiornate, ${response.closed_anomalies} anomalie comune chiuse.`,
      );
      await Promise.all([loadOverview(), loadCfWizard(), loadComuneWizard(), loadParticellaWizard()]);
    } catch (applyError) {
      setComuneError(applyError instanceof Error ? applyError.message : "Errore batch correzione comuni");
    } finally {
      setApplyingComuneAnomaliaId(null);
    }
  }

  async function handleApplyParticella(anomaliaId: string, particellaId: string): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) {
      return;
    }

    setApplyingParticellaAnomaliaId(anomaliaId);
    setParticellaError(null);
    setParticellaMessage(null);
    try {
      const response = await catastoApplyParticellaWizard(token, [
        {
          anomalia_id: anomaliaId,
          particella_id: particellaId,
          note_operatore: particellaBatchNote.trim() || "Collegamento particella da console anomalie",
        },
      ]);
      setParticellaMessage(
        `Collegamento applicato: ${response.updated_utenze} utenza aggiornata, ${response.closed_anomalies} anomalie particella chiuse.`,
      );
      await Promise.all([loadOverview(), loadCfWizard(), loadComuneWizard(), loadParticellaWizard()]);
    } catch (applyError) {
      setParticellaError(applyError instanceof Error ? applyError.message : "Errore collegamento particella");
    } finally {
      setApplyingParticellaAnomaliaId(null);
    }
  }

  async function handleApplyParticellaBatch(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) {
      return;
    }

    const selectedItems = particellaItems
      .map((item) => ({
        anomalia_id: item.anomalia_id,
        particella_id: particellaDrafts[item.anomalia_id] ?? "",
      }))
      .filter((item) => item.particella_id);

    if (selectedItems.length === 0) {
      setParticellaError("Seleziona almeno una candidata particella prima di applicare il batch.");
      setParticellaMessage(null);
      return;
    }

    setApplyingParticellaAnomaliaId("__batch__");
    setParticellaError(null);
    setParticellaMessage(null);
    try {
      const response = await catastoApplyParticellaWizard(
        token,
        selectedItems.map((item) => ({
          ...item,
          note_operatore: particellaBatchNote.trim() || "Collegamento particella batch da console anomalie",
        })),
      );
      setParticellaMessage(
        `Batch applicato: ${response.updated_utenze} utenze aggiornate, ${response.closed_anomalies} anomalie particella chiuse.`,
      );
      await Promise.all([loadOverview(), loadCfWizard(), loadComuneWizard(), loadParticellaWizard()]);
    } catch (applyError) {
      setParticellaError(applyError instanceof Error ? applyError.message : "Errore batch collegamento particelle");
    } finally {
      setApplyingParticellaAnomaliaId(null);
    }
  }

  async function handleRunAdeScan(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) {
      return;
    }

    setAdeScanBusy(true);
    setAdeScanError(null);
    setAdeScanMessage(null);
    try {
      const response = await catastoRunAdeStatusScan(token, {});
      setAdeScanMessage(
        response.created > 0
          ? `Batch scansione AdE creato: ${response.created} richieste messe in coda${response.skipped ? `, ${response.skipped} saltate` : ""}.`
          : "Nessuna nuova particella da mettere in coda.",
      );
      await loadAdeScan();
    } catch (runError) {
      setAdeScanError(runError instanceof Error ? runError.message : "Errore avvio scansione AdE");
    } finally {
      setAdeScanBusy(false);
    }
  }

  const selectedComuneCount = useMemo(
    () => comuneItems.filter((item) => Boolean(comuneDrafts[item.anomalia_id])).length,
    [comuneDrafts, comuneItems],
  );

  function handleSelectTopComuni(): void {
    setComuneDrafts((current) => {
      const next = { ...current };
      for (const item of comuneItems) {
        if (item.candidates[0]) {
          next[item.anomalia_id] = item.candidates[0].id;
        }
      }
      return next;
    });
  }

  function handleClearComuneSelections(): void {
    setComuneDrafts({});
  }

  const selectedParticellaCount = useMemo(
    () => particellaItems.filter((item) => Boolean(particellaDrafts[item.anomalia_id])).length,
    [particellaDrafts, particellaItems],
  );
  const visibleParticellaItems = useMemo(
    () =>
      particellaFilterMode === "without_candidates"
        ? particellaItems.filter((item) => item.candidates.length === 0)
        : particellaItems,
    [particellaFilterMode, particellaItems],
  );
  const withoutCandidatesCount = useMemo(
    () => particellaItems.filter((item) => item.candidates.length === 0).length,
    [particellaItems],
  );
  const runningAdeScanBatch = useMemo(
    () => adeScanBatches.find((batch) => batch.status === "pending" || batch.status === "processing") ?? null,
    [adeScanBatches],
  );

  function handleSelectTopCandidates(): void {
    setParticellaDrafts((current) => {
      const next = { ...current };
      for (const item of particellaItems) {
        if (item.candidates[0]) {
          next[item.anomalia_id] = item.candidates[0].id;
        }
      }
      return next;
    });
  }

  function handleClearParticellaSelections(): void {
    setParticellaDrafts({});
  }

  function handleOpenAdeScanBatch(batch: ElaborazioneBatch): void {
    setAdeScanWorkspace({
      href: `/elaborazioni/batches/${batch.id}`,
      title: batch.name ?? "Dettaglio batch",
      description: "Dettaglio operativo del batch visure AdE con stato richieste, errori e CAPTCHA manuali.",
    });
  }

  function handleOpenManualParticellaWorkspace(anomalia: CatAnomalia): void {
    if (!anomalia.particella_id) {
      return;
    }
    setManualAnomaliaWorkspace({
      href: `/catasto/particelle/${anomalia.particella_id}`,
      title: `Particella collegata a ${anomalia.tipo}`,
      description: "Scheda particella aperta dal triage manuale per verifiche e correzioni senza perdere il contesto della console anomalie.",
    });
  }

  async function handleSaveManualNote(anomalia: CatAnomalia): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) {
      return;
    }

    setManualNoteBusy(true);
    setManualNoteMessage(null);
    try {
      await catastoUpdateAnomalia(token, anomalia.id, {
        note_operatore: manualNoteDraft.trim() || null,
      });
      setManualNoteMessage("Nota operatore salvata.");
      await loadOverview();
    } catch (saveError) {
      setManualNoteMessage(saveError instanceof Error ? saveError.message : "Errore salvataggio nota");
    } finally {
      setManualNoteBusy(false);
    }
  }

  async function handleSaveManualAssignment(anomalia: CatAnomalia): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) {
      return;
    }

    setManualNoteBusy(true);
    setManualNoteMessage(null);
    try {
      await catastoUpdateAnomalia(token, anomalia.id, {
        assigned_to: manualAssignedToDraft ? Number(manualAssignedToDraft) : undefined,
      });
      setManualNoteMessage("Assegnazione aggiornata.");
      await loadOverview();
    } catch (saveError) {
      setManualNoteMessage(saveError instanceof Error ? saveError.message : "Errore aggiornamento assegnazione");
    } finally {
      setManualNoteBusy(false);
    }
  }

  async function handleCreateManualReport(anomalia: CatAnomalia): Promise<void> {
    if (!reportCategoryId || !reportSeverityId || !reportTitleDraft.trim()) {
      setManualNoteMessage("Compila categoria, gravità e titolo della segnalazione.");
      return;
    }

    const token = getStoredAccessToken();
    if (!token) {
      return;
    }

    setReportCreateBusy(true);
    setManualNoteMessage(null);
    try {
      const response = await createReport({
        category_id: reportCategoryId,
        severity_id: reportSeverityId,
        title: reportTitleDraft.trim(),
        description: reportDescriptionDraft.trim() || null,
      });
      const reportId = String((response as { report?: { id?: string } }).report?.id ?? "");
      const reportNumber = String((response as { report?: { report_number?: string } }).report?.report_number ?? "");
      if (!reportId) {
        throw new Error("Segnalazione creata senza ID report");
      }
      await catastoUpdateAnomalia(token, anomalia.id, {
        segnalazione_id: reportId,
      });
      setManualNoteMessage(
        reportNumber ? `Segnalazione operativa creata: ${reportNumber}.` : "Segnalazione operativa creata.",
      );
      await loadOverview();
    } catch (createError) {
      setManualNoteMessage(createError instanceof Error ? createError.message : "Errore creazione segnalazione");
    } finally {
      setReportCreateBusy(false);
    }
  }

  const handleSelectTab = useCallback((next: TabId, tipo?: string | null): void => {
    setTab(next);
    if (tipo !== undefined) {
      setFilters((current) => ({ ...current, tipo: tipo ?? "" }));
    }
    setOverviewPage(1);
    setCfPage(1);
    setComunePage(1);
    setParticellaPage(1);
    setCfMessage(null);
    setCfError(null);
    setComuneMessage(null);
    setComuneError(null);
    setParticellaMessage(null);
    setParticellaError(null);
  }, []);

  const columns = useMemo<ColumnDef<CatAnomalia>[]>(
    () => [
      {
        header: "Severità",
        accessorKey: "severita",
        cell: ({ row }) => <AnomaliaStatusBadge severita={row.original.severita} />,
      },
      {
        header: "Tipo",
        accessorKey: "tipo",
        cell: ({ row }) => <span className="text-sm font-medium text-gray-900">{row.original.tipo}</span>,
      },
      {
        header: "Stato",
        accessorKey: "status",
        cell: ({ row }) => <AnomaliaStatusPill status={row.original.status} />,
      },
      {
        header: "Descrizione",
        accessorKey: "descrizione",
        cell: ({ row }) => <span className="text-sm text-gray-600">{row.original.descrizione ?? "—"}</span>,
      },
      {
        header: "Perche",
        id: "motivo",
        cell: ({ row }) => <CatastoAnomaliaExplainer anomalia={row.original} />,
      },
      {
        header: "Anno",
        accessorKey: "anno_campagna",
        cell: ({ row }) => <span className="text-sm text-gray-600">{row.original.anno_campagna ?? "—"}</span>,
      },
      {
        header: "Creata",
        accessorKey: "created_at",
        cell: ({ row }) => <span className="text-sm text-gray-600">{formatDateTime(row.original.created_at)}</span>,
      },
      {
        header: "Azioni",
        id: "actions",
        cell: ({ row }) => (
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="btn-secondary !px-2 !py-1 text-xs"
              disabled={busy}
              onClick={(event) => {
                event.stopPropagation();
                void handleUpdateStatus(row.original.id, "chiusa");
              }}
            >
              Chiudi
            </button>
            <button
              type="button"
              className="btn-secondary !px-2 !py-1 text-xs"
              disabled={busy}
              onClick={(event) => {
                event.stopPropagation();
                void handleUpdateStatus(row.original.id, "ignora");
              }}
            >
              Ignora
            </button>
            <button
              type="button"
              className="btn-secondary !px-2 !py-1 text-xs"
              disabled={busy}
              onClick={(event) => {
                event.stopPropagation();
                void handleUpdateStatus(row.original.id, "aperta");
              }}
            >
              Riapri
            </button>
          </div>
        ),
      },
    ],
    [busy, handleUpdateStatus],
  );

  const workQueues = useMemo<WorkQueueCard[]>(() => {
    const summaryByTipo = new Map(summaryBuckets.map((bucket) => [bucket.tipo, bucket]));
    const getAggregate = (tipi: string[]) => {
      const buckets = tipi
        .map((tipo) => summaryByTipo.get(tipo))
        .filter((bucket): bucket is CatAnomaliaSummaryBucket => Boolean(bucket));
      const count = buckets.reduce((acc, bucket) => acc + bucket.count, 0);
      const severity = buckets.find((bucket) => bucket.severita === "error")?.severita
        ?? buckets.find((bucket) => bucket.severita === "warning")?.severita
        ?? buckets[0]?.severita
        ?? "info";
      return { count, severity };
    };

    const cfAggregate = getAggregate([...CF_WIZARD_TYPES]);
    const comuneAggregate = getAggregate([...COMUNE_WIZARD_TYPES]);
    const particellaAggregate = getAggregate([...PARTICELLA_WIZARD_TYPES]);
    const manualCount = Math.max(
      0,
      summaryTotal - cfAggregate.count - comuneAggregate.count - particellaAggregate.count,
    );

    return [
      {
        id: "cf",
        title: "Coda CF / P.IVA",
        description: "Correzione guidata di `VAL-02` e `VAL-03` sulle utenze con identificativo fiscale errato o mancante.",
        count: cfAggregate.count,
        severity: cfAggregate.severity,
        cta: "Apri workspace CF",
        tipo: "VAL-02-cf_invalido",
        mode: "cf",
        available: cfAggregate.count > 0,
      },
      {
        id: "comune",
        title: "Coda comuni",
        description: "Riallineamento di `VAL-04` verso il mapping canonico `cat_comuni`, con anteprima prima/dopo.",
        count: comuneAggregate.count,
        severity: comuneAggregate.severity,
        cta: "Apri workspace comuni",
        tipo: "VAL-04-comune_invalido",
        mode: "comune",
        available: comuneAggregate.count > 0,
      },
      {
        id: "particella",
        title: "Coda particelle",
        description: "Collegamento guidato di `VAL-05` con candidate correnti e apply singolo o batch.",
        count: particellaAggregate.count,
        severity: particellaAggregate.severity,
        cta: "Apri workspace particelle",
        tipo: "VAL-05-particella_assente",
        mode: "particella",
        available: particellaAggregate.count > 0,
      },
      {
        id: "manual",
        title: "Triage manuale",
        description: "Famiglie senza wizard specialistico: restano nel registro completo per revisione operatore.",
        count: manualCount,
        severity: manualCount > 0 ? "warning" : "info",
        cta: "Vai al registro",
        tipo: null,
        mode: null,
        available: manualCount > 0,
      },
    ];
  }, [summaryBuckets, summaryTotal]);

  const manualQueueCount = workQueues.find((queue) => queue.id === "manual")?.count ?? 0;
  const correggibiliCount = useMemo(
    () => workQueues.filter((queue) => queue.id !== "manual").reduce((acc, queue) => acc + queue.count, 0),
    [workQueues],
  );
  const tabs = useMemo<Array<{ id: TabId; label: string; count: number | null; tipo?: string | null }>>(() => {
    const byId = new Map(workQueues.map((queue) => [queue.id, queue]));
    return [
      { id: "manuale", label: "Triage manuale", count: byId.get("manual")?.count ?? 0, tipo: "" },
      { id: "cf", label: "CF / P.IVA", count: byId.get("cf")?.count ?? 0, tipo: "VAL-02-cf_invalido" },
      { id: "comune", label: "Comuni", count: byId.get("comune")?.count ?? 0, tipo: "VAL-04-comune_invalido" },
      { id: "particella", label: "Particelle", count: byId.get("particella")?.count ?? 0, tipo: "VAL-05-particella_assente" },
      { id: "ade", label: "Scansione AdE", count: adeScanSummary?.total_unmatched ?? null, tipo: undefined },
    ];
  }, [adeScanSummary, workQueues]);
  const activeTabLabel = tabs.find((entry) => entry.id === tab)?.label ?? "Registro manuale";
  const activeWorkspaceCount = wizardMode === "cf"
    ? cfTotal
    : wizardMode === "comune"
      ? comuneTotal
      : wizardMode === "particella"
        ? particellaTotal
        : tab === "ade"
          ? adeScanSummary?.total_unmatched ?? 0
          : total;
  const overviewPageCount = getPageCount(total, OVERVIEW_PAGE_SIZE);
  const cfPageCount = getPageCount(cfTotal, WIZARD_PAGE_SIZE);
  const comunePageCount = getPageCount(comuneTotal, WIZARD_PAGE_SIZE);
  const particellaPageCount = getPageCount(particellaTotal, WIZARD_PAGE_SIZE);
  const manualTableItems = useMemo(() => {
    return items.filter((item) => {
      if (manualFilterMode === "without_wizard" && resolveWizardMode(item.tipo) !== null) {
        return false;
      }
      if (
        manualFilterMode === "unworked"
        && (item.note_operatore?.trim() || item.assigned_to != null || item.status !== "aperta")
      ) {
        return false;
      }
      return true;
    });
  }, [items, manualFilterMode]);
  const selectedManualAnomalia = useMemo(
    () => manualTableItems.find((item) => item.id === selectedManualAnomaliaId) ?? manualTableItems[0] ?? null,
    [manualTableItems, selectedManualAnomaliaId],
  );
  const selectedAssignedUser = useMemo(
    () => assignableUsers.find((user) => selectedManualAnomalia?.assigned_to === user.id) ?? null,
    [assignableUsers, selectedManualAnomalia],
  );

  useEffect(() => {
    if (selectedManualAnomaliaId && !manualTableItems.some((item) => item.id === selectedManualAnomaliaId)) {
      setSelectedManualAnomaliaId(manualTableItems[0]?.id ?? null);
    }
  }, [manualTableItems, selectedManualAnomaliaId]);

  useEffect(() => {
    setManualNoteDraft(selectedManualAnomalia?.note_operatore ?? "");
    setManualAssignedToDraft(selectedManualAnomalia?.assigned_to != null ? String(selectedManualAnomalia.assigned_to) : "");
    setReportTitleDraft(
      selectedManualAnomalia
        ? `${selectedManualAnomalia.tipo} · ${selectedManualAnomalia.descrizione?.trim() || "Anomalia Catasto"}`
        : "",
    );
    setReportDescriptionDraft(
      selectedManualAnomalia
        ? [
          `Anomalia Catasto ${selectedManualAnomalia.id}`,
          selectedManualAnomalia.descrizione?.trim() ? `Descrizione: ${selectedManualAnomalia.descrizione.trim()}` : null,
          selectedManualAnomalia.anno_campagna != null ? `Anno campagna: ${selectedManualAnomalia.anno_campagna}` : null,
          selectedManualAnomalia.utenza_id ? `Utenza collegata: ${selectedManualAnomalia.utenza_id}` : null,
          selectedManualAnomalia.particella_id ? `Particella collegata: ${selectedManualAnomalia.particella_id}` : null,
          selectedManualAnomalia.note_operatore?.trim() ? `Nota operatore: ${selectedManualAnomalia.note_operatore.trim()}` : null,
        ].filter(Boolean).join("\n")
        : "",
    );
    setReportCategoryId("");
    setReportSeverityId("");
    setManualNoteMessage(null);
  }, [selectedManualAnomalia]);

  useEffect(() => {
    const params = new URLSearchParams();
    if (filters.tipo) params.set("tipo", filters.tipo);
    if (filters.severita) params.set("severita", filters.severita);
    if (filters.status) params.set("status", filters.status);
    if (filters.anno) params.set("anno", filters.anno);
    if (filters.distretto) params.set("distretto", filters.distretto);
    if (overviewPage > 1) params.set("page", String(overviewPage));
    if (tab !== "cf") params.set("tab", tab);
    if (manualSearch.trim()) params.set("q", manualSearch.trim());
    if (manualFilterMode !== "all") params.set("manual", manualFilterMode);
    if (manualSortBy !== "created_at") params.set("sort_by", manualSortBy);
    if (manualSortDir !== "desc") params.set("sort_dir", manualSortDir);
    const next = params.toString();
    const current = searchParams.toString();
    if (next !== current) {
      router.replace(next ? `/catasto/anomalie?${next}` : "/catasto/anomalie");
    }
  }, [
    filters,
    manualFilterMode,
    manualSearch,
    manualSortBy,
    manualSortDir,
    overviewPage,
    router,
    searchParams,
    tab,
  ]);

  return (
    <CatastoPage
      title="Anomalie"
      description="Console operativa del dominio Catasto: triage, code di lavoro e primi wizard di correzione."
      breadcrumb="Catasto / Anomalie"
      requiredModule="catasto"
      requiredRoles={["admin", "super_admin"]}
    >
      <div className="page-stack">
        {error ? (
          <AlertBanner variant="danger" title="Errore caricamento">
            {error}
          </AlertBanner>
        ) : null}

        <article className="panel-card">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="section-title">Console anomalie Catasto</p>
              <p className="section-copy mt-1">
                Scegli una coda di lavoro qui sotto: ogni scheda apre il workspace dedicato. Anno e distretto restano il contesto condiviso tra tutte le code.
              </p>
            </div>
            <Link className="text-sm font-medium text-[#1D4E35] underline underline-offset-2" href="/catasto/import">
              Import & report
            </Link>
          </div>

          <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-2xl border border-[#d9dfd6] bg-white p-4 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Anomalie aggregate</p>
              <p className="mt-2 text-3xl font-semibold text-[#1D4E35]">{busy ? "…" : summaryTotal}</p>
              <p className="mt-1 text-xs text-gray-400">sui filtri di contesto correnti</p>
            </div>
            <div className="rounded-2xl border border-[#d9dfd6] bg-white p-4 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Code correggibili</p>
              <p className="mt-2 text-3xl font-semibold text-[#1D4E35]">{correggibiliCount}</p>
              <p className="mt-1 text-xs text-gray-400">CF · comuni · particelle</p>
            </div>
            <div className="rounded-2xl border border-[#d9dfd6] bg-white p-4 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Triage manuale</p>
              <p className="mt-2 text-3xl font-semibold text-[#1D4E35]">{manualQueueCount}</p>
              <p className="mt-1 text-xs text-gray-400">senza wizard dedicato</p>
            </div>
            <div className="rounded-2xl border border-[#d9dfd6] bg-white p-4 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Registro caricato</p>
              <p className="mt-2 text-3xl font-semibold text-[#1D4E35]">{busy ? "…" : total}</p>
              <p className="mt-1 text-xs text-gray-400">{items.length} righe nella pagina corrente</p>
            </div>
          </div>
        </article>

        <nav className="flex flex-wrap gap-2" aria-label="Code anomalie">
          {tabs.map((entry) => {
            const isActive = tab === entry.id;
            return (
              <button
                key={entry.id}
                type="button"
                onClick={() => handleSelectTab(entry.id, entry.tipo)}
                aria-pressed={isActive}
                className={`flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition ${
                  isActive
                    ? "border-[#1D4E35] bg-[#1D4E35] text-white shadow-sm"
                    : "border-[#d9dfd6] bg-white text-gray-700 hover:border-[#1D4E35]"
                }`}
              >
                <span>{entry.label}</span>
                {entry.count != null ? (
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                      isActive ? "bg-white/20 text-white" : "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {entry.count}
                  </span>
                ) : null}
              </button>
            );
          })}
        </nav>

        <article className="panel-card">
          <div className="flex flex-wrap items-end gap-4">
            <label className="text-sm font-medium text-gray-700">
              Anno
              <input
                className="form-control mt-1"
                inputMode="numeric"
                value={filters.anno}
                onChange={(event) => {
                  setOverviewPage(1);
                  setCfPage(1);
                  setComunePage(1);
                  setParticellaPage(1);
                  setFilters((current) => ({ ...current, anno: event.target.value }));
                }}
                placeholder="Tutti"
              />
            </label>
            <label className="text-sm font-medium text-gray-700">
              Distretto
              <input
                className="form-control mt-1"
                inputMode="numeric"
                value={filters.distretto}
                onChange={(event) => {
                  setOverviewPage(1);
                  setCfPage(1);
                  setComunePage(1);
                  setParticellaPage(1);
                  setFilters((current) => ({ ...current, distretto: event.target.value }));
                }}
                placeholder="Tutti"
              />
            </label>
            <button
              className="btn-secondary"
              type="button"
              disabled={busy}
              onClick={() => {
                setFilters(buildDefaultFilters());
                setOverviewPage(1);
                setCfPage(1);
                setComunePage(1);
                setParticellaPage(1);
              }}
            >
              Reset contesto
            </button>
            <span className="text-sm text-gray-500">
              Scheda attiva: <span className="font-medium text-gray-900">{activeTabLabel}</span> · {activeWorkspaceCount} righe
            </span>
          </div>
        </article>

        {tab === "ade" ? (
        <article className="panel-card border-emerald-100 bg-gradient-to-br from-white via-[#f7fbf7] to-[#eef8f2]">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
            <div>
              <p className="section-title">Scansione AdE particelle non collegate</p>
              <p className="section-copy mt-1">
                Scarica tramite SISTER/Visure la visura storica sintetica delle `ruolo_particelle` non collegate a `cat_particelle`, archivia il PDF e salva catena di soppressione, frazionamento, origine/variazione e data scansione.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button className="btn-secondary" type="button" disabled={adeScanBusy} onClick={() => void loadAdeScan()}>
                Aggiorna
              </button>
              <button className="btn-primary" type="button" disabled={adeScanBusy} onClick={() => void handleRunAdeScan()}>
                {adeScanBusy ? "Preparazione..." : "Metti in coda tutte le visure"}
              </button>
            </div>
          </div>
          <p className="mt-3 text-sm text-gray-600">
            Il batch crea tutte le richieste eleggibili e il worker le elabora progressivamente dalla coda SISTER.
          </p>

          {adeScanError ? (
            <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{adeScanError}</div>
          ) : null}
          {adeScanMessage ? (
            <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{adeScanMessage}</div>
          ) : null}

          <div className="mt-5 grid gap-4 md:grid-cols-3">
            <div className="rounded-2xl border border-white bg-white/80 p-4 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Non collegate</p>
              <p className="mt-2 text-3xl font-semibold text-[#1D4E35]">{adeScanSummary?.total_unmatched ?? "—"}</p>
            </div>
            <div className="rounded-2xl border border-white bg-white/80 p-4 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">In coda SISTER</p>
              <p className="mt-2 text-3xl font-semibold text-[#1D4E35]">{adeScanSummary?.pending ?? "—"}</p>
            </div>
            <div className="rounded-2xl border border-white bg-white/80 p-4 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Ultima scansione</p>
              <p className="mt-2 text-sm font-semibold text-gray-900">
                {adeScanSummary?.last_checked_at ? formatDateTime(adeScanSummary.last_checked_at) : "Mai eseguita"}
              </p>
            </div>
          </div>

          <div className="mt-4 grid gap-4 xl:grid-cols-2">
            <div className="rounded-2xl border border-white bg-white/80 p-4 shadow-sm">
              <p className="text-sm font-semibold text-gray-900">Esiti scansione</p>
              <div className="mt-3 space-y-2">
                {(adeScanSummary?.buckets ?? []).slice(0, 6).map((bucket) => (
                  <div key={`${bucket.status}-${bucket.classification}`} className="flex items-center justify-between rounded-xl bg-gray-50 px-3 py-2 text-sm">
                    <span className="font-medium text-gray-700">{bucket.status} / {bucket.classification}</span>
                    <span className="font-semibold text-[#1D4E35]">{bucket.count}</span>
                  </div>
                ))}
                {adeScanSummary && adeScanSummary.buckets.length === 0 ? (
                  <p className="text-sm text-gray-500">Nessun esito AdE salvato.</p>
                ) : null}
              </div>
            </div>
            <div className="rounded-2xl border border-white bg-white/80 p-4 shadow-sm">
              <p className="text-sm font-semibold text-gray-900">Prime righe candidate</p>
              <div className="mt-3 space-y-2">
                {adeScanCandidates.map((item) => (
                  <div key={item.ruolo_particella_id} className="rounded-xl bg-gray-50 px-3 py-2 text-sm text-gray-600">
                    <p className="font-medium text-gray-900">
                      {item.comune_nome} {item.sezione ? `sez. ${item.sezione} ` : ""}Fg. {item.foglio} Part. {item.particella}
                      {item.subalterno ? ` Sub. ${item.subalterno}` : ""}
                    </p>
                    <p className="mt-1">
                      Motivo: {item.match_reason || "—"} · Stato AdE: {item.ade_scan_status || "non scansionata"}
                      {item.ade_scan_document_id ? " · PDF acquisito" : ""}
                    </p>
                  </div>
                ))}
                {adeScanCandidates.length === 0 ? (
                  <p className="text-sm text-gray-500">Nessuna candidata immediatamente disponibile.</p>
                ) : null}
              </div>
            </div>
          </div>

          <div className="mt-4 rounded-2xl border border-white bg-white/80 p-4 shadow-sm">
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div>
                <p className="text-sm font-semibold text-gray-900">Batch recenti scansione AdE</p>
                <p className="mt-1 text-sm text-gray-500">
                  Ha senso usare lo stesso workspace di elaborazioni: qui apri direttamente il dettaglio del lotto senza cambiare pattern operativo.
                </p>
              </div>
              {runningAdeScanBatch ? (
                <button className="btn-secondary" type="button" onClick={() => handleOpenAdeScanBatch(runningAdeScanBatch)}>
                  Apri batch attivo
                </button>
              ) : null}
            </div>

            {adeScanBatches.length === 0 ? (
              <p className="mt-3 text-sm text-gray-500">Nessun batch scansione AdE trovato per l&apos;utente corrente.</p>
            ) : (
              <div className="mt-4 overflow-x-auto">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Nome</th>
                      <th>Stato</th>
                      <th>Esito</th>
                      <th>Operazione</th>
                      <th>Creato</th>
                      <th>Azioni</th>
                    </tr>
                  </thead>
                  <tbody>
                    {adeScanBatches.map((batch) => (
                      <tr key={batch.id}>
                        <td>
                          <button
                            className="font-medium text-[#1D4E35] transition hover:text-[#143726]"
                            onClick={() => handleOpenAdeScanBatch(batch)}
                            type="button"
                          >
                            {batch.name ?? batch.id}
                          </button>
                        </td>
                        <td><ElaborazioneStatusBadge status={batch.status} /></td>
                        <td>
                          <div className="flex flex-wrap gap-2 text-xs text-gray-600">
                            <span>ok {batch.completed_items}</span>
                            <span>ko {batch.failed_items}</span>
                            {batch.not_found_items > 0 ? <span>n.d. {batch.not_found_items}</span> : null}
                            {batch.skipped_items > 0 ? <span>skip {batch.skipped_items}</span> : null}
                          </div>
                        </td>
                        <td><ElaborazioneOperationMessage value={batch.current_operation} /></td>
                        <td>{formatDateTime(batch.created_at)}</td>
                        <td>
                          <button
                            className="text-sm text-[#1D4E35] transition hover:text-[#143726]"
                            onClick={() => handleOpenAdeScanBatch(batch)}
                            type="button"
                          >
                            Apri batch
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </article>
        ) : null}

        {wizardMode === "cf" ? (
        <article className="panel-card">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="section-title">Wizard codice fiscale</p>
              <p className="section-copy mt-1">
                Correggi `VAL-02-cf_invalido` e `VAL-03-cf_mancante` senza uscire dal flusso: inserisci il dato corretto e chiudi automaticamente le anomalie CF collegate.
              </p>
            </div>
            <div className="rounded-full bg-[#eef5ef] px-3 py-1 text-sm font-medium text-[#1D4E35]">
              {cfBusy ? "Sincronizzazione..." : `${cfItems.length} righe su ${cfTotal}`}
            </div>
          </div>

          <div className="mt-4 rounded-2xl border border-[#d9dfd6] bg-[#f6faf6] px-4 py-3 text-sm text-gray-700">
            <span className="font-medium text-gray-900">Come usarlo:</span> controlla il CF attuale, usa il suggerimento se presente oppure digita il valore corretto, poi conferma con `Applica correzione`.
          </div>

          {cfError ? (
            <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{cfError}</div>
          ) : null}
          {cfMessage ? (
            <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{cfMessage}</div>
          ) : null}

          {cfBusy && cfItems.length === 0 ? (
            <div className="mt-4 rounded-xl border border-gray-100 bg-gray-50 px-4 py-5 text-sm text-gray-500">Caricamento workspace CF...</div>
          ) : cfItems.length === 0 ? (
            <div className="mt-4">
              <EmptyState
                icon={SearchIcon}
                title="Nessuna anomalia CF aperta"
                description="Per anno e distretto correnti non risultano righe `VAL-02` o `VAL-03` da correggere."
              />
            </div>
          ) : (
            <div className="mt-5 space-y-4">
              {cfItems.map((item) => (
                <div key={item.anomalia_id} className="rounded-2xl border border-[#d9dfd6] bg-white p-4 shadow-sm">
                  <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                    <div className="space-y-3">
                      <div className="flex flex-wrap items-center gap-3">
                        <span className="text-sm font-semibold text-gray-900">{item.denominazione || "Utenza senza denominazione"}</span>
                        <AnomaliaStatusBadge severita={item.severita} />
                        <AnomaliaStatusPill status={item.status} />
                        <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600">{item.tipo}</span>
                      </div>
                      <div className="grid gap-3 text-sm text-gray-600 md:grid-cols-2 xl:grid-cols-4">
                        <p>CF attuale: <span className="font-medium text-gray-900">{item.codice_fiscale || "—"}</span></p>
                        <p>CF raw: <span className="font-medium text-gray-900">{item.codice_fiscale_raw || "—"}</span></p>
                        <p>Errore: <span className="font-medium text-gray-900">{item.error_code || "Dato mancante"}</span></p>
                        <p>Distretto: <span className="font-medium text-gray-900">{item.num_distretto ?? "—"}</span></p>
                        <p>Comune: <span className="font-medium text-gray-900">{item.nome_comune || "—"}</span></p>
                        <p>
                          Riferimento: <span className="font-medium text-gray-900">{[item.sezione_catastale, item.foglio, item.particella, item.subalterno].filter(Boolean).join(" / ") || "—"}</span>
                        </p>
                        <p>Anno: <span className="font-medium text-gray-900">{item.anno_campagna ?? "—"}</span></p>
                        <p>Aperta il: <span className="font-medium text-gray-900">{formatDateTime(item.created_at)}</span></p>
                      </div>
                    </div>

                    <div className="w-full max-w-xl rounded-2xl border border-gray-100 bg-gray-50 p-4">
                      <label className="block text-sm font-medium text-gray-700">
                        Correzione CF / P.IVA
                        <input
                          className="form-control mt-1"
                          value={cfDrafts[item.anomalia_id] ?? ""}
                          onChange={(event) =>
                            setCfDrafts((current) => ({
                              ...current,
                              [item.anomalia_id]: event.target.value.toUpperCase(),
                            }))
                          }
                          placeholder="Inserisci il valore corretto"
                        />
                      </label>
                      <div className="mt-3 flex flex-wrap items-center gap-2">
                        {item.suggested_codice_fiscale ? (
                          <button
                            type="button"
                            className="btn-secondary !px-2.5 !py-1 text-xs"
                            onClick={() =>
                              setCfDrafts((current) => ({
                                ...current,
                                [item.anomalia_id]: item.suggested_codice_fiscale ?? "",
                              }))
                            }
                          >
                            Usa suggerito: {item.suggested_codice_fiscale}
                          </button>
                        ) : null}
                        <button
                          type="button"
                          className="btn-primary"
                          disabled={applyingAnomaliaId === item.anomalia_id}
                          onClick={() => void handleApplyCf(item)}
                        >
                          {applyingAnomaliaId === item.anomalia_id ? "Applicazione..." : "Applica correzione"}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
              <Pagination
                pageIndex={cfPage - 1}
                pageCount={cfPageCount}
                canPreviousPage={cfPage > 1}
                canNextPage={cfPage < cfPageCount}
                onPreviousPage={() => setCfPage((current) => Math.max(1, current - 1))}
                onNextPage={() => setCfPage((current) => (current < cfPageCount ? current + 1 : current))}
              />
            </div>
          )}
        </article>
        ) : null}

        {wizardMode === "comune" ? (
        <article className="panel-card">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="section-title">Wizard comune invalido</p>
              <p className="section-copy mt-1">
                Scegli il comune corretto tra le candidate proposte, verifica l&apos;anteprima prima/dopo e applica la correzione singola o batch.
              </p>
            </div>
            <div className="rounded-full bg-[#eef5ef] px-3 py-1 text-sm font-medium text-[#1D4E35]">
              {comuneBusy ? "Sincronizzazione..." : `${comuneItems.length} righe su ${comuneTotal}`}
            </div>
          </div>

          <div className="mt-4 rounded-2xl border border-[#d9dfd6] bg-[#f6faf6] px-4 py-3 text-sm text-gray-700">
            <span className="font-medium text-gray-900">Come usarlo:</span> lascia selezionata la candidata migliore, controlla l&apos;anteprima e usa `Applica batch` solo dopo aver rivisto le righe selezionate.
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              type="button"
              className="btn-primary"
              disabled={comuneBusy || applyingComuneAnomaliaId === "__batch__" || selectedComuneCount === 0}
              onClick={() => void handleApplyComuneBatch()}
            >
              {applyingComuneAnomaliaId === "__batch__" ? "Applicazione batch..." : `Applica batch (${selectedComuneCount})`}
            </button>
            <button className="btn-secondary" type="button" disabled={comuneBusy} onClick={handleSelectTopComuni}>
              Seleziona top candidate
            </button>
            <button className="btn-secondary" type="button" disabled={comuneBusy} onClick={handleClearComuneSelections}>
              Pulisci selezioni
            </button>
            <span className="text-sm text-gray-500">
              Allinea `comune_id`, `cod_comune_capacitas` e `nome_comune` sull&apos;utenza usando il mapping dei comuni validi del dominio.
            </span>
          </div>

          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700">
              Nota batch applicata alle correzioni
              <input
                className="form-control mt-1"
                value={comuneBatchNote}
                onChange={(event) => setComuneBatchNote(event.target.value)}
                placeholder="Es. Mapping comune validato da operatore"
              />
            </label>
          </div>

          {comuneError ? (
            <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{comuneError}</div>
          ) : null}
          {comuneMessage ? (
            <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{comuneMessage}</div>
          ) : null}

          {comuneBusy && comuneItems.length === 0 ? (
            <div className="mt-4 rounded-xl border border-gray-100 bg-gray-50 px-4 py-5 text-sm text-gray-500">Caricamento workspace comuni...</div>
          ) : comuneItems.length === 0 ? (
            <div className="mt-4">
              <EmptyState
                icon={SearchIcon}
                title="Nessuna anomalia comune aperta"
                description="Per anno e distretto correnti non risultano righe `VAL-04` da riallineare."
              />
            </div>
          ) : (
            <div className="mt-5 space-y-4">
              {comuneItems.map((item) => (
                <div key={item.anomalia_id} className="rounded-2xl border border-[#d9dfd6] bg-white p-4 shadow-sm">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="text-sm font-semibold text-gray-900">{item.denominazione || "Utenza senza denominazione"}</span>
                    <AnomaliaStatusBadge severita={item.severita} />
                    <AnomaliaStatusPill status={item.status} />
                    <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600">{item.tipo}</span>
                  </div>

                  <div className="mt-3 grid gap-3 text-sm text-gray-600 md:grid-cols-2 xl:grid-cols-4">
                    <p>Comune attuale: <span className="font-medium text-gray-900">{item.nome_comune || "—"}</span></p>
                    <p>Codice attuale: <span className="font-medium text-gray-900">{item.cod_comune_capacitas ?? "—"}</span></p>
                    <p>Codice sorgente: <span className="font-medium text-gray-900">{item.source_cod_comune_capacitas ?? "—"}</span></p>
                    <p>Distretto: <span className="font-medium text-gray-900">{item.num_distretto ?? "—"}</span></p>
                    <p>
                      Riferimento: <span className="font-medium text-gray-900">{[item.sezione_catastale, item.foglio, item.particella, item.subalterno].filter(Boolean).join(" / ") || "—"}</span>
                    </p>
                    <p>Anno: <span className="font-medium text-gray-900">{item.anno_campagna ?? "—"}</span></p>
                    <p>Aperta il: <span className="font-medium text-gray-900">{formatDateTime(item.created_at)}</span></p>
                  </div>

                  <div className="mt-4 rounded-2xl border border-gray-100 bg-gray-50 p-4">
                    <p className="text-sm font-medium text-gray-900">Candidate comune</p>
                    {item.candidates.length === 0 ? (
                      <p className="mt-2 text-sm text-gray-500">Nessun comune candidato trovato con i dati correnti. La riga resta in triage manuale.</p>
                    ) : (
                      <div className="mt-3 space-y-3">
                        {item.candidates.map((candidate) => (
                          <div key={candidate.id} className="flex flex-col gap-3 rounded-xl border border-white bg-white px-4 py-3 xl:flex-row xl:items-center xl:justify-between">
                            <label className="flex items-start gap-3">
                              <input
                                type="radio"
                                name={`comune-${item.anomalia_id}`}
                                checked={(comuneDrafts[item.anomalia_id] ?? "") === candidate.id}
                                onChange={() =>
                                  setComuneDrafts((current) => ({
                                    ...current,
                                    [item.anomalia_id]: candidate.id,
                                  }))
                                }
                              />
                              <div className="grid gap-2 text-sm text-gray-600 md:grid-cols-2 xl:grid-cols-4">
                                <p>Comune: <span className="font-medium text-gray-900">{candidate.nome_comune}</span></p>
                                <p>Codice Capacitas: <span className="font-medium text-gray-900">{candidate.cod_comune_capacitas}</span></p>
                                <p>Codice catastale: <span className="font-medium text-gray-900">{candidate.codice_catastale || "—"}</span></p>
                                <p>Match score: <span className="font-medium text-gray-900">{candidate.match_score}</span></p>
                                <p>Legacy: <span className="font-medium text-gray-900">{candidate.nome_comune_legacy || "—"}</span></p>
                                <p>Provincia: <span className="font-medium text-gray-900">{candidate.sigla_provincia || "—"}</span></p>
                              </div>
                            </label>
                          </div>
                        ))}
                      </div>
                    )}

                    {(() => {
                      const selectedCandidate = item.candidates.find((candidate) => candidate.id === comuneDrafts[item.anomalia_id]);
                      if (!selectedCandidate) {
                        return null;
                      }

                      return (
                        <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3">
                          <p className="text-sm font-medium text-emerald-900">Anteprima prima / dopo</p>
                          <div className="mt-3 grid gap-3 md:grid-cols-2">
                            <div className="rounded-lg border border-emerald-100 bg-white px-3 py-3 text-sm text-gray-600">
                              <p className="font-medium text-gray-900">Prima</p>
                              <p className="mt-2">
                                Comune: <span className="font-medium text-gray-900">{item.nome_comune || "—"}</span>
                              </p>
                              <p>
                                Codice comune: <span className="font-medium text-gray-900">{item.cod_comune_capacitas ?? item.source_cod_comune_capacitas ?? "—"}</span>
                              </p>
                            </div>
                            <div className="rounded-lg border border-emerald-100 bg-white px-3 py-3 text-sm text-gray-600">
                              <p className="font-medium text-gray-900">Dopo</p>
                              <p className="mt-2">
                                Comune: <span className="font-medium text-gray-900">{selectedCandidate.nome_comune}</span>
                              </p>
                              <p>
                                Codice comune: <span className="font-medium text-gray-900">{selectedCandidate.cod_comune_capacitas}</span>
                              </p>
                            </div>
                          </div>
                          <div className="mt-3">
                            <button
                              type="button"
                              className="btn-primary"
                              disabled={applyingComuneAnomaliaId === item.anomalia_id || applyingComuneAnomaliaId === "__batch__"}
                              onClick={() => void handleApplyComune(item.anomalia_id, selectedCandidate.id)}
                            >
                              {applyingComuneAnomaliaId === item.anomalia_id ? "Applicazione..." : "Applica solo questa riga"}
                            </button>
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                </div>
              ))}
              <Pagination
                pageIndex={comunePage - 1}
                pageCount={comunePageCount}
                canPreviousPage={comunePage > 1}
                canNextPage={comunePage < comunePageCount}
                onPreviousPage={() => setComunePage((current) => Math.max(1, current - 1))}
                onNextPage={() => setComunePage((current) => (current < comunePageCount ? current + 1 : current))}
              />
            </div>
          )}
        </article>
        ) : null}

        {wizardMode === "particella" ? (
        <article className="panel-card">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="section-title">Wizard particella assente</p>
              <p className="section-copy mt-1">
                Collega rapidamente `VAL-05-particella_assente` alla particella corretta partendo dalle candidate già ordinate per affinità.
              </p>
            </div>
            <div className="rounded-full bg-[#eef5ef] px-3 py-1 text-sm font-medium text-[#1D4E35]">
              {particellaBusy ? "Sincronizzazione..." : `${particellaItems.length} righe su ${particellaTotal}`}
            </div>
          </div>

          <div className="mt-4 rounded-2xl border border-[#d9dfd6] bg-[#f6faf6] px-4 py-3 text-sm text-gray-700">
            <span className="font-medium text-gray-900">Come usarlo:</span> se la prima candidata è corretta usa `Seleziona top candidate`, altrimenti filtra le righe senza match e gestiscile nel registro manuale.
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              type="button"
              className="btn-primary"
              disabled={particellaBusy || applyingParticellaAnomaliaId === "__batch__" || selectedParticellaCount === 0}
              onClick={() => void handleApplyParticellaBatch()}
            >
              {applyingParticellaAnomaliaId === "__batch__" ? "Applicazione batch..." : `Applica batch (${selectedParticellaCount})`}
            </button>
            <button className="btn-secondary" type="button" disabled={particellaBusy} onClick={handleSelectTopCandidates}>
              Seleziona top candidate
            </button>
            <button className="btn-secondary" type="button" disabled={particellaBusy} onClick={handleClearParticellaSelections}>
              Pulisci selezioni
            </button>
            <label className="text-sm font-medium text-gray-700">
              Vista
              <select
                className="form-control mt-1 min-w-56"
                value={particellaFilterMode}
                onChange={(event) => setParticellaFilterMode(event.target.value as ParticellaFilterMode)}
              >
                <option value="all">Tutte le righe</option>
                <option value="without_candidates">Solo senza candidate</option>
              </select>
            </label>
            <span className="text-sm text-gray-500">
              {withoutCandidatesCount} righe senza match candidato. Selezione esplicita candidata e collegamento massivo sulle righe attualmente in workspace.
            </span>
          </div>

          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700">
              Nota batch applicata alle correzioni
              <input
                className="form-control mt-1"
                value={particellaBatchNote}
                onChange={(event) => setParticellaBatchNote(event.target.value)}
                placeholder="Es. Match particella validato da operatore"
              />
            </label>
          </div>

          {particellaError ? (
            <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{particellaError}</div>
          ) : null}
          {particellaMessage ? (
            <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{particellaMessage}</div>
          ) : null}

          {particellaBusy && particellaItems.length === 0 ? (
            <div className="mt-4 rounded-xl border border-gray-100 bg-gray-50 px-4 py-5 text-sm text-gray-500">Caricamento workspace particelle...</div>
          ) : visibleParticellaItems.length === 0 ? (
            <div className="mt-4">
              <EmptyState
                icon={SearchIcon}
                title={particellaItems.length === 0 ? "Nessuna anomalia particella aperta" : "Nessuna riga nella vista corrente"}
                description={
                  particellaItems.length === 0
                    ? "Per anno e distretto correnti non risultano righe `VAL-05` da riallineare."
                    : "Il filtro workspace attuale non restituisce righe visibili."
                }
              />
            </div>
          ) : (
            <div className="mt-5 space-y-4">
              {visibleParticellaItems.map((item) => (
                <div key={item.anomalia_id} className="rounded-2xl border border-[#d9dfd6] bg-white p-4 shadow-sm">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="text-sm font-semibold text-gray-900">{item.denominazione || "Utenza senza denominazione"}</span>
                    <AnomaliaStatusBadge severita={item.severita} />
                    <AnomaliaStatusPill status={item.status} />
                    <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600">{item.tipo}</span>
                  </div>

                  <div className="mt-3 grid gap-3 text-sm text-gray-600 md:grid-cols-2 xl:grid-cols-4">
                    <p>Comune: <span className="font-medium text-gray-900">{item.nome_comune || "—"}</span></p>
                    <p>Codice comune: <span className="font-medium text-gray-900">{item.cod_comune_capacitas ?? "—"}</span></p>
                    <p>Distretto: <span className="font-medium text-gray-900">{item.num_distretto ?? "—"}</span></p>
                    <p>
                      Riferimento input: <span className="font-medium text-gray-900">{[item.sezione_catastale, item.foglio, item.particella, item.subalterno].filter(Boolean).join(" / ") || "—"}</span>
                    </p>
                    <p>Anno: <span className="font-medium text-gray-900">{item.anno_campagna ?? "—"}</span></p>
                    <p>Aperta il: <span className="font-medium text-gray-900">{formatDateTime(item.created_at)}</span></p>
                  </div>

                  <div className="mt-4 rounded-2xl border border-gray-100 bg-gray-50 p-4">
                    <p className="text-sm font-medium text-gray-900">Candidate particella</p>
                    {item.candidates.length === 0 ? (
                      <p className="mt-2 text-sm text-gray-500">Nessuna candidata trovata con i dati correnti. Questa riga resta in triage manuale.</p>
                    ) : (
                      <div className="mt-3 space-y-3">
                        {item.candidates.map((candidate) => (
                          <div key={candidate.id} className="flex flex-col gap-3 rounded-xl border border-white bg-white px-4 py-3 xl:flex-row xl:items-center xl:justify-between">
                            <label className="flex items-start gap-3">
                              <input
                                type="radio"
                                name={`candidate-${item.anomalia_id}`}
                                checked={(particellaDrafts[item.anomalia_id] ?? "") === candidate.id}
                                onChange={() =>
                                  setParticellaDrafts((current) => ({
                                    ...current,
                                    [item.anomalia_id]: candidate.id,
                                  }))
                                }
                              />
                              <div className="grid gap-2 text-sm text-gray-600 md:grid-cols-2 xl:grid-cols-4">
                                <p>
                                  Particella: <span className="font-medium text-gray-900">{[candidate.sezione_catastale, candidate.foglio, candidate.particella, candidate.subalterno].filter(Boolean).join(" / ")}</span>
                                </p>
                                <p>Comune: <span className="font-medium text-gray-900">{candidate.nome_comune || "—"}</span></p>
                                <p>Distretto: <span className="font-medium text-gray-900">{candidate.num_distretto || "—"}</span></p>
                                <p>Match score: <span className="font-medium text-gray-900">{candidate.match_score}</span></p>
                                <p>Codice catastale: <span className="font-medium text-gray-900">{candidate.codice_catastale || "—"}</span></p>
                                <p>Anagrafica: <span className="font-medium text-gray-900">{candidate.ha_anagrafica ? "Presente" : "Assente"}</span></p>
                              </div>
                            </label>
                          </div>
                        ))}
                      </div>
                    )}

                    {(() => {
                      const selectedCandidate = item.candidates.find((candidate) => candidate.id === particellaDrafts[item.anomalia_id]);
                      if (!selectedCandidate) {
                        return null;
                      }

                      return (
                        <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3">
                          <p className="text-sm font-medium text-emerald-900">Anteprima prima / dopo</p>
                          <div className="mt-3 grid gap-3 md:grid-cols-2">
                            <div className="rounded-lg border border-emerald-100 bg-white px-3 py-3 text-sm text-gray-600">
                              <p className="font-medium text-gray-900">Prima</p>
                              <p className="mt-2">
                                Comune: <span className="font-medium text-gray-900">{item.nome_comune || "—"}</span>
                              </p>
                              <p>
                                Riferimento: <span className="font-medium text-gray-900">{[item.sezione_catastale, item.foglio, item.particella, item.subalterno].filter(Boolean).join(" / ") || "—"}</span>
                              </p>
                              <p>
                                Particella collegata: <span className="font-medium text-gray-900">assente</span>
                              </p>
                            </div>
                            <div className="rounded-lg border border-emerald-100 bg-white px-3 py-3 text-sm text-gray-600">
                              <p className="font-medium text-gray-900">Dopo</p>
                              <p className="mt-2">
                                Comune: <span className="font-medium text-gray-900">{selectedCandidate.nome_comune || "—"}</span>
                              </p>
                              <p>
                                Riferimento: <span className="font-medium text-gray-900">{[selectedCandidate.sezione_catastale, selectedCandidate.foglio, selectedCandidate.particella, selectedCandidate.subalterno].filter(Boolean).join(" / ")}</span>
                              </p>
                              <p>
                                Distretto: <span className="font-medium text-gray-900">{selectedCandidate.num_distretto || "—"}</span>
                              </p>
                            </div>
                          </div>
                          <div className="mt-3">
                            <button
                              type="button"
                              className="btn-primary"
                              disabled={applyingParticellaAnomaliaId === item.anomalia_id || applyingParticellaAnomaliaId === "__batch__"}
                              onClick={() => void handleApplyParticella(item.anomalia_id, selectedCandidate.id)}
                            >
                              {applyingParticellaAnomaliaId === item.anomalia_id ? "Applicazione..." : "Applica solo questa riga"}
                            </button>
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                </div>
              ))}
              <Pagination
                pageIndex={particellaPage - 1}
                pageCount={particellaPageCount}
                canPreviousPage={particellaPage > 1}
                canNextPage={particellaPage < particellaPageCount}
                onPreviousPage={() => setParticellaPage((current) => Math.max(1, current - 1))}
                onNextPage={() => setParticellaPage((current) => (current < particellaPageCount ? current + 1 : current))}
              />
            </div>
          )}
        </article>
        ) : null}

        {tab === "manuale" && selectedManualAnomalia ? (
          <article className="panel-card border-[#d9dfd6] bg-[#fbfdfb]">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
              <div>
                <p className="section-title">Dettaglio anomalia selezionata</p>
                <p className="section-copy mt-1">
                  Click su una riga del registro per mantenere qui il contesto operativo: stato, note, payload tecnico e accesso rapido alla particella collegata.
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <AnomaliaStatusBadge severita={selectedManualAnomalia.severita} />
                <AnomaliaStatusPill status={selectedManualAnomalia.status} />
                <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600">{selectedManualAnomalia.tipo}</span>
              </div>
            </div>

            <div className="mt-5 grid gap-4 xl:grid-cols-[minmax(0,1.4fr)_minmax(320px,1fr)]">
              <div className="space-y-4">
                <div className="grid gap-3 text-sm text-gray-600 md:grid-cols-2 xl:grid-cols-3">
                  <p>ID anomalia: <span className="font-medium text-gray-900">{selectedManualAnomalia.id}</span></p>
                  <p>Anno: <span className="font-medium text-gray-900">{selectedManualAnomalia.anno_campagna ?? "—"}</span></p>
                  <p>Utente assegnato: <span className="font-medium text-gray-900">{selectedManualAnomalia.assigned_to ?? "—"}</span></p>
                  <p>Utenza collegata: <span className="font-medium text-gray-900">{selectedManualAnomalia.utenza_id ?? "—"}</span></p>
                  <p>Particella collegata: <span className="font-medium text-gray-900">{selectedManualAnomalia.particella_id ?? "—"}</span></p>
                  <p>Segnalazione: <span className="font-medium text-gray-900">{selectedManualAnomalia.segnalazione_id ?? "—"}</span></p>
                  <p>Creata il: <span className="font-medium text-gray-900">{formatDateTime(selectedManualAnomalia.created_at)}</span></p>
                  <p>Aggiornata il: <span className="font-medium text-gray-900">{formatDateTime(selectedManualAnomalia.updated_at)}</span></p>
                </div>

                <div className="rounded-2xl border border-gray-100 bg-white p-4">
                  <p className="text-sm font-semibold text-gray-900">Descrizione e note operatore</p>
                  <p className="mt-3 text-sm text-gray-700">{selectedManualAnomalia.descrizione ?? "Nessuna descrizione disponibile."}</p>
                  <div className="mt-3">
                    <CatastoAnomaliaExplainer anomalia={selectedManualAnomalia} buttonLabel="Approfondisci questa anomalia" />
                  </div>
                  <div className="mt-4 space-y-3 rounded-xl border border-dashed border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-600">
                    <label className="block text-sm font-medium text-gray-700">
                      Nota operatore
                      <textarea
                        className="form-control mt-1 min-h-28"
                        value={manualNoteDraft}
                        onChange={(event) => setManualNoteDraft(event.target.value)}
                        placeholder="Annotazioni operative, verifiche fatte, motivo chiusura o passaggi successivi"
                      />
                    </label>
                    <div className="flex flex-wrap gap-2">
                      <button
                        className="btn-secondary"
                        type="button"
                        disabled={manualNoteBusy}
                        onClick={() => void handleSaveManualNote(selectedManualAnomalia)}
                      >
                        {manualNoteBusy ? "Salvataggio..." : "Salva nota"}
                      </button>
                      <button
                        className="btn-secondary"
                        type="button"
                        disabled={manualNoteBusy}
                        onClick={() => void handleUpdateStatus(selectedManualAnomalia.id, "chiusa")}
                      >
                        Chiudi da pannello
                      </button>
                      <button
                        className="btn-secondary"
                        type="button"
                        disabled={manualNoteBusy}
                        onClick={() => void handleUpdateStatus(selectedManualAnomalia.id, "ignora")}
                      >
                        Ignora da pannello
                      </button>
                      <button
                        className="btn-secondary"
                        type="button"
                        disabled={manualNoteBusy}
                        onClick={() => void handleUpdateStatus(selectedManualAnomalia.id, "aperta")}
                      >
                        Riapri da pannello
                      </button>
                    </div>
                    {manualNoteMessage ? (
                      <p className="text-sm text-[#1D4E35]">{manualNoteMessage}</p>
                    ) : (
                      <p>
                        Ultima nota salvata: {selectedManualAnomalia.note_operatore?.trim() ? selectedManualAnomalia.note_operatore : "nessuna"}
                      </p>
                    )}
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div className="rounded-2xl border border-gray-100 bg-white p-4">
                  <p className="text-sm font-semibold text-gray-900">Azioni rapide</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {selectedManualAnomalia.particella_id ? (
                      <>
                        <Link
                          className="btn-secondary"
                          href={`/catasto/particelle/${selectedManualAnomalia.particella_id}`}
                        >
                          Apri pagina particella
                        </Link>
                        <button
                          className="btn-secondary"
                          type="button"
                          onClick={() => handleOpenManualParticellaWorkspace(selectedManualAnomalia)}
                        >
                          Apri in modale
                        </button>
                      </>
                    ) : (
                      <span className="text-sm text-gray-500">Nessuna particella collegata per questa anomalia.</span>
                    )}
                    {selectedManualAnomalia.segnalazione_id ? (
                      <Link
                        className="btn-secondary"
                        href={`/operazioni/segnalazioni/${selectedManualAnomalia.segnalazione_id}`}
                      >
                        Apri segnalazione
                      </Link>
                    ) : null}
                  </div>
                </div>

                {!selectedManualAnomalia.segnalazione_id ? (
                  <div className="rounded-2xl border border-[#d9dfd6] bg-[#f8fbf7] p-4">
                    <p className="text-sm font-semibold text-gray-900">Crea segnalazione operativa</p>
                    <p className="mt-1 text-sm text-gray-600">
                      Genera una segnalazione Operazioni e collegala subito a questa anomalia per tracciarne il follow-up.
                    </p>
                    <div className="mt-4 grid gap-3">
                      <div className="grid gap-3 md:grid-cols-2">
                        <label className="text-sm font-medium text-gray-700">
                          Categoria
                          <select
                            className="form-control mt-1"
                            value={reportCategoryId}
                            onChange={(event) => setReportCategoryId(event.target.value)}
                          >
                            <option value="">Seleziona categoria</option>
                            {reportCategories.map((item) => (
                              <option key={item.id} value={item.id}>
                                {item.name ?? item.code ?? item.id}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label className="text-sm font-medium text-gray-700">
                          Gravità
                          <select
                            className="form-control mt-1"
                            value={reportSeverityId}
                            onChange={(event) => setReportSeverityId(event.target.value)}
                          >
                            <option value="">Seleziona gravità</option>
                            {reportSeverities.map((item) => (
                              <option key={item.id} value={item.id}>
                                {item.name ?? item.code ?? item.id}
                              </option>
                            ))}
                          </select>
                        </label>
                      </div>
                      <label className="text-sm font-medium text-gray-700">
                        Titolo
                        <input
                          className="form-control mt-1"
                          value={reportTitleDraft}
                          onChange={(event) => setReportTitleDraft(event.target.value)}
                          placeholder="Titolo segnalazione"
                        />
                      </label>
                      <label className="text-sm font-medium text-gray-700">
                        Descrizione
                        <textarea
                          className="form-control mt-1 min-h-28"
                          value={reportDescriptionDraft}
                          onChange={(event) => setReportDescriptionDraft(event.target.value)}
                          placeholder="Contesto operativo e azioni richieste"
                        />
                      </label>
                      <div className="flex flex-wrap gap-2">
                        <button
                          className="btn-secondary"
                          type="button"
                          disabled={reportCreateBusy}
                          onClick={() => void handleCreateManualReport(selectedManualAnomalia)}
                        >
                          {reportCreateBusy ? "Creazione..." : "Crea segnalazione"}
                        </button>
                      </div>
                    </div>
                  </div>
                ) : null}

                <div className="rounded-2xl border border-gray-100 bg-white p-4">
                  <p className="text-sm font-semibold text-gray-900">Assegnazione</p>
                  <div className="mt-3 grid gap-3 md:grid-cols-[minmax(0,1fr)_auto]">
                    <label className="text-sm font-medium text-gray-700">
                      Assegna a
                      <select
                        className="form-control mt-1"
                        value={manualAssignedToDraft}
                        onChange={(event) => setManualAssignedToDraft(event.target.value)}
                      >
                        <option value="">Non assegnata</option>
                        {assignableUsers.map((user) => (
                          <option key={user.id} value={String(user.id)}>
                            {user.username} · {user.role}
                          </option>
                        ))}
                      </select>
                    </label>
                    <div className="flex items-end">
                      <button
                        className="btn-secondary"
                        type="button"
                        disabled={manualNoteBusy}
                        onClick={() => void handleSaveManualAssignment(selectedManualAnomalia)}
                      >
                        {manualNoteBusy ? "Salvataggio..." : "Salva assegnazione"}
                      </button>
                    </div>
                  </div>
                  <p className="mt-3 text-sm text-gray-500">
                    {selectedManualAnomalia.assigned_to != null
                      ? `Assegnazione corrente: ${selectedAssignedUser ? `${selectedAssignedUser.username} · ${selectedAssignedUser.role}` : `ID ${selectedManualAnomalia.assigned_to}`}`
                      : "Anomalia non ancora assegnata."}
                  </p>
                </div>

                <div className="rounded-2xl border border-gray-100 bg-white p-4">
                  <p className="text-sm font-semibold text-gray-900">Payload tecnico</p>
                  <pre className="mt-3 overflow-x-auto rounded-xl bg-[#0f172a] px-4 py-3 text-xs leading-6 text-slate-100">
                    {JSON.stringify(selectedManualAnomalia.dati_json ?? {}, null, 2)}
                  </pre>
                </div>
              </div>
            </div>
          </article>
        ) : null}

        {tab === "manuale" ? (
        <article className="panel-card">
          <div className="mb-4 flex items-start justify-between gap-4">
            <div>
            <p className="section-title">Registro completo anomalie</p>
            <p className="section-copy mt-1">
              Audit e fallback manuale. Usa questa tabella per i casi fuori workflow guidato o per chiudere rapidamente le anomalie già verificate.
            </p>
            </div>
            <div className="rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold text-gray-600">
              Pagina {overviewPageCount === 0 ? 0 : overviewPage} di {overviewPageCount}
            </div>
          </div>
          <div className="mb-4 grid gap-3 md:grid-cols-3">
            <label className="text-sm font-medium text-gray-700">
              Tipo
              <input
                className="form-control mt-1"
                value={filters.tipo}
                onChange={(event) => {
                  setOverviewPage(1);
                  setFilters((current) => ({ ...current, tipo: event.target.value }));
                }}
                placeholder="Es. VAL-02-cf_invalido"
              />
            </label>
            <label className="text-sm font-medium text-gray-700">
              Severità
              <select
                className="form-control mt-1"
                value={filters.severita}
                onChange={(event) => {
                  setOverviewPage(1);
                  setFilters((current) => ({ ...current, severita: event.target.value }));
                }}
              >
                <option value="">Tutte</option>
                <option value="error">Error</option>
                <option value="warning">Warning</option>
                <option value="info">Info</option>
              </select>
            </label>
            <label className="text-sm font-medium text-gray-700">
              Stato
              <select
                className="form-control mt-1"
                value={filters.status}
                onChange={(event) => {
                  setOverviewPage(1);
                  setFilters((current) => ({ ...current, status: event.target.value }));
                }}
              >
                <option value="">Tutti</option>
                <option value="aperta">Aperta</option>
                <option value="chiusa">Chiusa</option>
                <option value="ignora">Ignorata</option>
              </select>
            </label>
          </div>
          <div className="mb-4 grid gap-3 xl:grid-cols-[minmax(0,1fr)_240px_auto]">
            <label className="text-sm font-medium text-gray-700">
              Ricerca backend
              <input
                className="form-control mt-1"
                value={manualSearch}
                onChange={(event) => {
                  setOverviewPage(1);
                  setManualSearch(event.target.value);
                }}
                placeholder="ID, tipo, descrizione, note, utenza, particella"
              />
            </label>
            <label className="text-sm font-medium text-gray-700">
              Vista manuale
              <select
                className="form-control mt-1"
                value={manualFilterMode}
                onChange={(event) => setManualFilterMode(event.target.value as ManualQueueFilterMode)}
              >
                <option value="all">Tutte le righe</option>
                <option value="without_wizard">Solo senza wizard</option>
                <option value="unworked">Solo non lavorate</option>
              </select>
            </label>
            <div className="grid gap-3 md:grid-cols-2">
              <label className="text-sm font-medium text-gray-700">
                Ordina per
                <select
                  className="form-control mt-1"
                  value={manualSortBy}
                  onChange={(event) => {
                    setOverviewPage(1);
                    setManualSortBy(event.target.value as CatAnomaliaSortField);
                  }}
                >
                  <option value="created_at">Creazione</option>
                  <option value="updated_at">Aggiornamento</option>
                  <option value="tipo">Tipo</option>
                  <option value="status">Stato</option>
                  <option value="severita">Severita</option>
                  <option value="anno_campagna">Anno</option>
                </select>
              </label>
              <label className="text-sm font-medium text-gray-700">
                Direzione
                <select
                  className="form-control mt-1"
                  value={manualSortDir}
                  onChange={(event) => {
                    setOverviewPage(1);
                    setManualSortDir(event.target.value as SortDirection);
                  }}
                >
                  <option value="desc">Decrescente</option>
                  <option value="asc">Crescente</option>
                </select>
              </label>
            </div>
          </div>
          <div className="mb-4 flex flex-wrap items-center gap-3 text-sm text-gray-500">
            <span>{manualTableItems.length} righe visibili nella pagina corrente</span>
            <span>{total} righe totali dopo ricerca e ordinamento backend</span>
            {manualSearch.trim() ? <span>Ricerca attiva: {manualSearch.trim()}</span> : null}
            {manualFilterMode !== "all" ? <span>Filtro locale: {manualFilterMode}</span> : null}
            <div className="flex items-end">
              <button
                className="btn-secondary"
                type="button"
                onClick={() => {
                  setOverviewPage(1);
                  setManualSearch("");
                  setManualFilterMode("all");
                  setManualSortBy("created_at");
                  setManualSortDir("desc");
                }}
              >
                Reset registro
              </button>
            </div>
          </div>
          {busy && items.length === 0 ? (
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4 text-sm text-gray-500">Caricamento...</div>
          ) : manualTableItems.length === 0 ? (
            <EmptyState icon={SearchIcon} title="Nessuna anomalia" description="Non ci sono anomalie che corrispondono ai filtri correnti." />
          ) : (
            <DataTable
              data={manualTableItems}
              columns={columns}
              onRowClick={(row) => setSelectedManualAnomaliaId(row.id)}
              disableSorting
              pagination={{
                pageIndex: overviewPage - 1,
                pageCount: overviewPageCount,
                canPreviousPage: overviewPage > 1,
                canNextPage: overviewPage < overviewPageCount,
                onPreviousPage: () => setOverviewPage((current) => Math.max(1, current - 1)),
                onNextPage: () => setOverviewPage((current) => (current < overviewPageCount ? current + 1 : current)),
              }}
            />
          )}
        </article>
        ) : null}
      </div>
      <ElaborazioneWorkspaceModal
        open={Boolean(adeScanWorkspace)}
        href={adeScanWorkspace?.href ?? null}
        title={adeScanWorkspace?.title ?? "Dettaglio batch"}
        description={adeScanWorkspace?.description ?? null}
        onClose={() => setAdeScanWorkspace(null)}
      />
      <CatastoWorkspaceModal
        open={Boolean(manualAnomaliaWorkspace)}
        href={manualAnomaliaWorkspace?.href ?? null}
        title={manualAnomaliaWorkspace?.title ?? "Workspace particella"}
        description={manualAnomaliaWorkspace?.description ?? null}
        onClose={() => setManualAnomaliaWorkspace(null)}
      />
    </CatastoPage>
  );
}
