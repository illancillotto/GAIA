import type { FormEvent, ReactNode } from "react";

export function ActionCard({
  eyebrow,
  title,
  description,
  children,
  tone = "neutral",
}: {
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
  tone?: "neutral" | "emerald" | "sky" | "amber";
}) {
  const toneClassName = {
    neutral: "border-[#d8dfd3] bg-white",
    emerald: "border-emerald-200 bg-[linear-gradient(180deg,_rgba(236,253,245,0.9),_#ffffff)]",
    sky: "border-sky-200 bg-[linear-gradient(180deg,_rgba(240,249,255,0.9),_#ffffff)]",
    amber: "border-amber-200 bg-[linear-gradient(180deg,_rgba(255,251,235,0.92),_#ffffff)]",
  }[tone];

  return (
    <article className={`rounded-[22px] border p-3.5 shadow-panel ${toneClassName}`}>
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">{eyebrow}</p>
      <p className="mt-1 text-base font-semibold text-gray-900">{title}</p>
      <p className="mt-1 text-sm leading-5 text-gray-600">{description}</p>
      <div className="mt-3">{children}</div>
    </article>
  );
}

export function ActionField({
  htmlFor,
  label,
  children,
}: {
  htmlFor: string;
  label: string;
  children: ReactNode;
}) {
  return (
    <label htmlFor={htmlFor} className="grid gap-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
      <span>{label}</span>
      {children}
    </label>
  );
}

export function InternalNoteCard({ onSubmit }: { onSubmit: (event: FormEvent<HTMLFormElement>) => void }) {
  return (
    <ActionCard
      eyebrow="Tracciamento"
      title="Nota interna"
      description="Usa note brevi e operative per lasciare il contesto utile al prossimo passaggio."
    >
      <form className="space-y-3" onSubmit={onSubmit}>
        <ActionField htmlFor="tributi-note-body" label="Nota operativa">
          <textarea id="tributi-note-body" name="body" rows={3} placeholder="Es. utente contattato, pratica contestata..." className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm outline-none focus:border-[#8CB39D]" />
        </ActionField>
        <button type="submit" className="btn-secondary w-full">Salva nota</button>
      </form>
    </ActionCard>
  );
}
