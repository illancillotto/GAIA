"use client";

import { useEffect, useState } from "react";

import { createPosteLot, listPosteCandidates } from "@/lib/ruolo-poste-dispatch-api";
import type { PosteDispatchCandidate, PosteDispatchLotDetail } from "@/types/ruolo-poste-dispatch";
import { dateTime, errorMessage } from "./labels";

const MAX_ITEMS = 50;

export function CandidatePicker({ token, onCreated }: { token: string; onCreated: (lot: PosteDispatchLotDetail) => void }) {
  const [query, setQuery] = useState("");
  const [candidates, setCandidates] = useState<PosteDispatchCandidate[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listPosteCandidates(token, query)
      .then((response) => { if (!cancelled) setCandidates(response.items); })
      .catch((err) => { if (!cancelled) setError(errorMessage(err, "Solleciti non caricati")); });
    return () => { cancelled = true; };
  }, [token, query]);

  function toggle(id: string) {
    setSelected((current) => current.includes(id) ? current.filter((value) => value !== id) : current.length < MAX_ITEMS ? [...current, id] : current);
  }

  async function create() {
    setBusy(true);
    setError(null);
    try {
      const lot = await createPosteLot(token, title, selected);
      setSelected([]);
      setTitle("");
      onCreated(lot);
    } catch (err) {
      setError(errorMessage(err, "Lotto non creato"));
    } finally {
      setBusy(false);
    }
  }

  return <section aria-label="Nuovo lotto Poste" className="space-y-3">
    <h2 className="text-lg font-semibold text-slate-900">Nuovo lotto</h2>
    <p className="text-sm text-slate-600">Solo solleciti generati in PDF e non già in un lotto attivo. Massimo {MAX_ITEMS} per lotto.</p>
    <input className="form-control w-full" aria-label="Cerca sollecito" placeholder="Nome, codice fiscale o lotto" value={query} onChange={(event) => setQuery(event.target.value)} />
    {error && <p role="alert" className="text-sm text-rose-800">{error}</p>}
    <ul className="max-h-80 space-y-1 overflow-y-auto">
      {candidates.length === 0 && <li className="text-sm text-slate-500">Nessun sollecito disponibile.</li>}
      {candidates.map((candidate) => <li key={candidate.batch_item_id}>
        <label className="flex items-start gap-2 rounded-xl border border-slate-200 p-2 text-sm">
          <input type="checkbox" checked={selected.includes(candidate.batch_item_id)} onChange={() => toggle(candidate.batch_item_id)} />
          <span><span className="font-semibold">{candidate.display_name || candidate.codice_fiscale}</span><br />
            <span className="text-xs text-slate-500">Avviso {candidate.notice_number || "-"} · {candidate.batch_title || "Lotto senza titolo"} · {dateTime(candidate.created_at)}</span></span>
        </label>
      </li>)}
    </ul>
    <input className="form-control w-full" aria-label="Titolo lotto" placeholder="Es. Solleciti 2021 Oristano" value={title} onChange={(event) => setTitle(event.target.value)} />
    <button type="button" className="btn-primary" disabled={busy || !title.trim() || selected.length === 0} onClick={() => void create()}>
      {busy ? "Creazione..." : `Crea lotto (${selected.length})`}
    </button>
  </section>;
}
