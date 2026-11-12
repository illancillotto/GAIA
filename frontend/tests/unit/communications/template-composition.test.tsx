import { useState } from "react";
import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { useTemplateComposition } from "@/components/communications/use-template-composition";
import type { Channel, Template } from "@/types/communications";
import { template } from "./fixtures";

const api = vi.hoisted(() => vi.fn());
vi.mock("@/lib/communications-api", () => ({ communications: api }));
const sha = "a".repeat(64);
const preview = { subject: "Avviso 000123 / 2021", body: "Contribuente sintetico · 10,00", source_sha256: sha };
const empty = { recipient: "test@example.org", account_id: "", template_id: "", subject: "", body: "", expected_source_sha256: sha };
type Input = { sourceId: string; channel: Channel; templates: Template[] };
const initial: Input = { sourceId: "source", channel: "pec", templates: [template] };

function useComposition(input: Input) {
  const [compose, setCompose] = useState(empty);
  return { ...useTemplateComposition({ token: "token", ...input, compose, setCompose }), compose, setCompose };
}

beforeEach(() => { api.mockReset(); api.mockResolvedValue(preview); });
afterEach(cleanup);

it.each(["pec", "email"] as const)("defaults the sole approved %s template and fills canonical text without creating a draft", async (channel) => {
  const available = { ...template, channel };
  const { result } = renderHook(() => useComposition({ ...initial, channel, templates: [available, { ...available, id: "draft", status: "draft" }, { ...available, id: "other", channel: channel === "pec" ? "email" : "pec" }] }));
  expect(result.current.templateId).toBe("template");
  expect(result.current.loading).toBe(true);
  expect(result.current.ready).toBe(false);
  await waitFor(() => expect(result.current.ready).toBe(true));
  expect(result.current.compose).toMatchObject({ template_id: "template", subject: preview.subject, body: preview.body });
  expect(api).toHaveBeenCalledExactlyOnceWith("token", `/ruolo/candidates/source/template-preview?template_id=template&channel=${channel}`);
});

it("does not choose among multiple templates and preserves manual edits across refreshed lists", async () => {
  const templates = [template, { ...template, id: "second" }];
  const { result, rerender } = renderHook(useComposition, { initialProps: { ...initial, templates } });
  expect(result.current.templateId).toBe("");
  expect(result.current.ready).toBe(true);
  expect(api).not.toHaveBeenCalled();
  act(() => result.current.selectTemplate("second"));
  await waitFor(() => expect(result.current.ready).toBe(true));
  act(() => result.current.setCompose(value => ({ ...value, subject: "Revisione operatore" })));
  rerender({ ...initial, templates: templates.map(value => ({ ...value })) });
  expect(result.current.compose.subject).toBe("Revisione operatore");
  expect(api).toHaveBeenCalledTimes(1);
  act(() => result.current.selectTemplate(""));
  rerender(initial);
  expect(result.current.templateId).toBe("");
  expect(result.current.compose.subject).toBe("Revisione operatore");
  expect(result.current.compose.template_id).toBe("");
  expect(api).toHaveBeenCalledTimes(1);
});

it("waits for source and templates, and binds the loaded text to the exact rendered PDF", async () => {
  const { result, rerender } = renderHook(useComposition, { initialProps: { ...initial, sourceId: "", templates: [] } });
  expect(api).not.toHaveBeenCalled();
  rerender(initial);
  await waitFor(() => expect(result.current.ready).toBe(true));
  act(() => result.current.setCompose(value => ({ ...value, expected_source_sha256: "" })));
  expect(result.current.ready).toBe(false);
  expect(result.current.error).toBe("");
  act(() => result.current.setCompose(value => ({ ...value, expected_source_sha256: "b".repeat(64) })));
  expect(result.current.ready).toBe(false);
  expect(result.current.error).toMatch(/PDF è cambiato/);
  act(() => result.current.setCompose(value => ({ ...value, expected_source_sha256: sha })));
  expect(result.current.ready).toBe(true);
});

it.each([new Error("Variabile template mancante: pin_utenza"), "network"])("blocks failed rendering, exposes an error and permits retry", async failure => {
  api.mockRejectedValueOnce(failure);
  const { result } = renderHook(() => useComposition(initial));
  await waitFor(() => expect(result.current.loading).toBe(false));
  expect(result.current.ready).toBe(false);
  expect(result.current.compose.subject).toBe("");
  expect(result.current.error).toBe(failure instanceof Error ? failure.message : "Testo del template non disponibile");
  act(() => result.current.retry());
  await waitFor(() => expect(result.current.ready).toBe(true));
  expect(result.current.error).toBe("");
  expect(result.current.compose.body).toBe(preview.body);
});

it("ignores late success and failure when another template or manual text is selected", async () => {
  let resolve!: (value: typeof preview) => void;
  let reject!: (value: Error) => void;
  api.mockImplementationOnce(() => new Promise(done => { resolve = done; }))
    .mockImplementationOnce(() => new Promise((_done, fail) => { reject = fail; }));
  const { result } = renderHook(() => useComposition(initial));
  act(() => result.current.selectTemplate("second"));
  await act(async () => resolve({ ...preview, subject: "Vecchio avviso" }));
  expect(result.current.compose.subject).toBe("");
  expect(result.current.loading).toBe(true);
  act(() => result.current.selectTemplate(""));
  act(() => result.current.setCompose(value => ({ ...value, body: "Testo manuale" })));
  await act(async () => reject(new Error("Risposta vecchia")));
  expect(result.current.compose.body).toBe("Testo manuale");
  expect(result.current.error).toBe("");
  expect(result.current.ready).toBe(true);
});


it("shows incomplete template text and independent dispatch blockers without allowing a draft", async () => {
  api.mockResolvedValue({ ...preview, body: "PIN [Da verificare: pin_utenza]", missing_variables: ["pin_utenza"], send_blockers: ["Avviso riconciliato con Poste: invio PEC/email escluso per ora"] });
  const { result } = renderHook(() => useComposition(initial));
  await waitFor(() => expect(result.current.loading).toBe(false));
  expect(result.current.compose.subject).toBe(preview.subject);
  expect(result.current.compose.body).toContain("[Da verificare: pin_utenza]");
  expect(result.current.incomplete).toBe("pin_utenza");
  expect(result.current.blocked).toContain("riconciliato con Poste");
  expect(result.current.ready).toBe(false);
});
