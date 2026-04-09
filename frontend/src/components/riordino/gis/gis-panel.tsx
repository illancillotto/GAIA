"use client";

import { useState } from "react";

import { EmptyState } from "@/components/ui/empty-state";
import { GridIcon } from "@/components/ui/icons";
import { formatRiordinoDate, formatRiordinoLabel } from "@/components/riordino/shared/format";
import { createRiordinoGisLink, updateRiordinoGisLink } from "@/lib/riordino-api";
import type { RiordinoGisLink } from "@/types/riordino";

type RiordinoGisPanelProps = {
  token: string;
  practiceId: string;
  links: RiordinoGisLink[];
  onUpdated: () => Promise<void>;
};

const SYNC_STATUSES = ["manual", "pending", "synced"];

export function RiordinoGisPanel({ token, practiceId, links, onUpdated }: RiordinoGisPanelProps) {
  const [layerName, setLayerName] = useState("");
  const [featureId, setFeatureId] = useState("");
  const [geometryRef, setGeometryRef] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [syncStatusById, setSyncStatusById] = useState<Record<string, string>>({});

  async function handleCreate() {
    setBusy(true);
    setError(null);
    try {
      await createRiordinoGisLink(token, practiceId, {
        layer_name: layerName,
        feature_id: featureId || null,
        geometry_ref: geometryRef || null,
        notes: notes || null,
      });
      setLayerName("");
      setFeatureId("");
      setGeometryRef("");
      setNotes("");
      await onUpdated();
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Impossibile creare il link GIS");
    } finally {
      setBusy(false);
    }
  }

  async function handleSyncUpdate(linkId: string) {
    setBusy(true);
    setError(null);
    try {
      await updateRiordinoGisLink(token, practiceId, linkId, {
        sync_status: syncStatusById[linkId] || "manual",
      });
      await onUpdated();
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Impossibile aggiornare il link GIS");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[1.4fr_0.9fr]">
      <article className="panel-card">
        <p className="section-title">GIS links</p>
        <div className="mt-4 space-y-3">
          {links.length === 0 ? (
            <EmptyState icon={GridIcon} title="Nessun link GIS" description="I riferimenti GIS manuali compariranno qui." />
          ) : (
            links.map((link) => (
              <div key={link.id} className="rounded-2xl border border-gray-100 px-4 py-4">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-semibold text-gray-900">{link.layer_name}</p>
                  <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">{formatRiordinoLabel(link.sync_status)}</span>
                </div>
                <p className="mt-1 text-sm text-gray-600">
                  Feature {link.feature_id || "—"} • Geometry {link.geometry_ref || "—"} • Sync {formatRiordinoDate(link.last_synced_at, true)}
                </p>
                {link.notes ? <p className="mt-2 text-sm text-gray-600">{link.notes}</p> : null}
                <div className="mt-3 flex flex-wrap gap-2">
                  <select
                    className="form-control max-w-[220px]"
                    value={syncStatusById[link.id] ?? link.sync_status}
                    onChange={(event) => setSyncStatusById((current) => ({ ...current, [link.id]: event.target.value }))}
                  >
                    {SYNC_STATUSES.map((status) => (
                      <option key={status} value={status}>{formatRiordinoLabel(status)}</option>
                    ))}
                  </select>
                  <button className="btn-secondary" disabled={busy} onClick={() => void handleSyncUpdate(link.id)} type="button">
                    Aggiorna sync
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </article>

      <article className="panel-card">
        <p className="section-title">Nuovo link GIS</p>
        <div className="mt-4 grid gap-3">
          <input className="form-control" placeholder="Layer name" value={layerName} onChange={(event) => setLayerName(event.target.value)} />
          <input className="form-control" placeholder="Feature ID" value={featureId} onChange={(event) => setFeatureId(event.target.value)} />
          <input className="form-control" placeholder="Geometry ref" value={geometryRef} onChange={(event) => setGeometryRef(event.target.value)} />
          <textarea className="form-control min-h-24" placeholder="Note" value={notes} onChange={(event) => setNotes(event.target.value)} />
          <button className="btn-primary" disabled={busy || !layerName.trim()} onClick={() => void handleCreate()} type="button">
            Crea link GIS
          </button>
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
        </div>
      </article>
    </div>
  );
}
