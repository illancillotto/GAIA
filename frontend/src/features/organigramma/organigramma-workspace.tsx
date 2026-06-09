"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { getOrgReference } from "@/app/organigramma/reference-data";
import {
  CheckIcon,
  ChevronRightIcon,
  EyeIcon,
  FolderIcon,
  GridIcon,
  RefreshIcon,
  SearchIcon,
  ShieldIcon,
  UsersIcon,
} from "@/components/ui/icons";
import {
  createOrgOverride,
  getOrgAssignments,
  getOrgOverrides,
  getOrgTree,
  getOrgUnit,
  getOrgVisibility,
  isAuthError,
  listAllApplicationUsers,
  syncOrgWhiteCompany,
  updateOrgUnit,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { cn } from "@/lib/cn";
import { computeTreeInclusion, flattenTree, unitPath } from "@/lib/organigramma";
import type {
  ApplicationUser,
  OrgAssignment,
  OrgOverrideScope,
  OrgOverrideStatus,
  OrgSource,
  OrgUnitDetail,
  OrgUnitTreeNode,
  OrgUnitType,
  OrgVisibilityOverride,
  OrgVisibilityOverrideCreateInput,
  OrgVisibilityResult,
} from "@/types/api";

type UnitSummary = {
  descendantIds: Set<string>;
  directAssignments: OrgAssignment[];
  subtreeAssignments: OrgAssignment[];
  subtreeChildUnits: OrgUnitTreeNode[];
};

type SchemaNodeMeta = {
  lead: OrgAssignment | null;
  totalPeople: number;
  directPeople: number;
  descendantIds: Set<string>;
};

const TYPE_META: Record<OrgUnitType, { label: string; chip: string; dot: string }> = {
  direzione: { label: "Direzione", chip: "bg-[#D3EAD4] text-[#163d29] border-[#bcd9bf]", dot: "#1D4E35" },
  distretto: { label: "Distretto", chip: "bg-[#e0f3ec] text-[#0f6a4e] border-[#bfe5d6]", dot: "#1D9E75" },
  settore: { label: "Settore", chip: "bg-[#e3f0f5] text-[#215a72] border-[#c4e0ea]", dot: "#3b82a6" },
  squadra: { label: "Squadra", chip: "bg-[#efeaf7] text-[#574a78] border-[#ddd2ee]", dot: "#8a7bb8" },
};

const SCOPE_LABEL: Record<OrgOverrideScope, string> = { read: "Lettura", approve: "Approvazione", full: "Completo" };

const TYPE_FILTERS: { value: OrgUnitType | "all"; label: string }[] = [
  { value: "all", label: "Tutti" },
  { value: "direzione", label: "Direzione" },
  { value: "distretto", label: "Distretto" },
  { value: "settore", label: "Settore" },
  { value: "squadra", label: "Squadra" },
];

function initials(name: string | null | undefined): string {
  if (!name) return "?";
  return name.split(/\s+/).slice(0, 2).map((w) => w[0]?.toUpperCase() ?? "").join("");
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("it-IT");
}

function normalizeLabel(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim();
}

function collectDescendantIds(node: OrgUnitTreeNode): Set<string> {
  const ids = new Set<string>([node.id]);
  const queue = [...node.children];
  while (queue.length) {
    const current = queue.shift();
    if (!current) continue;
    ids.add(current.id);
    queue.push(...current.children);
  }
  return ids;
}

function buildUnitSummary(node: OrgUnitTreeNode, assignments: OrgAssignment[]): UnitSummary {
  const descendantIds = collectDescendantIds(node);
  return {
    descendantIds,
    directAssignments: assignments.filter((assignment) => assignment.org_unit_id === node.id),
    subtreeAssignments: assignments.filter((assignment) => descendantIds.has(assignment.org_unit_id)),
    subtreeChildUnits: node.children,
  };
}

function isLeadershipTitle(title: string | null | undefined): boolean {
  const normalized = (title ?? "").trim().toLowerCase();
  return normalized.includes("dirigent")
    || normalized.includes("dirett")
    || normalized.includes("responsab")
    || normalized.includes("capo ");
}

function pickLeadAssignment(assignments: OrgAssignment[]): OrgAssignment | null {
  return assignments.find((assignment) => isLeadershipTitle(assignment.title))
    ?? assignments.find((assignment) => assignment.manager_user_id == null)
    ?? assignments[0]
    ?? null;
}

function buildSchemaMeta(tree: OrgUnitTreeNode[], assignments: OrgAssignment[]): Map<string, SchemaNodeMeta> {
  const flat = flattenTree(tree);
  const meta = new Map<string, SchemaNodeMeta>();
  for (const node of flat) {
    const summary = buildUnitSummary(node, assignments);
    meta.set(node.id, {
      lead: pickLeadAssignment(summary.directAssignments),
      totalPeople: summary.subtreeAssignments.length,
      directPeople: summary.directAssignments.length,
      descendantIds: summary.descendantIds,
    });
  }
  return meta;
}

function Pill({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium leading-none", className)}>
      {children}
    </span>
  );
}

function SourceBadge({ source, legacyTeamId }: { source: OrgSource; legacyTeamId?: string | null }) {
  if (source === "whitecompany") {
    return (
      <Pill className="border-[#bfe5e0] bg-[#e2f4f1] text-[#0d7a66]">
        <span className="rounded-full bg-[#1D9E75] px-1 text-[9px] font-bold text-white">WC</span>
        WhiteCompany
      </Pill>
    );
  }
  if (source === "bridge_team") {
    return (
      <Pill className="border-[#d8d2ee] bg-[#efeaf7] text-[#574a78]">Bridge legacy{legacyTeamId ? " ·" : ""}</Pill>
    );
  }
  return (
    <Pill className="border-[#d5e2d8] bg-[#edf5f0] text-[#1D4E35]"><CheckIcon className="h-3 w-3" /> Manuale</Pill>
  );
}

function TypeChip({ tipo }: { tipo: OrgUnitType }) {
  const m = TYPE_META[tipo];
  return (
    <Pill className={m.chip}>
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: m.dot }} /> {m.label}
    </Pill>
  );
}

function StatusBadge({ active }: { active: boolean }) {
  return (
    <Pill className={active ? "border-[#bfe5d6] bg-[#e0f3ec] text-[#0f6a4e]" : "border-[#e6d3d3] bg-[#f7ecec] text-[#9a3b3b]"}>
      <span className={cn("h-1.5 w-1.5 rounded-full", active ? "bg-[#1D9E75]" : "bg-[#ba1a1a]")} />
      {active ? "Attivo" : "Inattivo"}
    </Pill>
  );
}

function Avatar({ name, size = 36, tone = "green" }: { name: string | null; size?: number; tone?: "green" | "amber" }) {
  const styles = tone === "amber"
    ? { background: "#fdebd0", color: "#92400e", border: "#f3d29a" }
    : { background: "#D3EAD4", color: "#1D4E35", border: "#bcd9bf" };
  return (
    <span
      className="inline-flex shrink-0 items-center justify-center rounded-full border font-semibold"
      style={{ width: size, height: size, fontSize: size * 0.36, background: styles.background, color: styles.color, borderColor: styles.border }}
    >
      {initials(name)}
    </span>
  );
}

const OVERRIDE_STATUS_PILL: Record<OrgOverrideStatus, string> = {
  attivo: "border-[#e7c89a] bg-[#fdf3e3] text-[#b45309]",
  programmato: "border-[#c4d3ea] bg-[#eef3fb] text-[#2f5da8]",
  scaduto: "border-[#dcdcdc] bg-[#f4f4f4] text-[#6b6b6b]",
  disattivato: "border-[#dcdcdc] bg-[#f4f4f4] text-[#6b6b6b]",
};

