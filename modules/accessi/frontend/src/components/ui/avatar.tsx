import { cn } from "@/lib/cn";

type AvatarProps = {
  label: string;
  size?: "sm" | "md" | "lg";
};

function getInitials(label: string): string {
  return label
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("") || "?";
}

export function Avatar({ label, size = "sm" }: AvatarProps) {
  return (
    <div
      className={cn(
        "flex shrink-0 items-center justify-center rounded-full bg-[#D3EAD4] font-medium text-[#1D4E35]",
        size === "sm" && "h-7 w-7 text-xs",
        size === "md" && "h-9 w-9 text-sm",
        size === "lg" && "h-12 w-12 text-base",
      )}
    >
      {getInitials(label)}
    </div>
  );
}
