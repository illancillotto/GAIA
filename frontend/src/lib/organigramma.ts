import type { OrgUnitTreeNode, OrgUnitType } from "@/types/api";

export type SchemaScaleSetter = (scale: number) => void;

type AnimationFrameApi = {
  requestAnimationFrame: (callback: FrameRequestCallback) => number;
  cancelAnimationFrame: (handle: number) => void;
};

/** Visita in profondità: ritorna tutti i nodi dell'albero in lista piatta. */
export function flattenTree(nodes: OrgUnitTreeNode[]): OrgUnitTreeNode[] {
  const out: OrgUnitTreeNode[] = [];
  const walk = (n: OrgUnitTreeNode) => {
    out.push(n);
    n.children.forEach(walk);
  };
  nodes.forEach(walk);
  return out;
}

export function computeAutoCollapsedIds(
  tree: OrgUnitTreeNode[],
  options: {
    threshold?: number;
    expandedDepth?: number;
  } = {},
): Set<string> {
  const threshold = options.threshold ?? 12;
  const expandedDepth = options.expandedDepth ?? 1;
  const collapsed = new Set<string>();

  if (flattenTree(tree).length <= threshold) {
    return collapsed;
  }

  const visit = (nodes: OrgUnitTreeNode[], depth: number) => {
    for (const node of nodes) {
      if (depth >= expandedDepth && node.children.length) {
        collapsed.add(node.id);
      }
      visit(node.children, depth + 1);
    }
  };

  visit(tree, 0);
  return collapsed;
}

export type TreeInclusion = {
  /** id da renderizzare (match + antenati) oppure null = nessun filtro attivo. */
  includeIds: Set<string> | null;
  /** id che combaciano direttamente con ricerca/filtro (da evidenziare). */
  matchIds: Set<string>;
};

/**
 * Calcola quali nodi mostrare data una ricerca testuale e un filtro per tipo.
 * Quando entrambi sono "vuoti" ritorna includeIds=null (mostra tutto).
 * Gli antenati dei match vengono inclusi per mantenere il contesto dell'albero.
 */
export function computeTreeInclusion(
  tree: OrgUnitTreeNode[],
  query: string,
  typeFilter: OrgUnitType | "all",
): TreeInclusion {
  const q = query.trim().toLowerCase();
  if (!q && typeFilter === "all") {
    return { includeIds: null, matchIds: new Set() };
  }

  const flat = flattenTree(tree);
  const byId = new Map(flat.map((n) => [n.id, n]));
  const matchIds = new Set<string>();
  for (const n of flat) {
    const matchType = typeFilter === "all" || n.tipo === typeFilter;
    const matchText = !q || n.nome.toLowerCase().includes(q);
    if (matchType && matchText) matchIds.add(n.id);
  }

  const includeIds = new Set<string>();
  for (const id of matchIds) {
    let cur: OrgUnitTreeNode | undefined = byId.get(id);
    while (cur) {
      includeIds.add(cur.id);
      cur = cur.parent_id ? byId.get(cur.parent_id) : undefined;
    }
  }
  return { includeIds, matchIds };
}

function cloneSubtree(node: OrgUnitTreeNode, parentId: string | null): OrgUnitTreeNode {
  const children = node.children.map((child) => cloneSubtree(child, node.id));
  return {
    ...node,
    parent_id: parentId,
    child_count: children.length,
    children,
  };
}

/**
 * Estrae uno o più sotto-alberi dalla foresta originale e li promuove a radice
 * della vista corrente. Utile per focalizzare lo schema su uno o più settori.
 */
export function filterTreeByRootIds(tree: OrgUnitTreeNode[], rootIds: Set<string> | null): OrgUnitTreeNode[] {
  if (!rootIds || rootIds.size === 0) {
    return tree;
  }

  const flat = flattenTree(tree);
  return flat
    .filter((node) => rootIds.has(node.id))
    .map((node) => cloneSubtree(node, null));
}

/** Percorso (breadcrumb) radice→nodo a partire da una lista piatta. */
export function unitPath(unitId: string, units: OrgUnitTreeNode[]): OrgUnitTreeNode[] {
  const byId = new Map(units.map((u) => [u.id, u]));
  const out: OrgUnitTreeNode[] = [];
  let cur = byId.get(unitId);
  const seen = new Set<string>();
  while (cur && !seen.has(cur.id)) {
    out.unshift(cur);
    seen.add(cur.id);
    cur = cur.parent_id ? byId.get(cur.parent_id) : undefined;
  }
  return out;
}

export function fitScrollableContentToViewport(
  viewport: HTMLElement | null,
  content: HTMLElement | null,
  setScale: SchemaScaleSetter,
  animationFrameApi: AnimationFrameApi = window,
): boolean {
  if (!viewport || !content) return false;
  if (viewport.clientWidth <= 0 || viewport.clientHeight <= 0 || content.scrollWidth <= 0 || content.scrollHeight <= 0) {
    return false;
  }

  const widthRatio = (viewport.clientWidth - 32) / Math.max(content.scrollWidth, 1);
  const heightRatio = (viewport.clientHeight - 32) / Math.max(content.scrollHeight, 1);
  const nextScale = Math.max(0.45, Math.min(1.15, Math.min(widthRatio, heightRatio)));
  setScale(nextScale);
  animationFrameApi.requestAnimationFrame(() => {
    const scaledWidth = content.scrollWidth * nextScale;
    const scaledHeight = content.scrollHeight * nextScale;
    viewport.scrollLeft = Math.max((scaledWidth - viewport.clientWidth) / 2, 0);
    viewport.scrollTop = Math.max((scaledHeight - viewport.clientHeight) / 2, 0);
  });
  return true;
}

export function scheduleScrollableContentFit(
  onFit: () => void,
  frames = 4,
  onComplete: () => void = () => undefined,
  animationFrameApi: AnimationFrameApi = window,
): () => void {
  const frameIds: number[] = [];
  let remainingFrames = Math.max(1, frames);
  let cancelled = false;

  const run = () => {
    if (cancelled) return;
    onFit();
    remainingFrames -= 1;
    if (remainingFrames > 0) {
      frameIds.push(animationFrameApi.requestAnimationFrame(run));
      return;
    }
    onComplete();
  };

  frameIds.push(animationFrameApi.requestAnimationFrame(run));
  return () => {
    cancelled = true;
    for (const frameId of frameIds) {
      animationFrameApi.cancelAnimationFrame(frameId);
    }
  };
}
