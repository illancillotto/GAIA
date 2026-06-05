"use client";

import { useEffect, useMemo, useState } from "react";

import { FilterPillGroup } from "@/components/network/filter-pill-group";
import { NetworkModulePage } from "@/components/network/network-module-page";
import { NetworkTrackToggle } from "@/components/network/network-track-toggle";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { BellIcon, ServerIcon } from "@/components/ui/icons";
import {
  createNetworkTrackedSubject,
  listNetworkTrackedSubjects,
  updateNetworkTrackedSubject,
} from "@/lib/api";
import type { NetworkTrackedSubject } from "@/types/api";

const ENTITY_OPTIONS = [
  { value: "", label: "Tutti" },
  { value: "device", label: "Device" },
  { value: "ip", label: "IP" },
  { value: "domain", label: "Domini" },
  { value: "url", label: "URL" },
] as const;

function formatBytes(value: number) {
  if (!Number.isFinite(value) || value <= 0) {
    return "0 B";
  }
  const units = ["B", "KB", "MB", "GB", "TB"];
  let size = value;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  return `${size >= 100 || unitIndex === 0 ? size.toFixed(0) : size.toFixed(1)} ${units[unitIndex]}`;
}

function TrackingContent({ token }: { token: string }) {
  const [subjects, setSubjects] = useState<NetworkTrackedSubject[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [entityFilter, setEntityFilter] = useState("");
  const [includeInactive, setIncludeInactive] = useState(false);
  const [formType, setFormType] = useState<"ip" | "domain" | "url">("ip");
  const [formValue, setFormValue] = useState("");
  const [formLabel, setFormLabel] = useState("");
  const [formNotes, setFormNotes] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [busySubjectId, setBusySubjectId] = useState<number | null>(null);

  useEffect(() => {
    async function loadSubjects() {
      setIsLoading(true);
      try {
        const response = await listNetworkTrackedSubjects(token, {
          includeInactive,
          windowHours: 168,
          entityType: entityFilter || undefined,
          search: search || undefined,
        });
        setSubjects(response);
        setLoadError(null);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore caricamento tracking");
      } finally {
        setIsLoading(false);
      }
    }

    void loadSubjects();
  }, [entityFilter, includeInactive, search, token]);

  const summary = useMemo(() => {
    return {
      total: subjects.length,
      active: subjects.filter((item) => item.is_active).length,
      devices: subjects.filter((item) => item.entity_type === "device").length,
      endpoints: subjects.filter((item) => item.entity_type === "ip" || item.entity_type === "domain" || item.entity_type === "url").length,
    };
  }, [subjects]);

  async function handleCreate() {
    if (!formValue.trim()) {
      setSubmitError("Inserisci un valore da tracciare.");
      return;
    }
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const subject = await createNetworkTrackedSubject(token, {
        entity_type: formType,
        value: formValue.trim(),
        label: formLabel.trim() || null,
        notes: formNotes.trim() || null,
      });
      setSubjects((current) => [subject, ...current.filter((item) => item.id !== subject.id)]);
      setFormValue("");
      setFormLabel("");
      setFormNotes("");
      setIncludeInactive(false);
      setEntityFilter("");
      setSearch("");
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Errore creazione tracking");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleToggle(subject: NetworkTrackedSubject) {
    setBusySubjectId(subject.id);
    setLoadError(null);
    try {
      const updated = await updateNetworkTrackedSubject(token, subject.id, { is_active: !subject.is_active });
      setSubjects((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore aggiornamento tracking");
    } finally {
      setBusySubjectId(null);
    }
  }

  return (
    <div className="page-stack">
      <article className="panel-card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="section-title">Centro di tracciamento</p>
            <p className="section-copy">
              Monitora device interni e target di navigazione. I riepiloghi usano gli eventi Sophos delle ultime 168 ore.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard label="Totale" value={summary.total} />
            <MetricCard label="Attivi" value={summary.active} />
            <MetricCard label="Device" value={summary.devices} />
            <MetricCard label="IP / URL / domini" value={summary.endpoints} />
          </div>
        </div>
      </article>

      <article className="panel-card">
        <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
          <div>
            <p className="section-title">Aggiungi target</p>
            <p className="section-copy">Per i device usa il flag dalle viste operative; qui puoi censire IP, dominio o URL.</p>
          </div>
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <label className="block text-sm font-medium text-gray-700">
                Tipo
                <select className="form-control mt-1" value={formType} onChange={(event) => setFormType(event.target.value as "ip" | "domain" | "url")}>
                  <option value="ip">IP</option>
                  <option value="domain">Dominio</option>
                  <option value="url">URL</option>
                </select>
              </label>
              <label className="block text-sm font-medium text-gray-700">
                Valore
                <input
                  className="form-control mt-1"
                  value={formValue}
                  onChange={(event) => setFormValue(event.target.value)}
                  placeholder={formType === "ip" ? "es. 8.8.8.8" : formType === "domain" ? "es. example.org" : "https://example.org/path"}
                />
              </label>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="block text-sm font-medium text-gray-700">
                Label operativa
                <input className="form-control mt-1" value={formLabel} onChange={(event) => setFormLabel(event.target.value)} placeholder="Opzionale" />
              </label>
              <label className="block text-sm font-medium text-gray-700">
                Note
                <input className="form-control mt-1" value={formNotes} onChange={(event) => setFormNotes(event.target.value)} placeholder="Perche lo stai tracciando" />
              </label>
            </div>
            {submitError ? <p className="text-sm text-red-600">{submitError}</p> : null}
            <div className="flex justify-end">
              <button type="button" className="btn-primary" onClick={() => void handleCreate()} disabled={isSubmitting}>
                {isSubmitting ? "Salvataggio..." : "Aggiungi tracking"}
              </button>
            </div>
          </div>
        </div>
      </article>

      <article className="panel-card">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="section-title">Filtri elenco</p>
            <p className="section-copy">Riduci il perimetro ai target davvero operativi.</p>
          </div>
          <label className="inline-flex items-center gap-2 text-sm text-gray-600">
            <input type="checkbox" checked={includeInactive} onChange={(event) => setIncludeInactive(event.target.checked)} />
            Mostra anche disattivati
          </label>
        </div>
        <div className="mt-4 grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
          <input
            className="form-control"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Cerca per valore, label o note"
          />
          <FilterPillGroup options={ENTITY_OPTIONS} value={entityFilter} onChange={setEntityFilter} />
        </div>
        {loadError ? <p className="mt-4 text-sm text-red-600">{loadError}</p> : null}
      </article>

      {isLoading ? (
        <article className="panel-card text-sm text-gray-500">Caricamento tracking.</article>
      ) : subjects.length === 0 ? (
        <article className="panel-card">
          <EmptyState
            icon={BellIcon}
            title="Nessun target tracciato"
            description="Usa i flag nelle viste operative oppure registra qui un IP, dominio o URL."
          />
        </article>
      ) : (
        <section className="grid gap-4">
          {subjects.map((subject) => (
            <article key={subject.id} className="panel-card">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={subject.is_active ? "success" : "neutral"}>{subject.is_active ? "Attivo" : "Disattivo"}</Badge>
                    <Badge variant="info">{subject.entity_type.toUpperCase()}</Badge>
                  </div>
                  <p className="mt-3 text-lg font-semibold text-gray-900">{subject.resolved_label}</p>
                  <p className="mt-1 break-all text-sm text-gray-500">{subject.value}</p>
                  {subject.notes ? <p className="mt-2 text-sm text-gray-600">{subject.notes}</p> : null}
                  <p className="mt-2 text-xs text-gray-400">
                    Creato da {subject.created_by_username || "n/d"} · aggiornato {new Date(subject.updated_at).toLocaleString("it-IT")}
                  </p>
                </div>
                <NetworkTrackToggle
                  tracked={subject.is_active}
                  label={subject.is_active ? "Disattiva" : "Riattiva"}
                  busy={busySubjectId === subject.id}
                  onClick={() => void handleToggle(subject)}
                />
              </div>

              <div className="mt-5 grid gap-4 xl:grid-cols-4">
                <MetricCard label="Eventi" value={subject.activity_summary?.total_events ?? 0} />
                <MetricCard label="Allowed" value={subject.activity_summary?.allowed_events ?? 0} />
                <MetricCard label="Blocked" value={subject.activity_summary?.blocked_events ?? 0} />
                <MetricCard label="Ultimo visto" value={subject.activity_summary?.last_observed_at ? new Date(subject.activity_summary.last_observed_at).toLocaleString("it-IT") : "n/d"} />
              </div>

              <div className="mt-4 grid gap-4 xl:grid-cols-2">
                <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-4">
                  <p className="label-caption">Traffico aggregato</p>
                  <div className="mt-3 flex flex-wrap gap-3 text-sm text-gray-700">
                    <span>In {formatBytes(subject.activity_summary?.bytes_in ?? 0)}</span>
                    <span>Out {formatBytes(subject.activity_summary?.bytes_out ?? 0)}</span>
                  </div>
                </div>
                <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-4">
                  <p className="label-caption">Ultimi eventi</p>
                  <div className="mt-3 space-y-2">
                    {subject.activity_summary?.recent_events.slice(0, 3).map((event) => (
                      <div key={`${subject.id}-${event.id}`} className="rounded-xl border border-white bg-white px-3 py-3 text-sm text-gray-700">
                        <p className="font-medium text-gray-900">{event.event_type}</p>
                        <p className="mt-1 text-xs text-gray-500">
                          {event.src_ip || "src n/d"} → {event.dst_ip || "dst n/d"} · {event.protocol || "n/d"}
                        </p>
                        <p className="mt-1 text-xs text-gray-500">
                          Match {event.matched_on} · In {formatBytes(event.bytes_in)} · Out {formatBytes(event.bytes_out)}
                        </p>
                      </div>
                    ))}
                    {!subject.activity_summary?.recent_events.length ? (
                      <p className="text-sm text-gray-500">Nessun evento correlato nel periodo osservato.</p>
                    ) : null}
                  </div>
                </div>
              </div>
            </article>
          ))}
        </section>
      )}
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-4">
      <p className="label-caption">{label}</p>
      <p className="mt-2 text-xl font-semibold text-gray-900">{value}</p>
    </div>
  );
}

export default function NetworkTrackingPage() {
  return (
    <NetworkModulePage
      title="Tracking"
      description="Target monitorati nel modulo rete: device interni, IP, domini e URL osservati dal firewall Sophos."
      breadcrumb="Tracking"
    >
      {({ token }) => <TrackingContent token={token} />}
    </NetworkModulePage>
  );
}
