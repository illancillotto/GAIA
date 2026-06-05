"use client";

import { BellIcon } from "@/components/ui/icons";

type NetworkTrackToggleProps = {
  tracked: boolean;
  label?: string;
  compact?: boolean;
  disabled?: boolean;
  busy?: boolean;
  onClick: () => void;
};

export function NetworkTrackToggle({
  tracked,
  label,
  compact = false,
  disabled = false,
  busy = false,
  onClick,
}: NetworkTrackToggleProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled || busy}
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition ${
        tracked
          ? "border-amber-200 bg-amber-50 text-amber-800"
          : "border-gray-200 bg-white text-gray-600 hover:border-[#8CB39D] hover:text-[#1D4E35]"
      } ${compact ? "px-2.5 py-1 text-[11px]" : ""} ${disabled || busy ? "cursor-not-allowed opacity-60" : ""}`}
      title={tracked ? "Elemento gia tracciato" : "Traccia questo elemento"}
    >
      <BellIcon className="h-3.5 w-3.5" />
      <span>{busy ? "..." : label || (tracked ? "Tracciato" : "Traccia")}</span>
    </button>
  );
}
