import { describe, expect, test } from "vitest";

import { hasUserModuleAccess, resolveAllowedModuleKeys } from "@/lib/module-access";

describe("module access helpers", () => {
  test("resolves GIS as an autonomous module", () => {
    expect(resolveAllowedModuleKeys("gis")).toEqual(["gis"]);
    expect(hasUserModuleAccess({ role: "viewer", enabled_modules: ["gis"] }, "gis")).toBe(true);
    expect(hasUserModuleAccess({ role: "viewer", enabled_modules: ["catasto"] }, "gis")).toBe(false);
  });

  test("keeps ordinary module checks strict", () => {
    expect(resolveAllowedModuleKeys("rete")).toEqual(["rete"]);
    expect(resolveAllowedModuleKeys("presenze")).toEqual(["presenze"]);
    expect(hasUserModuleAccess({ role: "viewer", enabled_modules: ["catasto"] }, "rete")).toBe(false);
    expect(hasUserModuleAccess({ role: "viewer", enabled_modules: ["rete"] }, "rete")).toBe(true);
  });

  test("uses explicit enabled modules for super admins too", () => {
    expect(hasUserModuleAccess({ role: "super_admin", enabled_modules: ["gis"] }, "gis")).toBe(true);
    expect(hasUserModuleAccess({ role: "super_admin", enabled_modules: [] }, "gis")).toBe(false);
  });
});
