import { buildWikiContextHref } from "@/features/wiki/context-links";

describe("wiki context links", () => {
  test.each([
    ["accessi", "/nas-control"], ["catasto", "/catasto"],
    ["operazioni", "/operazioni"], ["riordino", "/riordino"],
    ["ruolo", "/ruolo"], ["utenze", "/utenze"],
    ["unknown", null], ["", null], [null, null], [undefined, null],
  ])("uses the %s fallback for absent or unrecognized entities", (moduleKey, expected) => {
    for (const entityKey of [undefined, null, "", "unknown.entity", "CATasto.particelle.123"]) {
      expect(buildWikiContextHref(entityKey, moduleKey)).toBe(expected);
    }
  });

  test.each([
    ["catasto.particelle.", "/catasto/particelle/"],
    ["catasto.particelle.a/b?x", "/catasto/particelle/a/b?x"],
    ["catasto.particelle.catasto.particelle.123", "/catasto/particelle/catasto.particelle.123"],
    ["utenze.subjects.id", "/utenze/id"],
    ["riordino.practices.id", "/riordino/pratiche/id"],
    ["operazioni.cases.id", "/operazioni/pratiche/id"],
    ["operazioni.activities.id", "/operazioni/attivita/id"],
    ["accessi.permissions.", "/gaia/users"],
    ["accessi.shares.lookup", "/nas-control/shares"],
    ["accessi.shares.a b&c", "/nas-control/shares?q=a%20b%26c"],
    ["accessi.shares.", "/nas-control/shares?q="],
    ["accessi.share.lookup", "/nas-control/shares?q=lookup"],
    ["accessi.share.a b&c", "/nas-control/shares?q=a%20b%26c"],
    ["accessi.nas-users.lookup", "/nas-control/users"],
    ["accessi.nas-users.a b&c", "/nas-control/users?q=a%20b%26c"],
    ["ruolo.subjects.lookup", "/ruolo/avvisi"],
    ["ruolo.subjects.a b&c", "/ruolo/avvisi?q=a%20b%26c"],
  ])("preserves entity precedence and suffix handling for %s", (entityKey, expected) => {
    expect(buildWikiContextHref(entityKey, "unknown")).toBe(expected);
    expect(buildWikiContextHref(entityKey, "utenze")).toBe(expected);
    expect(buildWikiContextHref(entityKey)).toBe(expected);
  });

  test("maps entity keys to functional routes", () => {
    expect(buildWikiContextHref("catasto.particelle.123", "catasto")).toBe("/catasto/particelle/123");
    expect(buildWikiContextHref("accessi.nas-users.mrossi", "accessi")).toBe("/nas-control/users?q=mrossi");
    expect(buildWikiContextHref("accessi.shares.contabilita", "accessi")).toBe("/nas-control/shares?q=contabilita");
    expect(buildWikiContextHref("accessi.share.progetti", "accessi")).toBe("/nas-control/shares?q=progetti");
    expect(buildWikiContextHref("accessi.permissions.accessi.permissions", "accessi")).toBe("/gaia/users");
    expect(buildWikiContextHref("ruolo.subjects.CNTMRC67P66A357L", "ruolo")).toBe("/ruolo/avvisi?q=CNTMRC67P66A357L");
    expect(buildWikiContextHref("utenze.subjects.abc", "utenze")).toBe("/utenze/abc");
    expect(buildWikiContextHref("operazioni.activities.xyz", "operazioni")).toBe("/operazioni/attivita/xyz");
    expect(buildWikiContextHref("riordino.practices.r1", "riordino")).toBe("/riordino/pratiche/r1");
  });

  test("falls back to module dashboards", () => {
    expect(buildWikiContextHref(null, "accessi")).toBe("/nas-control");
    expect(buildWikiContextHref(null, "ruolo")).toBe("/ruolo");
    expect(buildWikiContextHref(null, "unknown")).toBeNull();
  });
});
