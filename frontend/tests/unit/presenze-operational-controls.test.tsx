import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { InazSyncControl } from "@/components/presenze/inaz-sync-control";
import { MealVoucherControl } from "@/components/presenze/meal-voucher-control";
import { relevantInazJobs, lastSuccessfulInazJob } from "@/lib/presenze-inaz-sync-state";
import type { PresenzeDailyRecord, PresenzeSyncJob } from "@/types/api";
const m=vi.hoisted(()=>({token:vi.fn(),create:vi.fn(),config:vi.fn(),credentials:vi.fn(),jobs:vi.fn(),update:vi.fn()}));
vi.mock("@/lib/auth",()=>({getStoredAccessToken:m.token}));
vi.mock("@/lib/api",()=>({createPresenzeSyncJob:m.create,getPresenzeAutoSyncConfig:m.config,listPresenzeCredentials:m.credentials,listPresenzeSyncJobs:m.jobs,updatePresenzeDailyRecord:m.update}));
const day={id:"one",meal_voucher_count:1,meal_voucher_manual:false,meal_voucher_automatic:true,meal_voucher_sources:["automatic"]} as PresenzeDailyRecord;
const job=(extra:Partial<PresenzeSyncJob>={}):PresenzeSyncJob=>({id:"job",status:"completed",credential_id:7,period_start:"2026-10-01",period_end:"2026-10-31",records_errors:0,finished_at:"2026-10-01T09:00:00Z",params_json:{},...extra} as PresenzeSyncJob);
function deferred<T>() {let resolve!:(v:T)=>void;const promise=new Promise<T>(r=>{resolve=r});return {promise,resolve};}
beforeEach(()=>{vi.resetAllMocks();m.token.mockReturnValue("token");m.config.mockResolvedValue({credential_id:7});m.credentials.mockResolvedValue([{id:7,active:true}]);m.jobs.mockResolvedValue([])});
afterEach(()=>{cleanup();vi.useRealTimers()});
describe("meal voucher",()=>{
 it("saves one grant and prevents duplicate clicks",async()=>{
  const saved=vi.fn(),pending=deferred<PresenzeDailyRecord>();m.update.mockReturnValue(pending.promise);
  render(<MealVoucherControl record={day} disabled={false} onSaved={saved}/>);
  fireEvent.click(screen.getByLabelText("Buono pasto manuale"));fireEvent.click(screen.getByLabelText("Buono pasto manuale"));
  expect(m.update).toHaveBeenCalledOnce();expect(m.update).toHaveBeenCalledWith("token","one",{meal_voucher_manual:true});
  expect(screen.getByRole("status")).toHaveTextContent("Salvataggio");await act(async()=>pending.resolve({...day,meal_voucher_manual:true}));expect(saved).toHaveBeenCalledOnce();
 });
 it("revokes only manual recognition, displays errors and disables unauthorized edits",async()=>{
  m.update.mockRejectedValue(new Error("Non autorizzato"));const {rerender}=render(<MealVoucherControl record={{...day,meal_voucher_manual:true}} disabled={false} onSaved={vi.fn()}/>);
  fireEvent.click(screen.getByLabelText("Buono pasto manuale"));expect(await screen.findByRole("alert")).toHaveTextContent("Non autorizzato");expect(m.update).toHaveBeenCalledWith("token","one",{meal_voucher_manual:false});
  rerender(<MealVoucherControl record={day} disabled onSaved={vi.fn()}/>);expect(screen.getByLabelText("Buono pasto manuale")).toBeDisabled();
 });
 it("handles no metadata, session and non-Error failures",async()=>{
  render(<MealVoucherControl record={{id:"one"} as PresenzeDailyRecord} disabled={false} onSaved={vi.fn()}/>);expect(screen.getByText(/non riconosciuto/)).toHaveTextContent("0");
  m.token.mockReturnValue(null);fireEvent.click(screen.getByLabelText("Buono pasto manuale"));expect(m.update).not.toHaveBeenCalled();m.token.mockReturnValue("token");m.update.mockRejectedValue("failure");fireEvent.click(screen.getByLabelText("Buono pasto manuale"));expect(await screen.findByRole("alert")).toHaveTextContent("Buono pasto non salvato");
 });
});
describe("INAZ",()=>{
 it("shows last success and queues unrestricted existing background pipeline once",async()=>{
  m.jobs.mockResolvedValue([job()]);const pending=deferred<PresenzeSyncJob>();m.create.mockReturnValue(pending.promise);
  render(<InazSyncControl month="2026-10" employeeCode="1407" onCompleted={vi.fn()}/>);await waitFor(()=>expect(screen.getByRole("button")).toBeEnabled());expect(screen.getByText(/Ultima sincronizzazione riuscita/)).not.toHaveTextContent("nessuna");
  fireEvent.click(screen.getByRole("button"));fireEvent.click(screen.getByRole("button"));expect(m.create).toHaveBeenCalledOnce();expect(m.create).toHaveBeenCalledWith("token",{year:2026,month:10,credential_id:7,collaborator_limit:null,employee_codes:["1407"]});await act(async()=>pending.resolve(job({status:"pending"})));expect(screen.getByRole("button")).toBeDisabled();
 });
 it("recovers running state after refresh and reloads once on completion",async()=>{
  vi.useFakeTimers();const done=vi.fn();m.jobs.mockResolvedValueOnce([job({status:"running"})]).mockResolvedValue([job()]);render(<InazSyncControl month="2026-10" onCompleted={done}/>);await act(async()=>{});expect(screen.getByRole("button")).toBeDisabled();await act(async()=>{await vi.advanceTimersByTimeAsync(3000)});expect(done).toHaveBeenCalledOnce();expect(screen.getByRole("button")).toBeEnabled();await act(async()=>{await vi.advanceTimersByTimeAsync(3000)});expect(done).toHaveBeenCalledOnce();
 });
 it("does not overlap slow polls or set state after unmount",async()=>{
  vi.useFakeTimers();const pending=deferred<PresenzeSyncJob[]>();m.jobs.mockReturnValue(pending.promise);const {unmount}=render(<InazSyncControl month="2026-10" onCompleted={vi.fn()}/>);await act(async()=>{await vi.advanceTimersByTimeAsync(6000)});expect(m.jobs).toHaveBeenCalledOnce();unmount();await act(async()=>pending.resolve([job()]));
 });
 it("shows failures and partial completion without marking it successful",async()=>{
  m.jobs.mockResolvedValue([job({status:"failed",error_detail:"INAZ offline"})]);m.create.mockRejectedValue(new Error("409 già in corso"));const {unmount}=render(<InazSyncControl month="2026-10" onCompleted={vi.fn()}/>);await waitFor(()=>expect(screen.getByRole("button")).toBeEnabled());expect(screen.getByText(/INAZ offline/)).toBeInTheDocument();fireEvent.click(screen.getByRole("button"));expect(await screen.findByText("409 già in corso")).toBeInTheDocument();unmount();m.jobs.mockResolvedValue([job({records_errors:1})]);m.credentials.mockResolvedValue([]);render(<InazSyncControl month="2026-10" onCompleted={vi.fn()}/>);await screen.findByText(/Configura una credenziale/);expect(screen.getByText(/Completamento parziale/)).toBeInTheDocument();expect(screen.getByRole("button")).toBeDisabled();
 });
 it("handles missing session and status/credential failures",async()=>{
  m.token.mockReturnValue(null);const {unmount}=render(<InazSyncControl month="2026-10" onCompleted={vi.fn()}/>);expect(m.jobs).not.toHaveBeenCalled();unmount();m.token.mockReturnValue("token");m.jobs.mockRejectedValue(new Error("stato offline"));m.credentials.mockRejectedValue("unavailable");render(<InazSyncControl month="2026-10" onCompleted={vi.fn()}/>);await screen.findByRole("alert");expect(screen.getByRole("button")).toBeDisabled();
 });
});
it("filters job scope and chooses latest successful finish",()=>{
 const old=job(),newer=job({id:"new",finished_at:"2026-10-02T09:00:00Z"});expect(relevantInazJobs([old,job({credential_id:null}),job({period_end:"2026-09-30"}),job({period_start:"2026-11-01"}),job({params_json:{employee_codes:["other"]}})],"2026-10","1407")).toEqual([old]);expect(relevantInazJobs([job({params_json:{employee_codes:[]}}),job({params_json:null})],"2026-10","1407")).toHaveLength(2);expect(lastSuccessfulInazJob([old,newer,job({records_errors:1}),job({finished_at:null}),job({status:"failed"})])).toBe(newer);
});
it("guards manual starts independently of button rendering and handles non-Error failures", async()=>{
  const { renderHook } = await import("@testing-library/react");
  const { useInazSync } = await import("@/components/presenze/use-inaz-sync");
  m.token.mockReturnValue(null);let hook=renderHook(()=>useInazSync("2026-10",undefined,vi.fn()));await act(async()=>{await hook.result.current.startInazSync()});expect(m.create).not.toHaveBeenCalled();hook.unmount();
  m.token.mockReturnValue("token");m.credentials.mockResolvedValue([]);hook=renderHook(()=>useInazSync("2026-10",undefined,vi.fn()));await act(async()=>{});await act(async()=>{await hook.result.current.startInazSync()});expect(m.create).not.toHaveBeenCalled();hook.unmount();
  m.credentials.mockResolvedValue([{id:9,active:true},{id:8,active:false}]);m.jobs.mockResolvedValue([job({status:"pending"})]);hook=renderHook(()=>useInazSync("2026-10",undefined,vi.fn()));await act(async()=>{});await act(async()=>{await hook.result.current.startInazSync()});expect(m.create).not.toHaveBeenCalled();hook.unmount();
  m.jobs.mockResolvedValue([]);m.create.mockRejectedValue("failure");hook=renderHook(()=>useInazSync("2026-10",undefined,vi.fn()));await act(async()=>{});await act(async()=>{const a=hook.result.current.startInazSync();const b=hook.result.current.startInazSync();await Promise.all([a,b])});expect(m.create).toHaveBeenCalledOnce();expect(hook.result.current.error).toBe("Sincronizzazione non avviata");expect(m.create).toHaveBeenCalledWith("token",expect.objectContaining({employee_codes:null,credential_id:9}));hook.unmount();
});
it("ignores delayed credentials responses and errors after unmount, and shows fallback diagnostics",async()=>{
 const pending=deferred<Array<{id:number;active:boolean}>>();m.credentials.mockReturnValue(pending.promise);const view=render(<InazSyncControl month="2026-10" onCompleted={vi.fn()}/>);view.unmount();await act(async()=>pending.resolve([{id:7,active:true}]));
 const errorPending=deferred<never>();m.credentials.mockReturnValue(errorPending.promise.then(()=>{throw new Error("late")}));const late=render(<InazSyncControl month="2026-10" onCompleted={vi.fn()}/>);late.unmount();await act(async()=>errorPending.resolve(undefined as never));
 m.credentials.mockRejectedValue(new Error("Credenziale scaduta"));m.jobs.mockRejectedValue("not-Error");render(<InazSyncControl month="2026-10" onCompleted={vi.fn()}/>);expect(await screen.findByRole("alert")).toHaveTextContent("Stato INAZ non disponibile");cleanup();
 m.credentials.mockResolvedValue([{id:7,active:true}]);m.jobs.mockResolvedValue([job({status:"failed",error_detail:null})]);render(<InazSyncControl month="2026-10" onCompleted={vi.fn()}/>);await screen.findByText(/Sincronizzazione fallita/);
 expect(relevantInazJobs([job({params_json:{employee_codes:["1407"]}})],"2026-10","1407")).toHaveLength(1);
});

it("ignores rejected job polls after leaving the page", async()=>{
 const pending=deferred<never>();m.jobs.mockReturnValue(pending.promise.then(()=>{throw new Error("late poll")}));const view=render(<InazSyncControl month="2026-10" onCompleted={vi.fn()}/>);view.unmount();await act(async()=>pending.resolve(undefined as never));
});
