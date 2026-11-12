"use client";

import { useState } from "react";
import { communications } from "@/lib/communications-api";
import type { Template } from "@/types/communications";

export type TemplateDraft = Pick<Template, "code" | "name" | "channel" | "subject" | "body"> & { module: string };
type Catalog = { variables: Record<string, string>; note: string; proposals: TemplateDraft[] };

export function useTemplateCatalog(token: string, onVariables?: (variables: Record<string, string>) => void) {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [status, setStatus] = useState({ busy: false, error: "" });
  async function load() {
    setStatus({ busy: true, error: "" });
    try {
      const loaded = await communications<Catalog>(token, "/admin/template-catalog");
      setCatalog(loaded);
      onVariables?.(loaded.variables);
      setStatus({ busy: false, error: "" });
    } catch (error) { setStatus({ busy: false, error: error instanceof Error ? error.message : "Modelli non disponibili" }); }
  }
  return { catalog, status, load };
}
