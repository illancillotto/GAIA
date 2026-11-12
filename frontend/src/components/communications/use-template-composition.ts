"use client";

import { useEffect, useMemo, useState } from "react";
import { communications } from "@/lib/communications-api";
import type { Channel, Template } from "@/types/communications";
import type { useCommunicationsWorkspace } from "./use-workspace";

type Workspace = ReturnType<typeof useCommunicationsWorkspace>;
type Preview = { subject: string; body: string; source_sha256: string; missing_variables?: string[]; send_blockers?: string[] };
type Props = {
  token: string; sourceId: string; channel: Channel; templates: Template[];
  compose: Workspace["compose"]; setCompose: Workspace["setCompose"];
};

export function useTemplateComposition({ token, sourceId, channel, templates, compose, setCompose }: Props) {
  const available = useMemo(() => templates.filter((value) => value.channel === channel && value.status === "approved"), [templates, channel]);
  const [choice, setChoice] = useState<string | null>(null);
  const templateId = choice ?? (available.length === 1 ? available[0].id : "");
  const key = `${sourceId}:${templateId}`;
  const [revision, setRevision] = useState(0);
  const [status, setStatus] = useState({ key: "", loading: false, error: "", sha: "", incomplete: "", blocked: "" });

  useEffect(() => {
    setCompose((current) => ({ ...current, template_id: templateId }));
    if (![sourceId, templateId].every(Boolean)) { setStatus({ key, loading: false, error: "", sha: "", incomplete: "", blocked: "" }); return; }
    let disposed = false;
    setStatus({ key, loading: true, error: "", sha: "", incomplete: "", blocked: "" });
    setCompose((current) => ({ ...current, subject: "", body: "" }));
    const query = new URLSearchParams({ template_id: templateId, channel });
    communications<Preview>(token, `/ruolo/candidates/${sourceId}/template-preview?${query}`)
      .then((preview) => {
        if (disposed) return;
        setCompose((current) => ({ ...current, subject: preview.subject, body: preview.body }));
        const details = Object.assign({ missing_variables: [], send_blockers: [] }, preview);
        setStatus({ key, loading: false, error: "", sha: preview.source_sha256, incomplete: details.missing_variables.join(", "), blocked: details.send_blockers.join(" · ") });
      })
      .catch((error: unknown) => {
        if (!disposed) setStatus({ key, loading: false, error: error instanceof Error ? error.message : "Testo del template non disponibile", sha: "", incomplete: "", blocked: "" });
      });
    return () => { disposed = true; };
  }, [token, sourceId, channel, templateId, key, revision, setCompose]);

  function selectTemplate(id: string) {
    setChoice(id);
    setCompose((current) => ({ ...current, template_id: id }));
  }
  const pdfChanged = Boolean(status.sha && compose.expected_source_sha256 && status.sha !== compose.expected_source_sha256);
  const error = pdfChanged ? "Il PDF è cambiato durante la composizione: riapri l’avviso e ricontrolla il testo." : status.error;
  const loading = Boolean(templateId) && (status.key !== key || status.loading);
  const ready = !templateId || [status.key === key, !loading, !error, !status.incomplete, !status.blocked, status.sha === compose.expected_source_sha256].every(Boolean);
  return { available, templateId, selectTemplate, loading, error, incomplete: status.incomplete, blocked: status.blocked, ready, retry: () => setRevision((value) => value + 1) };
}
