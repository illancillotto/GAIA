import { cn } from "@/lib/cn";
import {
  getHighestPrioritySourceIndexes,
  isMultiSourceAnomaly,
  parseSourceTokens,
} from "@/lib/permissions";

type SourceTagProps = {
  source: string;
  expanded?: boolean;
};

export function SourceTag({ source, expanded = false }: SourceTagProps) {
  const tokens = parseSourceTokens(source);

  if (!expanded || !isMultiSourceAnomaly(source) || tokens.length === 0) {
    return (
      <code className="inline-flex rounded border border-gray-100 bg-gray-50 px-1.5 py-0.5 font-mono text-xs text-gray-500">
        {source}
      </code>
    );
  }

  const highlightedIndexes = new Set(getHighestPrioritySourceIndexes(source));

  return (
    <div className="inline-flex max-w-full flex-col gap-1">
      {tokens.map((token, index) => (
        <code
          key={`${token.type}:${token.name}:${token.level}:${token.effect}:${index}`}
          className={cn(
            "inline-flex w-fit rounded border px-1.5 py-0.5 font-mono text-xs",
            highlightedIndexes.has(index)
              ? "border-amber-200 bg-amber-100 text-amber-800"
              : "border-gray-100 bg-gray-50 text-gray-500",
          )}
        >
          {token.type}:{token.name}:{token.level}:{token.effect}
        </code>
      ))}
    </div>
  );
}
