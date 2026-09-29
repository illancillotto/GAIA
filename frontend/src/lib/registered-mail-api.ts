import { request } from "@/lib/api";
import type {
  RuoloTributiRegisteredMailAssociationRequest,
  RuoloTributiRegisteredMailResponse,
  RuoloTributiRegisteredMailSummaryResponse,
} from "@/types/ruolo";
import type { RegisteredMailCampaignPreview, RegisteredMailReviewEvidence } from "@/types/registered-mail-campaign";

export async function getRegisteredMailCampaignPreview(token: string, createdBefore: string): Promise<RegisteredMailCampaignPreview> {
  return request<RegisteredMailCampaignPreview>(`/ruolo/tributi/raccomandate/campaign-preview?created_before=${encodeURIComponent(createdBefore)}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function checkRegisteredMailReferences(
  token: string, mailId: string, ref2022: string, ref2023: string,
): Promise<{ verified: boolean; reason: string }> {
  return request<{ verified: boolean; reason: string }>(`/ruolo/tributi/raccomandate/${mailId}/reference-check`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ ref_2022: ref2022, ref_2023: ref2023 }),
  });
}

export async function getTributiRegisteredMailSummary(token: string): Promise<RuoloTributiRegisteredMailSummaryResponse> {
  return request<RuoloTributiRegisteredMailSummaryResponse>("/ruolo/tributi/raccomandate/summary", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function updateTributiRegisteredMailAssociation(
  token: string,
  mailId: string,
  payload: RuoloTributiRegisteredMailAssociationRequest & { review_evidence?: RegisteredMailReviewEvidence },
): Promise<RuoloTributiRegisteredMailResponse> {
  return request<RuoloTributiRegisteredMailResponse>(`/ruolo/tributi/raccomandate/${mailId}/association`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
}
