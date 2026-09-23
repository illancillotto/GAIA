"use client";
import { useEffect, useState } from "react";
import { listAllPresenzeCollaborators, listPresenzeDailyRecords } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { buildMonthlySheet, monthlyCalendar } from "@/lib/presenze-monthly-sheet";
import type { PresenzeCollaborator } from "@/types/api";

export function useMonthlyPeople(setPersonId: (id: string) => void) {
  const [people, setPeople] = useState<PresenzeCollaborator[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    const token = getStoredAccessToken();
    if (!token) return;
    listAllPresenzeCollaborators(token).then(items => {
      if (!active) return;
      setPeople(items);
      setPersonId(items[0]?.id ?? "");
    }).catch(() => { if (active) setError("Impossibile caricare i dipendenti."); });
    return () => { active = false; };
  }, [setPersonId]);
  return { people, error };
}
export function useMonthlyReport(month: string, person: PresenzeCollaborator | undefined, reload: number) {
  const [report, setReport] = useState<ReturnType<typeof buildMonthlySheet> | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    let active = true;
    setReport(null);
    setLoading(false);
    const token = getStoredAccessToken();
    if (!token || !person || !month) return;
    const selected = person;
    setLoading(true);
    setError("");
    async function load() {
      try {
        const days = monthlyCalendar(month);
        const data = await listPresenzeDailyRecords(token!, {
          collaboratorId: selected.id, dateFrom: days[0].date, dateTo: days[days.length - 1].date,
          pageSize: 100, includePunches: true, includeRawPayload: false,
        });
        if (!active) return;
        if (data.total > data.items.length) throw new Error("Dati mensili incompleti.");
        setReport(buildMonthlySheet(month, data.items.map(item => ({ ...item, contract_kind: selected.contract_kind }))));
      } catch (cause) {
        if (active) setError(cause instanceof Error ? cause.message : "Caricamento non riuscito.");
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => { active = false; };
  }, [month, person, reload]);

  return { report, error, loading };
}
