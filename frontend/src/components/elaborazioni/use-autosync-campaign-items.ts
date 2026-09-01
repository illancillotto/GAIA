"use client";

import { useCallback, useEffect, useState } from "react";

import {
  getElaborazioneRuoloAutoSyncCampaignItems,
  type RoleCampaignScope,
} from "@/lib/autosync-campaign-api";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatastoPerpetualSyncItem } from "@/types/api";

const PAGE_SIZE = 50;
const ROLE_SCOPES: RoleCampaignScope[] = ["ruolo_particella", "ruolo_soggetto"];

type CampaignPageState = {
  items: CatastoPerpetualSyncItem[];
  total: number;
  hasMore: boolean;
  loading: boolean;
  error: string | null;
};

const EMPTY_PAGE: CampaignPageState = {
  items: [],
  total: 0,
  hasMore: false,
  loading: false,
  error: null,
};

export type AutoSyncCampaignPages = Record<RoleCampaignScope, CampaignPageState>;

function initialPages(): AutoSyncCampaignPages {
  return {
    ruolo_particella: { ...EMPTY_PAGE },
    ruolo_soggetto: { ...EMPTY_PAGE },
  };
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Errore caricamento elenco AutoSync";
}

export function useAutoSyncCampaignItems() {
  const [pages, setPages] = useState<AutoSyncCampaignPages>(initialPages);

  const load = useCallback(async (scope: RoleCampaignScope, append: boolean) => {
    const token = getStoredAccessToken();
    if (!token) return;
    const offset = append ? pages[scope].items.length : 0;
    setPages((current) => ({
      ...current,
      [scope]: { ...current[scope], loading: true, error: null },
    }));
    try {
      const page = await getElaborazioneRuoloAutoSyncCampaignItems(token, scope, PAGE_SIZE, offset);
      setPages((current) => ({
        ...current,
        [scope]: {
          items: append ? [...current[scope].items, ...page.items] : page.items,
          total: page.total,
          hasMore: page.has_more,
          loading: false,
          error: null,
        },
      }));
    } catch (error) {
      setPages((current) => ({
        ...current,
        [scope]: { ...current[scope], loading: false, error: errorMessage(error) },
      }));
    }
  }, [pages]);

  useEffect(() => {
    for (const scope of ROLE_SCOPES) void load(scope, false);
    // The first page is loaded once; explicit refreshes keep pagination stable.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    pages,
    loadMore: (scope: RoleCampaignScope) => load(scope, true),
    refresh: (scope: RoleCampaignScope) => load(scope, false),
  };
}
