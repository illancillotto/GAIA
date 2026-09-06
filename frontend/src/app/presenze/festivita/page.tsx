"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { EmptyState } from "@/components/ui/empty-state";
import { CalendarIcon } from "@/components/ui/icons";
import {
  bootstrapPresenzeHolidays,
  createPresenzeHoliday,
  deletePresenzeHoliday,
  listPresenzeHolidays,
  updatePresenzeHoliday,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { PresenzeHoliday } from "@/types/api";

type HolidayFormState = {
  holidayDate: string;
  label: string;
  companyCode: string;
  holidayKind: "ordinary" | "suppressed" | "working_override";
};

const EMPTY_FORM: HolidayFormState = {
  holidayDate: "",
  label: "",
  companyCode: "",
  holidayKind: "ordinary",
};

const HOLIDAY_EDITOR_COPY =
  "Usa il bootstrap per caricare il calendario base dell'anno e aggiungi eccezioni globali o per `company_code`.";
const HOLIDAY_EDITOR_EDIT_COPY =
  "I campi sotto sono compilati dalla voce selezionata. Salva o annulla per uscire dalla modifica.";

function currentYearValue(): string {
  return String(new Date().getFullYear());
}

function normalizeYear(rawValue: string): number {
  const parsed = Number(rawValue);
  return Number.isInteger(parsed) && parsed >= 2000 && parsed <= 2100 ? parsed : new Date().getFullYear();
}

function formatHolidayScope(item: PresenzeHoliday): string {
  return item.company_code?.trim() ? `Azienda ${item.company_code}` : "Globale";
}

function holidayKindLabel(value: PresenzeHoliday["holiday_kind"]): string {
  if (value === "suppressed") return "Festivita soppressa";
  if (value === "working_override") return "Override lavorativo";
  return "Festivita ordinaria";
}

function holidayFormFromItem(item: PresenzeHoliday): HolidayFormState {
  return {
    holidayDate: item.holiday_date.slice(0, 10),
    label: item.label,
    companyCode: item.company_code ?? "",
    holidayKind: item.holiday_kind,
  };
}

function holidayEditorTitle(isEditing: boolean): string {
  return isEditing ? "Modifica festivita" : "Calendario festivita";
}

function holidayEditorCopy(isEditing: boolean): string {
  return isEditing ? HOLIDAY_EDITOR_EDIT_COPY : HOLIDAY_EDITOR_COPY;
}

function holidayCardClassName(baseClassName: string, isEditing: boolean): string {
  return isEditing ? `${baseClassName} ring-2 ring-[#1D4E35] ring-offset-2` : baseClassName;
}

function holidayEntryMeta(item: PresenzeHoliday, suffix?: string): string {
  const base = `${formatHolidayScope(item)} · ${holidayKindLabel(item.holiday_kind)}`;
  return suffix ? `${base} · ${suffix}` : base;
}

function HolidayEntryCard(props: {
  item: PresenzeHoliday;
  cardClassName: string;
  metaClassName: string;
  metaSuffix?: string;
  isEditing: boolean;
  deleteBusy: boolean;
  onEdit: (item: PresenzeHoliday) => void;
  onDelete: (holidayId: number) => void;
}) {
  return (
    <div
      className={`rounded-2xl border px-4 py-3 ${holidayCardClassName(props.cardClassName, props.isEditing)}`}
      data-editing={props.isEditing ? "true" : undefined}
    >
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="font-medium text-gray-900">
            {props.item.holiday_date} · {props.item.label}
          </p>
          <p className={props.metaClassName}>{holidayEntryMeta(props.item, props.metaSuffix)}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="btn-secondary" type="button" onClick={() => props.onEdit(props.item)}>
            {props.isEditing ? "In modifica" : "Modifica"}
          </button>
          <button
            className="rounded-2xl border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-50"
            type="button"
            disabled={props.deleteBusy}
            onClick={() => props.onDelete(props.item.id)}
          >
            {props.deleteBusy ? "Eliminazione..." : "Elimina"}
          </button>
        </div>
      </div>
    </div>
  );
}

function HolidayKindColumn(props: {
  title: string;
  copy: string;
  loadingLabel: string;
  emptyTitle: string;
  emptyDescription: string;
  items: PresenzeHoliday[];
  cardClassName: string;
  metaClassName: string;
  metaSuffix?: string;
  editingId: number | null;
  busyDeleteId: number | null;
  loading: boolean;
  onEdit: (item: PresenzeHoliday) => void;
  onDelete: (holidayId: number) => void;
}) {
  return (
    <article className="panel-card">
      <div className="mb-4">
        <p className="section-title">{props.title}</p>
        <p className="section-copy">{props.copy}</p>
      </div>
      {props.loading ? (
        <p className="text-sm text-gray-500">{props.loadingLabel}</p>
      ) : props.items.length === 0 ? (
        <EmptyState icon={CalendarIcon} title={props.emptyTitle} description={props.emptyDescription} />
      ) : (
        <div className="space-y-3">
          {props.items.map((item) => (
            <HolidayEntryCard
              key={item.id}
              item={item}
              cardClassName={props.cardClassName}
              metaClassName={props.metaClassName}
              metaSuffix={props.metaSuffix}
              isEditing={props.editingId === item.id}
              deleteBusy={props.busyDeleteId === item.id}
              onEdit={props.onEdit}
              onDelete={props.onDelete}
            />
          ))}
        </div>
      )}
    </article>
  );
}

export default function PresenzeFestivitaPage() {
  const formCardRef = useRef<HTMLElement>(null);
  const dateInputRef = useRef<HTMLInputElement>(null);
  const [year, setYear] = useState(currentYearValue());
  const [holidays, setHolidays] = useState<PresenzeHoliday[]>([]);
  const [form, setForm] = useState<HolidayFormState>(EMPTY_FORM);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [bootstrapping, setBootstrapping] = useState(false);
  const [busyDeleteId, setBusyDeleteId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const loadHolidays = useCallback(async () => {
    const token = getStoredAccessToken();
    if (!token) return;
    setLoading(true);
    try {
      const items = await listPresenzeHolidays(token, normalizeYear(year));
      setHolidays(items);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento festivita giornaliere");
    } finally {
      setLoading(false);
    }
  }, [year]);

  useEffect(() => {
    void loadHolidays();
  }, [loadHolidays]);

  const festiveDays = useMemo(() => holidays.filter((item) => item.holiday_kind === "ordinary"), [holidays]);
  const suppressedDays = useMemo(() => holidays.filter((item) => item.holiday_kind === "suppressed"), [holidays]);
  const workingOverrideDays = useMemo(
    () => holidays.filter((item) => item.holiday_kind === "working_override"),
    [holidays],
  );

  function resetForm() {
    setForm(EMPTY_FORM);
    setEditingId(null);
  }

  function startEdit(item: PresenzeHoliday) {
    setEditingId(item.id);
    setForm(holidayFormFromItem(item));
    setError(null);
    setSuccess(null);
    formCardRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    dateInputRef.current?.focus();
  }

  async function handleSubmit() {
    const token = getStoredAccessToken();
    if (!token) return;
    if (!form.holidayDate || !form.label.trim()) {
      setError("Compila almeno data ed etichetta.");
      return;
    }

    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const payload = {
        holiday_date: form.holidayDate,
        label: form.label.trim(),
        company_code: form.companyCode.trim() || null,
        holiday_kind: form.holidayKind,
      };

      if (editingId == null) {
        await createPresenzeHoliday(token, payload);
        setSuccess(
          form.holidayKind === "suppressed"
            ? "Festivita soppressa aggiunta."
            : form.holidayKind === "working_override"
              ? "Override lavorativo aggiunto."
              : "Giornata festiva aggiunta.",
        );
      } else {
        await updatePresenzeHoliday(token, editingId, payload);
        setSuccess(
          form.holidayKind === "suppressed"
            ? "Festivita soppressa aggiornata."
            : form.holidayKind === "working_override"
              ? "Override lavorativo aggiornato."
              : "Giornata festiva aggiornata.",
        );
      }

      resetForm();
      await loadHolidays();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Errore salvataggio festivita");
    } finally {
      setSaving(false);
    }
  }

  async function handleBootstrap() {
    const token = getStoredAccessToken();
    if (!token) return;
    setBootstrapping(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await bootstrapPresenzeHolidays(token, normalizeYear(year));
      setSuccess(`Bootstrap completato: ${result.created} voci inserite o recuperate.`);
      await loadHolidays();
    } catch (bootstrapError) {
      setError(bootstrapError instanceof Error ? bootstrapError.message : "Errore bootstrap festivita");
    } finally {
      setBootstrapping(false);
    }
  }

  async function handleDelete(holidayId: number) {
    const token = getStoredAccessToken();
    if (!token) return;
    setBusyDeleteId(holidayId);
    setError(null);
    setSuccess(null);
    try {
      await deletePresenzeHoliday(token, holidayId);
      if (editingId === holidayId) {
        resetForm();
      }
      setSuccess("Voce eliminata.");
      await loadHolidays();
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Errore eliminazione festivita");
    } finally {
      setBusyDeleteId(null);
    }
  }

  const isEditing = editingId != null;

  return (
    <ProtectedPage
      title="Festivita giornaliere"
      description="Configura giornate festive e festivita soppresse o lavorative per la lettura cartellini e l'export."
      breadcrumb="Giornaliere"
      requiredModule="presenze"
    >
      <div className="space-y-6">
        {error ? <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
        {success ? <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div> : null}

        <article className="panel-card scroll-mt-24 space-y-5" id="festivita-editor" ref={formCardRef}>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="section-title">{holidayEditorTitle(isEditing)}</p>
              <p className="section-copy">{holidayEditorCopy(isEditing)}</p>
            </div>
            <div className="flex flex-wrap items-end gap-3">
              <label className="block text-sm font-medium text-gray-700">
                Anno
                <input className="form-control mt-1 w-32" value={year} onChange={(event) => setYear(event.target.value)} />
              </label>
              <button className="btn-secondary" type="button" disabled={bootstrapping} onClick={() => void handleBootstrap()}>
                {bootstrapping ? "Bootstrap..." : "Bootstrap anno"}
              </button>
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-4">
            <label className="block text-sm font-medium text-gray-700">
              Data
              <input
                className="form-control mt-1"
                type="date"
                value={form.holidayDate}
                onChange={(event) => setForm((current) => ({ ...current, holidayDate: event.target.value }))}
                ref={dateInputRef}
              />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Etichetta
              <input
                className="form-control mt-1"
                value={form.label}
                onChange={(event) => setForm((current) => ({ ...current, label: event.target.value }))}
                placeholder="Es. Santo Patrono"
              />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Company code
              <input
                className="form-control mt-1"
                value={form.companyCode}
                onChange={(event) => setForm((current) => ({ ...current, companyCode: event.target.value }))}
                placeholder="Vuoto = globale"
              />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Tipo giornata
              <select
                className="form-control mt-1"
                value={form.holidayKind}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    holidayKind: event.target.value as HolidayFormState["holidayKind"],
                  }))
                }
              >
                <option value="ordinary">Festivita ordinaria</option>
                <option value="suppressed">Festivita soppressa</option>
                <option value="working_override">Override lavorativo</option>
              </select>
            </label>
          </div>

          <div className="flex flex-wrap gap-3">
            <button className="btn-primary" type="button" disabled={saving} onClick={() => void handleSubmit()}>
              {saving ? "Salvataggio..." : isEditing ? "Salva modifica" : "Aggiungi voce"}
            </button>
            {isEditing ? (
              <button className="btn-secondary" type="button" onClick={resetForm}>
                Annulla modifica
              </button>
            ) : null}
          </div>
        </article>

        <div className="grid gap-6 xl:grid-cols-3">
          <HolidayKindColumn
            title="Giornate festive"
            copy="Date considerate non lavorative per calcolo e classificazione giornaliere."
            loadingLabel="Caricamento festivita..."
            emptyTitle="Nessuna festivita configurata"
            emptyDescription="Esegui il bootstrap dell'anno oppure inserisci una nuova giornata festiva."
            items={festiveDays}
            cardClassName="border-gray-100 bg-gray-50"
            metaClassName="text-xs text-gray-500"
            editingId={editingId}
            busyDeleteId={busyDeleteId}
            loading={loading}
            onEdit={startEdit}
            onDelete={handleDelete}
          />
          <HolidayKindColumn
            title="Festivita soppresse"
            copy="Giornate che restano lavorative ma maturano diritto al recupero."
            loadingLabel="Caricamento eccezioni..."
            emptyTitle="Nessuna festivita soppressa"
            emptyDescription="Aggiungi qui le festivita che restano lavorative ma danno diritto a un giorno di recupero."
            items={suppressedDays}
            cardClassName="border-amber-100 bg-amber-50/70"
            metaClassName="text-xs text-amber-700"
            metaSuffix="diritto a recupero"
            editingId={editingId}
            busyDeleteId={busyDeleteId}
            loading={loading}
            onEdit={startEdit}
            onDelete={handleDelete}
          />
          <HolidayKindColumn
            title="Override lavorativi"
            copy="Date che non devono essere trattate come festive, senza semantica di festivita soppressa."
            loadingLabel="Caricamento override..."
            emptyTitle="Nessun override lavorativo"
            emptyDescription="Usa questa categoria solo per eccezioni lavorative che non devono generare straordinario festivo o recupero da festivita soppressa."
            items={workingOverrideDays}
            cardClassName="border-slate-200 bg-slate-50"
            metaClassName="text-xs text-slate-600"
            editingId={editingId}
            busyDeleteId={busyDeleteId}
            loading={loading}
            onEdit={startEdit}
            onDelete={handleDelete}
          />
        </div>
      </div>
    </ProtectedPage>
  );
}
