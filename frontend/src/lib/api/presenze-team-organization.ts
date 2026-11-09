import { request } from "./core";

export type TeamOrganizationDirectory = {
  teams: { team_id: string; org_unit_id: string }[];
  units: { unit_id: string; path: { id: string; name: string; kind: string }[] }[];
};

export function getTeamOrganizationDirectory(token: string): Promise<TeamOrganizationDirectory> {
  return request("/gate/presenze/team-organizations", { headers: { Authorization: `Bearer ${token}` } });
}

export function saveTeamOrganization(token: string, teamId: string, unit: string | null, previous: string | null): Promise<{ team_id: string; org_unit_id: string | null }> {
  return request(`/gate/presenze/teams/${encodeURIComponent(teamId)}/organization`, {
    method: "PUT", headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ org_unit_id: unit, expected_org_unit_id: previous }),
  });
}
