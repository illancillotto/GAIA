import { describe, expect, test } from "vitest";

import {
  canAccessOperatorDashboard,
  canManageGaiaUsers,
  getActivePlatformModule,
  getAdminNavigationItems,
  getCurrentModuleKey,
  getCurrentModuleLabel,
  getModuleSections,
  getSidebarState,
  getVisiblePlatformModules,
} from "@/components/layout/navigation";
import type { CurrentUser } from "@/types/api";

function buildUser(overrides: Partial<CurrentUser> = {}): CurrentUser {
  return {
    id: 1,
    username: "nav-user",
    email: "nav-user@example.local",
    role: "viewer",
    is_active: true,
    module_accessi: false,
    module_rete: false,
    module_inventario: false,
    module_catasto: false,
    module_utenze: false,
    module_operazioni: false,
    module_riordino: false,
    module_ruolo: false,
    module_presenze: false,
    enabled_modules: [],
    ...overrides,
  };
}

describe("layout navigation helpers", () => {
  test("maps every supported route to the expected current module key", () => {
    const cases = [
      ["/gaia/users", "gaia"],
      ["/me", "me"],
      ["/nas-control", "nas_control"],
      ["/elaborazioni", "elaborazioni"],
      ["/gis/catalogo", "gis"],
      ["/catasto", "catasto"],
      ["/utenze", "utenze"],
      ["/anagrafica/anpr-config", "utenze"],
      ["/network", "network"],
      ["/inventory", "inventory"],
      ["/operazioni", "operazioni"],
      ["/riordino", "riordino"],
      ["/ruolo", "ruolo"],
      ["/presenze", "presenze"],
      ["/organigramma", "organigramma"],
      ["/wiki", "wiki"],
      ["/unknown", "nas_control"],
    ] as const;

    cases.forEach(([pathname, expected]) => {
      expect(getCurrentModuleKey(pathname)).toBe(expected);
    });
  });

  test("returns the display label for each supported module key", () => {
    const cases = [
      ["gaia", "Utenti GAIA"],
      ["me", "La mia attività"],
      ["nas_control", "NAS Control"],
      ["elaborazioni", "Elaborazioni"],
      ["gis", "GIS Platform"],
      ["catasto", "Catasto"],
      ["utenze", "Utenze"],
      ["network", "Rete"],
      ["inventory", "Inventario"],
      ["operazioni", "Operazioni"],
      ["riordino", "Riordino"],
      ["ruolo", "Ruolo"],
      ["presenze", "Presenze"],
      ["organigramma", "Organigramma"],
      ["wiki", "Wiki"],
    ] as const;

    cases.forEach(([key, expected]) => {
      expect(getCurrentModuleLabel(key)).toBe(expected);
    });
  });

  test("filters visible platform modules by access and keeps wiki always visible", () => {
    const viewer = buildUser({ enabled_modules: ["catasto"] });
    const superAdmin = buildUser({
      role: "super_admin",
      enabled_modules: ["accessi", "rete", "inventario", "gis", "catasto", "utenze", "operazioni", "riordino", "ruolo", "presenze", "organigramma"],
    });

    expect(getVisiblePlatformModules(viewer).map((module) => module.label)).toEqual([
      "La mia attività",
      "Catasto",
      "Wiki",
    ]);
    expect(getVisiblePlatformModules(superAdmin).map((module) => module.label)).toContain("Elaborazioni");
    expect(getVisiblePlatformModules(superAdmin).map((module) => module.label)).not.toContain("Organigramma");
  });

  test("detects active platform modules for aliases and nested routes", () => {
    const gisUser = buildUser({ enabled_modules: ["gis"] });

    expect(getActivePlatformModule("/gis", gisUser)?.label).toBe("GIS Platform");
    expect(getActivePlatformModule("/gis/catalogo/layers", gisUser)?.label).toBe("GIS Platform");
    expect(getActivePlatformModule("/unknown", gisUser)).toBeUndefined();
  });

  test("derives admin quick links and admin capability flags", () => {
    const admin = buildUser({ role: "admin", enabled_modules: ["accessi"] });
    const viewer = buildUser({ enabled_modules: ["operazioni"] });

    expect(canManageGaiaUsers(admin)).toBe(true);
    expect(canAccessOperatorDashboard(admin)).toBe(true);
    expect(canManageGaiaUsers(viewer)).toBe(false);
    expect(canAccessOperatorDashboard(viewer)).toBe(true);
    expect(getAdminNavigationItems(admin).map((item) => item.label)).toEqual([
      "Utenti GAIA",
      "Cruscotto operatori",
    ]);
    expect(getAdminNavigationItems(buildUser()).length).toBe(0);
    expect(canAccessOperatorDashboard(buildUser())).toBe(false);
  });

  test("builds sidebar state from the current path and user access", () => {
    const currentUser = buildUser({ role: "super_admin", enabled_modules: ["accessi", "operazioni"] });
    const sidebarState = getSidebarState(currentUser, "/gaia/users/operatori-cruscotto");

    expect(sidebarState.currentModuleKey).toBe("gaia");
    expect(sidebarState.currentModuleLabel).toBe("Utenti GAIA");
    expect(sidebarState.canManageGaiaUsers).toBe(true);
    expect(sidebarState.canAccessOperatorDashboard).toBe(true);
  });

  test("keeps the administrative Presenze export link in the module sidebar", () => {
    const items = getModuleSections({ currentModuleKey: "presenze" }).flatMap((section) => section.items);

    expect(items).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          href: "/presenze/export",
          label: "Export",
          match: "prefix",
        }),
      ]),
    );
  });

  test("exposes the operator straordinari request link from the self-service sidebar", () => {
    const items = getModuleSections({ currentModuleKey: "me" }).flatMap((section) => section.items);

    expect(items).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          href: "/me/straordinari",
          label: "Richiesta straordinari",
          match: "prefix",
        }),
      ]),
    );
  });

  test("exposes official VPN access management in the network sidebar", () => {
    const items = getModuleSections({ currentModuleKey: "network" }).flatMap((section) => section.items);

    expect(items).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          href: "/network/vpn-access",
          label: "Accessi VPN",
          match: "prefix",
        }),
      ]),
    );
  });

  test("builds every module section and exposes SISTER portal health", () => {
    const moduleKeys = [
      "nas_control",
      "catasto",
      "gis",
      "elaborazioni",
      "gaia",
      "utenze",
      "operazioni",
      "riordino",
      "ruolo",
      "organigramma",
      "wiki",
      "inventory",
    ] as const;

    for (const currentModuleKey of moduleKeys) {
      const sections = getModuleSections({
        currentModuleKey,
        currentUserRole: "super_admin",
        grantedSectionKeys: ["accessi.users", "organigramma.read", "organigramma.manage"],
        reviewBadge: 3,
        userBadge: 2,
      });
      expect(sections.length).toBeGreaterThan(0);
    }

    const elaborazioniItems = getModuleSections({ currentModuleKey: "elaborazioni" })
      .flatMap((section) => section.items);
    expect(elaborazioniItems).toContainEqual(expect.objectContaining({
      href: "/elaborazioni/portal-health",
      label: "Stato portale SISTER",
      match: "prefix",
    }));
  });

  test("applies conditional module permissions and badge fallbacks", () => {
    const restrictedNas = getModuleSections({ currentModuleKey: "nas_control" });
    const allowedNasWithoutCount = getModuleSections({
      currentModuleKey: "nas_control",
      grantedSectionKeys: ["accessi.users"],
    });
    expect(restrictedNas.flatMap((section) => section.items).find((entry) => entry.label === "Utenti"))
      .toMatchObject({ disabled: true, badge: undefined });
    expect(allowedNasWithoutCount.flatMap((section) => section.items).find((entry) => entry.label === "Utenti"))
      .toMatchObject({ disabled: false, badge: undefined });

    const catastoViewer = getModuleSections({ currentModuleKey: "catasto", currentUserRole: "viewer" });
    const utenzeViewer = getModuleSections({ currentModuleKey: "utenze", currentUserRole: "viewer" });
    expect(catastoViewer.flatMap((section) => section.items).some((entry) => entry.href.includes("configurazione")))
      .toBe(false);
    expect(utenzeViewer.flatMap((section) => section.items).some((entry) => entry.href.includes("anomalies")))
      .toBe(false);

    const restrictedOrganigramma = getModuleSections({ currentModuleKey: "organigramma" });
    expect(restrictedOrganigramma).toHaveLength(1);
    expect(restrictedOrganigramma[0].items.every((entry) => entry.disabled)).toBe(true);
  });
});
