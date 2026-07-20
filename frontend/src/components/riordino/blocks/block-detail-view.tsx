"use client";

import { useEffect, useState } from "react";

import { ParticellaGisDialog } from "@/components/catasto/gis/ParticellaGisDialog";
import { RiordinoStatusBadge } from "@/components/riordino/shared/status-badge";
import { catastoGetParticellaGeojson } from "@/lib/api/catasto";
import {
  completeRiordinoBlockSisterVisura,
  createRiordinoBlockPhase2Practice,
  exportRiordinoBlockSummary,
  getRiordinoBlock,
  getRiordinoBlockCoordinatorSummary,
  getRiordinoBlockWizard,
  requestRiordinoBlockSisterVisura,
  reviewRiordinoBlockParcel,
  syncRiordinoBlockSisterVisura,
  syncRiordinoBlockSisterVisure,
} from "@/lib/riordino-api";
import type { CatAnagraficaMatch, GeoJSONFeature } from "@/types/catasto";
import type {
  RiordinoBlockCoordinatorSummary,
  RiordinoBlockDetail,
  RiordinoBlockParcelSnapshot,
  RiordinoBlockWizard,
} from "@/types/riordino";

function extractLonLat(feature: GeoJSONFeature | null): { lon: number; lat: number } | null {
  const properties = feature?.properties ?? {};
  const lon = properties["centroid_lon"];
  const lat = properties["centroid_lat"];
  if (typeof lon === "number" && typeof lat === "number") return { lon, lat };
  return null;
}

function capacitasStatus(snapshot: RiordinoBlockParcelSnapshot): string {
  const status = snapshot.capacitas_payload_json?.["match_status"];
  return typeof status === "string" ? status : "not_checked";
}

function buildGisMatch(snapshot: RiordinoBlockParcelSnapshot): CatAnagraficaMatch | null {
  if (!snapshot.cat_particella_id || !snapshot.foglio || !snapshot.particella) return null;
  return {
    particella_id: snapshot.cat_particella_id,
    unit_id: null,
    comune_id: null,
    comune: snapshot.codice_catastale,
    cod_comune_capacitas: null,
    codice_catastale: snapshot.codice_catastale,
    foglio: snapshot.foglio,
    particella: snapshot.particella,
    subalterno: null,
    num_distretto: null,
    nome_distretto: null,
    superficie_mq: null,
    superficie_grafica_mq: null,
    utenza_latest: null,
    cert_com: null,
    cert_pvc: null,
    cert_fra: null,
    cert_ccs: null,
    stato_ruolo: null,
    stato_cnc: null,
    intestatari: [],
    anomalie_count: 0,
    anomalie_top: [],
    note: snapshot.cat_particella_match_reason,
  };
}

