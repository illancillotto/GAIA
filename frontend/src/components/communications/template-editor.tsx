"use client";

import { useRef } from "react";
import { BLOCK_LABELS, readBlocks, writeBlocks, type TemplateBlock, type BlockKind } from "./template-blocks";
import { TemplateBlockEditor } from "./template-block-editor";
import { TemplatePreview } from "./template-preview";

type Props = { value: string; onChange: (value: string) => void; label?: string; subject?: string; disabled?: boolean; variables?: Record<string, string> };

export function TemplateEditor({ value, onChange, label = "Corpo template", subject, disabled, variables = {} }: Props) {
  const blocks = readBlocks(value);
  const focus = useRef<{ index: number; start: number; end: number }>({ index: -1, start: 0, end: 0 });
  function update(index: number, changes: Partial<TemplateBlock>) {
    onChange(writeBlocks(blocks!.map((block, position) => position === index ? { ...block, ...changes } : block)));
  }
  function add(kind: BlockKind) {
    const block: TemplateBlock = kind === "logo" ? { kind } : { kind, text: "" };
    if (kind === "link" || kind === "button") block.url = "https://";
    onChange(writeBlocks([...blocks!, block]));
  }
  function move(index: number, step: number) {
    const next = [...blocks!];
    [next[index], next[index + step]] = [next[index + step], next[index]];
    onChange(writeBlocks(next));
  }
  function insertVariable(name: string) {
    const { index, start, end } = focus.current;
    const marker = `{{${name}}}`;
    if (!blocks) { onChange(value.slice(0, start) + marker + value.slice(end)); return; }
    if (index < 0 || !blocks[index] || blocks[index].kind === "logo") { onChange(writeBlocks([...blocks, { kind: "paragraph", text: marker }])); return; }
    const text = blocks[index].text!;
    update(index, { text: text.slice(0, start) + marker + text.slice(end) });
  }
  return <div className="min-w-0 space-y-3">
    <fieldset disabled={disabled} className="min-w-0 space-y-3">
      <legend className="mb-2 font-medium">{label}</legend>
      {!blocks ? <><label className="block text-sm">{label}<textarea className="mt-1 block min-h-40 w-full rounded border p-2" maxLength={20000} value={value} onSelect={(event) => { focus.current = { index: -1, start: event.currentTarget.selectionStart, end: event.currentTarget.selectionEnd }; }} onChange={(event) => onChange(event.target.value)} /></label>
        <button type="button" className="btn-secondary" onClick={() => onChange(writeBlocks([{ kind: "paragraph", text: value }]))}>Crea layout con logo e link</button></> : <>
        <div className="flex flex-wrap gap-2" aria-label="Aggiungi blocco">{Object.entries(BLOCK_LABELS).map(([kind, name]) => <button type="button" className="btn-secondary" key={kind} disabled={blocks.length >= 60} onClick={() => add(kind as BlockKind)}>+ {name}</button>)}</div>
        {blocks.map((block, index) => <TemplateBlockEditor key={index} block={block} index={index} count={blocks.length}
          update={(changes) => update(index, changes)} move={(step) => move(index, step)}
          remove={() => onChange(writeBlocks(blocks.filter((_, position) => position !== index)))}
          select={(start, end) => { focus.current = { index, start, end }; }} />)}
      </>}
      {Object.keys(variables).length > 0 && <label className="block text-sm">Inserisci campo dell’avviso<select className="ml-2 max-w-full rounded border p-2" disabled={blocks?.length === 60} value="" onChange={(event) => insertVariable(event.target.value)}><option value="" disabled>Scegli un campo</option>{Object.entries(variables).map(([name, description]) => <option key={name} value={name}>{description} ({name})</option>)}</select></label>}
    </fieldset>
    <TemplatePreview body={value} subject={subject} />
  </div>;
}
