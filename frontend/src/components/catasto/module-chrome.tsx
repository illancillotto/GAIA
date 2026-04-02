"use client";

import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export function CatastoHero({
  badge,
  title,
  description,
  actions,
  children,
}: {
  badge: ReactNode;
  title: string;
  description: string;
  actions?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <section className="overflow-hidden rounded-[28px] border border-[#d8dfd3] bg-[radial-gradient(circle_at_top_left,_rgba(212,231,220,0.95),_rgba(248,246,238,0.92)_55%,_rgba(255,255,255,0.98)_100%)] p-6 shadow-panel">
      <div className="grid gap-6 xl:grid-cols-[1.15fr,0.85fr]">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-white/80 bg-white/70 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-[#1D4E35]">
            {badge}
          </div>
          <h3 className="mt-4 max-w-2xl text-3xl font-semibold tracking-tight text-[#183325]">{title}</h3>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-gray-600">{description}</p>
        </div>
        {actions ? <div className="grid gap-3 self-start">{actions}</div> : null}
      </div>
      {children ? <div className="mt-6">{children}</div> : null}
    </section>
  );
}

export function CatastoMiniStat({
  eyebrow,
  value,
  description,
  tone = "default",
}: {
  eyebrow: string;
  value: string | number;
  description: string;
  tone?: "default" | "success" | "warning";
}) {
  const toneClasses =
    tone === "success"
      ? "border-emerald-200/70 bg-emerald-50/80"
      : tone === "warning"
        ? "border-amber-200/80 bg-amber-50/80"
        : "border-white/70 bg-white/75";

  return (
    <div className={cn("rounded-2xl border p-4 backdrop-blur", toneClasses)}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">{eyebrow}</p>
      <p className="mt-3 text-2xl font-semibold text-gray-900">{value}</p>
      <p className="mt-2 text-sm leading-6 text-gray-600">{description}</p>
    </div>
  );
}

export function CatastoNoticeCard({
  title,
  description,
  tone = "neutral",
}: {
  title: string;
  description: string;
  tone?: "neutral" | "danger" | "success" | "warning" | "info";
}) {
  const toneClasses =
    tone === "danger"
      ? "border-red-200 bg-red-50 text-red-800"
      : tone === "success"
        ? "border-emerald-200 bg-emerald-50 text-emerald-800"
        : tone === "warning"
          ? "border-amber-200 bg-amber-50 text-amber-900"
          : tone === "info"
            ? "border-sky-200 bg-sky-50 text-sky-800"
            : "border-white/80 bg-white/70 text-gray-600";

  return (
    <div className={cn("rounded-2xl border px-4 py-3", toneClasses)}>
      <p className="text-sm font-semibold">{title}</p>
      <p className="mt-1 text-sm leading-6">{description}</p>
    </div>
  );
}

export function CatastoPanelHeader({
  badge,
  title,
  description,
  actions,
}: {
  badge?: ReactNode;
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <div className="border-b border-[#edf1eb] bg-[linear-gradient(135deg,_rgba(29,78,53,0.06),_rgba(255,255,255,0.92))] px-6 py-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          {badge ? (
            <div className="inline-flex items-center gap-2 rounded-full bg-[#e8f2ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
              {badge}
            </div>
          ) : null}
          <p className="mt-3 text-lg font-semibold text-gray-900">{title}</p>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-600">{description}</p>
        </div>
        {actions ? <div>{actions}</div> : null}
      </div>
    </div>
  );
}
