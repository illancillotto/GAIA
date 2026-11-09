import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { TemplateAdministration } from "@/components/communications/admin-templates";
import { TemplateCatalog } from "@/components/communications/template-catalog";
import catalog from "../../../../backend/app/modules/communications/template_catalog.json";

const mocks = vi.hoisted(() => ({ api: vi.fn() }));
vi.mock("@/lib/communications-api", () => ({ communications: mocks.api }));
beforeEach(() => {
  vi.resetAllMocks();
  mocks.api.mockImplementation((_token, path) => Promise.resolve(path === "/admin/template-catalog" ? catalog : []));
});
afterEach(cleanup);

it("loads real PEC/email proposals on demand, documents fields and never saves automatically", async () => {
  const onSelect = vi.fn();
  const view = render(<TemplateCatalog token="token" disabled={false} onSelect={onSelect} />);
  expect(mocks.api).not.toHaveBeenCalled();
  fireEvent.click(screen.getByText("Modelli di partenza 2021 e variabili"));
  await screen.findByText(catalog.note);
  expect(mocks.api).toHaveBeenCalledWith("token", "/admin/template-catalog");
  for (const proposal of catalog.proposals) {
    fireEvent.click(screen.getByText(`Usa ${proposal.name}`));
    expect(onSelect).toHaveBeenLastCalledWith(proposal);
  }
  fireEvent.click(screen.getByText("Variabili disponibili · solo testo semplice"));
  for (const [name, description] of Object.entries(catalog.variables)) {
    expect(screen.getByText(`{{${name}}}`)).toBeInTheDocument();
    expect(screen.getByText(description)).toBeInTheDocument();
  }
  view.rerender(<TemplateCatalog token="token" disabled onSelect={onSelect} />);
  for (const button of screen.getAllByRole("button")) expect(button).toBeDisabled();
  expect(mocks.api).toHaveBeenCalledTimes(1);
});

it("disables catalogue commands during loading and recovers from errors", async () => {
  let resolve!: (value: unknown) => void;
  mocks.api.mockImplementationOnce(() => new Promise((done) => { resolve = done; }));
  render(<TemplateCatalog token="token" disabled={false} onSelect={vi.fn()} />);
  const button = screen.getByText("Modelli di partenza 2021 e variabili");
  fireEvent.click(button);
  expect(button).toBeDisabled();
  await act(async () => resolve(catalog));
  await screen.findByText(catalog.note);
  for (const failure of [new Error("Catalogo offline"), "failure"]) {
    mocks.api.mockRejectedValueOnce(failure);
    fireEvent.click(button);
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(failure instanceof Error ? failure.message : "Modelli non disponibili"));
    expect(button).toBeEnabled();
  }
  fireEvent.click(button);
  await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
});

it.each(catalog.proposals)("fills an editable $channel draft and saves only on explicit command", async (proposal) => {
  render(<TemplateAdministration token="token" />);
  fireEvent.click(screen.getByText("Modelli di partenza 2021 e variabili"));
  fireEvent.click(await screen.findByText(`Usa ${proposal.name}`));
  expect(screen.getByLabelText("Codice template")).toHaveValue(proposal.code);
  expect(screen.getByLabelText("Canale template")).toHaveValue(proposal.channel);
  expect(screen.getByLabelText("Oggetto template")).toHaveValue(proposal.subject);
  expect(screen.getByLabelText("Corpo template")).toHaveValue(proposal.body);
  expect(mocks.api.mock.calls.every((call) => call[2] === undefined)).toBe(true);
  fireEvent.change(screen.getByLabelText("Corpo template"), { target: { value: "Testo revisionato dall'ufficio" } });
  fireEvent.click(screen.getByText("Salva nuova versione bozza"));
  await waitFor(() => expect(mocks.api).toHaveBeenCalledWith("token", "/templates", { ...proposal, body: "Testo revisionato dall'ufficio" }));
  await waitFor(() => expect(screen.getByLabelText("Codice template")).toHaveValue(""));
  expect(mocks.api.mock.calls.some((call) => call[1].includes("approve"))).toBe(false);
});
