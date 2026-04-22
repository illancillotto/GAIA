"use client";

import { useMemo, useState } from "react";

export type AnagraficaSingleSearchValues = {
  comune: string;
  foglio: string;
  particella: string;
};

export function AnagraficaSingleSearchForm({
  disabled,
  initialValues,
  onSubmit,
}: {
  disabled: boolean;
  initialValues: AnagraficaSingleSearchValues;
  onSubmit: (values: AnagraficaSingleSearchValues) => void;
}) {
  const [values, setValues] = useState<AnagraficaSingleSearchValues>(initialValues);
  const validationError = useMemo(() => {
    if (!values.foglio.trim()) return "Inserisci il foglio.";
    if (!values.particella.trim()) return "Inserisci la particella.";
    return null;
  }, [values.foglio, values.particella]);

  return (
    <form
      className="grid gap-3 md:grid-cols-4"
      onSubmit={(e) => {
        e.preventDefault();
        if (validationError) return;
        onSubmit({
          comune: values.comune.trim(),
          foglio: values.foglio.trim(),
          particella: values.particella.trim(),
        });
      }}
    >
      <label className="text-sm font-medium text-gray-700">
        Comune (codice Capacitas o nome)
        <input
          className="form-control mt-1"
          placeholder="Es. 165 oppure Oristano"
          value={values.comune}
          onChange={(e) => setValues((c) => ({ ...c, comune: e.target.value }))}
          disabled={disabled}
        />
      </label>
      <label className="text-sm font-medium text-gray-700">
        Foglio *
        <input
          className="form-control mt-1"
          placeholder="Es. 5"
          value={values.foglio}
          onChange={(e) => setValues((c) => ({ ...c, foglio: e.target.value }))}
          disabled={disabled}
        />
      </label>
      <label className="text-sm font-medium text-gray-700">
        Particella *
        <input
          className="form-control mt-1"
          placeholder="Es. 120"
          value={values.particella}
          onChange={(e) => setValues((c) => ({ ...c, particella: e.target.value }))}
          disabled={disabled}
        />
      </label>

      <div className="flex items-end gap-2">
        <button className="btn-primary w-full" type="submit" disabled={disabled || Boolean(validationError)}>
          {disabled ? "Ricerca…" : "Cerca"}
        </button>
      </div>

      {validationError ? (
        <div className="md:col-span-4 rounded-xl border border-amber-100 bg-amber-50 p-3 text-sm text-amber-800">
          {validationError}
        </div>
      ) : null}
    </form>
  );
}
