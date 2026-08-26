"use client";

import { useEffect, useRef, useState } from "react";

import { listGisLayerFeatures } from "@/lib/api/gis";
import type {
  GisCatalogLayer,
  GisCatalogLayerFeature,
} from "@/types/gis";

type FeatureSelectorProps = {
  token: string;
  layer: GisCatalogLayer;
  selectedId: string;
  initialFeatureId?: string;
  allowWholeLayer?: boolean;
  disabled?: boolean;
  onSelect: (feature: GisCatalogLayerFeature | null) => void;
};

function featureLoadErrorMessage(error: unknown) {
  return error instanceof Error
    ? error.message
    : "Elementi della mappa non disponibili";
}

function useFeatureSelectorState({
  token,
  layer,
  initialFeatureId,
  onSelect,
}: FeatureSelectorProps) {
  const [query, setQuery] = useState(initialFeatureId ?? "");
  const [features, setFeatures] = useState<GisCatalogLayerFeature[]>([]);
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  async function loadFeatures(nextOffset: number, search = query) {
    setBusy(true);
    setError(null);
    try {
      const response = await listGisLayerFeatures(
        token,
        layer.id,
        search,
        20,
        nextOffset,
      );
      setFeatures(response.items);
      setOffset(response.offset);
      setTotal(response.total);
    } catch (loadError) {
      setFeatures([]);
      setTotal(0);
      setError(featureLoadErrorMessage(loadError));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    let ignore = false;
    setBusy(true);
    setError(null);
    void listGisLayerFeatures(token, layer.id, initialFeatureId, 20, 0)
      .then((response) => {
        if (ignore) return;
        setFeatures(response.items);
        setOffset(response.offset);
        setTotal(response.total);
        const initialFeature = response.items.find(
          function matchesInitialFeature(feature) {
            return feature.feature_id === initialFeatureId;
          },
        );
        if (initialFeature) onSelectRef.current(initialFeature);
      })
      .catch((loadError: unknown) => {
        if (ignore) return;
        setFeatures([]);
        setTotal(0);
        setError(featureLoadErrorMessage(loadError));
      })
      .finally(() => {
        if (!ignore) setBusy(false);
      });
    return () => {
      ignore = true;
    };
  }, [initialFeatureId, layer.id, token]);

  return {
    busy,
    error,
    features,
    loadFeatures,
    offset,
    query,
    setQuery,
    total,
  };
}

function FeatureSearch({
  query,
  busy,
  disabled,
  onQueryChange,
  onSearch,
}: {
  query: string;
  busy: boolean;
  disabled?: boolean;
  onQueryChange: (query: string) => void;
  onSearch: () => void;
}) {
  return (
    <label className="block text-sm font-semibold text-gray-800">
      Cerca per codice o descrizione
      <div className="mt-2 flex flex-col gap-2 sm:flex-row">
        <input
          className="form-control text-base"
          type="search"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Es. condotta principale"
          disabled={disabled}
        />
        <button
          className="btn-secondary shrink-0"
          type="button"
          disabled={busy || disabled}
          onClick={onSearch}
        >
          {busy ? "Ricerca..." : "Cerca"}
        </button>
      </div>
    </label>
  );
}

function FeatureSelect({
  features,
  selectedId,
  allowWholeLayer,
  disabled,
  onSelect,
}: Pick<
  FeatureSelectorProps,
  "selectedId" | "allowWholeLayer" | "disabled" | "onSelect"
> & {
  features: GisCatalogLayerFeature[];
}) {
  return (
    <label className="mt-3 block text-sm font-semibold text-gray-800">
      Elemento della mappa
      <select
        className="form-control mt-2 text-base"
        value={selectedId}
        disabled={disabled}
        onChange={(event) =>
          onSelect(
            features.find(
              (feature) => feature.feature_id === event.target.value,
            ) ?? null,
          )
        }
      >
        <option value="">
          {allowWholeLayer
            ? "Nota generale sulla mappa"
            : "Seleziona un elemento"}
        </option>
        {features.map((feature) => (
          <option key={feature.feature_id} value={feature.feature_id}>
            {feature.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function FeatureLoadFeedback({
  error,
  busy,
  total,
}: {
  error: string | null;
  busy: boolean;
  total: number;
}) {
  if (error) {
    return (
      <p className="mt-2 text-sm font-medium text-red-700" role="alert">
        {error}
      </p>
    );
  }
  if (busy) return null;
  return (
    <p className="mt-2 text-xs text-gray-500" role="status">
      {total} elementi trovati
    </p>
  );
}

function FeaturePagination({
  offset,
  total,
  busy,
  onPage,
}: {
  offset: number;
  total: number;
  busy: boolean;
  onPage: (offset: number) => void;
}) {
  if (total <= 20) return null;
  return (
    <div className="mt-3 flex items-center justify-between gap-2">
      <button
        className="btn-secondary"
        type="button"
        disabled={offset === 0 || busy}
        onClick={() => onPage(Math.max(0, offset - 20))}
      >
        Precedenti
      </button>
      <span className="text-xs text-gray-500">
        Da {offset + 1} a {Math.min(offset + 20, total)}
      </span>
      <button
        className="btn-secondary"
        type="button"
        disabled={offset + 20 >= total || busy}
        onClick={() => onPage(offset + 20)}
      >
        Successivi
      </button>
    </div>
  );
}

export function FeatureSelector(props: FeatureSelectorProps) {
  const { selectedId, allowWholeLayer, disabled, onSelect } = props;
  const state = useFeatureSelectorState(props);

  return (
    <div className="rounded-2xl border border-[#dce8de] bg-[#f7faf7] p-4">
      <FeatureSearch
        query={state.query}
        busy={state.busy}
        disabled={disabled}
        onQueryChange={state.setQuery}
        onSearch={() => void state.loadFeatures(0)}
      />
      <FeatureSelect
        features={state.features}
        selectedId={selectedId}
        allowWholeLayer={allowWholeLayer}
        disabled={disabled}
        onSelect={onSelect}
      />
      <FeatureLoadFeedback
        error={state.error}
        busy={state.busy}
        total={state.total}
      />
      <FeaturePagination
        offset={state.offset}
        total={state.total}
        busy={state.busy}
        onPage={(offset) => void state.loadFeatures(offset)}
      />
    </div>
  );
}