export function RiordinoBlockDetailView({ token, blockId }: { token: string; blockId: string }) {
  const [block, setBlock] = useState<RiordinoBlockDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedMatch, setSelectedMatch] = useState<CatAnagraficaMatch | null>(null);
  const [selectedGeojson, setSelectedGeojson] = useState<GeoJSONFeature | null>(null);
  const [wizard, setWizard] = useState<RiordinoBlockWizard | null>(null);
  const [coordinatorSummary, setCoordinatorSummary] = useState<RiordinoBlockCoordinatorSummary | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState<string | null>(null);
  const [gisError, setGisError] = useState<string | null>(null);

  useEffect(() => {
    void loadData();
  }, [blockId, token]);

  async function loadData(): Promise<void> {
    try {
      const [blockResponse, wizardResponse, summaryResponse] = await Promise.all([
        getRiordinoBlock(token, blockId),
        getRiordinoBlockWizard(token, blockId),
        getRiordinoBlockCoordinatorSummary(token, blockId).catch(() => null),
      ]);
      setBlock(blockResponse);
      setWizard(wizardResponse);
      setCoordinatorSummary(summaryResponse);
      setLoadError(null);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore nel caricamento blocco");
    }
  }

  async function openGis(snapshot: RiordinoBlockParcelSnapshot): Promise<void> {
    const match = buildGisMatch(snapshot);
    if (!match) return;
    try {
      const geojson = await catastoGetParticellaGeojson(token, match.particella_id);
      setSelectedMatch(match);
      setSelectedGeojson(geojson);
      setGisError(null);
    } catch (error) {
      setGisError(error instanceof Error ? error.message : "Geometria GIS non caricabile");
    }
  }

  async function runSnapshotAction(actionKey: string, action: () => Promise<void>): Promise<void> {
    setActionBusy(actionKey);
    try {
      await action();
      await loadData();
      setActionError(null);
      setActionMessage(null);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Operazione non riuscita");
    } finally {
      setActionBusy(null);
    }
  }

  async function reviewSnapshot(snapshot: RiordinoBlockParcelSnapshot, status: "aligned" | "mismatch" | "resolved"): Promise<void> {
    const defaultNote =
      status === "aligned" ? "Confronto AdE/Capacitas allineato" : status === "resolved" ? "Disallineamento risolto" : "Disallineamento da verificare";
    await runSnapshotAction(`review-${snapshot.id}-${status}`, async () => {
      await reviewRiordinoBlockParcel(token, blockId, snapshot.id, { status, notes: defaultNote });
    });
  }

  async function exportSummary(): Promise<void> {
    setActionBusy("export-summary");
    try {
      const blob = await exportRiordinoBlockSummary(token, blockId);
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${block?.code.toLowerCase() ?? "riordino-blocco"}-particelle.csv`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(url);
      setActionError(null);
      setActionMessage("Export CSV generato.");
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Export blocco non riuscito");
    } finally {
      setActionBusy(null);
    }
  }

  async function createPhase2Practice(): Promise<void> {
    const ownerRaw = window.prompt("ID owner pratica Fase 2", String(block?.coordinator_user_id ?? ""));
    if (!ownerRaw) return;
    const ownerUserId = Number.parseInt(ownerRaw, 10);
    if (!Number.isFinite(ownerUserId)) {
      setActionError("ID owner non valido.");
      return;
    }
    const title = window.prompt("Titolo pratica Fase 2", `Fase 2 - ${block?.code ?? "blocco"}`);
    setActionBusy("phase2-practice");
    try {
      const practice = await createRiordinoBlockPhase2Practice(token, blockId, {
        owner_user_id: ownerUserId,
        title: title || null,
      });
      await loadData();
      setActionError(null);
      setActionMessage(`Pratica Fase 2 creata: ${practice.code}`);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Creazione pratica Fase 2 non riuscita");
    } finally {
      setActionBusy(null);
    }
  }

  async function requestVisura(snapshot: RiordinoBlockParcelSnapshot): Promise<void> {
    await runSnapshotAction(`request-visura-${snapshot.id}`, async () => {
      await requestRiordinoBlockSisterVisura(token, blockId, snapshot.id, {
        notes: "Richiesta da workspace blocco riordino",
      });
    });
  }

  async function syncVisura(snapshot: RiordinoBlockParcelSnapshot): Promise<void> {
    await runSnapshotAction(`sync-visura-${snapshot.id}`, async () => {
      await syncRiordinoBlockSisterVisura(token, blockId, snapshot.id);
    });
  }

  async function syncBlockVisure(): Promise<void> {
    setActionBusy("sync-block-visure");
    try {
      const result = await syncRiordinoBlockSisterVisure(token, blockId);
      await loadData();
      setActionError(null);
      setActionMessage(
        `Sync SISTER: ${result.downloaded_count} scaricate, ${result.failed_count} fallite, ${result.requested_count} in corso, ${result.skipped_count} saltate.`,
      );
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Sync SISTER blocco non riuscita");
    } finally {
      setActionBusy(null);
    }
  }

  async function completeVisura(snapshot: RiordinoBlockParcelSnapshot): Promise<void> {
    const documentRef = window.prompt("Riferimento documento visura scaricata", snapshot.sister_visura_document_ref ?? "");
    if (!documentRef) return;
    await runSnapshotAction(`complete-visura-${snapshot.id}`, async () => {
      await completeRiordinoBlockSisterVisura(token, blockId, snapshot.id, { status: "downloaded", document_ref: documentRef });
    });
  }

  async function failVisura(snapshot: RiordinoBlockParcelSnapshot): Promise<void> {
    const errorMessage = window.prompt("Motivo fallimento visura Sister", snapshot.sister_visura_error ?? "Errore SISTER");
    if (!errorMessage) return;
    await runSnapshotAction(`fail-visura-${snapshot.id}`, async () => {
      await completeRiordinoBlockSisterVisura(token, blockId, snapshot.id, { status: "failed", error_message: errorMessage });
    });
  }

  if (loadError) {
    return <p className="rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">{loadError}</p>;
  }

  if (!block) {
    return <p className="text-sm text-gray-500">Caricamento blocco...</p>;
  }

  const operators = block.assignments.filter((assignment) => assignment.assignment_role === "operator" && assignment.is_active);

  return (
    <div className="page-stack">
      <section className="rounded-[32px] border border-[#d7e3d5] bg-gradient-to-br from-[#f7f3e7] via-white to-[#eef6ee] p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#617c55]">{block.code}</p>
            <h1 className="mt-2 text-2xl font-semibold text-gray-950">{block.title}</h1>
            <p className="mt-2 max-w-3xl text-sm text-gray-600">
              {block.description ?? "Blocco operativo per riordino fondiario catastale, generato da snapshot AdE."}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button type="button" className="btn-secondary disabled:opacity-50" disabled={actionBusy !== null} onClick={() => void exportSummary()}>
              {actionBusy === "export-summary" ? "Export..." : "Esporta CSV"}
            </button>
            <button type="button" className="btn-secondary disabled:opacity-50" disabled={actionBusy !== null} onClick={() => void syncBlockVisure()}>
              {actionBusy === "sync-block-visure" ? "Sync SISTER..." : "Sync SISTER blocco"}
            </button>
            <button type="button" className="btn-primary disabled:opacity-50" disabled={actionBusy !== null} onClick={() => void createPhase2Practice()}>
              {actionBusy === "phase2-practice" ? "Creo pratica..." : "Crea Fase 2"}
            </button>
            <RiordinoStatusBadge value={block.status} />
          </div>
        </div>
        <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-2xl bg-white/80 px-4 py-3">
            <p className="text-xs text-gray-500">Particelle AdE</p>
            <p className="text-2xl font-semibold text-gray-950">{block.parcel_count}</p>
          </div>
          <div className="rounded-2xl bg-white/80 px-4 py-3">
            <p className="text-xs text-gray-500">Disallineamenti</p>
            <p className="text-2xl font-semibold text-amber-700">{block.mismatch_count}</p>
          </div>
          <div className="rounded-2xl bg-white/80 px-4 py-3">
            <p className="text-xs text-gray-500">Coordinatore</p>
            <p className="text-2xl font-semibold text-gray-950">#{block.coordinator_user_id}</p>
          </div>
          <div className="rounded-2xl bg-white/80 px-4 py-3">
            <p className="text-xs text-gray-500">Operatori</p>
            <p className="text-2xl font-semibold text-gray-950">{operators.length}</p>
          </div>
        </div>
      </section>

      <article className="panel-card">
        <div className="mb-4">
          <p className="section-title">Coordinamento</p>
          <p className="section-copy">Vista sintetica per coordinatore: avanzamento task, stato operatori e ultime operazioni tracciate.</p>
        </div>
        {coordinatorSummary ? (
          <div className="space-y-5">
            <div className="grid gap-3 md:grid-cols-4">
              <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
                <p className="text-xs text-gray-500">Task completati</p>
                <p className="text-2xl font-semibold text-emerald-700">{coordinatorSummary.task_status_counts.done ?? 0}</p>
              </div>
              <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
                <p className="text-xs text-gray-500">Task bloccati</p>
                <p className="text-2xl font-semibold text-amber-700">{coordinatorSummary.task_status_counts.blocked ?? 0}</p>
              </div>
              <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
                <p className="text-xs text-gray-500">Visure scaricate</p>
                <p className="text-2xl font-semibold text-emerald-700">{coordinatorSummary.sister_status_counts.downloaded ?? 0}</p>
              </div>
              <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
                <p className="text-xs text-gray-500">Revisioni risolte</p>
                <p className="text-2xl font-semibold text-emerald-700">{coordinatorSummary.review_status_counts.resolved ?? 0}</p>
              </div>
            </div>
            <div className="overflow-hidden rounded-2xl border border-gray-200">
              <div className="grid grid-cols-[0.8fr_0.8fr_0.8fr_0.8fr_1fr] gap-3 border-b border-gray-200 bg-gray-50 px-4 py-3 text-xs font-semibold uppercase tracking-[0.14em] text-gray-500">
                <span>Utente</span>
                <span>Ruolo</span>
                <span>Revisioni</span>
                <span>Visure</span>
                <span>Ultima attività</span>
              </div>
              {coordinatorSummary.operators.map((operator) => (
                <div key={`${operator.user_id}-${operator.assignment_role}`} className="grid grid-cols-[0.8fr_0.8fr_0.8fr_0.8fr_1fr] gap-3 border-b border-gray-100 px-4 py-3 text-sm last:border-b-0">
                  <span className="font-medium text-gray-950">#{operator.user_id}</span>
                  <span>{operator.assignment_role}</span>
                  <span>{operator.reviewed_count}</span>
                  <span>{operator.sister_completed_count}/{operator.sister_requested_count}</span>
                  <span className="text-gray-500">{operator.last_activity_at ? new Date(operator.last_activity_at).toLocaleString("it-IT") : "—"}</span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-sm text-gray-500">Vista coordinatore disponibile solo per admin e coordinatore assegnato.</p>
        )}
      </article>

      <article className="panel-card">
        <div className="mb-4">
          <p className="section-title">Procedura guidata operatore</p>
          <p className="section-copy">Task derivati dagli snapshot: confronto AdE/Capacitas, richiesta visura Sister e risoluzione disallineamenti.</p>
        </div>
        {actionError ? <p className="mb-3 rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">{actionError}</p> : null}
        {actionMessage ? <p className="mb-3 rounded-xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{actionMessage}</p> : null}
        <div className="grid gap-3 lg:grid-cols-2">
          {(wizard?.tasks ?? []).map((task) => (
            <div key={task.code} className="rounded-2xl border border-gray-100 bg-white px-4 py-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">{task.phase} · {task.assignee_hint}</p>
                  <p className="mt-1 text-sm font-medium text-gray-950">{task.title}</p>
                  {task.blocking_reason ? <p className="mt-1 text-xs text-amber-700">{task.blocking_reason}</p> : null}
                </div>
                <RiordinoStatusBadge value={task.status} />
              </div>
            </div>
          ))}
          {wizard && wizard.tasks.length === 0 ? <p className="text-sm text-gray-500">Nessun task disponibile.</p> : null}
        </div>
      </article>

      <article className="panel-card">
        <div className="mb-4">
          <p className="section-title">Particelle del blocco</p>
          <p className="section-copy">Snapshot creato da Agenzia delle Entrate, confronto con Catasto consortile/Capacitas e stato visura Sister.</p>
        </div>
        {gisError ? <p className="mb-3 text-sm text-amber-700">{gisError}</p> : null}
        <div className="overflow-hidden rounded-2xl border border-gray-200">
          <div className="grid grid-cols-[1.2fr_0.8fr_0.8fr_0.8fr_0.8fr_auto] gap-3 border-b border-gray-200 bg-gray-50 px-4 py-3 text-xs font-semibold uppercase tracking-[0.14em] text-gray-500">
            <span>Particella AdE</span>
            <span>Catasto</span>
            <span>Capacitas</span>
            <span>Revisione</span>
            <span>Sister</span>
            <span>Azioni</span>
          </div>
          {block.parcel_snapshots.map((snapshot) => (
            <div key={snapshot.id} className="grid grid-cols-[1.2fr_0.8fr_0.8fr_0.8fr_0.8fr_auto] gap-3 border-b border-gray-100 px-4 py-3 text-sm last:border-b-0">
              <div>
                <p className="font-medium text-gray-950">
                  Fg.{snapshot.foglio ?? "—"} Part.{snapshot.particella ?? "—"}
                </p>
                <p className="mt-1 text-xs text-gray-500">{snapshot.national_cadastral_reference}</p>
              </div>
              <RiordinoStatusBadge value={snapshot.cat_particella_match_status} />
              <RiordinoStatusBadge value={capacitasStatus(snapshot)} />
              <RiordinoStatusBadge value={snapshot.operator_review_status} />
              <RiordinoStatusBadge value={snapshot.sister_visura_status} />
              <div className="flex flex-wrap justify-end gap-2">
                <button
                  type="button"
                  className="btn-secondary whitespace-nowrap disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={!snapshot.cat_particella_id || actionBusy !== null}
                  onClick={() => void openGis(snapshot)}
                >
                  Mappa
                </button>
                <button
                  type="button"
                  className="btn-secondary whitespace-nowrap disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={actionBusy !== null}
                  onClick={() => void reviewSnapshot(snapshot, "aligned")}
                >
                  Allinea
                </button>
                <button
                  type="button"
                  className="btn-secondary whitespace-nowrap disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={actionBusy !== null}
                  onClick={() => void reviewSnapshot(snapshot, snapshot.cat_particella_match_status === "matched" ? "resolved" : "mismatch")}
                >
                  {snapshot.cat_particella_match_status === "matched" ? "Risolvi" : "Disall."}
                </button>
                <button
                  type="button"
                  className="btn-secondary whitespace-nowrap disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={actionBusy !== null || !snapshot.foglio || !snapshot.particella}
                  onClick={() => void requestVisura(snapshot)}
                >
                  Richiedi
                </button>
                <button
                  type="button"
                  className="btn-secondary whitespace-nowrap disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={actionBusy !== null || snapshot.sister_visura_status === "not_requested"}
                  onClick={() => void syncVisura(snapshot)}
                >
                  Sync
                </button>
                <button
                  type="button"
                  className="btn-secondary whitespace-nowrap disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={actionBusy !== null}
                  onClick={() => void completeVisura(snapshot)}
                >
                  Scaricata
                </button>
                <button
                  type="button"
                  className="btn-secondary whitespace-nowrap disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={actionBusy !== null}
                  onClick={() => void failVisura(snapshot)}
                >
                  Fallita
                </button>
              </div>
            </div>
          ))}
        </div>
      </article>

      <article className="panel-card">
        <p className="section-title">Audit blocco</p>
        <div className="mt-4 space-y-3">
          {block.events.length === 0 ? (
            <p className="text-sm text-gray-500">Nessun evento disponibile.</p>
          ) : (
            block.events.map((event) => (
              <div key={event.id} className="rounded-xl border border-gray-100 px-4 py-3">
                <p className="text-sm font-medium text-gray-900">{event.event_type}</p>
                <p className="mt-1 text-xs text-gray-500">{new Date(event.created_at).toLocaleString("it-IT")}</p>
              </div>
            ))
          )}
        </div>
      </article>

      <ParticellaGisDialog
        open={Boolean(selectedMatch)}
        match={selectedMatch}
        geojson={selectedGeojson}
        centroid={extractLonLat(selectedGeojson)}
        onClose={() => {
          setSelectedMatch(null);
          setSelectedGeojson(null);
        }}
      />
    </div>
  );
}
