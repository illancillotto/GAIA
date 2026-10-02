import type { ApplicationUser, CurrentUser } from "@/types/api";

const standardRoles = ["operator", "viewer", "reviewer", "hr_manager"];
const cedModules = ["inventario", "dotazioni", "gis", "catasto", "utenze", "operazioni", "riordino", "ruolo", "presenze", "organigramma"];

export const gaiaRoleOptions = [
  { value: "operator", label: "Operatore" },
  { value: "viewer", label: "Viewer" },
  { value: "reviewer", label: "Reviewer" },
  { value: "hr_manager", label: "HR Manager" },
  { value: "ced", label: "CED" },
  { value: "admin", label: "Admin" },
  { value: "super_admin", label: "Super Admin" },
];

export function canManageUsers(user: CurrentUser): boolean {
  return user.role === "ced" || (["admin", "super_admin"].includes(user.role) && user.enabled_modules.includes("accessi"));
}

export function managedUsers(users: ApplicationUser[], actor: CurrentUser | null): ApplicationUser[] {
  return actor?.role === "ced" ? users.filter((user) => standardRoles.includes(user.role)) : users;
}

export function assignableRoles(actor: CurrentUser | null) {
  return actor?.role === "ced" ? gaiaRoleOptions.filter((role) => standardRoles.includes(role.value)) : gaiaRoleOptions;
}

export function delegableModules<Module extends { moduleKey: string }>(modules: Module[], actor: CurrentUser | null): Module[] {
  return actor?.role === "ced" ? modules.filter((module) => cedModules.includes(module.moduleKey)) : modules;
}

export function userManagementAccess(actor: CurrentUser | null) {
  const isCed = actor?.role === "ced";
  return { requiredModule: isCed ? undefined : "accessi", canManageQgis: !isCed };
}

export function canEditUserSectionPermissions(actor: CurrentUser | null, target: ApplicationUser | null): boolean {
  return Boolean(actor && target && ["admin", "super_admin"].includes(actor.role)
    && (actor.role === "super_admin" || target.role !== "super_admin")
    && !(actor.role === "admin" && ["admin", "super_admin"].includes(target.role)));
}
