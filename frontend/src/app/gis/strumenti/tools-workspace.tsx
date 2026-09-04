"use client";

import { GisActivityCenter } from "./activity-center";
import { GisQgisTools } from "./qgis-tools";
import {
  GisToolsFeedback,
  GisToolsHero,
  GisToolsImportConfirmation,
  GisToolsImportSection,
  GisToolsSessionStatus,
  GisToolsUploadSection,
} from "./tools-workspace-panels";
import { useGisToolsWorkspace } from "./use-gis-tools-workspace";

export function GisToolsWorkspace({ token }: { token: string | null }) {
  const tools = useGisToolsWorkspace(token);
  if (!token) {
    return <GisToolsSessionStatus />;
  }
  return (
    <div className="space-y-6">
      <GisToolsHero />
      <GisQgisTools token={token} />
      <GisToolsFeedback notice={tools.notice} error={tools.error} />
      <GisToolsUploadSection tools={tools} />
      <GisToolsImportSection tools={tools} />
      <GisActivityCenter key={tools.historyVersion} token={token} layers={tools.layers} onResumeImport={tools.loadPreview} />
      <GisToolsImportConfirmation tools={tools} />
    </div>
  );
}
