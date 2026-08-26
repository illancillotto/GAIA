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

export type PresenzeCollaboratorUserSuggestion = {
  userId: number | null;
  score: number;
  confidence: "high" | "medium" | "low" | "none" | "conflict";
};

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

function candidateCoversCollaboratorName(collaboratorName: string, candidate: string): boolean {
  if (!candidate) return false;
  if (candidate === collaboratorName) return true;
  const collaboratorTokens = buildTokenSet(collaboratorName);
  if (collaboratorTokens.size < 2) return false;
  const candidateTokens = buildTokenSet(candidate);
  const candidateCompact = candidate.replace(/\s+/g, "");
  return [...collaboratorTokens].every(
    (token) => candidateTokens.has(token) || (token.length > 2 && candidateCompact.includes(token)),
  );
}

function reliableIdentitySignalCount(collaborator: PresenzeCollaborator, user: ApplicationUser): number {
  const collaboratorName = normalizePersonText(collaborator.name);
  return [user.full_name, user.username, user.email.split("@")[0]].filter((candidate) =>
    candidateCoversCollaboratorName(collaboratorName, normalizePersonText(candidate)),
  ).length;
}

/** Higher score = closer match between collaborator name and GAIA user identity. */
export function scorePresenzeCollaboratorUserMatch(collaborator: PresenzeCollaborator, user: ApplicationUser): number {
  const collaboratorName = normalizePersonText(collaborator.name);
  if (!collaboratorName) return 0;

  const userFullName = normalizePersonText(user.full_name);
  const userUsername = normalizePersonText(user.username);
  const userEmailLocal = normalizePersonText(user.email.split("@")[0]);
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

  if (collaborator.birth_date && user.full_name && userFullName.includes(collaboratorName.split(" ")[0])) {
    score += 5;
  }

  return score;
}

export function suggestedUserForPresenzeCollaborator(
  collaborator: PresenzeCollaborator,
  users: ApplicationUser[],
  assignedApplicationUserIds: Set<number>,
): PresenzeCollaboratorUserSuggestion {
  let bestUser: ApplicationUser | null = null;
  let bestScore = 0;
  let bestScoreCandidates = 0;
  for (const user of users) {
    const userMappedToCurrentCollaborator = collaborator.application_user_id === user.id;
    if (!userMappedToCurrentCollaborator && assignedApplicationUserIds.has(user.id)) {
      continue;
    }
    const score = scorePresenzeCollaboratorUserMatch(collaborator, user);
    if (score > bestScore) {
      bestScore = score;
      bestUser = user;
      bestScoreCandidates = 1;
    } else if (score > 0 && score === bestScore) {
      bestScoreCandidates += 1;
    }
  }

  if (bestScore >= 35 && bestScoreCandidates > 1) {
    return { userId: null, score: bestScore, confidence: "conflict" };
  }

  const reliableSignals = bestUser ? reliableIdentitySignalCount(collaborator, bestUser) : 0;
  const confidence: PresenzeCollaboratorUserSuggestion["confidence"] =
    bestScore >= 70 && reliableSignals >= 2 ? "high" : bestScore >= 70 ? "medium" : bestScore >= 35 ? "low" : "none";

  return {
    userId: bestUser && confidence !== "none" ? bestUser.id : null,
    score: bestScore,
    confidence,
  };
}

/** Builds a collision-safe suggestion plan for the whole collaborator set. */
export function buildPresenzeCollaboratorMappingSuggestionPlan(
  collaborators: PresenzeCollaborator[],
  users: ApplicationUser[],
): Map<string, PresenzeCollaboratorUserSuggestion> {
  const assignedUserIds = presenzeAssignedApplicationUserIds(collaborators);
  const suggestions = new Map<string, PresenzeCollaboratorUserSuggestion>();
  const claimsByUser = new Map<number, string[]>();

  for (const collaborator of collaborators) {
    const suggestion = suggestedUserForPresenzeCollaborator(collaborator, users, assignedUserIds);
    suggestions.set(collaborator.id, suggestion);
    if (collaborator.application_user_id == null && suggestion.userId != null) {
      const claims = claimsByUser.get(suggestion.userId) ?? [];
      claims.push(collaborator.id);
      claimsByUser.set(suggestion.userId, claims);
    }
  }

  for (const collaboratorIds of claimsByUser.values()) {
    if (collaboratorIds.length < 2) continue;
    for (const collaboratorId of collaboratorIds) {
      const suggestion = suggestions.get(collaboratorId)!;
      suggestions.set(collaboratorId, { ...suggestion, confidence: "conflict" });
    }
  }

  return suggestions;
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
