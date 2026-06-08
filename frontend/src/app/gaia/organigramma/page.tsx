"use client";

import { useDeferredValue, useEffect, useMemo, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { AlertTriangleIcon, RefreshIcon, SearchIcon, UserIcon, UsersIcon } from "@/components/ui/icons";
import { MetricCard } from "@/components/ui/metric-card";
import {
  bootstrapOrgStructureFromWhiteCompany,
  deleteOrgStructureAssignment,
  getCurrentUser,
  getOrgStructureWorkspace,
  listAllApplicationUsers,
  upsertOrgStructureAssignment,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { cn } from "@/lib/cn";
import type {
  ApplicationUser,
  CurrentUser,
  OrgStructureAssignment,
  OrgStructureAssignmentUpdateInput,
  OrgStructureSuggestion,
  OrgStructureWorkspace,
} from "@/types/api";

type EditorState = {
  userId: number;
  managerUserId: string;
  title: string;
  areaLabel: string;
  notes: string;
  isActive: boolean;
};

function displayUser(user: Pick<ApplicationUser, "full_name" | "username"> | Pick<OrgStructureAssignment["user"], "full_name" | "username">): string {
  return user.full_name?.trim() || user.username;
}

function sourceBadgeVariant(sourceMode: string): "info" | "warning" | "success" | "neutral" {
  if (sourceMode === "manual") return "warning";
  if (sourceMode === "hybrid") return "success";
  if (sourceMode === "whitecompany") return "info";
  return "neutral";
}

function sourceBadgeLabel(sourceMode: string): string {
  if (sourceMode === "manual") return "Manuale";
  if (sourceMode === "hybrid") return "Pubblicato + import";
  if (sourceMode === "whitecompany") return "Importato";
  return sourceMode;
}

function emptyEditor(userId: number): EditorState {
  return {
    userId,
    managerUserId: "",
    title: "",
    areaLabel: "",
    notes: "",
    isActive: true,
  };
}

export default function GaiaOrgStructurePage() {
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [workspace, setWorkspace] = useState<OrgStructureWorkspace | null>(null);
  const [allUsers, setAllUsers] = useState<ApplicationUser[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [editor, setEditor] = useState<EditorState | null>(null);
  const [search, setSearch] = useState("");
  const [showOnlyUnassigned, setShowOnlyUnassigned] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isBootstrapping, setIsBootstrapping] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const deferredSearch = useDeferredValue(search);

  async function loadWorkspace(nextSelectedUserId?: number | null) {
    const token = getStoredAccessToken();
    if (!token) return;
    const [sessionUser, users, nextWorkspace] = await Promise.all([
      getCurrentUser(token),
      listAllApplicationUsers(token),
      getOrgStructureWorkspace(token),
    ]);
    setCurrentUser(sessionUser);
    setAllUsers(users);
    setWorkspace(nextWorkspace);

    const preferredUserId = nextSelectedUserId ?? selectedUserId;
    const firstPublished = nextWorkspace.items[0]?.application_user_id ?? null;
    const firstSuggested = nextWorkspace.suggestions.find((item) => !item.already_published)?.application_user_id ?? null;
    const resolvedUserId =
      preferredUserId && (nextWorkspace.items.some((item) => item.application_user_id === preferredUserId) || nextWorkspace.suggestions.some((item) => item.application_user_id === preferredUserId))
        ? preferredUserId
        : firstPublished ?? firstSuggested;
    setSelectedUserId(resolvedUserId);
  }

  useEffect(() => {
    void loadWorkspace().catch((loadError) => {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento organigramma");
    });
  }, []);

  const assignmentsByUserId = useMemo(
    () => new Map((workspace?.items ?? []).map((item) => [item.application_user_id, item])),
    [workspace],
  );
  const suggestionsByUserId = useMemo(
    () => new Map((workspace?.suggestions ?? []).map((item) => [item.application_user_id, item])),
    [workspace],
  );

  const selectedAssignment = selectedUserId != null ? assignmentsByUserId.get(selectedUserId) ?? null : null;
  const selectedSuggestion = selectedUserId != null ? suggestionsByUserId.get(selectedUserId) ?? null : null;

  useEffect(() => {
    if (selectedAssignment) {
      setEditor({
        userId: selectedAssignment.application_user_id,
        managerUserId: selectedAssignment.manager_user_id != null ? String(selectedAssignment.manager_user_id) : "",
        title: selectedAssignment.title ?? selectedAssignment.source_wc_role ?? "",
        areaLabel: selectedAssignment.area_label ?? "",
        notes: selectedAssignment.notes ?? "",
        isActive: selectedAssignment.is_active,
      });
      return;
    }
    if (selectedSuggestion) {
      setEditor({
        ...emptyEditor(selectedSuggestion.application_user_id),
        title: selectedSuggestion.wc_role ?? "",
      });
      return;
    }
    setEditor(null);
  }, [selectedAssignment, selectedSuggestion]);

  const treeChildren = useMemo(() => {
    const map = new Map<number, OrgStructureAssignment[]>();
    for (const item of workspace?.items ?? []) {
      if (item.manager_user_id == null) continue;
      const current = map.get(item.manager_user_id) ?? [];
      current.push(item);
      map.set(item.manager_user_id, current);
    }
    for (const group of map.values()) {
      group.sort((left, right) => displayUser(left.user).localeCompare(displayUser(right.user), "it"));
    }
    return map;
  }, [workspace]);

  const filteredAssignments = useMemo(() => {
    const term = deferredSearch.trim().toLowerCase();
    const unpublishedIds = new Set(
      (workspace?.suggestions ?? [])
        .filter((item) => !item.already_published)
        .map((item) => item.application_user_id),
    );
    return (workspace?.items ?? []).filter((item) => {
      if (showOnlyUnassigned) {
        return false;
      }
      if (!term) return true;
      return [
        displayUser(item.user),
        item.user.username,
        item.user.email,
        item.title ?? "",
        item.area_label ?? "",
      ].some((value) => value.toLowerCase().includes(term));
    }).filter((item) => !showOnlyUnassigned || unpublishedIds.has(item.application_user_id));
  }, [deferredSearch, showOnlyUnassigned, workspace]);

  const visibleRoots = useMemo(() => {
    const items = filteredAssignments;
    const visibleIds = new Set(items.map((item) => item.application_user_id));
    return items
      .filter((item) => item.manager_user_id == null || !visibleIds.has(item.manager_user_id))
      .sort((left, right) => displayUser(left.user).localeCompare(displayUser(right.user), "it"));
  }, [filteredAssignments]);

  const unpublishedSuggestions = useMemo(() => {
    const term = deferredSearch.trim().toLowerCase();
    return (workspace?.suggestions ?? [])
      .filter((item) => !item.already_published)
      .filter((item) => {
        if (!showOnlyUnassigned && term === "") return true;
        if (!showOnlyUnassigned && term !== "") {
          return [
            item.full_name ?? "",
            item.username,
            item.email,
            item.wc_role ?? "",
            item.chart_summary ?? "",
          ].some((value) => value.toLowerCase().includes(term));
        }
        return true;
      })
      .sort((left, right) => (left.full_name || left.username).localeCompare(right.full_name || right.username, "it"));
  }, [deferredSearch, showOnlyUnassigned, workspace]);

  const selectableManagers = useMemo(
    () =>
      allUsers
        .filter((user) => user.id !== editor?.userId)
        .sort((left, right) => displayUser(left).localeCompare(displayUser(right), "it")),
    [allUsers, editor?.userId],
  );

  const selectedChildren = useMemo(
    () => (selectedUserId != null ? treeChildren.get(selectedUserId) ?? [] : []),
    [selectedUserId, treeChildren],
  );

  async function handleBootstrap() {
    const token = getStoredAccessToken();
    if (!token) return;
    setIsBootstrapping(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await bootstrapOrgStructureFromWhiteCompany(token);
      await loadWorkspace(selectedUserId);
      setSuccess(`Bootstrap completato: ${result.created} creati, ${result.updated} aggiornati, ${result.skipped} invariati.`);
    } catch (bootstrapError) {
      setError(bootstrapError instanceof Error ? bootstrapError.message : "Errore bootstrap organigramma");
    } finally {
      setIsBootstrapping(false);
    }
  }

  async function handleSave() {
    const token = getStoredAccessToken();
    if (!token || !editor) return;
    setIsSaving(true);
    setError(null);
    setSuccess(null);
    const payload: OrgStructureAssignmentUpdateInput = {
      manager_user_id: editor.managerUserId ? Number(editor.managerUserId) : null,
      title: editor.title.trim() || null,
      area_label: editor.areaLabel.trim() || null,
      notes: editor.notes.trim() || null,
      is_active: editor.isActive,
    };
    try {
      const saved = await upsertOrgStructureAssignment(token, editor.userId, payload);
      await loadWorkspace(saved.application_user_id);
      setSuccess(`Nodo organigramma aggiornato per ${displayUser(saved.user)}.`);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Errore salvataggio organigramma");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleReset() {
    const token = getStoredAccessToken();
    if (!token || !editor) return;
    setIsSaving(true);
    setError(null);
    setSuccess(null);
    try {
      await deleteOrgStructureAssignment(token, editor.userId);
      await loadWorkspace(editor.userId);
      setSuccess("Nodo organigramma rimosso. I riporti diretti sono stati riportati a radice.");
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Errore rimozione nodo");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <ProtectedPage
      title="Organigramma Inaz"
      description="Editor visuale della gerarchia interna: import WhiteCompany come base, correzioni manuali e struttura effettiva pubblicata per permessi e validazioni."
      breadcrumb="Inaz"
      requiredModule="inaz"
      requiredRoles={["admin", "super_admin"]}
    >
      <div className="space-y-6">
        {error ? <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
        {success ? <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div> : null}

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <MetricCard label="Utenti GAIA" value={workspace?.metrics.total_users ?? 0} sub="Account disponibili nel dominio" />
          <MetricCard label="Nodi pubblicati" value={workspace?.metrics.published_nodes ?? 0} sub="Gerarchia effettiva salvata" variant="success" />
          <MetricCard label="Radici" value={workspace?.metrics.root_nodes ?? 0} sub="Responsabili di primo livello" />
          <MetricCard label="Da assegnare" value={workspace?.metrics.unassigned_users ?? 0} sub="Senza posizione nella gerarchia" variant="warning" />
          <MetricCard label="Link WC" value={workspace?.metrics.linked_whitecompany_users ?? 0} sub="Utenti collegati a WhiteCompany" variant="info" />
        </section>

        <section className="panel-card">
          <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr_auto] xl:items-end">
            <label className="block text-sm font-medium text-gray-700">
              Cerca persona, ruolo o area
              <div className="relative mt-1">
                <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <input
                  className="form-control pl-10"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Nome, username, email, ruolo, area"
                />
              </div>
            </label>
            <label className="flex items-center gap-3 rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={showOnlyUnassigned}
                onChange={(event) => setShowOnlyUnassigned(event.target.checked)}
              />
              Mostra solo utenti ancora da posizionare
            </label>
            <button type="button" className="btn-secondary" onClick={() => void handleBootstrap()} disabled={isBootstrapping}>
              <RefreshIcon className="h-4 w-4" />
              {isBootstrapping ? "Import in corso..." : "Importa da WhiteCompany"}
            </button>
          </div>
          <div className="mt-4 flex flex-wrap gap-3 text-xs text-gray-500">
            <span>Sessione: {currentUser?.username ?? "—"}</span>
            <span>La struttura pubblicata è quella che useremo per i permessi a cascata.</span>
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-[minmax(0,1.25fr)_420px]">
          <article className="panel-card min-w-0">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="section-title">Mappa gerarchica</p>
                <p className="section-copy">Naviga i nodi pubblicati e usa i suggerimenti WhiteCompany per completare la struttura.</p>
              </div>
              <Badge variant="neutral">{workspace?.items.length ?? 0} nodi</Badge>
            </div>

            <div className="mt-5 space-y-3">
              {visibleRoots.length === 0 ? (
                <EmptyState icon={UsersIcon} title="Nessun nodo pubblicato" description="Importa le posizioni da WhiteCompany o seleziona un suggerimento per creare il primo responsabile." />
              ) : (
                visibleRoots.map((item) => (
                  <TreeBranch
                    key={item.application_user_id}
                    item={item}
                    childrenMap={treeChildren}
                    selectedUserId={selectedUserId}
                    onSelect={setSelectedUserId}
                  />
                ))
              )}
            </div>

            <div className="mt-8 border-t border-gray-100 pt-6">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="section-title">Suggerimenti WhiteCompany</p>
                  <p className="section-copy">Utenti collegati al dominio operativo ma non ancora pubblicati nella gerarchia effettiva.</p>
                </div>
                <Badge variant="info">{unpublishedSuggestions.length}</Badge>
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {unpublishedSuggestions.length === 0 ? (
                  <EmptyState icon={UserIcon} title="Nessun suggerimento aperto" description="Tutti gli utenti WhiteCompany collegati sono già stati pubblicati oppure la sync non ha ancora prodotto mapping utili." />
                ) : (
                  unpublishedSuggestions.map((item) => (
                    <button
                      key={item.application_user_id}
                      type="button"
                      onClick={() => setSelectedUserId(item.application_user_id)}
                      className={cn(
                        "rounded-[24px] border px-4 py-4 text-left transition",
                        selectedUserId === item.application_user_id
                          ? "border-emerald-300 bg-emerald-50 shadow-[0_12px_30px_-22px_rgba(5,150,105,0.55)]"
                          : "border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50",
                      )}
                    >
                      <div className="flex items-start gap-3">
                        <Avatar label={item.full_name || item.username} size="md" />
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-semibold text-gray-900">{item.full_name || item.username}</p>
                          <p className="mt-1 text-xs text-gray-500">{item.username} · {item.wc_role || item.role}</p>
                          {item.chart_summary ? <p className="mt-2 text-xs text-gray-600">{item.chart_summary}</p> : null}
                        </div>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>
          </article>

          <aside className="panel-card">
            <div>
              <p className="section-title">Dettaglio nodo</p>
              <p className="section-copy">Qui correggi la struttura effettiva: responsabile, titolo, area e note operative.</p>
            </div>

            {!editor || (!selectedAssignment && !selectedSuggestion) ? (
              <div className="mt-6">
                <EmptyState icon={UserIcon} title="Seleziona una persona" description="Clicca un nodo esistente o un suggerimento WhiteCompany per aprire l'editor laterale." />
              </div>
            ) : (
              <div className="mt-6 space-y-5">
                <div className="rounded-[28px] border border-gray-200 bg-[linear-gradient(180deg,_#ffffff,_#f6faf7)] p-5">
                  <div className="flex items-start gap-4">
                    <Avatar label={selectedAssignment?.user.full_name || selectedSuggestion?.full_name || selectedAssignment?.user.username || selectedSuggestion?.username || "U"} size="lg" />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="truncate text-base font-semibold text-gray-900">
                          {selectedAssignment ? displayUser(selectedAssignment.user) : selectedSuggestion?.full_name || selectedSuggestion?.username}
                        </p>
                        {selectedAssignment ? <Badge variant={sourceBadgeVariant(selectedAssignment.source_mode)}>{sourceBadgeLabel(selectedAssignment.source_mode)}</Badge> : <Badge variant="info">Suggerimento</Badge>}
                        {editor.isActive ? <Badge variant="success">Attivo</Badge> : <Badge variant="neutral">Inattivo</Badge>}
                      </div>
                      <p className="mt-1 text-sm text-gray-500">
                        {selectedAssignment?.user.username || selectedSuggestion?.username} · {selectedAssignment?.user.email || selectedSuggestion?.email}
                      </p>
                      {selectedAssignment?.source_chart_summary || selectedSuggestion?.chart_summary ? (
                        <p className="mt-3 rounded-2xl bg-white/80 px-3 py-2 text-xs text-gray-600">
                          Fonte WhiteCompany: {selectedAssignment?.source_chart_summary || selectedSuggestion?.chart_summary}
                        </p>
                      ) : null}
                    </div>
                  </div>
                </div>

                <label className="block text-sm font-medium text-gray-700">
                  Responsabile diretto
                  <select
                    className="form-control mt-1"
                    value={editor.managerUserId}
                    onChange={(event) => setEditor((current) => current ? { ...current, managerUserId: event.target.value } : current)}
                  >
                    <option value="">Radice organizzativa</option>
                    {selectableManagers.map((user) => (
                      <option key={user.id} value={user.id}>
                        {displayUser(user)} · {user.username}
                      </option>
                    ))}
                  </select>
                </label>

                <div className="grid gap-4 md:grid-cols-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Titolo / ruolo operativo
                    <input
                      className="form-control mt-1"
                      value={editor.title}
                      onChange={(event) => setEditor((current) => current ? { ...current, title: event.target.value } : current)}
                      placeholder="Es. Capo settore manutenzione"
                    />
                  </label>
                  <label className="block text-sm font-medium text-gray-700">
                    Area / perimetro
                    <input
                      className="form-control mt-1"
                      value={editor.areaLabel}
                      onChange={(event) => setEditor((current) => current ? { ...current, areaLabel: event.target.value } : current)}
                      placeholder="Es. Distretto Nord"
                    />
                  </label>
                </div>

                <label className="block text-sm font-medium text-gray-700">
                  Note interne
                  <textarea
                    className="form-control mt-1 min-h-28"
                    value={editor.notes}
                    onChange={(event) => setEditor((current) => current ? { ...current, notes: event.target.value } : current)}
                    placeholder="Annotazioni organizzative, eccezioni, chiarimenti sulla responsabilità."
                  />
                </label>

                <label className="flex items-center gap-3 rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-700">
                  <input
                    type="checkbox"
                    checked={editor.isActive}
                    onChange={(event) => setEditor((current) => current ? { ...current, isActive: event.target.checked } : current)}
                  />
                  Nodo attivo nella struttura pubblicata
                </label>

                <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-500">Impatto immediato</p>
                  <div className="mt-3 grid gap-3 md:grid-cols-2">
                    <div>
                      <p className="text-2xl font-semibold text-gray-900">{selectedAssignment?.direct_reports_count ?? 0}</p>
                      <p className="text-sm text-gray-500">riporti diretti attuali</p>
                    </div>
                    <div>
                      <p className="text-2xl font-semibold text-gray-900">{selectedAssignment?.descendants_count ?? 0}</p>
                      <p className="text-sm text-gray-500">persone nel perimetro complessivo</p>
                    </div>
                  </div>
                  {selectedChildren.length > 0 ? (
                    <div className="mt-4 flex flex-wrap gap-2">
                      {selectedChildren.map((child) => (
                        <span key={child.application_user_id} className="rounded-full bg-white px-3 py-1 text-xs text-gray-600">
                          {displayUser(child.user)}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-4 text-sm text-gray-500">Nessun riporto diretto associato a questo nodo.</p>
                  )}
                </div>

                <div className="flex flex-wrap gap-3">
                  <button type="button" className="btn-primary" disabled={isSaving} onClick={() => void handleSave()}>
                    {isSaving ? "Salvataggio..." : "Pubblica nodo"}
                  </button>
                  {selectedAssignment ? (
                    <button type="button" className="btn-secondary" disabled={isSaving} onClick={() => void handleReset()}>
                      Ripristina nodo
                    </button>
                  ) : null}
                </div>
              </div>
            )}
          </aside>
        </section>
      </div>
    </ProtectedPage>
  );
}

function TreeBranch({
  item,
  childrenMap,
  selectedUserId,
  onSelect,
}: {
  item: OrgStructureAssignment;
  childrenMap: Map<number, OrgStructureAssignment[]>;
  selectedUserId: number | null;
  onSelect: (userId: number) => void;
}) {
  const children = childrenMap.get(item.application_user_id) ?? [];
  return (
    <div className="space-y-3">
      <button
        type="button"
        onClick={() => onSelect(item.application_user_id)}
        className={cn(
          "w-full rounded-[28px] border px-4 py-4 text-left transition",
          selectedUserId === item.application_user_id
            ? "border-emerald-300 bg-emerald-50 shadow-[0_14px_30px_-22px_rgba(5,150,105,0.6)]"
            : "border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50",
        )}
      >
        <div className="flex items-start gap-3">
          <Avatar label={displayUser(item.user)} size="md" />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <p className="truncate text-sm font-semibold text-gray-900">{displayUser(item.user)}</p>
              <Badge variant={sourceBadgeVariant(item.source_mode)}>{sourceBadgeLabel(item.source_mode)}</Badge>
              {item.is_active ? <Badge variant="success">attivo</Badge> : <Badge variant="neutral">off</Badge>}
            </div>
            <p className="mt-1 truncate text-xs text-gray-500">
              {item.title || item.user.role} {item.area_label ? `· ${item.area_label}` : ""} {item.user.username ? `· ${item.user.username}` : ""}
            </p>
            <div className="mt-3 flex flex-wrap gap-2 text-xs text-gray-500">
              <span>{item.direct_reports_count} diretti</span>
              <span>{item.descendants_count} nel perimetro</span>
              {item.manager ? <span>riporta a {displayUser(item.manager)}</span> : <span>radice</span>}
            </div>
          </div>
        </div>
      </button>

      {children.length > 0 ? (
        <div className="ml-6 border-l border-dashed border-gray-200 pl-4">
          {children.map((child) => (
            <TreeBranch
              key={child.application_user_id}
              item={child}
              childrenMap={childrenMap}
              selectedUserId={selectedUserId}
              onSelect={onSelect}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}
