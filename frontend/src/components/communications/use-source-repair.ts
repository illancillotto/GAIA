"use client";

import { useRef, useState } from "react";
import { communications } from "@/lib/communications-api";

/** Reopen the exact PDF and its text after an explicit, versioned document repair. */
export function useSourceRepair(token: string, sourceId: string, expectedSha: string, reloadText: () => void) {
  const current = useRef(sourceId);
  current.current = sourceId;
  const [state, setState] = useState({ identity: "", busy: false, error: "", revision: 0 });
  async function complete() {
    setState(value => ({ ...value, identity: sourceId, busy: true, error: "" }));
    try {
      await communications(token, `/ruolo/candidates/${sourceId}/complete-portal-snapshot?expected_source_sha256=${expectedSha}`, { method: "POST" });
      if (current.current !== sourceId) return;
      setState(value => ({ identity: sourceId, busy: false, error: "", revision: value.revision + 1 }));
      reloadText();
    } catch (error: unknown) {
      if (current.current === sourceId) setState(value => ({ ...value, busy: false, error: error instanceof Error ? error.message : "Revisione PDF non riuscita" }));
    }
  }
  return { ...state, busy: state.identity === sourceId && state.busy, error: state.identity === sourceId ? state.error : "", complete };
}
