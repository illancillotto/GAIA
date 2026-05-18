"use client";

type CatastoFilePickerProps = {
  id: string;
  label: string;
  accept: string;
  file?: File | null;
  files?: File[];
  onChange: (file: File | null) => void;
  onChangeFiles?: (files: File[]) => void;
  hint?: string;
  disabled?: boolean;
  buttonLabel?: string;
  emptyLabel?: string;
  multiple?: boolean;
};

export function CatastoFilePicker({
  id,
  label,
  accept,
  file,
  files,
  onChange,
  onChangeFiles,
  hint,
  disabled = false,
  buttonLabel = "Scegli file",
  emptyLabel = "Nessun file selezionato",
  multiple = false,
}: CatastoFilePickerProps) {
  const selectedFiles = files ?? (file ? [file] : []);
  const displayLabel =
    selectedFiles.length <= 1
      ? selectedFiles[0]?.name ?? emptyLabel
      : `${selectedFiles.length} file selezionati`;

  return (
    <div className="text-sm font-medium text-gray-700">
      <p>{label}</p>
      <label
        htmlFor={id}
        className={[
          "mt-1 flex items-center gap-3 rounded-xl border border-gray-200 bg-white px-4 py-3 transition",
          disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer hover:border-[#1D4E35]/40 hover:bg-[#f7fbf8]",
        ].join(" ")}
      >
        <span className="inline-flex shrink-0 rounded-lg border border-[#1D4E35]/20 bg-[#eef6f0] px-3 py-1.5 text-sm font-semibold text-[#1D4E35]">
          {buttonLabel}
        </span>
        <span className={`min-w-0 truncate text-sm ${selectedFiles.length > 0 ? "text-gray-800" : "text-gray-400"}`}>
          {displayLabel}
        </span>
      </label>
      <input
        id={id}
        className="sr-only"
        type="file"
        accept={accept}
        disabled={disabled}
        multiple={multiple}
        onChange={(event) => {
          const nextFiles = Array.from(event.target.files ?? []);
          if (multiple) {
            onChangeFiles?.(nextFiles);
            onChange(nextFiles[0] ?? null);
            return;
          }
          onChange(nextFiles[0] ?? null);
        }}
      />
      {hint ? <p className="mt-1 text-xs text-gray-400">{hint}</p> : null}
    </div>
  );
}
