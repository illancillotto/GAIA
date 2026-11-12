import { useState } from "react";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { TemplateEditor } from "@/components/communications/template-editor";
import { TemplatePreview } from "@/components/communications/template-preview";
import { MessageBodyEditor } from "@/components/communications/message-body-editor";
import { BLOCK_PREFIX, readBlocks, writeBlocks, safeLink } from "@/components/communications/template-blocks";

afterEach(cleanup);
const variables = { numero_avviso: "Numero avviso", contribuente_nome: "Intestatario" };
function Editor({ initial = "Testo iniziale", disabled = false }: { initial?: string; disabled?: boolean }) {
  const [body, setBody] = useState(initial);
  return <><TemplateEditor value={body} subject="Oggetto di prova" onChange={setBody} disabled={disabled} variables={variables} /><output data-testid="body">{body}</output></>;
}
const stored = () => screen.getByTestId("body").textContent!;
const insert = (name = "numero_avviso") => fireEvent.change(screen.getByLabelText("Inserisci campo dell’avviso"), { target: { value: name } });
function select(textarea: HTMLElement, start: number, end = start) {
  (textarea as HTMLTextAreaElement).focus();
  (textarea as HTMLTextAreaElement).setSelectionRange(start, end);
  fireEvent.select(textarea);
}

it("keeps legacy text editable, inserts fields at selection and converts without losing text", () => {
  render(<Editor />);
  const textarea = screen.getByLabelText("Corpo template");
  fireEvent.change(textarea, { target: { value: "Gentile Mario" } });
  select(textarea, 8, 13);
  insert("contribuente_nome");
  expect(stored()).toBe("Gentile {{contribuente_nome}}");
  fireEvent.click(screen.getByText("Crea layout con logo e link"));
  expect(readBlocks(stored())).toEqual([{ kind: "paragraph", text: "Gentile {{contribuente_nome}}" }]);
  expect(screen.getByText("Oggetto:")).toBeInTheDocument();
});

it("adds, edits, reorders and removes all supported block types with a live safe preview", () => {
  render(<Editor initial={writeBlocks([{ kind: "paragraph", text: "Originale" }])} />);
  for (const name of ["Logo ufficiale", "Titolo", "Paragrafo", "Elenco", "Link", "Pulsante"]) fireEvent.click(screen.getByRole("button", { name: `+ ${name}`, exact: true }));
  expect(readBlocks(stored())).toHaveLength(7);
  fireEvent.change(screen.getByLabelText("Testo blocco 3"), { target: { value: "Titolo avviso" } });
  fireEvent.change(screen.getByLabelText("Testo blocco 4"), { target: { value: "Riga uno\nRiga due" } });
  fireEvent.change(screen.getByLabelText("Testo blocco 5"), { target: { value: "Prima\nSeconda" } });
  for (const number of [6, 7]) {
    fireEvent.change(screen.getByLabelText(`Testo blocco ${number}`), { target: { value: `Apri ${number}` } });
    fireEvent.change(screen.getByLabelText(`URL blocco ${number}`), { target: { value: `https://example.org/${number}` } });
  }
  const preview = within(screen.getByRole("region", { name: "Anteprima messaggio" }));
  expect(preview.getByRole("img")).toHaveAttribute("src", "/communications/official-logo.png");
  expect(preview.getByRole("heading", { name: "Titolo avviso" })).toBeInTheDocument();
  expect(preview.getByRole("link", { name: "Apri 7" })).toHaveAttribute("href", "https://example.org/7");
  expect(preview.getByText("Seconda")).toBeInTheDocument();
  fireEvent.click(screen.getByLabelText("Sposta su blocco 2"));
  expect(readBlocks(stored())![0].kind).toBe("logo");
  fireEvent.click(screen.getByLabelText("Sposta giù blocco 1"));
  expect(readBlocks(stored())![1].kind).toBe("logo");
  fireEvent.click(screen.getByLabelText("Rimuovi blocco 2"));
  expect(readBlocks(stored())).toHaveLength(6);
  select(screen.getByLabelText("Testo blocco 1"), 0, 9);
  insert();
  expect(readBlocks(stored())![0].text).toBe("{{numero_avviso}}");
});

