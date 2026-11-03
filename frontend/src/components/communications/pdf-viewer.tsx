"use client";

import { useRef, useState, type UIEvent } from "react";
import { usePdfSnapshot, type PdfViewerProps } from "./use-pdf-snapshot";

export function CommunicationPdfViewer(props: PdfViewerProps) {
  const { part } = props;
  const root = useRef<HTMLDivElement>(null);
  const pages = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(1);
  const [current, setCurrent] = useState(1);
  const { resource, setResource } = usePdfSnapshot(props, pages, zoom);

  function navigate(page: number) {
    pages.current?.querySelector(`[data-page="${page}"]`)?.scrollIntoView({ block: "start" });
    setCurrent(page);
  }
  function trackPage(event: UIEvent<HTMLDivElement>) {
    const box = event.currentTarget;
    const top = box.getBoundingClientRect().top;
    const visible = Array.from(box.children).find((element) => element.getBoundingClientRect().bottom > top + 20) as HTMLElement | undefined;
    if (visible) setCurrent(Number(visible.dataset.page));
  }
  async function fullscreen() {
    try {
      if (!root.current?.requestFullscreen) throw new Error("unsupported");
      await root.current.requestFullscreen();
    } catch { setResource((state) => ({ ...state, error: "Schermo intero non disponibile" })); }
  }
  return <section ref={root} aria-label="Documento da verificare" className="min-w-0 space-y-3 rounded-2xl border bg-white p-3">
    <div className="flex flex-wrap items-center gap-2">
      <button className="btn-secondary" disabled={current <= 1} onClick={() => navigate(current - 1)}>Pagina precedente</button>
      <span aria-live="polite">{current} / {part.pages}</span>
      <button className="btn-secondary" disabled={current >= part.pages} onClick={() => navigate(current + 1)}>Pagina successiva</button>
      <button className="btn-secondary" aria-label="Riduci zoom" disabled={zoom <= 0.5} onClick={() => setZoom((value) => value - 0.25)}>−</button>
      <button className="btn-secondary" aria-label="Aumenta zoom" disabled={zoom >= 3} onClick={() => setZoom((value) => value + 0.25)}>+</button>
      <button className="btn-secondary" onClick={() => setZoom(1)}>Adatta alla larghezza</button>
      <button className="btn-secondary" onClick={() => void fullscreen()}>Schermo intero</button>
      {resource.url && <a className="btn-secondary" href={resource.url} target="_blank" rel="noreferrer">Apri PDF in nuova scheda</a>}
    </div>
    <p className="break-all text-xs text-slate-600">{part.filename} · {part.size} byte · v{part.version}<br />SHA-256: {part.sha256}</p>
    {resource.loading && <p role="status">Rendering di tutte le pagine...</p>}
    {resource.error && <p role="alert" className="text-rose-800">{resource.error}</p>}
    <div ref={pages} onScroll={trackPage} className="h-[70vh] min-h-80 space-y-4 overflow-auto bg-slate-100 p-2" />
    <p className="text-xs text-slate-600">La conferma di aver controllato il contenuto integrale è richiesta separatamente nella checklist.</p>
  </section>;
}
