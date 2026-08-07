import { describe, expect, test, vi } from "vitest";

import { cn } from "@/lib/cn";
import { generateUuid } from "@/lib/uuid";
import { hasSectionAccess } from "@/lib/section-access";
import {
  buildPermissionTree,
  extractGroups,
  filterPermissionTreeForDisplay,
  getAnomalousPermissions,
  getHighestPrioritySourceIndexes,
  hasMultiGroupPermissions,
  isEscalation,
  isMultiSourceAnomaly,
  parseSourceTokens,
} from "@/lib/permissions";
import type { EffectivePermission, Share } from "@/types/api";

describe("cn", () => {
  test("merges tailwind classes and drops conflicts", () => {
    expect(cn("px-2", "px-4", false && "hidden", "text-sm")).toBe("px-4 text-sm");
  });
});

describe("generateUuid", () => {
  test("uses crypto.randomUUID when available", () => {
    const randomUUID = vi.fn(() => "11111111-1111-4111-8111-111111111111");
    vi.stubGlobal("crypto", { randomUUID });

    expect(generateUuid()).toBe("11111111-1111-4111-8111-111111111111");
  });

  test("falls back to getRandomValues when randomUUID is unavailable", () => {
    const bytes = Uint8Array.from({ length: 16 }, (_, index) => index);
    vi.stubGlobal("crypto", {
      getRandomValues: (target: Uint8Array) => {
        target.set(bytes);
        return target;
      },
    });

    expect(generateUuid()).toMatch(/^[0-9a-f-]{36}$/);
  });

  test("falls back to timestamp id when crypto is unavailable", () => {
    vi.stubGlobal("crypto", undefined);

    expect(generateUuid()).toMatch(/^id-\d+-[0-9a-f]+$/);
  });
});

describe("hasSectionAccess", () => {
  test("returns true only when section key is granted", () => {
    expect(hasSectionAccess(["a", "b"], "b")).toBe(true);
    expect(hasSectionAccess(["a"], "b")).toBe(false);
  });
});

function permission(overrides: Partial<EffectivePermission> = {}): EffectivePermission {
  return {
    id: 1,
    share_id: 10,
    can_read: true,
    can_write: false,
    is_denied: false,
    source_summary: "group:team-a:read:allow",
    ...overrides,
  };
}

function share(overrides: Partial<Share> = {}): Share {
  return {
    id: 10,
    name: "Share A",
    path: "/a",
    parent_id: null,
    ...overrides,
  };
}

describe("permissions helpers", () => {
  test("parseSourceTokens handles empty and malformed tokens", () => {
    expect(parseSourceTokens("")).toEqual([]);
    expect(parseSourceTokens("no-match")).toEqual([]);
    expect(parseSourceTokens("broken-token")).toEqual([]);
    expect(parseSourceTokens("user:alice:write:allow")).toEqual([
      { type: "user", name: "alice", level: "write", effect: "allow" },
    ]);
  });

  test("extractGroups and multi-group detection", () => {
    const summary = "group:team-a:read:allow, group:team-b:write:allow";
    expect(extractGroups(summary)).toEqual(["team-a", "team-b"]);
    expect(isMultiSourceAnomaly(summary)).toBe(true);
    expect(hasMultiGroupPermissions([permission({ source_summary: summary })])).toBe(true);
  });

  test("getHighestPrioritySourceIndexes prefers highest write level", () => {
    const indexes = getHighestPrioritySourceIndexes(
      "group:team-a:read:allow, group:team-b:write:allow",
    );

    expect(indexes).toEqual([1]);
  });

  test("getAnomalousPermissions flags mixed sources and write escalation", () => {
    const permissions = [
      permission({
        id: 1,
        share_id: 10,
        can_write: true,
        source_summary: "group:team-a:write:allow, group:team-b:read:allow",
      }),
      permission({
        id: 2,
        share_id: 20,
        can_write: false,
        source_summary: "group:team-b:read:allow",
      }),
    ];

    expect(getAnomalousPermissions(permissions).map((item) => item.id)).toEqual([1]);
  });

  test("buildPermissionTree and display filter keep visible descendants", () => {
    const shares = [
      share({ id: 10, path: "/root" }),
      share({ id: 20, parent_id: 10, path: "/root/child", name: "Child" }),
    ];
    const permissions = [
      permission({ id: 1, share_id: 10, can_read: false, can_write: false, is_denied: false }),
      permission({
        id: 2,
        share_id: 20,
        can_read: true,
        can_write: true,
        source_summary: "group:team-a:write:allow",
      }),
    ];

    const tree = buildPermissionTree(permissions, shares);
    const visible = filterPermissionTreeForDisplay(tree);
    const childNode = visible.find((node) => node.share.id === 20);

    expect(tree).toHaveLength(2);
    expect(visible.map((node) => node.share.id)).toEqual([10, 20]);
    expect(childNode).toBeDefined();
    expect(isEscalation(childNode!)).toBe(true);
  });
});
