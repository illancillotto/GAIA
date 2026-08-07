import { describe, expect, test } from "vitest";

import { resolvePresenceRouteMeta } from "@/lib/presence";

describe("resolvePresenceRouteMeta", () => {
  test("resolves specific operazioni pages", () => {
    expect(resolvePresenceRouteMeta("/operazioni/attivita")).toEqual({
      moduleKey: "operazioni",
      routeLabel: "Operazioni / Attivita",
    });
    expect(resolvePresenceRouteMeta("/operazioni/attivita/123")).toEqual({
      moduleKey: "operazioni",
      routeLabel: "Operazioni / Dettaglio attivita",
    });
    expect(resolvePresenceRouteMeta("/operazioni/segnalazioni/cruscotto")).toEqual({
      moduleKey: "operazioni",
      routeLabel: "Operazioni / Cruscotto segnalazioni",
    });
  });

  test("resolves specific pages across major modules", () => {
    expect(resolvePresenceRouteMeta("/catasto/letture-contatori")).toEqual({
      moduleKey: "catasto",
      routeLabel: "Catasto / Contatori irrigui",
    });
    expect(resolvePresenceRouteMeta("/network/devices/77")).toEqual({
      moduleKey: "rete",
      routeLabel: "Rete / Dispositivi",
    });
    expect(resolvePresenceRouteMeta("/wiki/support/analytics")).toEqual({
      moduleKey: "wiki",
      routeLabel: "Wiki / Analytics supporto",
    });
    expect(resolvePresenceRouteMeta("/gis/catalogo")).toEqual({
      moduleKey: "gis",
      routeLabel: "GIS Platform / Catalogo",
    });
    expect(resolvePresenceRouteMeta("/ruolo/avvisi/42")).toEqual({
      moduleKey: "ruolo",
      routeLabel: "Ruolo / Dettaglio avviso",
    });
    expect(resolvePresenceRouteMeta("/ruolo/raccomandate")).toEqual({
      moduleKey: "ruolo",
      routeLabel: "Ruolo / Raccomandate",
    });
    expect(resolvePresenceRouteMeta("/elaborazioni/presenze-sync")).toEqual({
      moduleKey: "elaborazioni",
      routeLabel: "Elaborazioni / Presenze INAZ Sync",
    });
  });

  test("keeps fallback labels for unmapped paths", () => {
    expect(resolvePresenceRouteMeta("/custom-area/flusso-speciale")).toEqual({
      moduleKey: "custom-area",
      routeLabel: "Custom area / Flusso speciale",
    });
  });

  test("resolves home and null paths", () => {
    expect(resolvePresenceRouteMeta("/")).toEqual({
      moduleKey: "home",
      routeLabel: "Home",
    });
    expect(resolvePresenceRouteMeta(null)).toEqual({
      moduleKey: "home",
      routeLabel: "Home",
    });
    expect(resolvePresenceRouteMeta("///")).toEqual({
      moduleKey: "other",
      routeLabel: "Home",
    });
    expect(resolvePresenceRouteMeta("")).toEqual({
      moduleKey: "home",
      routeLabel: "Home",
    });
  });

  test("resolves additional module prefixes", () => {
    expect(resolvePresenceRouteMeta("/me/presenze")).toEqual({
      moduleKey: "me",
      routeLabel: "La mia attivita / Presenze",
    });
    expect(resolvePresenceRouteMeta("/nas-control/users")).toEqual({
      moduleKey: "accessi",
      routeLabel: "NAS Control / Utenti",
    });
    expect(resolvePresenceRouteMeta("/inventory/items")).toEqual({
      moduleKey: "inventario",
      routeLabel: "Inventario",
    });
    expect(resolvePresenceRouteMeta("/riordino/configurazione")).toEqual({
      moduleKey: "riordino",
      routeLabel: "Riordino / Configurazione",
    });
    expect(resolvePresenceRouteMeta("/anagrafica/subjects")).toEqual({
      moduleKey: "utenze",
      routeLabel: "Utenze / ANPR",
    });
  });
});
