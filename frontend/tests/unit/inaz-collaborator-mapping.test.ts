import { describe, expect, test, vi } from "vitest";

import {
  INAZ_COLLABORATOR_DETAIL_UPDATED_MESSAGE,
  inazAssignedApplicationUserIds,
  notifyInazCollaboratorDetailUpdated,
  scoreInazCollaboratorUserMatch,
  usersForInazCollaboratorMapping,
  usersForInazCollaboratorMappingSorted,
} from "@/lib/inaz-collaborator-mapping";
import type { ApplicationUser, InazCollaborator } from "@/types/api";

const baseCollaborator = (id: string, applicationUserId: number | null): InazCollaborator => ({
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
  module_catasto: false,
  module_utenze: false,
  module_operazioni: false,
  module_riordino: false,
  module_ruolo: false,
  module_inaz: false,
  enabled_modules: ["accessi"],
  created_at: "2026-06-04T00:00:00Z",
  last_login_at: null,
  last_login_ip: null,
  login_count: 0,
  updated_at: "2026-06-04T00:00:00Z",
});

describe("inaz collaborator mapping helpers", () => {
  test("excludes users assigned to other collaborators", () => {
    const collaborators = [baseCollaborator("a", 10), baseCollaborator("b", null)];
    const users = [baseUser(10), baseUser(11)];

    expect(usersForInazCollaboratorMapping(users, collaborators, "b").map((user) => user.id)).toEqual([11]);
  });

  test("keeps current collaborator mapping available in the list", () => {
    const collaborators = [baseCollaborator("a", 10), baseCollaborator("b", null)];
    const users = [baseUser(10), baseUser(11)];

    expect(usersForInazCollaboratorMapping(users, collaborators, "a").map((user) => user.id)).toEqual([10, 11]);
  });

  test("collects all assigned ids when no collaborator is excluded", () => {
    const collaborators = [baseCollaborator("a", 10), baseCollaborator("b", 11)];
    expect(inazAssignedApplicationUserIds(collaborators)).toEqual(new Set([10, 11]));
  });

  test("posts update message to parent window when embedded", () => {
    const postMessage = vi.fn();
    const parentWindow = { postMessage } as unknown as Window;
    vi.stubGlobal("window", {
      parent: parentWindow,
      location: { origin: "http://localhost:8080" },
    } as Window & typeof globalThis);

    notifyInazCollaboratorDetailUpdated();

    expect(postMessage).toHaveBeenCalledWith(
      { type: INAZ_COLLABORATOR_DETAIL_UPDATED_MESSAGE },
      "http://localhost:8080",
    );
    vi.unstubAllGlobals();
  });

  test("sorts users with best name match first in dropdown order", () => {
    const collaborator = { ...baseCollaborator("ardu", null), name: "ARDU PIER PAOLO" };
    const users = [
      { ...baseUser(1), username: "zzzz", email: "zzzz@example.local", full_name: "Altro Utente" },
      { ...baseUser(2), username: "ardu.pierpaolo", email: "pierpaoloardu41@gmail.com", full_name: null },
      { ...baseUser(3), username: "mrossi", email: "mrossi@example.local", full_name: "Mario Rossi" },
    ];

    const sorted = usersForInazCollaboratorMappingSorted(collaborator, users, [collaborator], "ardu");
    expect(sorted.map((user) => user.id)).toEqual([2, 1, 3]);
    expect(scoreInazCollaboratorUserMatch(collaborator, sorted[0])).toBeGreaterThan(
      scoreInazCollaboratorUserMatch(collaborator, sorted[1]),
    );
  });
});
