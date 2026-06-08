"use client";

/**
 * MOCKUP UI — Sezione "Organigramma" della piattaforma GAIA
 * ----------------------------------------------------------
 * Artifact self-contained ad alta fedeltà. Solo frontend, dati finti inline,
 * nessuna chiamata di rete. Route: /gaia/organigramma/mockup
 *
 * Nota: lucide-react non è installato in questo repo, quindi le icone sono
 * componenti SVG inline con gli stessi nomi di lucide-react. Per usare lucide:
 *   npm i lucide-react
 *   import { Search, Filter, ChevronRight, ... } from "lucide-react";
 * e rimuovere il blocco "Icone" qui sotto.
 */

import { useMemo, useState } from "react";

/* ============================================================
 * Tipi (layer canonico + bridge)
 * ============================================================ */

type OrgUnitType = "direzione" | "distretto" | "settore" | "squadra";
type Source = "whitecompany" | "manuale" | "bridge_team";
type RbacRole = "super_admin" | "admin" | "reviewer" | "viewer" | "operator";
type Scope = "read" | "approve" | "full";
type OverrideStatus = "attivo" | "programmato" | "scaduto";

interface OrgUnit {
  id: string;
  nome: string;
  tipo: OrgUnitType;
  parentId: string | null;
  source: Source;
  wcAreaId?: number | null;
  legacyTeamId?: string | null;
}

interface Person {
  userId: number;
  fullName: string;
  email: string;
  rbacRole: RbacRole;
  isActive: boolean;
}

interface OrgAssignment {
  id: string;
  userId: number;
  orgUnitId: string;
  managerUserId: number | null;
  title: string;
  active: boolean;
  source: Source;
}

interface OrgVisibilityOverride {
  id: string;
  viewerUserId: number;
  targetType: "user" | "org_unit";
  targetId: number | string;
  scope: Scope;
  motivo: string;
  validFrom: string;
  validTo: string | null;
}

/* ============================================================
 * Dati finti — Consorzio di Bonifica dell'Oristanese
 * ============================================================ */

const TODAY = "2026-06-08";

const ORG_UNITS: OrgUnit[] = [
  { id: "u1", nome: "Direzione Generale", tipo: "direzione", parentId: null, source: "manuale" },
  { id: "u2", nome: "Direzione Esercizio e Manutenzione", tipo: "direzione", parentId: "u1", source: "manuale" },
  { id: "u3", nome: "Distretto Irriguo Tirso–Arborea", tipo: "distretto", parentId: "u2", source: "whitecompany", wcAreaId: 101 },
  { id: "u4", nome: "Distretto Irriguo del Sinis", tipo: "distretto", parentId: "u2", source: "whitecompany", wcAreaId: 102 },
  { id: "u5", nome: "Settore Idraulico", tipo: "settore", parentId: "u3", source: "whitecompany", wcAreaId: 201 },
  { id: "u6", nome: "Settore Elettromeccanico", tipo: "settore", parentId: "u3", source: "manuale" },
  { id: "u7", nome: "Settore Movimento Terra", tipo: "settore", parentId: "u4", source: "whitecompany", wcAreaId: 202 },
  { id: "u8", nome: "Squadra Manutenzione A", tipo: "squadra", parentId: "u5", source: "bridge_team", legacyTeamId: "TEAM-014" },
  { id: "u9", nome: "Squadra Reperibilità", tipo: "squadra", parentId: "u5", source: "manuale" },
  { id: "u10", nome: "Squadra Sollevamenti", tipo: "squadra", parentId: "u6", source: "whitecompany", wcAreaId: 301 },
  { id: "u11", nome: "Squadra Scavi", tipo: "squadra", parentId: "u7", source: "bridge_team", legacyTeamId: "TEAM-022" },
];

const PEOPLE: Person[] = [
  { userId: 1, fullName: "Mario Sanna", email: "m.sanna@cbonorate.it", rbacRole: "super_admin", isActive: true },
  { userId: 2, fullName: "Lucia Pinna", email: "l.pinna@cbonorate.it", rbacRole: "admin", isActive: true },
  { userId: 3, fullName: "Giovanni Loi", email: "g.loi@cbonorate.it", rbacRole: "reviewer", isActive: true },
  { userId: 4, fullName: "Antonio Murru", email: "a.murru@cbonorate.it", rbacRole: "reviewer", isActive: true },
  { userId: 5, fullName: "Paolo Carta", email: "p.carta@cbonorate.it", rbacRole: "operator", isActive: true },
  { userId: 6, fullName: "Sergio Melis", email: "s.melis@cbonorate.it", rbacRole: "operator", isActive: true },
  { userId: 7, fullName: "Franco Atzeni", email: "f.atzeni@cbonorate.it", rbacRole: "operator", isActive: true },
  { userId: 8, fullName: "Marco Deidda", email: "m.deidda@cbonorate.it", rbacRole: "reviewer", isActive: true },
  { userId: 9, fullName: "Roberto Sanna", email: "r.sanna@cbonorate.it", rbacRole: "operator", isActive: false },
  { userId: 10, fullName: "Davide Corona", email: "d.corona@cbonorate.it", rbacRole: "operator", isActive: false },
  { userId: 11, fullName: "Stefano Piras", email: "s.piras@cbonorate.it", rbacRole: "reviewer", isActive: true },
  { userId: 12, fullName: "Luca Sechi", email: "l.sechi@cbonorate.it", rbacRole: "operator", isActive: true },
  { userId: 13, fullName: "Giuseppe Cossu", email: "g.cossu@cbonorate.it", rbacRole: "operator", isActive: true },
  { userId: 14, fullName: "Anna Cabras", email: "a.cabras@cbonorate.it", rbacRole: "viewer", isActive: true },
  { userId: 15, fullName: "Elena Floris", email: "e.floris@cbonorate.it", rbacRole: "admin", isActive: true },
  { userId: 16, fullName: "Marta Usai", email: "m.usai@cbonorate.it", rbacRole: "operator", isActive: true },
  { userId: 17, fullName: "Carla Mereu", email: "c.mereu@cbonorate.it", rbacRole: "operator", isActive: true },
  { userId: 18, fullName: "Bruno Loche", email: "b.loche@cbonorate.it", rbacRole: "reviewer", isActive: true },
];

