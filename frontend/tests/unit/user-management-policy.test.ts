import { describe, expect, test } from "vitest";

import { assignableRoles, canEditUserSectionPermissions, canManageUsers, delegableModules, gaiaRoleOptions, managedUsers, userManagementAccess } from "@/lib/user-management-policy";
import type { ApplicationUser, CurrentUser } from "@/types/api";

function actor(role: string, modules: string[] = []): CurrentUser {
  return { role, enabled_modules: modules } as CurrentUser;
}

describe("CED user management policy", () => {
  test("section permissions and QGIS credentials remain administrative", () => {
    const standard = { role: "viewer" } as ApplicationUser;
    expect(userManagementAccess(actor("ced"))).toEqual({ requiredModule: undefined, canManageQgis: false });
    expect(userManagementAccess(null)).toEqual({ requiredModule: "accessi", canManageQgis: true });
    expect(userManagementAccess(actor("admin")).canManageQgis).toBe(true);
    expect(canEditUserSectionPermissions(null, standard)).toBe(false);
    expect(canEditUserSectionPermissions(actor("admin"), null)).toBe(false);
    expect(canEditUserSectionPermissions(actor("ced"), standard)).toBe(false);
    expect(canEditUserSectionPermissions(actor("admin"), standard)).toBe(true);
    expect(canEditUserSectionPermissions(actor("admin"), { role: "admin" } as ApplicationUser)).toBe(false);
    expect(canEditUserSectionPermissions(actor("admin"), { role: "super_admin" } as ApplicationUser)).toBe(false);
    expect(canEditUserSectionPermissions(actor("super_admin"), { role: "super_admin" } as ApplicationUser)).toBe(true);
    expect(canEditUserSectionPermissions(actor("reviewer"), standard)).toBe(false);
    expect(canEditUserSectionPermissions(actor("viewer"), standard)).toBe(false);
  });
  test("management is independent of NAS for CED and preserves admin module checks", () => {
    expect(canManageUsers(actor("ced"))).toBe(true);
    expect(canManageUsers(actor("admin", ["accessi"]))).toBe(true);
    expect(canManageUsers(actor("super_admin", ["accessi"]))).toBe(true);
    expect(canManageUsers(actor("admin"))).toBe(false);
    expect(canManageUsers(actor("viewer", ["accessi"]))).toBe(false);
  });

  test("CED manages only standard accounts and cannot assign privileged roles", () => {
    const users = gaiaRoleOptions.map((role) => ({ role: role.value }) as ApplicationUser);
    const standard = ["operator", "viewer", "reviewer", "hr_manager"];
    expect(managedUsers(users, actor("ced")).map((user) => user.role)).toEqual(standard);
    expect(assignableRoles(actor("ced")).map((role) => role.value)).toEqual(standard);
    expect(managedUsers(users, null)).toBe(users);
    expect(managedUsers(users, actor("admin"))).toBe(users);
    expect(assignableRoles(null)).toBe(gaiaRoleOptions);
    expect(assignableRoles(actor("super_admin"))).toBe(gaiaRoleOptions);
  });

  test("network, NAS and future modules are excluded from delegation", () => {
    const modules = ["accessi", "rete", "gis", "presenze", "dotazioni", "future"].map((moduleKey) => ({ moduleKey }));
    expect(delegableModules(modules, actor("ced")).map((module) => module.moduleKey)).toEqual(["gis", "presenze", "dotazioni"]);
    expect(delegableModules(modules, null)).toBe(modules);
    expect(delegableModules(modules, actor("admin"))).toBe(modules);
  });
});
