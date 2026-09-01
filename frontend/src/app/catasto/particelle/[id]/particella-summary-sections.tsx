import type { ColumnDef } from "@tanstack/react-table";

import { DataTable } from "@/components/table/data-table";
import { AlertBanner } from "@/components/ui/alert-banner";
import { MetricCard } from "@/components/ui/metric-card";
import type { CatParticellaConsorzio, CatParticellaDetail } from "@/types/catasto";

import {
  formatDateTime,
  formatHaFromMq,
  formatHectares,
  formatIndice,
  renderResolutionLabel,
} from "./particella-detail-helpers";

type Occupancy = CatParticellaConsorzio["units"][number]["occupancies"][number];
type ConsorzioUnit = CatParticellaConsorzio["units"][number];
type ConsorzioOwner = ConsorzioUnit["intestatari_proprietari"][number];

function ParticellaHeader({ item, reference, syncBusy, onSync }: {
  item: CatParticellaDetail;
  reference: string;
  syncBusy: boolean;
  onSync: () => Promise<void>;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0">
        <p className="text-lg font-semibold text-gray-900">{reference}</p>
        <p className="mt-1 text-sm text-gray-500">
          Comune: <span className="font-medium text-gray-800">{item.nome_comune ?? item.cod_comune_capacitas}</span> · Distretto:{" "}
          <span className="font-medium text-gray-800">{item.num_distretto ?? "—"}</span>
          {item.fuori_distretto ? <span className="ml-2 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">Fuori distretto</span> : null}
        </p>
      </div>
      <div className="flex flex-col items-end gap-2">
        <button type="button" className="btn-primary" disabled={syncBusy} onClick={() => void onSync()}>
          {syncBusy ? "Sincronizzazione…" : "Sincronizza con Capacitas"}
        </button>
        <p className="text-xs text-gray-500">
          Ultimo aggiornamento: {formatDateTime(item.capacitas_last_sync_at)}
          {item.capacitas_last_sync_status ? ` · ${item.capacitas_last_sync_status}` : ""}
        </p>
      </div>
    </div>
  );
}

function SwappedCapacitasAlert({ item }: { item: CatParticellaDetail }) {
  const swapped = item.swapped_capacitas;
  if (!swapped) return null;
  return (
    <div className="mt-3 rounded-2xl border border-orange-200 bg-orange-50 px-4 py-3 text-sm text-orange-950">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-semibold">Comune Capacitas/Ruolo diverso dal comune GAIA</p>
          <p className="mt-1 text-orange-900">
            In GAIA la particella risulta su <span className="font-semibold">{item.nome_comune ?? item.codice_catastale ?? "Comune ND"}</span>; nel Ruolo/Capacitas sorgente risulta su{" "}
            <span className="font-semibold">{swapped.source_comune_nome ?? swapped.source_codice_catastale ?? "Comune ND"}</span>.
          </p>
          <p className="mt-1 text-xs text-orange-800">
            Rif. sorgente {swapped.source_foglio ?? "—"}/{swapped.source_particella ?? "—"}{swapped.source_subalterno ? `/${swapped.source_subalterno}` : ""}
            {swapped.anno_tributario_latest ? ` · anno ${swapped.anno_tributario_latest}` : ""} · {swapped.n_righe_ruolo} righe ruolo collegate.
          </p>
        </div>
        <span className="rounded-full bg-white px-2.5 py-1 text-xs font-semibold text-orange-700">Arborea/Terralba</span>
      </div>
    </div>
  );
}

