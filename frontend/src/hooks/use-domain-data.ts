"use client";

import { useEffect, useState } from "react";

import { getNasGroups, getNasUsers, getShares } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { NasGroup, NasUser, Share } from "@/types/api";

type DomainDataState = {
  users: NasUser[];
  groups: NasGroup[];
  shares: Share[];
  error: string | null;
};

export function useDomainData() {
  const [state, setState] = useState<DomainDataState>({
    users: [],
    groups: [],
    shares: [],
    error: null,
  });

  useEffect(() => {
    async function loadDomainData() {
      const token = getStoredAccessToken();
      if (!token) return;

      try {
        const [users, groups, shares] = await Promise.all([
          getNasUsers(token),
          getNasGroups(token),
          getShares(token),
        ]);
        setState({
          users,
          groups,
          shares,
          error: null,
        });
      } catch (error) {
        setState((current) => ({
          ...current,
          error: error instanceof Error ? error.message : "Errore caricamento dati dominio",
        }));
      }
    }

    void loadDomainData();
  }, []);

  return state;
}
