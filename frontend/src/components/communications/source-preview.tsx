"use client";

import { useCallback, useEffect, useState } from "react";
import { loadSourcePreview, type SourceSnapshot } from "@/lib/communication-source-preview";
import { CommunicationPdfViewer } from "./pdf-viewer";

export function SourcePreview({ token, sourceId, onReady }: { token: string; sourceId: string; onReady: (sha256: string) => void }) {
  const [state, setState] = useState<{ snapshot: SourceSnapshot | null; error: string }>({ snapshot: null, error: "" });
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let disposed = false;
    const abort = new AbortController();
    setState({ snapshot: null, error: "" }); onReady("");
    loadSourcePreview(token, sourceId, abort.signal)
      .then((snapshot) => { if (!disposed) setState({ snapshot, error: "" }); })
      .catch((error: unknown) => { if (!disposed) setState({ snapshot: null, error: error instanceof Error ? error.message : "Anteprima PDF non disponibile" }); });
    return () => { disposed = true; abort.abort(); };
  }, [token, sourceId, retry, onReady]);
  const onRendered = useCallback((ok: boolean) => onReady(ok && state.snapshot ? state.snapshot.part.sha256 : ""), [onReady, state.snapshot]);
  const loadContent = useCallback(async () => ({ content: state.snapshot!.content.slice(0), reviewId: "" }), [state.snapshot]);
  return <section aria-label="Anteprima avviso selezionato" className="min-w-0 space-y-3 border-t pt-4">
    <h3 className="font-semibold">Anteprima PDF dell&apos;avviso</h3>
    <p className="text-xs text-slate-600">Controlla tutte le pagine. La creazione della bozza conserva questi stessi byte; l&apos;approvazione individuale è richiesta successivamente.</p>
    {state.error ? <><p role="alert">{state.error}</p><button className="btn-secondary" onClick={() => setRetry((value) => value + 1)}>Riprova anteprima</button></> : state.snapshot ?
      <CommunicationPdfViewer token={token} messageId="" version={1} part={state.snapshot.part} loadContent={loadContent} onRendered={onRendered} canReview={false} pixelBudget={64_000_000} /> : <p role="status">Caricamento PDF dell&apos;avviso...</p>}
  </section>;
}
