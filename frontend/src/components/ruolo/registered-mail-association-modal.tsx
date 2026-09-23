"use client";

import { useEffect, useState } from "react";

import { updateTributiRegisteredMailAssociation } from "@/lib/registered-mail-api";
import { listTributiAvvisi } from "@/lib/ruolo-api";
import type {
  RuoloTributiAvvisoListItemResponse,
  RuoloTributiRegisteredMailResponse,
} from "@/types/ruolo";

type RegisteredMailAssociationModalProps = {
  mail: RuoloTributiRegisteredMailResponse;
  token: string;
  onClose: () => void;
  onSaved: (mail: RuoloTributiRegisteredMailResponse) => void;
};

function candidateIds(mail: RuoloTributiRegisteredMailResponse): Set<string> {
  const value = mail.raw_payload_json?.candidate_avviso_ids;
  return new Set(Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : []);
}

function formatMoney(value: number | null): string {
  if (value == null) return "-";
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(value);
}

function toggleId(current: string[], id: string): string[] {
  if (current.includes(id)) return current.filter((value) => value !== id);
  return [...current, id];
}

function useAssociationModal({ mail, token, onClose, onSaved }: RegisteredMailAssociationModalProps) {
  const [query, setQuery] = useState(mail.recipient_name ?? mail.shipment_name ?? "");
  const [items, setItems] = useState<RuoloTributiAvvisoListItemResponse[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>(mail.avviso_ids?.length ? mail.avviso_ids : mail.avviso_id ? [mail.avviso_id] : []);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent): void {
      if (event.key === "Escape") onClose();
    }
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [onClose]);

  useEffect(() => {
    let cancelled = false;
    const handle = window.setTimeout(async () => {
      setLoading(true);
      try {
        const response = await listTributiAvvisi(token, {
          q: query.trim() || undefined,
          page: 1,
          page_size: 20,
        });
        if (!cancelled) {
          setItems(response.items);
          setError(null);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Errore ricerca avvisi");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 300);
    return () => {
      cancelled = true;
      window.clearTimeout(handle);
    };
  }, [query, token]);

  function toggleSelected(id: string): void {
    setSelectedIds((current) => toggleId(current, id));
  }

  async function saveAssociation(ids: string[]): Promise<void> {
    setSaving(true);
    setError(null);
    try {
      onSaved(await updateTributiRegisteredMailAssociation(token, mail.id, { avviso_ids: ids }));
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Errore aggiornamento associazione");
    } finally {
      setSaving(false);
    }
  }

  return {
    automaticCandidates: candidateIds(mail),
    error,
    items,
    loading,
    query,
    saveAssociation,
    saving,
    selectedIds,
    setQuery,
    toggleSelected,
  };
}

type AssociationModalState = ReturnType<typeof useAssociationModal>;

function AssociationHeader({
  mail,
  saving,
  onClose,
}: {
  mail: RuoloTributiRegisteredMailResponse;
  saving: boolean;
  onClose: () => void;
}) {
  return (
    <header className="border-b border-gray-100 bg-gradient-to-r from-[#eef5ec] via-white to-[#f5efe2] px-5 py-5 sm:px-7">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Matching manuale</p>
          <h2 id="registered-mail-association-title" className="mt-2 text-2xl font-semibold text-gray-900">
            Associa raccomandata ad avvisi
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            {mail.recipient_name ?? mail.shipment_name ?? "Destinatario non letto"} · invio {mail.source_shipment_id}
          </p>
        </div>
        <button className="btn-secondary" disabled={saving} onClick={onClose} type="button">
          Chiudi
        </button>
      </div>
    </header>
  );
}

function AssociationResult({
  item,
  isCandidate,
  isSelected,
  onSelect,
}: {
  item: RuoloTributiAvvisoListItemResponse;
  isCandidate: boolean;
  isSelected: boolean;
  onSelect: (id: string) => void;
}) {
  return (
    <button
      aria-checked={isSelected}
      className={`w-full rounded-2xl border p-4 text-left transition ${
        isSelected ? "border-[#1D4E35] bg-[#edf5ef] shadow-sm" : "border-gray-200 bg-white hover:border-[#9db3a3]"
      }`}
      onClick={() => onSelect(item.id)}
      role="checkbox"
      type="button"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-semibold text-gray-900">{item.display_name ?? item.nominativo_raw ?? "Nominativo assente"}</p>
          <p className="mt-1 text-xs text-gray-500">
            {item.codice_fiscale_raw ?? "CF assente"} · CNC {item.codice_cnc} · utenza {item.codice_utenza ?? "-"}
          </p>
        </div>
        <div className="text-right">
          <p className="text-sm font-semibold text-gray-800">{item.anno_tributario}</p>
          <p className="mt-1 text-xs text-gray-500">{formatMoney(item.importo_totale_euro)}</p>
        </div>
      </div>
      {isCandidate ? <span className="mt-3 inline-flex rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-800">Candidato automatico</span> : null}
    </button>
  );
}

function AssociationSearch({ state }: { state: AssociationModalState }) {
  return (
    <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-5 sm:px-7">
      <label className="block">
        <span className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Cerca avviso</span>
        <input
          autoFocus
          className="mt-2 w-full rounded-xl border border-gray-200 px-4 py-3 text-sm outline-none focus:border-[#6f8f78] focus:ring-2 focus:ring-[#dfeadf]"
          onChange={(event) => state.setQuery(event.target.value)}
          placeholder="Nominativo, codice fiscale, CNC o utenza"
          type="search"
          value={state.query}
        />
      </label>
      {state.error ? <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{state.error}</div> : null}
      {state.loading ? <p className="py-8 text-center text-sm text-gray-500">Ricerca avvisi...</p> : null}
      {!state.loading && state.items.length === 0 ? <p className="py-8 text-center text-sm text-gray-500">Nessun avviso trovato.</p> : null}
      {!state.loading && state.items.length > 0 ? (
        <div className="space-y-2" role="group" aria-label="Avvisi disponibili">
          {state.items.map((item) => (
            <AssociationResult
              isCandidate={state.automaticCandidates.has(item.id)}
              isSelected={state.selectedIds.includes(item.id)}
              item={item}
              key={item.id}
              onSelect={state.toggleSelected}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

function AssociationFooter({ mail, state }: { mail: RuoloTributiRegisteredMailResponse; state: AssociationModalState }) {
  return (
    <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-gray-100 bg-gray-50 px-5 py-4 sm:px-7">
      <button
        className="btn-secondary text-red-700"
        disabled={state.saving || mail.avviso_id == null}
        onClick={() => void state.saveAssociation([])}
        type="button"
      >
        Rimuovi associazione
      </button>
      <button
        className="btn-primary"
        disabled={state.saving || state.selectedIds.length === 0}
        onClick={() => void state.saveAssociation(state.selectedIds)}
        type="button"
      >
        {state.saving ? "Salvataggio..." : `Conferma ${state.selectedIds.length} avvisi`}
      </button>
    </footer>
  );
}

export function RegisteredMailAssociationModal(props: RegisteredMailAssociationModalProps) {
  const state = useAssociationModal(props);

  return (
    <div className="fixed inset-0 z-[80] flex items-end justify-center bg-black/45 p-0 backdrop-blur-sm sm:items-center sm:p-6">
      <section
        aria-labelledby="registered-mail-association-title"
        aria-modal="true"
        className="flex max-h-[94dvh] w-full max-w-4xl flex-col overflow-hidden rounded-t-[28px] border border-gray-200 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.3)] sm:rounded-[28px]"
        role="dialog"
      >
        <AssociationHeader mail={props.mail} onClose={props.onClose} saving={state.saving} />
        <AssociationSearch state={state} />
        <AssociationFooter mail={props.mail} state={state} />
      </section>
    </div>
  );
}
