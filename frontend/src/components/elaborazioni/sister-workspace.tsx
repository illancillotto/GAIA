"use client";

import Link from "next/link";
import { useState } from "react";

import { useAppShellContext } from "@/components/layout/app-shell-context";
import { ElaborazioneNoticeCard } from "@/components/elaborazioni/module-chrome";
import { ElaborazioneRequestWorkspace } from "@/components/elaborazioni/request-workspace";
import { RecentBatchesOpenProvider } from "@/components/elaborazioni/recent-batches-open-context";
import { SisterPortalHealthWorkspace } from "@/components/elaborazioni/sister-portal-health-workspace";
import { ElaborazioneWorkspaceModal } from "@/components/elaborazioni/workspace-modal";
import { hasUserModuleAccess } from "@/lib/module-access";

export type SisterWorkspaceView = "operations" | "health";

type ModalState = {
  href: string;
  title: string;
  description: string;
};

function canViewPortalHealth(currentUser: ReturnType<typeof useAppShellContext>["currentUser"]): boolean {
  return Boolean(
    currentUser &&
      (currentUser.role === "admin" ||
        currentUser.role === "super_admin" ||
        hasUserModuleAccess(currentUser, "catasto")),
  );
}

export function SisterWorkspace({ initialView = "operations" }: { initialView?: SisterWorkspaceView }) {
  const { currentUser } = useAppShellContext();
  const [modalState, setModalState] = useState<ModalState | null>(null);
  const portalHealthAllowed = canViewPortalHealth(currentUser);
  const activeView = initialView === "health" && portalHealthAllowed ? "health" : "operations";

  function openBatchModal(batchId: string): void {
    setModalState({
      href: `/elaborazioni/batches/${batchId}`,
      title: "Dettaglio batch visure",
      description: "Dettaglio aperto in modale per mantenere il contesto del workspace visure.",
    });
  }

  return (
    <div className="space-y-6">
      <nav aria-label="Sezioni SISTER" className="flex flex-wrap gap-2 rounded-[22px] border border-[#d9dfd6] bg-white p-2 shadow-sm">
        <Link
          aria-current={activeView === "operations" ? "page" : undefined}
          className={`rounded-2xl px-4 py-2.5 text-sm font-semibold transition ${activeView === "operations" ? "bg-[#1D4E35] text-white" : "text-gray-600 hover:bg-[#eef6f0] hover:text-[#1D4E35]"}`}
          href="/elaborazioni/sister"
        >
          Operatività visure
        </Link>
        {portalHealthAllowed ? (
          <Link
            aria-current={activeView === "health" ? "page" : undefined}
            className={`rounded-2xl px-4 py-2.5 text-sm font-semibold transition ${activeView === "health" ? "bg-[#1D4E35] text-white" : "text-gray-600 hover:bg-[#eef6f0] hover:text-[#1D4E35]"}`}
            href="/elaborazioni/sister?view=health"
          >
            Stato portale
          </Link>
        ) : null}
      </nav>

      {initialView === "health" && !portalHealthAllowed ? (
        <ElaborazioneNoticeCard
          title="Stato portale non disponibile"
          description="La telemetria SISTER richiede l'accesso al modulo Catasto. È stata aperta la vista operativa."
          tone="warning"
        />
      ) : null}

      {activeView === "health" ? (
        <SisterPortalHealthWorkspace />
      ) : (
        <>
          <RecentBatchesOpenProvider value={{ onOpenBatch: openBatchModal }}>
            <ElaborazioneRequestWorkspace embedded initialMode="autosync" onOpenBatch={openBatchModal} />
          </RecentBatchesOpenProvider>
          <ElaborazioneWorkspaceModal
            description={modalState?.description}
            href={modalState?.href ?? null}
            onClose={() => setModalState(null)}
            open={modalState != null}
            title={modalState?.title ?? "Workspace"}
          />
        </>
      )}
    </div>
  );
}
