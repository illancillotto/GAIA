type SourceTagProps = {
  source: string;
};

export function SourceTag({ source }: SourceTagProps) {
  return (
    <code className="inline-flex rounded border border-gray-100 bg-gray-50 px-1.5 py-0.5 font-mono text-xs text-gray-500">
      {source}
    </code>
  );
}