const ASSIGNMENTS: OrgAssignment[] = [
  { id: "a1", userId: 1, orgUnitId: "u1", managerUserId: null, title: "Direttore Generale", active: true, source: "manuale" },
  { id: "a2", userId: 2, orgUnitId: "u2", managerUserId: 1, title: "Dirigente Esercizio", active: true, source: "manuale" },
  { id: "a3", userId: 3, orgUnitId: "u3", managerUserId: 2, title: "Caposettore Distretto", active: true, source: "whitecompany" },
  { id: "a4", userId: 15, orgUnitId: "u4", managerUserId: 2, title: "Caposettore Distretto", active: true, source: "manuale" },
  { id: "a5", userId: 4, orgUnitId: "u5", managerUserId: 3, title: "Caposettore", active: true, source: "whitecompany" },
  { id: "a6", userId: 5, orgUnitId: "u8", managerUserId: 4, title: "Operatore idraulico", active: true, source: "bridge_team" },
  { id: "a7", userId: 6, orgUnitId: "u8", managerUserId: 4, title: "Operatore idraulico", active: true, source: "whitecompany" },
  { id: "a8", userId: 9, orgUnitId: "u8", managerUserId: 4, title: "Autista", active: false, source: "manuale" },
  { id: "a9", userId: 16, orgUnitId: "u9", managerUserId: 4, title: "Operatrice reperibilità", active: true, source: "manuale" },
  { id: "a10", userId: 8, orgUnitId: "u6", managerUserId: 3, title: "Caposettore", active: true, source: "manuale" },
  { id: "a11", userId: 7, orgUnitId: "u10", managerUserId: 8, title: "Elettromeccanico", active: true, source: "whitecompany" },
  { id: "a12", userId: 17, orgUnitId: "u10", managerUserId: 8, title: "Operatrice sollevamenti", active: true, source: "whitecompany" },
  { id: "a13", userId: 11, orgUnitId: "u7", managerUserId: 15, title: "Caposettore", active: true, source: "whitecompany" },
  { id: "a14", userId: 12, orgUnitId: "u11", managerUserId: 11, title: "Operatore scavi", active: true, source: "bridge_team" },
  { id: "a15", userId: 10, orgUnitId: "u11", managerUserId: 11, title: "Operaio", active: false, source: "whitecompany" },
  { id: "a16", userId: 13, orgUnitId: "u11", managerUserId: 11, title: "Autista", active: true, source: "manuale" },
  { id: "a17", userId: 14, orgUnitId: "u1", managerUserId: 1, title: "Responsabile HR", active: true, source: "manuale" },
  { id: "a18", userId: 18, orgUnitId: "u6", managerUserId: 3, title: "Caposettore (sostituto)", active: true, source: "manuale" },
];

const OVERRIDES: OrgVisibilityOverride[] = [
  {
    id: "ov1",
    viewerUserId: 14, // Anna Cabras — Responsabile HR
    targetType: "org_unit",
    targetId: "u1", // tutta la Direzione Generale
    scope: "read",
    motivo: "HR vede tutto",
    validFrom: "2026-01-01",
    validTo: null,
  },
  {
    id: "ov2",
    viewerUserId: 15, // Elena Floris — admin operativo
    targetType: "org_unit",
    targetId: "u4", // Distretto Irriguo del Sinis
    scope: "full",
    motivo: "Gestione operativa Sinis",
    validFrom: "2026-03-01",
    validTo: null,
  },
  {
    id: "ov3",
    viewerUserId: 18, // Bruno Loche — caposettore sostituto
    targetType: "org_unit",
    targetId: "u8", // Squadra Manutenzione A
    scope: "approve",
    motivo: "Sostituzione ferie",
    validFrom: "2026-06-02",
    validTo: "2026-06-16",
  },
  {
    id: "ov4",
    viewerUserId: 8, // Marco Deidda
    targetType: "org_unit",
    targetId: "u11", // Squadra Scavi
    scope: "read",
    motivo: "Supporto temporaneo cantiere scavi",
    validFrom: "2026-04-01",
    validTo: "2026-05-31",
  },
  {
    id: "ov5",
    viewerUserId: 17, // Carla Mereu
    targetType: "org_unit",
    targetId: "u9", // Squadra Reperibilità
    scope: "read",
    motivo: "Turnazione reperibilità estiva",
    validFrom: "2026-07-01",
    validTo: "2026-09-30",
  },
];

/* ============================================================
 * Icone SVG inline (drop-in con nomi lucide-react)
 * ============================================================ */

type IconProps = { className?: string; strokeWidth?: number };
const baseIcon = (children: React.ReactNode) =>
  function Icon({ className, strokeWidth = 1.75 }: IconProps) {
    return (
      <svg
        className={className}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        {children}
      </svg>
    );
  };

