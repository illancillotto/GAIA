"use client";

import { useEffect, useState } from "react";
import { requestBlob } from "@/lib/api";

type BlobState = { loading: boolean; url: string | null; error: string | null };

export function useDocumentBlob(token: string, path: string, method: string) {
  const [request, setRequest] = useState(0);
  const [state, setState] = useState<BlobState>({ loading: false, url: null, error: null });
  useEffect(() => {
    if (request === 0) return;
    let cancelled = false;
    let objectUrl: string | null = null;
    setState({ loading: true, url: null, error: null });
    requestBlob(path, { method, headers: { Authorization: `Bearer ${token}` }, cache: "no-store" })
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setState({ loading: false, url: objectUrl, error: null });
      })
      .catch((error) => {
        if (!cancelled) setState({ loading: false, url: null, error: error instanceof Error ? error.message : "Documento non disponibile" });
      });
    return () => { cancelled = true; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [token, path, method, request]);
  return { ...state, request: () => setRequest((value) => value + 1) };
}

function PreviewContent({ token, batchId, itemId }: { token: string; batchId: string; itemId: string }) {
  const resource = useDocumentBlob(token, `/ruolo/tributi/solleciti/batches/${batchId}/items/${itemId}/preview`, "GET");
  return <div className="mt-3 space-y-3">
    <p className="text-sm text-amber-900">Copia di revisione marcata come bozza. I dati possono essere cambiati: la conferma e l&apos;export li ricontrollano.</p>
    <button type="button" className="btn-secondary" disabled={resource.loading} onClick={resource.request}>{resource.loading ? "Preparazione anteprima..." : "Carica anteprima PDF"}</button>
    {resource.error && <p role="alert" className="text-sm text-rose-800">{resource.error}</p>}
    {resource.url && <>
      <a className="btn-secondary" href={resource.url} target="_blank" rel="noreferrer">Apri bozza in una nuova scheda</a>
      <iframe title="Anteprima documento - BOZZA" src={resource.url} className="h-[65vh] min-h-80 w-full rounded-xl border border-slate-300" />
      <p className="text-xs text-slate-600">Se il visualizzatore non compare sul telefono, usa il collegamento sopra. Il PDF resta marcato anche se scaricato o stampato.</p>
    </>}
  </div>;
}

export function NoticePreview(props: { token: string; batchId: string; itemId: string; status: string }) {
  const [open, setOpen] = useState(false);
  if (!["draft", "confirmed"].includes(props.status)) return null;
  return <div className="mt-3 border-t border-slate-200 pt-3">
    <button type="button" className="btn-secondary" aria-expanded={open} onClick={() => setOpen(!open)}>{open ? "Chiudi anteprima" : "Esamina documento"}</button>
    {open && <PreviewContent {...props} />}
  </div>;
}

export function NoticeExport({ token, batchId, canEdit }: { token: string; batchId: string; canEdit: boolean }) {
  const resource = useDocumentBlob(token, `/ruolo/tributi/solleciti/batches/${batchId}/export`, "POST");
  return <section aria-label="Export definitivo" className="mt-6 space-y-3 border-t border-emerald-100 pt-5">
    <p className="text-sm text-emerald-800">Lotto confermato. L&apos;export definitivo contiene gli originali PDF o DOCX e il manifest. Non esegue spedizioni.</p>
    <p className="text-sm text-slate-600">Ogni preparazione ricontrolla i dati e viene registrata. Se il lotto risulta obsoleto occorre rigenerarlo. Un file gia scaricato non viene aggiornato automaticamente.</p>
    {canEdit && <button type="button" className="btn-primary" disabled={resource.loading} onClick={resource.request}>{resource.loading ? "Verifica e preparazione..." : "Prepara export definitivo"}</button>}
    {resource.error && <p role="alert" className="text-sm text-rose-800">{resource.error}</p>}
    {resource.url && <a className="btn-secondary" href={resource.url} download={`solleciti-${batchId}-v1.zip`}>Scarica ZIP definitivo</a>}
  </section>;
}
