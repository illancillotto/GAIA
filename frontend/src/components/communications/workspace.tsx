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
  const { message, setMessage, data, status } = workspace;
  return <div className="mt-5 space-y-5">
    <CandidateFilters workspace={workspace} />
    {status.error && <p role="alert" className="rounded-lg bg-rose-50 p-3 text-rose-800">{status.error}</p>}
    {status.loading && <p role="status">Caricamento candidati 2021...</p>}
    <CandidateTable workspace={workspace} channel={channel} canEdit={canEdit} />
    <NewCommunication workspace={workspace} channel={channel} canEdit={canEdit} />
    {message && <CommunicationComposer key={`${message.id}:${message.version}`} token={token} message={message} accounts={data.accounts} canEdit={canEdit} onChange={setMessage} />}
  </div>;
}
