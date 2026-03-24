import type { EffectivePermission, Share } from "@/types/api";

export type SourceToken = {
  type: "user" | "group";
  name: string;
  level: string;
  effect: "allow" | "deny";
};

export type PermissionTreeNode = {
  permission: EffectivePermission;
  share: Share;
  depth: number;
  parentPermission: EffectivePermission | null;
};

const TOKEN_PATTERN = /^(user|group):([^:]+):([^:]+):(allow|deny)$/;

function splitSourceSummary(sourceSummary: string): string[] {
  return sourceSummary
    .split(",")
    .map((chunk) => chunk.trim())
    .filter(Boolean);
}

function getLevelRank(level: string): number {
  const normalized = level.trim().toLowerCase();

  if (normalized.includes("write")) {
    return 2;
  }

  if (normalized.includes("read")) {
    return 1;
  }

  return 0;
}

export function parseSourceTokens(sourceSummary: string): SourceToken[] {
  const normalizedSource = sourceSummary.trim();

  if (!normalizedSource || normalizedSource === "no-match") {
    return [];
  }

  return splitSourceSummary(normalizedSource).flatMap((token) => {
    const match = TOKEN_PATTERN.exec(token);

    if (!match) {
      return [];
    }

    return [
      {
        type: match[1] as SourceToken["type"],
        name: match[2],
        level: match[3],
        effect: match[4] as SourceToken["effect"],
      },
    ];
  });
}

export function extractGroups(sourceSummary: string): string[] {
  return Array.from(
    new Set(
      parseSourceTokens(sourceSummary)
        .filter((token) => token.type === "group")
        .map((token) => token.name),
    ),
  );
}

export function isMultiSourceAnomaly(sourceSummary: string): boolean {
  const tokens = parseSourceTokens(sourceSummary);

  if (tokens.length === 0) {
    return false;
  }

  const distinctGroups = new Set(
    tokens.filter((token) => token.type === "group").map((token) => token.name),
  );

  if (distinctGroups.size >= 2) {
    return true;
  }

  const userTokens = tokens.filter((token) => token.type === "user");
  const groupTokens = tokens.filter((token) => token.type === "group");

  if (userTokens.length > 0 && groupTokens.length > 0) {
    const distinctLevels = new Set(tokens.map((token) => `${token.level}:${token.effect}`));
    return distinctLevels.size >= 2;
  }

  return false;
}

export function hasMultiGroupPermissions(permissions: EffectivePermission[]): boolean {
  return new Set(permissions.flatMap((permission) => extractGroups(permission.source_summary))).size >= 2;
}

export function getAnomalousPermissions(
  permissions: EffectivePermission[],
): EffectivePermission[] {
  return permissions.filter((permission) => {
    if (isMultiSourceAnomaly(permission.source_summary)) {
      return true;
    }

    if (!permission.can_write) {
      return false;
    }

    const currentGroups = extractGroups(permission.source_summary);

    if (currentGroups.length !== 1) {
      return false;
    }

    return permissions.some((candidate) => {
      if (candidate.id === permission.id) {
        return false;
      }

      if (candidate.share_id !== permission.share_id || candidate.can_write || candidate.is_denied) {
        return false;
      }

      const candidateGroups = extractGroups(candidate.source_summary);
      return candidateGroups.length === 1 && candidateGroups[0] !== currentGroups[0];
    });
  });
}

export function getHighestPrioritySourceIndexes(sourceSummary: string): number[] {
  const tokens = parseSourceTokens(sourceSummary);

  if (tokens.length === 0) {
    return [];
  }

  const groupIndexes = tokens
    .map((token, index) => ({ token, index }))
    .filter(({ token }) => token.type === "group");

  const candidates = groupIndexes.length > 0 ? groupIndexes : tokens.map((token, index) => ({ token, index }));
  const highestRank = Math.max(...candidates.map(({ token }) => getLevelRank(token.level)));

  return candidates
    .filter(({ token }) => getLevelRank(token.level) === highestRank)
    .map(({ index }) => index);
}

export function buildPermissionTree(
  permissions: EffectivePermission[],
  shares: Share[],
): PermissionTreeNode[] {
  const shareMap = new Map(shares.map((share) => [share.id, share]));
  const permissionMap = new Map(permissions.map((permission) => [permission.share_id, permission]));

  function getDepth(shareId: number, visited = new Set<number>()): number {
    if (visited.has(shareId)) {
      return 0;
    }

    visited.add(shareId);
    const share = shareMap.get(shareId);

    if (!share?.parent_id) {
      return 0;
    }

    return 1 + getDepth(share.parent_id, visited);
  }

  return permissions
    .map((permission) => {
      const share = shareMap.get(permission.share_id);

      if (!share) {
        return null;
      }

      const parentShare = share.parent_id ? shareMap.get(share.parent_id) : null;
      const parentPermission = parentShare ? permissionMap.get(parentShare.id) ?? null : null;

      return {
        permission,
        share,
        depth: getDepth(permission.share_id),
        parentPermission,
      };
    })
    .filter((node): node is PermissionTreeNode => node !== null)
    .sort((left, right) => left.share.path.localeCompare(right.share.path, "it"));
}

function hasEffectiveAccess(permission: EffectivePermission): boolean {
  return permission.can_read || permission.can_write || permission.is_denied;
}

export function filterPermissionTreeForDisplay(
  nodes: PermissionTreeNode[],
): PermissionTreeNode[] {
  const childrenByParentId = new Map<number, PermissionTreeNode[]>();

  for (const node of nodes) {
    const parentId = node.share.parent_id;

    if (!parentId) {
      continue;
    }

    const siblings = childrenByParentId.get(parentId) ?? [];
    siblings.push(node);
    childrenByParentId.set(parentId, siblings);
  }

  const visibleShareIds = new Set<number>();

  function markVisible(node: PermissionTreeNode): boolean {
    const children = childrenByParentId.get(node.share.id) ?? [];
    const descendantVisible = children.some(markVisible);
    const visible = node.depth === 0 || hasEffectiveAccess(node.permission) || descendantVisible;

    if (visible) {
      visibleShareIds.add(node.share.id);
    }

    return visible;
  }

  nodes.filter((node) => node.depth === 0).forEach(markVisible);

  return nodes.filter((node) => visibleShareIds.has(node.share.id));
}

export function isEscalation(node: PermissionTreeNode): boolean {
  const { permission, parentPermission } = node;

  if (!parentPermission) {
    return false;
  }

  if (permission.can_write && !parentPermission.can_write) {
    return true;
  }

  if ((permission.can_read || permission.can_write) && parentPermission.is_denied) {
    return true;
  }

  return false;
}
