"use client";

import Link from "next/link";
import { useState } from "react";
import { useSessionBootstrap } from "@/lib/use-session-bootstrap";
import type { RegisterView } from "@/types/notice-register";
import { DocumentDetail } from "./document-detail";
import { RecordForm } from "./mutation-form";
import { panelClass } from "./presentation";
import { RegisterList } from "./register-list";
import { ImportWorkspace } from "./import-workspace";

const VIEWS = { tutti: "Tutti gli avvisi", anomalie: "Anomalie", affidamenti: "Affidamenti", riconciliati: "Riconciliati", importazioni: "Importazioni" };

function RegisterWorkspace({ token, canEdit }: { token: string; canEdit: boolean }) {
  const [view, setView] = useState<RegisterView | "importazioni">("tutti");
  const [selected, setSelected] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  function back() { setSelected(null); setCreating(false); }
  return <div className="space-y-5">
    <header className="rounded-2xl border border-[#d8dfd3] bg-gradient-to-br from-[#edf4e9] via-white to-[#f3eee0] p-5 sm:p-7">
      <p className="section-title">Tributi | Registro operativo</p><h2 className="mt-2 text-2xl font-semibold text-[#1D4E35]">Documenti, notifiche e recupero crediti</h2>
      <p className="mt-3 max-w-3xl text-sm leading-6 text-gray-600">Generato, inviato e notificato sono stati distinti. La verifica STEP riguarda ogni posizione annuale. Le registrazioni non creano debiti e non autorizzano invii.</p>
      <div className="mt-4 flex flex-wrap gap-2"><Link className="btn-secondary" href="/ruolo/tributi">Torna ai tributi</Link>
        {canEdit && <button className="btn-primary" onClick={() => { setCreating(true); setSelected(null); }}>Registra avviso storico</button>}
      </div>{!canEdit && <p className="mt-3 text-sm">Accesso in sola lettura.</p>}
    </header>
    {selected || creating ? <button className="btn-secondary" onClick={back}>Torna al registro</button> : <nav aria-label="Viste registro" className="flex flex-wrap gap-2">
      {Object.entries(VIEWS).map(([key, label]) => <button key={key} className="btn-secondary" aria-pressed={view === key} onClick={() => setView(key as keyof typeof VIEWS)}>{label}</button>)}
    </nav>}
    {creating && canEdit && <section className={panelClass}><RecordForm token={token} version={1} path="" method="POST" title="Nuovo avviso storico" kind="document" initial={{}}
      onSaved={(result) => { setCreating(false); setSelected(result.document_id); }} /></section>}
    {selected && <DocumentDetail key={selected} token={token} documentId={selected} canEdit={canEdit} onSelect={setSelected} />}
    {!selected && !creating && <RegisterViewContent view={view} token={token} canEdit={canEdit} onSelect={setSelected} />}
  </div>;
}

function RegisterViewContent({ view, token, canEdit, onSelect }: { view: keyof typeof VIEWS; token: string; canEdit: boolean; onSelect: (id: string) => void }) {
  if (view === "importazioni") return <ImportWorkspace token={token} canEdit={canEdit} onSelect={onSelect} />;
  return <RegisterList key={view} token={token} view={view} onSelect={onSelect} />;
}

export function NoticeRegisterWorkspace() {
  const session = useSessionBootstrap();
  if (session.status !== "ready" || !session.token || !session.currentUser) return <p role="status">Verifica accesso al registro...</p>;
  const hasModule = session.currentUser.role === "super_admin" || session.currentUser.enabled_modules.includes("ruolo");
  if (!hasModule || !session.grantedSectionKeys.includes("ruolo.tributi.view")) return <p role="alert">Accesso al registro non autorizzato.</p>;
  return <RegisterWorkspace key={session.token} token={session.token} canEdit={session.grantedSectionKeys.includes("ruolo.tributi.manage_status")} />;
}
