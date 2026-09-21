"use client";

import { useState } from "react";
import type { RegisterPage } from "@/types/notice-register";
import type { ImportBatch } from "./import-client";
import { ImportDetail } from "./import-detail";
import { ImportSources } from "./import-forms";
import { Pagination, ReadState, panelClass } from "./presentation";
import { useRegisterResource } from "./use-register-resource";

function ImportHistory({ token, onSelect }: { token: string; onSelect: (id: string) => void }) {
  const [page, setPage] = useState(1);
  const result = useRegisterResource<RegisterPage<ImportBatch>>(token, `/importazioni?page=${page}&page_size=10`);
  return <section className={panelClass}><h3 className="mb-3 text-lg font-semibold">Storico importazioni</h3>
    <ReadState {...result} />{result.data && <>
      {result.data.items.map((batch) => <div key={batch.id} className="mb-3 flex flex-wrap items-center gap-3 text-sm">
        <button className="btn-secondary max-w-full break-all" onClick={() => onSelect(batch.id)}>{batch.filename}</button><span>{batch.created_at} | {batch.status}</span>
      </div>)}
      {result.data.total === 0 && <p>Nessuna importazione presente.</p>}
      <Pagination page={page} total={result.data.total} pageSize={10} onPage={setPage} />
    </>}
  </section>;
}

export function ImportWorkspace({ token, canEdit, onSelect }: { token: string; canEdit: boolean; onSelect: (id: string) => void }) {
  const [selected, setSelected] = useState<string | null>(null);
  return <div className="space-y-5"><section className={panelClass}>
    <h2 className="mb-3 text-xl font-semibold">Importazioni Excel e Poste</h2>
    <p className="mb-5 text-sm">Originali conservati, anteprima e conferma separata. Excel e Poste non vengono uniti automaticamente. I conflitti restano da verificare, senza aggiornare documenti gia valutati.</p>
    {canEdit && <ImportSources token={token} onSaved={(batch) => setSelected(batch.id)} />}
  </section>
    {selected ? <><button className="btn-secondary" onClick={() => setSelected(null)}>Torna allo storico importazioni</button>
      <ImportDetail key={selected} token={token} batchId={selected} canEdit={canEdit} onSelect={onSelect} /></>
      : <ImportHistory token={token} onSelect={setSelected} />}
  </div>;
}
