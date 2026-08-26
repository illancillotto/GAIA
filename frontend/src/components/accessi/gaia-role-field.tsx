type GaiaRoleFieldProps = {
  value: string;
  options: { value: string; label: string }[];
  canAssignSuperAdmin: boolean;
  onChange: (value: string) => void;
};

export function GaiaRoleField({ value, options, canAssignSuperAdmin, onChange }: GaiaRoleFieldProps) {
  return (
    <div className="block text-sm font-medium text-gray-700 lg:col-span-6">
      <label>
        Ruolo
        <select className="form-control mt-1" value={value} onChange={(event) => onChange(event.target.value)}>
          {options
            .filter((role) => canAssignSuperAdmin || role.value !== "super_admin")
            .map((role) => (
              <option key={role.value} value={role.value}>
                {role.label}
              </option>
            ))}
        </select>
      </label>
      <span className="mt-2 block text-xs font-normal text-gray-500">
        Questo ruolo governa i permessi GAIA. Dirigente e capi vengono assegnati nell&apos;
        <a className="font-medium text-[#1D4E35] underline-offset-2 hover:underline" href="/presenze/organigramma">
          organigramma giornaliere
        </a>
        .
      </span>
    </div>
  );
}
