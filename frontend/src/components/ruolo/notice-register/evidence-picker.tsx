"use client";

import { useState } from "react";
import type { RegisterEvidence, RegisterPage } from "@/types/notice-register";
import { inputClass, ReadState } from "./presentation";
import { useRegisterResource } from "./use-register-resource";

export function EvidencePicker({ token, documentPath, initial }: { token: string; documentPath: string; initial: string }) {
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState(initial);
  const resource = useRegisterResource<RegisterPage<RegisterEvidence>>(token, `${documentPath}/evidenze?page=${page}&page_size=20`);
  return <span className="grid gap-2">
    <select className={inputClass} name="evidence_id" value={selected} onChange={(event) => setSelected(event.target.value)}>
      <option value="">Seleziona una evidenza</option>
      {selected && <option value={selected}>Selezionata: {selected}</option>}
      {resource.data?.items.filter((entry) => entry.id !== selected).map((entry) => <option key={entry.id} value={entry.id}>{entry.kind}: {entry.reference}</option>)}
    </select>
    <ReadState loading={resource.loading} error={resource.error} />
    <span className="flex flex-wrap gap-2">
      <button type="button" className="btn-secondary" disabled={page === 1} onClick={() => setPage(page - 1)}>Evidenze precedenti</button>
      <button type="button" className="btn-secondary" disabled={!resource.data || page * 20 >= resource.data.total} onClick={() => setPage(page + 1)}>Altre evidenze</button>
    </span>
  </span>;
}
