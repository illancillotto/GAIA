"use client";

import { useEffect, useMemo, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import {
  ModuleWorkspaceHero,
  ModuleWorkspaceKpiRow,
  ModuleWorkspaceKpiTile,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import { EmptyState } from "@/components/ui/empty-state";
import { Badge } from "@/components/ui/badge";
import { DocumentIcon } from "@/components/ui/icons";
import { exportInazXlsm, listInazCollaborators, listInazDailyRecords } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { getInazCompanyLabel } from "@/lib/inaz-display";
import type { InazCollaborator, InazDailyRecord } from "@/types/api";

function currentMonthValue(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function shiftMonth(monthValue: string, delta: number): string {
  const [year, month] = monthValue.split("-").map(Number);
  const shifted = new Date(year, month - 1 + delta, 1);
  return `${shifted.getFullYear()}-${String(shifted.getMonth() + 1).padStart(2, "0")}`;
}

function formatMonthLabel(monthValue: string): string {
  return new Intl.DateTimeFormat("it-IT", { month: "long", year: "numeric" }).format(new Date(`${monthValue}-01T00:00:00`));
}

function monthBoundsFromValue(value: string): { start: string; end: string } {
  const [year, month] = value.split("-").map(Number);
  const end = new Date(year, month, 0).getDate();
  return {
    start: `${year}-${String(month).padStart(2, "0")}-01`,
    end: `${year}-${String(month).padStart(2, "0")}-${String(end).padStart(2, "0")}`,
  };
}

export default function InazExportPage() {
  const [collaborators, setCollaborators] = useState<InazCollaborator[]>([]);
  const [records, setRecords] = useState<InazDailyRecord[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [selectedMonth, setSelectedMonth] = useState(currentMonthValue());
  const [employeeKind, setEmployeeKind] = useState("AVVENTIZI");
  const [templatePath, setTemplatePath] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    listInazCollaborators(token, { page: 1, pageSize: 200 })
      .then((response) => setCollaborators(response.items))
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Errore caricamento collaboratori"))
      .finally(() => setIsLoading(false));
  }, []);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token || !selectedMonth) return;
    const bounds = monthBoundsFromValue(selectedMonth);
    setIsLoadingPreview(true);
    listInazDailyRecords(token, { dateFrom: bounds.start, dateTo: bounds.end, page: 1, pageSize: 200 })
      .then((response) => setRecords(response.items))
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Errore caricamento preview export"))
      .finally(() => setIsLoadingPreview(false));
  }, [selectedMonth]);

  const mappedCount = useMemo(() => collaborators.filter((item) => item.application_user_id != null).length, [collaborators]);
  const selectedCollaborators = useMemo(
    () => (selectedIds.length > 0 ? collaborators.filter((item) => selectedIds.includes(item.id)) : collaborators),
    [collaborators, selectedIds],
  );
  const selectedCollaboratorIds = useMemo(() => new Set(selectedCollaborators.map((item) => item.id)), [selectedCollaborators]);
  const scopedRecords = useMemo(
    () => records.filter((record) => selectedIds.length === 0 || selectedCollaboratorIds.has(record.collaborator_id)),
    [records, selectedIds, selectedCollaboratorIds],
  );
  const specialDayCount = useMemo(() => scopedRecords.filter((record) => record.special_day).length, [scopedRecords]);
  const detailDrivenCount = useMemo(
    () => scopedRecords.filter((record) => Object.keys(record.detail_day_totals).length > 0 || Object.keys(record.detail_day_summary).length > 0).length,
    [scopedRecords],
  );
  const previewCollaborators = useMemo(() => selectedCollaborators.slice(0, 6), [selectedCollaborators]);

  async function handleExport() {
    const token = getStoredAccessToken();
    if (!token) return;
    setIsExporting(true);
    setError(null);
    setSuccess(null);
    try {
      const { start } = monthBoundsFromValue(selectedMonth);
      const blob = await exportInazXlsm(token, {
        periodStart: start,
        collaboratorIds: selectedIds,
        employeeKind,
        templatePath: templatePath.trim() || undefined,
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `inaz_giornaliere_${selectedMonth}.xlsm`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setSuccess("Export XLSM generato e download avviato.");
    } catch (exportError) {
      setError(exportError instanceof Error ? exportError.message : "Errore export XLSM");
    } finally {
      setIsExporting(false);
    }
  }

  return (
    <ProtectedPage
      title="Export Inaz"
      description="Generazione file giornaliere XLSM."
      breadcrumb="Inaz"
      requiredModule="inaz"
      requiredRoles={["admin", "super_admin"]}
    >
      <div className="space-y-8">
        <ModuleWorkspaceHero
          badge={<>Export giornaliere</>}
          title="Genera il file XLSM dalle giornaliere Inaz persistite in GAIA."
          description="Seleziona il mese, limita l'export a uno o piu collaboratori e, se serve, indica un template `.xlsm` alternativo. Il backend preserva le macro del file sorgente."
          actions={
            <>
              <ModuleWorkspaceNoticeCard
                title={templatePath.trim() ? "Template personalizzato" : "Template di default"}
                description={templatePath.trim() || "Verrà usato il template standard configurato lato backend."}
                tone="info"
              />
              <ModuleWorkspaceNoticeCard
                title={selectedIds.length > 0 ? "Export filtrato" : "Export completo"}
                description={
                  selectedIds.length > 0
                    ? `${selectedIds.length} collaboratori selezionati per il download.`
                    : "Nessun filtro collaboratore: il backend includera tutti i collaboratori con giornaliere nel mese scelto."
                }
                tone={selectedIds.length > 0 ? "warning" : "success"}
              />
            </>
          }
        >
          <ModuleWorkspaceKpiRow>
            <ModuleWorkspaceKpiTile label="Collaboratori" value={collaborators.length} hint="Dataset disponibile" />
            <ModuleWorkspaceKpiTile label="Mappati GAIA" value={mappedCount} hint="Collegati a application_users" variant="emerald" />
            <ModuleWorkspaceKpiTile label="Selezionati" value={selectedIds.length || "Tutti"} hint="Ambito export" />
            <ModuleWorkspaceKpiTile label="Righe mese" value={scopedRecords.length} hint="Giornaliere incluse" />
          </ModuleWorkspaceKpiRow>
        </ModuleWorkspaceHero>

        {error ? <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
        {success ? <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div> : null}

        <section className="panel-card space-y-5">
          <div>
            <p className="section-title">Parametri export</p>
            <p className="section-copy">Configura il file da generare e avvia il download direttamente dal backend.</p>
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <label className="block text-sm font-medium text-gray-700">
              <span>Mese di riferimento</span>
              <div className="mt-1 flex items-center gap-2">
                <button
                  type="button"
                  className="btn-secondary px-3"
                  aria-label="Mese precedente"
                  onClick={() => setSelectedMonth((current) => shiftMonth(current, -1))}
                >
                  ‹
                </button>
                <input className="form-control flex-1" type="month" value={selectedMonth} onChange={(event) => setSelectedMonth(event.target.value)} />
                <button
                  type="button"
                  className="btn-secondary px-3"
                  aria-label="Mese successivo"
                  onClick={() => setSelectedMonth((current) => shiftMonth(current, 1))}
                >
                  ›
                </button>
              </div>
              <p className="mt-1 text-xs capitalize text-gray-400">{formatMonthLabel(selectedMonth)}</p>
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Tipo personale
              <input className="form-control mt-1" value={employeeKind} onChange={(event) => setEmployeeKind(event.target.value)} />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Template XLSM opzionale
              <input className="form-control mt-1" value={templatePath} onChange={(event) => setTemplatePath(event.target.value)} placeholder="/percorso/template.xlsm" />
            </label>
          </div>

          {isLoading ? (
            <p className="text-sm text-gray-500">Caricamento collaboratori...</p>
          ) : collaborators.length === 0 ? (
            <EmptyState icon={DocumentIcon} title="Nessun collaboratore importato" description="Importa prima un file JSON Inaz per poter esportare il mese." />
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-medium text-gray-700">Collaboratori inclusi</p>
                <div className="flex gap-2">
                  <button className="btn-secondary" type="button" onClick={() => setSelectedIds(collaborators.map((item) => item.id))}>
                    Seleziona tutti
                  </button>
                  <button className="btn-secondary" type="button" onClick={() => setSelectedIds([])}>
                    Deseleziona
                  </button>
                </div>
              </div>
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {collaborators.map((collaborator) => {
                  const isSelected = selectedIds.includes(collaborator.id);
                  return (
                    <label key={collaborator.id} className="flex items-start gap-3 rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 text-sm">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={(event) =>
                          setSelectedIds((current) =>
                            event.target.checked ? [...current, collaborator.id] : current.filter((item) => item !== collaborator.id),
                          )
                        }
                      />
                      <div className="min-w-0">
                        <p className="font-medium text-gray-900">{collaborator.name}</p>
                        <p className="text-xs text-gray-500">
                          {[
                            `Matricola ${collaborator.employee_code}`,
                            getInazCompanyLabel(collaborator.company_label, collaborator.company_code, ""),
                            collaborator.application_user_id ? "mappato" : "non mappato",
                          ]
                            .filter(Boolean)
                            .join(" · ")}
                        </p>
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>
          )}

          <div className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
            <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
              <p className="section-title">Preview dataset mese</p>
              <p className="section-copy">
                {isLoadingPreview
                  ? "Caricamento giornaliere del mese selezionato..."
                  : `Periodo ${monthBoundsFromValue(selectedMonth).start} / ${monthBoundsFromValue(selectedMonth).end}. La preview usa le giornaliere gia persistite in GAIA.`}
              </p>
              <div className="mt-4 grid gap-3 md:grid-cols-3">
                <div className="rounded-xl border border-white bg-white px-3 py-3">
                  <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Righe incluse</p>
                  <p className="mt-2 text-2xl font-semibold text-gray-900">{scopedRecords.length}</p>
                </div>
                <div className="rounded-xl border border-white bg-white px-3 py-3">
                  <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Giorni speciali</p>
                  <p className="mt-2 text-2xl font-semibold text-gray-900">{specialDayCount}</p>
                </div>
                <div className="rounded-xl border border-white bg-white px-3 py-3">
                  <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Dettaglio Inaz ricco</p>
                  <p className="mt-2 text-2xl font-semibold text-gray-900">{detailDrivenCount}</p>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
              <p className="section-title">Collaboratori esportati</p>
              <p className="section-copy">
                {selectedIds.length > 0
                  ? "Campione dei collaboratori selezionati esplicitamente."
                  : "Campione dei collaboratori che rientreranno nell'export completo."}
              </p>
              <div className="mt-4 space-y-3">
                {previewCollaborators.map((collaborator) => (
                  <div key={collaborator.id} className="rounded-xl border border-white bg-white px-3 py-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-medium text-gray-900">{collaborator.name}</p>
                        <p className="text-xs text-gray-500">
                          {[
                            `Matricola ${collaborator.employee_code}`,
                            getInazCompanyLabel(collaborator.company_label, collaborator.company_code, "") ? `Azienda ${getInazCompanyLabel(collaborator.company_label, collaborator.company_code, "")}` : null,
                          ]
                            .filter(Boolean)
                            .join(" · ")}
                        </p>
                      </div>
                      <Badge variant={collaborator.application_user_id ? "success" : "warning"}>
                        {collaborator.application_user_id ? "Mappato" : "Non mappato"}
                      </Badge>
                    </div>
                  </div>
                ))}
                {previewCollaborators.length === 0 ? <p className="text-sm text-gray-500">Nessun collaboratore nel perimetro selezionato.</p> : null}
              </div>
            </div>
          </div>

          <div className="flex justify-end">
            <button className="btn-primary" type="button" onClick={() => void handleExport()} disabled={isExporting || !selectedMonth}>
              {isExporting ? "Generazione..." : "Scarica XLSM"}
            </button>
          </div>
        </section>
      </div>
    </ProtectedPage>
  );
}
