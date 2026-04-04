"use client";

import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export function CatastoHero({
  badge,
  title,
  description,
  actions,
  children,
  compact = false,
}: {
  badge: ReactNode;
  title: string;
  description: string;
  actions?: ReactNode;
  children?: ReactNode;
  compact?: boolean;
}) {
  return (
    <section className={cn("overflow-hidden rounded-[28px] border border-[#d8dfd3] bg-[radial-gradient(circle_at_top_left,_rgba(212,231,220,0.95),_rgba(248,246,238,0.92)_55%,_rgba(255,255,255,0.98)_100%)] shadow-panel", compact ? "p-5" : "p-6")}>
      <div className={cn("grid xl:grid-cols-[1.15fr,0.85fr]", compact ? "gap-4" : "gap-6")}>
        <div>
          <div className={cn("inline-flex items-center gap-2 rounded-full border border-white/80 bg-white/70 font-semibold uppercase tracking-[0.22em] text-[#1D4E35]", compact ? "px-3 py-1 text-[10px]" : "px-3 py-1 text-[11px]")}>
            {badge}
          </div>
          <h3 className={cn("max-w-2xl font-semibold tracking-tight text-[#183325]", compact ? "mt-3 text-[2rem] leading-tight" : "mt-4 text-3xl")}>{title}</h3>
          <p className={cn("max-w-2xl text-sm text-gray-600", compact ? "mt-3 leading-6" : "mt-4 leading-7")}>{description}</p>
        </div>
        {actions ? <div className={cn("grid self-start", compact ? "gap-2" : "gap-3")}>{actions}</div> : null}
      </div>
      {children ? <div className={cn(compact ? "mt-4" : "mt-6")}>{children}</div> : null}
    </section>
  );
}

export function CatastoMiniStat({
  eyebrow,
  value,
  description,
  tone = "default",
  compact = false,
}: {
  eyebrow: string;
  value: string | number;
  description: string;
  tone?: "default" | "success" | "warning";
  compact?: boolean;
}) {
  const toneClasses =
    tone === "success"
      ? "border-emerald-200/70 bg-emerald-50/80"
      : tone === "warning"
        ? "border-amber-200/80 bg-amber-50/80"
        : "border-white/70 bg-white/75";

  return (
    <div className={cn("rounded-2xl border backdrop-blur", toneClasses, compact ? "p-3" : "p-4")}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">{eyebrow}</p>
      <p className={cn("font-semibold text-gray-900", compact ? "mt-2 text-xl" : "mt-3 text-2xl")}>{value}</p>
      <p className={cn("text-sm text-gray-600", compact ? "mt-1.5 leading-5" : "mt-2 leading-6")}>{description}</p>
    </div>
  );
}

export function CatastoNoticeCard({
  title,
  description,
  tone = "neutral",
  compact = false,
}: {
  title: string;
  description: string;
  tone?: "neutral" | "danger" | "success" | "warning" | "info";
  compact?: boolean;
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
    <div className={cn("rounded-2xl border", toneClasses, compact ? "px-4 py-2.5" : "px-4 py-3")}>
      <p className="text-sm font-semibold">{title}</p>
      <p className={cn("text-sm", compact ? "mt-1 leading-5" : "mt-1 leading-6")}>{description}</p>
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
