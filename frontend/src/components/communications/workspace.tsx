"use client";

import Link from "next/link";
import { RuoloModulePage } from "@/components/ruolo/module-page";
import { useSessionBootstrap } from "@/lib/use-session-bootstrap";
import type { Channel } from "@/types/communications";
import { useCommunicationsWorkspace } from "./use-workspace";
import { CandidateFilters, CandidateTable, NewCommunication } from "./workspace-controls";
import { CommunicationComposer } from "./composer";
import { CommunicationsNavigation } from "./navigation";

export function CommunicationsAccess({ channel }: { channel: Channel }) {
  const session = useSessionBootstrap();
  if (session.status !== "ready" || !session.token || !session.currentUser) return <p role="status">Verifica accesso...</p>;
  if (!session.currentUser.enabled_modules.includes("ruolo") && session.currentUser.role !== "super_admin") return <p role="alert">Accesso non autorizzato.</p>;
  if (!session.grantedSectionKeys.includes("ruolo.tributi.view")) return <p role="alert">Accesso non autorizzato.</p>;
  const canEdit = session.grantedSectionKeys.includes("ruolo.tributi.manage_status");
  return <RuoloModulePage title="Invio solleciti" description="Comunicazioni PEC ed email con revisione individuale del documento." requiredSection="ruolo.tributi.view">
    <CommunicationsNavigation channel={channel} />
    {["admin", "super_admin"].includes(session.currentUser.role) && <Link className="btn-secondary my-4 inline-block" href="/gaia/communications">Amministrazione comunicazioni</Link>}
    <ChannelWorkspace token={session.token} channel={channel} canEdit={canEdit} />
  </RuoloModulePage>;
}

function ChannelWorkspace({ token, channel, canEdit }: { token: string; channel: Channel; canEdit: boolean }) {
  const workspace = useCommunicationsWorkspace(token, channel, canEdit);
  return <div className="mt-5 grid min-w-0 items-start gap-5 xl:grid-cols-2">
    <CandidateFilters workspace={workspace} />
    {workspace.status.error && <p role="alert" className="rounded-lg bg-rose-50 p-3 text-rose-800 xl:col-span-2">{workspace.status.error}</p>}
    {workspace.status.loading && <p role="status" className="xl:col-span-2">Caricamento candidati 2021...</p>}
    <CandidateTable workspace={workspace} channel={channel} canEdit={canEdit} />
    <aside aria-label="Composizione avviso" className="min-w-0 rounded-2xl border border-[#d8dfd3] bg-[#f7f9f5] p-3 xl:sticky xl:top-4 xl:max-h-[calc(100dvh-6rem)] xl:overflow-y-auto">
      {workspace.message ? <CommunicationComposer key={`${workspace.message.id}:${workspace.message.version}`} token={token} message={workspace.message} accounts={workspace.data.accounts} canEdit={canEdit} onChange={workspace.setMessage} /> : <NewCommunication workspace={workspace} channel={channel} canEdit={canEdit} />}
    </aside>
  </div>;
}
