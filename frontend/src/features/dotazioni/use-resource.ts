import { useEffect, useState } from "react";

export function useResource<T>(loader: () => Promise<T>, revision = 0) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    setData(null);
    loader().then((result) => {
      if (active) setData(result);
    }).catch((failure: Error) => {
      if (active) setError(failure.message);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [loader, revision]);
  return { data, error, loading };
}
