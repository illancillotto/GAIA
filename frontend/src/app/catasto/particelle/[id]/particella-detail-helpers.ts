import type { CatParticellaConsorzio, CatParticellaDetail, CatUtenzaIrrigua } from "@/types/catasto";

export function formatHaFromMq(value: string | number): string {
  const mq = typeof value === "number" ? value : Number(value);
  const ha = (Number.isFinite(mq) ? mq : 0) / 10_000;
  return new Intl.NumberFormat("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(ha);
}

export function renderResolutionLabel(mode: string | null | undefined): string {
  switch (mode) {
    case "swapped_arborea_terralba":
      return "Comune corretto da GAIA (Arborea/Terralba)";
    case "source_match":
      return "Comune sorgente confermato";
    case "resolved_from_particella":
      return "Comune risolto dalla particella GAIA";
    case "source_only":
      return "Solo sorgente Capacitas";
    default:
      return mode ?? "—";
  }
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "Mai";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("it-IT");
}

export function formatIndice(value: string | number | null | undefined): string {
  if (value == null) return "—";
  const parsed = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(parsed)) return "—";
  return parsed.toLocaleString("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function formatHectares(value: string | number | null | undefined): string {
  if (value == null) return "—";
  const parsed = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(parsed)) return "—";
  return `${parsed.toLocaleString("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 4 })} ha`;
}

function padCapacitasCode(value: string | number | null | undefined, length: number): string | null {
  if (value == null) return null;
  const normalized = String(value).trim();
  if (!normalized) return null;
  return normalized.padStart(length, "0");
}

export function normalizeIdentifier(value: string | null | undefined): string | null {
  if (!value) return null;
  const normalized = value.replace(/\s+/g, "").trim().toUpperCase();
  return normalized || null;
}

type Occupancy = CatParticellaConsorzio["units"][number]["occupancies"][number];
type ConsorzioUnit = CatParticellaConsorzio["units"][number];

function unitOccupancies(unit: ConsorzioUnit): Occupancy[] {
  return unit.occupancies;
}

function isCertificateOccupancy(occupancy: Occupancy, utenzaId: string): boolean {
  return occupancy.utenza_id === utenzaId && Boolean(occupancy.com && occupancy.pvc && occupancy.fra);
}

function compareCertificateOccupancies(left: Occupancy, right: Occupancy): number {
  if (left.is_current !== right.is_current) return left.is_current ? -1 : 1;
  const validFromComparison = (right.valid_from ?? "").localeCompare(left.valid_from ?? "");
  if (validFromComparison !== 0) return validFromComparison;
  return (right.updated_at ?? "").localeCompare(left.updated_at ?? "");
}

export function resolveUtenzaCertContext(
  consorzio: CatParticellaConsorzio | null,
  utenza: CatUtenzaIrrigua,
): { com?: string; pvc?: string; fra?: string; ccs?: string } {
  if (!consorzio) return {};

  const best = consorzio.units
    .flatMap(unitOccupancies)
    .filter((occupancy) => isCertificateOccupancy(occupancy, utenza.id))
    .sort(compareCertificateOccupancies)[0];
  if (!best) return {};
  return {
    com: best.com as string,
    pvc: best.pvc as string,
    fra: best.fra as string,
    ccs: best.ccs ?? undefined,
  };
}

export function formatUtenzaPartita(consorzio: CatParticellaConsorzio | null, utenza: CatUtenzaIrrigua): string | null {
  const cco = padCapacitasCode(utenza.cco, 9);
  if (!cco) return null;
  const context = resolveUtenzaCertContext(consorzio, utenza);
  const fra = padCapacitasCode(context.fra ?? utenza.cod_frazione, 2);
  const ccs = padCapacitasCode(context.ccs ?? "00000", 5);
  if (!fra || !ccs) return cco;
  return `${cco}/${fra}/${ccs}`;
}

export function getUtenzaSubjectLabel(utenza: CatUtenzaIrrigua): string | null {
  return utenza.subject_display_name?.trim() || utenza.denominazione?.trim() || null;
}

export function particellaReference(item: CatParticellaDetail | null): string {
  if (!item) return "Particella";
  return `Fg.${item.foglio} Part.${item.particella}${item.subalterno ? ` Sub.${item.subalterno}` : ""}`;
}
