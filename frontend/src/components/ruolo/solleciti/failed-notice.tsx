"use client";

import { useEffect, useRef, useState } from "react";

import { errorMessage } from "@/components/ruolo/poste-dispatch/labels";
import { regenerateReminderItem } from "@/lib/ruolo-regeneration-api";
import { GeneratedNoticePreview } from "./document-access";

type Props = { token: string; itemId: string; detail: string | null; canEdit: boolean; onRegenerated: () => void };
type Attempt = { running: boolean; problem: string | null; done?: boolean };

// A sollecito whose PDF failed is rendered again as soon as an editor opens its batch.
export function FailedNotice({ token, itemId, detail, canEdit, onRegenerated }: Props) {
  const started = useRef(false);
  const [attempt, setAttempt] = useState<Attempt>({ running: false, problem: null });

  async function retry() {
    setAttempt({ running: true, problem: null });
    try {
      const result = await regenerateReminderItem(token, itemId, "template");
      if (result.outcome === "regenerated") {
        setAttempt({ running: false, problem: null, done: true });
        onRegenerated();
        return;
      }
      setAttempt({ running: false, problem: result.detail ?? "PDF non generato" });
    } catch (err) {
      setAttempt({ running: false, problem: errorMessage(err, "Rigenerazione non riuscita") });
    }
  }

  useEffect(() => {
    if (!canEdit || started.current) return;
    started.current = true;
    void retry();
  });

  // The batch keeps its old data until reopened; the new PDF is shown right away.
  if (attempt.done) return <GeneratedNoticePreview token={token} url={`/ruolo/tributi/solleciti/items/${itemId}/download`} />;
  return <div className="mt-3 space-y-2 border-t border-slate-200 pt-3 text-sm">
    {attempt.running
      ? <p role="status" className="text-slate-600">PDF non generato: rigenerazione in corso...</p>
      : <p role="alert" className="text-rose-800">PDF non generato: {attempt.problem ?? detail ?? "motivo non registrato"}</p>}
    {canEdit && !attempt.running && <button type="button" className="btn-secondary" onClick={() => void retry()}>Riprova a generare</button>}
  </div>;
}
