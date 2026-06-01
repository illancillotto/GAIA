import { buildWikiContextHref } from "@/features/wiki/context-links";

describe("wiki context links", () => {
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
