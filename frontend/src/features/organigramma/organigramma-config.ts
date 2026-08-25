import type { OrgPositionCode, OrgUnitType } from "@/types/api";

export const TYPE_META: Record<OrgUnitType, { label: string; chip: string; dot: string }> = {
  direzione: { label: "Direzione", chip: "bg-[#D3EAD4] text-[#163d29] border-[#bcd9bf]", dot: "#1D4E35" },
  distretto: { label: "Distretto", chip: "bg-[#e0f3ec] text-[#0f6a4e] border-[#bfe5d6]", dot: "#1D9E75" },
  settore: { label: "Settore", chip: "bg-[#e3f0f5] text-[#215a72] border-[#c4e0ea]", dot: "#3b82a6" },
  reparto: { label: "Reparto", chip: "bg-[#f9eadf] text-[#8a4828] border-[#edcdb8]", dot: "#c66b3d" },
  squadra: { label: "Squadra", chip: "bg-[#efeaf7] text-[#574a78] border-[#ddd2ee]", dot: "#8a7bb8" },
};

export const TYPE_FILTERS: { value: OrgUnitType | "all"; label: string }[] = [
  { value: "all", label: "Tutti" },
  ...Object.entries(TYPE_META).map(([value, meta]) => ({ value: value as OrgUnitType, label: meta.label })),
];

export function defaultLeadTitle(tipo: OrgUnitType): string {
  return {
    direzione: "Dirigente",
    distretto: "Responsabile distretto",
    settore: "Capo settore",
    reparto: "Capo reparto",
    squadra: "Capo operai",
  }[tipo];
}

export function defaultLeadPositionCode(tipo: OrgUnitType): OrgPositionCode | null {
  return {
    direzione: "dirigente",
    distretto: null,
    settore: "capo_settore",
    reparto: "capo_reparto",
    squadra: "capo_operai",
  }[tipo] as OrgPositionCode | null;
}
