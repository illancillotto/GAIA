import { describe, expect, test } from "vitest";

import { buildBonificaDiagnosis, buildCapacitasDiagnosis } from "@/lib/elaborazioni-credential-diagnostics";

describe("credential provider diagnostics", () => {
  test("diagnoses Capacitas token, viewstate and gateway failures", () => {
    expect(buildCapacitasDiagnosis("Tóken non trovato", 200)).toContain("AUTH_COOKIE");
    expect(buildCapacitasDiagnosis("__VIEWSTATE assente", 200)).toContain("ASP.NET");
    expect(buildCapacitasDiagnosis("upstream", 502)).toContain("negoziazione");
    expect(buildCapacitasDiagnosis("errore generico", 400)).toBeNull();
    expect(buildCapacitasDiagnosis(null, null)).toBeNull();
  });

  test("diagnoses Bonifica CSRF, invalid credentials and gateway failures", () => {
    expect(buildBonificaDiagnosis("CSRF assente", 400)).toContain("token CSRF");
    expect(buildBonificaDiagnosis("campo _TOKEN assente", 400)).toContain("token CSRF");
    expect(buildBonificaDiagnosis("Credenziali non valide", 401)).toContain("form di login");
    expect(buildBonificaDiagnosis("upstream", 502)).toContain("autenticazione Laravel");
    expect(buildBonificaDiagnosis("errore generico", 400)).toBeNull();
    expect(buildBonificaDiagnosis(null, null)).toBeNull();
  });
});
