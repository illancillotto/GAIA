"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { RiordinoStatusBadge } from "@/components/riordino/shared/status-badge";
import { createRiordinoBlock, listRiordinoBlocks, previewRiordinoBlockSelection } from "@/lib/riordino-api";
import type { RiordinoBlock, RiordinoBlockCreateInput, RiordinoBlockSelectionPreview } from "@/types/riordino";

type BlockFormState = {
  title: string;
  description: string;
  municipality: string;
  selection_type: RiordinoBlockCreateInput["selection_type"];
  codice_catastale: string;
  administrative_unit: string;
  foglio: string;
  grid_code: string;
  lot_code: string;
  ade_particella_ids: string;
  parcel_refs: string;
  coordinator_user_id: string;
  operator_user_ids: string;
};

const initialForm: BlockFormState = {
  title: "",
  description: "",
  municipality: "",
  selection_type: "municipality",
  codice_catastale: "",
  administrative_unit: "",
  foglio: "",
  grid_code: "",
  lot_code: "",
  ade_particella_ids: "",
  parcel_refs: "",
  coordinator_user_id: "",
  operator_user_ids: "",
};

function parseNumberList(value: string): number[] {
  return value
    .split(/[,\s]+/)
    .map((item) => Number.parseInt(item.trim(), 10))
    .filter((item) => Number.isFinite(item));
}

function parseIdList(value: string): string[] {
  return value
    .split(/[,\s]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseParcelRefs(value: string): RiordinoBlockCreateInput["parcel_refs"] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [codice_catastale, foglio, particella] = line.split(/[;,]/).map((item) => item.trim());
      return { codice_catastale, foglio, particella };
    })
    .filter((item) => item.codice_catastale && item.foglio && item.particella);
}

function buildPayload(form: BlockFormState): RiordinoBlockCreateInput {
  return {
    title: form.title.trim(),
    description: form.description.trim() || null,
    municipality: form.municipality.trim() || null,
    selection_type: form.selection_type,
    codice_catastale: form.codice_catastale.trim() || null,
    administrative_unit: form.administrative_unit.trim() || null,
    foglio: form.foglio.trim() || null,
    grid_code: form.grid_code.trim() || null,
    lot_code: form.lot_code.trim() || null,
    coordinator_user_id: Number.parseInt(form.coordinator_user_id, 10),
    operator_user_ids: parseNumberList(form.operator_user_ids),
    ade_particella_ids: parseIdList(form.ade_particella_ids),
    parcel_refs: parseParcelRefs(form.parcel_refs),
  };
}