const Search = baseIcon(<><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></>);
const ChevronRight = baseIcon(<path d="m9 6 6 6-6 6" />);
const Network = baseIcon(<><rect x="9" y="2" width="6" height="6" rx="1" /><rect x="2" y="16" width="6" height="6" rx="1" /><rect x="16" y="16" width="6" height="6" rx="1" /><path d="M12 8v4M5 16v-2a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v2" /></>);
const Eye = baseIcon(<><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" /><circle cx="12" cy="12" r="3" /></>);
const Users = baseIcon(<><path d="M16 19v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 19v-2a4 4 0 0 0-3-3.87M16 3.13A4 4 0 0 1 16 11" /></>);
const FolderTree = baseIcon(<><path d="M20 10a1 1 0 0 0 1-1V6a1 1 0 0 0-1-1h-2.5a1 1 0 0 1-.8-.4l-.9-1.2A1 1 0 0 0 15 3h-2a1 1 0 0 0-1 1v5a1 1 0 0 0 1 1Z" /><path d="M20 21a1 1 0 0 0 1-1v-3a1 1 0 0 0-1-1h-7a1 1 0 0 0-1 1v3a1 1 0 0 0 1 1Z" /><path d="M3 5a2 2 0 0 0 2 2h3M3 3v13a2 2 0 0 0 2 2h3" /></>);
const ShieldAlert = baseIcon(<><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1Z" /><path d="M12 8v4M12 16h.01" /></>);
const Plus = baseIcon(<path d="M5 12h14M12 5v14" />);
const X = baseIcon(<path d="M18 6 6 18M6 6l12 12" />);
const UserRound = baseIcon(<><circle cx="12" cy="8" r="5" /><path d="M20 21a8 8 0 0 0-16 0" /></>);
const ArrowUpRight = baseIcon(<path d="M7 17 17 7M7 7h10v10" />);
const CornerDownRight = baseIcon(<path d="m15 10 5 5-5 5M4 4v7a4 4 0 0 0 4 4h12" />);
const CircleDot = baseIcon(<><circle cx="12" cy="12" r="10" /><circle cx="12" cy="12" r="2.5" fill="currentColor" stroke="none" /></>);
const Link2 = baseIcon(<><path d="M9 17H7A5 5 0 0 1 7 7h2M15 7h2a5 5 0 0 1 0 10h-2" /><path d="M8 12h8" /></>);
const Filter = baseIcon(<path d="M22 3H2l8 9.46V19l4 2v-8.54Z" />);
const ClockAlert = baseIcon(<><circle cx="10" cy="13" r="8" /><path d="M10 9v4l2.5 1.5M22 9v4M22 17h.01" /></>);
const Check = baseIcon(<path d="M20 6 9 17l-5-5" />);
const Building2 = baseIcon(<><path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z" /><path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2M10 6h4M10 10h4M10 14h4M10 18h4" /></>);

/* ============================================================
 * Helper / indici
 * ============================================================ */

const PEOPLE_BY_ID = new Map(PEOPLE.map((p) => [p.userId, p]));
const UNIT_BY_ID = new Map(ORG_UNITS.map((u) => [u.id, u]));

function initials(name: string): string {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("");
}

function childrenOf(unitId: string | null): OrgUnit[] {
  return ORG_UNITS.filter((u) => u.parentId === unitId);
}

function assignmentsOfUnit(unitId: string): OrgAssignment[] {
  return ASSIGNMENTS.filter((a) => a.orgUnitId === unitId);
}

function descendantUnitIds(unitId: string): Set<string> {
  const out = new Set<string>([unitId]);
  const stack = [unitId];
  while (stack.length) {
    const cur = stack.pop()!;
    for (const child of childrenOf(cur)) {
      if (!out.has(child.id)) {
        out.add(child.id);
        stack.push(child.id);
      }
    }
  }
  return out;
}

function ancestorPath(unitId: string): OrgUnit[] {
  const path: OrgUnit[] = [];
  let cur: OrgUnit | undefined = UNIT_BY_ID.get(unitId);
  while (cur) {
    path.unshift(cur);
    cur = cur.parentId ? UNIT_BY_ID.get(cur.parentId) : undefined;
  }
  return path;
}

function unitResponsabile(unitId: string): Person | undefined {
  const members = assignmentsOfUnit(unitId).filter((a) => a.active);
  const leader = members.find((a) => /capo|dirigent|direttore|responsabile/i.test(a.title));
  if (leader) return PEOPLE_BY_ID.get(leader.userId);
  // altrimenti: il manager comune dei membri (spesso nell'unità padre)
  const mgrCount = new Map<number, number>();
  for (const m of members) {
    if (m.managerUserId != null) mgrCount.set(m.managerUserId, (mgrCount.get(m.managerUserId) ?? 0) + 1);
  }
  let best: number | null = null;
  let bestN = 0;
  for (const [id, n] of mgrCount) {
    if (n > bestN) {
      best = id;
      bestN = n;
    }
  }
  return best != null ? PEOPLE_BY_ID.get(best) : undefined;
}

function overrideStatus(o: OrgVisibilityOverride): OverrideStatus {
  if (o.validFrom > TODAY) return "programmato";
  if (o.validTo && o.validTo < TODAY) return "scaduto";
  return "attivo";
}

function overrideTargetLabel(o: OrgVisibilityOverride): string {
  if (o.targetType === "org_unit") return UNIT_BY_ID.get(String(o.targetId))?.nome ?? String(o.targetId);
  return PEOPLE_BY_ID.get(Number(o.targetId))?.fullName ?? `Utente #${o.targetId}`;
}

const TYPE_META: Record<OrgUnitType, { label: string; dot: string; chip: string }> = {
  direzione: { label: "Direzione", dot: "#1D4E35", chip: "bg-[#D3EAD4] text-[#163d29] border-[#bcd9bf]" },
  distretto: { label: "Distretto", dot: "#1D9E75", chip: "bg-[#e0f3ec] text-[#0f6a4e] border-[#bfe5d6]" },
  settore: { label: "Settore", dot: "#3b82a6", chip: "bg-[#e3f0f5] text-[#215a72] border-[#c4e0ea]" },
  squadra: { label: "Squadra", dot: "#8a7bb8", chip: "bg-[#efeaf7] text-[#574a78] border-[#ddd2ee]" },
};

const SCOPE_META: Record<Scope, string> = { read: "Lettura", approve: "Approvazione", full: "Completo" };

function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}

/* ============================================================
 * Atomi UI
 * ============================================================ */

function Pill({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium leading-none ${className}`}
    >
      {children}
    </span>
  );
}

function SourceBadge({ unit, assignment }: { unit?: OrgUnit; assignment?: OrgAssignment }) {
  const source = unit?.source ?? assignment?.source ?? "manuale";
  if (source === "whitecompany") {
    return (
      <Pill className="border-[#bfe5e0] bg-[#e2f4f1] text-[#0d7a66]">
        <span className="rounded-full bg-[#1D9E75] px-1 text-[9px] font-bold text-white">WC</span>
        WhiteCompany
        {unit?.wcAreaId ? <span className="text-[#0d7a66]/70">· area {unit.wcAreaId}</span> : null}
      </Pill>
    );
  }
  if (source === "bridge_team") {
    return (
      <Pill className="border-[#d8d2ee] bg-[#efeaf7] text-[#574a78]">
        <Link2 className="h-3 w-3" />
        Bridge legacy
        {unit?.legacyTeamId ? <span className="text-[#574a78]/70">· {unit.legacyTeamId}</span> : null}
      </Pill>
    );
  }
  return (
    <Pill className="border-[#d5e2d8] bg-[#edf5f0] text-[#1D4E35]">
      <Check className="h-3 w-3" /> Manuale
    </Pill>
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

function StatusDot({ active }: { active: boolean }) {
  return (
    <Pill
      className={
        active
          ? "border-[#bfe5d6] bg-[#e0f3ec] text-[#0f6a4e]"
          : "border-[#e6d3d3] bg-[#f7ecec] text-[#9a3b3b]"
      }
    >
      <span className={`h-1.5 w-1.5 rounded-full ${active ? "bg-[#1D9E75]" : "bg-[#ba1a1a]"}`} />
      {active ? "Attivo" : "Inattivo"}
    </Pill>
  );
}

function Avatar({ name, size = 36, tone = "green" }: { name: string; size?: number; tone?: "green" | "amber" }) {
  const styles =
    tone === "amber"
      ? { background: "#fdebd0", color: "#92400e", border: "#f3d29a" }
      : { background: "#D3EAD4", color: "#1D4E35", border: "#bcd9bf" };
  return (
    <span
      className="inline-flex shrink-0 items-center justify-center rounded-full border font-semibold"
      style={{
        width: size,
        height: size,
        fontSize: size * 0.36,
        background: styles.background,
        color: styles.color,
        borderColor: styles.border,
      }}
    >
      {initials(name)}
    </span>
  );
}

function OverrideStatusPill({ status }: { status: OverrideStatus }) {
  const map: Record<OverrideStatus, string> = {
    attivo: "border-[#e7c89a] bg-[#fdf3e3] text-[#b45309]",
    programmato: "border-[#c4d3ea] bg-[#eef3fb] text-[#2f5da8]",
    scaduto: "border-[#dcdcdc] bg-[#f4f4f4] text-[#6b6b6b]",
  };
  const label = { attivo: "Attivo", programmato: "Programmato", scaduto: "Scaduto" }[status];
  return (
    <Pill className={map[status]}>
      <CircleDot className="h-3 w-3" /> {label}
    </Pill>
  );
}

/* ============================================================
 * Albero ricorsivo
 * ============================================================ */

interface TreeNodeProps {
  unit: OrgUnit;
  depth: number;
  expanded: Set<string>;
  selectedId: string | null;
  showProvenance: boolean;
  includeSet: Set<string> | null;
  highlightIds: Set<string>;
  onToggle: (id: string) => void;
  onSelect: (id: string) => void;
}

function TreeNode(props: TreeNodeProps) {
  const { unit, depth, expanded, selectedId, showProvenance, includeSet, highlightIds, onToggle, onSelect } = props;
  const allChildren = childrenOf(unit.id);
  const children = includeSet ? allChildren.filter((c) => includeSet.has(c.id)) : allChildren;
  const hasChildren = children.length > 0;
  const isOpen = expanded.has(unit.id);
  const isSelected = selectedId === unit.id;
  const isHit = highlightIds.has(unit.id);
  const peopleCount = assignmentsOfUnit(unit.id).filter((a) => a.active).length;

  return (
    <li>
      <div
        role="treeitem"
        aria-expanded={hasChildren ? isOpen : undefined}
        aria-selected={isSelected}
        tabIndex={0}
        onClick={() => onSelect(unit.id)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onSelect(unit.id);
          } else if (e.key === "ArrowRight" && hasChildren && !isOpen) {
            onToggle(unit.id);
          } else if (e.key === "ArrowLeft" && hasChildren && isOpen) {
            onToggle(unit.id);
          }
        }}
        className={`group flex cursor-pointer items-center gap-2 rounded-xl border px-2.5 py-2 outline-none transition-colors focus-visible:ring-2 focus-visible:ring-[#1D9E75]/60 ${
          isSelected
            ? "border-[#1D4E35] bg-[#D3EAD4]"
            : isHit
              ? "border-[#bfe5d6] bg-[#f1faf4] hover:bg-[#e9f6ee]"
              : "border-transparent hover:border-[#e6ebe5] hover:bg-[#f5f9f4]"
        }`}
        style={{ marginLeft: depth * 16 }}
      >
        <button
          type="button"
          aria-label={isOpen ? "Comprimi" : "Espandi"}
          onClick={(e) => {
            e.stopPropagation();
            if (hasChildren) onToggle(unit.id);
          }}
          className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-md ${
            hasChildren ? "text-[#1D4E35] hover:bg-white" : "text-transparent"
          }`}
          tabIndex={-1}
        >
          <ChevronRight className={`h-4 w-4 transition-transform ${isOpen ? "rotate-90" : ""}`} />
        </button>

        <span className="flex min-w-0 flex-1 flex-col gap-1">
          <span className="flex flex-wrap items-center gap-2">
            <span className="truncate text-[13.5px] font-semibold text-[#051b12]">{unit.nome}</span>
            <TypeChip tipo={unit.tipo} />
          </span>
          <span className="flex flex-wrap items-center gap-2 text-[11px] text-[#5f6d61]">
            <span className="inline-flex items-center gap-1">
              <Users className="h-3 w-3" /> {peopleCount} {peopleCount === 1 ? "persona" : "persone"}
            </span>
            <span className="inline-flex items-center gap-1">
              <FolderTree className="h-3 w-3" /> {allChildren.length} sotto-unità
            </span>
            {showProvenance ? <SourceBadge unit={unit} /> : null}
          </span>
        </span>
      </div>

      {hasChildren && isOpen ? (
        <ul role="group" className="mt-1 flex flex-col gap-1 border-l border-dashed border-[#dbe6dc]" style={{ marginLeft: depth * 16 + 16 }}>
          {children.map((c) => (
            <div key={c.id} className="-ml-px">
              <TreeNode {...props} unit={c} depth={0} />
            </div>
          ))}
        </ul>
      ) : null}
    </li>
  );
}

