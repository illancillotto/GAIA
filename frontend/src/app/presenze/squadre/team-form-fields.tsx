import type { Dispatch, SetStateAction } from "react";

export type TeamFormState = {
  name: string;
  code: string;
  personnelArea: "AGRARIO" | "IMPIANTI";
};

type TeamFormFieldsProps = {
  value: TeamFormState;
  setValue: Dispatch<SetStateAction<TeamFormState>>;
};

export function TeamFormFields({ value, setValue }: TeamFormFieldsProps) {
  return (
    <>
      <label className="text-sm font-semibold text-slate-700">
        Nome squadra
        <input
          className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
          name="team_name"
          value={value.name}
          onChange={(event) => setValue((current) => ({ ...current, name: event.target.value }))}
          placeholder="Es. Squadra Nord"
        />
      </label>
      <label className="text-sm font-semibold text-slate-700">
        Codice
        <input
          className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
          name="team_code"
          value={value.code}
          onChange={(event) => setValue((current) => ({ ...current, code: event.target.value }))}
          placeholder="NORD"
        />
      </label>
      <label className="text-sm font-semibold text-slate-700">
        Area personale
        <select
          className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
          value={value.personnelArea}
          onChange={(event) => setValue((current) => ({
            ...current,
            personnelArea: event.target.value as TeamFormState["personnelArea"],
          }))}
        >
          <option value="AGRARIO">Agrario</option>
          <option value="IMPIANTI">Impianti</option>
        </select>
      </label>
    </>
  );
}
