"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { getGisCatalogLayer } from "@/lib/api/gis";
import type { GisCatalogLayer } from "@/types/gis";

import { domainWorkspaceDestination } from "../catalog-essential";
import { GisLayerViewer } from "../layer-viewer";

function readableValue(value: string | number | null | undefined): string {
  return value == null || value === "" ? "Non disponibile" : String(value);
}

function LayerDetailFact({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-2xl border border-[#dce6dc] bg-white px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#526a59]">
        {label}
      </p>
      <p className="mt-2 break-words text-sm font-semibold text-gray-950">
        {value}
      </p>
    </div>
  );
}

export function GisLayerDetailWorkspace({
  token,
  layerId,
}: {
  token: string | null;
  layerId: string;
}) {
  const detail = useLayerDetail(token, layerId);
  const content = !token || detail.loading ? (
    <LayerDetailLoading />
  ) : detail.error || !detail.layer ? (
    <LayerDetailError message={detail.error ?? "Mappa non trovata"} />
  ) : (
    <LayerDetailContent token={token} layer={detail.layer} />
  );

  return (
    <div className="space-y-4">
      <Link className="btn-secondary w-fit shadow-sm" href="/gis/catalogo">
        <span aria-hidden="true">&larr;</span>
        Torna al catalogo
      </Link>
      {content}
    </div>
  );
}

function useLayerDetail(token: string | null, layerId: string) {
  const [layer, setLayer] = useState<GisCatalogLayer | null>(null);
  const [loading, setLoading] = useState(Boolean(token));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    void getGisCatalogLayer(token, layerId)
      .then((response) => {
        if (cancelled) return;
        setLayer(response);
      })
      .catch((loadError: unknown) => {
        if (cancelled) return;
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Dettaglio mappa non disponibile",
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [layerId, token]);

  return { layer, loading, error };
}

function LayerDetailLoading() {
  return (
    <p className="rounded-2xl border border-[#dce6dc] bg-white px-4 py-3 text-sm font-semibold text-[#1D4E35]" role="status">
      Caricamento dettaglio mappa...
    </p>
  );
}

function LayerDetailError({ message }: { message: string }) {
  return (
    <section className="rounded-2xl border border-red-200 bg-red-50 p-5" role="alert">
      <p className="font-semibold text-red-800">{message}</p>
    </section>
  );
}

function LayerDetailContent({ token, layer }: { token: string; layer: GisCatalogLayer }) {
  return (
    <div className="space-y-5">
      <LayerDetailHeader layer={layer} />
      <LayerDetailViewer token={token} layer={layer} />
      <LayerTechnicalDetails layer={layer} />
    </div>
  );
}

function LayerDetailHeader({ layer }: { layer: GisCatalogLayer }) {
  const accessDescription = layer.can_edit ? "proporre modifiche" : layer.can_annotate ? "aggiungere note" : "consultare";
  return (
    <section className="overflow-hidden rounded-[30px] border border-[#b9cdbd] bg-[radial-gradient(circle_at_top_right,_rgba(210,231,191,0.38),_transparent_38%),linear-gradient(135deg,_#16281c,_#29442e)] p-5 text-white shadow-xl sm:p-7">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#bcd6b1]">{layer.workspace} · {layer.is_active ? "Mappa attiva" : "Mappa non attiva"}</p>
          <h2 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">{layer.title}</h2>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-[#e7f0e4] sm:text-base">{layer.description || "Nessuna descrizione disponibile per questa mappa."}</p>
        </div>
        <span className="w-fit rounded-full bg-white/10 px-4 py-2 text-sm font-semibold">Puoi {accessDescription}</span>
      </div>
    </section>
  );
}

function LayerDetailViewer({ token, layer }: { token: string; layer: GisCatalogLayer }) {
  if (layer.source_type === "postgis" && Boolean(layer.geometry_type)) {
    return <GisLayerViewer token={token} layer={layer} />;
  }
  const destination = domainWorkspaceDestination(layer);
  return (
    <section className="rounded-[26px] border border-[#e6d9a8] bg-[#fff9e2] p-5">
      <h3 className="text-xl font-semibold text-[#564713]">Questo elemento non contiene una geometria</h3>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-[#6d5b1b]">È un registro operativo collegato al dominio. Apri il modulo responsabile per consultare i dati nel loro contesto.</p>
      {destination ? <Link className="btn-primary mt-4" href={destination.href}>{destination.label}</Link> : null}
    </section>
  );
}

function LayerTechnicalDetails({ layer }: { layer: GisCatalogLayer }) {
  return (
    <details className="rounded-[24px] border border-[#dce6dc] bg-[#f7faf7] p-5">
      <summary className="cursor-pointer text-sm font-semibold text-[#1D4E35]">Informazioni tecniche della mappa</summary>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <LayerDetailFact label="Sorgente" value={layer.official_source} />
        <LayerDetailFact label="Tipo" value={layer.source_type} />
        <LayerDetailFact label="Geometria" value={readableValue(layer.geometry_type)} />
        <LayerDetailFact label="Sistema coordinate" value={readableValue(layer.srid)} />
        <LayerDetailFact label="Tabella" value={readableValue(layer.postgis_table)} />
        <LayerDetailFact label="Campo identificativo" value={readableValue(layer.feature_id_column)} />
        <LayerDetailFact label="Tile Martin" value={readableValue(layer.martin_layer_id)} />
        <LayerDetailFact label="Dominio" value={readableValue(layer.domain_module)} />
      </div>
    </details>
  );
}