// --------------------------------------------------------------------------- //
// Recursive tree
// --------------------------------------------------------------------------- //
type TreeProps = {
  node: OrgUnitTreeNode;
  depth: number;
  expanded: Set<string>;
  selectedId: string | null;
  showProvenance: boolean;
  includeIds: Set<string> | null;
  matchIds: Set<string>;
  onToggle: (id: string) => void;
  onSelect: (id: string) => void;
};

function TreeNode({ node, depth, expanded, selectedId, showProvenance, includeIds, matchIds, onToggle, onSelect }: TreeProps) {
  const children = includeIds ? node.children.filter((c) => includeIds.has(c.id)) : node.children;
  const hasChildren = node.children.length > 0;
  const isOpen = expanded.has(node.id) || (includeIds !== null && includeIds.has(node.id));
  const isSelected = selectedId === node.id;
  const isHit = matchIds.has(node.id);

  return (
    <li>
      <div
        role="treeitem"
        aria-expanded={hasChildren ? isOpen : undefined}
        aria-selected={isSelected}
        tabIndex={0}
        onClick={() => onSelect(node.id)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onSelect(node.id);
          } else if ((e.key === "ArrowRight" || e.key === "ArrowLeft") && hasChildren) {
            onToggle(node.id);
          }
        }}
        className={cn(
          "group flex cursor-pointer items-center gap-2 rounded-xl border px-2.5 py-2 outline-none transition-colors focus-visible:ring-2 focus-visible:ring-[#1D9E75]/60",
          isSelected
            ? "border-[#1D4E35] bg-[#D3EAD4]"
            : isHit
              ? "border-[#bfe5d6] bg-[#f1faf4] hover:bg-[#e9f6ee]"
              : "border-transparent hover:border-[#e6ebe5] hover:bg-[#f5f9f4]",
        )}
        style={{ marginLeft: depth * 16 }}
      >
        <button
          type="button"
          aria-label={isOpen ? "Comprimi" : "Espandi"}
          tabIndex={-1}
          onClick={(e) => {
            e.stopPropagation();
            if (hasChildren) onToggle(node.id);
          }}
          className={cn("flex h-5 w-5 shrink-0 items-center justify-center rounded-md", hasChildren ? "text-[#1D4E35] hover:bg-white" : "text-transparent")}
        >
          <ChevronRightIcon className={cn("h-4 w-4 transition-transform", isOpen ? "rotate-90" : "")} />
        </button>
        <span className="flex min-w-0 flex-1 flex-col gap-1">
          <span className="flex flex-wrap items-center gap-2">
            <span className="truncate text-[13.5px] font-semibold text-[#051b12]">{node.nome}</span>
            <TypeChip tipo={node.tipo} />
          </span>
          <span className="flex flex-wrap items-center gap-2 text-[11px] text-[#5f6d61]">
            <span className="inline-flex items-center gap-1"><UsersIcon className="h-3 w-3" /> {node.person_count}</span>
            <span className="inline-flex items-center gap-1"><FolderIcon className="h-3 w-3" /> {node.child_count} sotto-unità</span>
            {showProvenance ? <SourceBadge source={node.source} legacyTeamId={node.legacy_team_id} /> : null}
          </span>
        </span>
      </div>
      {hasChildren && isOpen ? (
        <ul role="group" className="mt-1 flex flex-col gap-1 border-l border-dashed border-[#dbe6dc]" style={{ marginLeft: depth * 16 + 16 }}>
          {children.map((c) => (
            <div key={c.id} className="-ml-px">
              <TreeNode
                node={c}
                depth={0}
                expanded={expanded}
                selectedId={selectedId}
                showProvenance={showProvenance}
                includeIds={includeIds}
                matchIds={matchIds}
                onToggle={onToggle}
                onSelect={onSelect}
              />
            </div>
          ))}
        </ul>
      ) : null}
    </li>
  );
}

// --------------------------------------------------------------------------- //
// Person card
// --------------------------------------------------------------------------- //
function PersonCard({ assignment, onOpen }: { assignment: OrgAssignment; onOpen: (id: number) => void }) {
  const name = assignment.person?.full_name ?? assignment.person?.username ?? `Utente #${assignment.user_id}`;
  const active = assignment.active && (assignment.person?.is_active ?? true);
  return (
    <button
      type="button"
      onClick={() => onOpen(assignment.user_id)}
      className="flex w-full items-start gap-3 rounded-xl border border-[#e6ebe5] bg-white p-3 text-left transition-all hover:border-[#bcd9bf] hover:shadow-[0_8px_24px_rgba(15,23,42,0.06)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1D9E75]/60"
    >
      <Avatar name={name} />
      <span className="min-w-0 flex-1">
        <span className="flex flex-wrap items-center gap-2">
          <span className="text-[13.5px] font-semibold text-[#051b12]">{name}</span>
          <StatusBadge active={active} />
        </span>
        <span className="mt-0.5 block text-[12px] text-[#3a4a3f]">{assignment.title ?? "—"}</span>
        <span className="mt-1 block text-[11.5px] text-[#5f6d61]">
          {assignment.manager
            ? <>riporta a <span className="font-medium text-[#1D4E35]">{assignment.manager.full_name ?? assignment.manager.username}</span></>
            : "vertice — nessun responsabile"}
        </span>
        <span className="mt-1.5 flex flex-wrap items-center gap-1.5">
          <SourceBadge source={assignment.source} />
          {assignment.person ? <Pill className="border-[#d5e2d8] bg-[#f5f9f4] text-[#5f6d61]">RBAC: {assignment.person.rbac_role}</Pill> : null}
        </span>
      </span>
    </button>
  );
}

