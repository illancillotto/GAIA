"use client";

import { useDeferredValue, useEffect, useState } from "react";

import {
  getPresenzeWhatsAppDashboard,
  getPresenzeWhatsAppPreview,
  listPresenzeWhatsAppMessages,
  listPresenzeWhatsAppOptOuts,
  reconcilePresenzeWhatsAppMessage,
  restorePresenzeWhatsAppUser,
  updatePresenzeWhatsAppPhone,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { PresenzeWhatsAppDashboardSummary, PresenzeWhatsAppMessage, PresenzeWhatsAppOptOut, PresenzeWhatsAppPreview } from "@/types/api";

export function useWhatsAppDashboard() {
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
  const deferredQuery = useDeferredValue(query);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    setLoading(true);
    Promise.all([
      getPresenzeWhatsAppDashboard(token),
      listPresenzeWhatsAppMessages(token, { status, q: deferredQuery, page, pageSize: 25 }),
      listPresenzeWhatsAppOptOuts(token),
    ]).then(([dashboard, history, stops]) => {
      setSummary(dashboard);
      setMessages(history.items);
      setTotal(history.total);
      setOptOuts(stops);
      setError(null);
    }).catch((reason) => setError(reason instanceof Error ? reason.message : "Impossibile caricare la dashboard WhatsApp")).finally(() => setLoading(false));
  }, [deferredQuery, page, status]);

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

  return { summary, messages, total, query, status, page, selected, preview, optOuts, loading, busy, error, setQuery, setStatus, setPage, setSelected, setPreview, openPreview, restoreUser, updatePhone, reconcile };
}
