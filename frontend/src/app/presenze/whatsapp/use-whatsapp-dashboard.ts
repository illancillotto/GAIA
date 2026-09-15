"use client";

import { useDeferredValue, useEffect, useState } from "react";

import {
  getPresenzeWhatsAppDashboard,
  getPresenzeWhatsAppConfiguration,
  getPresenzeWhatsAppPreview,
  listPresenzeWhatsAppMessages,
  listPresenzeWhatsAppOptOuts,
  reconcilePresenzeWhatsAppMessage,
  restorePresenzeWhatsAppUser,
  updatePresenzeWhatsAppPhone,
  updatePresenzeWhatsAppConfiguration,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { PresenzeWhatsAppConfig, PresenzeWhatsAppConfigUpdate, PresenzeWhatsAppDashboardSummary, PresenzeWhatsAppMessage, PresenzeWhatsAppOptOut, PresenzeWhatsAppPreview } from "@/types/api";

type ConfigurationContext = {
  setBusy: (value: boolean) => void;
  setConfiguration: (value: PresenzeWhatsAppConfig) => void;
  setError: (value: string | null) => void;
  setSummary: (value: PresenzeWhatsAppDashboardSummary) => void;
};

async function saveDashboardConfiguration(
  payload: PresenzeWhatsAppConfigUpdate,
  context: ConfigurationContext,
): Promise<void> {
  const token = getStoredAccessToken();
  if (!token) return;
  context.setBusy(true);
  try {
    context.setConfiguration(await updatePresenzeWhatsAppConfiguration(token, payload));
    context.setSummary(await getPresenzeWhatsAppDashboard(token));
    context.setError(null);
  } catch (reason) {
    context.setError(reason instanceof Error ? reason.message : "Impossibile salvare la configurazione WhatsApp");
    throw reason;
  } finally {
    context.setBusy(false);
  }
}

export function useWhatsAppDashboard(isSuperAdmin = false) {
  const [summary, setSummary] = useState<PresenzeWhatsAppDashboardSummary | null>(null);
  const [messages, setMessages] = useState<PresenzeWhatsAppMessage[]>([]);
  const [total, setTotal] = useState(0);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<PresenzeWhatsAppMessage | null>(null);
  const [preview, setPreview] = useState<PresenzeWhatsAppPreview | null>(null);
  const [optOuts, setOptOuts] = useState<PresenzeWhatsAppOptOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [configuration, setConfiguration] = useState<PresenzeWhatsAppConfig | null>(null);
  const deferredQuery = useDeferredValue(query);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    setLoading(true);
    Promise.all([
      getPresenzeWhatsAppDashboard(token),
      listPresenzeWhatsAppMessages(token, { status, q: deferredQuery, page, pageSize: 25 }),
      listPresenzeWhatsAppOptOuts(token),
      isSuperAdmin ? getPresenzeWhatsAppConfiguration(token) : Promise.resolve(null),
    ]).then(([dashboard, history, stops, config]) => {
      setSummary(dashboard);
      setMessages(history.items);
      setTotal(history.total);
      setOptOuts(stops);
      setConfiguration(config);
      setError(null);
    }).catch((reason) => setError(reason instanceof Error ? reason.message : "Impossibile caricare la dashboard WhatsApp")).finally(() => setLoading(false));
  }, [deferredQuery, isSuperAdmin, page, status]);

  async function saveConfiguration(payload: PresenzeWhatsAppConfigUpdate): Promise<void> {
    return saveDashboardConfiguration(payload, {
      setBusy, setConfiguration, setError, setSummary,
    });
  }

  async function openPreview(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;
    setBusy(true);
    try {
      setPreview(await getPresenzeWhatsAppPreview(token));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Impossibile calcolare l’anteprima");
    } finally {
      setBusy(false);
    }
  }

  async function restoreUser(userId: number): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;
    await restorePresenzeWhatsAppUser(token, userId);
    setOptOuts((items) => items.filter((item) => item.application_user_id !== userId));
  }

  async function updatePhone(userId: number, phone: string): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;
    await updatePresenzeWhatsAppPhone(token, userId, phone);
    setPreview(await getPresenzeWhatsAppPreview(token));
  }

  async function reconcile(messageId: string, sent: boolean, evidence: string, providerMessageId: string): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;
    setBusy(true);
    try {
      await reconcilePresenzeWhatsAppMessage(token, messageId, { sent, evidence, provider_message_id: providerMessageId || null });
      const history = await listPresenzeWhatsAppMessages(token, { status, q: deferredQuery, page, pageSize: 25 });
      setMessages(history.items);
      setTotal(history.total);
      setSelected(null);
    } finally {
      setBusy(false);
    }
  }

  return { summary, messages, total, query, status, page, selected, preview, optOuts, configuration, loading, busy, error, setQuery, setStatus, setPage, setSelected, setPreview, openPreview, restoreUser, updatePhone, reconcile, saveConfiguration };
}
