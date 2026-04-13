"use client";

import Link from "next/link";

import { ProtectedPage } from "@/components/app/protected-page";
import { ElaborazioneHero, ElaborazioneNoticeCard, ElaborazionePanelHeader } from "@/components/elaborazioni/module-chrome";
import { LockIcon, RefreshIcon, UsersIcon } from "@/components/ui/icons";

type ElaborazioniWhiteCompanyWorkspaceProps = {
  embedded?: boolean;
};

function WhiteCompanyWorkspaceContent() {
  return (
    <>
      <ElaborazioneHero
        badge={
          <>
            <UsersIcon className="h-3.5 w-3.5" />
            WhiteCompany
          </>
        }
        title="WhiteCompany · Bonifica Oristanese"
        description="Gestione credenziali, test, e console sync. I consorziati vengono sincronizzati in staging e poi validati nel modulo Utenze."
        actions={
          <ElaborazioneNoticeCard
            title="Accesso amministrativo richiesto"
            description="La console sync è riservata ad admin/super admin. Le credenziali sono gestite nella sezione Elaborazioni."
          />
        }
      />

      <div className="grid gap-6 xl:grid-cols-2">
        <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
          <ElaborazionePanelHeader
            badge={
              <>
                <LockIcon className="h-3.5 w-3.5" />
                Setup
              </>
            }
            title="Credenziali WhiteCompany"
            description="Configura e testa il pool di credenziali operative usate per la sync (login e resilienza errori)."
            actions={
              <Link className="btn-secondary" href="/elaborazioni/settings">
                Apri credenziali
              </Link>
            }
          />
          <div className="p-6">
            <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
              <p className="text-sm font-medium text-gray-900">Suggerimento operativo</p>
              <p className="mt-1 text-sm text-gray-600">
                Prima di lanciare una sync, verifica che ci sia almeno una credenziale attiva e senza errori recenti.
              </p>
            </div>
          </div>
        </article>

        <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
          <ElaborazionePanelHeader
            badge={
              <>
                <RefreshIcon className="h-3.5 w-3.5" />
                Sync
              </>
            }
            title="Console sync WhiteCompany"
            description="Avvio e monitor delle entità sincronizzate (operatori) e consorziati (staging Utenze)."
            actions={
              <Link className="btn-secondary" href="/elaborazioni/bonifica">
                Apri console
              </Link>
            }
          />
          <div className="p-6">
            <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
              <p className="text-sm font-medium text-gray-900">Nota sui consorziati</p>
              <p className="mt-1 text-sm text-gray-600">
                I consorziati vengono importati separatamente e finiscono nello staging del modulo Utenze per revisione manuale.
              </p>
            </div>
          </div>
        </article>
      </div>
    </>
  );
}

export function ElaborazioniWhiteCompanyWorkspace({ embedded }: ElaborazioniWhiteCompanyWorkspaceProps) {
  if (embedded) {
    return <WhiteCompanyWorkspaceContent />;
  }

  return (
    <ProtectedPage
      title="WhiteCompany"
      description="Console operativa per credenziali e sincronizzazione dati WhiteCompany (Bonifica Oristanese)."
      breadcrumb="Elaborazioni"
      requiredModule="catasto"
    >
      <WhiteCompanyWorkspaceContent />
    </ProtectedPage>
  );
}

