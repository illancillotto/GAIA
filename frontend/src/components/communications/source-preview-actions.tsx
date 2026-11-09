"use client";
import { useCallback } from "react";
import { SourcePreview } from "./source-preview";
import type { useCommunicationsWorkspace } from "./use-workspace";

type Workspace = ReturnType<typeof useCommunicationsWorkspace>;

/** Keep the draft command tied to successful rendering of the selected source. */
export function SourcePreviewActions({ token, sourceId, workspace }: { token: string; sourceId: string; workspace: Workspace }) {
  const { compose, setCompose, status, create } = workspace;
  const onReady = useCallback((sha256: string) => setCompose((value) => ({ ...value, expected_source_sha256: sha256 })), [setCompose]);
  return <>
    <button className="btn-primary" disabled={status.busy || !compose.recipient || !compose.expected_source_sha256} onClick={() => void create()}>Crea bozza e snapshot PDF</button>
    <SourcePreview token={token} sourceId={sourceId} onReady={onReady} />
  </>;
}
