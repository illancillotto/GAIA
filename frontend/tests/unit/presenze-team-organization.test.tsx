import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { TeamOrganizationEditor, TeamOrganizationHeader } from "@/app/presenze/squadre/team-organization";
import type { GatePresenzeTeam } from "@/types/api";

const session = vi.hoisted(() => ({ token: "synthetic" as string | null }));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: () => session.token }));
const directory = { teams: [], units: [{ unit_id: "unit-1", path: [{ id: "root", name: "Settore", kind: "settore" }, { id: "unit-1", name: "Reparto", kind: "reparto" }] }] };
const reply = (data: unknown) => new Response(JSON.stringify(data), { status: 200, headers: { "content-type": "application/json" } });

beforeEach(() => { session.token = "synthetic"; });
afterEach(() => { vi.unstubAllGlobals(); });

describe("explicit organization assignment", () => {
  it("loads canonical paths, saves an explicit assignment and unlinks with the previous ID", async () => {
    const fetch = vi.fn(async (_url, options) => options?.method === "PUT"
      ? reply({ team_id: "team", org_unit_id: JSON.parse(options.body).org_unit_id }) : reply(directory));
    vi.stubGlobal("fetch", fetch);
    render(<TeamOrganizationEditor teamId="team" />);
    expect(screen.getByRole("button", { name: "Salva collegamento" })).toBeDisabled();
    const select = await screen.findByRole("combobox", { name: "Unità organizzativa" });
    await waitFor(() => expect(select).toBeEnabled());
    expect(screen.getByRole("option", { name: "Settore / Reparto" })).toHaveValue("unit-1");
    fireEvent.change(select, { target: { value: "unit-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva collegamento" }));
    await screen.findByText(/Collegamento salvato/);
    expect(JSON.parse(fetch.mock.calls[1]![1].body)).toEqual({ org_unit_id: "unit-1", expected_org_unit_id: null });
    fireEvent.change(select, { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva collegamento" }));
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(3));
    await waitFor(() => expect(screen.getByRole("button", { name: "Salva collegamento" })).toBeDisabled());
    expect(JSON.parse(fetch.mock.calls[2]![1].body)).toEqual({ org_unit_id: null, expected_org_unit_id: "unit-1" });
    expect(fetch.mock.calls[1]![0]).toContain("/teams/team/organization");
  });

  it("recovers from load errors and preserves a missing linked unit until an explicit selection", async () => {
    const fetch = vi.fn().mockRejectedValueOnce(new Error("Offline"))
      .mockResolvedValueOnce(reply({ ...directory, teams: [{ team_id: "team", org_unit_id: "inactive" }] }))
      .mockRejectedValueOnce(new Error("Organization link changed; reload before saving"))
      .mockRejectedValueOnce("unknown");
    vi.stubGlobal("fetch", fetch);
    render(<TeamOrganizationEditor teamId="team" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Offline");
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna organigramma" }));
    await waitFor(() => expect(screen.getByRole("combobox")).toHaveValue("inactive"));
    expect(screen.getByRole("option", { name: "Unità collegata non disponibile" })).toBeDisabled();
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "unit-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva collegamento" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Organization link changed");
    fireEvent.click(screen.getByRole("button", { name: "Salva collegamento" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Collegamento non salvato");
    expect(screen.getByRole("combobox")).toHaveValue("unit-1");
    expect(JSON.parse(fetch.mock.calls[2]![1].body).expected_org_unit_id).toBe("inactive");
  });

  it("reports an absent session on load and on save, without submitting anything", async () => {
    const fetch = vi.fn().mockResolvedValue(reply(directory)); vi.stubGlobal("fetch", fetch);
    session.token = null;
    const first = render(<TeamOrganizationEditor teamId="team" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Sessione scaduta");
    expect(fetch).not.toHaveBeenCalled(); first.unmount();
    session.token = "synthetic";
    render(<TeamOrganizationEditor teamId="team" />);
    await waitFor(() => expect(screen.getByRole("combobox")).toBeEnabled());
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "unit-1" } });
    session.token = null;
    fireEvent.click(screen.getByRole("button", { name: "Salva collegamento" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Sessione scaduta");
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("ignores successful and failed responses from a previously selected team", async () => {
    let resolve!: (response: Response) => void;
    let reject!: (error: unknown) => void;
    const first = new Promise<Response>(yes => { resolve = yes; });
    const second = new Promise<Response>((_yes, no) => { reject = no; });
    const fetch = vi.fn().mockReturnValueOnce(first).mockReturnValueOnce(second).mockResolvedValue(reply(directory));
    vi.stubGlobal("fetch", fetch);
    const view = render(<TeamOrganizationEditor teamId="first" />);
    view.rerender(<TeamOrganizationEditor teamId="second" />);
    view.rerender(<TeamOrganizationEditor teamId="third" />);
    await waitFor(() => expect(screen.getByRole("combobox")).toBeEnabled());
    await act(async () => { resolve(reply({ teams: [{ team_id: "first", org_unit_id: "wrong" }], units: [] })); reject(new Error("Old error")); });
    expect(screen.getByRole("combobox")).toHaveValue("");
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.getByRole("option", { name: "Settore / Reparto" })).toBeVisible();
  });

  it("shows a safe fallback for an unknown load failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue("unknown"));
    render(<TeamOrganizationEditor teamId="team" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Organigramma non disponibile");
  });

  it("preserves the team header and active toggle", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reply(directory)));
    const onToggle = vi.fn(async () => {});
    const team = { id: "team", name: "Synthetic", code: null, personnel_area: "AGRARIO", active: true } as GatePresenzeTeam;
    const view = render(<TeamOrganizationHeader team={team} onToggle={onToggle} />);
    fireEvent.click(screen.getByRole("button", { name: "Disattiva" })); expect(onToggle).toHaveBeenCalledWith(team);
    expect(screen.getByText(/Codice n\/d/)).toBeVisible();
    view.rerender(<TeamOrganizationHeader team={{ ...team, active: false, code: "A" }} onToggle={onToggle} />);
    expect(screen.getByRole("button", { name: "Riattiva" })).toBeEnabled();
    expect(screen.getByText(/Codice A/)).toBeVisible();
    await waitFor(() => expect(screen.getByRole("combobox")).toBeEnabled());
  });
});
