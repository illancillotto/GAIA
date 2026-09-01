import type { ColumnDef } from "@tanstack/react-table";

import { AnomaliaStatusBadge } from "@/components/catasto/AnomaliaStatusBadge";
import { CatastoAnomaliaExplainer } from "@/components/catasto/catasto-anomalia-explainer";
import { DataTable } from "@/components/table/data-table";
import { UtenzeSubjectQuickViewDialog } from "@/components/utenze/utenze-subject-quick-view-dialog";
import { describeCatastoAnomalia } from "@/lib/catasto-anomalie";
import type { CatAnomalia, CatParticellaHistory, CatUtenzaIrrigua } from "@/types/catasto";

function isOpenAnomalia(anomalia: CatAnomalia): boolean {
  return anomalia.status === "aperta";
}

function selectedSubjectLabel(utenze: CatUtenzaIrrigua[], subjectId: string): string | null {
  for (const utenza of utenze) {
    if (utenza.subject_id === subjectId) return utenza.subject_display_name ?? null;
  }
  return null;
}

export function UtenzePanel({ anno, capacitasLinkError, columns, isLoading, subjectLookupError, utenze, onAnnoChange }: {
  anno: number;
  capacitasLinkError: string | null;
  columns: ColumnDef<CatUtenzaIrrigua>[];
  isLoading: boolean;
  subjectLookupError: string | null;
  utenze: CatUtenzaIrrigua[];
  onAnnoChange: (anno: number) => void;
}) {
  const currentYear = new Date().getFullYear();
  return (
    <article className="panel-card">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div><p className="text-sm font-medium text-gray-900">Utilizzatore / pagatore annualità</p><p className="mt-1 text-sm text-gray-500">Righe `cat_utenze_irrigue` per anno campagna: soggetto operativo che usa l’acqua o paga il ruolo.</p></div>
        <div>
          <p className="text-sm text-gray-500">Anno campagna</p>
          <select className="form-control mt-1 w-[160px]" value={String(anno)} onChange={(event) => onAnnoChange(Number(event.target.value))}>
            {[currentYear + 1, currentYear, currentYear - 1, currentYear - 2].map((year) => <option key={year} value={String(year)}>{year}</option>)}
          </select>
        </div>
      </div>
      {capacitasLinkError ? <div className="mt-3 rounded-xl border border-red-100 bg-red-50 p-3 text-sm text-red-800">{capacitasLinkError}</div> : null}
      {subjectLookupError ? <div className="mt-3 rounded-xl border border-amber-100 bg-amber-50 p-3 text-sm text-amber-800">{subjectLookupError}</div> : null}
      <div className="mt-4"><DataTable data={utenze} columns={columns} initialPageSize={8} emptyTitle={isLoading ? "Caricamento…" : "Nessuna utenza"} /></div>
    </article>
  );
}

function AnomalieExplanation({ anomalie }: { anomalie: CatAnomalia[] }) {
  if (anomalie.length === 0) return null;
  return (
    <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><p className="text-sm font-semibold text-rose-950">Perche questa particella ha anomalie ruolo</p><p className="mt-1 text-sm text-rose-800">Le anomalie derivano dalle righe ruolo/utenze collegate a questa particella nell&apos;anno selezionato.</p></div>
        <span className="rounded-full bg-white px-2.5 py-1 text-xs font-semibold text-rose-700">{anomalie.length} aperte</span>
      </div>
      <div className="mt-3 grid gap-2 md:grid-cols-2">
        {anomalie.slice(0, 6).map((anomalia) => (
          <div key={anomalia.id} className="rounded-xl border border-rose-100 bg-white/85 px-3 py-2">
            <div className="flex flex-wrap items-center gap-2"><span className="text-sm font-semibold text-gray-900">{anomalia.descrizione ?? anomalia.tipo}</span><AnomaliaStatusBadge severita={anomalia.severita} /></div>
            <p className="mt-1 text-sm text-gray-600">{describeCatastoAnomalia(anomalia)}</p>
            <div className="mt-2"><CatastoAnomaliaExplainer anomalia={anomalia} /></div>
            {anomalia.anno_campagna ? <p className="mt-1 text-xs font-medium text-rose-700">Anno ruolo {anomalia.anno_campagna}</p> : null}
          </div>
        ))}
      </div>
    </div>
  );
}

export function AnomaliePanel({ anomalie, columns, isLoading }: {
  anomalie: CatAnomalia[];
  columns: ColumnDef<CatAnomalia>[];
  isLoading: boolean;
}) {
  const aperte = anomalie.filter(isOpenAnomalia);
  return (
    <article className="panel-card">
      <div className="flex items-start justify-between gap-4"><div><p className="text-sm font-medium text-gray-900">Anomalie</p><p className="mt-1 text-sm text-gray-500">Anomalie collegate alle utenze della particella (per anno).</p></div><p className="text-sm text-gray-500">{isLoading ? "Caricamento…" : `${anomalie.length} righe`}</p></div>
      <AnomalieExplanation anomalie={aperte} />
      <div className="mt-4"><DataTable data={anomalie} columns={columns} initialPageSize={8} emptyTitle={isLoading ? "Caricamento…" : "Nessuna anomalia"} /></div>
    </article>
  );
}

export function HistoryPanel({ columns, history, isLoading }: {
  columns: ColumnDef<CatParticellaHistory>[];
  history: CatParticellaHistory[];
  isLoading: boolean;
}) {
  return (
    <article className="panel-card">
      <div className="flex items-start justify-between gap-4"><div><p className="text-sm font-medium text-gray-900">Storico</p><p className="mt-1 text-sm text-gray-500">Versioni precedenti della particella (SCD Type 2).</p></div><p className="text-sm text-gray-500">{isLoading ? "Caricamento…" : `${history.length} righe`}</p></div>
      <div className="mt-4"><DataTable data={history} columns={columns} initialPageSize={10} /></div>
    </article>
  );
}

export function SubjectQuickView({ selectedSubjectId, utenze, onClose }: {
  selectedSubjectId: string | null;
  utenze: CatUtenzaIrrigua[];
  onClose: () => void;
}) {
  if (!selectedSubjectId) return null;
  return <UtenzeSubjectQuickViewDialog subjectId={selectedSubjectId} subjectLabel={selectedSubjectLabel(utenze, selectedSubjectId)} onClose={onClose} />;
}
