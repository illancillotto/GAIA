"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";

import { CatastoPage } from "@/components/catasto/catasto-page";
import { AnomaliaStatusBadge } from "@/components/catasto/AnomaliaStatusBadge";
import { AnomaliaStatusPill } from "@/components/catasto/AnomaliaStatusPill";
import { DataTable } from "@/components/table/data-table";
import { TableFilters } from "@/components/table/table-filters";
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
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";
import type {
  CatAnomalia,
  CatAdeStatusScanCandidate,
  CatAdeStatusScanSummary,
  CatAnomaliaComuneWizardItem,
  CatAnomaliaCfWizardItem,
  CatAnomaliaParticellaWizardItem,
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

function currentYear(): number {
  return new Date().getFullYear();
}

function buildDefaultFilters(): FiltersState {
  return {
    tipo: "",
    severita: "",
    status: "aperta",
    anno: String(currentYear()),
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

export default function CatastoAnomaliePage() {
  const [filters, setFilters] = useState<FiltersState>(buildDefaultFilters());
  const [items, setItems] = useState<CatAnomalia[]>([]);
  const [total, setTotal] = useState(0);
  const [summaryBuckets, setSummaryBuckets] = useState<CatAnomaliaSummaryBucket[]>([]);
  const [summaryTotal, setSummaryTotal] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [wizardMode, setWizardMode] = useState<"cf" | "comune" | "particella" | null>("cf");
  const [cfItems, setCfItems] = useState<CatAnomaliaCfWizardItem[]>([]);
  const [cfTotal, setCfTotal] = useState(0);
  const [cfBusy, setCfBusy] = useState(false);
  const [cfDrafts, setCfDrafts] = useState<CfDraftState>({});
  const [cfError, setCfError] = useState<string | null>(null);
  const [cfMessage, setCfMessage] = useState<string | null>(null);
  const [applyingAnomaliaId, setApplyingAnomaliaId] = useState<string | null>(null);
  const [comuneItems, setComuneItems] = useState<CatAnomaliaComuneWizardItem[]>([]);
  const [comuneTotal, setComuneTotal] = useState(0);
  const [comuneBusy, setComuneBusy] = useState(false);
  const [comuneError, setComuneError] = useState<string | null>(null);
  const [comuneMessage, setComuneMessage] = useState<string | null>(null);
  const [applyingComuneAnomaliaId, setApplyingComuneAnomaliaId] = useState<string | null>(null);
  const [comuneDrafts, setComuneDrafts] = useState<ComuneDraftState>({});
  const [comuneBatchNote, setComuneBatchNote] = useState("Correzione comune batch da console anomalie");
  const [particellaItems, setParticellaItems] = useState<CatAnomaliaParticellaWizardItem[]>([]);
  const [particellaTotal, setParticellaTotal] = useState(0);
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
          page: 1,
          pageSize: 200,
        }),
        catastoGetAnomalieSummary(token, {
          status: filters.status || undefined,
          severita: filters.severita || undefined,
          anno: filters.anno ? Number(filters.anno) : undefined,
          distretto: filters.distretto || undefined,
        }),
      ]);
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
  }, [filters.anno, filters.distretto, filters.severita, filters.status, filters.tipo]);

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
        limit: 50,
      });
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
  }, [filters.anno, filters.distretto, wizardMode]);

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
        limit: 50,
      });
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
  }, [filters.anno, filters.distretto, wizardMode]);

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
        limit: 50,
      });
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
  }, [filters.anno, filters.distretto, wizardMode]);

  const loadAdeScan = useCallback(async (): Promise<void> => {
    const token = getStoredAccessToken();
    if (!token) {
      return;
    }

    setAdeScanBusy(true);
    try {
      const [summaryData, candidateData] = await Promise.all([
        catastoGetAdeStatusScanSummary(token),
        catastoGetAdeStatusScanCandidates(token, { limit: 8 }),
      ]);
      setAdeScanSummary(summaryData);
      setAdeScanCandidates(candidateData.items);
      setAdeScanError(null);
    } catch (loadError) {
      setAdeScanError(loadError instanceof Error ? loadError.message : "Errore caricamento scansione AdE");
    } finally {
      setAdeScanBusy(false);
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

  async function handleRunAdeScan(limit: number): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) {
      return;
    }

    setAdeScanBusy(true);
    setAdeScanError(null);
    setAdeScanMessage(null);
    try {
      const response = await catastoRunAdeStatusScan(token, { limit });
      setAdeScanMessage(
        response.created > 0
          ? `Batch scansione AdE creato: ${response.created} richieste in coda${response.skipped ? `, ${response.skipped} saltate` : ""}.`
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
              onClick={() => void handleUpdateStatus(row.original.id, "chiusa")}
            >
              Chiudi
            </button>
            <button
              type="button"
              className="btn-secondary !px-2 !py-1 text-xs"
              disabled={busy}
              onClick={() => void handleUpdateStatus(row.original.id, "ignora")}
            >
              Ignora
            </button>
            <button
              type="button"
              className="btn-secondary !px-2 !py-1 text-xs"
              disabled={busy}
              onClick={() => void handleUpdateStatus(row.original.id, "aperta")}
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
              <p className="section-title">Panoramica anomalie</p>
              <p className="section-copy mt-1">
                La pagina resta il punto di triage generale, ma apre workspace dedicati quando una famiglia di anomalie ha una correzione guidata disponibile.
              </p>
            </div>
            <Link className="text-sm font-medium text-[#1D4E35] underline underline-offset-2" href="/catasto/import">
              Import & report
            </Link>
          </div>

          <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {summaryBuckets.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-gray-200 bg-gray-50 px-4 py-5 text-sm text-gray-500 md:col-span-2 xl:col-span-4">
                Nessuna anomalia aggregata per i filtri correnti.
              </div>
            ) : (
              summaryBuckets.map((bucket) => (
                <button
                  key={bucket.tipo}
                  type="button"
                  onClick={() => {
                    setFilters((current) => ({ ...current, tipo: bucket.tipo }));
                    setWizardMode(resolveWizardMode(bucket.tipo));
                    setCfMessage(null);
                    setCfError(null);
                    setComuneMessage(null);
                    setComuneError(null);
                    setParticellaMessage(null);
                    setParticellaError(null);
                  }}
                  className="rounded-2xl border border-[#d9dfd6] bg-white p-4 text-left shadow-sm transition hover:border-[#1D4E35] hover:shadow-md"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">{bucket.tipo}</p>
                      <p className="mt-2 text-base font-semibold text-gray-900">{bucket.label}</p>
                    </div>
                    <AnomaliaStatusBadge severita={bucket.severita} />
                  </div>
                  <p className="mt-4 text-3xl font-semibold text-[#1D4E35]">{bucket.count}</p>
                  <p className="mt-2 text-sm text-gray-500">
                    {canOpenCfWizard(bucket.tipo)
                      ? "Apri wizard CF"
                      : canOpenComuneWizard(bucket.tipo)
                        ? "Apri wizard comune"
                      : canOpenParticellaWizard(bucket.tipo)
                        ? "Apri wizard particella"
                        : "Solo triage manuale per ora"}
                  </p>
                </button>
              ))
            )}
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-3 text-sm text-gray-500">
            <span>{busy ? "Aggiornamento in corso..." : `${summaryTotal} anomalie aggregate`}</span>
            <span>{busy ? "..." : `${items.length} righe caricate su ${total} totali`}</span>
          </div>
        </article>

        <article className="panel-card">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="section-title">Code di lavoro</p>
              <p className="section-copy mt-1">
                Vista operativa delle famiglie correggibili: ogni coda apre direttamente il workspace più adatto invece di costringere l&apos;operatore a partire dalla tabella completa.
              </p>
            </div>
            <div className="rounded-full bg-[#f4f1e8] px-3 py-1 text-sm font-medium text-[#7a5b1f]">
              {workQueues.filter((queue) => queue.available).length} code attive
            </div>
          </div>

          <div className="mt-5 grid gap-4 xl:grid-cols-2">
            {workQueues.map((queue) => (
              <div
                key={queue.id}
                className={`rounded-2xl border p-4 shadow-sm ${wizardMode === queue.mode ? "border-[#1D4E35] bg-[#f6faf6]" : "border-[#d9dfd6] bg-white"}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-gray-900">{queue.title}</p>
                    <p className="mt-2 text-sm text-gray-500">{queue.description}</p>
                  </div>
                  <AnomaliaStatusBadge severita={queue.severity} />
                </div>
                <div className="mt-4 flex items-end justify-between gap-4">
                  <div>
                    <p className="text-3xl font-semibold text-[#1D4E35]">{queue.count}</p>
                    <p className="mt-1 text-xs uppercase tracking-[0.16em] text-gray-400">
                      {queue.mode === wizardMode ? "workspace attivo" : queue.available ? "da lavorare" : "nessuna riga aperta"}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="btn-secondary"
                    disabled={!queue.available}
                    onClick={() => {
                      setFilters((current) => ({ ...current, tipo: queue.tipo ?? "" }));
                      setWizardMode(queue.mode);
                      setCfMessage(null);
                      setCfError(null);
                      setComuneMessage(null);
                      setComuneError(null);
                      setParticellaMessage(null);
                      setParticellaError(null);
                    }}
                  >
                    {queue.cta}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </article>

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
              <button className="btn-primary" type="button" disabled={adeScanBusy} onClick={() => void handleRunAdeScan(50)}>
                {adeScanBusy ? "Preparazione..." : "Scarica 50 visure storiche"}
              </button>
            </div>
          </div>

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
        </article>

        <article className="panel-card">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-gray-900">Filtri</p>
              <p className="mt-1 text-sm text-gray-500">
                I risultati tabellari restano limitati a max 200 righe; i workspace dedicati leggono solo la famiglia di anomalie che sanno correggere.
              </p>
            </div>
            <button
              className="btn-secondary"
              type="button"
              disabled={busy}
              onClick={() => {
                const next = buildDefaultFilters();
                setFilters(next);
                setWizardMode("cf");
                setCfMessage(null);
                setCfError(null);
                setComuneMessage(null);
                setComuneError(null);
                setParticellaMessage(null);
                setParticellaError(null);
              }}
            >
              Reset completo
            </button>
          </div>

          <div className="mt-4">
            <TableFilters>
              <label className="text-sm font-medium text-gray-700">
                Tipo
                <input
                  className="form-control mt-1"
                  value={filters.tipo}
                  onChange={(event) => setFilters((current) => ({ ...current, tipo: event.target.value }))}
                  placeholder="Es. VAL-02-cf_invalido"
                />
              </label>
              <label className="text-sm font-medium text-gray-700">
                Severità
                <select
                  className="form-control mt-1"
                  value={filters.severita}
                  onChange={(event) => setFilters((current) => ({ ...current, severita: event.target.value }))}
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
                  onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))}
                >
                  <option value="">Tutti</option>
                  <option value="aperta">Aperta</option>
                  <option value="chiusa">Chiusa</option>
                  <option value="ignora">Ignorata</option>
                </select>
              </label>
              <label className="text-sm font-medium text-gray-700">
                Distretto
                <input
                  className="form-control mt-1"
                  inputMode="numeric"
                  value={filters.distretto}
                  onChange={(event) => setFilters((current) => ({ ...current, distretto: event.target.value }))}
                  placeholder="Es. 10"
                />
              </label>
              <label className="text-sm font-medium text-gray-700">
                Anno
                <input
                  className="form-control mt-1"
                  inputMode="numeric"
                  value={filters.anno}
                  onChange={(event) => setFilters((current) => ({ ...current, anno: event.target.value }))}
                />
              </label>
            </TableFilters>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button className="btn-primary" type="button" disabled={busy} onClick={() => void loadOverview()}>
              {busy ? "Caricamento..." : "Applica filtri"}
            </button>
            <button
              className="btn-secondary"
              type="button"
              disabled={cfBusy || comuneBusy || particellaBusy}
              onClick={() => Promise.all([loadCfWizard(), loadComuneWizard(), loadParticellaWizard()])}
            >
              {cfBusy || comuneBusy || particellaBusy ? "Aggiornamento workspace..." : "Aggiorna workspace"}
            </button>
          </div>
        </article>

        <article className="panel-card">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="section-title">Wizard codice fiscale</p>
              <p className="section-copy mt-1">
                Primo workspace reale della console anomalie. Copre `VAL-02-cf_invalido` e `VAL-03-cf_mancante`: corregge il dato sull&apos;utenza e chiude le anomalie CF aperte collegate.
              </p>
            </div>
            <div className="rounded-full bg-[#eef5ef] px-3 py-1 text-sm font-medium text-[#1D4E35]">
              {cfBusy ? "Sincronizzazione..." : `${cfItems.length} righe su ${cfTotal}`}
            </div>
          </div>

          {cfError ? (
            <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{cfError}</div>
          ) : null}
          {cfMessage ? (
            <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{cfMessage}</div>
          ) : null}

          {wizardMode !== "cf" ? (
            <div className="mt-4 rounded-xl border border-dashed border-gray-200 bg-gray-50 px-4 py-5 text-sm text-gray-500">
              Nessun wizard attivo per il filtro selezionato. Seleziona una card `VAL-02` o `VAL-03` per aprire il workspace CF.
            </div>
          ) : cfBusy && cfItems.length === 0 ? (
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
            </div>
          )}
        </article>

        <article className="panel-card">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="section-title">Wizard comune invalido</p>
              <p className="section-copy mt-1">
                Workspace dedicato a `VAL-04-comune_invalido`: propone i comuni di riferimento `CatComune` usando codice Capacitas e nome comune importato, poi riallinea l&apos;utenza e chiude le anomalie collegate.
              </p>
            </div>
            <div className="rounded-full bg-[#eef5ef] px-3 py-1 text-sm font-medium text-[#1D4E35]">
              {comuneBusy ? "Sincronizzazione..." : `${comuneItems.length} righe su ${comuneTotal}`}
            </div>
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

          {wizardMode !== "comune" ? (
            <div className="mt-4 rounded-xl border border-dashed border-gray-200 bg-gray-50 px-4 py-5 text-sm text-gray-500">
              Nessun wizard comune attivo. Seleziona una card `VAL-04-comune_invalido` per aprire questo workspace.
            </div>
          ) : comuneBusy && comuneItems.length === 0 ? (
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
            </div>
          )}
        </article>

        <article className="panel-card">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="section-title">Wizard particella assente</p>
              <p className="section-copy mt-1">
                Workspace dedicato a `VAL-05-particella_assente`: propone le particelle correnti candidate in base a comune, sezione, foglio, particella e subalterno presenti sull&apos;utenza importata.
              </p>
            </div>
            <div className="rounded-full bg-[#eef5ef] px-3 py-1 text-sm font-medium text-[#1D4E35]">
              {particellaBusy ? "Sincronizzazione..." : `${particellaItems.length} righe su ${particellaTotal}`}
            </div>
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

          {wizardMode !== "particella" ? (
            <div className="mt-4 rounded-xl border border-dashed border-gray-200 bg-gray-50 px-4 py-5 text-sm text-gray-500">
              Nessun wizard particella attivo. Seleziona una card `VAL-05-particella_assente` per aprire questo workspace.
            </div>
          ) : particellaBusy && particellaItems.length === 0 ? (
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
            </div>
          )}
        </article>

        <article className="panel-card">
          <div className="mb-4">
            <p className="section-title">Registro completo anomalie</p>
            <p className="section-copy mt-1">
              Audit e fallback manuale. Le famiglie senza wizard dedicato continuano a essere gestite da qui.
            </p>
          </div>
          {busy && items.length === 0 ? (
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4 text-sm text-gray-500">Caricamento...</div>
          ) : items.length === 0 ? (
            <EmptyState icon={SearchIcon} title="Nessuna anomalia" description="Non ci sono anomalie che corrispondono ai filtri correnti." />
          ) : (
            <DataTable data={items} columns={columns} initialPageSize={12} />
          )}
        </article>
      </div>
    </CatastoPage>
  );
}
