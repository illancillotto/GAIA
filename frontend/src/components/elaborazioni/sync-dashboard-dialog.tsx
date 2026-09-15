"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, type KeyboardEvent } from "react";
import { SyncServiceDetails } from "./sync-service-details";
import { SyncSchedules } from "./sync-schedules";
import type { SyncService, SyncServiceState } from "@/lib/sync-dashboard-model";

const WorkspaceContent = dynamic(() => import("./workspace-modal").then((module) => module.NativeWorkspaceRenderer), {
  loading: () => <p role="status" className="p-6">Caricamento monitor...</p>,
});

export type SyncDialogTarget =
  | { kind: "details"; title: string; service: SyncService }
  | { kind: "workspace"; title: string; href: string }
  | { kind: "schedules"; title: string };

function trapFocus(event: KeyboardEvent<HTMLDialogElement>) {
  if (event.key !== "Tab") return;
  const controls = [...event.currentTarget.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), iframe, [tabindex="0"]')]
    .filter((element) => element.getClientRects().length > 0);
  const first = controls[0];
  const last = controls.at(-1);
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last!.focus(); }
  if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first!.focus(); }
}

export function SyncDashboardDialog({ target, states, onClose, onOpen }: {
  target: SyncDialogTarget;
  states: Record<string, SyncServiceState>;
  onClose: () => void;
  onOpen: (href: string, title: string) => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current!;
    const opener = document.activeElement as HTMLElement;
    const overflow = document.body.style.overflow;
    dialog.showModal();
    document.body.style.overflow = "hidden";
    return () => { dialog.close(); document.body.style.overflow = overflow; opener.focus(); };
  }, []);
  return (
    <dialog ref={ref} aria-label={target.title} onKeyDown={trapFocus} onCancel={(event) => { event.preventDefault(); onClose(); }}
      className={`fixed inset-0 m-auto overflow-hidden rounded-[20px] border border-stone-200 bg-[#f4f7f5] p-0 text-stone-800 shadow-2xl backdrop:bg-black/50 backdrop:backdrop-blur-sm ${target.kind === "workspace" ? "h-[calc(100dvh-1rem)] max-h-none w-[calc(100%-1rem)] max-w-none open:flex open:flex-col" : "max-h-[94dvh] w-[calc(100%-1.5rem)] max-w-5xl"}`}>
      <header className="flex shrink-0 items-center justify-between gap-4 border-b border-stone-200 bg-white px-5 py-3">
        <h2 className="text-lg font-semibold text-[#163524]">{target.title}</h2>
        <button type="button" className="btn-secondary shrink-0" onClick={onClose}>Chiudi</button>
      </header>
      <div className={target.kind === "workspace" ? "min-h-0 flex-1 overflow-y-auto p-2 [&>iframe]:h-full [&>iframe]:min-h-0" : "max-h-[calc(94dvh-5rem)] overflow-y-auto p-4 sm:p-6"}>
        {target.kind === "details" ? <>
          <p className="mb-4 text-sm text-stone-600">{target.service.description} Per avviare una sincronizzazione o consultare lo storico, apri il monitor.</p>
          <SyncServiceDetails state={states[target.service.id]} />
          <button type="button" className="btn-primary mt-5" onClick={() => onOpen(target.service.href, target.service.title)}>Apri monitor</button>
        </> : null}
        {target.kind === "schedules" ? <SyncSchedules onOpen={onOpen} /> : null}
        {target.kind === "workspace" ? <WorkspaceContent href={target.href} onNavigate={(href) => onOpen(href, target.title)} /> : null}
      </div>
    </dialog>
  );
}
