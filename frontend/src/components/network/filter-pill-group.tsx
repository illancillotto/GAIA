"use client";

type FilterPillOption<T extends string> = {
  value: T;
  label: string;
};

export function FilterPillGroup<T extends string>({
  options,
  value,
  onChange,
}: {
  options: readonly FilterPillOption<T>[];
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((option) => {
        const isActive = value === option.value;
        return (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            className={`rounded-full border px-3 py-1.5 text-xs font-medium transition ${
              isActive
                ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                : "border-gray-200 bg-white text-gray-600 hover:border-emerald-200 hover:text-emerald-700"
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
