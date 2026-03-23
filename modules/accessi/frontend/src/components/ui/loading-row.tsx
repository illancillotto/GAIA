type LoadingRowProps = {
  columns?: number;
};

export function LoadingRow({ columns = 5 }: LoadingRowProps) {
  return (
    <tr>
      {Array.from({ length: columns }).map((_, index) => (
        <td key={index}>
          <div className="h-4 animate-pulse rounded bg-gray-100" />
        </td>
      ))}
    </tr>
  );
}
