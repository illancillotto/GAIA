"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { formatDate, formatEuro } from "@/components/elaborazioni/step/step-format";
import { listStepLinksForAvviso } from "@/lib/api/step";
import type { StepAvvisoLink } from "@/types/step";

type CardState = { status: "loading" } | { status: "error" } | { status: "ready"; links: StepAvvisoLink[] };

const STATE_MESSAGES: Record<"loading" | "error" | "empty", string> = {
  loading: "Caricamento dati STEP...",
  error: "Dati STEP non disponibili.",
  empty: "Nessun documento STEP collegato.",
};

function StepLinkItem({ item }: { item: StepAvvisoLink }) {
  return (
    <li className="rounded-2xl border border-[#e3e9e0] bg-[#fbfcfb] p-4 text-sm">
      <p className="font-semibold text-gray-900">
        Documento {item.num_doc} · {item.denominazione ?? item.codice_fiscale}
      </p>
      <p className="mt-1 text-xs leading-5 text-gray-500">
        Notifica {formatDate(item.data_notifica)} · Carico {formatEuro(item.link.imp_carico)} · Pagato{" "}
        {formatEuro(item.link.imp_carico_pagato)} · Discaricato {formatEuro(item.link.imp_discaricato)}
      </p>
      <Link className="mt-2 inline-block text-xs font-semibold text-[#1D4E35] hover:underline" href="/elaborazioni/step">
        Apri archivio STEP
      </Link>
    </li>
  );
}

function StepLinksBody({ state }: { state: CardState }) {
  if (state.status !== "ready") return <p className="text-sm text-gray-500">{STATE_MESSAGES[state.status]}</p>;
  if (state.links.length === 0) return <p className="text-sm text-gray-500">{STATE_MESSAGES.empty}</p>;
  return (
    <ul className="space-y-2">
      {state.links.map((item) => (
        <StepLinkItem key={item.link.id} item={item} />
      ))}
    </ul>
  );
}

export function StepAvvisoCard({ token, avvisoId }: { token: string | null; avvisoId: string }) {
  const [state, setState] = useState<CardState>({ status: "loading" });

  useEffect(() => {
    if (!token) return;
    let active = true;
    listStepLinksForAvviso(token, avvisoId)
      .then((links) => active && setState({ status: "ready", links }))
      .catch(() => active && setState({ status: "error" }));
    return () => {
      active = false;
    };
  }, [token, avvisoId]);

  return (
    <section className="rounded-[28px] border border-[#d8dfd3] bg-white p-6 shadow-panel" aria-label="Riscossione STEP">
      <p className="text-lg font-semibold text-gray-900">Riscossione coattiva STEP</p>
      <p className="mt-1 text-sm leading-6 text-gray-600">
        Documenti STEP collegati a questo avviso tramite il codice CNC. Lo stato STEP del registro avvisi viene
        aggiornato automaticamente dai sync.
      </p>
      <div className="mt-4">
        <StepLinksBody state={state} />
      </div>
    </section>
  );
}
