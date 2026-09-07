"use client";

import { useEffect, useRef, type ReactNode } from "react";
import styles from "./gis-workspace.module.css";

export default function GisWorkspace({ children, consoleOpen, onConsoleChange, onExpand }: {
  children: ReactNode;
  consoleOpen: boolean;
  onConsoleChange: (open: boolean) => void;
  onExpand: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = ref.current!;
    const resize = () => {
      const top = element.getBoundingClientRect().top + window.scrollY;
      element.style.setProperty("--gis-top", `${top}px`);
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
        <div className="flex gap-2">
          <button type="button" onClick={onExpand} className="rounded-lg bg-slate-950 px-3 py-2 text-xs font-semibold text-white">Vista estesa</button>
          <button type="button" aria-expanded={consoleOpen} aria-controls="gis-console" onClick={() => onConsoleChange(!consoleOpen)} className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-900">
            {consoleOpen ? "Nascondi Console GIS" : "Apri Console GIS"}
          </button>
        </div>
      </div>
      {children}
    </div>
  );
}
