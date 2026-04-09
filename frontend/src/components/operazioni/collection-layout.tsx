"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export function OperazioniCollectionHero({
  eyebrow,
  title,
  description,
  icon,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  icon: ReactNode;
  children?: ReactNode;
}) {
  return (
    <section className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-[linear-gradient(135deg,_rgba(236,244,238,0.96),_rgba(249,247,240,0.96)_52%,_rgba(255,255,255,0.98)_100%)] shadow-panel">
      <div className="grid gap-6 px-6 py-6 lg:grid-cols-[1.15fr,0.85fr]">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-white/80 bg-white/75 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-[#1D4E35]">
            {icon}
            {eyebrow}
          </div>
          <h3 className="mt-4 max-w-3xl text-[2rem] font-semibold leading-tight tracking-tight text-[#183325]">{title}</h3>
          <p className="mt-3 max-w-3xl text-sm leading-7 text-gray-600">{description}</p>
        </div>
        {children ? <div className="grid content-start gap-3">{children}</div> : null}
      </div>
    </section>
  );
}

export function OperazioniHeroNotice({
  title,
  description,
  tone = "default",
}: {
  title: string;
  description: string;
  tone?: "default" | "danger";
}) {
  return (
    <div
      className={cn(
        "rounded-2xl border px-4 py-3",
        tone === "danger" ? "border-red-200 bg-red-50 text-red-800" : "border-white/80 bg-white/75 text-gray-700",
      )}
    >
      <p className="text-sm font-semibold">{title}</p>
      <p className="mt-1 text-sm leading-6">{description}</p>
    </div>
  );
}

export function OperazioniMetricStrip({ children }: { children: ReactNode }) {
  return <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">{children}</div>;
}

export function OperazioniToolbar({
  search,
  onSearchChange,
  searchPlaceholder,
  filterValue,
  onFilterChange,
  filterOptions,
}: {
  search?: string;
  onSearchChange?: (value: string) => void;
  searchPlaceholder?: string;
  filterValue?: string;
  onFilterChange?: (value: string) => void;
  filterOptions?: { value: string; label: string }[];
}) {
  if (!onSearchChange && !onFilterChange) {
    return null;
  }

  return (
    <div className="grid gap-3 rounded-[24px] border border-[#e4e8e2] bg-[#fcfcf9] p-3 md:grid-cols-[minmax(0,1fr),240px]">
      {onSearchChange ? (
        <label className="block">
          <span className="label-caption">Ricerca rapida</span>
          <input
            className="form-control mt-2"
            value={search ?? ""}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder={searchPlaceholder ?? "Cerca"}
          />
        </label>
      ) : (
        <div />
      )}
      {onFilterChange ? (
        <label className="block">
          <span className="label-caption">Filtro stato</span>
          <select
            className="form-control mt-2"
            value={filterValue ?? ""}
            onChange={(event) => onFilterChange(event.target.value)}
          >
            {(filterOptions ?? []).map((option) => (
              <option key={option.value || "__all"} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      ) : null}
    </div>
  );
}

export function OperazioniCollectionPanel({
  title,
  description,
  count,
  children,
}: {
  title: string;
  description: string;
  count: number;
  children: ReactNode;
}) {
  return (
    <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
      <div className="border-b border-[#edf1eb] bg-[linear-gradient(135deg,_rgba(29,78,53,0.05),_rgba(255,255,255,0.92))] px-6 py-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#5f6d61]">Vista elenco</p>
            <h4 className="mt-2 text-lg font-semibold text-gray-900">{title}</h4>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-600">{description}</p>
          </div>
          <span className="rounded-full border border-[#d5e2d8] bg-[#edf5f0] px-3 py-1 text-xs font-semibold text-[#1D4E35]">{count}</span>
        </div>
      </div>
      <div className="p-5">{children}</div>
    </article>
  );
}

export function OperazioniList({
  children,
}: {
  children: ReactNode;
}) {
  return <div className="space-y-3">{children}</div>;
}

export function OperazioniListLink({
  href,
  title,
  meta,
  status,
  statusTone,
  aside,
  onClick,
}: {
  href?: string;
  title: string;
  meta: string;
  status: string;
  statusTone: string;
  aside?: ReactNode;
  onClick?: () => void;
}) {
  const className =
    "group grid w-full gap-3 rounded-[24px] border border-[#e6ebe5] bg-[linear-gradient(180deg,_#ffffff,_#fbfcfa)] px-4 py-4 text-left transition hover:-translate-y-0.5 hover:border-[#c9d6cd] hover:shadow-sm md:grid-cols-[minmax(0,1fr),auto]";
  const content = (
    <>
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-gray-900">{title}</p>
        <p className="mt-1 truncate text-xs leading-5 text-gray-500">{meta}</p>
      </div>
      <div className="flex items-center gap-3 justify-self-start md:justify-self-end">
        {aside}
        <span className={cn("rounded-full px-2.5 py-1 text-xs font-semibold", statusTone)}>{status}</span>
        <span className="text-sm text-gray-300 transition group-hover:text-[#1D4E35]">→</span>
      </div>
    </>
  );

  if (href) {
    return (
      <Link href={href} className={className}>
        {content}
      </Link>
    );
  }

  if (!onClick) {
    return <div className={className}>{content}</div>;
  }

  return (
    <button type="button" className={className} onClick={onClick}>
      {content}
    </button>
  );
}

export function OperazioniBreadcrumb({
  items,
}: {
  items: { label: string; href?: string }[];
}) {
  return (
    <nav className="flex flex-wrap items-center gap-1 text-sm text-gray-500">
      {items.map((item, index) => (
        <div key={`${item.label}-${index}`} className="flex items-center gap-1">
          {item.href ? <Link href={item.href} className="hover:text-[#1D4E35]">{item.label}</Link> : <span className="text-gray-800">{item.label}</span>}
          {index < items.length - 1 ? <span className="text-gray-300">/</span> : null}
        </div>
      ))}
    </nav>
  );
}

export function OperazioniDetailHero({
  eyebrow,
  title,
  description,
  status,
  statusTone,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  status: string;
  statusTone: string;
  children?: ReactNode;
}) {
  return (
    <section className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-[linear-gradient(135deg,_rgba(236,244,238,0.96),_rgba(249,247,240,0.96)_52%,_rgba(255,255,255,0.98)_100%)] shadow-panel">
      <div className="grid gap-5 px-6 py-6 lg:grid-cols-[1.1fr,0.9fr]">
        <div>
          <p className="inline-flex rounded-full border border-white/80 bg-white/75 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-[#1D4E35]">
            {eyebrow}
          </p>
          <h3 className="mt-4 text-[2rem] font-semibold leading-tight tracking-tight text-[#183325]">{title}</h3>
          <p className="mt-3 max-w-3xl text-sm leading-7 text-gray-600">{description}</p>
        </div>
        <div className="grid content-start gap-3">
          <div className="rounded-2xl border border-white/80 bg-white/75 px-4 py-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">Stato corrente</p>
            <div className="mt-3">
              <span className={cn("inline-flex rounded-full px-2.5 py-1 text-xs font-semibold", statusTone)}>{status}</span>
            </div>
          </div>
          {children}
        </div>
      </div>
    </section>
  );
}

export function OperazioniInfoGrid({
  items,
}: {
  items: { label: string; value: ReactNode }[];
}) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {items.map((item) => (
        <div key={item.label} className="rounded-2xl border border-[#e6ebe5] bg-[#fbfcfa] px-4 py-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">{item.label}</p>
          <div className="mt-2 text-sm font-medium text-gray-900">{item.value}</div>
        </div>
      ))}
    </div>
  );
}
