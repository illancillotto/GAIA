import { describe, expect, test, vi } from "vitest";

import {
  PRESENZE_COLLABORATOR_DETAIL_UPDATED_MESSAGE,
  notifyPresenzeCollaboratorDetailUpdated,
  presenzeAssignedApplicationUserIds,
  scorePresenzeCollaboratorUserMatch,
  usersForPresenzeCollaboratorMapping,
  usersForPresenzeCollaboratorMappingSorted,
} from "@/lib/presenze-collaborator-mapping";
import type { ApplicationUser, PresenzeCollaborator } from "@/types/api";

const baseCollaborator = (id: string, applicationUserId: number | null): PresenzeCollaborator => ({
  id,
  owner_user_id: 1,
  application_user_id: applicationUserId,
  kint: null,
  kkint: null,
  employee_code: id,
  company_code: null,
  company_label: null,
  name: id,
  birth_date: null,
  contract_kind: null,
  operai_group: null,
  standard_daily_minutes: null,
  is_active: true,
  last_seen_at: null,
  created_at: "2026-06-04T00:00:00Z",
  updated_at: "2026-06-04T00:00:00Z",
});

const baseUser = (id: number): ApplicationUser => ({
  id,
  username: `user-${id}`,
  email: `user-${id}@example.local`,
  full_name: null,
  office_location: null,
  phone_extension: null,
  role: "viewer",
  is_active: true,
  module_accessi: true,
  module_rete: false,
  module_inventario: false,
  module_gis: false,
  module_catasto: false,
  module_utenze: false,
  module_operazioni: false,
  module_riordino: false,
  module_ruolo: false,
  module_presenze: false,
  enabled_modules: ["accessi"],
  created_at: "2026-06-04T00:00:00Z",
  last_login_at: null,
  last_login_ip: null,
  login_count: 0,
  gate_mobile_console: null,
  updated_at: "2026-06-04T00:00:00Z",
});

describe("presenze collaborator mapping helpers", () => {
  test("excludes users assigned to other collaborators", () => {
    const collaborators = [baseCollaborator("a", 10), baseCollaborator("b", null)];
    const users = [baseUser(10), baseUser(11)];

    expect(usersForPresenzeCollaboratorMapping(users, collaborators, "b").map((user) => user.id)).toEqual([11]);
  });

  test("keeps current collaborator mapping available in the list", () => {
    const collaborators = [baseCollaborator("a", 10), baseCollaborator("b", null)];
    const users = [baseUser(10), baseUser(11)];

    expect(usersForPresenzeCollaboratorMapping(users, collaborators, "a").map((user) => user.id)).toEqual([10, 11]);
  });

  test("collects all assigned ids when no collaborator is excluded", () => {
    const collaborators = [baseCollaborator("a", 10), baseCollaborator("b", 11)];
    expect(presenzeAssignedApplicationUserIds(collaborators)).toEqual(new Set([10, 11]));
  });

  test("posts update message to parent window when embedded", () => {
    const postMessage = vi.fn();
    const parentWindow = { postMessage } as unknown as Window;
    vi.stubGlobal("window", {
      parent: parentWindow,
      location: { origin: "http://localhost:8080" },
    } as Window & typeof globalThis);

    notifyPresenzeCollaboratorDetailUpdated();

    expect(postMessage).toHaveBeenCalledWith(
      { type: PRESENZE_COLLABORATOR_DETAIL_UPDATED_MESSAGE },
      "http://localhost:8080",
    );
    vi.unstubAllGlobals();
  });

  test("does not post update message when page is not embedded", () => {
    expect(() => notifyPresenzeCollaboratorDetailUpdated()).not.toThrow();
  });

  test("sorts users with best name match first in dropdown order", () => {
    const collaborator = { ...baseCollaborator("ardu", null), name: "ARDU PIER PAOLO" };
    const users = [
      { ...baseUser(1), username: "zzzz", email: "zzzz@example.local", full_name: "Altro Utente" },
      { ...baseUser(2), username: "ardu.pierpaolo", email: "pierpaoloardu41@gmail.com", full_name: null },
      { ...baseUser(3), username: "mrossi", email: "mrossi@example.local", full_name: "Mario Rossi" },
    ];

    const sorted = usersForPresenzeCollaboratorMappingSorted(collaborator, users, [collaborator], "ardu");
    expect(sorted.map((user) => user.id)).toEqual([2, 1, 3]);
    expect(scorePresenzeCollaboratorUserMatch(collaborator, sorted[0])).toBeGreaterThan(
      scorePresenzeCollaboratorUserMatch(collaborator, sorted[1]),
    );
  });

  test("scores partial token matches and birth date bonus", () => {
    const partialCollaborator = { ...baseCollaborator("salvatore", null), name: "AMADU SALVATORE" };
    const partialUser = { ...baseUser(4), username: "salvatore", email: "salvatore@example.local", full_name: "Salvatore" };
    expect(scorePresenzeCollaboratorUserMatch(partialCollaborator, partialUser)).toBe(54);

    const birthDateCollaborator = { ...baseCollaborator("rossi", null), name: "ROSSI", birth_date: "1980-01-01" };
    const birthDateUser = { ...baseUser(5), username: "mrossi", email: "mrossi@example.local", full_name: "Rossi Mario" };
    expect(scorePresenzeCollaboratorUserMatch(birthDateCollaborator, birthDateUser)).toBeGreaterThan(5);
    expect(
      scorePresenzeCollaboratorUserMatch(birthDateCollaborator, {
        ...birthDateUser,
        full_name: null,
      }),
    ).toBeLessThan(scorePresenzeCollaboratorUserMatch(birthDateCollaborator, birthDateUser));
  });

  test("scores exact identity matches and empty collaborator names", () => {
    const emptyCollaborator = { ...baseCollaborator("empty", null), name: "" };
    expect(scorePresenzeCollaboratorUserMatch(emptyCollaborator, baseUser(6))).toBe(0);

    const exactCollaborator = { ...baseCollaborator("exact", null), name: "ROSSI MARIO" };
    expect(
      scorePresenzeCollaboratorUserMatch(exactCollaborator, {
        ...baseUser(7),
        username: "rossi mario",
        email: "rossi mario@example.local",
        full_name: "Rossi Mario",
      }),
    ).toBeGreaterThan(250);
  });

  test("sorts alphabetically by full name fallback when scores tie", () => {
    const collaborator = { ...baseCollaborator("none", null), name: "NOME NON PRESENTE" };
    const users = [
      { ...baseUser(8), username: "zeta", full_name: null },
      { ...baseUser(9), username: "beta", full_name: " Beta Utente " },
      { ...baseUser(10), username: "alfa", full_name: "   " },
    ];

    const sorted = usersForPresenzeCollaboratorMappingSorted(collaborator, users, [], "none");

    expect(sorted.map((user) => user.id)).toEqual([10, 9, 8]);
  });
});
