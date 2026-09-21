"use client";

import { useEffect, useState } from "react";
import { registerError, registerGet } from "./client";

type Resource<T> = { key: string; data?: T; error?: string };

export function useRegisterResource<T>(token: string, path: string, revision = 0) {
  const key = JSON.stringify([token, path, revision]);
  const [result, setResult] = useState<Resource<T> | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    registerGet<T>(token, path, controller.signal).then((data) => {
      if (!controller.signal.aborted) setResult({ key, data });
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) setResult({ key, error: registerError(error) });
    });
    return () => controller.abort();
  }, [token, path, key]);
  const current = result?.key === key ? result : null;
  return { data: current?.data, error: current?.error, loading: current === null };
}