/* ============================================================
 * Pannello dettaglio unità
 * ============================================================ */

function PersonCard({ assignment, onOpen }: { assignment: OrgAssignment; onOpen: (userId: number) => void }) {
  const person = PEOPLE_BY_ID.get(assignment.userId);
  const manager = assignment.managerUserId != null ? PEOPLE_BY_ID.get(assignment.managerUserId) : null;
  if (!person) return null;
  return (
    <button
      type="button"
      onClick={() => onOpen(person.userId)}
      className="flex w-full items-start gap-3 rounded-xl border border-[#e6ebe5] bg-white p-3 text-left transition-all hover:border-[#bcd9bf] hover:shadow-[0_8px_24px_rgba(15,23,42,0.06)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1D9E75]/60"
    >
      <Avatar name={person.fullName} />
      <span className="min-w-0 flex-1">
        <span className="flex flex-wrap items-center gap-2">
          <span className="text-[13.5px] font-semibold text-[#051b12]">{person.fullName}</span>
          <StatusDot active={assignment.active && person.isActive} />
        </span>
        <span className="mt-0.5 block text-[12px] text-[#3a4a3f]">{assignment.title}</span>
        {manager ? (
          <span className="mt-1 inline-flex items-center gap-1 text-[11.5px] text-[#5f6d61]">
            <CornerDownRight className="h-3 w-3" /> riporta a <span className="font-medium text-[#1D4E35]">{manager.fullName}</span>
          </span>
        ) : (
          <span className="mt-1 inline-flex items-center gap-1 text-[11.5px] text-[#5f6d61]">vertice — nessun responsabile</span>
        )}
        <span className="mt-1.5 flex flex-wrap items-center gap-1.5">
          <SourceBadge assignment={assignment} />
          <Pill className="border-[#d5e2d8] bg-[#f5f9f4] text-[#5f6d61]">RBAC: {person.rbacRole}</Pill>
        </span>
      </span>
    </button>
  );
}

function UnitDetail({ unitId, onOpenPerson }: { unitId: string; onOpenPerson: (userId: number) => void }) {
  const unit = UNIT_BY_ID.get(unitId)!;
  const responsabile = unitResponsabile(unitId);
  const respAssignment = responsabile ? ASSIGNMENTS.find((a) => a.userId === responsabile.userId) : undefined;
  const members = assignmentsOfUnit(unitId);
  const path = ancestorPath(unitId);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <nav className="flex flex-wrap items-center gap-1 text-[11px] text-[#5f6d61]">
          {path.map((p, i) => (
            <span key={p.id} className="inline-flex items-center gap-1">
              {i > 0 ? <ChevronRight className="h-3 w-3 text-[#9fb0a3]" /> : null}
              <span className={i === path.length - 1 ? "font-semibold text-[#1D4E35]" : ""}>{p.nome}</span>
            </span>
          ))}
        </nav>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <h3 className="font-serif text-[20px] font-semibold text-[#051b12]">{unit.nome}</h3>
          <TypeChip tipo={unit.tipo} />
          <SourceBadge unit={unit} />
        </div>
      </div>

      {/* Responsabile in evidenza */}
      <div className="rounded-2xl border border-[#bcd9bf] bg-[#eef7ef] p-3.5">
        <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#5f6d61]">Responsabile unità</div>
        {responsabile ? (
          <div className="mt-2 flex items-center gap-3">
            <Avatar name={responsabile.fullName} size={42} />
            <div className="min-w-0">
              <div className="text-[14px] font-semibold text-[#051b12]">{responsabile.fullName}</div>
              <div className="text-[12px] text-[#3a4a3f]">{respAssignment?.title ?? "—"}</div>
              <div className="text-[11px] text-[#5f6d61]">{responsabile.email}</div>
            </div>
          </div>
        ) : (
          <div className="mt-2 text-[12.5px] text-[#5f6d61]">Nessun responsabile assegnato a questa unità.</div>
        )}
      </div>

      {/* Persone assegnate */}
      <div>
        <div className="mb-2 flex items-center justify-between">
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#5f6d61]">
            Persone assegnate · {members.length}
          </div>
        </div>
        {members.length ? (
          <div className="grid grid-cols-1 gap-2.5 xl:grid-cols-2">
            {members.map((m) => (
              <PersonCard key={m.id} assignment={m} onOpen={onOpenPerson} />
            ))}
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-[#d8e3d9] bg-[#fafdf9] p-6 text-center text-[12.5px] text-[#5f6d61]">
            Nessuna persona assegnata direttamente a questa unità.
          </div>
        )}
      </div>
    </div>
  );
}

/* ============================================================
 * Pannello Override (stile eccezione, ambra)
 * ============================================================ */