function ParticellaMetrics({ item }: { item: CatParticellaDetail }) {
  return (
    <div className="mt-4 grid gap-3 md:grid-cols-4">
      <MetricCard label="Sup. catastale (ha)" value={item.superficie_mq ? `${formatHaFromMq(item.superficie_mq)} ha` : "—"} />
      <MetricCard label="Sup. grafica (ha)" value={item.superficie_grafica_mq ? `${formatHaFromMq(item.superficie_grafica_mq)} ha` : "—"} />
      <MetricCard label="Tariffa finale" value={item.indice_irriguo_finale != null ? `${formatIndice(item.indice_irriguo_finale)} €/ha` : "—"} sub={item.indice_irriguo_gruppo_coltura ?? "Coltura non classificata secondo delibera 28 febbraio 2025"} />
      <MetricCard label="IB territoriale" value={formatIndice(item.indice_irriguo_moltiplicatore)} sub={item.indice_irriguo_comune_arborea ? "Gruppo Arborea (Lotti Nord/Sud o fallback comune)" : "Gruppo territoriale del distretto"} />
      <MetricCard label="Coltura ruolo" value={item.indice_irriguo_coltura ?? "—"} sub={`Sup. irrigata ${formatHectares(item.indice_irriguo_sup_irrigata_ha)}`} />
      <MetricCard label="Costo stimato" value={item.indice_irriguo_importo_stimato != null ? `${formatIndice(item.indice_irriguo_importo_stimato)} €` : "—"} sub={item.indice_irriguo_euro_mc != null ? `${formatIndice(item.indice_irriguo_euro_mc)} €/mc` : "€/mc non applicabile"} />
      <MetricCard label="Anno indice" value={item.indice_irriguo_anno_riferimento ?? "—"} />
      <MetricCard label="Valid from" value={item.valid_from} />
      <MetricCard label="Source" value={item.source_type} />
      <MetricCard label="Current" value={item.is_current ? "Sì" : "No"} variant={item.is_current ? "success" : "warning"} />
    </div>
  );
}

export function ParticellaSummaryPanel({ item, isLoading, reference, syncBusy, syncMessage, onSync }: {
  item: CatParticellaDetail | null;
  isLoading: boolean;
  reference: string;
  syncBusy: boolean;
  syncMessage: string | null;
  onSync: () => Promise<void>;
}) {
  if (isLoading && !item) return <article className="panel-card"><div className="rounded-xl border border-gray-100 bg-gray-50 p-4 text-sm text-gray-500">Caricamento…</div></article>;
  if (!item) return <article className="panel-card"><AlertBanner variant="warning" title="Particella non trovata">Non risultano dati per l’ID richiesto.</AlertBanner></article>;
  return (
    <article className="panel-card">
      <ParticellaHeader item={item} reference={reference} syncBusy={syncBusy || isLoading} onSync={onSync} />
      {syncMessage ? <div className="mt-3 rounded-xl border border-emerald-100 bg-emerald-50 p-3 text-sm text-emerald-800">{syncMessage}</div> : null}
      {item.capacitas_last_sync_error ? <div className="mt-3 rounded-xl border border-amber-100 bg-amber-50 p-3 text-sm text-amber-800">{item.capacitas_last_sync_error}</div> : null}
      <SwappedCapacitasAlert item={item} />
      <ParticellaMetrics item={item} />
    </article>
  );
}

function OwnerCard({ owner }: { owner: ConsorzioOwner }) {
  return (
    <div className="rounded-lg border border-gray-100 bg-gray-50 px-3 py-2">
      <p className="text-sm font-medium text-gray-900">{owner.denominazione ?? "—"}{owner.deceduto ? <span className="ml-2 rounded-full bg-rose-50 px-2 py-0.5 text-xs font-medium text-rose-700">Deceduto</span> : null}</p>
      <p className="mt-1 text-xs text-gray-500">CF: <span className="font-medium text-gray-700">{owner.codice_fiscale ?? "—"}</span>{" · "}Titolo: <span className="font-medium text-gray-700">{owner.titoli ?? "—"}</span></p>
      <p className="mt-1 text-xs text-gray-500">Nascita: <span className="font-medium text-gray-700">{owner.data_nascita ?? "—"}</span>{owner.luogo_nascita ? ` · ${owner.luogo_nascita}` : ""}</p>
      <p className="mt-1 text-xs text-gray-500">Residenza: <span className="font-medium text-gray-700">{owner.residenza ?? owner.comune_residenza ?? "—"}</span></p>
      {owner.person ? (
        <div className="mt-2 rounded-md border border-emerald-100 bg-emerald-50 px-2 py-1.5">
          <p className="text-xs font-medium text-emerald-800">Anagrafica GAIA corrente</p>
          <p className="mt-1 text-xs text-emerald-700">{owner.person.cognome} {owner.person.nome} · {owner.person.codice_fiscale}</p>
          <p className="mt-1 text-xs text-emerald-700">Residenza corrente: {owner.person.indirizzo ?? owner.person.comune_residenza ?? "—"}</p>
          <p className="mt-1 text-xs text-emerald-700">Storico anagrafica: {owner.person_snapshots.length} snapshot</p>
        </div>
      ) : null}
    </div>
  );
}

