import { useState } from "react";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { TemplateEditor } from "@/components/communications/template-editor";
import { TemplateBlockEditor } from "@/components/communications/template-block-editor";
import { MessageBodyEditor } from "@/components/communications/message-body-editor";
import { readBlocks, writeBlocks, type TemplateBlock } from "@/components/communications/template-blocks";
import { CONDITION_LABEL, convertToBlocks, icatastoBlocks, IcatastoInsert } from "@/components/communications/icatasto-blocks";
import catalog from "../../../../backend/app/modules/communications/template_catalog.json";

afterEach(cleanup);
function Editor({ initial }: { initial: string }) {
  const [body, setBody] = useState(initial);
  return <><TemplateEditor value={body} onChange={setBody} /><output data-testid="body">{body}</output></>;
}
const blocks = () => readBlocks(screen.getByTestId("body").textContent!)!;

it("inserts editable portal text and link, retaining conditions through edits and reordering", () => {
  render(<Editor initial={writeBlocks([{ kind: "paragraph", text: "Gentile contribuente" }])} />);
  fireEvent.click(screen.getByRole("button", { name: "+ Servizio ICATASTO" }));
  expect(blocks().slice(1)).toEqual(icatastoBlocks());
  expect(screen.getAllByLabelText(CONDITION_LABEL).map((el) => (el as HTMLInputElement).checked)).toEqual([false, true, true]);
  const preview = within(screen.getByRole("region", { name: "Anteprima messaggio" }));
  expect(preview.getAllByText(/Se manca uno dei due dati/)).toHaveLength(2);
  expect(preview.getByRole("link", { name: "Accedi al SERVIZIO ICATASTO" })).toHaveAttribute("href", "https://incatasto.servizicapacitas.com/pages/main.aspx?cons=090");
  fireEvent.change(screen.getByLabelText("Testo blocco 2"), { target: { value: "PIN {{pin_utenza}} e utenza {{codice_utenza}}" } });
  expect(blocks()[1].condition).toBe("icatasto");
  fireEvent.click(screen.getByLabelText("Sposta su blocco 3"));
  expect(blocks()[1].kind).toBe("button");
  fireEvent.click(screen.getAllByLabelText(CONDITION_LABEL)[1]);
  expect(blocks()[1]).not.toHaveProperty("condition");
  fireEvent.click(screen.getAllByLabelText(CONDITION_LABEL)[1]);
  expect(blocks()[1].condition).toBe("icatasto");
  fireEvent.click(screen.getByLabelText("Rimuovi blocco 2"));
  expect(blocks()).toHaveLength(2);
});

it.each(catalog.proposals)("converts the existing $channel office text without losing the other paragraphs", (proposal) => {
  render(<Editor initial={proposal.body} />);
  fireEvent.click(screen.getByText("Crea layout con logo e link"));
  const conditional = blocks().filter((block) => block.condition);
  expect(conditional).toHaveLength(2);
  expect(conditional[0].text).toContain("{{codice_utenza}}");
  expect(conditional[0].text).toContain("{{pin_utenza}}");
  expect(conditional[0].text).not.toContain("{{url_portale}}");
  for (const paragraph of proposal.body.split("\n\n").filter((text) => !text.includes("SERVIZIO ICATASTO"))) {
    expect(blocks()).toContainEqual({ kind: "paragraph", text: paragraph });
  }
});

it("preserves custom text, empty text, Windows line endings and oversized legacy text", () => {
  for (const text of ["", "SERVIZIO ICATASTO senza credenziali", "PIN {{pin_utenza}}", Array(61).fill("Paragrafo").join("\n\n")]) {
    expect(readBlocks(convertToBlocks(text))).toEqual([{ kind: "paragraph", text }]);
  }
  const text = catalog.proposals[0].body.replaceAll("\n", "\r\n");
  expect(readBlocks(convertToBlocks(text))!.filter((block) => block.condition)).toHaveLength(2);
});

it("converts pasted text with blank lines without producing unsaveable empty blocks", () => {
  render(<Editor initial={"\n\nGentile contribuente\n\n \n\n\nCordiali saluti\r\n\r\n"} />);
  fireEvent.click(screen.getByText("Crea layout con logo e link"));
  expect(blocks()).toEqual([
    { kind: "paragraph", text: "Gentile contribuente" },
    { kind: "paragraph", text: "Cordiali saluti" },
  ]);
});

it("honors the 60-block limit and disables conditional authoring in composed messages", () => {
  const onChange = vi.fn();
  const list: TemplateBlock[] = Array.from({ length: 58 }, () => ({ kind: "logo" }));
  const view = render(<IcatastoInsert blocks={list} onChange={onChange} />);
  fireEvent.click(screen.getByRole("button"));
  expect(readBlocks(onChange.mock.calls[0][0])).toHaveLength(60);
  view.rerender(<IcatastoInsert blocks={[...list, { kind: "logo" }]} onChange={onChange} />);
  expect(screen.getByRole("button")).toBeDisabled();
  view.rerender(<MessageBodyEditor value={writeBlocks([{ kind: "paragraph", text: "Avviso" }])} subject="Test" onChange={onChange} />);
  expect(screen.queryByText("+ Servizio ICATASTO")).not.toBeInTheDocument();
  expect(screen.queryByLabelText(CONDITION_LABEL)).not.toBeInTheDocument();
});

it("enables the condition selector by default for a standalone block editor", () => {
  render(<TemplateBlockEditor block={{ kind: "logo" }} index={0} count={1} update={vi.fn()} move={vi.fn()} remove={vi.fn()} select={vi.fn()} />);
  expect(screen.getByLabelText(CONDITION_LABEL)).not.toBeChecked();
});
