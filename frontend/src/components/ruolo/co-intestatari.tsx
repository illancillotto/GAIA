"use client";

import { useState } from "react";

import { RuoloWorkspaceModal } from "@/components/ruolo/workspace-modal";
import { searchUtenzeSubjects } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { AnagraficaSubjectListItem } from "@/types/api";

function normalizeName(name: string): string {
  return name.trim().replace(/\s+/g, " ").toLocaleUpperCase("it-IT");
}

function SubjectCandidates({ items, onSelect }: {
  items: AnagraficaSubjectListItem[];
  onSelect: (subject: AnagraficaSubjectListItem) => void;
}) {
  if (items.length === 0) return null;
  return (
    <div className="mt-3 space-y-2">
      <p>Seleziona il soggetto corretto:</p>
      {items.map((subject) => (
        <button
          key={subject.id}
          type="button"
          className="block text-left text-[#1D4E35] underline hover:text-[#173f2b]"
          onClick={() => onSelect(subject)}
        >
          {subject.display_name} · {subject.codice_fiscale || subject.partita_iva || "CF/P.IVA non disponibile"}
        </button>
      ))}
    </div>
  );
}

export function RuoloCoIntestatari({ names }: { names: string | null }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<AnagraficaSubjectListItem[]>([]);
  const [selected, setSelected] = useState<AnagraficaSubjectListItem | null>(null);
  const labels = [...new Set((names ?? "").split(/[;,\n]+/).map((name) => name.trim()).filter(Boolean))];

  async function openSubject(name: string): Promise<void> {
    setError(null);
    setCandidates([]);
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile. Accedi per aprire il soggetto.");
      return;
    }
    setBusy(true);
    try {
      const response = await searchUtenzeSubjects(token, name, 20);
      if (response.items.length === 0) {
        setError(`Nessun soggetto GAIA trovato per ${name}.`);
      } else if (response.total === 1 && normalizeName(response.items[0].display_name) === normalizeName(name)) {
        setSelected(response.items[0]);
      } else {
        setCandidates(response.items);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Errore ricerca soggetto");
    } finally {
      setBusy(false);
    }
  }

  if (labels.length === 0) return null;
  return (
    <div className="mb-4 rounded-2xl border border-[#e3e9e0] bg-[#fbfcfb] px-4 py-3 text-sm text-gray-600">
      <span className="font-semibold text-gray-900">Co-intestatari:</span>{" "}
      {labels.map((name, index) => (
        <span key={name}>
          {index > 0 ? "; " : null}
          <button
            type="button"
            className="text-[#1D4E35] underline decoration-[#1D4E35]/40 underline-offset-2 hover:decoration-[#1D4E35] disabled:opacity-60"
            disabled={busy}
            onClick={() => void openSubject(name)}
          >
            {name}
          </button>
        </span>
      ))}
      {busy ? <p role="status" className="mt-2">Ricerca soggetto...</p> : null}
      {error ? <p role="alert" className="mt-2 text-red-700">{error}</p> : null}
      <SubjectCandidates items={candidates} onSelect={setSelected} />
      <RuoloWorkspaceModal
        open={selected !== null}
        href={selected ? `/utenze/${selected.id}` : null}
        title="Dettaglio soggetto"
        description={selected?.display_name}
        onClose={() => setSelected(null)}
      />
    </div>
  );
}
