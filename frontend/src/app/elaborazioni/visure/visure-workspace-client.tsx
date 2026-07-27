"use client";

import { useState } from "react";

import { ElaborazioneRequestWorkspace } from "@/components/elaborazioni/request-workspace";
import { RecentBatchesOpenProvider } from "@/components/elaborazioni/recent-batches-open-context";
import { ElaborazioneWorkspaceModal } from "@/components/elaborazioni/workspace-modal";

type ModalState = {
  href: string;
  title: string;
  description: string;
};

export function ElaborazioniVisureWorkspaceClient() {
  const [modalState, setModalState] = useState<ModalState | null>(null);

  function openBatchModal(batchId: string): void {
    setModalState({
      href: `/elaborazioni/batches/${batchId}`,
      title: "Dettaglio batch visure",
      description: "Dettaglio aperto in modale per mantenere il contesto del workspace visure.",
    });
  }

  return (
    <>
      <RecentBatchesOpenProvider value={{ onOpenBatch: openBatchModal }}>
        <ElaborazioneRequestWorkspace embedded initialMode="recent" onOpenBatch={openBatchModal} />
      </RecentBatchesOpenProvider>
      <ElaborazioneWorkspaceModal
        description={modalState?.description}
        href={modalState?.href ?? null}
        onClose={() => setModalState(null)}
        open={modalState != null}
        title={modalState?.title ?? "Workspace"}
      />
    </>
  );
}