export function RiordinoBlockList({ token, limit }: { token: string; limit?: number }) {
  const [items, setItems] = useState<RiordinoBlock[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [form, setForm] = useState<BlockFormState>(initialForm);
  const [preview, setPreview] = useState<RiordinoBlockSelectionPreview | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [formBusy, setFormBusy] = useState<"preview" | "create" | null>(null);

  useEffect(() => {
    async function loadData(): Promise<void> {
      try {
        const response = await listRiordinoBlocks(token, { per_page: String(limit ?? 100) });
        setItems(response.items);
        setLoadError(null);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore nel caricamento blocchi");
      }
    }

    void loadData();
  }, [limit, token]);

  async function runPreview(): Promise<void> {
    const payload = buildPayload(form);
    setFormBusy("preview");
    try {
      const response = await previewRiordinoBlockSelection(token, {
        selection_type: payload.selection_type,
        codice_catastale: payload.codice_catastale,
        administrative_unit: payload.administrative_unit,
        foglio: payload.foglio,
        ade_particella_ids: payload.ade_particella_ids,
        parcel_refs: payload.parcel_refs,
      });
      setPreview(response);
      setFormError(null);
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "Preview non riuscita");
    } finally {
      setFormBusy(null);
    }
  }

  async function submitBlock(): Promise<void> {
    const payload = buildPayload(form);
    if (!payload.title || !Number.isFinite(payload.coordinator_user_id)) {
      setFormError("Titolo e ID coordinatore sono obbligatori.");
      return;
    }
    setFormBusy("create");
    try {
      const created = await createRiordinoBlock(token, payload);
      setItems((current) => [created, ...current]);
      setForm(initialForm);
      setPreview(null);
      setFormError(null);
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "Creazione blocco non riuscita");
    } finally {
      setFormBusy(null);
    }
  }

  return (
    <article className="panel-card">
      <div className="mb-6 rounded-[28px] border border-[#d7e3d5] bg-[#fbf8ef] p-5">
        <div className="mb-4">
          <p className="section-title">Nuovo blocco operativo</p>
          <p className="section-copy">Crea blocchi da particelle AdE per comune, foglio/lotto, lista ID AdE o riferimenti catastali.</p>
        </div>
        {formError ? <p className="mb-3 rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">{formError}</p> : null}
        <div className="grid gap-3 lg:grid-cols-3">
          <label className="block text-sm">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-gray-500">Titolo</span>
            <input className="mt-1 w-full rounded-2xl border border-gray-200 px-3 py-2" value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} />
          </label>
          <label className="block text-sm">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-gray-500">Comune label</span>
            <input className="mt-1 w-full rounded-2xl border border-gray-200 px-3 py-2" value={form.municipality} onChange={(event) => setForm({ ...form, municipality: event.target.value })} />
          </label>
          <label className="block text-sm">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-gray-500">Criterio</span>
            <select className="mt-1 w-full rounded-2xl border border-gray-200 px-3 py-2" value={form.selection_type} onChange={(event) => setForm({ ...form, selection_type: event.target.value as BlockFormState["selection_type"] })}>
              <option value="municipality">Comune</option>
              <option value="lot">Foglio / lotto</option>
              <option value="parcel_list">Lista particelle</option>
              <option value="gis_selection">Selezione GIS</option>
            </select>
          </label>
          <label className="block text-sm">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-gray-500">Codice catastale</span>
            <input className="mt-1 w-full rounded-2xl border border-gray-200 px-3 py-2" value={form.codice_catastale} onChange={(event) => setForm({ ...form, codice_catastale: event.target.value })} />
          </label>
          <label className="block text-sm">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-gray-500">Administrative unit</span>
            <input className="mt-1 w-full rounded-2xl border border-gray-200 px-3 py-2" value={form.administrative_unit} onChange={(event) => setForm({ ...form, administrative_unit: event.target.value })} />
          </label>
          <label className="block text-sm">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-gray-500">Foglio</span>
            <input className="mt-1 w-full rounded-2xl border border-gray-200 px-3 py-2" value={form.foglio} onChange={(event) => setForm({ ...form, foglio: event.target.value })} />
          </label>
          <label className="block text-sm">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-gray-500">Maglia</span>
            <input className="mt-1 w-full rounded-2xl border border-gray-200 px-3 py-2" value={form.grid_code} onChange={(event) => setForm({ ...form, grid_code: event.target.value })} />
          </label>
          <label className="block text-sm">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-gray-500">Lotto</span>
            <input className="mt-1 w-full rounded-2xl border border-gray-200 px-3 py-2" value={form.lot_code} onChange={(event) => setForm({ ...form, lot_code: event.target.value })} />
          </label>
          <label className="block text-sm">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-gray-500">ID coordinatore</span>
            <input className="mt-1 w-full rounded-2xl border border-gray-200 px-3 py-2" value={form.coordinator_user_id} onChange={(event) => setForm({ ...form, coordinator_user_id: event.target.value })} />
          </label>
          <label className="block text-sm lg:col-span-2">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-gray-500">ID AdE particelle</span>
            <textarea className="mt-1 min-h-20 w-full rounded-2xl border border-gray-200 px-3 py-2" value={form.ade_particella_ids} onChange={(event) => setForm({ ...form, ade_particella_ids: event.target.value })} placeholder="UUID separati da virgola o spazio" />
          </label>
          <label className="block text-sm">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-gray-500">Operatori</span>
            <textarea className="mt-1 min-h-20 w-full rounded-2xl border border-gray-200 px-3 py-2" value={form.operator_user_ids} onChange={(event) => setForm({ ...form, operator_user_ids: event.target.value })} placeholder="ID separati da virgola" />
          </label>
          <label className="block text-sm lg:col-span-3">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-gray-500">Riferimenti particelle</span>
            <textarea className="mt-1 min-h-20 w-full rounded-2xl border border-gray-200 px-3 py-2" value={form.parcel_refs} onChange={(event) => setForm({ ...form, parcel_refs: event.target.value })} placeholder="Una riga per particella: H501;1;10" />
          </label>
          <label className="block text-sm lg:col-span-3">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-gray-500">Descrizione</span>
            <textarea className="mt-1 min-h-20 w-full rounded-2xl border border-gray-200 px-3 py-2" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} />
          </label>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <button type="button" className="btn-secondary disabled:opacity-50" disabled={formBusy !== null} onClick={() => void runPreview()}>
            {formBusy === "preview" ? "Preview..." : "Preview selezione"}
          </button>
          <button type="button" className="btn-primary disabled:opacity-50" disabled={formBusy !== null} onClick={() => void submitBlock()}>
            {formBusy === "create" ? "Creazione..." : "Crea blocco"}
          </button>
        </div>
        {preview ? (
          <div className="mt-4 grid gap-3 text-sm md:grid-cols-5">
            <div className="rounded-2xl bg-white px-3 py-2"><span className="text-gray-500">Particelle</span><p className="text-xl font-semibold">{preview.parcel_count}</p></div>
            <div className="rounded-2xl bg-white px-3 py-2"><span className="text-gray-500">Allineate</span><p className="text-xl font-semibold text-emerald-700">{preview.matched_count}</p></div>
            <div className="rounded-2xl bg-white px-3 py-2"><span className="text-gray-500">Disall.</span><p className="text-xl font-semibold text-amber-700">{preview.mismatch_count}</p></div>
            <div className="rounded-2xl bg-white px-3 py-2"><span className="text-gray-500">Ambigue</span><p className="text-xl font-semibold text-orange-700">{preview.ambiguous_count}</p></div>
            <div className="rounded-2xl bg-white px-3 py-2"><span className="text-gray-500">Chiavi mancanti</span><p className="text-xl font-semibold text-red-700">{preview.sister_missing_keys_count}</p></div>
          </div>
        ) : null}
      </div>
      <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="section-title">Blocchi di riordino</p>
          <p className="section-copy">Ogni blocco parte da snapshot AdE e guida confronto, visure Sister e lavorazioni operatori.</p>
        </div>
        <Link className="btn-secondary" href="/riordino/blocchi">
          Vedi tutti
        </Link>
      </div>
      {loadError ? <p className="mb-4 text-sm text-red-600">{loadError}</p> : null}
      {items.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-gray-200 bg-gray-50 px-5 py-8">
          <p className="text-sm font-medium text-gray-800">Nessun blocco disponibile.</p>
          <p className="mt-1 text-sm text-gray-500">Il super admin potrà creare blocchi da comune, lotto/maglia, lista particelle o selezione GIS.</p>
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {items.map((block) => (
            <Link
              key={block.id}
              href={`/riordino/blocchi/${block.id}`}
              className="group rounded-3xl border border-[#d7e3d5] bg-gradient-to-br from-[#fbf8ef] to-white p-5 transition hover:-translate-y-0.5 hover:border-[#9dbb95] hover:shadow-lg"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#617c55]">{block.code}</p>
                  <h3 className="mt-2 text-lg font-semibold text-gray-950 group-hover:text-[#1d4e35]">{block.title}</h3>
                  <p className="mt-1 text-sm text-gray-500">{block.municipality ?? "Comune non specificato"}</p>
                </div>
                <RiordinoStatusBadge value={block.status} />
              </div>
              <div className="mt-5 grid grid-cols-3 gap-3 text-sm">
                <div className="rounded-2xl bg-white/75 px-3 py-2">
                  <p className="text-xs text-gray-500">Particelle</p>
                  <p className="text-lg font-semibold text-gray-950">{block.parcel_count}</p>
                </div>
                <div className="rounded-2xl bg-white/75 px-3 py-2">
                  <p className="text-xs text-gray-500">Disall.</p>
                  <p className="text-lg font-semibold text-amber-700">{block.mismatch_count}</p>
                </div>
                <div className="rounded-2xl bg-white/75 px-3 py-2">
                  <p className="text-xs text-gray-500">Criterio</p>
                  <p className="truncate text-sm font-semibold text-gray-900">{block.selection_type}</p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </article>
  );
}
