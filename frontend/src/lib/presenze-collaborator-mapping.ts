import type { ApplicationUser, PresenzeCollaborator } from "@/types/api";

export const PRESENZE_COLLABORATOR_DETAIL_UPDATED_MESSAGE = "gaia:presenze-collaborator-detail-updated";

/** Notifies the parent list page (iframe host) that collaborator data changed. */
export function notifyPresenzeCollaboratorDetailUpdated(): void {
  if (typeof window === "undefined" || window.parent === window) {
    return;
  }
  window.parent.postMessage({ type: PRESENZE_COLLABORATOR_DETAIL_UPDATED_MESSAGE }, window.location.origin);
}

export function presenzeAssignedApplicationUserIds(
  collaborators: PresenzeCollaborator[],
  excludeCollaboratorId?: string,
): Set<number> {
  const ids = new Set<number>();
  for (const collaborator of collaborators) {
    if (collaborator.application_user_id == null) {
      continue;
    }
    if (excludeCollaboratorId && collaborator.id === excludeCollaboratorId) {
      continue;
    }
    ids.add(collaborator.application_user_id);
  }
  return ids;
}

export function usersForPresenzeCollaboratorMapping(
  users: ApplicationUser[],
  collaborators: PresenzeCollaborator[],
  collaboratorId?: string,
): ApplicationUser[] {
  const assignedElsewhere = presenzeAssignedApplicationUserIds(collaborators, collaboratorId);
  return users.filter((user) => !assignedElsewhere.has(user.id));
}

function normalizePersonText(value: string | null | undefined): string {
  return (value ?? "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function buildTokenSet(value: string): Set<string> {
  return new Set(
    normalizePersonText(value)
      .split(/[\s._-]+/)
      .filter((token) => token.length > 1),
  );
}

/** Higher score = closer match between collaborator name and GAIA user identity. */
export function scorePresenzeCollaboratorUserMatch(collaborator: PresenzeCollaborator, user: ApplicationUser): number {
  const collaboratorName = normalizePersonText(collaborator.name);
  if (!collaboratorName) return 0;

  const userFullName = normalizePersonText(user.full_name);
  const userUsername = normalizePersonText(user.username);
  const userEmailLocal = normalizePersonText(user.email.split("@")[0] ?? "");
  let score = 0;

  if (userFullName && userFullName === collaboratorName) score += 120;
  if (userUsername && userUsername === collaboratorName) score += 90;
  if (userEmailLocal && userEmailLocal === collaboratorName) score += 80;

  const collaboratorTokens = buildTokenSet(collaborator.name);
  for (const candidate of [userFullName, userUsername, userEmailLocal]) {
    if (!candidate) continue;
    const candidateTokens = buildTokenSet(candidate);
    const candidateCompact = candidate.replace(/\s+/g, "");
    let intersection = 0;
    collaboratorTokens.forEach((token) => {
      if (candidateTokens.has(token)) {
        intersection += 1;
      } else if (token.length > 2 && candidateCompact.includes(token)) {
        intersection += 1;
      }
    });
    if (intersection === collaboratorTokens.size && collaboratorTokens.size > 1) {
      score += 70;
    } else if (intersection > 0) {
      score += intersection * 18;
    }
  }

  if (collaborator.birth_date && user.full_name && userFullName.includes(collaboratorName.split(" ")[0] ?? "")) {
    score += 5;
  }

  return score;
}

/** Available users for mapping, best name matches first. */
export function usersForPresenzeCollaboratorMappingSorted(
  collaborator: PresenzeCollaborator,
  users: ApplicationUser[],
  collaborators: PresenzeCollaborator[],
  collaboratorId?: string,
): ApplicationUser[] {
  const available = usersForPresenzeCollaboratorMapping(users, collaborators, collaboratorId);
  return [...available].sort((left, right) => {
    const scoreDiff = scorePresenzeCollaboratorUserMatch(collaborator, right) - scorePresenzeCollaboratorUserMatch(collaborator, left);
    if (scoreDiff !== 0) {
      return scoreDiff;
    }
    const leftLabel = left.full_name?.trim() || left.username;
    const rightLabel = right.full_name?.trim() || right.username;
    return leftLabel.localeCompare(rightLabel, "it");
  });
}
