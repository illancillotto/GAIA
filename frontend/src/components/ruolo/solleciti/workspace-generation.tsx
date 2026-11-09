export function WorkspaceGeneration() {
  return <div className="flex flex-wrap items-center gap-3">
    <button type="button" className="btn-secondary" disabled aria-describedby="notice-generation-disabled">Genera o recupera PDF</button>
    <p id="notice-generation-disabled" className="text-sm text-slate-500">Generazione temporaneamente disabilitata.</p>
  </div>;
}
