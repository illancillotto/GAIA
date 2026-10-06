import { type FormEvent } from "react";

import type { ControlCase } from "@/types/parcel-control";

type Props = { practice: ControlCase; busy: boolean; editable: boolean;
  save: (action: string, data: Record<string, unknown>, reason: string) => Promise<void> };

export function ParcelSpatialPanel({ practice, busy, editable, save }: Props) {
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const { reason, ...data } = Object.fromEntries(new FormData(event.currentTarget)) as Record<string, string>;
    await save("spatial_check", data, reason);
  }
  return <section aria-label="Confronto geometrico PostGIS" className="rounded-xl border bg-white p-4">
    <h3 className="font-semibold">Confronto geometrico PostGIS</h3>
    <p>Confini comunali, distretti e insediamenti sono verifiche distinte. Il risultato non inserisce o esclude automaticamente la particella.</p>
    {practice.evidence.filter(entry => entry.kind === "spatial_check").map(entry => <p key={entry.id}>
      Confronto geometrico · {entry.scope} · {entry.result} · versione {entry.version} · superficie particella {entry.parcel_area_m2 ?? "non verificabile"} m² · sovrapposizione {entry.intersection_area_m2 ?? "non verificabile"} m² · {entry.intersection_percent ?? "non verificabile"}%
    </p>)}
    {editable && <form onSubmit={submit} className="mt-3 grid gap-3 md:grid-cols-2">
      <p>Seleziona un layer poligonale pubblicato nel GIS. WMS e confini lineari non sono utilizzabili. La versione e la completezza della copertura devono essere verificate.</p>
      <label>Particella<select name="parcel_id" className="form-control"><option value={practice.parcel_id || ""}>{practice.current.label}</option>
        {practice.parcels.map(parcel => <option key={parcel.id} value={parcel.id}>{parcel.reference.foglio}/{parcel.reference.particella}</option>)}</select></label>
      <label>Ambito geometrico<select name="scope_kind" className="form-control"><option value="districts">Distretti irrigui</option><option value="municipality">Confine comunale</option><option value="settlements">Insediamenti — preliminare</option></select></label>
      <label>ID layer GIS<input name="layer_id" required className="form-control" /></label>
      <label>Colonna codice distretto<input name="district_column" defaultValue="num_distretto" className="form-control" placeholder="NUM_DIST per lo shapefile originale" /></label>
      <label>Campo identificativo del comune<input name="feature_column" className="form-control" /></label>
      <label>Valore identificativo del comune<input name="feature_value" className="form-control" /></label>
      <label>Versione della fonte<input name="source_version" required className="form-control" /></label>
      <label>Copertura verificata<input name="coverage" required className="form-control" /></label>
      <label>Motivazione confronto geometrico<input name="reason" minLength={3} required className="form-control" /></label>
      <button disabled={busy} className="btn-secondary">Calcola e salva confronto</button>
    </form>}
  </section>;
}
