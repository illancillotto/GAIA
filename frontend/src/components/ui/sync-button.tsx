import { RefreshIcon } from "@/components/ui/icons";

type SyncButtonProps = {
  onClick?: () => void;
  disabled?: boolean;
  loading?: boolean;
  label?: string;
};

export function SyncButton({
  onClick,
  disabled = false,
  loading = false,
  label = "Sincronizza ora",
}: SyncButtonProps) {
  return (
    <button className="btn-primary" disabled={disabled || loading} type="button" onClick={onClick}>
      <RefreshIcon className={loading ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
      {loading ? "Sincronizzazione..." : label}
    </button>
  );
}