function ConsorzioUnitHeader({ unit }: { unit: ConsorzioUnit }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <p className="text-sm font-semibold text-gray-900">Unità {unit.foglio ?? "—"}/{unit.particella ?? "—"}{unit.subalterno ? `/${unit.subalterno}` : ""}</p>
        <p className="mt-1 text-sm text-gray-600">Comune reale: <span className="font-medium text-gray-800">{unit.comune_label ?? unit.cod_comune_capacitas ?? "—"}</span>{" · "}Comune sorgente Capacitas: <span className="font-medium text-gray-800">{unit.source_comune_resolved_label ?? unit.source_comune_label ?? unit.source_cod_comune_capacitas ?? "—"}</span></p>
      </div>
      <div className="flex flex-wrap gap-2">
        <span className="rounded-full bg-[#eef5f1] px-2.5 py-1 text-xs font-medium text-[#1D4E35]">{renderResolutionLabel(unit.comune_resolution_mode)}</span>
        {unit.source_codice_catastale ? <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">Belfiore sorgente {unit.source_codice_catastale}</span> : null}
      </div>
    </div>
  );
}

function ConsorzioUnitMetrics({ unit }: { unit: ConsorzioUnit }) {
  return (
    <div className="mt-4 grid gap-3 md:grid-cols-4">
      <MetricCard label="Ultimo rilevamento" value={unit.source_last_seen ?? "—"} />
      <MetricCard label="Primo rilevamento" value={unit.source_first_seen ?? "—"} />
      <MetricCard label="Occupazioni" value={String(unit.occupancies.length)} />
      <MetricCard label="Attiva" value={unit.is_active ? "Sì" : "No"} variant={unit.is_active ? "success" : "warning"} />
    </div>
  );
}

function ConsorzioOwners({ owners }: { owners: ConsorzioOwner[] }) {
  return (
    <div className="mt-4 rounded-xl border border-white bg-white p-3">
      <div className="flex items-start justify-between gap-4"><div><p className="text-sm font-medium text-gray-900">Intestatari proprietari</p><p className="mt-1 text-sm text-gray-500">Proprietari / aventi titolo rilevati in Capacitas. Non coincidono necessariamente con chi usa o paga l’acqua nell’annualità.</p></div><p className="text-sm text-gray-500">{owners.length} righe</p></div>
      {owners.length === 0 ? <p className="mt-3 text-sm text-gray-500">Nessun intestatario strutturato ancora disponibile per questa unità.</p> : <div className="mt-3 space-y-2">{owners.map((owner) => <OwnerCard key={owner.id} owner={owner} />)}</div>}
    </div>
  );
}

function ConsorzioUnitCard({ unit, columns }: { unit: ConsorzioUnit; columns: ColumnDef<Occupancy>[] }) {
  return (
    <div className="rounded-2xl border border-[#e5ebe2] bg-[#fbfcfb] p-4">
      <ConsorzioUnitHeader unit={unit} />
      <ConsorzioUnitMetrics unit={unit} />
      <ConsorzioOwners owners={unit.intestatari_proprietari} />
      <div className="mt-4"><DataTable data={unit.occupancies} columns={columns} initialPageSize={6} emptyTitle="Nessuna occupancy" /></div>
    </div>
  );
}

export function ConsorzioPanel({ consorzio, isLoading, columns }: {
  consorzio: CatParticellaConsorzio | null;
  isLoading: boolean;
  columns: ColumnDef<Occupancy>[];
}) {
  return (
    <article className="panel-card">
      <div className="flex items-start justify-between gap-4"><div><p className="text-sm font-medium text-gray-900">Catasto consortile</p><p className="mt-1 text-sm text-gray-500">Vista operativa del Consorzio: distingue utilizzatore/pagatore annuale e intestatari proprietari rilevati in Capacitas.</p></div><p className="text-sm text-gray-500">{isLoading ? "Caricamento…" : `${consorzio?.units.length ?? 0} unità`}</p></div>
      {isLoading && !consorzio ? <div className="mt-4 rounded-xl border border-gray-100 bg-gray-50 p-4 text-sm text-gray-500">Caricamento…</div> : !consorzio || consorzio.units.length === 0 ? <div className="mt-4 rounded-xl border border-dashed border-gray-200 bg-gray-50 p-4 text-sm text-gray-500">Nessun dato consortile ancora consolidato per questa particella.</div> : <div className="mt-4 space-y-4">{consorzio.units.map((unit) => <ConsorzioUnitCard key={unit.id} unit={unit} columns={columns} />)}</div>}
    </article>
  );
}