type SchemaBoardProps = {
  tree: OrgUnitTreeNode[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onOpenPerson: (id: number) => void;
  draggingNodeId: string | null;
  onDragStart: (id: string | null) => void;
  onDragEnd: () => void;
  onMove: (nodeId: string, parentId: string | null) => void;
  meta: Map<string, SchemaNodeMeta>;
  canManage: boolean;
};

function SchemaBoard({
  tree,
  selectedId,
  onSelect,
  onOpenPerson,
  draggingNodeId,
  onDragStart,
  onDragEnd,
  onMove,
  meta,
  canManage,
}: SchemaBoardProps) {
  return (
    <section className="rounded-[28px] border border-[#c8d9e7] bg-[radial-gradient(circle_at_top,_#ffffff,_#f6fafc_65%,_#eef4f7)] p-5 shadow-[0_20px_60px_rgba(15,23,42,0.08)]">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-serif text-[18px] font-semibold text-[#10233e]">Schema organigramma</h2>
          <p className="text-[12.5px] text-[#5c6d82]">
            Vista visuale top-down. Trascina un box sopra un altro per cambiare il responsabile gerarchico.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-[12px] text-[#5c6d82]">
          <Pill className="border-[#c4d3ea] bg-white text-[#2f5da8]">drag & drop guidato</Pill>
          <Pill className="border-[#d5e2d8] bg-white text-[#1D4E35]">{canManage ? "modifica attiva" : "sola lettura"}</Pill>
        </div>
      </div>

      {canManage ? (
        <div
          onDragOver={(event) => {
            if (!draggingNodeId) return;
            event.preventDefault();
          }}
          onDrop={(event) => {
            event.preventDefault();
            if (draggingNodeId) void onMove(draggingNodeId, null);
          }}
          className="mb-4 rounded-2xl border border-dashed border-[#c4d3ea] bg-white/80 px-4 py-3 text-[12.5px] text-[#2f5da8]"
        >
          Rilascia qui per portare il nodo in radice.
        </div>
      ) : null}

      <div className="overflow-x-auto pb-2">
        <div className="min-w-max">
          <div className="flex justify-center">
            {tree.length ? (
              tree.map((node) => (
                <SchemaNodeCard
                  key={node.id}
                  node={node}
                  depth={0}
                  selectedId={selectedId}
                  onSelect={onSelect}
                  onOpenPerson={onOpenPerson}
                  draggingNodeId={draggingNodeId}
                  onDragStart={onDragStart}
                  onDragEnd={onDragEnd}
                  onMove={onMove}
                  meta={meta}
                  canManage={canManage}
                />
              ))
            ) : (
              <div className="rounded-2xl border border-dashed border-[#d6dfef] bg-white px-8 py-10 text-[13px] text-[#5c6d82]">
                Nessun nodo disponibile per lo schema.
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

type SchemaNodeCardProps = {
  node: OrgUnitTreeNode;
  depth: number;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onOpenPerson: (id: number) => void;
  draggingNodeId: string | null;
  onDragStart: (id: string | null) => void;
  onDragEnd: () => void;
  onMove: (nodeId: string, parentId: string | null) => void;
  meta: Map<string, SchemaNodeMeta>;
  canManage: boolean;
};

function SchemaNodeCard({
  node,
  depth,
  selectedId,
  onSelect,
  onOpenPerson,
  draggingNodeId,
  onDragStart,
  onDragEnd,
  onMove,
  meta,
  canManage,
}: SchemaNodeCardProps) {
  const nodeMeta = meta.get(node.id);
  const lead = nodeMeta?.lead ?? null;
  const isSelected = selectedId === node.id;
  const isDragging = draggingNodeId === node.id;
  const canDropHere = Boolean(draggingNodeId && draggingNodeId !== node.id && !nodeMeta?.descendantIds.has(draggingNodeId));

  return (
    <div className="flex flex-col items-center">
      <div
        onDragOver={(event) => {
          if (!canManage || !canDropHere) return;
          event.preventDefault();
        }}
        onDrop={(event) => {
          event.preventDefault();
          if (canManage && draggingNodeId && draggingNodeId !== node.id) {
            void onMove(draggingNodeId, node.id);
          }
        }}
        className={cn(
          "relative w-[246px] rounded-[24px] border p-4 shadow-[0_18px_50px_rgba(15,23,42,0.08)] transition-all",
          depth === 0
            ? "border-[#7ea1bf] bg-[linear-gradient(180deg,#fdfefe,#edf4fa)]"
            : depth === 1
              ? "border-[#efb295] bg-[linear-gradient(180deg,#fffdfc,#fff2eb)]"
              : "border-[#a9c6b1] bg-[linear-gradient(180deg,#fefefe,#edf8ef)]",
          isSelected ? "ring-2 ring-[#1D4E35]/40" : "",
          isDragging ? "opacity-55" : "",
          canDropHere ? "hover:border-[#1D9E75]" : "",
        )}
        draggable={canManage}
        onDragStart={() => onDragStart(node.id)}
        onDragEnd={onDragEnd}
        onClick={() => onSelect(node.id)}
      >
        <div className="absolute -left-2 -top-2 h-full w-full rounded-[24px] border border-black/5 bg-black/[0.06]" />
        <div className="relative">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <TypeChip tipo={node.tipo} />
            <SourceBadge source={node.source} legacyTeamId={node.legacy_team_id} />
          </div>
          <div className="text-center font-serif text-[18px] font-semibold leading-tight text-[#051b12]">{node.nome}</div>
          <div className="mt-2 text-center text-[12.5px] text-[#3a4a3f]">
            {lead?.title ?? "Unità senza responsabile esplicito"}
          </div>
          <div className="mt-1 text-center text-[12px] text-[#5f6d61]">
            {lead?.person?.full_name ?? lead?.person?.username ?? "Nessun responsabile diretto"}
          </div>
          <div className="mt-3 flex flex-wrap justify-center gap-2">
            <Pill className="border-[#d5e2d8] bg-white text-[#1D4E35]">
              <UsersIcon className="h-3 w-3" /> {nodeMeta?.totalPeople ?? node.person_count}
            </Pill>
            <Pill className="border-[#e6ebe5] bg-white text-[#5f6d61]">
              diretti {nodeMeta?.directPeople ?? node.person_count}
            </Pill>
          </div>
          {lead?.person ? (
            <div className="mt-3 flex justify-center">
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  onOpenPerson(lead.user_id);
                }}
                className="rounded-full border border-[#d5e2d8] bg-white px-3 py-1 text-[11.5px] font-medium text-[#1D4E35] hover:bg-[#edf5f0]"
              >
                Apri scheda responsabile
              </button>
            </div>
          ) : null}
        </div>
      </div>

      {node.children.length ? (
        <>
          <div className="h-6 w-px bg-[#c4d3ea]" />
          <div className="relative flex items-start justify-center gap-4">
            {node.children.length > 1 ? (
              <div className="absolute left-[123px] right-[123px] top-0 h-px bg-[#c4d3ea]" />
            ) : null}
            {node.children.map((child) => (
              <div key={child.id} className="flex flex-col items-center">
                <div className="h-6 w-px bg-[#c4d3ea]" />
                <SchemaNodeCard
                  node={child}
                  depth={depth + 1}
                  selectedId={selectedId}
                  onSelect={onSelect}
                  onOpenPerson={onOpenPerson}
                  draggingNodeId={draggingNodeId}
                  onDragStart={onDragStart}
                  onDragEnd={onDragEnd}
                  onMove={onMove}
                  meta={meta}
                  canManage={canManage}
                />
              </div>
            ))}
          </div>
        </>
      ) : null}
    </div>
  );
}

// --------------------------------------------------------------------------- //
// Workspace
// --------------------------------------------------------------------------- //
type ViewMode = "albero" | "schema" | "chi-vede-chi";

export function OrganigrammaWorkspace() {
  const token = typeof window !== "undefined" ? getStoredAccessToken() : null;

  const [view, setView] = useState<ViewMode>("albero");
  const [tree, setTree] = useState<OrgUnitTreeNode[]>([]);
  const [overrides, setOverrides] = useState<OrgVisibilityOverride[]>([]);
  const [users, setUsers] = useState<ApplicationUser[]>([]);
  const [canManage, setCanManage] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<OrgUnitType | "all">("all");
  const [showProvenance, setShowProvenance] = useState(true);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<OrgUnitDetail | null>(null);

  const [simUserId, setSimUserId] = useState<number | null>(null);
  const [visibility, setVisibility] = useState<OrgVisibilityResult | null>(null);

  const [showAddOverride, setShowAddOverride] = useState(false);
  const [drawerUserId, setDrawerUserId] = useState<number | null>(null);
  const [allAssignments, setAllAssignments] = useState<OrgAssignment[]>([]);
  const [draggingNodeId, setDraggingNodeId] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined" && window.location.hash === "#chi-vede-chi") {
      setView("chi-vede-chi");
    }
  }, []);

  const loadCore = useCallback(async () => {
    if (!token) {
      setError("Sessione non disponibile.");
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const [treeData, usersData, assignmentsData] = await Promise.all([
        getOrgTree(token),
        listAllApplicationUsers(token),
        getOrgAssignments(token),
      ]);
      setTree(treeData);
      setUsers(usersData);
      setAllAssignments(assignmentsData);
      const flat = flattenTree(treeData);
      if (flat.length) {
        setExpanded(new Set(flat.slice(0, 3).map((n) => n.id)));
        setSelectedId((prev) => prev ?? flat[0].id);
      }
      // overrides are manage-gated; tolerate 403 for read-only users
      try {
        setOverrides(await getOrgOverrides(token));
        setCanManage(true);
      } catch (err) {
        if (!isAuthError(err)) setCanManage(false);
      }
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore di caricamento");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void loadCore();
  }, [loadCore]);

  // unit detail on selection
  useEffect(() => {
    if (!token || !selectedId) {
      setDetail(null);
      return;
    }
    let active = true;
    void getOrgUnit(token, selectedId)
      .then((d) => {
        if (active) setDetail(d);
      })
      .catch(() => {
        if (active) setDetail(null);
      });
    return () => {
      active = false;
    };
  }, [token, selectedId]);

  // visibility on simulator user change
  useEffect(() => {
    if (!token || simUserId == null || view !== "chi-vede-chi") return;
    let active = true;
    void getOrgVisibility(token, simUserId)
      .then((v) => {
        if (active) setVisibility(v);
      })
      .catch(() => {
        if (active) setVisibility(null);
      });
    return () => {
      active = false;
    };
  }, [token, simUserId, view]);

  useEffect(() => {
    if (simUserId == null && users.length) setSimUserId(users[0].id);
  }, [users, simUserId]);

  const { includeIds, matchIds } = useMemo(
    () => computeTreeInclusion(tree, query, typeFilter),
    [query, typeFilter, tree],
  );

  const flatTree = useMemo(() => flattenTree(tree), [tree]);
  const selectedNode = useMemo(
    () => flatTree.find((node) => node.id === selectedId) ?? null,
    [flatTree, selectedId],
  );
  const selectedSummary = useMemo(
    () => (selectedNode ? buildUnitSummary(selectedNode, allAssignments) : null),
    [selectedNode, allAssignments],
  );
  const schemaMeta = useMemo(
    () => buildSchemaMeta(tree, allAssignments),
    [tree, allAssignments],
  );

  const roots = includeIds ? tree.filter((r) => includeIds.has(r.id)) : tree;

  const toggle = (id: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  async function handleSync() {
    if (!token) return;
    setSyncing(true);
    setNotice(null);
    try {
      const result = await syncOrgWhiteCompany(token);
      setNotice(result.message);
      await loadCore();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Sync non riuscito");
    } finally {
      setSyncing(false);
    }
  }

  async function handleCreateOverride(payload: OrgVisibilityOverrideCreateInput) {
    if (!token) return;
    await createOrgOverride(token, payload);
    setOverrides(await getOrgOverrides(token));
    setShowAddOverride(false);
  }

  async function handleMoveNode(nodeId: string, parentId: string | null) {
    if (!token || !canManage || nodeId === parentId) return;
    const nodeMeta = schemaMeta.get(nodeId);
    if (parentId && nodeMeta?.descendantIds.has(parentId)) {
      setNotice("Operazione non valida: non puoi spostare un nodo dentro un suo discendente.");
      return;
    }
    setNotice(null);
    try {
      await updateOrgUnit(token, nodeId, { parent_id: parentId });
      setSelectedId(nodeId);
      await loadCore();
      setNotice(parentId ? "Gerarchia aggiornata." : "Nodo spostato in radice.");
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Aggiornamento gerarchia non riuscito");
    } finally {
      setDraggingNodeId(null);
    }
  }

  if (loading) {
    return <div className="rounded-2xl border border-[#e6ebe5] bg-white p-8 text-center text-[13px] text-[#5f6d61]">Caricamento organigramma…</div>;
  }
  if (error) {
    return <div className="rounded-2xl border border-[#e6d3d3] bg-[#fdf2f2] p-6 text-[13px] text-[#9a3b3b]">{error}</div>;
  }

  return (
    <div className="text-[#051b12]">
      {/* header */}
      <header className="mb-5">
        <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#5f6d61]">Governance · Organigramma</div>
        <h1 className="mt-1 font-serif text-[28px] font-semibold leading-tight">Organigramma operativo</h1>
        <p className="mt-1 max-w-3xl text-[13.5px] text-[#3a4a3f]">
          Gerarchia canonica delle unità (verità in GAIA), perimetro persona→responsabile→unità ed eccezioni di visibilità
          controllate. WhiteCompany è la <strong>provenienza</strong> iniziale, non la struttura finale.
        </p>
      </header>

      {/* toolbar */}
      <div className="mb-5 rounded-2xl border border-[#e6ebe5] bg-gradient-to-b from-white to-[#fbfcfa] p-3 shadow-[0_14px_40px_rgba(15,23,42,0.06)]">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative min-w-[220px] flex-1">
            <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#9fb0a3]" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Cerca unità…"
              className="w-full rounded-xl border border-[#e6ebe5] bg-[#fbfcfa] py-2 pl-9 pr-3 text-[13px] outline-none focus:border-[#1D9E75] focus:ring-2 focus:ring-[#1D9E75]/30"
            />
          </div>
          <div className="flex items-center gap-1.5 rounded-xl border border-[#e6ebe5] bg-[#fbfcfa] p-1">
            {TYPE_FILTERS.map((f) => (
              <button
                key={f.value}
                type="button"
                onClick={() => setTypeFilter(f.value)}
                className={cn("rounded-lg px-2.5 py-1.5 text-[12px] font-medium transition-colors", typeFilter === f.value ? "bg-[#1D4E35] text-white" : "text-[#3a4a3f] hover:bg-[#edf5f0]")}
              >
                {f.label}
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={() => setShowProvenance((v) => !v)}
            className={cn("inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-[12.5px] font-medium transition-colors", showProvenance ? "border-[#bfe5e0] bg-[#e2f4f1] text-[#0d7a66]" : "border-[#e6ebe5] bg-white text-[#5f6d61]")}
          >
            <span className={cn("flex h-4 w-7 items-center rounded-full p-0.5 transition-colors", showProvenance ? "bg-[#1D9E75]" : "bg-[#cdd6cf]")}>
              <span className={cn("h-3 w-3 rounded-full bg-white transition-transform", showProvenance ? "translate-x-3" : "")} />
            </span>
            Provenienza WhiteCompany
          </button>
          {canManage ? (
            <button
              type="button"
              onClick={handleSync}
              disabled={syncing}
              className="inline-flex items-center gap-2 rounded-xl border border-[#bfe5e0] bg-white px-3 py-2 text-[12.5px] font-medium text-[#0d7a66] transition-colors hover:bg-[#e2f4f1] disabled:opacity-60"
            >
              <RefreshIcon className={cn("h-4 w-4", syncing ? "animate-spin" : "")} /> Sync WhiteCompany
            </button>
          ) : null}
          <div className="ml-auto flex items-center gap-1 rounded-xl border border-[#e6ebe5] bg-[#fbfcfa] p-1">
            <button type="button" onClick={() => setView("albero")} className={cn("inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[12.5px] font-semibold transition-colors", view === "albero" ? "bg-[#1D4E35] text-white" : "text-[#3a4a3f] hover:bg-[#edf5f0]")}>
              <GridIcon className="h-4 w-4" /> Albero
            </button>
            <button type="button" onClick={() => setView("schema")} className={cn("inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[12.5px] font-semibold transition-colors", view === "schema" ? "bg-[#1D4E35] text-white" : "text-[#3a4a3f] hover:bg-[#edf5f0]")}>
              <FolderIcon className="h-4 w-4" /> Schema
            </button>
            <button type="button" onClick={() => setView("chi-vede-chi")} className={cn("inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[12.5px] font-semibold transition-colors", view === "chi-vede-chi" ? "bg-[#1D4E35] text-white" : "text-[#3a4a3f] hover:bg-[#edf5f0]")}>
              <EyeIcon className="h-4 w-4" /> Chi vede chi
            </button>
          </div>
        </div>
      </div>

      {notice ? (
        <div className="mb-4 rounded-xl border border-[#bfe5e0] bg-[#e2f4f1] px-4 py-2 text-[12.5px] text-[#0d7a66]">{notice}</div>
      ) : null}

      {view === "albero" ? (
        <div className="flex flex-col gap-5">
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
            <section className="rounded-2xl border border-[#e6ebe5] bg-gradient-to-b from-white to-[#fbfcfa] p-4 shadow-[0_14px_40px_rgba(15,23,42,0.06)]">
              <div className="mb-3 flex items-center gap-2">
                <FolderIcon className="h-4 w-4 text-[#1D4E35]" />
                <h2 className="font-serif text-[15px] font-semibold">Albero organizzativo</h2>
              </div>
              {roots.length ? (
                <ul role="tree" className="flex flex-col gap-1">
                  {roots.map((r) => (
                    <TreeNode
                      key={r.id}
                      node={r}
                      depth={0}
                      expanded={expanded}
                      selectedId={selectedId}
                      showProvenance={showProvenance}
                      includeIds={includeIds}
                      matchIds={matchIds}
                      onToggle={toggle}
                      onSelect={setSelectedId}
                    />
                  ))}
                </ul>
              ) : (
                <div className="rounded-xl border border-dashed border-[#d8e3d9] bg-[#fafdf9] p-8 text-center text-[12.5px] text-[#5f6d61]">
                  {tree.length ? "Nessuna unità corrisponde alla ricerca." : "Nessuna unità. Usa “Sync WhiteCompany” o crea la struttura via API."}
                </div>
              )}
            </section>

            <section className="rounded-2xl border border-[#e6ebe5] bg-gradient-to-b from-white to-[#fbfcfa] p-4 shadow-[0_14px_40px_rgba(15,23,42,0.06)]">
              {detail && selectedSummary ? <UnitDetail detail={detail} summary={selectedSummary} onOpenPerson={setDrawerUserId} /> : (
                <div className="flex h-full min-h-[240px] items-center justify-center rounded-xl border border-dashed border-[#d8e3d9] bg-[#fafdf9] text-center text-[12.5px] text-[#5f6d61]">
                  Seleziona un&apos;unità nell&apos;albero per vederne responsabile e persone.
                </div>
              )}
            </section>
          </div>

          <OverridePanel
            overrides={overrides}
            canManage={canManage}
            onAdd={() => setShowAddOverride(true)}
          />
        </div>
      ) : view === "schema" ? (
        <SchemaBoard
          tree={roots}
          selectedId={selectedId}
          onSelect={setSelectedId}
          onOpenPerson={setDrawerUserId}
          draggingNodeId={draggingNodeId}
          onDragStart={setDraggingNodeId}
          onDragEnd={() => setDraggingNodeId(null)}
          onMove={handleMoveNode}
          meta={schemaMeta}
          canManage={canManage}
        />
      ) : (
        <WhoSeesWho
          users={users}
          simUserId={simUserId}
          onPick={setSimUserId}
          visibility={visibility}
          onOpenPerson={setDrawerUserId}
        />
      )}

      {showAddOverride ? (
        <AddOverrideModal
          users={users}
          units={flatTree}
          onClose={() => setShowAddOverride(false)}
          onCreate={handleCreateOverride}
        />
      ) : null}

      {drawerUserId != null ? (
        <PersonDrawer
          token={token}
          userId={drawerUserId}
          overrides={overrides}
          units={flatTree}
          onClose={() => setDrawerUserId(null)}
        />
      ) : null}
    </div>
  );
}

// --------------------------------------------------------------------------- //
function UnitDetail({ detail, summary, onOpenPerson }: { detail: OrgUnitDetail; summary: UnitSummary; onOpenPerson: (id: number) => void }) {
  const { unit, path, responsabile, responsabile_title } = detail;
  const directAssignments = summary.directAssignments;
  const subtreeAssignments = summary.subtreeAssignments;
  const reference = getOrgReference(unit.nome);
  const actualByChildLabel = new Map(
    summary.subtreeChildUnits.map((child) => [
      normalizeLabel(child.nome),
      subtreeAssignments.filter((assignment) => assignment.org_unit_id === child.id).length,
    ]),
  );
  return (
    <div className="flex flex-col gap-4">
      <div>
        <nav className="flex flex-wrap items-center gap-1 text-[11px] text-[#5f6d61]">
          {path.map((p, i) => (
            <span key={p.id} className="inline-flex items-center gap-1">
              {i > 0 ? <ChevronRightIcon className="h-3 w-3 text-[#9fb0a3]" /> : null}
              <span className={i === path.length - 1 ? "font-semibold text-[#1D4E35]" : ""}>{p.nome}</span>
            </span>
          ))}
        </nav>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <h3 className="font-serif text-[20px] font-semibold">{unit.nome}</h3>
          <TypeChip tipo={unit.tipo} />
          <SourceBadge source={unit.source} legacyTeamId={unit.legacy_team_id} />
        </div>
      </div>

      <div className="rounded-2xl border border-[#bcd9bf] bg-[#eef7ef] p-3.5">
        <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#5f6d61]">Responsabile unità</div>
        {responsabile ? (
          <div className="mt-2 flex items-center gap-3">
            <Avatar name={responsabile.full_name ?? responsabile.username} size={42} />
            <div className="min-w-0">
              <div className="text-[14px] font-semibold">{responsabile.full_name ?? responsabile.username}</div>
              <div className="text-[12px] text-[#3a4a3f]">{responsabile_title ?? "—"}</div>
              <div className="text-[11px] text-[#5f6d61]">{responsabile.email}</div>
            </div>
          </div>
        ) : (
          <div className="mt-2 text-[12.5px] text-[#5f6d61]">Nessun responsabile assegnato a questa unità.</div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className="rounded-2xl border border-[#e6ebe5] bg-white p-3">
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#5f6d61]">Assegnazioni dirette</div>
          <div className="mt-2 text-[24px] font-semibold text-[#051b12]">{directAssignments.length}</div>
        </div>
        <div className="rounded-2xl border border-[#e6ebe5] bg-white p-3">
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#5f6d61]">Persone nel sotto-albero</div>
          <div className="mt-2 text-[24px] font-semibold text-[#051b12]">{subtreeAssignments.length}</div>
        </div>
        <div className="rounded-2xl border border-[#e6ebe5] bg-white p-3">
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#5f6d61]">Sotto-unità dirette</div>
          <div className="mt-2 text-[24px] font-semibold text-[#051b12]">{summary.subtreeChildUnits.length}</div>
        </div>
      </div>

      {reference ? (
        <div className="rounded-2xl border border-[#d6dfef] bg-[#f7f9fd] p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#5f6d61]">Riferimento consorzio 2026</div>
              <div className="mt-1 text-[14px] font-semibold text-[#10233e]">{reference.title}</div>
              <div className="text-[12px] text-[#5c6d82]">{reference.sourceLabel}</div>
            </div>
            <Pill className="border-[#c4d3ea] bg-white text-[#2f5da8]">atteso {reference.totalHeadcount} addetti</Pill>
          </div>
          <div className="mt-3 grid grid-cols-1 gap-2.5 xl:grid-cols-2">
            {reference.rows.map((row) => {
              const actual = actualByChildLabel.get(normalizeLabel(row.label)) ?? 0;
              const delta = actual - row.expectedHeadcount;
              return (
                <div key={row.label} className="rounded-xl border border-[#dbe4f1] bg-white p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="text-[13px] font-semibold text-[#10233e]">{row.label}</div>
                      {row.note ? <div className="mt-0.5 text-[11.5px] text-[#5c6d82]">{row.note}</div> : null}
                    </div>
                    <Pill className="border-[#e6ebe5] bg-[#fbfcfa] text-[#3a4a3f]">attesi {row.expectedHeadcount}</Pill>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-2 text-[12px]">
                    <Pill className="border-[#d5e2d8] bg-[#edf5f0] text-[#1D4E35]">attuali {actual}</Pill>
                    <Pill className={delta === 0 ? "border-[#bfe5d6] bg-[#e0f3ec] text-[#0f6a4e]" : delta > 0 ? "border-[#e7c89a] bg-[#fdf3e3] text-[#b45309]" : "border-[#e6d3d3] bg-[#fdf2f2] text-[#9a3b3b]"}>
                      delta {delta > 0 ? `+${delta}` : delta}
                    </Pill>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}

      <div>
        <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-[#5f6d61]">Persone assegnate direttamente · {directAssignments.length}</div>
        {directAssignments.length ? (
          <div className="grid grid-cols-1 gap-2.5 xl:grid-cols-2">
            {directAssignments.map((a) => <PersonCard key={a.id} assignment={a} onOpen={onOpenPerson} />)}
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-[#d8e3d9] bg-[#fafdf9] p-6 text-center text-[12.5px] text-[#5f6d61]">Nessuna persona assegnata direttamente.</div>
        )}
      </div>

      {subtreeAssignments.length > directAssignments.length ? (
        <div>
          <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-[#5f6d61]">
            Copertura del sotto-albero · {subtreeAssignments.length - directAssignments.length} persone nelle sotto-unità
          </div>
          <div className="rounded-xl border border-[#e6ebe5] bg-white p-3 text-[12.5px] text-[#3a4a3f]">
            Questa unità governa anche <strong>{subtreeAssignments.length - directAssignments.length}</strong> persone assegnate ai nodi figli.
            Usa il riquadro di riferimento e l&apos;albero a sinistra per confrontare rapidamente la distribuzione.
          </div>
        </div>
      ) : null}
    </div>
  );
}

// --------------------------------------------------------------------------- //
function OverridePanel({ overrides, canManage, onAdd }: { overrides: OrgVisibilityOverride[]; canManage: boolean; onAdd: () => void }) {
  return (
    <section className="rounded-2xl border border-[#ecd6ac] bg-gradient-to-b from-[#fffdf8] to-[#fdf6e9] p-4 shadow-[0_14px_40px_rgba(180,83,9,0.06)]">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-start gap-2.5">
          <span className="mt-0.5 flex h-8 w-8 items-center justify-center rounded-lg bg-[#fdebd0] text-[#b45309]"><ShieldIcon className="h-4 w-4" /></span>
          <div>
            <h2 className="font-serif text-[16px] font-semibold text-[#7c3d06]">Override di visibilità</h2>
            <p className="text-[12px] text-[#9a6a2f]">Eccezioni controllate, tenute <strong>separate</strong> dall&apos;albero canonico. Rule-based, non ruoli RBAC.</p>
          </div>
        </div>
        {canManage ? (
          <button type="button" onClick={onAdd} className="inline-flex items-center gap-1.5 rounded-xl border border-[#e7c89a] bg-white px-3 py-2 text-[12.5px] font-semibold text-[#b45309] transition-colors hover:bg-[#fdf3e3]">
            + Aggiungi eccezione
          </button>
        ) : null}
      </header>

      {!canManage ? (
        <p className="mt-3 text-[12.5px] text-[#9a6a2f]">Le eccezioni sono visibili solo a chi gestisce l&apos;organigramma (organigramma.manage).</p>
      ) : overrides.length === 0 ? (
        <p className="mt-3 text-[12.5px] text-[#9a6a2f]">Nessuna eccezione configurata.</p>
      ) : (
        <ul className="mt-3 flex flex-col gap-2.5">
          {overrides.map((o) => (
            <li key={o.id} className={cn("rounded-xl border bg-white/70 p-3", o.status === "scaduto" || o.status === "disattivato" ? "border-[#e2e2e2] opacity-80" : "border-[#f0ddba]")}>
              <div className="flex flex-wrap items-center gap-2">
                <Avatar name={o.viewer?.full_name ?? o.viewer?.username ?? "?"} size={28} tone="amber" />
                <span className="text-[13px] font-semibold">{o.viewer?.full_name ?? o.viewer?.username ?? `#${o.viewer_user_id}`}</span>
                <span className="text-[#b45309]">→</span>
                <span className="text-[12.5px] font-medium text-[#3a4a3f]">{o.target_label ?? (o.target_type === "org_unit" ? "unità" : "utente")}</span>
                <Pill className="border-[#e7c89a] bg-[#fdf3e3] text-[#b45309]">scope: {SCOPE_LABEL[o.scope]}</Pill>
                {o.status ? <Pill className={OVERRIDE_STATUS_PILL[o.status]}>{o.status}</Pill> : null}
              </div>
              <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-[11.5px] text-[#9a6a2f]">
                <span className="italic text-[#7c3d06]">{o.motivo ? `“${o.motivo}”` : ""}</span>
                <span>{formatDate(o.valid_from)} → {o.valid_to ? formatDate(o.valid_to) : "senza scadenza"}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

// --------------------------------------------------------------------------- //
function WhoSeesWho({
  users,
  simUserId,
  onPick,
  visibility,
  onOpenPerson,
}: {
  users: ApplicationUser[];
  simUserId: number | null;
  onPick: (id: number) => void;
  visibility: OrgVisibilityResult | null;
  onOpenPerson: (id: number) => void;
}) {
  const overrideCount = visibility?.units.filter((u) => u.via === "override").length ?? 0;
  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-[320px_minmax(0,1fr)]">
      <div className="rounded-2xl border border-[#e6ebe5] bg-gradient-to-b from-white to-[#fbfcfa] p-4 shadow-[0_14px_40px_rgba(15,23,42,0.06)]">
        <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#5f6d61]">Simula la visibilità di</div>
        <div className="mt-3 flex max-h-[60vh] flex-col gap-1.5 overflow-y-auto">
          {users.map((u) => (
            <button
              key={u.id}
              type="button"
              onClick={() => onPick(u.id)}
              className={cn("flex items-center gap-2.5 rounded-xl border px-2.5 py-2 text-left transition-colors", u.id === simUserId ? "border-[#1D4E35] bg-[#D3EAD4]" : "border-transparent hover:border-[#e6ebe5] hover:bg-[#f5f9f4]")}
            >
              <Avatar name={u.full_name ?? u.username} size={30} />
              <span className="min-w-0">
                <span className="block truncate text-[12.5px] font-semibold">{u.full_name ?? u.username}</span>
                <span className="block truncate text-[11px] text-[#5f6d61]">{u.role}</span>
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-4">
        {visibility ? (
          <>
            <div className="rounded-2xl border border-[#e6ebe5] bg-gradient-to-b from-white to-[#fbfcfa] p-4 shadow-[0_14px_40px_rgba(15,23,42,0.06)]">
              <div className="flex flex-wrap items-center gap-3">
                <Avatar name={visibility.viewer.full_name ?? visibility.viewer.username} size={44} />
                <div className="min-w-0">
                  <div className="font-serif text-[18px] font-semibold">{visibility.viewer.full_name ?? visibility.viewer.username}</div>
                  <div className="text-[12px] text-[#5f6d61]">{visibility.full ? "super_admin · vede l'intera struttura" : `RBAC: ${visibility.viewer.rbac_role}`}</div>
                </div>
              </div>
              <div className="mt-4 grid grid-cols-3 gap-3">
                <Metric value={visibility.units.length} label="Unità visibili" tone="green" />
                <Metric value={overrideCount} label="da Override" tone="amber" />
                <Metric value={visibility.people.length} label="Persone visibili" tone="teal" />
              </div>
              <div className="mt-4 flex flex-wrap items-center gap-4 text-[11.5px] text-[#5f6d61]">
                <span className="inline-flex items-center gap-1.5"><span className="h-3 w-3 rounded-full border border-[#bcd9bf] bg-[#D3EAD4]" /> Da gerarchia (cascata)</span>
                <span className="inline-flex items-center gap-1.5"><span className="h-3 w-3 rounded-full border border-[#e7c89a] bg-[#fdebd0]" /> Da override (eccezione)</span>
              </div>
            </div>

            <div className="rounded-2xl border border-[#e6ebe5] bg-white p-4">
              <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#5f6d61]">Insieme effettivo di unità</div>
              {visibility.units.length ? (
                <ul className="mt-3 flex flex-col gap-1.5">
                  {visibility.units.map((u) => (
                    <li key={u.org_unit_id} className={cn("flex flex-wrap items-center gap-2 rounded-xl border px-3 py-2", u.via === "override" ? "border-[#f0ddba] bg-[#fffdf8]" : "border-[#dceadf] bg-[#f3faf5]")}>
                      <span className="h-2.5 w-2.5 rounded-full" style={{ background: u.via === "override" ? "#e7a93f" : "#1D9E75" }} />
                      <span className="text-[13px] font-semibold">{u.nome}</span>
                      <TypeChip tipo={u.tipo} />
                      {u.via === "override" ? (
                        <Pill className="border-[#e7c89a] bg-[#fdf3e3] text-[#b45309]">override{u.scope ? ` · ${SCOPE_LABEL[u.scope]}` : ""}</Pill>
                      ) : (
                        <Pill className="border-[#bfe5d6] bg-[#e0f3ec] text-[#0f6a4e]">gerarchia</Pill>
                      )}
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="mt-3 rounded-xl border border-dashed border-[#d8e3d9] bg-[#fafdf9] p-6 text-center text-[12.5px] text-[#5f6d61]">Nessun perimetro gerarchico né override attivi.</div>
              )}
            </div>

            <div className="rounded-2xl border border-[#e6ebe5] bg-white p-4">
              <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#5f6d61]">Persone visibili · {visibility.people.length}</div>
              <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
                {visibility.people.map((p) => (
                  <button
                    key={p.user_id}
                    type="button"
                    onClick={() => onOpenPerson(p.user_id)}
                    className={cn("flex items-center gap-2.5 rounded-xl border px-2.5 py-2 text-left transition-colors hover:shadow-[0_8px_24px_rgba(15,23,42,0.06)]", p.via === "override" ? "border-[#f0ddba] bg-[#fffdf8]" : "border-[#e6ebe5] bg-white")}
                  >
                    <Avatar name={p.full_name} size={30} tone={p.via === "override" ? "amber" : "green"} />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[12.5px] font-semibold">{p.full_name ?? `#${p.user_id}`}</span>
                      <span className="block truncate text-[11px] text-[#5f6d61]">{p.title ?? "—"}</span>
                    </span>
                    <span className={cn("h-2 w-2 shrink-0 rounded-full", p.via === "override" ? "bg-[#e7a93f]" : "bg-[#1D9E75]")} />
                  </button>
                ))}
              </div>
            </div>
          </>
        ) : (
          <div className="rounded-2xl border border-[#e6ebe5] bg-white p-8 text-center text-[12.5px] text-[#5f6d61]">Seleziona un utente per calcolarne la visibilità effettiva.</div>
        )}
      </div>
    </div>
  );
}

function Metric({ value, label, tone }: { value: number; label: string; tone: "green" | "amber" | "teal" }) {
  const map = {
    green: "border-[#bcd9bf] bg-[#eef7ef] text-[#1D4E35]",
    amber: "border-[#e7c89a] bg-[#fdf3e3] text-[#b45309]",
    teal: "border-[#bfe5e0] bg-[#e2f4f1] text-[#0d7a66]",
  } as const;
  return (
    <div className={cn("rounded-xl border p-3", map[tone])}>
      <div className="font-serif text-[24px] font-semibold leading-none">{value}</div>
      <div className="mt-1 text-[11px] font-medium">{label}</div>
    </div>
  );
}

// --------------------------------------------------------------------------- //
function AddOverrideModal({
  users,
  units,
  onClose,
  onCreate,
}: {
  users: ApplicationUser[];
  units: OrgUnitTreeNode[];
  onClose: () => void;
  onCreate: (payload: OrgVisibilityOverrideCreateInput) => Promise<void>;
}) {
  const [viewerUserId, setViewerUserId] = useState<number | "">(users[0]?.id ?? "");
  const [targetType, setTargetType] = useState<"user" | "org_unit">("org_unit");
  const [targetOrgUnitId, setTargetOrgUnitId] = useState<string>(units[0]?.id ?? "");
  const [targetUserId, setTargetUserId] = useState<number | "">(users[0]?.id ?? "");
  const [scope, setScope] = useState<OrgOverrideScope>("read");
  const [motivo, setMotivo] = useState("");
  const [validFrom, setValidFrom] = useState("");
  const [validTo, setValidTo] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const inputCls = "w-full rounded-xl border border-[#e6ebe5] bg-[#fbfcfa] px-3 py-2 text-[13px] outline-none focus:border-[#1D9E75] focus:ring-2 focus:ring-[#1D9E75]/30";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (viewerUserId === "") return;
    setSaving(true);
    setErr(null);
    try {
      await onCreate({
        viewer_user_id: Number(viewerUserId),
        target_type: targetType,
        target_org_unit_id: targetType === "org_unit" ? targetOrgUnitId : null,
        target_user_id: targetType === "user" ? Number(targetUserId) : null,
        scope,
        motivo: motivo || null,
        valid_from: validFrom ? new Date(validFrom).toISOString() : null,
        valid_to: validTo ? new Date(validTo).toISOString() : null,
      });
    } catch (error) {
      setErr(error instanceof Error ? error.message : "Errore");
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-[#051b12]/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-md rounded-2xl border border-[#ecd6ac] bg-white p-5 shadow-[0_24px_70px_rgba(15,23,42,0.25)]">
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#fdebd0] text-[#b45309]"><ShieldIcon className="h-4 w-4" /></span>
          <h3 className="font-serif text-[16px] font-semibold text-[#7c3d06]">Nuova eccezione di visibilità</h3>
        </div>
        <form className="mt-4 flex flex-col gap-3" onSubmit={submit}>
          <label className="flex flex-col gap-1">
            <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#5f6d61]">Viewer (utente)</span>
            <select className={inputCls} value={viewerUserId} onChange={(e) => setViewerUserId(Number(e.target.value))}>
              {users.map((u) => <option key={u.id} value={u.id}>{u.full_name ?? u.username}</option>)}
            </select>
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="flex flex-col gap-1">
              <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#5f6d61]">Tipo target</span>
              <select className={inputCls} value={targetType} onChange={(e) => setTargetType(e.target.value as "user" | "org_unit")}>
                <option value="org_unit">Unità organizzativa</option>
                <option value="user">Utente</option>
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#5f6d61]">Scope</span>
              <select className={inputCls} value={scope} onChange={(e) => setScope(e.target.value as OrgOverrideScope)}>
                <option value="read">Lettura</option>
                <option value="approve">Approvazione</option>
                <option value="full">Completo</option>
              </select>
            </label>
          </div>
          <label className="flex flex-col gap-1">
            <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#5f6d61]">Target</span>
            {targetType === "org_unit" ? (
              <select className={inputCls} value={targetOrgUnitId} onChange={(e) => setTargetOrgUnitId(e.target.value)}>
                {units.map((u) => <option key={u.id} value={u.id}>{u.nome}</option>)}
              </select>
            ) : (
              <select className={inputCls} value={targetUserId} onChange={(e) => setTargetUserId(Number(e.target.value))}>
                {users.map((u) => <option key={u.id} value={u.id}>{u.full_name ?? u.username}</option>)}
              </select>
            )}
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#5f6d61]">Motivo</span>
            <input className={inputCls} value={motivo} onChange={(e) => setMotivo(e.target.value)} placeholder="Es. Sostituzione ferie" />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="flex flex-col gap-1">
              <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#5f6d61]">Valido da</span>
              <input type="date" className={inputCls} value={validFrom} onChange={(e) => setValidFrom(e.target.value)} />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#5f6d61]">Valido fino a</span>
              <input type="date" className={inputCls} value={validTo} onChange={(e) => setValidTo(e.target.value)} />
            </label>
          </div>
          {err ? <p className="text-[12px] text-[#ba1a1a]">{err}</p> : null}
          <div className="mt-1 flex items-center justify-end gap-2">
            <button type="button" onClick={onClose} className="rounded-xl border border-[#e6ebe5] px-3.5 py-2 text-[12.5px] font-medium text-[#3a4a3f] hover:bg-[#f5f9f4]">Annulla</button>
            <button type="submit" disabled={saving} className="rounded-xl bg-[#b45309] px-3.5 py-2 text-[12.5px] font-semibold text-white hover:bg-[#9a4708] disabled:opacity-60">{saving ? "Salvataggio…" : "Crea eccezione"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

// --------------------------------------------------------------------------- //
function PersonDrawer({
  token,
  userId,
  overrides,
  units,
  onClose,
}: {
  token: string | null;
  userId: number;
  overrides: OrgVisibilityOverride[];
  units: OrgUnitTreeNode[];
  onClose: () => void;
}) {
  const [assignments, setAssignments] = useState<OrgAssignment[] | null>(null);

  useEffect(() => {
    if (!token) return;
    let active = true;
    void getOrgAssignments(token, { userId })
      .then((a) => {
        if (active) setAssignments(a);
      })
      .catch(() => {
        if (active) setAssignments([]);
      });
    return () => {
      active = false;
    };
  }, [token, userId]);

  const primary = assignments?.[0];
  const person = primary?.person;
  const unitsById = useMemo(() => new Map(units.map((u) => [u.id, u])), [units]);

  const path = useMemo(() => (primary ? unitPath(primary.org_unit_id, units) : []), [primary, units]);
  const ancestorIds = useMemo(() => new Set(path.map((p) => p.id)), [path]);

  const outgoing = overrides.filter((o) => o.viewer_user_id === userId);
  const incoming = overrides.filter(
    (o) =>
      (o.target_type === "user" && o.target_user_id === userId) ||
      (o.target_type === "org_unit" && o.target_org_unit_id != null && ancestorIds.has(o.target_org_unit_id)),
  );

  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-[#051b12]/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative flex h-full w-full max-w-md flex-col overflow-y-auto border-l border-[#e6ebe5] bg-gradient-to-b from-white to-[#fbfcfa] shadow-[0_0_60px_rgba(15,23,42,0.2)]">
        <div className="sticky top-0 z-10 flex items-start justify-between gap-3 border-b border-[#e6ebe5] bg-white/90 p-4 backdrop-blur">
          <div className="flex items-center gap-3">
            <Avatar name={person?.full_name ?? `#${userId}`} size={46} />
            <div>
              <h3 className="font-serif text-[18px] font-semibold">{person?.full_name ?? person?.username ?? `Utente #${userId}`}</h3>
              <div className="text-[12px] text-[#5f6d61]">{person?.email ?? ""}</div>
            </div>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg p-1 text-[#5f6d61] hover:bg-[#f3f3f3]" aria-label="Chiudi">✕</button>
        </div>

        <div className="flex flex-col gap-4 p-4">
          {assignments == null ? (
            <div className="text-[12.5px] text-[#5f6d61]">Caricamento…</div>
          ) : (
            <>
              <section className="rounded-2xl border border-[#e6ebe5] bg-white p-3.5">
                <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#5f6d61]">Assegnazioni · {assignments.length}</div>
                {assignments.length ? (
                  <ul className="mt-2 flex flex-col gap-2">
                    {assignments.map((a) => (
                      <li key={a.id} className="rounded-xl border border-[#e6ebe5] p-2.5 text-[12.5px]">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold">{unitsById.get(a.org_unit_id)?.nome ?? a.org_unit_id}</span>
                          <StatusBadge active={a.active} />
                        </div>
                        <div className="mt-1 text-[#3a4a3f]">{a.title ?? "—"}</div>
                        <div className="mt-0.5 text-[11.5px] text-[#5f6d61]">
                          {a.manager ? <>riporta a {a.manager.full_name ?? a.manager.username}</> : "vertice"}
                        </div>
                        <div className="mt-1.5"><SourceBadge source={a.source} /></div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="mt-2 text-[12.5px] text-[#5f6d61]">Nessuna assegnazione.</div>
                )}
              </section>

              {path.length ? (
                <section className="rounded-2xl border border-[#e6ebe5] bg-white p-3.5">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#5f6d61]">Percorso organizzativo</div>
                  <div className="mt-2 flex flex-wrap items-center gap-1 text-[12px] text-[#1D4E35]">
                    {path.map((p, i) => (
                      <span key={p.id} className="inline-flex items-center gap-1">
                        {i > 0 ? <ChevronRightIcon className="h-3 w-3 text-[#9fb0a3]" /> : null}
                        <span className={i === path.length - 1 ? "font-semibold" : ""}>{p.nome}</span>
                      </span>
                    ))}
                  </div>
                </section>
              ) : null}

              <OverrideMini title="Override in uscita (è viewer)" items={outgoing} empty="Nessuna eccezione assegnata." render={(o) => o.target_label ?? ""} />
              <OverrideMini title="Override in entrata (la riguardano)" items={incoming} empty="Nessuna eccezione la riguarda." render={(o) => `da ${o.viewer?.full_name ?? o.viewer?.username ?? "?"}`} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function OverrideMini({ title, items, empty, render }: { title: string; items: OrgVisibilityOverride[]; empty: string; render: (o: OrgVisibilityOverride) => string }) {
  return (
    <section className="rounded-2xl border border-[#f0ddba] bg-[#fffdf8] p-3.5">
      <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#9a6a2f]">{title}</div>
      {items.length ? (
        <ul className="mt-2 flex flex-col gap-2">
          {items.map((o) => (
            <li key={o.id} className="flex flex-wrap items-center gap-2 text-[12px] text-[#7c3d06]">
              {o.status ? <Pill className={OVERRIDE_STATUS_PILL[o.status]}>{o.status}</Pill> : null}
              <span className="font-medium">{render(o)}</span>
              <Pill className="border-[#e7c89a] bg-[#fdf3e3] text-[#b45309]">{SCOPE_LABEL[o.scope]}</Pill>
              {o.motivo ? <span className="italic text-[#9a6a2f]">“{o.motivo}”</span> : null}
            </li>
          ))}
        </ul>
      ) : (
        <div className="mt-2 text-[12px] text-[#9a6a2f]">{empty}</div>
      )}
    </section>
  );
}
