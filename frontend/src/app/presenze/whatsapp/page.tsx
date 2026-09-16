"use client";

import { ProtectedPage } from "@/components/app/protected-page";
import { useSessionBootstrap } from "@/lib/use-session-bootstrap";

import { useWhatsAppDashboard } from "./use-whatsapp-dashboard";
import { WhatsAppChannelOverview, WhatsAppMessageHistory } from "./whatsapp-dashboard-sections";
import { WhatsAppMessageDialog, WhatsAppPreviewDialog } from "./whatsapp-dialogs";
import { WhatsAppConfiguration } from "./whatsapp-configuration";
import { WhatsAppSessionManager } from "./whatsapp-session-manager";

export default function PresenzeWhatsAppPage() {
  const session = useSessionBootstrap();
  const isSuperAdmin = session.currentUser?.role === "super_admin";
  const dashboard = useWhatsAppDashboard(isSuperAdmin);
  return (
    <ProtectedPage title="Promemoria WhatsApp" description="Controlla destinatari, consegne, letture e anomalie dei promemoria timbrature." breadcrumb="Presenze" requiredModule="presenze" requiredRoles={["admin", "super_admin"]}>
      <WhatsAppChannelOverview summary={dashboard.summary} busy={dashboard.busy} onOpenPreview={() => void dashboard.openPreview()} />
      {isSuperAdmin ? <div className="grid gap-5 xl:grid-cols-2"><WhatsAppSessionManager /><WhatsAppConfiguration configuration={dashboard.configuration} busy={dashboard.busy} onSave={dashboard.saveConfiguration} /></div> : null}
      {dashboard.error ? <p className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700" role="alert">{dashboard.error}</p> : null}
      <WhatsAppMessageHistory messages={dashboard.messages} total={dashboard.total} query={dashboard.query} status={dashboard.status} page={dashboard.page} loading={dashboard.loading} onQuery={(value) => { dashboard.setQuery(value); dashboard.setPage(1); }} onStatus={(value) => { dashboard.setStatus(value); dashboard.setPage(1); }} onPage={dashboard.setPage} onOpen={dashboard.setSelected} />
      {dashboard.selected ? <WhatsAppMessageDialog message={dashboard.selected} busy={dashboard.busy} onClose={() => dashboard.setSelected(null)} onReconcile={(sent, evidence, providerMessageId) => dashboard.reconcile(dashboard.selected!.id, sent, evidence, providerMessageId)} /> : null}
      {dashboard.preview ? <WhatsAppPreviewDialog preview={dashboard.preview} optOuts={dashboard.optOuts} onClose={() => dashboard.setPreview(null)} onRestore={dashboard.restoreUser} onUpdatePhone={dashboard.updatePhone} /> : null}
    </ProtectedPage>
  );
}
