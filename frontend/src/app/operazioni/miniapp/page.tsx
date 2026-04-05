"use client";

import Link from "next/link";

import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { TruckIcon, RefreshIcon, AlertTriangleIcon } from "@/components/ui/icons";

function MiniAppContent() {
  return (
    <div className="page-stack">
      <article className="panel-card">
        <div className="mb-6">
          <p className="section-title">Operazioni rapide</p>
          <p className="section-copy">Azioni principali per gli operatori sul campo.</p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Link
            href="/operazioni/miniapp"
            className="flex items-center gap-4 rounded-xl border border-gray-100 bg-white p-6 transition hover:border-gray-200 hover:bg-gray-50"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-[#D3EAD4] text-[#1D4E35]">
              <RefreshIcon className="h-6 w-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">Avvia attività</p>
              <p className="text-xs text-gray-500">Seleziona e inizia una nuova attività</p>
            </div>
          </Link>

          <Link
            href="/operazioni/miniapp"
            className="flex items-center gap-4 rounded-xl border border-gray-100 bg-white p-6 transition hover:border-gray-200 hover:bg-gray-50"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-[#D3EAD4] text-[#1D4E35]">
              <TruckIcon className="h-6 w-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">Chiudi attività</p>
              <p className="text-xs text-gray-500">Registra la chiusura dell&apos;attività in corso</p>
            </div>
          </Link>

          <Link
            href="/operazioni/miniapp"
            className="flex items-center gap-4 rounded-xl border border-gray-100 bg-white p-6 transition hover:border-gray-200 hover:bg-gray-50"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-[#D3EAD4] text-[#1D4E35]">
              <AlertTriangleIcon className="h-6 w-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">Nuova segnalazione</p>
              <p className="text-xs text-gray-500">Crea una segnalazione dal campo</p>
            </div>
          </Link>
        </div>
      </article>

      <article className="panel-card">
        <div className="mb-4">
          <p className="section-title">Accesso rapido</p>
          <p className="section-copy">Strumenti operativi per il personale.</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Link
            href="/operazioni/miniapp/bozze"
            className="flex items-center gap-4 rounded-xl border border-gray-100 bg-white p-5 transition hover:border-gray-200 hover:bg-gray-50"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#D3EAD4] text-[#1D4E35]">
              <TruckIcon className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">Bozze locali</p>
              <p className="text-xs text-gray-500">Gestione sincronizzazione offline</p>
            </div>
          </Link>
          <Link
            href="/operazioni"
            className="flex items-center gap-4 rounded-xl border border-gray-100 bg-white p-5 transition hover:border-gray-200 hover:bg-gray-50"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#D3EAD4] text-[#1D4E35]">
              <TruckIcon className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">Dashboard operazioni</p>
              <p className="text-xs text-gray-500">Torna alla vista principale</p>
            </div>
          </Link>
        </div>
      </article>
    </div>
  );
}

export default function MiniAppPage() {
  return (
    <OperazioniModulePage
      title="Mini-app"
      description="Interfaccia mobile-first per operatori sul campo."
      breadcrumb="Operatori"
    >
      {() => <MiniAppContent />}
    </OperazioniModulePage>
  );
}
