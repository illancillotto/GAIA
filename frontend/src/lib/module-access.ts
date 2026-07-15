import type { CurrentUser } from "@/types/api";

type ModuleAccessUser = Pick<CurrentUser, "enabled_modules" | "role">;

export function resolveAllowedModuleKeys(requiredModule: string): string[] {
  if (requiredModule === "presenze") {
    return ["presenze"];
  }
  return [requiredModule];
}

export function hasUserModuleAccess(user: ModuleAccessUser, requiredModule: string): boolean {
  return resolveAllowedModuleKeys(requiredModule).some((moduleKey) => user.enabled_modules.includes(moduleKey));
}
