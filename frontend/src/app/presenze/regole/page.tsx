"use client";

import { useEffect, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { getGatePresenzeRules } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { GatePresenzeRuleItem, GatePresenzeRulesResponse } from "@/types/api";

const severityLabels: Record<GatePresenzeRuleItem["severity"], string> = {
  info: "Informativa",
  warning: "Da verificare",
  blocking: "Bloccante",
};

const severityClasses: Record<GatePresenzeRuleItem["severity"], string> = {
  info: "border-sky-200 bg-sky-50 text-sky-800",
  warning: "border-amber-200 bg-amber-50 text-amber-900",
  blocking: "border-red-200 bg-red-50 text-red-900",
};

export default function PresenzeRegolePage() {
  const [rules, setRules] = useState<GatePresenzeRulesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    getGatePresenzeRules(token)
      .then(setRules)
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Errore caricamento regole Presenze"));
  }, []);

  return (
    <ProtectedPage
      title="Regole Presenze"
      description="Regole operative condivise tra GAIA e GATE Console Mobile."
      breadcrumb="Regole"
      requiredModule="presenze"
    >
      <div className="space-y-6">
        <section className="rounded-3xl border border-slate-200 bg-gradient-to-br from-slate-950 via-slate-900 to-emerald-950 p-6 text-white shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-emerald-200">GAIA / GATE</p>
          <h2 className="mt-3 text-3xl font-semibold">Regole usate dal sistema</h2>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-200">
            {rules?.summary ?? "Caricamento regole operative condivise tra GAIA e GATE."}
          </p>
          <div className="mt-5 flex flex-wrap gap-3 text-xs font-semibold">
            <span className="rounded-full bg-white/10 px-3 py-1">Rules: {rules?.rules_version ?? "..."}</span>
            <span className="rounded-full bg-white/10 px-3 py-1">Export: {rules?.export_rules_version ?? "..."}</span>
          </div>
        </section>

        {error ? <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div> : null}

        <div className="grid gap-5 lg:grid-cols-3">
          {(rules?.sections ?? []).map((section) => (
            <section key={section.code} className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
              <h3 className="text-lg font-semibold text-slate-950">{section.title}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">{section.description}</p>
              <div className="mt-5 space-y-4">
                {section.rules.map((rule) => (
                  <article key={rule.code} className={`rounded-2xl border p-4 ${severityClasses[rule.severity]}`}>
                    <div className="flex items-start justify-between gap-3">
                      <h4 className="font-semibold">{rule.title}</h4>
                      <span className="shrink-0 rounded-full bg-white/70 px-2 py-1 text-[11px] font-bold uppercase tracking-wide">
                        {severityLabels[rule.severity]}
                      </span>
                    </div>
                    <p className="mt-3 text-sm leading-6">{rule.description}</p>
                    <p className="mt-3 text-xs font-semibold uppercase tracking-wide opacity-75">Azione operatore</p>
                    <p className="mt-1 text-sm leading-6">{rule.operator_action}</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {rule.applies_to.map((item) => (
                        <span key={item} className="rounded-full bg-white/70 px-2 py-1 text-[11px] font-semibold">
                          {item}
                        </span>
                      ))}
                    </div>
                  </article>
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>
    </ProtectedPage>
  );
}
