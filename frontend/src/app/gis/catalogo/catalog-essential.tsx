import type { GisCatalogLayer } from "@/types/gis";

type EssentialCatalogFilters = {
  query: string;
  workspace: string;
};

export type CatalogDestination = {
  href: string;
  label: string;
};

const catalogDestinations: Record<string, CatalogDestination> = {
  catasto: { href: "/catasto/gis", label: "Apri mappa Catasto" },
  rete: { href: "/network", label: "Apri modulo Rete" },
  network: { href: "/network", label: "Apri modulo Rete" },
  riordino: { href: "/riordino", label: "Apri modulo Riordino" },
};

const catalogCategories = [
  { value: "", label: "Tutte" },
  { value: "catasto", label: "Catasto" },
  { value: "rete", label: "Rete" },
  { value: "riordino", label: "Riordino" },
] as const;

function normalizeCatalogText(value: string): string {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

export function layerMatchesCatalogFilters(layer: GisCatalogLayer, filters: EssentialCatalogFilters): boolean {
  const selectedCategory = normalizeCatalogText(filters.workspace);
  const layerCategory = normalizeCatalogText(`${layer.workspace} ${layer.domain_module}`);
  if (selectedCategory && !layerCategory.includes(selectedCategory)) return false;

  const searchTerms = normalizeCatalogText(filters.query).trim().split(/\s+/).filter(Boolean);
  const searchableText = normalizeCatalogText(
    `${layer.title} ${layer.description ?? ""} ${layer.workspace} ${layer.domain_module}`,
  );
  return searchTerms.every((term) => searchableText.includes(term));
}

export function domainWorkspaceDestination(layer: GisCatalogLayer): CatalogDestination | null {
  return catalogDestinations[String(layer.workspace)] ?? catalogDestinations[String(layer.domain_module)] ?? null;
}

export function catalogLayerDestination(layer: GisCatalogLayer): CatalogDestination | null {
  if (layer.source_type === "postgis" && layer.geometry_type) {
    return {
      href: `/gis/catalogo/${layer.id}`,
      label: "Apri mappa",
    };
  }
  return domainWorkspaceDestination(layer);
}

export function CatalogSearchControls({
  filters,
  visibleLayerCount,
  onFilterChange,
}: {
  filters: EssentialCatalogFilters;
  visibleLayerCount: number;
  onFilterChange: (key: keyof EssentialCatalogFilters, value: string) => void;
}) {
  return (
    <>
      <label className="block text-sm font-semibold text-gray-800">
        Cerca per nome o contenuto
        <input
          className="form-control mt-2 text-base"
          type="search"
          value={filters.query}
          onChange={(event) => onFilterChange("query", event.target.value)}
          placeholder="Es. particelle, condotte, pratiche..."
        />
      </label>
      <div className="mt-4" aria-label="Categorie delle mappe">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Scegli un&apos;area</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {catalogCategories.map((category) => (
            <button
              key={category.value || "all"}
              className={
                filters.workspace === category.value
                  ? "rounded-full bg-[#1D4E35] px-4 py-2 text-sm font-semibold text-white shadow-sm"
                  : "rounded-full border border-[#cddbcf] bg-white px-4 py-2 text-sm font-semibold text-[#1D4E35]"
              }
              type="button"
              aria-pressed={filters.workspace === category.value}
              onClick={() => onFilterChange("workspace", category.value)}
            >
              {category.label}
            </button>
          ))}
        </div>
      </div>
      <p className="mt-4 text-right text-sm font-semibold text-[#1D4E35]" role="status" aria-live="polite">
        {visibleLayerCount} {visibleLayerCount === 1 ? "mappa trovata" : "mappe trovate"}
      </p>
    </>
  );
}

export function CatalogLayerSummary({ layer, actionLabels }: { layer: GisCatalogLayer; actionLabels: string[] }) {
  return (
    <>
      {layer.source_type === "domain_registry" ? (
        <p className="mt-3 rounded-xl bg-[#fff8dc] px-3 py-2 text-sm text-[#6d5715]">
          Questo elemento apre un registro operativo: non contiene una geometria da visualizzare sulla mappa.
        </p>
      ) : null}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span className="text-xs font-semibold uppercase tracking-[0.14em] text-[#526a59]">Azioni disponibili:</span>
        {actionLabels.map((label) => (
          <span key={label} className="rounded-full bg-[#f3f7f3] px-3 py-1.5 text-xs font-semibold text-[#1D4E35]">
            {label}
          </span>
        ))}
      </div>
    </>
  );
}
