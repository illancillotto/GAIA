import { useMemo } from "react";
import type { CellContext, ColumnDef } from "@tanstack/react-table";

import { AnomaliaStatusBadge } from "@/components/catasto/AnomaliaStatusBadge";
import { AnomaliaStatusPill } from "@/components/catasto/AnomaliaStatusPill";
import { CatastoAnomaliaExplainer } from "@/components/catasto/catasto-anomalia-explainer";
import { describeCatastoAnomalia } from "@/lib/catasto-anomalie";
import type {
  CatAnomalia,
  CatParticellaConsorzio,
  CatParticellaHistory,
  CatUtenzaIrrigua,
} from "@/types/catasto";

import { formatHaFromMq, formatUtenzaPartita, getUtenzaSubjectLabel } from "./particella-detail-helpers";

type ParticellaHistoryCell = CellContext<CatParticellaHistory, unknown>;
type UtenzaCell = CellContext<CatUtenzaIrrigua, unknown>;
type AnomaliaCell = CellContext<CatAnomalia, unknown>;
type Occupancy = CatParticellaConsorzio["units"][number]["occupancies"][number];
type OccupancyCell = CellContext<Occupancy, unknown>;

type ColumnOptions = {
  capacitasLinkBusy: boolean;
  consorzio: CatParticellaConsorzio | null;
  subjectLookupBusyId: string | null;
  onOpenCertificato: (utenza: CatUtenzaIrrigua) => Promise<void>;
  onOpenSubject: (utenza: CatUtenzaIrrigua) => Promise<void>;
  onUpdateAnomalia: (id: string, status: string) => Promise<void>;
};

function historyColumns(): ColumnDef<CatParticellaHistory>[] {
  return [
    {
      header: "Validità",
      id: "valid",
      cell: ({ row }: ParticellaHistoryCell) => <span className="text-sm text-gray-700">{row.original.valid_from} → {row.original.valid_to}</span>,
    },
    { header: "Distretto", accessorKey: "num_distretto", cell: ({ row }: ParticellaHistoryCell) => <span className="text-sm text-gray-700">{row.original.num_distretto ?? "—"}</span> },
    {
      header: "Sup. catastale (ha)",
      id: "supCatastale",
      cell: ({ row }: ParticellaHistoryCell) => <span className="text-sm text-gray-700">{row.original.superficie_mq ? `${formatHaFromMq(row.original.superficie_mq)} ha` : "—"}</span>,
    },
    {
      header: "Sup. grafica (ha)",
      id: "supGrafica",
      cell: ({ row }: ParticellaHistoryCell) => <span className="text-sm text-gray-700">{row.original.superficie_grafica_mq ? `${formatHaFromMq(row.original.superficie_grafica_mq)} ha` : "—"}</span>,
    },
    { header: "Reason", accessorKey: "change_reason", cell: ({ row }: ParticellaHistoryCell) => <span className="text-sm text-gray-600">{row.original.change_reason ?? "—"}</span> },
  ];
}

function SubjectCell({ row, options }: { row: UtenzaCell["row"]; options: ColumnOptions }) {
  const utenza = row.original;
  const label = getUtenzaSubjectLabel(utenza);
  const canOpenSubject = Boolean(utenza.subject_id || utenza.codice_fiscale);
  const isBusy = options.subjectLookupBusyId === utenza.id;
  const blockClass = "w-full rounded-xl border border-[#D9E8DF] bg-[#F5FAF7] px-3 py-2 text-left transition hover:border-[#B7D2C1] hover:bg-[#EEF6F1] disabled:cursor-wait disabled:opacity-70";
  return (
    <div className="min-w-[240px]">
      {canOpenSubject ? (
        <button type="button" className={blockClass} disabled={isBusy} onClick={() => void options.onOpenSubject(utenza)}>
          <span className="block text-sm font-semibold tracking-[0.01em] text-[#1D4E35]">{isBusy ? "Apertura…" : utenza.codice_fiscale ?? "—"}</span>
          <span className="mt-1 block text-xs font-medium text-gray-600">{label ?? "Apri dettaglio soggetto"}</span>
        </button>
      ) : (
        <div className="rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-left">
          <div className="text-sm font-semibold tracking-[0.01em] text-gray-800">{utenza.codice_fiscale ?? "—"}</div>
          <div className="mt-1 text-xs font-medium text-gray-500">{label ?? "Nessun soggetto collegato"}</div>
        </div>
      )}
    </div>
  );
}

