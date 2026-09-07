"use client";

import type { Dispatch, SetStateAction } from "react";

type Setter<T> = Dispatch<SetStateAction<T>>;
type ToggleProps = { label: string; active: boolean; setActive: Setter<boolean>; tone: "emerald" | "sky" | "indigo" | "teal" | "amber" };
const TONES = {
  emerald: ["border-emerald-200 bg-emerald-50 text-emerald-700", "bg-emerald-500"],
  sky: ["border-sky-200 bg-sky-50 text-sky-700", "bg-sky-400"],
  indigo: ["border-indigo-200 bg-indigo-50 text-indigo-700", "bg-indigo-400"],
  teal: ["border-teal-200 bg-teal-50 text-teal-700", "bg-teal-400"],
  amber: ["border-amber-200 bg-amber-50 text-amber-700", "bg-amber-400"],
};

function LayerToggle({ label, active, setActive, tone }: ToggleProps) {
  return <button type="button" aria-pressed={active} onClick={() => setActive((value) => !value)} className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-all ${active ? TONES[tone][0] : "border-gray-200 bg-white text-gray-500 hover:border-gray-300 hover:text-gray-700"}`}>
    <span className={`h-1.5 w-1.5 rounded-full transition-colors ${active ? TONES[tone][1] : "bg-gray-300"}`} />{label}
  </button>;
}

function LayerOpacity({ label, value, onChange }: { label: string; value: number; onChange: Setter<number> }) {
  return <label className="block text-[11px] text-emerald-900/75">
    <span className="flex items-center justify-between"><span>{label}</span><span className="rounded-full bg-emerald-50 px-2 py-0.5 font-semibold text-emerald-700">{Math.round(value * 100)}%</span></span>
    <input aria-label={label} type="range" min="0" max="1" step="0.05" value={value} onChange={(event) => onChange(Number(event.target.value))} className="mt-2 w-full accent-emerald-600" />
  </label>;
}

const POPOVER = "pointer-events-none absolute left-0 top-full z-10 w-52 translate-y-1 rounded-2xl border border-blue-100 bg-white/95 p-3 pt-5 opacity-0 shadow-xl ring-1 ring-black/5 backdrop-blur transition-all duration-150 group-hover:pointer-events-auto group-hover:translate-y-0 group-hover:opacity-100 group-focus-within:pointer-events-auto group-focus-within:translate-y-0 group-focus-within:opacity-100";

export type GisLayerControlsProps = {
  showDistretti: boolean; setShowDistretti: Setter<boolean>;
  showDistrettiFill: boolean; setShowDistrettiFill: Setter<boolean>;
  showParticelleFill: boolean; setShowParticelleFill: Setter<boolean>;
  showDeliveryPoints: boolean; setShowDeliveryPoints: Setter<boolean>;
  highlightSelected: boolean; setHighlightSelected: Setter<boolean>;
  distrettiOpacity: number; setDistrettiOpacity: Setter<number>;
  particelleOpacity: number; setParticelleOpacity: Setter<number>;
};

export default function GisLayerControls(props: GisLayerControlsProps) {
  return <div className="flex flex-wrap gap-1.5">
    <div className="group relative">
      <LayerToggle label="Distretti" tone="emerald" active={props.showDistretti} setActive={props.setShowDistretti} />
      <div className={POPOVER}>
        <div className="mb-3"><LayerToggle label="Aree colorate" tone="sky" active={props.showDistrettiFill} setActive={props.setShowDistrettiFill} /></div>
        <LayerOpacity label="Opacità aree distretto" value={props.distrettiOpacity} onChange={props.setDistrettiOpacity} />
      </div>
    </div>
    <div className="group relative">
      <LayerToggle label="Riempimento particelle" tone="indigo" active={props.showParticelleFill} setActive={props.setShowParticelleFill} />
      <div className={POPOVER}><LayerOpacity label="Opacità particelle" value={props.particelleOpacity} onChange={props.setParticelleOpacity} /></div>
    </div>
    <LayerToggle label="Punti consegna" tone="teal" active={props.showDeliveryPoints} setActive={props.setShowDeliveryPoints} />
    <LayerToggle label="Evidenzia sel." tone="amber" active={props.highlightSelected} setActive={props.setHighlightSelected} />
  </div>;
}
