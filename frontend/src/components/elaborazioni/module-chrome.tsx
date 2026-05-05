"use client";

import type { ReactNode } from "react";

export {
  ModuleWorkspaceHero as ElaborazioneHero,
  ModuleWorkspaceMiniStat as ElaborazioneMiniStat,
  ModuleWorkspaceNoticeCard as ElaborazioneNoticeCard,
} from "@/components/layout/module-workspace-hero";

export function ElaborazionePanelHeader({
  badge,
  title,
  description,
  descriptionTooltip,
  actions,
}: {
  badge?: ReactNode;
  title: string;
  description: string;
  /** Testo mostrato al passaggio del mouse sulla descrizione (tooltip nativo). */
  descriptionTooltip?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="border-b border-[#edf1eb] bg-[linear-gradient(135deg,_rgba(29,78,53,0.06),_rgba(255,255,255,0.92))] px-6 py-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          {badge ? (
            <div className="inline-flex items-center gap-2 rounded-full bg-[#e8f2ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
              {badge}
            </div>
          ) : null}
          <p className="mt-3 text-lg font-semibold text-gray-900">{title}</p>
          <p
            className={descriptionTooltip ? "mt-2 max-w-2xl cursor-help text-sm leading-6 text-gray-600" : "mt-2 max-w-2xl text-sm leading-6 text-gray-600"}
            title={descriptionTooltip}
          >
            {description}
          </p>
        </div>
        {actions ? <div>{actions}</div> : null}
      </div>
    </div>
  );
}
