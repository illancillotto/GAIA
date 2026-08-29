import type { GisTerritorioLayer } from "@/lib/api/territorio";

export function mapScaleDenominator(latitude: number, zoom: number): number {
  const metresPerPixel = 156543.03392 * Math.cos(latitude * Math.PI / 180) / 2 ** zoom;
  return Math.max(1, Math.round(metresPerPixel / 0.00028));
}

export function buildTerritorioPrintHtml({ image, scale, layers }: { image: string; scale: number; layers: GisTerritorioLayer[] }): string {
  const entities: Record<string, string> = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  const escape = (value: string) => value.replace(/[&<>"']/g, (char) => entities[char]);
  const legend = layers.map((layer) => `<li>${escape(layer.title)}</li>`).join("") || "<li>Nessuno strato territoriale attivo</li>";
  const attributions = [...new Set(layers.map((layer) => layer.attribution))].map((value) => `<p>${escape(value)}</p>`).join("");
  const formattedScale = String(scale).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `<!doctype html><html lang="it"><head><meta charset="utf-8"><title>GAIA - Stampa territorio</title><style>@page{size:A4 landscape;margin:12mm}body{font-family:Georgia,serif;color:#173f32}header{display:flex;justify-content:space-between;border-bottom:3px solid #173f32}img{width:100%;max-height:145mm;object-fit:contain}footer{font-size:10px;border-top:1px solid #aaa}</style></head><body><header><h1>Consorzio di Bonifica - GAIA</h1><strong>Scala 1:${formattedScale}</strong></header><main><img src="${escape(image)}" alt="Mappa territoriale"><h2>Legenda</h2><ul>${legend}</ul></main><footer><strong>Attribuzioni</strong>${attributions}</footer></body></html>`;
}
