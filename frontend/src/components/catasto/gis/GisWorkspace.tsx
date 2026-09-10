"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import type { GisBasemap } from "@/types/gis";
import styles from "./gis-workspace.module.css";

const BASEMAP_OPTIONS: Array<{ id: GisBasemap; label: string; icon: string; requiresGoogleKey?: boolean }> = [
  { id: "osm", label: "Vista classica", icon: "map" },
  { id: "satellite", label: "Vista satellitare", icon: "satellite_alt" },
  { id: "google_satellite", label: "Google Earth", icon: "public", requiresGoogleKey: true },
];

export function GisBasemapControl({ basemap, onBasemapChange, googleTilesConfigured }: {
  basemap: GisBasemap;
  onBasemapChange: (basemap: GisBasemap) => void;
  googleTilesConfigured: boolean;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative flex items-center">
      <button type="button" aria-label="Sfondo mappa" aria-expanded={open} onClick={() => setOpen((value) => !value)} className={`inline-flex h-9 items-center gap-1.5 rounded-lg border px-2.5 text-xs font-semibold transition ${open ? "border-emerald-300 bg-emerald-100 text-emerald-950" : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"}`} title="Sfondo mappa">
        <span aria-hidden="true" className="material-symbols-outlined text-[18px]">layers</span>
        <span className="hidden 2xl:inline">Sfondo</span>
      </button>
      {open ? (
        <div className="fixed left-3 right-3 top-[calc(var(--gis-top,52px)+4.5rem)] z-50 grid grid-cols-2 gap-2 rounded-2xl border border-slate-200 bg-white/95 p-2 shadow-2xl backdrop-blur sm:absolute sm:left-auto sm:right-0 sm:top-11 sm:w-52 sm:grid-cols-1">
          {BASEMAP_OPTIONS.filter((option) => !option.requiresGoogleKey || googleTilesConfigured).map((option) => (
            <button key={option.id} type="button" aria-pressed={basemap === option.id} onClick={() => { onBasemapChange(option.id); setOpen(false); }} className={`inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-left text-xs font-semibold transition ${basemap === option.id ? "border-emerald-300 bg-emerald-50 text-emerald-900" : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"}`}>
              <span aria-hidden="true" className="material-symbols-outlined text-[18px]">{option.icon}</span>
              {option.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export default function GisWorkspace({ children, consoleOpen, onConsoleChange, onExpand, basemap, onBasemapChange, googleTilesConfigured }: {
  children: ReactNode;
  consoleOpen: boolean;
  onConsoleChange: (open: boolean) => void;
  onExpand: () => void;
  basemap: GisBasemap;
  onBasemapChange: (basemap: GisBasemap) => void;
  googleTilesConfigured: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = ref.current!;
    const resize = () => {
      const bounds = element.getBoundingClientRect();
      const top = bounds.top + window.scrollY;
      element.style.setProperty("--gis-top", `${top}px`);
      element.style.setProperty("--gis-left", `${bounds.left}px`);
    };
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(element.parentElement!);
    window.addEventListener("resize", resize);
    return () => { observer.disconnect(); window.removeEventListener("resize", resize); };
  }, []);

  return (
    <div ref={ref} className={`${styles.workspace} relative -mx-4 -mb-4 -mt-4 flex min-h-0 flex-col overflow-hidden bg-[#101b17] md:-mx-7 md:-mb-6 md:-mt-6`} data-console-open={consoleOpen}>
      <div className="flex shrink-0 items-center justify-between gap-2 border-y border-slate-200 bg-white px-3 py-2">
        <h2 className="text-xs font-bold tracking-widest text-emerald-900">GAIA GIS</h2>
        <div className="flex min-w-0 items-center gap-2">
          <div id="gis-toolbar-tools" className="flex shrink-0 items-center gap-1" />
          <GisBasemapControl {...{ basemap, onBasemapChange, googleTilesConfigured }} />
          <button type="button" aria-label="Vista estesa" onClick={onExpand} className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-slate-950 px-2.5 text-xs font-semibold text-white sm:px-3">
            <span aria-hidden="true" className="material-symbols-outlined text-[18px]">fullscreen</span>
            <span className="hidden sm:inline">Vista estesa</span>
          </button>
          <button type="button" aria-label={consoleOpen ? "Nascondi Console GIS" : "Apri Console GIS"} aria-expanded={consoleOpen} aria-controls="gis-console" onClick={() => onConsoleChange(!consoleOpen)} className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50 px-2.5 text-xs font-semibold text-emerald-900 sm:px-3">
            <span aria-hidden="true" className="material-symbols-outlined text-[18px]">tune</span>
            <span className="hidden sm:inline">{consoleOpen ? "Nascondi Console GIS" : "Apri Console GIS"}</span>
          </button>
        </div>
      </div>
      {children}
    </div>
  );
}
