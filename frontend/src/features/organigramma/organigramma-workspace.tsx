"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

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
  createOrgAssignment,
  createOrgUnit,
  deleteOrgAssignment,
  exportOrganigrammaSnapshot,
  getCurrentUser,
  getOrgAssignments,
  getOrgOverrides,
  getOrgTree,
  getOrgUnit,
  getOrgVisibility,
  importOrganigrammaSnapshot,
  isAuthError,
  listAllApplicationUsers,
  syncOrgWhiteCompany,
  updateOrgUnit,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { cn } from "@/lib/cn";
import { computeTreeInclusion, filterTreeByRootIds, flattenTree, unitPath } from "@/lib/organigramma";
import type {
  ApplicationUser,
  CurrentUser,
  OrgAssignment,
  OrgAssignmentCreateInput,
  OrganigrammaSnapshot,
  OrgOverrideScope,
  OrgOverrideStatus,
  OrgImportMode,
  OrgSource,
  OrgUnitCreateInput,
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

type SchemaDisplayPosition = {
  x: number;
  y: number;
};

type UserDropMode = "member" | "lead";
type SchemaOrientation = "vertical" | "horizontal";
type ImportSnapshotAnalysis = {
  units: number;
  assignments: number;
  overrides: number;
  schemaVersion: number | null;
  errors: string[];
  warnings: string[];
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

const SCHEMA_NODE_WIDTH = 246;
const SCHEMA_NODE_HEIGHT = 188;
const SCHEMA_CANVAS_PADDING = 120;
const SCHEMA_GRID_SIZE = 24;
const SCHEMA_LAYER_X_GAP = 340;
const SCHEMA_LAYER_Y_GAP = 72;
const QUICK_SECTOR_LIMIT = 10;
// Above this number of visible blocks the schema auto-groups deep levels.
const SCHEMA_AUTO_GROUP_THRESHOLD = 12;
// Levels always expanded by the auto-grouping (roots + their children).
const SCHEMA_AUTO_GROUP_DEPTH = 1;

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

function analyzeOrganigrammaSnapshot(snapshot: OrganigrammaSnapshot): ImportSnapshotAnalysis {
  const units = snapshot.units ?? [];
  const assignments = snapshot.assignments ?? [];
  const overrides = snapshot.overrides ?? [];
  const unitIds = new Set(units.map((unit) => unit.id));
  const errors: string[] = [];
  const warnings: string[] = [];

  const duplicateIds = (values: string[]): string[] =>
    [...new Set(values.filter((value, index) => values.indexOf(value) !== index))];

  const duplicateUnitIds = duplicateIds(units.map((unit) => unit.id));
  if (duplicateUnitIds.length) {
    errors.push(`ID unità duplicati: ${duplicateUnitIds.slice(0, 3).join(", ")}${duplicateUnitIds.length > 3 ? "…" : ""}`);
  }

  const orphanParents = units.filter((unit) => unit.parent_id && !unitIds.has(unit.parent_id));
  if (orphanParents.length) {
    errors.push(`${orphanParents.length} unità con parent_id non presente nello snapshot.`);
  }

  const assignmentMissingUnits = assignments.filter((assignment) => !unitIds.has(assignment.org_unit_id));
  if (assignmentMissingUnits.length) {
    errors.push(`${assignmentMissingUnits.length} assegnazioni puntano a unità mancanti.`);
  }

  const overrideMissingUnits = overrides.filter(
    (override) => override.target_type === "org_unit" && override.target_org_unit_id && !unitIds.has(override.target_org_unit_id),
  );
  if (overrideMissingUnits.length) {
    errors.push(`${overrideMissingUnits.length} override puntano a unità mancanti.`);
  }

  const rootUnits = units.filter((unit) => unit.parent_id == null);
  if (rootUnits.length === 0 && units.length > 0) {
    warnings.push("Nessuna unità radice trovata nel file.");
  }
  if (rootUnits.length > 1) {
    warnings.push(`Il file contiene ${rootUnits.length} radici distinte.`);
  }

  const inactiveAssignments = assignments.filter((assignment) => assignment.active === false).length;
  if (inactiveAssignments > 0) {
    warnings.push(`${inactiveAssignments} assegnazioni risultano già inattive nel file.`);
  }

  return {
    units: units.length,
    assignments: assignments.length,
    overrides: overrides.length,
    schemaVersion: snapshot.schema_version ?? null,
    errors,
    warnings,
  };
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

function safeCanvasCoord(value: number | null | undefined): number {
  return Number.isFinite(value) ? Number(value) : 0;
}

function pruneCollapsedTree(nodes: OrgUnitTreeNode[], collapsedIds: Set<string>): OrgUnitTreeNode[] {
  if (!collapsedIds.size) return nodes;
  return nodes.map((node) =>
    collapsedIds.has(node.id)
      ? { ...node, children: [] }
      : { ...node, children: pruneCollapsedTree(node.children, collapsedIds) },
  );
}

// MyHeritage-like auto grouping: when the visible tree is large, every node
// below SCHEMA_AUTO_GROUP_DEPTH that has children starts collapsed. Expanding
// a group reveals one more level (whose own groups stay collapsed).
function computeAutoCollapsedIds(nodes: OrgUnitTreeNode[]): Set<string> {
  const collapsed = new Set<string>();
  if (flattenTree(nodes).length <= SCHEMA_AUTO_GROUP_THRESHOLD) return collapsed;
  const visit = (level: OrgUnitTreeNode[], depth: number) => {
    for (const node of level) {
      if (depth >= SCHEMA_AUTO_GROUP_DEPTH && node.children.length) {
        collapsed.add(node.id);
      }
      visit(node.children, depth + 1);
    }
  };
  visit(nodes, 0);
  return collapsed;
}

function computeSchemaDisplayPositions(flatNodes: OrgUnitTreeNode[]): Map<string, SchemaDisplayPosition> {
  return new Map(
    flatNodes.map((node) => [
      node.id,
      { x: safeCanvasCoord(node.canvas_x), y: safeCanvasCoord(node.canvas_y) },
    ]),
  );
}

function computeSchemaCanvasBounds(
  flatNodes: OrgUnitTreeNode[],
  positions: Map<string, SchemaDisplayPosition>,
) {
  if (!flatNodes.length) {
    return {
      width: 1600,
      height: 900,
      offsetX: 0,
      offsetY: 0,
    };
  }
  const xs = flatNodes.map((node) => positions.get(node.id)?.x ?? safeCanvasCoord(node.canvas_x));
  const ys = flatNodes.map((node) => positions.get(node.id)?.y ?? safeCanvasCoord(node.canvas_y));
  const minX = Math.min(...xs);
  const minY = Math.min(...ys);
  const maxX = Math.max(...xs);
  const maxY = Math.max(...ys);
  const offsetX = minX < SCHEMA_CANVAS_PADDING ? SCHEMA_CANVAS_PADDING - minX : 0;
  const offsetY = minY < SCHEMA_CANVAS_PADDING ? SCHEMA_CANVAS_PADDING - minY : 0;
  return {
    width: maxX + offsetX + SCHEMA_NODE_WIDTH + SCHEMA_CANVAS_PADDING,
    height: maxY + offsetY + SCHEMA_NODE_HEIGHT + SCHEMA_CANVAS_PADDING,
    offsetX,
    offsetY,
  };
}

function computeHorizontalTreeLayout(tree: OrgUnitTreeNode[]): Map<string, { x: number; y: number }> {
  const positions = new Map<string, { x: number; y: number }>();
  const rootSpacing = SCHEMA_NODE_HEIGHT + SCHEMA_LAYER_Y_GAP * 2;
  const verticalStep = SCHEMA_NODE_HEIGHT + SCHEMA_LAYER_Y_GAP;
  const baseX = 120;
  let cursorY = 120;

  const walk = (node: OrgUnitTreeNode, depth: number, startY: number): { nextY: number; centerY: number } => {
    const x = baseX + depth * SCHEMA_LAYER_X_GAP;
    if (!node.children.length) {
      positions.set(node.id, { x, y: startY });
      return {
        nextY: startY + verticalStep,
        centerY: startY + SCHEMA_NODE_HEIGHT / 2,
      };
    }

    let childCursorY = startY;
    const childCenters: number[] = [];

    for (const child of node.children) {
      const childLayout = walk(child, depth + 1, childCursorY);
      childCursorY = childLayout.nextY;
      childCenters.push(childLayout.centerY);
    }

    const centerY = childCenters.length === 1
      ? childCenters[0]
      : (childCenters[0] + childCenters[childCenters.length - 1]) / 2;
    const y = Math.max(120, Math.round(centerY - SCHEMA_NODE_HEIGHT / 2));
    positions.set(node.id, { x, y });

    return {
      nextY: Math.max(childCursorY, y + verticalStep),
      centerY,
    };
  };

  for (const root of tree) {
    const rootLayout = walk(root, 0, cursorY);
    cursorY = rootLayout.nextY + rootSpacing;
  }

  return positions;
}

function computeVerticalTreeLayout(tree: OrgUnitTreeNode[]): Map<string, { x: number; y: number }> {
  const positions = new Map<string, { x: number; y: number }>();
  const rootSpacing = SCHEMA_NODE_WIDTH + SCHEMA_LAYER_X_GAP / 2;
  const horizontalStep = SCHEMA_NODE_WIDTH + SCHEMA_LAYER_X_GAP / 2;
  const verticalStep = SCHEMA_NODE_HEIGHT + SCHEMA_LAYER_Y_GAP;
  const baseY = 120;
  let cursorX = 120;

  const walk = (node: OrgUnitTreeNode, depth: number, startX: number): { nextX: number; centerX: number } => {
    const y = baseY + depth * verticalStep;
    if (!node.children.length) {
      positions.set(node.id, { x: startX, y });
      return {
        nextX: startX + horizontalStep,
        centerX: startX + SCHEMA_NODE_WIDTH / 2,
      };
    }

    let childCursorX = startX;
    const childCenters: number[] = [];

    for (const child of node.children) {
      const childLayout = walk(child, depth + 1, childCursorX);
      childCursorX = childLayout.nextX;
      childCenters.push(childLayout.centerX);
    }

    const centerX = childCenters.length === 1
      ? childCenters[0]
      : (childCenters[0] + childCenters[childCenters.length - 1]) / 2;
    const x = Math.max(120, Math.round(centerX - SCHEMA_NODE_WIDTH / 2));
    positions.set(node.id, { x, y });

    return {
      nextX: Math.max(childCursorX, x + horizontalStep),
      centerX,
    };
  };

  for (const root of tree) {
    const rootLayout = walk(root, 0, cursorX);
    cursorX = rootLayout.nextX + rootSpacing;
  }

  return positions;
}

function updateTreeNodeInForest(
  nodes: OrgUnitTreeNode[],
  nodeId: string,
  patch: Partial<Pick<OrgUnitTreeNode, "parent_id" | "canvas_x" | "canvas_y">>,
): OrgUnitTreeNode[] {
  return nodes.map((node) => {
    if (node.id === nodeId) {
      return { ...node, ...patch };
    }
    if (!node.children.length) {
      return node;
    }
    return {
      ...node,
      children: updateTreeNodeInForest(node.children, nodeId, patch),
    };
  });
}

function applyCanvasPositionsToForest(
  nodes: OrgUnitTreeNode[],
  positions: Map<string, SchemaDisplayPosition>,
): OrgUnitTreeNode[] {
  return nodes.map((node) => {
    const position = positions.get(node.id);
    const nextNode: OrgUnitTreeNode = position
      ? { ...node, canvas_x: position.x, canvas_y: position.y }
      : node;
    if (!node.children.length) {
      return nextNode;
    }
    return {
      ...nextNode,
      children: applyCanvasPositionsToForest(node.children, positions),
    };
  });
}

function rectsOverlap(
  leftA: number,
  topA: number,
  leftB: number,
  topB: number,
  width: number,
  height: number,
  gutterX = 0,
  gutterY = 0,
): boolean {
  return !(
    leftA + width + gutterX <= leftB
    || leftB + width + gutterX <= leftA
    || topA + height + gutterY <= topB
    || topB + height + gutterY <= topA
  );
}

function resolveSubtreeCollisionShift(
  subtreePositions: Map<string, SchemaDisplayPosition>,
  occupiedPositions: SchemaDisplayPosition[],
  orientation: SchemaOrientation,
): { x: number; y: number } {
  if (!subtreePositions.size || !occupiedPositions.length) {
    return { x: 0, y: 0 };
  }

  const subtreeEntries = [...subtreePositions.values()];
  const primaryStep = orientation === "horizontal" ? SCHEMA_NODE_WIDTH + 56 : SCHEMA_NODE_WIDTH + 40;
  const secondaryStep = orientation === "horizontal" ? SCHEMA_NODE_HEIGHT + 36 : SCHEMA_NODE_HEIGHT + 48;
  const gutterX = 28;
  const gutterY = 24;

  const hasCollision = (shiftX: number, shiftY: number): boolean =>
    subtreeEntries.some((entry) =>
      occupiedPositions.some((occupied) =>
        rectsOverlap(
          entry.x + shiftX,
          entry.y + shiftY,
          occupied.x,
          occupied.y,
          SCHEMA_NODE_WIDTH,
          SCHEMA_NODE_HEIGHT,
          gutterX,
          gutterY,
        ),
      ),
    );

  if (!hasCollision(0, 0)) {
    return { x: 0, y: 0 };
  }

  for (let primaryIndex = 1; primaryIndex <= 24; primaryIndex += 1) {
    const primaryShift = primaryStep * primaryIndex;
    const primaryCandidate = orientation === "horizontal"
      ? { x: primaryShift, y: 0 }
      : { x: primaryShift, y: 0 };
    if (!hasCollision(primaryCandidate.x, primaryCandidate.y)) {
      return primaryCandidate;
    }

    for (let secondaryIndex = 1; secondaryIndex <= 8; secondaryIndex += 1) {
      const secondaryShift = secondaryStep * secondaryIndex;
      const candidates = orientation === "horizontal"
        ? [
            { x: primaryShift, y: secondaryShift },
            { x: primaryShift, y: -secondaryShift },
          ]
        : [
            { x: primaryShift, y: secondaryShift },
            { x: -primaryShift, y: secondaryShift },
          ];
      for (const candidate of candidates) {
        if (!hasCollision(candidate.x, candidate.y)) {
          return candidate;
        }
      }
    }
  }

  return orientation === "horizontal"
    ? { x: primaryStep * 8, y: 0 }
    : { x: primaryStep * 6, y: secondaryStep * 2 };
}

function defaultLeadTitle(tipo: OrgUnitType): string {
  switch (tipo) {
    case "direzione":
      return "Direttore";
    case "distretto":
      return "Responsabile distretto";
    case "settore":
      return "Capo settore";
    case "squadra":
      return "Capo squadra";
    default:
      return "Responsabile unità";
  }
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
  draggingNodeId: string | null;
  draggingUserId: number | null;
  canManage: boolean;
  canAssignPeople: boolean;
  userDropMode: UserDropMode;
  onToggle: (id: string) => void;
  onSelect: (id: string) => void;
  onDragStart: (id: string | null) => void;
  onDragEnd: () => void;
  onMove: (nodeId: string, parentId: string | null) => void;
  onAssignUser: (userId: number, unitId: string, mode: UserDropMode) => void;
};

function TreeNode({
  node,
  depth,
  expanded,
  selectedId,
  showProvenance,
  includeIds,
  matchIds,
  draggingNodeId,
  draggingUserId,
  canManage,
  canAssignPeople,
  userDropMode,
  onToggle,
  onSelect,
  onDragStart,
  onDragEnd,
  onMove,
  onAssignUser,
}: TreeProps) {
  const children = includeIds ? node.children.filter((c) => includeIds.has(c.id)) : node.children;
  const hasChildren = node.children.length > 0;
  const isOpen = expanded.has(node.id) || (includeIds !== null && includeIds.has(node.id));
  const isSelected = selectedId === node.id;
  const isHit = matchIds.has(node.id);
  const canDropHere = !!draggingNodeId && draggingNodeId !== node.id;

  return (
    <li>
      <div
        role="treeitem"
        data-testid={`tree-node-${node.id}`}
        aria-expanded={hasChildren ? isOpen : undefined}
        aria-selected={isSelected}
        tabIndex={0}
        draggable={canManage}
        onClick={() => onSelect(node.id)}
        onDragStart={() => onDragStart(node.id)}
        onDragEnd={onDragEnd}
        onDragOver={(event) => {
          if ((canManage && draggingNodeId && draggingNodeId !== node.id) || (canAssignPeople && draggingUserId != null)) {
            event.preventDefault();
          }
        }}
        onDrop={(event) => {
          if (canAssignPeople && draggingUserId != null) {
            event.preventDefault();
            onAssignUser(draggingUserId, node.id, userDropMode);
            return;
          }
          if (!canManage || !draggingNodeId || draggingNodeId === node.id) return;
          event.preventDefault();
          onMove(draggingNodeId, node.id);
        }}
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
          canManage && canDropHere ? "hover:border-[#1D9E75]" : "",
          draggingNodeId === node.id ? "opacity-60" : "",
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
                draggingNodeId={draggingNodeId}
                draggingUserId={draggingUserId}
                canManage={canManage}
                canAssignPeople={canAssignPeople}
                userDropMode={userDropMode}
                onToggle={onToggle}
                onSelect={onSelect}
                onDragStart={onDragStart}
                onDragEnd={onDragEnd}
                onMove={onMove}
                onAssignUser={onAssignUser}
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
function PersonCard({
  assignment,
  onOpen,
  canDetach = false,
  onDetach,
}: {
  assignment: OrgAssignment;
  onOpen: (id: number) => void;
  canDetach?: boolean;
  onDetach?: (assignmentId: string) => void;
}) {
  const name = assignment.person?.full_name ?? assignment.person?.username ?? `Utente #${assignment.user_id}`;
  const active = assignment.active && (assignment.person?.is_active ?? true);
  return (
    <div className="rounded-xl border border-[#e6ebe5] bg-white p-3 transition-all hover:border-[#bcd9bf] hover:shadow-[0_8px_24px_rgba(15,23,42,0.06)]">
      <button
        type="button"
        onClick={() => onOpen(assignment.user_id)}
        className="flex w-full items-start gap-3 text-left focus-visible:outline-none"
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
      {canDetach && onDetach ? (
        <div className="mt-3 flex justify-end">
          <button
            type="button"
            onClick={() => onDetach(assignment.id)}
            className="rounded-full border border-[#e6d3d3] bg-[#fdf2f2] px-3 py-1 text-[11.5px] font-medium text-[#9a3b3b] hover:bg-[#fbe6e6]"
          >
            Stacca dall&apos;unità
          </button>
        </div>
      ) : null}
    </div>
  );
}

type SchemaBoardProps = {
  tree: OrgUnitTreeNode[];
  selectedId: string | null;
  multiSelectedIds: Set<string>;
  marquee: { x: number; y: number; width: number; height: number } | null;
  collapsedIds: Set<string>;
  collapsedPreview: Map<string, { childNames: string[] }>;
  onToggleCollapse: (id: string) => void;
  onExpandAll: () => void;
  onSelect: (id: string, event?: React.MouseEvent) => void;
  onOpenPerson: (id: number) => void;
  draggingUserId: number | null;
  draggingNodeId: string | null;
  userDropMode: UserDropMode;
  linkDraft: { sourceId: string; mode: "above" | "below" } | null;
  onBeginLink: (nodeId: string, mode: "above" | "below") => void;
  onCardPointerDown: (nodeId: string, event: React.PointerEvent<HTMLDivElement>) => void;
  onCardContextMenu: (nodeId: string, event: React.MouseEvent<HTMLDivElement>) => void;
  onConnectNode: (targetId: string) => void;
  onDetachParent: (nodeId: string) => void;
  onApplyHorizontalLayout: () => void;
  onApplyVerticalLayout: () => void;
  onCompactVisibleArea: () => void;
  onAssignUser: (userId: number, unitId: string, mode: UserDropMode) => void;
  meta: Map<string, SchemaNodeMeta>;
  orientation: SchemaOrientation;
  canModifyStructure: boolean;
  editEnabled: boolean;
  snapToGrid: boolean;
  onToggleSnapToGrid: (enabled: boolean) => void;
  onToggleEdit: (enabled: boolean) => void;
  scale: number;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onFit: () => void;
  onPanStart: (event: React.MouseEvent<HTMLDivElement>) => void;
  viewportRef: React.RefObject<HTMLDivElement>;
  contentRef: React.RefObject<HTMLDivElement>;
};

function SchemaBoard({
  tree,
  selectedId,
  multiSelectedIds,
  marquee,
  collapsedIds,
  collapsedPreview,
  onToggleCollapse,
  onExpandAll,
  onSelect,
  onOpenPerson,
  draggingUserId,
  draggingNodeId,
  userDropMode,
  linkDraft,
  onBeginLink,
  onCardPointerDown,
  onCardContextMenu,
  onConnectNode,
  onDetachParent,
  onApplyHorizontalLayout,
  onApplyVerticalLayout,
  onCompactVisibleArea,
  onAssignUser,
  meta,
  orientation,
  canModifyStructure,
  editEnabled,
  snapToGrid,
  onToggleSnapToGrid,
  onToggleEdit,
  scale,
  onZoomIn,
  onZoomOut,
  onFit,
  onPanStart,
  viewportRef,
  contentRef,
}: SchemaBoardProps) {
  const flatNodes = useMemo(() => flattenTree(tree), [tree]);
  const nodesById = useMemo(() => new Map(flatNodes.map((node) => [node.id, node])), [flatNodes]);
  const displayPositions = useMemo(() => computeSchemaDisplayPositions(flatNodes), [flatNodes]);
  const canvasBounds = useMemo(
    () => computeSchemaCanvasBounds(flatNodes, displayPositions),
    [displayPositions, flatNodes],
  );

  return (
    <section className="min-w-0 overflow-hidden rounded-[28px] border border-[#c8d9e7] bg-[radial-gradient(circle_at_top,_#ffffff,_#f6fafc_65%,_#eef4f7)] p-5 shadow-[0_20px_60px_rgba(15,23,42,0.08)]">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-serif text-[18px] font-semibold text-[#10233e]">Schema organigramma</h2>
          <p className="text-[12.5px] text-[#5c6d82]">
            Modalità lavagna: trascina liberamente le card. Usa le frecce per collegare i blocchi sopra o sotto.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-[12px] text-[#5c6d82]">
          {multiSelectedIds.size > 1 ? (
            <Pill className="border-[#bfe5d6] bg-[#e2f4f1] text-[#0d7a66]">{multiSelectedIds.size} blocchi selezionati</Pill>
          ) : null}
          {collapsedIds.size ? (
            <button
              type="button"
              onClick={onExpandAll}
              className="rounded-full border border-[#e7c89a] bg-[#fdf3e3] px-3 py-1 text-[12px] font-semibold text-[#7c3d06] hover:bg-[#fbe9cf]"
              title="Riapri tutti i gruppi compressi"
            >
              Esplodi tutto ({collapsedIds.size})
            </button>
          ) : null}
          <Pill className="border-[#c4d3ea] bg-white text-[#2f5da8]">canvas libero</Pill>
          <Pill className={snapToGrid ? "border-[#bfe5d6] bg-white text-[#0f6a4e]" : "border-[#d6dfef] bg-white text-[#5c6d82]"}>
            {snapToGrid ? "griglia attiva" : "griglia libera"}
          </Pill>
          <Pill className="border-[#d6dfef] bg-white text-[#2f5da8]">
            vista {orientation === "horizontal" ? "orizzontale" : "verticale"}
          </Pill>
          <Pill className={canModifyStructure ? "border-[#d5e2d8] bg-white text-[#1D4E35]" : "border-[#e6d3d3] bg-white text-[#9a3b3b]"}>
            {canModifyStructure ? "super admin" : "sola lettura"}
          </Pill>
          <div className="ml-2 flex items-center gap-1 rounded-xl border border-[#d6dfef] bg-white p-1">
            {canModifyStructure ? (
              <button
                type="button"
                onClick={onApplyVerticalLayout}
                className={cn("rounded-lg px-2 py-1 text-[12px] font-semibold hover:bg-[#eef3fb]", orientation === "vertical" ? "bg-[#eef3fb] text-[#2f5da8]" : "text-[#5c6d82]")}
              >
                Verticale
              </button>
            ) : null}
            {canModifyStructure ? (
              <button
                type="button"
                onClick={onApplyHorizontalLayout}
                className={cn("rounded-lg px-2 py-1 text-[12px] font-semibold hover:bg-[#eef3fb]", orientation === "horizontal" ? "bg-[#eef3fb] text-[#2f5da8]" : "text-[#5c6d82]")}
              >
                Orizzontale
              </button>
            ) : null}
            {canModifyStructure ? (
              <button
                type="button"
                onClick={onCompactVisibleArea}
                className="rounded-lg px-2 py-1 text-[12px] font-semibold text-[#2f5da8] hover:bg-[#eef3fb]"
                title="Ricompone solo i blocchi attualmente visibili"
              >
                Compatta
              </button>
            ) : null}
            <button type="button" onClick={onZoomOut} className="rounded-lg px-2 py-1 text-[12px] font-semibold text-[#2f5da8] hover:bg-[#eef3fb]">-</button>
            <button type="button" onClick={onFit} className="rounded-lg px-2 py-1 text-[12px] font-semibold text-[#2f5da8] hover:bg-[#eef3fb]">Fit</button>
            <button type="button" onClick={onZoomIn} className="rounded-lg px-2 py-1 text-[12px] font-semibold text-[#2f5da8] hover:bg-[#eef3fb]">+</button>
            <span className="px-2 text-[11.5px] text-[#5c6d82]">{Math.round(scale * 100)}%</span>
          </div>
          {canModifyStructure ? (
            <label className="inline-flex items-center gap-2 rounded-xl border border-[#d6dfef] bg-white px-3 py-2 text-[12px] font-medium text-[#2f5da8]">
              <input type="checkbox" checked={snapToGrid} onChange={(event) => onToggleSnapToGrid(event.target.checked)} />
              Snap griglia
            </label>
          ) : null}
          {canModifyStructure ? (
            <label className="ml-2 inline-flex items-center gap-2 rounded-xl border border-[#e7c89a] bg-white px-3 py-2 text-[12px] font-medium text-[#7c3d06]">
              <input type="checkbox" checked={editEnabled} onChange={(event) => onToggleEdit(event.target.checked)} />
              Abilita modifica
            </label>
          ) : null}
        </div>
      </div>

      {canModifyStructure ? (
        <div
          className={cn(
            "mb-4 rounded-2xl border border-dashed px-4 py-3 text-[12.5px]",
            linkDraft
              ? "border-[#e7c89a] bg-[#fdf3e3] text-[#7c3d06]"
              : editEnabled
              ? "border-[#c4d3ea] bg-white/80 text-[#2f5da8]"
              : "border-[#e6ebe5] bg-white/60 text-[#8a938f]",
          )}
        >
          {linkDraft
            ? linkDraft.mode === "below"
              ? "Seleziona il blocco padre: la card di partenza verrà spostata sotto quel blocco."
              : "Clicca i blocchi da agganciare sotto la card di partenza: puoi collegarne più di uno in sequenza. Esc o di nuovo ↓ per terminare."
            : editEnabled
              ? "Trascina le card per posizionarle liberamente. Usa ↓ per agganciare i figli, ↑ per scegliere il padre. Ctrl/Shift+click o Shift+trascina sullo sfondo per selezionare più blocchi e spostarli insieme."
              : "Attiva “Abilita modifica” per usare la lavagna."}
        </div>
      ) : null}

      <div ref={viewportRef} onMouseDown={onPanStart} className="w-full overflow-auto pb-2 [cursor:grab]">
        <div
          ref={contentRef}
          className="origin-top-left transition-transform duration-200"
          style={{
            width: canvasBounds.width,
            height: canvasBounds.height,
            transform: `scale(${scale})`,
          }}
        >
          {flatNodes.length ? (
            <div className="relative h-full w-full">
              {marquee ? (
                <div
                  aria-hidden="true"
                  className="pointer-events-none absolute z-30 rounded-md border-2 border-[#1D9E75] bg-[#1D9E75]/10"
                  style={{ left: marquee.x, top: marquee.y, width: marquee.width, height: marquee.height }}
                />
              ) : null}
              {snapToGrid ? (
                <div
                  aria-hidden="true"
                  className="pointer-events-none absolute inset-0 z-0"
                  style={{
                    backgroundImage:
                      "linear-gradient(to right, rgba(196,211,234,0.16) 1px, transparent 1px), linear-gradient(to bottom, rgba(196,211,234,0.16) 1px, transparent 1px)",
                    backgroundSize: `${SCHEMA_GRID_SIZE}px ${SCHEMA_GRID_SIZE}px`,
                    backgroundPosition: `${canvasBounds.offsetX}px ${canvasBounds.offsetY}px`,
                  }}
                />
              ) : null}
              <svg className="pointer-events-none absolute inset-0 z-10 h-full w-full overflow-visible">
                <defs>
                  <marker
                    id="org-edge-arrow"
                    viewBox="0 0 10 10"
                    refX="8.5"
                    refY="5"
                    markerWidth="7"
                    markerHeight="7"
                    orient="auto-start-reverse"
                  >
                    <path d="M 0 0 L 10 5 L 0 10 z" fill="#7ea1bf" />
                  </marker>
                </defs>
                {flatNodes.map((node) => {
                  if (!node.parent_id) return null;
                  const parent = nodesById.get(node.parent_id);
                  if (!parent) return null;
                  const parentPosition = displayPositions.get(parent.id);
                  const nodePosition = displayPositions.get(node.id);
                  const parentX = parentPosition?.x ?? safeCanvasCoord(parent.canvas_x);
                  const parentY = parentPosition?.y ?? safeCanvasCoord(parent.canvas_y);
                  const nodeX = nodePosition?.x ?? safeCanvasCoord(node.canvas_x);
                  const nodeY = nodePosition?.y ?? safeCanvasCoord(node.canvas_y);
                  const startX = orientation === "horizontal"
                    ? parentX + canvasBounds.offsetX + SCHEMA_NODE_WIDTH
                    : parentX + canvasBounds.offsetX + SCHEMA_NODE_WIDTH / 2;
                  const startY = orientation === "horizontal"
                    ? parentY + canvasBounds.offsetY + SCHEMA_NODE_HEIGHT / 2
                    : parentY + canvasBounds.offsetY + SCHEMA_NODE_HEIGHT;
                  const endX = orientation === "horizontal"
                    ? nodeX + canvasBounds.offsetX
                    : nodeX + canvasBounds.offsetX + SCHEMA_NODE_WIDTH / 2;
                  const endY = orientation === "horizontal"
                    ? nodeY + canvasBounds.offsetY + SCHEMA_NODE_HEIGHT / 2
                    : nodeY + canvasBounds.offsetY;
                  const path = orientation === "horizontal"
                    ? (() => {
                        const midX = startX + Math.max((endX - startX) / 2, 56);
                        return `M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}`;
                      })()
                    : (() => {
                        const midY = startY + Math.max((endY - startY) / 2, 40);
                        return `M ${startX} ${startY} C ${startX} ${midY}, ${endX} ${midY}, ${endX} ${endY}`;
                      })();
                  return (
                    <path
                      key={`${parent.id}-${node.id}`}
                      d={path}
                      stroke="#c4d3ea"
                      strokeWidth="2"
                      fill="none"
                      markerEnd="url(#org-edge-arrow)"
                    />
                  );
                })}
              </svg>
              {flatNodes.map((node) => (
                <SchemaNodeCard
                  key={node.id}
                  node={node}
                  displayPosition={displayPositions.get(node.id) ?? { x: safeCanvasCoord(node.canvas_x), y: safeCanvasCoord(node.canvas_y) }}
                  offsetX={canvasBounds.offsetX}
                  offsetY={canvasBounds.offsetY}
                  selectedId={selectedId}
                  isMultiSelected={multiSelectedIds.has(node.id)}
                  collapsed={collapsedIds.has(node.id)}
                  collapsedChildNames={collapsedPreview.get(node.id)?.childNames ?? null}
                  onToggleCollapse={onToggleCollapse}
                  onSelect={onSelect}
                  onOpenPerson={onOpenPerson}
                  draggingUserId={draggingUserId}
                  draggingNodeId={draggingNodeId}
                  userDropMode={userDropMode}
                  onCardPointerDown={onCardPointerDown}
                  onCardContextMenu={onCardContextMenu}
                  onConnectNode={onConnectNode}
                  onDetachParent={onDetachParent}
                  onBeginLink={onBeginLink}
                  onAssignUser={onAssignUser}
                  meta={meta}
                  canManage={canModifyStructure && editEnabled}
                  linkDraft={linkDraft}
                />
              ))}
            </div>
          ) : (
            <div className="flex h-full items-center justify-center rounded-2xl border border-dashed border-[#d6dfef] bg-white px-8 py-10 text-[13px] text-[#5c6d82]">
              Nessun nodo disponibile per lo schema.
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

type SchemaNodeCardProps = {
  node: OrgUnitTreeNode;
  displayPosition: SchemaDisplayPosition;
  offsetX: number;
  offsetY: number;
  selectedId: string | null;
  isMultiSelected: boolean;
  collapsed: boolean;
  collapsedChildNames: string[] | null;
  onToggleCollapse: (id: string) => void;
  onSelect: (id: string, event?: React.MouseEvent) => void;
  onOpenPerson: (id: number) => void;
  draggingUserId: number | null;
  userDropMode: UserDropMode;
  linkDraft: { sourceId: string; mode: "above" | "below" } | null;
  draggingNodeId: string | null;
  onCardPointerDown: (nodeId: string, event: React.PointerEvent<HTMLDivElement>) => void;
  onCardContextMenu: (nodeId: string, event: React.MouseEvent<HTMLDivElement>) => void;
  onConnectNode: (targetId: string) => void;
  onDetachParent: (nodeId: string) => void;
  onBeginLink: (nodeId: string, mode: "above" | "below") => void;
  onAssignUser: (userId: number, unitId: string, mode: UserDropMode) => void;
  meta: Map<string, SchemaNodeMeta>;
  canManage: boolean;
};

function SchemaNodeCard({
  node,
  displayPosition,
  offsetX,
  offsetY,
  selectedId,
  isMultiSelected,
  collapsed,
  collapsedChildNames,
  onToggleCollapse,
  onSelect,
  onOpenPerson,
  draggingUserId,
  userDropMode,
  linkDraft,
  draggingNodeId,
  onCardPointerDown,
  onCardContextMenu,
  onConnectNode,
  onDetachParent,
  onBeginLink,
  onAssignUser,
  meta,
  canManage,
}: SchemaNodeCardProps) {
  const nodeMeta = meta.get(node.id);
  const lead = nodeMeta?.lead ?? null;
  const subtreeSize = Math.max((nodeMeta?.descendantIds.size ?? 1) - 1, collapsed ? 1 : 0);
  const isSelected = selectedId === node.id;
  const isLinkTarget = linkDraft?.sourceId !== node.id;
  const cardX = displayPosition.x;
  const cardY = displayPosition.y;

  return (
    <div
      className={cn("absolute z-20", collapsed ? "group hover:z-40" : "")}
      style={{
        left: cardX + offsetX,
        top: cardY + offsetY,
        width: SCHEMA_NODE_WIDTH,
      }}
    >
      <div
        data-schema-node-card=""
        data-testid={`schema-node-${node.id}`}
        onDragOver={(event) => {
          if (draggingUserId != null) event.preventDefault();
        }}
        onDrop={(event) => {
          event.preventDefault();
          if (draggingUserId != null) {
            void onAssignUser(draggingUserId, node.id, userDropMode);
          }
        }}
        className={cn(
          "relative w-[246px] select-none rounded-[24px] border p-4 shadow-[0_18px_50px_rgba(15,23,42,0.08)] transition-all",
          node.tipo === "direzione"
            ? "border-[#7ea1bf] bg-[linear-gradient(180deg,#fdfefe,#edf4fa)]"
            : node.tipo === "settore"
              ? "border-[#efb295] bg-[linear-gradient(180deg,#fffdfc,#fff2eb)]"
              : "border-[#a9c6b1] bg-[linear-gradient(180deg,#fefefe,#edf8ef)]",
          isSelected ? "ring-2 ring-[#1D4E35]/40" : "",
          isMultiSelected ? "ring-2 ring-[#1D9E75]/60" : "",
          collapsed ? "border-dashed shadow-[0_6px_0_-2px_rgba(125,145,135,0.35),0_12px_0_-6px_rgba(125,145,135,0.2),0_18px_50px_rgba(15,23,42,0.08)]" : "",
          linkDraft && isLinkTarget ? "hover:border-[#b45309]" : "",
          linkDraft && !isLinkTarget ? "ring-2 ring-[#b45309]/60" : "",
          canManage ? "cursor-grab touch-none" : "",
          draggingNodeId === node.id ? "cursor-grabbing" : "",
        )}
        onPointerDown={(event) => {
          if (linkDraft && linkDraft.sourceId !== node.id) {
            event.preventDefault();
            void onConnectNode(node.id);
            return;
          }
          if (canManage) {
            onCardPointerDown(node.id, event);
          }
        }}
        onContextMenu={(event) => {
          if (!canManage) return;
          onCardContextMenu(node.id, event);
        }}
        onClick={(event) => {
          if (!linkDraft) onSelect(node.id, event);
        }}
      >
        <div className="relative">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <TypeChip tipo={node.tipo} />
            <SourceBadge source={node.source} legacyTeamId={node.legacy_team_id} />
            {canManage ? (
              <div className="ml-auto flex items-center gap-1">
                {node.parent_id ? (
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      onDetachParent(node.id);
                    }}
                    className="rounded-full border border-[#e6d3d3] bg-white px-2 py-1 text-[11px] font-semibold text-[#9a3b3b] hover:bg-[#fdf2f2]"
                    title="Scollega questo blocco dal padre"
                  >
                    Scollega
                  </button>
                ) : null}
                <button
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation();
                    onBeginLink(node.id, "below");
                  }}
                  className="rounded-full border border-[#d6dfef] bg-white px-2 py-1 text-[11px] font-semibold text-[#2f5da8] hover:bg-[#eef3fb]"
                  title="Scegli il padre: questo blocco verrà spostato sotto la card che clicchi"
                >
                  ↑
                </button>
                <button
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation();
                    onBeginLink(node.id, "above");
                  }}
                  className="rounded-full border border-[#d6dfef] bg-white px-2 py-1 text-[11px] font-semibold text-[#2f5da8] hover:bg-[#eef3fb]"
                  title="Aggancia figli: i blocchi che clicchi finiranno sotto questa card (anche più di uno)"
                >
                  ↓
                </button>
              </div>
            ) : null}
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
          {subtreeSize > 0 ? (
            <div className="mt-2 flex justify-center">
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  onToggleCollapse(node.id);
                }}
                onPointerDown={(event) => event.stopPropagation()}
                className={cn(
                  "rounded-full border px-3 py-1 text-[11.5px] font-semibold",
                  collapsed
                    ? "border-[#e7c89a] bg-[#fdf3e3] text-[#7c3d06] hover:bg-[#fbe9cf]"
                    : "border-[#d6dfef] bg-white text-[#2f5da8] hover:bg-[#eef3fb]",
                )}
                title={collapsed ? "Mostra di nuovo il sotto-albero raggruppato" : "Nascondi il sotto-albero in questo blocco"}
              >
                {collapsed ? `Esplodi (+${subtreeSize})` : "Raggruppa"}
              </button>
            </div>
          ) : null}
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
      {collapsed ? (
        <div className="pointer-events-none absolute left-1/2 top-full z-50 hidden w-[280px] -translate-x-1/2 pt-2 group-hover:block">
          <div className="pointer-events-auto rounded-2xl border border-[#d6dfef] bg-white p-3 shadow-[0_20px_60px_rgba(15,23,42,0.18)]">
            <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#5f6d61]">Gruppo compresso</div>
            <div className="mt-1 text-[12.5px] text-[#3a4a3f]">
              <strong>{subtreeSize}</strong> unità · <strong>{nodeMeta?.totalPeople ?? node.person_count}</strong> persone nel sotto-albero
            </div>
            {collapsedChildNames?.length ? (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {collapsedChildNames.slice(0, 4).map((name) => (
                  <Pill key={name} className="border-[#e6ebe5] bg-[#fbfcfa] text-[#5f6d61]">{name}</Pill>
                ))}
                {collapsedChildNames.length > 4 ? (
                  <Pill className="border-[#e6ebe5] bg-[#fbfcfa] text-[#8a938f]">+{collapsedChildNames.length - 4} altre</Pill>
                ) : null}
              </div>
            ) : null}
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                onToggleCollapse(node.id);
              }}
              onPointerDown={(event) => event.stopPropagation()}
              className="mt-3 w-full rounded-xl bg-[#1D4E35] px-3 py-2 text-[12px] font-semibold text-white hover:bg-[#163d29]"
            >
              Esplodi
            </button>
          </div>
        </div>
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

  const [view, setView] = useState<ViewMode>("schema");
  const [tree, setTree] = useState<OrgUnitTreeNode[]>([]);
  const [overrides, setOverrides] = useState<OrgVisibilityOverride[]>([]);
  const [users, setUsers] = useState<ApplicationUser[]>([]);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [canManage, setCanManage] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [exportingSnapshot, setExportingSnapshot] = useState(false);
  const [importingSnapshot, setImportingSnapshot] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<OrgUnitType | "all">("all");
  const [sectorFilterId, setSectorFilterId] = useState<string>("all");
  const [showProvenance, setShowProvenance] = useState(true);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [schemaFocusNodeId, setSchemaFocusNodeId] = useState<string | null>(null);
  const [detail, setDetail] = useState<OrgUnitDetail | null>(null);

  const [simUserId, setSimUserId] = useState<number | null>(null);
  const [visibility, setVisibility] = useState<OrgVisibilityResult | null>(null);

  const [showAddOverride, setShowAddOverride] = useState(false);
  const [drawerUserId, setDrawerUserId] = useState<number | null>(null);
  const [allAssignments, setAllAssignments] = useState<OrgAssignment[]>([]);
  const [draggingNodeId, setDraggingNodeId] = useState<string | null>(null);
  const [draggingUserId, setDraggingUserId] = useState<number | null>(null);
  const [userDropMode, setUserDropMode] = useState<UserDropMode>("member");
  const [schemaScale, setSchemaScale] = useState(1);
  const [treeScale, setTreeScale] = useState(1);
  const [schemaLinkDraft, setSchemaLinkDraft] = useState<{ sourceId: string; mode: "above" | "below" } | null>(null);
  const [schemaDragging, setSchemaDragging] = useState<{
    nodeId: string;
    pointerId: number;
    startX: number;
    startY: number;
    nodes: { nodeId: string; originX: number; originY: number }[];
  } | null>(null);
  const [multiSelectedIds, setMultiSelectedIds] = useState<Set<string>>(new Set());
  const [schemaMarquee, setSchemaMarquee] = useState<{ x: number; y: number; width: number; height: number } | null>(null);
  const [schemaCollapsedIds, setSchemaCollapsedIds] = useState<Set<string>>(new Set());
  const [schemaContextMenu, setSchemaContextMenu] = useState<{
    nodeId: string;
    x: number;
    y: number;
  } | null>(null);
  const [schemaOrientation, setSchemaOrientation] = useState<SchemaOrientation>("vertical");
  const [schemaEditEnabled, setSchemaEditEnabled] = useState(false);
  const [schemaSnapToGrid, setSchemaSnapToGrid] = useState(true);
  const [importMode, setImportMode] = useState<OrgImportMode>("merge");
  const [pendingImportFile, setPendingImportFile] = useState<File | null>(null);
  const [pendingImportSummary, setPendingImportSummary] = useState<ImportSnapshotAnalysis | null>(null);
  const [showReplaceImportConfirm, setShowReplaceImportConfirm] = useState(false);
  const [replaceImportConfirmText, setReplaceImportConfirmText] = useState("");
  const [createUnitPreset, setCreateUnitPreset] = useState<{ tipo: OrgUnitType; parentId: string | null } | null>(null);
  const importFileInputRef = useRef<HTMLInputElement>(null);
  const schemaViewportRef = useRef<HTMLDivElement>(null);
  const schemaContentRef = useRef<HTMLDivElement>(null);
  const treeRef = useRef<OrgUnitTreeNode[]>([]);
  const treeViewportRef = useRef<HTMLDivElement>(null);
  const schemaPanStateRef = useRef<{ active: boolean; startX: number; startY: number; scrollLeft: number; scrollTop: number }>({
    active: false,
    startX: 0,
    startY: 0,
    scrollLeft: 0,
    scrollTop: 0,
  });
  const schemaAutoFitDoneRef = useRef(false);
  const treePanStateRef = useRef<{ active: boolean; startX: number; startY: number; scrollLeft: number; scrollTop: number }>({
    active: false,
    startX: 0,
    startY: 0,
    scrollLeft: 0,
    scrollTop: 0,
  });

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
      const [sessionUser, treeData, usersData, assignmentsData] = await Promise.all([
        getCurrentUser(token),
        getOrgTree(token),
        listAllApplicationUsers(token),
        getOrgAssignments(token),
      ]);
      setCurrentUser(sessionUser);
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
      } catch (err) {
        if (!isAuthError(err)) setOverrides([]);
      }
      setCanManage(sessionUser.role === "super_admin");
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

  // Lightweight refresh after structure mutations: updates tree, assignments and
  // the selected unit detail in place, without unmounting the workspace (no
  // loading screen, pan/zoom preserved).
  const refreshStructure = useCallback(async () => {
    if (!token) return;
    try {
      const [treeData, assignmentsData] = await Promise.all([
        getOrgTree(token),
        getOrgAssignments(token),
      ]);
      setTree(treeData);
      setAllAssignments(assignmentsData);
      if (selectedId) {
        try {
          setDetail(await getOrgUnit(token, selectedId));
        } catch {
          // the selected unit may no longer exist; the selection effect handles it
        }
      }
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Aggiornamento dati non riuscito");
    }
  }, [token, selectedId]);

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

  const flatTree = useMemo(() => flattenTree(tree), [tree]);
  treeRef.current = tree;
  const settoreOptions = useMemo(
    () =>
      flatTree
        .filter((node) => node.tipo === "settore")
        .sort((left, right) => left.nome.localeCompare(right.nome, "it-IT")),
    [flatTree],
  );
  const scopedTree = useMemo(
    () => filterTreeByRootIds(tree, sectorFilterId === "all" ? null : new Set([sectorFilterId])),
    [tree, sectorFilterId],
  );
  const visibleFlatTree = useMemo(() => flattenTree(scopedTree), [scopedTree]);
  const { includeIds, matchIds } = useMemo(
    () => computeTreeInclusion(scopedTree, query, typeFilter),
    [query, scopedTree, typeFilter],
  );
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

  const roots = includeIds ? scopedTree.filter((r) => includeIds.has(r.id)) : scopedTree;
  const schemaRoots = pruneCollapsedTree(roots, schemaCollapsedIds);
  const scopedTreeRef = useRef(scopedTree);
  scopedTreeRef.current = scopedTree;

  // Apply the auto-grouping on first load and when the sector scope changes;
  // structure refreshes after mutations must not re-collapse manual choices.
  useEffect(() => {
    if (loading) return;
    setSchemaCollapsedIds(computeAutoCollapsedIds(scopedTreeRef.current));
  }, [loading, sectorFilterId]);

  const collapsedPreview = useMemo(() => {
    const map = new Map<string, { childNames: string[] }>();
    if (!schemaCollapsedIds.size) return map;
    for (const node of flatTree) {
      if (schemaCollapsedIds.has(node.id)) {
        map.set(node.id, { childNames: node.children.map((child) => child.nome) });
      }
    }
    return map;
  }, [schemaCollapsedIds, flatTree]);

  const canModifyStructure = canManage && currentUser?.role === "super_admin";
  const assignedUserIds = useMemo(
    () => new Set(allAssignments.filter((assignment) => assignment.active).map((assignment) => assignment.user_id)),
    [allAssignments],
  );
  const unassignedUsers = useMemo(
    () => users.filter((user) => user.is_active && !assignedUserIds.has(user.id)),
    [assignedUserIds, users],
  );
  const operatorUsers = useMemo(
    () =>
      users
        .filter((user) => user.is_active)
        .slice()
        .sort((left, right) => {
          const leftAssigned = assignedUserIds.has(left.id) ? 1 : 0;
          const rightAssigned = assignedUserIds.has(right.id) ? 1 : 0;
          if (leftAssigned !== rightAssigned) return leftAssigned - rightAssigned;
          return (left.full_name ?? left.username).localeCompare(right.full_name ?? right.username, "it-IT");
        }),
    [assignedUserIds, users],
  );
  const selectedSector = useMemo(
    () => (sectorFilterId === "all" ? null : flatTree.find((node) => node.id === sectorFilterId) ?? null),
    [flatTree, sectorFilterId],
  );
  const quickSectorOptions = useMemo(() => settoreOptions.slice(0, QUICK_SECTOR_LIMIT), [settoreOptions]);
  const schemaContextNode = useMemo(
    () => (schemaContextMenu ? flatTree.find((node) => node.id === schemaContextMenu.nodeId) ?? null : null),
    [flatTree, schemaContextMenu],
  );
  const viewportWidth = typeof window !== "undefined" ? window.innerWidth : 1280;
  const viewportHeight = typeof window !== "undefined" ? window.innerHeight : 800;

  useEffect(() => {
    if (sectorFilterId !== "all" && !settoreOptions.some((node) => node.id === sectorFilterId)) {
      setSectorFilterId("all");
    }
  }, [sectorFilterId, settoreOptions]);

  useEffect(() => {
    if (!visibleFlatTree.length) {
      setSelectedId(null);
      return;
    }
    if (!selectedId || !visibleFlatTree.some((node) => node.id === selectedId)) {
      setSelectedId(visibleFlatTree[0].id);
    }
  }, [selectedId, visibleFlatTree]);

  useEffect(() => {
    if (!canModifyStructure) {
      setSchemaEditEnabled(false);
      setDraggingUserId(null);
      setSchemaLinkDraft(null);
      setSchemaDragging(null);
      setSchemaContextMenu(null);
    }
  }, [canModifyStructure]);

  const handleToggleSchemaEdit = useCallback((enabled: boolean) => {
    setSchemaEditEnabled(enabled);
    if (!enabled) {
      setSchemaLinkDraft(null);
      setSchemaDragging(null);
      setSchemaContextMenu(null);
      setMultiSelectedIds(new Set());
    }
  }, []);

  const focusSectorWorkspace = useCallback((sectorId: string) => {
    setSectorFilterId(sectorId);
    setSelectedId(sectorId);
    setView("schema");
    setSchemaFocusNodeId(sectorId);
    setSchemaContextMenu(null);
  }, []);

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

  async function handleExportSnapshot() {
    if (!token || !canModifyStructure) return;
    setExportingSnapshot(true);
    setNotice(null);
    try {
      const snapshot = await exportOrganigrammaSnapshot(token);
      const blob = new Blob([JSON.stringify(snapshot, null, 2)], { type: "application/json;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      const timestamp = new Date().toISOString().replaceAll(":", "-");
      link.href = url;
      link.download = `organigramma-snapshot-${timestamp}.json`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setNotice("Snapshot JSON esportato.");
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Export JSON non riuscito");
    } finally {
      setExportingSnapshot(false);
    }
  }

  function handleOpenImportDialog() {
    if (!canModifyStructure) return;
    importFileInputRef.current?.click();
  }

  function closeReplaceImportConfirm() {
    setShowReplaceImportConfirm(false);
    setPendingImportFile(null);
    setPendingImportSummary(null);
    setReplaceImportConfirmText("");
    if (importFileInputRef.current) importFileInputRef.current.value = "";
  }

  async function handleImportFile(file: File | null) {
    if (!file || !token || !canModifyStructure) return;
    if (importMode === "replace") {
      try {
        const parsed = JSON.parse(await file.text()) as OrganigrammaSnapshot;
        setPendingImportSummary(analyzeOrganigrammaSnapshot(parsed));
      } catch (err) {
        setNotice(err instanceof Error ? err.message : "JSON non valido");
        if (importFileInputRef.current) importFileInputRef.current.value = "";
        return;
      }
      setPendingImportFile(file);
      setReplaceImportConfirmText("");
      setShowReplaceImportConfirm(true);
      return;
    }
    setImportingSnapshot(true);
    setNotice(null);
    try {
      const parsed = JSON.parse(await file.text()) as OrganigrammaSnapshot;
      const result = await importOrganigrammaSnapshot(token, parsed, importMode);
      await loadCore();
      setNotice(
        [
          `Import ${result.mode} completato.`,
          `Unità create ${result.units_created}, aggiornate ${result.units_updated}.`,
          `Assegnazioni create ${result.assignments_created}, aggiornate ${result.assignments_updated}.`,
          `Override create ${result.overrides_created}, aggiornate ${result.overrides_updated}.`,
        ].join(" "),
      );
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Import JSON non riuscito");
    } finally {
      if (importFileInputRef.current) importFileInputRef.current.value = "";
      setImportingSnapshot(false);
    }
  }

  async function handleConfirmReplaceImport() {
    if (!pendingImportFile || !token || !canModifyStructure) return;
    setImportingSnapshot(true);
    setNotice(null);
    try {
      const parsed = JSON.parse(await pendingImportFile.text()) as OrganigrammaSnapshot;
      const result = await importOrganigrammaSnapshot(token, parsed, "replace");
      await loadCore();
      setNotice(
        [
          `Import ${result.mode} completato.`,
          `Unità create ${result.units_created}, aggiornate ${result.units_updated}.`,
          `Assegnazioni create ${result.assignments_created}, aggiornate ${result.assignments_updated}.`,
          `Override create ${result.overrides_created}, aggiornate ${result.overrides_updated}.`,
        ].join(" "),
      );
      closeReplaceImportConfirm();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Import JSON non riuscito");
    } finally {
      if (importFileInputRef.current) importFileInputRef.current.value = "";
      setImportingSnapshot(false);
    }
  }

  async function handleCreateOverride(payload: OrgVisibilityOverrideCreateInput) {
    if (!token || !canModifyStructure) return;
    await createOrgOverride(token, payload);
    setOverrides(await getOrgOverrides(token));
    setShowAddOverride(false);
  }

  async function handleMoveNode(nodeId: string, parentId: string | null) {
    if (!token || !canModifyStructure || !schemaEditEnabled || nodeId === parentId) return;
    const nodeMeta = schemaMeta.get(nodeId);
    if (parentId && nodeMeta?.descendantIds.has(parentId)) {
      setNotice("Operazione non valida: non puoi spostare un nodo dentro un suo discendente.");
      return;
    }
    setNotice(null);
    try {
      await updateOrgUnit(token, nodeId, { parent_id: parentId });
      setSelectedId(nodeId);
      await refreshStructure();
      setNotice(parentId ? "Gerarchia aggiornata." : "Nodo spostato in radice.");
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Aggiornamento gerarchia non riuscito");
    } finally {
      setDraggingNodeId(null);
      setDraggingUserId(null);
    }
  }

  function handleBeginSchemaLink(nodeId: string, mode: "above" | "below") {
    if (!canModifyStructure || !schemaEditEnabled) return;
    setSchemaLinkDraft((current) => {
      if (current?.sourceId === nodeId && current.mode === mode) {
        return null;
      }
      return { sourceId: nodeId, mode };
    });
  }

  async function performSchemaLink(sourceId: string, targetId: string, mode: "above" | "below"): Promise<boolean> {
    if (!token || !canModifyStructure || !schemaEditEnabled) return false;
    if (sourceId === targetId) return false;

    const sourceMeta = schemaMeta.get(sourceId);
    const targetMeta = schemaMeta.get(targetId);
    if (mode === "below" && sourceMeta?.descendantIds.has(targetId)) {
      setNotice("Collegamento non valido: il blocco sorgente non può finire sotto un suo discendente.");
      return false;
    }
    if (mode === "above" && targetMeta?.descendantIds.has(sourceId)) {
      setNotice("Collegamento non valido: il blocco destinazione non può finire sotto un suo discendente.");
      return false;
    }

    try {
      if (mode === "below") {
        await updateOrgUnit(token, sourceId, { parent_id: targetId });
      } else {
        await updateOrgUnit(token, targetId, { parent_id: sourceId });
      }
      // Keep the source block selected so multiple children can be linked in sequence.
      setSelectedId(sourceId);
      setNotice("Collegamento aggiornato.");
      await refreshStructure();
      return true;
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Aggiornamento collegamento non riuscito");
      return false;
    }
  }

  async function handleConnectSchemaNode(targetId: string) {
    if (!schemaLinkDraft) return;
    const { sourceId, mode } = schemaLinkDraft;
    const ok = await performSchemaLink(sourceId, targetId, mode);
    // "above" collects children: keep the draft alive so more blocks can be
    // linked under the same source. "below" picks the single parent, so close it.
    if (!ok || mode === "below") {
      setSchemaLinkDraft(null);
    }
  }

  async function handleConnectSelectedNodeToTarget(targetId: string, mode: "above" | "below") {
    if (!selectedId) return;
    setSchemaLinkDraft(null);
    await performSchemaLink(selectedId, targetId, mode);
  }

  async function handleAssignUserToUnit(userId: number, unitId: string, mode: UserDropMode) {
    if (!token || !canModifyStructure || !schemaEditEnabled) return;
    const unitMeta = schemaMeta.get(unitId);
    const unit = flatTree.find((entry) => entry.id === unitId);
    const user = users.find((entry) => entry.id === userId);
    if (!unit || !user) return;
    if (assignedUserIds.has(userId)) {
      setNotice("Questo utente risulta già assegnato a una unità.");
      setDraggingUserId(null);
      return;
    }
    if (mode === "lead" && unitMeta?.lead) {
      setNotice("L'unità ha già un responsabile diretto. Spostalo o sostituiscilo prima di assegnarne un altro.");
      setDraggingUserId(null);
      return;
    }

    const payload: OrgAssignmentCreateInput = {
      user_id: userId,
      org_unit_id: unitId,
      manager_user_id: null,
      title: mode === "lead" ? defaultLeadTitle(unit.tipo) : null,
      is_primary: mode === "lead",
      active: true,
      source: "manuale",
    };

    try {
      await createOrgAssignment(token, payload);
      setNotice(
        mode === "lead"
          ? `${user.full_name ?? user.username} impostato come responsabile di ${unit.nome}.`
          : `${user.full_name ?? user.username} assegnato a ${unit.nome}.`,
      );
      await refreshStructure();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Assegnazione non riuscita");
    } finally {
      setDraggingUserId(null);
    }
  }

  async function handleCreateUnit(payload: OrgUnitCreateInput, responsibleUserId: number | null) {
    if (!token || !canModifyStructure) return;
    try {
      const parentUnit = payload.parent_id ? flatTree.find((entry) => entry.id === payload.parent_id) : null;
      const seededPayload: OrgUnitCreateInput = {
        ...payload,
        canvas_x: payload.canvas_x ?? (parentUnit ? parentUnit.canvas_x + 320 : 120),
        canvas_y: payload.canvas_y ?? (parentUnit ? parentUnit.canvas_y + 220 : 120 + flatTree.length * 40),
      };
      const created = await createOrgUnit(token, seededPayload);
      if (responsibleUserId != null) {
        const tipo = payload.tipo;
        await createOrgAssignment(token, {
          user_id: responsibleUserId,
          org_unit_id: created.id,
          manager_user_id: null,
          title: defaultLeadTitle(tipo),
          is_primary: true,
          active: true,
          source: "manuale",
        });
      }
      setCreateUnitPreset(null);
      setSelectedId(created.id);
      setNotice(`Unità ${created.nome} creata correttamente.`);
      await refreshStructure();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Creazione unità non riuscita");
    }
  }

  function openCreateUnit(tipo: OrgUnitType, parentId: string | null = selectedId) {
    setCreateUnitPreset({ tipo, parentId });
  }

  function resolveSectorParentId(): string | null {
    if (selectedNode?.tipo === "distretto" || selectedNode?.tipo === "direzione") {
      return selectedNode.id;
    }
    if (selectedNode?.tipo === "settore") {
      return selectedNode.parent_id;
    }
    if (selectedSector?.parent_id) {
      return selectedSector.parent_id;
    }
    return selectedId;
  }

  function resolveGenericUnitType(): OrgUnitType {
    if (selectedNode?.tipo === "direzione") return "distretto";
    if (selectedNode?.tipo === "distretto") return "settore";
    if (selectedNode?.tipo === "settore") return "squadra";
    return "settore";
  }

  function snapCoordinate(value: number) {
    return Math.max(0, Math.round(value / SCHEMA_GRID_SIZE) * SCHEMA_GRID_SIZE);
  }

  const realignExpandedSubtree = useCallback(async (nodeId: string) => {
    const expandedNode = flatTree.find((node) => node.id === nodeId);
    if (!expandedNode || !expandedNode.children.length) return;
    const subtreeRoot = expandedNode.parent_id
      ? flatTree.find((node) => node.id === expandedNode.parent_id) ?? expandedNode
      : expandedNode;
    if (!subtreeRoot.children.length) return;

    const layout = schemaOrientation === "horizontal"
      ? computeHorizontalTreeLayout([subtreeRoot])
      : computeVerticalTreeLayout([subtreeRoot]);
    const rootLayout = layout.get(subtreeRoot.id);
    if (!rootLayout) return;

    const rootX = safeCanvasCoord(subtreeRoot.canvas_x);
    const rootY = safeCanvasCoord(subtreeRoot.canvas_y);
    const deltaX = rootX - rootLayout.x;
    const deltaY = rootY - rootLayout.y;
    const rawPositions = new Map<string, SchemaDisplayPosition>();

    for (const [entryId, position] of layout.entries()) {
      if (entryId === subtreeRoot.id) continue;
      rawPositions.set(entryId, {
        x: snapCoordinate(position.x + deltaX),
        y: snapCoordinate(position.y + deltaY),
      });
    }

    if (!rawPositions.size) return;

    const subtreeIds = new Set(rawPositions.keys());
    subtreeIds.add(subtreeRoot.id);
    const occupiedPositions = flatTree
      .filter((entry) => !subtreeIds.has(entry.id))
      .map((entry) => ({
        x: safeCanvasCoord(entry.canvas_x),
        y: safeCanvasCoord(entry.canvas_y),
      }));
    const collisionShift = resolveSubtreeCollisionShift(rawPositions, occupiedPositions, schemaOrientation);
    const nextPositions = new Map<string, SchemaDisplayPosition>();

    for (const [entryId, position] of rawPositions.entries()) {
      nextPositions.set(entryId, {
        x: snapCoordinate(Math.max(0, position.x + collisionShift.x)),
        y: snapCoordinate(Math.max(0, position.y + collisionShift.y)),
      });
    }

    setTree((current) => applyCanvasPositionsToForest(current, nextPositions));

    if (!token || !canModifyStructure) return;

    await Promise.all(
      [...nextPositions.entries()].map(([entryId, position]) =>
        updateOrgUnit(token, entryId, {
          canvas_x: position.x,
          canvas_y: position.y,
        }),
      ),
    );
  }, [canModifyStructure, flatTree, schemaOrientation, token]);

  const toggleSchemaCollapse = useCallback((nodeId: string) => {
    const wasCollapsed = schemaCollapsedIds.has(nodeId);
    setSchemaCollapsedIds((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });

    if (wasCollapsed) {
      void realignExpandedSubtree(nodeId).catch((err) => {
        setNotice(err instanceof Error ? err.message : "Riallineamento del sotto-albero non riuscito");
      });
    }
  }, [realignExpandedSubtree, schemaCollapsedIds]);

  async function handleDetachAssignment(assignmentId: string) {
    if (!token || !canModifyStructure || !schemaEditEnabled) return;
    try {
      await deleteOrgAssignment(token, assignmentId);
      setNotice("Assegnazione rimossa dall'organigramma.");
      await refreshStructure();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Rimozione assegnazione non riuscita");
    }
  }

  async function handleApplyTreeLayout(orientation: SchemaOrientation) {
    if (!token || !canModifyStructure) return;
    const layoutTree = scopedTree;
    const nextPositions = orientation === "horizontal"
      ? computeHorizontalTreeLayout(layoutTree)
      : computeVerticalTreeLayout(layoutTree);
    setTree((current) => {
      let nextTree = current;
      for (const [nodeId, position] of nextPositions) {
        nextTree = updateTreeNodeInForest(nextTree, nodeId, {
          canvas_x: position.x,
          canvas_y: position.y,
        });
      }
      return nextTree;
    });
    try {
      await Promise.all(
        Array.from(nextPositions.entries()).map(([nodeId, position]) =>
          updateOrgUnit(token, nodeId, {
            canvas_x: position.x,
            canvas_y: position.y,
          }),
        ),
      );
      setSchemaOrientation(orientation);
      setNotice(`Layout ${orientation === "horizontal" ? "orizzontale" : "verticale"} applicato.`);
      await refreshStructure();
      if (view === "schema") {
        window.requestAnimationFrame(() => {
          fitSchemaToViewport();
        });
      }
    } catch (err) {
      setNotice(err instanceof Error ? err.message : `Applicazione layout ${orientation === "horizontal" ? "orizzontale" : "verticale"} non riuscita`);
    }
  }

  async function handleCompactVisibleArea() {
    if (!token || !canModifyStructure) return;
    const layoutTree = schemaRoots;
    const visibleNodes = flattenTree(layoutTree);
    if (!visibleNodes.length) return;

    const baseLayout = schemaOrientation === "horizontal"
      ? computeHorizontalTreeLayout(layoutTree)
      : computeVerticalTreeLayout(layoutTree);
    const currentMinX = Math.min(...visibleNodes.map((node) => safeCanvasCoord(node.canvas_x)));
    const currentMinY = Math.min(...visibleNodes.map((node) => safeCanvasCoord(node.canvas_y)));
    const layoutMinX = Math.min(...visibleNodes.map((node) => baseLayout.get(node.id)?.x ?? 0));
    const layoutMinY = Math.min(...visibleNodes.map((node) => baseLayout.get(node.id)?.y ?? 0));
    const offsetX = currentMinX - layoutMinX;
    const offsetY = currentMinY - layoutMinY;
    const nextPositions = new Map<string, SchemaDisplayPosition>();

    for (const node of visibleNodes) {
      const position = baseLayout.get(node.id);
      if (!position) continue;
      nextPositions.set(node.id, {
        x: snapCoordinate(Math.max(0, position.x + offsetX)),
        y: snapCoordinate(Math.max(0, position.y + offsetY)),
      });
    }

    setTree((current) => applyCanvasPositionsToForest(current, nextPositions));
    try {
      await Promise.all(
        [...nextPositions.entries()].map(([nodeId, position]) =>
          updateOrgUnit(token, nodeId, {
            canvas_x: position.x,
            canvas_y: position.y,
          }),
        ),
      );
      setNotice("Area visibile compattata.");
      if (view === "schema") {
        window.requestAnimationFrame(() => {
          fitSchemaToViewport();
        });
      }
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Compattazione area visibile non riuscita");
    }
  }

  function handleSchemaCardSelect(nodeId: string, event?: React.MouseEvent) {
    if (event && (event.ctrlKey || event.metaKey || event.shiftKey)) {
      const isToggleOff = (event.ctrlKey || event.metaKey) && multiSelectedIds.has(nodeId);
      setMultiSelectedIds((prev) => {
        const next = new Set(prev);
        // Seed the multi-selection with the currently selected card on the first modifier click.
        if (!next.size && selectedId && selectedId !== nodeId) next.add(selectedId);
        if (isToggleOff) {
          next.delete(nodeId);
        } else {
          next.add(nodeId);
        }
        return next;
      });
      if (!isToggleOff) setSelectedId(nodeId);
      return;
    }
    setMultiSelectedIds(new Set());
    setSelectedId(nodeId);
  }

  function handleSchemaCardPointerDown(nodeId: string, event: React.PointerEvent<HTMLDivElement>) {
    if (!schemaEditEnabled || event.button !== 0) return;
    // Modifier clicks are selection gestures (handled on click), not drag starts.
    if (event.ctrlKey || event.metaKey || event.shiftKey) return;
    const target = event.target as HTMLElement | null;
    if (target?.closest("button, input, select, textarea, label, a")) return;
    const node = flatTree.find((entry) => entry.id === nodeId);
    if (!node) return;
    if (typeof event.currentTarget.setPointerCapture === "function") {
      event.currentTarget.setPointerCapture(event.pointerId);
    }
    event.preventDefault();
    event.stopPropagation();
    setSelectedId(nodeId);
    const groupIds = multiSelectedIds.has(nodeId)
      ? Array.from(new Set([nodeId, ...multiSelectedIds]))
      : [nodeId];
    if (!multiSelectedIds.has(nodeId) && multiSelectedIds.size) {
      setMultiSelectedIds(new Set());
    }
    const dragNodes = groupIds
      .map((id) => flatTree.find((entry) => entry.id === id))
      .filter((entry): entry is OrgUnitTreeNode => Boolean(entry))
      .map((entry) => ({
        nodeId: entry.id,
        originX: safeCanvasCoord(entry.canvas_x),
        originY: safeCanvasCoord(entry.canvas_y),
      }));
    setSchemaDragging({
      nodeId,
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      nodes: dragNodes,
    });
  }

  function handleSchemaCardContextMenu(nodeId: string, event: React.MouseEvent<HTMLDivElement>) {
    if (!schemaEditEnabled) return;
    event.preventDefault();
    event.stopPropagation();
    setSelectedId(nodeId);
    setSchemaContextMenu({
      nodeId,
      x: event.clientX,
      y: event.clientY,
    });
  }

  useEffect(() => {
    if (!schemaDragging || !token || !schemaEditEnabled) return;

    const handlePointerMove = (event: PointerEvent) => {
      if (event.pointerId !== schemaDragging.pointerId) return;
      const deltaX = Math.round((event.clientX - schemaDragging.startX) / Math.max(schemaScale, 0.01));
      const deltaY = Math.round((event.clientY - schemaDragging.startY) / Math.max(schemaScale, 0.01));
      setTree((current) => {
        let nextTree = current;
        for (const dragNode of schemaDragging.nodes) {
          const rawX = Math.max(0, dragNode.originX + deltaX);
          const rawY = Math.max(0, dragNode.originY + deltaY);
          const nextX = schemaSnapToGrid ? snapCoordinate(rawX) : rawX;
          const nextY = schemaSnapToGrid ? snapCoordinate(rawY) : rawY;
          nextTree = updateTreeNodeInForest(nextTree, dragNode.nodeId, { canvas_x: nextX, canvas_y: nextY });
        }
        return nextTree;
      });
    };

    const handlePointerUp = (event: PointerEvent) => {
      if (event.pointerId !== schemaDragging.pointerId) return;
      const flat = flattenTree(treeRef.current);
      setSchemaDragging(null);
      for (const dragNode of schemaDragging.nodes) {
        const movedNode = flat.find((entry) => entry.id === dragNode.nodeId);
        if (!movedNode) continue;
        void updateOrgUnit(token, dragNode.nodeId, {
          canvas_x: movedNode.canvas_x,
          canvas_y: movedNode.canvas_y,
        }).catch((err) => {
          setNotice(err instanceof Error ? err.message : "Salvataggio posizione non riuscito");
        });
      }
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    window.addEventListener("pointercancel", handlePointerUp);
    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      window.removeEventListener("pointercancel", handlePointerUp);
    };
  }, [schemaDragging, token, schemaEditEnabled, schemaScale, schemaSnapToGrid]);

  const fitSchemaToViewport = useCallback(() => {
    const viewport = schemaViewportRef.current;
    const content = schemaContentRef.current;
    if (!viewport || !content) return;
    const widthRatio = (viewport.clientWidth - 32) / Math.max(content.scrollWidth, 1);
    const heightRatio = (viewport.clientHeight - 32) / Math.max(content.scrollHeight, 1);
    const nextScale = Math.max(0.45, Math.min(1.15, Math.min(widthRatio, heightRatio)));
    setSchemaScale(nextScale);
    window.requestAnimationFrame(() => {
      const scaledWidth = content.scrollWidth * nextScale;
      const scaledHeight = content.scrollHeight * nextScale;
      viewport.scrollLeft = Math.max((scaledWidth - viewport.clientWidth) / 2, 0);
      viewport.scrollTop = Math.max((scaledHeight - viewport.clientHeight) / 2, 0);
    });
  }, []);

  useEffect(() => {
    if (view !== "schema" || loading || !roots.length || schemaAutoFitDoneRef.current) return;
    const id = window.requestAnimationFrame(() => {
      fitSchemaToViewport();
      schemaAutoFitDoneRef.current = true;
    });
    return () => window.cancelAnimationFrame(id);
  }, [view, loading, roots.length, fitSchemaToViewport]);

  useEffect(() => {
    if (view !== "schema") {
      schemaAutoFitDoneRef.current = false;
      return;
    }
    if (loading) {
      schemaAutoFitDoneRef.current = false;
    }
  }, [view, loading]);

  useEffect(() => {
    if (view !== "schema") return;
    const handleResize = () => fitSchemaToViewport();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [view, fitSchemaToViewport]);

  useEffect(() => {
    if (view !== "schema" || !schemaFocusNodeId) return;
    const viewport = schemaViewportRef.current;
    if (!viewport) return;
    const visibleNodes = flattenTree(roots);
    const targetNode = visibleNodes.find((node) => node.id === schemaFocusNodeId);
    if (!targetNode) {
      setSchemaFocusNodeId(null);
      return;
    }
    const positions = computeSchemaDisplayPositions(visibleNodes);
    const bounds = computeSchemaCanvasBounds(visibleNodes, positions);
    const widthRatio = (viewport.clientWidth - 32) / Math.max(bounds.width, 1);
    const heightRatio = (viewport.clientHeight - 32) / Math.max(bounds.height, 1);
    const nextScale = Math.max(0.45, Math.min(1.2, Math.min(widthRatio, heightRatio)));
    setSchemaScale(nextScale);

    const id = window.requestAnimationFrame(() => {
      const targetPosition = positions.get(targetNode.id) ?? {
        x: safeCanvasCoord(targetNode.canvas_x),
        y: safeCanvasCoord(targetNode.canvas_y),
      };
      const targetX = (targetPosition.x + bounds.offsetX) * nextScale;
      const targetY = (targetPosition.y + bounds.offsetY) * nextScale;
      viewport.scrollLeft = Math.max(targetX - (viewport.clientWidth - SCHEMA_NODE_WIDTH * nextScale) / 2, 0);
      viewport.scrollTop = Math.max(targetY - (viewport.clientHeight - SCHEMA_NODE_HEIGHT * nextScale) / 2, 0);
      setSchemaFocusNodeId(null);
    });

    return () => window.cancelAnimationFrame(id);
  }, [view, schemaFocusNodeId, roots]);

  useEffect(() => {
    if (!schemaContextMenu) return;
    const handleClose = () => setSchemaContextMenu(null);
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setSchemaContextMenu(null);
      }
    };
    window.addEventListener("pointerdown", handleClose);
    window.addEventListener("contextmenu", handleClose);
    window.addEventListener("keydown", handleEscape);
    return () => {
      window.removeEventListener("pointerdown", handleClose);
      window.removeEventListener("contextmenu", handleClose);
      window.removeEventListener("keydown", handleEscape);
    };
  }, [schemaContextMenu]);

  useEffect(() => {
    if (!schemaLinkDraft) return;
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setSchemaLinkDraft(null);
      }
    };
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [schemaLinkDraft]);

  const handleTreePanStart = useCallback((event: React.MouseEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    const target = event.target as HTMLElement | null;
    if (target?.closest("[role='treeitem'], button, input, select, textarea, label, a")) return;
    const viewport = treeViewportRef.current;
    if (!viewport) return;

    treePanStateRef.current = {
      active: true,
      startX: event.clientX,
      startY: event.clientY,
      scrollLeft: viewport.scrollLeft,
      scrollTop: viewport.scrollTop,
    };
    viewport.style.cursor = "grabbing";
    event.preventDefault();

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const current = treePanStateRef.current;
      if (!current.active) return;
      viewport.scrollLeft = current.scrollLeft - (moveEvent.clientX - current.startX);
      viewport.scrollTop = current.scrollTop - (moveEvent.clientY - current.startY);
    };

    const handleMouseUp = () => {
      treePanStateRef.current.active = false;
      viewport.style.cursor = "grab";
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
  }, []);

  const handleSchemaPanStart = useCallback((event: React.MouseEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    const target = event.target as HTMLElement | null;
    if (target?.closest("[data-schema-node-card], button, input, select, textarea, label, a")) return;
    const viewport = schemaViewportRef.current;
    if (!viewport) return;

    if (event.shiftKey) {
      // Shift+drag on the background: marquee selection instead of panning.
      event.preventDefault();
      const visibleNodes = flattenTree(schemaRoots);
      const bounds = computeSchemaCanvasBounds(visibleNodes, computeSchemaDisplayPositions(visibleNodes));
      const scale = Math.max(schemaScale, 0.01);
      const viewportRect = viewport.getBoundingClientRect();
      const toCanvas = (clientX: number, clientY: number) => ({
        x: (clientX - viewportRect.left + viewport.scrollLeft) / scale,
        y: (clientY - viewportRect.top + viewport.scrollTop) / scale,
      });
      const start = toCanvas(event.clientX, event.clientY);

      const updateSelection = (clientX: number, clientY: number) => {
        const current = toCanvas(clientX, clientY);
        const minX = Math.min(start.x, current.x);
        const maxX = Math.max(start.x, current.x);
        const minY = Math.min(start.y, current.y);
        const maxY = Math.max(start.y, current.y);
        setSchemaMarquee({ x: minX, y: minY, width: maxX - minX, height: maxY - minY });
        const ids = new Set<string>();
        for (const node of visibleNodes) {
          const left = safeCanvasCoord(node.canvas_x) + bounds.offsetX;
          const top = safeCanvasCoord(node.canvas_y) + bounds.offsetY;
          if (left < maxX && left + SCHEMA_NODE_WIDTH > minX && top < maxY && top + SCHEMA_NODE_HEIGHT > minY) {
            ids.add(node.id);
          }
        }
        setMultiSelectedIds(ids);
      };

      const handleMarqueeMove = (moveEvent: MouseEvent) => {
        updateSelection(moveEvent.clientX, moveEvent.clientY);
      };
      const handleMarqueeUp = (upEvent: MouseEvent) => {
        updateSelection(upEvent.clientX, upEvent.clientY);
        setSchemaMarquee(null);
        window.removeEventListener("mousemove", handleMarqueeMove);
        window.removeEventListener("mouseup", handleMarqueeUp);
      };
      window.addEventListener("mousemove", handleMarqueeMove);
      window.addEventListener("mouseup", handleMarqueeUp);
      return;
    }

    // Clicking the empty canvas exits link mode and clears the multi-selection.
    setSchemaLinkDraft(null);
    setMultiSelectedIds(new Set());

    schemaPanStateRef.current = {
      active: true,
      startX: event.clientX,
      startY: event.clientY,
      scrollLeft: viewport.scrollLeft,
      scrollTop: viewport.scrollTop,
    };
    viewport.style.cursor = "grabbing";
    event.preventDefault();

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const current = schemaPanStateRef.current;
      if (!current.active) return;
      viewport.scrollLeft = current.scrollLeft - (moveEvent.clientX - current.startX);
      viewport.scrollTop = current.scrollTop - (moveEvent.clientY - current.startY);
    };

    const handleMouseUp = () => {
      schemaPanStateRef.current.active = false;
      viewport.style.cursor = "grab";
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
  }, [schemaRoots, schemaScale]);

  const handleTreeZoomWheel = useCallback((event: WheelEvent) => {
    if (!event.ctrlKey) return;
    event.preventDefault();
    const viewport = treeViewportRef.current;
    if (!viewport) return;

    const rect = viewport.getBoundingClientRect();
    const pointerX = event.clientX - rect.left + viewport.scrollLeft;
    const pointerY = event.clientY - rect.top + viewport.scrollTop;

    setTreeScale((current) => {
      const delta = event.deltaY > 0 ? -0.08 : 0.08;
      const next = Math.max(0.65, Math.min(1.6, Number((current + delta).toFixed(2))));
      window.requestAnimationFrame(() => {
        const ratio = next / current;
        viewport.scrollLeft = Math.max(pointerX * ratio - (event.clientX - rect.left), 0);
        viewport.scrollTop = Math.max(pointerY * ratio - (event.clientY - rect.top), 0);
      });
      return next;
    });
  }, []);

  const handleSchemaZoomWheel = useCallback((event: WheelEvent) => {
    if (!event.ctrlKey) return;
    event.preventDefault();
    const viewport = schemaViewportRef.current;
    if (!viewport) return;

    const rect = viewport.getBoundingClientRect();
    const pointerX = event.clientX - rect.left + viewport.scrollLeft;
    const pointerY = event.clientY - rect.top + viewport.scrollTop;

    setSchemaScale((current) => {
      const delta = event.deltaY > 0 ? -0.08 : 0.08;
      const next = Math.max(0.5, Math.min(1.6, Number((current + delta).toFixed(2))));
      window.requestAnimationFrame(() => {
        const ratio = next / current;
        viewport.scrollLeft = Math.max(pointerX * ratio - (event.clientX - rect.left), 0);
        viewport.scrollTop = Math.max(pointerY * ratio - (event.clientY - rect.top), 0);
      });
      return next;
    });
  }, []);

  // `loading` is a dependency because on first mount the workspace renders the
  // loading placeholder: the viewport refs only exist after loading completes.
  useEffect(() => {
    const viewport = treeViewportRef.current;
    if (!viewport) return;
    const listener = (event: WheelEvent) => {
      handleTreeZoomWheel(event);
    };
    viewport.addEventListener("wheel", listener, { passive: false });
    return () => viewport.removeEventListener("wheel", listener);
  }, [handleTreeZoomWheel, view, loading]);

  useEffect(() => {
    const viewport = schemaViewportRef.current;
    if (!viewport) return;
    const listener = (event: WheelEvent) => {
      handleSchemaZoomWheel(event);
    };
    viewport.addEventListener("wheel", listener, { passive: false });
    return () => viewport.removeEventListener("wheel", listener);
  }, [handleSchemaZoomWheel, view, loading]);

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
          <label className="min-w-[240px] rounded-xl border border-[#e6ebe5] bg-[#fbfcfa] px-3 py-2 text-[12.5px] text-[#3a4a3f]">
            <span className="mb-1 block text-[11px] font-semibold uppercase tracking-[0.12em] text-[#5f6d61]">Filtro settore</span>
            <select
              value={sectorFilterId}
              onChange={(event) => {
                const nextId = event.target.value;
                if (nextId === "all") {
                  setSectorFilterId("all");
                  setSchemaFocusNodeId(null);
                  return;
                }
                focusSectorWorkspace(nextId);
              }}
              className="w-full bg-transparent text-[13px] outline-none"
            >
              <option value="all">Tutti i settori</option>
              {settoreOptions.map((settore) => (
                <option key={settore.id} value={settore.id}>
                  {settore.nome}
                </option>
              ))}
            </select>
          </label>
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
          {canModifyStructure ? (
            <>
              <button
                type="button"
                onClick={() => void handleExportSnapshot()}
                disabled={exportingSnapshot}
                className="inline-flex items-center gap-2 rounded-xl border border-[#d6dfef] bg-white px-3 py-2 text-[12.5px] font-medium text-[#2f5da8] transition-colors hover:bg-[#eef3fb] disabled:opacity-60"
              >
                {exportingSnapshot ? "Export..." : "Esporta JSON"}
              </button>
              <label className="inline-flex items-center gap-2 rounded-xl border border-[#e6ebe5] bg-[#fbfcfa] px-3 py-2 text-[12px] text-[#3a4a3f]">
                <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#5f6d61]">Import</span>
                <select
                  value={importMode}
                  onChange={(event) => setImportMode(event.target.value as OrgImportMode)}
                  className="bg-transparent text-[12.5px] font-medium outline-none"
                >
                  <option value="merge">merge</option>
                  <option value="replace">replace</option>
                </select>
              </label>
              <input
                ref={importFileInputRef}
                type="file"
                accept="application/json,.json"
                className="hidden"
                onChange={(event) => void handleImportFile(event.target.files?.[0] ?? null)}
              />
              <button
                type="button"
                onClick={handleOpenImportDialog}
                disabled={importingSnapshot}
                className="inline-flex items-center gap-2 rounded-xl border border-[#d7e5db] bg-white px-3 py-2 text-[12.5px] font-medium text-[#1D4E35] transition-colors hover:bg-[#edf5f0] disabled:opacity-60"
              >
                {importingSnapshot ? "Import..." : "Importa JSON"}
              </button>
            </>
          ) : null}
          {canModifyStructure ? (
            <button
              type="button"
              onClick={() => openCreateUnit("settore", resolveSectorParentId())}
              className="inline-flex items-center gap-2 rounded-xl border border-[#bcd9bf] bg-white px-3 py-2 text-[12.5px] font-semibold text-[#1D4E35] transition-colors hover:bg-[#edf5f0]"
            >
              + Nuovo settore
            </button>
          ) : null}
          <div className="ml-auto flex items-center gap-1 rounded-xl border border-[#e6ebe5] bg-[#fbfcfa] p-1">
            <button type="button" onClick={() => setView("schema")} className={cn("inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[12.5px] font-semibold transition-colors", view === "schema" ? "bg-[#1D4E35] text-white" : "text-[#3a4a3f] hover:bg-[#edf5f0]")}>
              <FolderIcon className="h-4 w-4" /> Schema
            </button>
            <button type="button" onClick={() => setView("albero")} className={cn("inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[12.5px] font-semibold transition-colors", view === "albero" ? "bg-[#1D4E35] text-white" : "text-[#3a4a3f] hover:bg-[#edf5f0]")}>
              <GridIcon className="h-4 w-4" /> Albero
            </button>
            <button type="button" onClick={() => setView("chi-vede-chi")} className={cn("inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[12.5px] font-semibold transition-colors", view === "chi-vede-chi" ? "bg-[#1D4E35] text-white" : "text-[#3a4a3f] hover:bg-[#edf5f0]")}>
              <EyeIcon className="h-4 w-4" /> Chi vede chi
            </button>
          </div>
        </div>
        {settoreOptions.length ? (
          <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-[#eef2ed] pt-3">
            <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#5f6d61]">Accesso rapido settori</span>
            <button
              type="button"
              onClick={() => {
                setSectorFilterId("all");
                setSchemaFocusNodeId(null);
              }}
              className={cn(
                "rounded-full border px-3 py-1.5 text-[12px] font-medium transition-colors",
                sectorFilterId === "all"
                  ? "border-[#1D4E35] bg-[#1D4E35] text-white"
                  : "border-[#d6dfef] bg-white text-[#5c6d82] hover:border-[#bcd9bf] hover:text-[#1D4E35]",
              )}
            >
              Tutti
            </button>
            {quickSectorOptions.map((settore) => (
              <button
                key={settore.id}
                type="button"
                onClick={() => focusSectorWorkspace(settore.id)}
                className={cn(
                  "rounded-full border px-3 py-1.5 text-[12px] font-medium transition-colors",
                  sectorFilterId === settore.id
                    ? "border-[#1D9E75] bg-[#e2f4f1] text-[#0d7a66]"
                    : "border-[#d6dfef] bg-white text-[#3a4a3f] hover:border-[#bcd9bf] hover:bg-[#edf5f0]",
                )}
              >
                {settore.nome}
              </button>
            ))}
            {settoreOptions.length > quickSectorOptions.length ? (
              <span className="text-[12px] text-[#7a867d]">+{settoreOptions.length - quickSectorOptions.length} nel filtro completo</span>
            ) : null}
          </div>
        ) : null}
      </div>

      {notice ? (
        <div className="mb-4 rounded-xl border border-[#bfe5e0] bg-[#e2f4f1] px-4 py-2 text-[12.5px] text-[#0d7a66]">{notice}</div>
      ) : null}
      {selectedSector ? (
        <div className="mb-4 rounded-xl border border-[#d6dfef] bg-[#f7f9fd] px-4 py-2 text-[12.5px] text-[#2f5da8]">
          Vista focalizzata sul settore <strong>{selectedSector.nome}</strong>: albero e schema mostrano il suo sotto-albero operativo.
        </div>
      ) : null}

      {view === "albero" ? (
        <div className="flex flex-col gap-5">
          <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-[minmax(0,1fr)_360px] xl:grid-cols-[minmax(0,1fr)_380px]">
            <section className="min-w-0 overflow-hidden rounded-2xl border border-[#e6ebe5] bg-gradient-to-b from-white to-[#fbfcfa] p-4 shadow-[0_14px_40px_rgba(15,23,42,0.06)]">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <FolderIcon className="h-4 w-4 text-[#1D4E35]" />
                  <h2 className="font-serif text-[15px] font-semibold">Albero organizzativo</h2>
                </div>
                <div className="flex flex-wrap items-center gap-2 text-[12px] text-[#5f6d61]">
                  <Pill className="border-[#c4d3ea] bg-white text-[#2f5da8]">Ctrl + rotellina: zoom</Pill>
                  <Pill className="border-[#d6dfef] bg-white text-[#5c6d82]">{Math.round(treeScale * 100)}%</Pill>
                  <Pill className={canModifyStructure ? "border-[#d5e2d8] bg-white text-[#1D4E35]" : "border-[#e6d3d3] bg-white text-[#9a3b3b]"}>
                    {canModifyStructure ? "super admin" : "sola lettura"}
                  </Pill>
                  {canModifyStructure ? (
                    <label className="inline-flex items-center gap-2 rounded-xl border border-[#e7c89a] bg-white px-3 py-2 text-[12px] font-medium text-[#7c3d06]">
                      <input type="checkbox" checked={schemaEditEnabled} onChange={(event) => setSchemaEditEnabled(event.target.checked)} />
                      Abilita modifica
                    </label>
                  ) : null}
                </div>
              </div>
              {canModifyStructure ? (
                <div
                  onDragOver={(event) => {
                    if (!draggingNodeId || !schemaEditEnabled) return;
                    event.preventDefault();
                  }}
                  onDrop={(event) => {
                    if (!draggingNodeId || !schemaEditEnabled) return;
                    event.preventDefault();
                    void handleMoveNode(draggingNodeId, null);
                  }}
                  className={cn(
                    "mb-3 rounded-xl px-4 py-3 text-[12.5px] transition-colors",
                    draggingNodeId && schemaEditEnabled
                      ? "bg-[#eef3fb] text-[#2f5da8]"
                      : "bg-[#f9fbfe] text-[#5c6d82]",
                  )}
                >
                  {schemaEditEnabled ? "Rilascia qui per portare il nodo in radice." : "Attiva “Abilita modifica” per spostare i nodi anche da questa vista."}
                </div>
              ) : null}
              {roots.length ? (
                <div
                  ref={treeViewportRef}
                  onMouseDown={handleTreePanStart}
                  className="max-h-[72vh] overflow-auto pr-2 [cursor:grab]"
                >
                  <div className="min-w-max origin-top-left transition-transform duration-150" style={{ transform: `scale(${treeScale})` }}>
                    <ul role="tree" className="flex flex-col gap-1 min-w-max">
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
                          draggingNodeId={draggingNodeId}
                          draggingUserId={draggingUserId}
                          canManage={canModifyStructure && schemaEditEnabled}
                          canAssignPeople={canModifyStructure && schemaEditEnabled}
                          userDropMode={userDropMode}
                          onToggle={toggle}
                          onSelect={setSelectedId}
                          onDragStart={setDraggingNodeId}
                          onDragEnd={() => setDraggingNodeId(null)}
                          onMove={handleMoveNode}
                          onAssignUser={handleAssignUserToUnit}
                        />
                      ))}
                    </ul>
                  </div>
                </div>
              ) : (
                <div className="rounded-xl border border-dashed border-[#d8e3d9] bg-[#fafdf9] p-8 text-center text-[12.5px] text-[#5f6d61]">
                  {tree.length ? "Nessuna unità corrisponde alla ricerca." : "Nessuna unità. Usa “Sync WhiteCompany” o crea la struttura via API."}
                </div>
              )}
            </section>

            <section className="min-w-0 rounded-2xl border border-[#e6ebe5] bg-gradient-to-b from-white to-[#fbfcfa] p-4 shadow-[0_14px_40px_rgba(15,23,42,0.06)]">
              <div className="flex flex-col gap-5">
                {detail && selectedSummary ? (
                  <UnitDetail
                    detail={detail}
                    summary={selectedSummary}
                    onOpenPerson={setDrawerUserId}
                    canDetachAssignments={canModifyStructure && schemaEditEnabled}
                    onDetachAssignment={handleDetachAssignment}
                    canPromoteToRoot={canModifyStructure && schemaEditEnabled && detail.unit.parent_id != null}
                    onPromoteToRoot={() => {
                      void handleMoveNode(detail.unit.id, null);
                    }}
                  />
                ) : (
                  <div className="flex h-full min-h-[240px] items-center justify-center rounded-xl border border-dashed border-[#d8e3d9] bg-[#fafdf9] text-center text-[12.5px] text-[#5f6d61]">
                    Seleziona un&apos;unità nell&apos;albero per vederne responsabile e persone.
                  </div>
                )}
                <AssignmentInboxPanel
                  selectedNode={selectedNode}
                  selectedSummary={selectedSummary}
                  linkableNodes={visibleFlatTree}
                  operatorUsers={operatorUsers}
                  assignedUserIds={assignedUserIds}
                  canModifyStructure={canModifyStructure}
                  editEnabled={schemaEditEnabled}
                  assignMode={userDropMode}
                  onAssignModeChange={setUserDropMode}
                  onToggleEdit={handleToggleSchemaEdit}
                  onSelectNode={setSelectedId}
                  onConnectSelectedToNode={handleConnectSelectedNodeToTarget}
                  onCreateUnit={() => openCreateUnit("settore", resolveSectorParentId())}
                  onCreateGenericUnit={() => openCreateUnit(resolveGenericUnitType(), selectedId)}
                  onStartDragUser={setDraggingUserId}
                  onEndDragUser={() => setDraggingUserId(null)}
                />
              </div>
            </section>
          </div>

          <OverridePanel
            overrides={overrides}
            canManage={canManage}
            onAdd={() => setShowAddOverride(true)}
          />
        </div>
      ) : view === "schema" ? (
        <div className="grid grid-cols-1 items-start gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
          <div className="min-w-0 overflow-hidden">
            <SchemaBoard
              tree={schemaRoots}
              selectedId={selectedId}
              multiSelectedIds={multiSelectedIds}
              marquee={schemaMarquee}
              collapsedIds={schemaCollapsedIds}
              collapsedPreview={collapsedPreview}
              onToggleCollapse={toggleSchemaCollapse}
              onExpandAll={() => setSchemaCollapsedIds(new Set())}
              onSelect={handleSchemaCardSelect}
              onOpenPerson={setDrawerUserId}
              draggingUserId={draggingUserId}
              draggingNodeId={schemaDragging?.nodeId ?? null}
              userDropMode={userDropMode}
              linkDraft={schemaLinkDraft}
              onBeginLink={handleBeginSchemaLink}
              onCardPointerDown={handleSchemaCardPointerDown}
              onCardContextMenu={handleSchemaCardContextMenu}
              onConnectNode={handleConnectSchemaNode}
              onDetachParent={(nodeId) => {
                void handleMoveNode(nodeId, null);
              }}
              onApplyHorizontalLayout={() => {
                void handleApplyTreeLayout("horizontal");
              }}
              onApplyVerticalLayout={() => {
                void handleApplyTreeLayout("vertical");
              }}
              onCompactVisibleArea={() => {
                void handleCompactVisibleArea();
              }}
              onAssignUser={handleAssignUserToUnit}
              meta={schemaMeta}
              orientation={schemaOrientation}
              canModifyStructure={canModifyStructure}
              editEnabled={schemaEditEnabled}
              snapToGrid={schemaSnapToGrid}
              onToggleSnapToGrid={setSchemaSnapToGrid}
              onToggleEdit={handleToggleSchemaEdit}
              scale={schemaScale}
              onZoomIn={() => setSchemaScale((current) => Math.min(1.4, Number((current + 0.1).toFixed(2))))}
              onZoomOut={() => setSchemaScale((current) => Math.max(0.4, Number((current - 0.1).toFixed(2))))}
              onFit={fitSchemaToViewport}
              onPanStart={handleSchemaPanStart}
              viewportRef={schemaViewportRef}
              contentRef={schemaContentRef}
            />
          </div>
          <AssignmentInboxPanel
            selectedNode={selectedNode}
            selectedSummary={selectedSummary}
            linkableNodes={visibleFlatTree}
            operatorUsers={operatorUsers}
            assignedUserIds={assignedUserIds}
            canModifyStructure={canModifyStructure}
            editEnabled={schemaEditEnabled}
            assignMode={userDropMode}
            onAssignModeChange={setUserDropMode}
            onToggleEdit={handleToggleSchemaEdit}
            onSelectNode={setSelectedId}
            onConnectSelectedToNode={handleConnectSelectedNodeToTarget}
            onCreateUnit={() => openCreateUnit("settore", resolveSectorParentId())}
            onCreateGenericUnit={() => openCreateUnit(resolveGenericUnitType(), selectedId)}
            onStartDragUser={setDraggingUserId}
            onEndDragUser={() => setDraggingUserId(null)}
          />
        </div>
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

      {createUnitPreset ? (
        <CreateUnitModal
          units={flatTree}
          unassignedUsers={unassignedUsers}
          defaultParentId={createUnitPreset.parentId}
          defaultType={createUnitPreset.tipo}
          onClose={() => setCreateUnitPreset(null)}
          onCreate={handleCreateUnit}
        />
      ) : null}

      {showReplaceImportConfirm ? (
        <ReplaceImportConfirmModal
          filename={pendingImportFile?.name ?? null}
          summary={pendingImportSummary}
          confirmText={replaceImportConfirmText}
          busy={importingSnapshot}
          onChangeConfirmText={setReplaceImportConfirmText}
          onClose={closeReplaceImportConfirm}
          onConfirm={() => void handleConfirmReplaceImport()}
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

      {schemaContextMenu && schemaContextNode ? (
        <div
          className="fixed z-[120] min-w-[220px] rounded-2xl border border-[#d6dfef] bg-white p-2 shadow-[0_20px_60px_rgba(15,23,42,0.18)]"
          style={{
            left: Math.max(12, Math.min(schemaContextMenu.x, viewportWidth - 240)),
            top: Math.max(12, Math.min(schemaContextMenu.y, viewportHeight - 260)),
          }}
          onPointerDown={(event) => event.stopPropagation()}
          onContextMenu={(event) => event.preventDefault()}
        >
          <div className="border-b border-[#eef2ed] px-2 pb-2">
            <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#5f6d61]">Azioni blocco</div>
            <div className="mt-1 text-[13px] font-semibold text-[#051b12]">{schemaContextNode.nome}</div>
          </div>
          <div className="mt-2 flex flex-col gap-1">
            {schemaContextNode.parent_id ? (
              <button
                type="button"
                onClick={() => {
                  setSchemaContextMenu(null);
                  void handleMoveNode(schemaContextNode.id, null);
                }}
                className="rounded-xl px-3 py-2 text-left text-[12.5px] font-medium text-[#7c3d06] hover:bg-[#fdf3e3]"
              >
                Scollega da “{flatTree.find((node) => node.id === schemaContextNode.parent_id)?.nome ?? "padre"}”
              </button>
            ) : null}
            {(schemaMeta.get(schemaContextNode.id)?.descendantIds.size ?? 0) > 1 ? (
              <button
                type="button"
                onClick={() => {
                  const subtreeIds = schemaMeta.get(schemaContextNode.id)?.descendantIds;
                  setSchemaContextMenu(null);
                  if (subtreeIds?.size) {
                    setMultiSelectedIds(new Set(subtreeIds));
                    setSelectedId(schemaContextNode.id);
                  }
                }}
                className="rounded-xl px-3 py-2 text-left text-[12.5px] font-medium text-[#0d7a66] hover:bg-[#e2f4f1]"
              >
                Seleziona sottoalbero ({schemaMeta.get(schemaContextNode.id)?.descendantIds.size} blocchi)
              </button>
            ) : null}
            {(schemaMeta.get(schemaContextNode.id)?.descendantIds.size ?? 0) > 1 || schemaCollapsedIds.has(schemaContextNode.id) ? (
              <button
                type="button"
                onClick={() => {
                  const nodeId = schemaContextNode.id;
                  setSchemaContextMenu(null);
                  toggleSchemaCollapse(nodeId);
                }}
                className="rounded-xl px-3 py-2 text-left text-[12.5px] font-medium text-[#0d7a66] hover:bg-[#e2f4f1]"
              >
                {schemaCollapsedIds.has(schemaContextNode.id)
                  ? "Esplodi sottoalbero"
                  : `Raggruppa sottoalbero (${(schemaMeta.get(schemaContextNode.id)?.descendantIds.size ?? 1) - 1} blocchi)`}
              </button>
            ) : null}
            <button
              type="button"
              onClick={() => {
                setSchemaContextMenu(null);
                handleBeginSchemaLink(schemaContextNode.id, "above");
              }}
              className="rounded-xl px-3 py-2 text-left text-[12.5px] font-medium text-[#2f5da8] hover:bg-[#eef3fb]"
            >
              Aggancia figli sotto questo blocco
            </button>
            <button
              type="button"
              onClick={() => {
                setSchemaContextMenu(null);
                handleBeginSchemaLink(schemaContextNode.id, "below");
              }}
              className="rounded-xl px-3 py-2 text-left text-[12.5px] font-medium text-[#2f5da8] hover:bg-[#eef3fb]"
            >
              Sposta sotto un altro blocco
            </button>
            {schemaMeta.get(schemaContextNode.id)?.lead?.user_id ? (
              <button
                type="button"
                onClick={() => {
                  const leadUserId = schemaMeta.get(schemaContextNode.id)?.lead?.user_id;
                  setSchemaContextMenu(null);
                  if (leadUserId != null) {
                    setDrawerUserId(leadUserId);
                  }
                }}
                className="rounded-xl px-3 py-2 text-left text-[12.5px] font-medium text-[#1D4E35] hover:bg-[#edf5f0]"
              >
                Apri scheda responsabile
              </button>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}

// --------------------------------------------------------------------------- //
function UnitDetail({
  detail,
  summary,
  onOpenPerson,
  canDetachAssignments = false,
  onDetachAssignment,
  canPromoteToRoot = false,
  onPromoteToRoot,
}: {
  detail: OrgUnitDetail;
  summary: UnitSummary;
  onOpenPerson: (id: number) => void;
  canDetachAssignments?: boolean;
  onDetachAssignment?: (assignmentId: string) => void;
  canPromoteToRoot?: boolean;
  onPromoteToRoot?: () => void;
}) {
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
          {canPromoteToRoot ? (
            <button
              type="button"
              onClick={onPromoteToRoot}
              className="ml-auto rounded-full border border-[#e7c89a] bg-white px-3 py-1.5 text-[12px] font-semibold text-[#7c3d06] transition-colors hover:bg-[#fdf3e3]"
            >
              Imposta come radice
            </button>
          ) : null}
        </div>
        {canPromoteToRoot ? (
          <div className="mt-2 text-[12px] text-[#7c3d06]">
            Rimuove il collegamento al padre e porta questa unità al livello radice dell&apos;organigramma.
          </div>
        ) : null}
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
            {directAssignments.map((a) => (
              <PersonCard
                key={a.id}
                assignment={a}
                onOpen={onOpenPerson}
                canDetach={canDetachAssignments}
                onDetach={onDetachAssignment}
              />
            ))}
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
function AssignmentInboxPanel({
  selectedNode,
  selectedSummary,
  linkableNodes,
  operatorUsers,
  assignedUserIds,
  canModifyStructure,
  editEnabled,
  assignMode,
  onAssignModeChange,
  onToggleEdit,
  onSelectNode,
  onConnectSelectedToNode,
  onCreateUnit,
  onCreateGenericUnit,
  onStartDragUser,
  onEndDragUser,
}: {
  selectedNode: OrgUnitTreeNode | null;
  selectedSummary: UnitSummary | null;
  linkableNodes: OrgUnitTreeNode[];
  operatorUsers: ApplicationUser[];
  assignedUserIds: Set<number>;
  canModifyStructure: boolean;
  editEnabled: boolean;
  assignMode: UserDropMode;
  onAssignModeChange: (mode: UserDropMode) => void;
  onToggleEdit: (enabled: boolean) => void;
  onSelectNode: (nodeId: string) => void;
  onConnectSelectedToNode: (targetId: string, mode: "above" | "below") => void;
  onCreateUnit: () => void;
  onCreateGenericUnit: () => void;
  onStartDragUser: (userId: number) => void;
  onEndDragUser: () => void;
}) {
  const [linkQuery, setLinkQuery] = useState("");
  const [operatorQuery, setOperatorQuery] = useState("");
  const filteredLinkableNodes = useMemo(() => {
    const normalizedQuery = normalizeLabel(linkQuery);
    return linkableNodes
      .filter((node) => node.id !== selectedNode?.id)
      .filter((node) => !normalizedQuery || normalizeLabel(node.nome).includes(normalizedQuery))
      .sort((left, right) => left.nome.localeCompare(right.nome, "it-IT"));
  }, [linkQuery, linkableNodes, selectedNode?.id]);
  const filteredOperatorUsers = useMemo(() => {
    const normalizedQuery = normalizeLabel(operatorQuery);
    if (!normalizedQuery) return operatorUsers;
    return operatorUsers.filter((user) =>
      normalizeLabel(`${user.full_name ?? ""} ${user.username}`).includes(normalizedQuery),
    );
  }, [operatorQuery, operatorUsers]);

  return (
    <aside className="self-start rounded-2xl border-2 border-[#c8d9e7] bg-gradient-to-b from-white to-[#fbfcfa] p-4 shadow-[0_14px_40px_rgba(15,23,42,0.06)] md:sticky md:top-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#2f5da8]">Sidebar operativa</div>
          <h3 className="mt-1 font-serif text-[18px] font-semibold text-[#051b12]">Blocchi e operatori</h3>
          <p className="mt-1 text-[12.5px] text-[#5f6d61]">
            Collega rapidamente i blocchi dal pannello laterale e trascina gli operatori disponibili nei settori corretti.
          </p>
        </div>
        {canModifyStructure ? (
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={onCreateUnit}
              className="rounded-xl border border-[#bcd9bf] bg-white px-3 py-2 text-[12.5px] font-semibold text-[#1D4E35] hover:bg-[#edf5f0]"
            >
              + Nuovo settore
            </button>
            <button
              type="button"
              onClick={onCreateGenericUnit}
              className="rounded-xl border border-[#e6ebe5] bg-white px-3 py-2 text-[12.5px] font-semibold text-[#3a4a3f] hover:bg-[#f5f9f4]"
            >
              + Nuova unità
            </button>
          </div>
        ) : null}
      </div>

      <div className="mt-3 rounded-xl border border-[#e6ebe5] bg-white p-3">
        <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#5f6d61]">Nodo selezionato</div>
        {selectedNode ? (
          <div className="mt-2 flex flex-col gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[14px] font-semibold text-[#051b12]">{selectedNode.nome}</span>
              <TypeChip tipo={selectedNode.tipo} />
            </div>
            <div className="flex flex-wrap gap-2 text-[12px] text-[#5f6d61]">
              <Pill className="border-[#d5e2d8] bg-[#edf5f0] text-[#1D4E35]">diretti {selectedSummary?.directAssignments.length ?? 0}</Pill>
              <Pill className="border-[#e6ebe5] bg-white text-[#5f6d61]">sotto-albero {selectedSummary?.subtreeAssignments.length ?? 0}</Pill>
            </div>
          </div>
        ) : (
          <div className="mt-2 text-[12.5px] text-[#5f6d61]">Seleziona un nodo in albero o schema.</div>
        )}
      </div>

      <div className="mt-3 rounded-xl border border-[#d6dfef] bg-white p-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#5f6d61]">Blocchi collegabili</div>
            <div className="mt-1 text-[12.5px] text-[#5c6d82]">
              {selectedNode
                ? <>Usa <strong>{selectedNode.nome}</strong> come blocco sorgente.</>
                : "Seleziona prima un blocco per vedere i collegamenti rapidi."}
            </div>
          </div>
          <Pill className="border-[#d6dfef] bg-[#f7f9fd] text-[#2f5da8]">{filteredLinkableNodes.length}</Pill>
        </div>
        <div className="mt-3">
          <input
            value={linkQuery}
            onChange={(event) => setLinkQuery(event.target.value)}
            placeholder="Cerca blocco da collegare…"
            className="w-full rounded-xl border border-[#e6ebe5] bg-[#fbfcfa] px-3 py-2 text-[13px] outline-none focus:border-[#1D9E75] focus:ring-2 focus:ring-[#1D9E75]/30"
          />
        </div>
        <div className="mt-3 max-h-[280px] overflow-y-auto">
          {filteredLinkableNodes.length ? (
            <div className="flex flex-col gap-2">
              {filteredLinkableNodes.map((node) => (
                <div key={node.id} className="rounded-xl border border-[#e6ebe5] bg-[#fbfcfa] p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <button
                        type="button"
                        onClick={() => onSelectNode(node.id)}
                        className="truncate text-left text-[13px] font-semibold text-[#051b12] hover:text-[#1D4E35]"
                      >
                        {node.nome}
                      </button>
                      <div className="mt-1 flex flex-wrap items-center gap-2">
                        <TypeChip tipo={node.tipo} />
                        <span className="text-[11.5px] text-[#5f6d61]">{node.person_count} persone</span>
                      </div>
                    </div>
                    {selectedNode && canModifyStructure && editEnabled ? (
                      <div className="flex shrink-0 gap-1">
                        <button
                          type="button"
                          onClick={() => void onConnectSelectedToNode(node.id, "above")}
                          className="rounded-lg border border-[#d6dfef] bg-white px-2 py-1 text-[11px] font-semibold text-[#2f5da8] hover:bg-[#eef3fb]"
                          title={`Collega ${selectedNode.nome} sopra ${node.nome}`}
                        >
                          Sopra
                        </button>
                        <button
                          type="button"
                          onClick={() => void onConnectSelectedToNode(node.id, "below")}
                          className="rounded-lg border border-[#d6dfef] bg-white px-2 py-1 text-[11px] font-semibold text-[#2f5da8] hover:bg-[#eef3fb]"
                          title={`Collega ${selectedNode.nome} sotto ${node.nome}`}
                        >
                          Sotto
                        </button>
                      </div>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-[#d8e3d9] bg-[#fafdf9] p-4 text-center text-[12.5px] text-[#5f6d61]">
              Nessun blocco disponibile con il filtro corrente.
            </div>
          )}
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => onAssignModeChange("member")}
          className={cn("rounded-xl px-3 py-2 text-[12px] font-semibold", assignMode === "member" ? "bg-[#1D4E35] text-white" : "border border-[#e6ebe5] bg-white text-[#3a4a3f]")}
        >
          Assegna persona
        </button>
        <button
          type="button"
          onClick={() => onAssignModeChange("lead")}
          className={cn("rounded-xl px-3 py-2 text-[12px] font-semibold", assignMode === "lead" ? "bg-[#7c3d06] text-white" : "border border-[#e6ebe5] bg-white text-[#3a4a3f]")}
        >
          Imposta responsabile
        </button>
        {canModifyStructure ? (
          <label className="ml-auto inline-flex items-center gap-2 rounded-xl border border-[#e7c89a] bg-white px-3 py-2 text-[12px] font-medium text-[#7c3d06]">
            <input type="checkbox" checked={editEnabled} onChange={(event) => onToggleEdit(event.target.checked)} />
            Abilita modifica
          </label>
        ) : null}
      </div>

      <div className="mt-3 text-[12px] text-[#7c3d06]">
        Tasto destro su una card: menu rapido per collegare, scollegare o portare il blocco in radice.
      </div>

      <div className="mt-3 flex items-center justify-between gap-3">
        <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#5f6d61]">Operatori</div>
        <Pill className="border-[#d5e2d8] bg-[#edf5f0] text-[#1D4E35]">{filteredOperatorUsers.length}</Pill>
      </div>
      <div className="mt-2">
        <input
          value={operatorQuery}
          onChange={(event) => setOperatorQuery(event.target.value)}
          placeholder="Cerca operatore…"
          className="w-full rounded-xl border border-[#e6ebe5] bg-[#fbfcfa] px-3 py-2 text-[13px] outline-none focus:border-[#1D9E75] focus:ring-2 focus:ring-[#1D9E75]/30"
        />
      </div>
      <div className="mt-3 max-h-[420px] overflow-y-auto">
        {filteredOperatorUsers.length ? (
          <div className="flex flex-col gap-2">
            {filteredOperatorUsers.map((user) => {
              const isAssigned = assignedUserIds.has(user.id);
              return (
                <div
                  key={user.id}
                  data-testid={`unassigned-user-${user.id}`}
                  draggable={canModifyStructure && editEnabled}
                  onDragStart={() => onStartDragUser(user.id)}
                  onDragEnd={onEndDragUser}
                  className={cn(
                    "rounded-xl border bg-white p-3 transition-all",
                    canModifyStructure && editEnabled ? "cursor-grab border-[#d5e2d8] hover:border-[#1D9E75]" : "border-[#e6ebe5] opacity-80",
                  )}
                >
                  <div className="flex items-center gap-2.5">
                    <Avatar name={user.full_name ?? user.username} size={34} tone={isAssigned ? "amber" : "green"} />
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-[13px] font-semibold text-[#051b12]">{user.full_name ?? user.username}</div>
                      <div className="truncate text-[11.5px] text-[#5f6d61]">{user.username} · {user.role}</div>
                    </div>
                    <Pill
                      className={
                        isAssigned
                          ? "shrink-0 border-[#e7c89a] bg-[#fdf3e3] text-[#7c3d06]"
                          : "shrink-0 border-[#d5e2d8] bg-[#edf5f0] text-[#1D4E35]"
                      }
                    >
                      {isAssigned ? "assegnato" : "da assegnare"}
                    </Pill>
                  </div>
                  <div className="mt-2 text-[11.5px] text-[#5f6d61]">
                    {assignMode === "lead" ? "Drop su un nodo per impostarlo come responsabile." : "Drop su un nodo per assegnarlo all'unità."}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-[#d8e3d9] bg-[#fafdf9] p-6 text-center text-[12.5px] text-[#5f6d61]">
            {operatorQuery ? "Nessun operatore corrisponde alla ricerca." : "Nessun application user attivo disponibile."}
          </div>
        )}
      </div>
    </aside>
  );
}

function CreateUnitModal({
  units,
  unassignedUsers,
  defaultParentId,
  defaultType,
  onClose,
  onCreate,
}: {
  units: OrgUnitTreeNode[];
  unassignedUsers: ApplicationUser[];
  defaultParentId: string | null;
  defaultType: OrgUnitType;
  onClose: () => void;
  onCreate: (payload: OrgUnitCreateInput, responsibleUserId: number | null) => Promise<void>;
}) {
  const [nome, setNome] = useState("");
  const [tipo, setTipo] = useState<OrgUnitType>(defaultType);
  const [parentId, setParentId] = useState<string | "">(defaultParentId ?? "");
  const [responsibleUserId, setResponsibleUserId] = useState<number | "">("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const inputCls = "w-full rounded-xl border border-[#e6ebe5] bg-[#fbfcfa] px-3 py-2 text-[13px] outline-none focus:border-[#1D9E75] focus:ring-2 focus:ring-[#1D9E75]/30";
  const parentUnit = useMemo(
    () => (parentId ? units.find((unit) => unit.id === parentId) ?? null : null),
    [parentId, units],
  );

  useEffect(() => {
    setTipo(defaultType);
  }, [defaultType]);

  useEffect(() => {
    setParentId(defaultParentId ?? "");
  }, [defaultParentId]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!nome.trim()) {
      setErr("Inserisci il nome della nuova unità.");
      return;
    }
    if (tipo === "settore" && parentUnit && parentUnit.tipo === "squadra") {
      setErr("Un settore non può essere creato sotto una squadra.");
      return;
    }
    setSaving(true);
    setErr(null);
    try {
      await onCreate(
        {
          nome: nome.trim(),
          tipo,
          parent_id: parentId || null,
          source: "manuale",
          is_active: true,
        },
        responsibleUserId === "" ? null : Number(responsibleUserId),
      );
    } catch (error) {
      setErr(error instanceof Error ? error.message : "Errore di creazione");
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-[#051b12]/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-lg rounded-2xl border border-[#bcd9bf] bg-white p-5 shadow-[0_24px_70px_rgba(15,23,42,0.25)]">
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#edf5f0] text-[#1D4E35]"><FolderIcon className="h-4 w-4" /></span>
          <h3 className="font-serif text-[18px] font-semibold text-[#1D4E35]">Nuova unità organizzativa</h3>
        </div>
        <form className="mt-4 flex flex-col gap-3" onSubmit={submit}>
          <label className="flex flex-col gap-1">
            <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#5f6d61]">Nome</span>
            <input className={inputCls} value={nome} onChange={(event) => setNome(event.target.value)} placeholder="Es. Settore Manutenzione Sud" />
          </label>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <label className="flex flex-col gap-1">
              <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#5f6d61]">Tipo</span>
              <select className={inputCls} value={tipo} onChange={(event) => setTipo(event.target.value as OrgUnitType)}>
                {TYPE_FILTERS.filter((item) => item.value !== "all").map((item) => (
                  <option key={item.value} value={item.value}>{item.label}</option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#5f6d61]">Unità padre</span>
              <select className={inputCls} value={parentId} onChange={(event) => setParentId(event.target.value)}>
                <option value="">Radice</option>
                {units.map((unit) => <option key={unit.id} value={unit.id}>{unit.nome}</option>)}
              </select>
            </label>
          </div>
          {tipo === "settore" ? (
            <div className="rounded-xl border border-[#d6dfef] bg-[#f7f9fd] px-3 py-2 text-[12px] text-[#2f5da8]">
              I nuovi settori sono pensati per essere agganciati a una direzione o a un distretto. Seleziona il padre corretto per generare subito il sotto-albero operativo.
            </div>
          ) : null}
          <label className="flex flex-col gap-1">
            <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#5f6d61]">Responsabile iniziale</span>
            <select className={inputCls} value={responsibleUserId} onChange={(event) => setResponsibleUserId(event.target.value ? Number(event.target.value) : "")}>
              <option value="">Nessuno</option>
              {unassignedUsers.map((user) => (
                <option key={user.id} value={user.id}>{user.full_name ?? user.username}</option>
              ))}
            </select>
          </label>
          {err ? <p className="text-[12px] text-[#ba1a1a]">{err}</p> : null}
          <div className="mt-1 flex items-center justify-end gap-2">
            <button type="button" onClick={onClose} className="rounded-xl border border-[#e6ebe5] px-3.5 py-2 text-[12.5px] font-medium text-[#3a4a3f] hover:bg-[#f5f9f4]">Annulla</button>
            <button type="submit" disabled={saving} className="rounded-xl bg-[#1D4E35] px-3.5 py-2 text-[12.5px] font-semibold text-white hover:bg-[#163d29] disabled:opacity-60">
              {saving ? "Creazione…" : "Crea unità"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// --------------------------------------------------------------------------- //
function ReplaceImportConfirmModal({
  filename,
  summary,
  confirmText,
  busy,
  onChangeConfirmText,
  onClose,
  onConfirm,
}: {
  filename: string | null;
  summary: ImportSnapshotAnalysis | null;
  confirmText: string;
  busy: boolean;
  onChangeConfirmText: (value: string) => void;
  onClose: () => void;
  onConfirm: () => void;
}) {
  const confirmationPhrase = "SOSTITUISCI";
  const hasBlockingIssues = Boolean(summary?.errors.length);
  const canConfirm = confirmText.trim() === confirmationPhrase && !busy && !hasBlockingIssues;
  const inputCls = "w-full rounded-xl border border-[#e6d3d3] bg-[#fff8f8] px-3 py-2 text-[13px] outline-none focus:border-[#ba1a1a] focus:ring-2 focus:ring-[#ba1a1a]/20";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-[#051b12]/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-lg rounded-2xl border border-[#e6d3d3] bg-white p-5 shadow-[0_24px_70px_rgba(15,23,42,0.25)]">
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#fdf2f2] text-[#ba1a1a]">!</span>
          <h3 className="font-serif text-[18px] font-semibold text-[#7a1d1d]">Conferma sostituzione organigramma</h3>
        </div>
        <div className="mt-4 rounded-xl border border-[#f1d0d0] bg-[#fff7f7] p-4 text-[12.5px] text-[#7a1d1d]">
          <p className="font-semibold">Questa operazione sostituisce l&apos;organigramma canonico corrente.</p>
          <p className="mt-2">Verranno rimpiazzate unità, assegnazioni e override presenti in GAIA con il contenuto del file JSON selezionato.</p>
          {filename ? <p className="mt-2 text-[12px] text-[#9a3b3b]">File selezionato: <span className="font-medium">{filename}</span></p> : null}
        </div>
        {summary ? (
          <>
            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div className="rounded-xl border border-[#f1d0d0] bg-[#fff7f7] px-3 py-3">
                <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#9a3b3b]">Schema</p>
                <p className="mt-1 text-lg font-semibold text-[#7a1d1d]">{summary.schemaVersion ?? "n/d"}</p>
              </div>
              <div className="rounded-xl border border-[#f1d0d0] bg-[#fff7f7] px-3 py-3">
                <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#9a3b3b]">Unità</p>
                <p className="mt-1 text-lg font-semibold text-[#7a1d1d]">{summary.units}</p>
              </div>
              <div className="rounded-xl border border-[#f1d0d0] bg-[#fff7f7] px-3 py-3">
                <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#9a3b3b]">Assegnazioni</p>
                <p className="mt-1 text-lg font-semibold text-[#7a1d1d]">{summary.assignments}</p>
              </div>
              <div className="rounded-xl border border-[#f1d0d0] bg-[#fff7f7] px-3 py-3">
                <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#9a3b3b]">Override</p>
                <p className="mt-1 text-lg font-semibold text-[#7a1d1d]">{summary.overrides}</p>
              </div>
            </div>
            {summary.errors.length ? (
              <div className="mt-4 rounded-xl border border-[#e8b6b6] bg-[#fff1f1] p-4 text-[12.5px] text-[#7a1d1d]">
                <p className="font-semibold">Problemi bloccanti nel file JSON</p>
                <ul className="mt-2 list-disc pl-5">
                  {summary.errors.map((issue) => (
                    <li key={issue}>{issue}</li>
                  ))}
                </ul>
                <p className="mt-2 text-[12px] text-[#9a3b3b]">
                  Correggi il file prima di usare la modalità replace.
                </p>
              </div>
            ) : null}
            {summary.warnings.length ? (
              <div className="mt-4 rounded-xl border border-[#ecd9a2] bg-[#fff9ea] p-4 text-[12.5px] text-[#72510b]">
                <p className="font-semibold">Avvisi da verificare</p>
                <ul className="mt-2 list-disc pl-5">
                  {summary.warnings.map((issue) => (
                    <li key={issue}>{issue}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </>
        ) : null}
        <label className="mt-4 flex flex-col gap-1">
          <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#9a3b3b]">
            Digita {confirmationPhrase} per continuare
          </span>
          <input
            className={inputCls}
            value={confirmText}
            onChange={(event) => onChangeConfirmText(event.target.value)}
            placeholder={confirmationPhrase}
          />
        </label>
        <div className="mt-5 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-[#e6ebe5] px-3.5 py-2 text-[12.5px] font-medium text-[#3a4a3f] hover:bg-[#f5f9f4]"
          >
            Annulla
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={!canConfirm}
            className="rounded-xl bg-[#ba1a1a] px-3.5 py-2 text-[12.5px] font-semibold text-white hover:bg-[#a11414] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {busy ? "Import..." : "Conferma replace"}
          </button>
        </div>
      </div>
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
