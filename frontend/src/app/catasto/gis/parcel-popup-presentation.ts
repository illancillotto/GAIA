import type { ParticellaPopupData } from "@/types/gis";

interface ParcelRoleBadge {
  readonly className: string;
  readonly label: string;
}

const EXACT_ROLE_BADGE: ParcelRoleBadge = {
  className: "bg-emerald-100 text-emerald-700",
  label: "A ruolo",
};
const INFERRED_ROLE_BADGE: ParcelRoleBadge = {
  className: "bg-amber-100 text-amber-700",
  label: "Ruolo inferito",
};
const OUTSIDE_ROLE_BADGE: ParcelRoleBadge = {
  className: "bg-slate-100 text-slate-600",
  label: "Fuori ruolo",
};

export function selectParcelRoleBadge(hasExactRole: boolean | undefined, hasFallbackRole: boolean): ParcelRoleBadge {
  if (hasExactRole) return EXACT_ROLE_BADGE;
  return hasFallbackRole ? INFERRED_ROLE_BADGE : OUTSIDE_ROLE_BADGE;
}

export function hasIncompleteParcelKey(parcel: ParticellaPopupData | null): boolean {
  return Boolean(parcel && (!parcel.codice_catastale || !parcel.foglio || !parcel.particella));
}

export function getParcelPopupTitle(parcel: ParticellaPopupData | null, hasIncompleteKey: boolean): string {
  if (!parcel) return "";
  return parcel.cfm || (hasIncompleteKey ? "Particella GIS incompleta" : `${parcel.foglio} / ${parcel.particella}`);
}

export function getParcelPopupLocation(parcel: ParticellaPopupData | null, hasIncompleteKey: boolean): string {
  if (hasIncompleteKey) return "Riferimenti catastali non disponibili per questo poligono GIS.";
  return `${parcel?.nome_comune ?? parcel?.codice_catastale ?? "Comune ND"} · Fg. ${parcel?.foglio ?? "-"} · Part. ${parcel?.particella ?? "-"}${parcel?.subalterno ? ` · Sub. ${parcel.subalterno}` : ""}`;
}

export function getParcelPopupRecordState(parcel: ParticellaPopupData | null): string {
  if (!parcel) return "-";
  if (parcel.suppressed) return "Soppresso";
  return parcel.is_current ? "Corrente" : "Storico";
}