function utenzeColumns(options: ColumnOptions): ColumnDef<CatUtenzaIrrigua>[] {
  return [
    { header: "Anno", accessorKey: "anno_campagna", cell: ({ row }: UtenzaCell) => <span className="text-sm text-gray-700">{row.original.anno_campagna}</span> },
    {
      header: "CCO",
      accessorKey: "cco",
      cell: ({ row }: UtenzaCell) => {
        const partita = formatUtenzaPartita(options.consorzio, row.original);
        return <div className="space-y-0.5 text-sm text-gray-700"><div>{row.original.cco ?? "—"}</div><div className="text-xs text-gray-500">{partita ? `Partita ${partita}` : "Partita n/d"}</div></div>;
      },
    },
    { header: "CF / soggetto", accessorKey: "codice_fiscale", cell: ({ row }: UtenzaCell) => <SubjectCell row={row} options={options} /> },
    { header: "0648 (€)", id: "i0648", cell: ({ row }: UtenzaCell) => <span className="text-sm text-gray-700">{row.original.importo_0648 ?? "—"}</span> },
    { header: "0985 (€)", id: "i0985", cell: ({ row }: UtenzaCell) => <span className="text-sm text-gray-700">{row.original.importo_0985 ?? "—"}</span> },
    {
      header: "Azioni",
      id: "azioniUtenza",
      cell: ({ row }: UtenzaCell) => row.original.cco ? (
        <button type="button" className="flex items-center gap-1 text-xs font-medium text-[#1D4E35] hover:underline" disabled={options.capacitasLinkBusy} onClick={() => void options.onOpenCertificato(row.original)}>
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="h-3.5 w-3.5">
            <path d="M6.22 8.72a.75.75 0 0 0 1.06 1.06l5.22-5.22v1.69a.75.75 0 0 0 1.5 0v-3.5a.75.75 0 0 0-.75-.75h-3.5a.75.75 0 0 0 0 1.5h1.69L6.22 8.72Z" />
            <path d="M3.5 6.75c0-.69.56-1.25 1.25-1.25H7A.75.75 0 0 0 7 4H4.75A2.75 2.75 0 0 0 2 6.75v4.5A2.75 2.75 0 0 0 4.75 14h4.5A2.75 2.75 0 0 0 12 11.25V9a.75.75 0 0 0-1.5 0v2.25c0 .69-.56 1.25-1.25 1.25h-4.5c-.69 0-1.25-.56-1.25-1.25v-4.5Z" />
          </svg>
          {options.capacitasLinkBusy ? "Apertura…" : "Visualizza su Capacitas"}
        </button>
      ) : null,
    },
  ];
}

function anomalieColumns(onUpdate: ColumnOptions["onUpdateAnomalia"]): ColumnDef<CatAnomalia>[] {
  const action = (label: string, status: string, anomalia: CatAnomalia) => (
    <button type="button" className="btn-secondary !px-2 !py-1 text-xs" onClick={() => void onUpdate(anomalia.id, status)}>{label}</button>
  );
  return [
    { header: "Sev", accessorKey: "severita", cell: ({ row }: AnomaliaCell) => <AnomaliaStatusBadge severita={row.original.severita} /> },
    { header: "Tipo", accessorKey: "tipo", cell: ({ row }: AnomaliaCell) => <span className="text-sm font-medium text-gray-900">{row.original.tipo}</span> },
    { header: "Stato", accessorKey: "status", cell: ({ row }: AnomaliaCell) => <AnomaliaStatusPill status={row.original.status} /> },
    { header: "Descrizione", accessorKey: "descrizione", cell: ({ row }: AnomaliaCell) => <span className="text-sm text-gray-600">{row.original.descrizione ?? "—"}</span> },
    { header: "Perche", id: "motivo", cell: ({ row }: AnomaliaCell) => <div className="space-y-1.5"><span className="text-sm text-gray-600">{describeCatastoAnomalia(row.original)}</span><div><CatastoAnomaliaExplainer anomalia={row.original} /></div></div> },
    { header: "Azioni", id: "actions", cell: ({ row }: AnomaliaCell) => <div className="flex flex-wrap gap-2">{action("Chiudi", "chiusa", row.original)}{action("Ignora", "ignora", row.original)}{action("Riapri", "aperta", row.original)}</div> },
  ];
}

function occupancyColumns(): ColumnDef<Occupancy>[] {
  return [
    { header: "Relazione", accessorKey: "relationship_type", cell: ({ row }: OccupancyCell) => <span className="text-sm text-gray-700">{row.original.relationship_type}</span> },
    { header: "CCO", accessorKey: "cco", cell: ({ row }: OccupancyCell) => <span className="text-sm text-gray-700">{row.original.cco ?? "—"}</span> },
    { header: "Sorgente", accessorKey: "source_type", cell: ({ row }: OccupancyCell) => <span className="text-sm text-gray-700">{row.original.source_type}</span> },
    { header: "Periodo", id: "periodo", cell: ({ row }: OccupancyCell) => <span className="text-sm text-gray-700">{row.original.valid_from ?? "—"} → {row.original.valid_to ?? "—"}</span> },
    { header: "Stato", id: "current", cell: ({ row }: OccupancyCell) => <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${row.original.is_current ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-600"}`}>{row.original.is_current ? "Corrente" : "Storico"}</span> },
  ];
}

export function useParticellaDetailColumns(options: ColumnOptions) {
  const history = useMemo(historyColumns, []);
  const utenze = useMemo(() => utenzeColumns(options), [options]);
  const anomalie = useMemo(() => anomalieColumns(options.onUpdateAnomalia), [options.onUpdateAnomalia]);
  const occupancies = useMemo(occupancyColumns, []);
  return { anomalie, history, occupancies, utenze };
}