it("inserts a new paragraph without a selected text block, including stale selections", () => {
  const view = render(<Editor initial={writeBlocks([{ kind: "logo" }])} />);
  insert();
  expect(readBlocks(stored())![1].text).toBe("{{numero_avviso}}");
  select(screen.getByLabelText("Testo blocco 2"), 0);
  fireEvent.click(screen.getByLabelText("Rimuovi blocco 2"));
  insert();
  expect(readBlocks(stored())).toHaveLength(2);
  // A selected paragraph moved away leaves its old position occupied by the logo.
  select(screen.getByLabelText("Testo blocco 2"), 0);
  fireEvent.click(screen.getByLabelText("Sposta su blocco 2"));
  insert();
  expect(readBlocks(stored())).toHaveLength(3);
  view.unmount();
  render(<TemplateEditor value="Legacy" onChange={() => {}} />);
  expect(screen.queryByLabelText("Inserisci campo dell’avviso")).not.toBeInTheDocument();
});

it("respects disabled controls, one-block minimum and 60-block maximum", () => {
  const view = render(<Editor initial={writeBlocks([{ kind: "paragraph", text: "One" }])} disabled />);
  for (const button of screen.getAllByRole("button")) expect(button).toBeDisabled();
  view.unmount();
  render(<Editor initial={writeBlocks(Array.from({ length: 60 }, () => ({ kind: "logo" })))} />);
  for (const button of screen.getAllByRole("button", { name: /^\+/ })) expect(button).toBeDisabled();
  expect(screen.getByLabelText("Inserisci campo dell’avviso")).toBeDisabled();
});

it("renders raw text as text, rejects malformed documents and never turns unsafe URLs into links", () => {
  for (const value of ["old", BLOCK_PREFIX + "bad", BLOCK_PREFIX + "{}", BLOCK_PREFIX + "[]", BLOCK_PREFIX + "[null]", BLOCK_PREFIX + '[{"kind":"script"}]', writeBlocks(Array.from({ length: 61 }, () => ({ kind: "logo" })))]) expect(readBlocks(value)).toBeNull();
  for (const value of ["http://example.org", "javascript:alert(1)", "https://user@host.test", "https://:pass@host.test", "https://host.test/a b", "https://host.test/{{pin_utenza}}", "https://host.test/\n", "https://["]) expect(safeLink(value)).toBe(false);
  expect(safeLink("https://example.org/?a=1&b=2#ref")).toBe(true);
  const view = render(<TemplatePreview body={'<script>alert("x")</script>'} />);
  expect(screen.getByText('<script>alert("x")</script>')).toBeInTheDocument();
  expect(view.container.querySelector("script")).toBeNull();
  view.rerender(<TemplatePreview body={writeBlocks([{ kind: "link", text: "Unsafe", url: "javascript:x" }, { kind: "button" }, { kind: "list" }])} />);
  expect(screen.queryByRole("link")).not.toBeInTheDocument();
  expect(screen.getByText(/Unsafe · URL HTTPS/)).toBeInTheDocument();
});

it("starts an empty layout without implicit saving", () => {
  render(<Editor initial="" />);
  fireEvent.click(screen.getByText("Crea layout con logo e link"));
  fireEvent.click(screen.getByRole("button", { name: "+ Logo ufficiale", exact: true }));
  expect(readBlocks(stored())!.map((block) => block.kind)).toEqual(["paragraph", "logo"]);
});

it("keeps the notice composition compact and exposes graphical editing when requested", () => {
  const changes: string[] = [];
  const onChange = (value: string) => changes.push(value);
  const view = render(<MessageBodyEditor value="Old text" subject="Avviso" onChange={onChange} />);
  expect(screen.getByLabelText("Testo")).toHaveAttribute("rows", "3");
  fireEvent.change(screen.getByLabelText("Testo"), { target: { value: "Updated" } });
  expect(changes).toEqual(["Updated"]);
  view.rerender(<MessageBodyEditor value="Old text" subject="Avviso" onChange={onChange} rows={2} disabled />);
  expect(screen.getByLabelText("Testo")).toBeDisabled();
  expect(screen.getByLabelText("Testo")).toHaveAttribute("rows", "2");
  view.rerender(<MessageBodyEditor value={writeBlocks([{ kind: "paragraph", text: "Gentile contribuente" }])} subject="Avviso" onChange={onChange} />);
  expect(screen.getByLabelText("Messaggio da inviare").querySelector(".max-h-80")).toHaveClass("overflow-y-auto");
  const previewSummary = screen.getByText("Anteprima messaggio", { selector: "summary" });
  fireEvent.click(previewSummary);
  expect(within(previewSummary.closest("details")!).getByText("Gentile contribuente", { selector: "p" })).toBeVisible();
  fireEvent.click(screen.getByText("Modifica testo e layout"));
  fireEvent.change(screen.getByLabelText("Testo blocco 1"), { target: { value: "Edited" } });
  expect(readBlocks(changes.at(-1)!)![0].text).toBe("Edited");
});
