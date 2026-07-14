import { describe, expect, test } from "vitest";

import { hasUserModuleAccess, resolveAllowedModuleKeys } from "@/lib/module-access";

describe("module access helpers", () => {
  test("resolves GIS as an autonomous module with Catasto fallback", () => {
    expect(resolveAllowedModuleKeys("gis")).toEqual(["gis", "catasto"]);
    expect(hasUserModuleAccess({ role: "viewer", enabled_modules: ["gis"] }, "gis")).toBe(true);
    expect(hasUserModuleAccess({ role: "viewer", enabled_modules: ["catasto"] }, "gis")).toBe(true);
  });

  test("keeps ordinary module checks strict", () => {
    expect(resolveAllowedModuleKeys("rete")).toEqual(["rete"]);
    expect(hasUserModuleAccess({ role: "viewer", enabled_modules: ["catasto"] }, "rete")).toBe(false);
    expect(hasUserModuleAccess({ role: "viewer", enabled_modules: ["rete"] }, "rete")).toBe(true);
  });

  test("lets super admins open GIS even before the backend exposes module_gis", () => {
    expect(hasUserModuleAccess({ role: "super_admin", enabled_modules: [] }, "gis")).toBe(true);
    expect(hasUserModuleAccess({ role: "super_admin", enabled_modules: [] }, "catasto")).toBe(false);
  });
});