function OverridePanel({ onAdd }: { onAdd: () => void }) {
  return (
    <section className="rounded-2xl border border-[#ecd6ac] bg-gradient-to-b from-[#fffdf8] to-[#fdf6e9] p-4 shadow-[0_14px_40px_rgba(180,83,9,0.06)]">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-start gap-2.5">
          <span className="mt-0.5 flex h-8 w-8 items-center justify-center rounded-lg bg-[#fdebd0] text-[#b45309]">
            <ShieldAlert className="h-4.5 w-4.5" />
          </span>
          <div>
            <h2 className="font-serif text-[16px] font-semibold text-[#7c3d06]">Override di visibilità</h2>
            <p className="text-[12px] text-[#9a6a2f]">
              Eccezioni controllate, tenute <strong>separate</strong> dall&apos;albero canonico. Rule-based, non ruoli RBAC.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onAdd}
          className="inline-flex items-center gap-1.5 rounded-xl border border-[#e7c89a] bg-white px-3 py-2 text-[12.5px] font-semibold text-[#b45309] transition-colors hover:bg-[#fdf3e3] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#b45309]/40"
        >
          <Plus className="h-4 w-4" /> Aggiungi eccezione
        </button>
      </header>

      <ul className="mt-3 flex flex-col gap-2.5">
        {OVERRIDES.map((o) => {
          const viewer = PEOPLE_BY_ID.get(o.viewerUserId);
          const status = overrideStatus(o);
          return (
            <li
              key={o.id}
              className={`rounded-xl border bg-white/70 p-3 ${
                status === "scaduto" ? "border-[#e2e2e2] opacity-80" : "border-[#f0ddba]"
              }`}
            >
              <div className="flex flex-wrap items-center gap-2">
                <Avatar name={viewer?.fullName ?? "?"} size={28} tone="amber" />
                <span className="text-[13px] font-semibold text-[#051b12]">{viewer?.fullName}</span>
                <ArrowUpRight className="h-3.5 w-3.5 text-[#b45309]" />
                <span className="inline-flex items-center gap-1 text-[12.5px] text-[#3a4a3f]">
                  {o.targetType === "org_unit" ? <Building2 className="h-3.5 w-3.5 text-[#9a6a2f]" /> : <UserRound className="h-3.5 w-3.5 text-[#9a6a2f]" />}
                  <span className="font-medium">{overrideTargetLabel(o)}</span>
                </span>
                <Pill className="border-[#e7c89a] bg-[#fdf3e3] text-[#b45309]">scope: {SCOPE_META[o.scope]}</Pill>
                <OverrideStatusPill status={status} />
              </div>
              <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-[11.5px] text-[#9a6a2f]">
                <span className="italic text-[#7c3d06]">“{o.motivo}”</span>
                <span className="inline-flex items-center gap-1.5">
                  <ClockAlert className="h-3.5 w-3.5" />
                  {formatDate(o.validFrom)} → {o.validTo ? formatDate(o.validTo) : "senza scadenza"}
                </span>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

/* ============================================================
 * Form mock "Aggiungi eccezione"
 * ============================================================ */

function AddOverrideModal({ onClose }: { onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-[#051b12]/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-md rounded-2xl border border-[#ecd6ac] bg-white p-5 shadow-[0_24px_70px_rgba(15,23,42,0.25)]">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#fdebd0] text-[#b45309]">
              <ShieldAlert className="h-4.5 w-4.5" />
            </span>
            <h3 className="font-serif text-[16px] font-semibold text-[#7c3d06]">Nuova eccezione di visibilità</h3>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg p-1 text-[#5f6d61] hover:bg-[#f3f3f3]" aria-label="Chiudi">
            <X className="h-4.5 w-4.5" />
          </button>
        </div>

        <form
          className="mt-4 flex flex-col gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            onClose();
          }}
        >
          <Field label="Viewer (utente)">
            <select className={inputCls}>
              {PEOPLE.map((p) => (
                <option key={p.userId}>{p.fullName}</option>
              ))}
            </select>
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Tipo target">
              <select className={inputCls}>
                <option>Unità organizzativa</option>
                <option>Utente</option>
              </select>
            </Field>
            <Field label="Scope">
              <select className={inputCls}>
                <option>Lettura</option>
                <option>Approvazione</option>
                <option>Completo</option>
              </select>
            </Field>
          </div>
          <Field label="Target">
            <select className={inputCls}>
              {ORG_UNITS.map((u) => (
                <option key={u.id}>{u.nome}</option>
              ))}
            </select>
          </Field>
          <Field label="Motivo">
            <input className={inputCls} placeholder="Es. Sostituzione ferie" defaultValue="" />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Valido da">
              <input type="date" className={inputCls} defaultValue="2026-06-08" />
            </Field>
            <Field label="Valido fino a (opz.)">
              <input type="date" className={inputCls} />
            </Field>
          </div>
          <div className="mt-1 flex items-center justify-end gap-2">
            <button type="button" onClick={onClose} className="rounded-xl border border-[#e6ebe5] px-3.5 py-2 text-[12.5px] font-medium text-[#3a4a3f] hover:bg-[#f5f9f4]">
              Annulla
            </button>
            <button type="submit" className="rounded-xl bg-[#b45309] px-3.5 py-2 text-[12.5px] font-semibold text-white hover:bg-[#9a4708]">
              Crea eccezione
            </button>
          </div>
          <p className="text-center text-[11px] text-[#9aa39c]">Mockup — nessuna persistenza</p>
        </form>
      </div>
    </div>
  );
}

const inputCls =
  "w-full rounded-xl border border-[#e6ebe5] bg-[#fbfcfa] px-3 py-2 text-[13px] text-[#051b12] outline-none focus:border-[#1D9E75] focus:ring-2 focus:ring-[#1D9E75]/30";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#5f6d61]">{label}</span>
      {children}
    </label>
  );
}

/* ============================================================
 * Drawer persona
 * ============================================================ */

function PersonDrawer({ userId, onClose, onJumpToUnit }: { userId: number; onClose: () => void; onJumpToUnit: (unitId: string) => void }) {
  const person = PEOPLE_BY_ID.get(userId)!;
  const assignment = ASSIGNMENTS.find((a) => a.userId === userId);
  const unit = assignment ? UNIT_BY_ID.get(assignment.orgUnitId) : undefined;
  const manager = assignment?.managerUserId != null ? PEOPLE_BY_ID.get(assignment.managerUserId) : null;
  const path = unit ? ancestorPath(unit.id) : [];

  // Override in uscita (lui è viewer) e in entrata (lui o la sua unità è target)
  const outgoing = OVERRIDES.filter((o) => o.viewerUserId === userId);
  const incoming = OVERRIDES.filter(
    (o) =>
      (o.targetType === "user" && Number(o.targetId) === userId) ||
      (o.targetType === "org_unit" && unit && descendantUnitIds(String(o.targetId)).has(unit.id)),
  );

  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-[#051b12]/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative flex h-full w-full max-w-md flex-col overflow-y-auto border-l border-[#e6ebe5] bg-gradient-to-b from-white to-[#fbfcfa] shadow-[0_0_60px_rgba(15,23,42,0.2)]">
        <div className="sticky top-0 z-10 flex items-start justify-between gap-3 border-b border-[#e6ebe5] bg-white/90 p-4 backdrop-blur">
          <div className="flex items-center gap-3">
            <Avatar name={person.fullName} size={46} />
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-serif text-[18px] font-semibold text-[#051b12]">{person.fullName}</h3>
                <StatusDot active={person.isActive} />
              </div>
              <div className="text-[12px] text-[#5f6d61]">{person.email}</div>
            </div>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg p-1 text-[#5f6d61] hover:bg-[#f3f3f3]" aria-label="Chiudi">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex flex-col gap-4 p-4">
          {/* Assignment */}
          <section className="rounded-2xl border border-[#e6ebe5] bg-white p-3.5">
            <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#5f6d61]">Assegnazione</div>
            <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-2 text-[12.5px]">
              <dt className="text-[#5f6d61]">Unità</dt>
              <dd className="font-medium text-[#051b12]">{unit?.nome ?? "—"}</dd>
              <dt className="text-[#5f6d61]">Ruolo operativo</dt>
              <dd className="font-medium text-[#051b12]">{assignment?.title ?? "—"}</dd>
              <dt className="text-[#5f6d61]">Responsabile</dt>
              <dd className="font-medium text-[#051b12]">{manager ? manager.fullName : "— (vertice)"}</dd>
              <dt className="text-[#5f6d61]">Ruolo RBAC</dt>
              <dd>
                <Pill className="border-[#d5e2d8] bg-[#edf5f0] text-[#1D4E35]">{person.rbacRole}</Pill>
              </dd>
              <dt className="text-[#5f6d61]">Stato</dt>
              <dd>
                <StatusDot active={(assignment?.active ?? false) && person.isActive} />
              </dd>
              <dt className="text-[#5f6d61]">Provenienza</dt>
              <dd>{assignment ? <SourceBadge assignment={assignment} unit={unit} /> : "—"}</dd>
            </dl>
          </section>

          {/* Percorso nell'albero */}
          {unit ? (
            <section className="rounded-2xl border border-[#e6ebe5] bg-white p-3.5">
              <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#5f6d61]">Percorso organizzativo</div>
              <button
                type="button"
                onClick={() => onJumpToUnit(unit.id)}
                className="mt-2 flex flex-wrap items-center gap-1 text-left text-[12px] text-[#1D4E35] hover:underline"
              >
                {path.map((p, i) => (
                  <span key={p.id} className="inline-flex items-center gap-1">
                    {i > 0 ? <ChevronRight className="h-3 w-3 text-[#9fb0a3]" /> : null}
                    <span className={i === path.length - 1 ? "font-semibold" : ""}>{p.nome}</span>
                  </span>
                ))}
              </button>
            </section>
          ) : null}

          {/* Override in uscita */}
          <OverrideMiniList
            title="Override in uscita (è viewer)"
            empty="Nessuna eccezione assegnata a questa persona."
            items={outgoing}
            renderTarget={(o) => overrideTargetLabel(o)}
          />

          {/* Override in entrata */}
          <OverrideMiniList
            title="Override in entrata (la riguardano)"
            empty="Nessuna eccezione punta a questa persona o alla sua unità."
            items={incoming}
            renderTarget={(o) => `da ${PEOPLE_BY_ID.get(o.viewerUserId)?.fullName ?? "?"} su ${overrideTargetLabel(o)}`}
          />
        </div>
      </div>
    </div>
  );
}

function OverrideMiniList({
  title,
  empty,
  items,
  renderTarget,
}: {
  title: string;
  empty: string;
  items: OrgVisibilityOverride[];
  renderTarget: (o: OrgVisibilityOverride) => string;
}) {
  return (
    <section className="rounded-2xl border border-[#f0ddba] bg-[#fffdf8] p-3.5">
      <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#9a6a2f]">{title}</div>
      {items.length ? (
        <ul className="mt-2 flex flex-col gap-2">
          {items.map((o) => (
            <li key={o.id} className="flex flex-wrap items-center gap-2 text-[12px] text-[#7c3d06]">
              <OverrideStatusPill status={overrideStatus(o)} />
              <span className="font-medium">{renderTarget(o)}</span>
              <Pill className="border-[#e7c89a] bg-[#fdf3e3] text-[#b45309]">{SCOPE_META[o.scope]}</Pill>
              <span className="italic text-[#9a6a2f]">“{o.motivo}”</span>
            </li>
          ))}
        </ul>
      ) : (
        <div className="mt-2 text-[12px] text-[#9a6a2f]">{empty}</div>
      )}
    </section>
  );
}

/* ============================================================
 * Vista "Chi vede chi" — simulatore audit
 * ============================================================ */

interface VisibilityResult {
  hierUnits: Set<string>;
  overrideUnits: Map<string, OrgVisibilityOverride>;
  visiblePeople: { assignment: OrgAssignment; via: "gerarchia" | "override" }[];
}

function computeVisibility(userId: number): VisibilityResult {
  const myAssignments = ASSIGNMENTS.filter((a) => a.userId === userId && a.active);

  const hierUnits = new Set<string>();
  for (const a of myAssignments) {
    for (const d of descendantUnitIds(a.orgUnitId)) hierUnits.add(d);
  }

  const overrideUnits = new Map<string, OrgVisibilityOverride>();
  for (const o of OVERRIDES) {
    if (o.viewerUserId !== userId) continue;
    if (overrideStatus(o) !== "attivo") continue;
    if (o.targetType === "org_unit") {
      for (const d of descendantUnitIds(String(o.targetId))) {
        if (!hierUnits.has(d)) overrideUnits.set(d, o);
      }
    } else {
      const targetUser = Number(o.targetId);
      for (const ta of ASSIGNMENTS.filter((x) => x.userId === targetUser)) {
        if (!hierUnits.has(ta.orgUnitId)) overrideUnits.set(ta.orgUnitId, o);
      }
    }
  }

  const visiblePeople: VisibilityResult["visiblePeople"] = [];
  for (const a of ASSIGNMENTS) {
    if (hierUnits.has(a.orgUnitId)) visiblePeople.push({ assignment: a, via: "gerarchia" });
    else if (overrideUnits.has(a.orgUnitId)) visiblePeople.push({ assignment: a, via: "override" });
  }

  return { hierUnits, overrideUnits, visiblePeople };
}

function WhoSeesWho({ userId, onPick, onOpenPerson }: { userId: number; onPick: (id: number) => void; onOpenPerson: (id: number) => void }) {
  const result = useMemo(() => computeVisibility(userId), [userId]);
  const person = PEOPLE_BY_ID.get(userId)!;
  const myUnits = ASSIGNMENTS.filter((a) => a.userId === userId && a.active).map((a) => UNIT_BY_ID.get(a.orgUnitId)?.nome).filter(Boolean);
  const totalUnits = result.hierUnits.size + result.overrideUnits.size;

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-[320px_minmax(0,1fr)]">
      {/* Selettore utente */}
      <div className="flex flex-col gap-3">
        <div className="rounded-2xl border border-[#e6ebe5] bg-gradient-to-b from-white to-[#fbfcfa] p-4 shadow-[0_14px_40px_rgba(15,23,42,0.06)]">
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#5f6d61]">Simula la visibilità di</div>
          <div className="mt-3 flex flex-col gap-1.5">
            {PEOPLE.map((p) => (
              <button
                key={p.userId}
                type="button"
                onClick={() => onPick(p.userId)}
                className={`flex items-center gap-2.5 rounded-xl border px-2.5 py-2 text-left transition-colors ${
                  p.userId === userId
                    ? "border-[#1D4E35] bg-[#D3EAD4]"
                    : "border-transparent hover:border-[#e6ebe5] hover:bg-[#f5f9f4]"
                }`}
              >
                <Avatar name={p.fullName} size={30} />
                <span className="min-w-0">
                  <span className="block truncate text-[12.5px] font-semibold text-[#051b12]">{p.fullName}</span>
                  <span className="block truncate text-[11px] text-[#5f6d61]">{p.rbacRole}</span>
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Risultato */}
      <div className="flex flex-col gap-4">
        <div className="rounded-2xl border border-[#e6ebe5] bg-gradient-to-b from-white to-[#fbfcfa] p-4 shadow-[0_14px_40px_rgba(15,23,42,0.06)]">
          <div className="flex flex-wrap items-center gap-3">
            <Avatar name={person.fullName} size={44} />
            <div className="min-w-0">
              <div className="font-serif text-[18px] font-semibold text-[#051b12]">{person.fullName}</div>
              <div className="text-[12px] text-[#5f6d61]">
                Perimetro gerarchico: {myUnits.length ? myUnits.join(" · ") : "nessuna assegnazione attiva"}
              </div>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-3 gap-3">
            <Metric value={totalUnits} label="Unità visibili" tone="green" />
            <Metric value={result.overrideUnits.size} label="da Override" tone="amber" />
            <Metric value={result.visiblePeople.length} label="Persone visibili" tone="teal" />
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-4 text-[11.5px] text-[#5f6d61]">
            <span className="inline-flex items-center gap-1.5">
              <span className="h-3 w-3 rounded-full border border-[#bcd9bf] bg-[#D3EAD4]" /> Da gerarchia (cascata)
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-3 w-3 rounded-full border border-[#e7c89a] bg-[#fdebd0]" /> Da override (eccezione)
            </span>
          </div>
        </div>

        {/* Unità visibili */}
        <div className="rounded-2xl border border-[#e6ebe5] bg-white p-4">
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#5f6d61]">Insieme effettivo di unità</div>
          {totalUnits ? (
            <ul className="mt-3 flex flex-col gap-1.5">
              {ORG_UNITS.filter((u) => result.hierUnits.has(u.id) || result.overrideUnits.has(u.id)).map((u) => {
                const viaOverride = result.overrideUnits.has(u.id);
                const ov = result.overrideUnits.get(u.id);
                const depth = ancestorPath(u.id).length - 1;
                return (
                  <li
                    key={u.id}
                    className={`flex flex-wrap items-center gap-2 rounded-xl border px-3 py-2 ${
                      viaOverride ? "border-[#f0ddba] bg-[#fffdf8]" : "border-[#dceadf] bg-[#f3faf5]"
                    }`}
                    style={{ marginLeft: Math.min(depth, 4) * 14 }}
                  >
                    <span
                      className="h-2.5 w-2.5 rounded-full"
                      style={{ background: viaOverride ? "#e7a93f" : "#1D9E75" }}
                    />
                    <span className="text-[13px] font-semibold text-[#051b12]">{u.nome}</span>
                    <TypeChip tipo={u.tipo} />
                    {viaOverride ? (
                      <Pill className="border-[#e7c89a] bg-[#fdf3e3] text-[#b45309]">
                        override · {ov ? SCOPE_META[ov.scope] : ""}
                      </Pill>
                    ) : (
                      <Pill className="border-[#bfe5d6] bg-[#e0f3ec] text-[#0f6a4e]">gerarchia</Pill>
                    )}
                  </li>
                );
              })}
            </ul>
          ) : (
            <div className="mt-3 rounded-xl border border-dashed border-[#d8e3d9] bg-[#fafdf9] p-6 text-center text-[12.5px] text-[#5f6d61]">
              Questo utente non ha perimetro gerarchico né override attivi.
            </div>
          )}
        </div>

        {/* Persone visibili */}
        <div className="rounded-2xl border border-[#e6ebe5] bg-white p-4">
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#5f6d61]">
            Persone visibili · {result.visiblePeople.length}
          </div>
          <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
            {result.visiblePeople.map(({ assignment, via }) => {
              const p = PEOPLE_BY_ID.get(assignment.userId)!;
              return (
                <button
                  key={assignment.id}
                  type="button"
                  onClick={() => onOpenPerson(p.userId)}
                  className={`flex items-center gap-2.5 rounded-xl border px-2.5 py-2 text-left transition-colors hover:shadow-[0_8px_24px_rgba(15,23,42,0.06)] ${
                    via === "override" ? "border-[#f0ddba] bg-[#fffdf8]" : "border-[#e6ebe5] bg-white"
                  }`}
                >
                  <Avatar name={p.fullName} size={30} tone={via === "override" ? "amber" : "green"} />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[12.5px] font-semibold text-[#051b12]">{p.fullName}</span>
                    <span className="block truncate text-[11px] text-[#5f6d61]">
                      {assignment.title} · {UNIT_BY_ID.get(assignment.orgUnitId)?.nome}
                    </span>
                  </span>
                  <span
                    className={`h-2 w-2 shrink-0 rounded-full ${via === "override" ? "bg-[#e7a93f]" : "bg-[#1D9E75]"}`}
                    title={via === "override" ? "via override" : "via gerarchia"}
                  />
                </button>
              );
            })}
          </div>
        </div>
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
    <div className={`rounded-xl border p-3 ${map[tone]}`}>
      <div className="font-serif text-[24px] font-semibold leading-none">{value}</div>
      <div className="mt-1 text-[11px] font-medium">{label}</div>
    </div>
  );
}

/* ============================================================
 * Pagina
 * ============================================================ */

type ViewMode = "albero" | "chi-vede-chi";

const TYPE_FILTERS: { value: OrgUnitType | "all"; label: string }[] = [
  { value: "all", label: "Tutti" },
  { value: "direzione", label: "Direzione" },
  { value: "distretto", label: "Distretto" },
  { value: "settore", label: "Settore" },
  { value: "squadra", label: "Squadra" },
];

export default function OrganigrammaMockupPage() {
  const [view, setView] = useState<ViewMode>("albero");
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<OrgUnitType | "all">("all");
  const [showProvenance, setShowProvenance] = useState(true);
  const [expanded, setExpanded] = useState<Set<string>>(new Set(["u1", "u2", "u3"]));
  const [selectedId, setSelectedId] = useState<string | null>("u5");
  const [drawerUserId, setDrawerUserId] = useState<number | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [simUserId, setSimUserId] = useState<number>(15);

  const q = query.trim().toLowerCase();

  // Calcolo set di nodi da includere + match per ricerca/filtro
  const { includeSet, highlightIds } = useMemo(() => {
    if (!q && typeFilter === "all") return { includeSet: null as Set<string> | null, highlightIds: new Set<string>() };
    const hits = new Set<string>();
    for (const u of ORG_UNITS) {
      const matchType = typeFilter === "all" || u.tipo === typeFilter;
      const matchText =
        !q ||
        u.nome.toLowerCase().includes(q) ||
        assignmentsOfUnit(u.id).some((a) => {
          const p = PEOPLE_BY_ID.get(a.userId);
          return (
            p?.fullName.toLowerCase().includes(q) ||
            p?.email.toLowerCase().includes(q) ||
            a.title.toLowerCase().includes(q)
          );
        });
      if (matchType && matchText) hits.add(u.id);
    }
    const include = new Set<string>();
    for (const id of hits) {
      for (const anc of ancestorPath(id)) include.add(anc.id);
    }
    return { includeSet: include, highlightIds: hits };
  }, [q, typeFilter]);

  const roots = childrenOf(null).filter((u) => !includeSet || includeSet.has(u.id));
  const effectiveExpanded = includeSet ? new Set([...expanded, ...includeSet]) : expanded;

  const toggle = (id: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const jumpToUnit = (unitId: string) => {
    setView("albero");
    setSelectedId(unitId);
    setExpanded((prev) => new Set([...prev, ...ancestorPath(unitId).map((u) => u.id)]));
    setDrawerUserId(null);
  };

  return (
    <div className="min-h-screen bg-[#EAF3E8] text-[#051b12]">
      <div className="mx-auto max-w-[1400px] px-4 py-8 sm:px-6 lg:px-8">
        {/* Header */}
        <header className="mb-6">
          <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#5f6d61]">
            Governance · Organigramma
          </div>
          <h1 className="mt-1 font-serif text-[30px] font-semibold leading-tight text-[#051b12]">Organigramma operativo</h1>
          <p className="mt-1 max-w-3xl text-[13.5px] text-[#3a4a3f]">
            Gerarchia canonica delle unità (verità in GAIA), perimetro persona→responsabile→unità ed eccezioni di
            visibilità controllate. WhiteCompany è la <strong>provenienza</strong> iniziale, non la struttura finale.
          </p>
        </header>

        {/* Toolbar */}
        <div className="mb-5 rounded-2xl border border-[#e6ebe5] bg-gradient-to-b from-white to-[#fbfcfa] p-3 shadow-[0_14px_40px_rgba(15,23,42,0.06)]">
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative min-w-[220px] flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#9fb0a3]" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Cerca persona o unità…"
                className="w-full rounded-xl border border-[#e6ebe5] bg-[#fbfcfa] py-2 pl-9 pr-3 text-[13px] outline-none focus:border-[#1D9E75] focus:ring-2 focus:ring-[#1D9E75]/30"
              />
            </div>

            <div className="flex items-center gap-1.5 rounded-xl border border-[#e6ebe5] bg-[#fbfcfa] p-1">
              <Filter className="ml-1.5 h-4 w-4 text-[#9fb0a3]" />
              {TYPE_FILTERS.map((f) => (
                <button
                  key={f.value}
                  type="button"
                  onClick={() => setTypeFilter(f.value)}
                  className={`rounded-lg px-2.5 py-1.5 text-[12px] font-medium transition-colors ${
                    typeFilter === f.value ? "bg-[#1D4E35] text-white" : "text-[#3a4a3f] hover:bg-[#edf5f0]"
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>

            <button
              type="button"
              onClick={() => setShowProvenance((v) => !v)}
              className={`inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-[12.5px] font-medium transition-colors ${
                showProvenance
                  ? "border-[#bfe5e0] bg-[#e2f4f1] text-[#0d7a66]"
                  : "border-[#e6ebe5] bg-white text-[#5f6d61]"
              }`}
            >
              <span className={`flex h-4 w-7 items-center rounded-full p-0.5 transition-colors ${showProvenance ? "bg-[#1D9E75]" : "bg-[#cdd6cf]"}`}>
                <span className={`h-3 w-3 rounded-full bg-white transition-transform ${showProvenance ? "translate-x-3" : ""}`} />
              </span>
              Provenienza WhiteCompany
            </button>

            <div className="ml-auto flex items-center gap-1 rounded-xl border border-[#e6ebe5] bg-[#fbfcfa] p-1">
              <ViewToggleBtn active={view === "albero"} onClick={() => setView("albero")} icon={<Network className="h-4 w-4" />} label="Albero" />
              <ViewToggleBtn active={view === "chi-vede-chi"} onClick={() => setView("chi-vede-chi")} icon={<Eye className="h-4 w-4" />} label="Chi vede chi" />
            </div>
          </div>
        </div>

        {/* Corpo */}
        {view === "albero" ? (
          <div className="flex flex-col gap-5">
            <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
              {/* Albero */}
              <section className="rounded-2xl border border-[#e6ebe5] bg-gradient-to-b from-white to-[#fbfcfa] p-4 shadow-[0_14px_40px_rgba(15,23,42,0.06)]">
                <div className="mb-3 flex items-center gap-2">
                  <FolderTree className="h-4 w-4 text-[#1D4E35]" />
                  <h2 className="font-serif text-[15px] font-semibold text-[#051b12]">Albero organizzativo</h2>
                </div>
                {roots.length ? (
                  <ul role="tree" className="flex flex-col gap-1">
                    {roots.map((r) => (
                      <TreeNode
                        key={r.id}
                        unit={r}
                        depth={0}
                        expanded={effectiveExpanded}
                        selectedId={selectedId}
                        showProvenance={showProvenance}
                        includeSet={includeSet}
                        highlightIds={highlightIds}
                        onToggle={toggle}
                        onSelect={setSelectedId}
                      />
                    ))}
                  </ul>
                ) : (
                  <div className="rounded-xl border border-dashed border-[#d8e3d9] bg-[#fafdf9] p-8 text-center text-[12.5px] text-[#5f6d61]">
                    Nessuna unità corrisponde alla ricerca.
                  </div>
                )}
              </section>

              {/* Dettaglio */}
              <section className="rounded-2xl border border-[#e6ebe5] bg-gradient-to-b from-white to-[#fbfcfa] p-4 shadow-[0_14px_40px_rgba(15,23,42,0.06)]">
                {selectedId ? (
                  <UnitDetail unitId={selectedId} onOpenPerson={setDrawerUserId} />
                ) : (
                  <div className="flex h-full min-h-[240px] items-center justify-center rounded-xl border border-dashed border-[#d8e3d9] bg-[#fafdf9] text-center text-[12.5px] text-[#5f6d61]">
                    {"Seleziona un'unità nell'albero per vederne responsabile e persone."}
                  </div>
                )}
              </section>
            </div>

            {/* Override (separato, stile eccezione) */}
            <OverridePanel onAdd={() => setShowAdd(true)} />
          </div>
        ) : (
          <WhoSeesWho userId={simUserId} onPick={setSimUserId} onOpenPerson={setDrawerUserId} />
        )}
      </div>

      {drawerUserId != null ? (
        <PersonDrawer userId={drawerUserId} onClose={() => setDrawerUserId(null)} onJumpToUnit={jumpToUnit} />
      ) : null}
      {showAdd ? <AddOverrideModal onClose={() => setShowAdd(false)} /> : null}
    </div>
  );
}

function ViewToggleBtn({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[12.5px] font-semibold transition-colors ${
        active ? "bg-[#1D4E35] text-white" : "text-[#3a4a3f] hover:bg-[#edf5f0]"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}
