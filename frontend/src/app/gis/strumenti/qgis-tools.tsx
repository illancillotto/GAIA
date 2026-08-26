"use client";

import { useState } from "react";

import { downloadGisQgisProject, getGisOgcPoc } from "@/lib/api/gis";
import type { GisOgcPocResponse } from "@/types/gis";

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export function GisQgisTools({ token }: { token: string }) {
  const [busy, setBusy] = useState<"download" | "ogc" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [ogc, setOgc] = useState<GisOgcPocResponse | null>(null);

  async function downloadProject() {
    setBusy("download");
    setError(null);
    try {
      saveBlob(await downloadGisQgisProject(token), "gaia-gis-platform.qgz");
      setNotice("Progetto QGIS scaricato.");
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : "Download QGIS non riuscito");
    } finally {
      setBusy(null);
    }
  }

  async function inspectOgc() {
    setBusy("ogc");
    setError(null);
    try {
      setOgc(await getGisOgcPoc(token));
    } catch (ogcError) {
      setError(ogcError instanceof Error ? ogcError.message : "Piano OGC non disponibile");
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="rounded-[28px] border border-[#c9d6c8] bg-[#17231d] p-5 text-white shadow-xl sm:p-7">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#c6ddbd]">Solo utenti tecnici</p>
      <h3 className="mt-2 text-2xl font-semibold">QGIS Desktop e servizi OGC</h3>
      <p className="mt-3 max-w-3xl text-sm leading-6 text-[#dce8db]">Scarica un progetto già configurato. Il piano OGC è informativo e mantiene WMS/WFS in sola lettura.</p>
      <div className="mt-5 flex flex-col gap-3 sm:flex-row">
        <button className="btn-primary" type="button" disabled={busy === "download"} onClick={() => void downloadProject()}>{busy === "download" ? "Preparazione..." : "Scarica progetto QGIS"}</button>
        <button className="btn-secondary" type="button" disabled={busy === "ogc"} onClick={() => void inspectOgc()}>{busy === "ogc" ? "Verifica..." : "Verifica piano OGC"}</button>
      </div>
      {notice ? <p className="mt-4 rounded-xl bg-white/10 px-4 py-3 text-sm font-semibold" role="status">{notice}</p> : null}
      {error ? <p className="mt-4 rounded-xl bg-red-100 px-4 py-3 text-sm font-semibold text-red-800" role="alert">{error}</p> : null}
      {ogc ? (
        <div className="mt-5 grid gap-3 sm:grid-cols-3" role="status">
          <QgisFact label="Server consigliato" value={ogc.recommended_server} />
          <QgisFact label="Mappe pubblicabili" value={String(ogc.publishable_layer_count)} />
          <QgisFact label="Modalità" value="Sola lettura" />
        </div>
      ) : null}
    </section>
  );
}

function QgisFact({ label, value }: { label: string; value: string }) {
  return <div className="rounded-2xl border border-white/10 bg-white/10 p-4"><p className="text-xs uppercase tracking-[0.14em] text-[#bcd6b1]">{label}</p><p className="mt-2 font-semibold">{value}</p></div>;
}
