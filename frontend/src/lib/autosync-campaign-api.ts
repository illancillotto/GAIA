import { request } from "@/lib/api";
import type { CatastoPerpetualSyncItem, ElaborazioneOperationResponse } from "@/types/api";

export type RoleCampaignScope = "ruolo_particella" | "ruolo_soggetto";

export type AutoSyncCampaignItemsPage = {
  items: CatastoPerpetualSyncItem[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
};

export function getElaborazioneRuoloAutoSyncCampaignItems(
  token: string,
  scope: RoleCampaignScope,
  limit = 50,
  offset = 0,
): Promise<AutoSyncCampaignItemsPage> {
  const query = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  return request<AutoSyncCampaignItemsPage>(
    `/elaborazioni/ruolo-autosync/campaigns/${scope}/items?${query.toString()}`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
}

export function retryElaborazioneRuoloAutoSyncCampaignFailures(
  token: string,
  scope: RoleCampaignScope,
): Promise<ElaborazioneOperationResponse> {
  return request<ElaborazioneOperationResponse>(
    `/elaborazioni/ruolo-autosync/campaigns/${scope}/retry-failed`,
    { method: "POST", headers: { Authorization: `Bearer ${token}` } },
  );
}
