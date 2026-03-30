"use client";

import Draggable from "react-draggable";
import { useCallback, useEffect, useMemo, useState } from "react";

import { NetworkModulePage } from "@/components/network/network-module-page";
import { NetworkStatusBadge } from "@/components/network/network-status-badge";
import { EmptyState } from "@/components/ui/empty-state";
import { FolderIcon } from "@/components/ui/icons";
import {
  createNetworkFloorPlan,
  getNetworkDevices,
  getNetworkFloorPlan,
  getNetworkFloorPlans,
  updateNetworkDevicePosition,
} from "@/lib/api";
import type { NetworkDevice, NetworkFloorPlan, NetworkFloorPlanDetail } from "@/types/api";

function FloorPlanContent({ token }: { token: string }) {
  const [plans, setPlans] = useState<NetworkFloorPlan[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null);
  const [planDetail, setPlanDetail] = useState<NetworkFloorPlanDetail | null>(null);
  const [devices, setDevices] = useState<NetworkDevice[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isSavingPosition, setIsSavingPosition] = useState<number | null>(null);
  const [newPlanName, setNewPlanName] = useState("");
  const [newPlanFloor, setNewPlanFloor] = useState("");
  const [newPlanBuilding, setNewPlanBuilding] = useState("");
  const [newPlanSvg, setNewPlanSvg] = useState("");
  const [newPlanImageUrl, setNewPlanImageUrl] = useState("");

  const loadBaseData = useCallback(async () => {
    try {
      const [planItems, deviceResponse] = await Promise.all([
        getNetworkFloorPlans(token),
        getNetworkDevices(token, { pageSize: 200 }),
      ]);
      setPlans(planItems);
      setDevices(deviceResponse.items);
      setSelectedPlanId((current) => current ?? planItems[0]?.id ?? null);
      setLoadError(null);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore nel caricamento planimetrie");
    }
  }, [token]);

  useEffect(() => {
    void loadBaseData();
  }, [loadBaseData]);

  useEffect(() => {
    async function loadDetail() {
      if (!selectedPlanId) {
        setPlanDetail(null);
        return;
      }

      try {
        const response = await getNetworkFloorPlan(token, selectedPlanId);
        setPlanDetail(response);
        setLoadError(null);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore nel caricamento planimetria");
      }
    }

    void loadDetail();
  }, [selectedPlanId, token]);

  const deviceMap = useMemo(() => new Map(devices.map((device) => [device.id, device])), [devices]);
  const unpositionedDevices = useMemo(() => {
    if (!planDetail) {
      return [];
    }
    const positionedIds = new Set(planDetail.positions.map((position) => position.device_id));
    return devices.filter((device) => !positionedIds.has(device.id));
  }, [devices, planDetail]);

  async function handlePositionSave(deviceId: number, x: number, y: number, label: string | null) {
    if (!planDetail) {
      return;
    }
    setIsSavingPosition(deviceId);
    try {
      await updateNetworkDevicePosition(token, deviceId, {
        floor_plan_id: planDetail.id,
        x,
        y,
        label,
      });
      const updated = await getNetworkFloorPlan(token, planDetail.id);
      setPlanDetail(updated);
      setLoadError(null);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore salvataggio posizione");
    } finally {
      setIsSavingPosition(null);
    }
  }

  async function handleAddDevice(deviceId: number) {
    await handlePositionSave(deviceId, 40, 40, null);
  }

  async function handleCreatePlan() {
    try {
      const created = await createNetworkFloorPlan(token, {
        name: newPlanName,
        floor_label: newPlanFloor,
        building: newPlanBuilding || null,
        svg_content: newPlanSvg || null,
        image_url: newPlanImageUrl || null,
      });
      setNewPlanName("");
      setNewPlanFloor("");
      setNewPlanBuilding("");
      setNewPlanSvg("");
      setNewPlanImageUrl("");
      await loadBaseData();
      setSelectedPlanId(created.id);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore creazione planimetria");
    }
  }

  return (
    <div className="page-stack">
      {loadError ? (
        <article className="panel-card">
          <p className="text-sm font-medium text-red-700">Planimetria non disponibile</p>
          <p className="mt-2 text-sm text-gray-600">{loadError}</p>
        </article>
      ) : null}

      <article className="panel-card">
        <div className="mb-4">
          <p className="section-title">Nuova planimetria</p>
          <p className="section-copy">Salva una planimetria come SVG inline o come URL immagine per abilitare il posizionamento.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <input className="form-control" value={newPlanName} onChange={(event) => setNewPlanName(event.target.value)} placeholder="Nome planimetria" />
          <input className="form-control" value={newPlanFloor} onChange={(event) => setNewPlanFloor(event.target.value)} placeholder="Piano / etichetta" />
          <input className="form-control" value={newPlanBuilding} onChange={(event) => setNewPlanBuilding(event.target.value)} placeholder="Edificio" />
          <input className="form-control" value={newPlanImageUrl} onChange={(event) => setNewPlanImageUrl(event.target.value)} placeholder="URL immagine PNG/JPG" />
          <textarea className="form-control min-h-32 md:col-span-2" value={newPlanSvg} onChange={(event) => setNewPlanSvg(event.target.value)} placeholder="Incolla SVG inline se disponibile" />
        </div>
        <div className="mt-4 flex justify-end">
          <button className="btn-primary" type="button" onClick={() => void handleCreatePlan()} disabled={!newPlanName || !newPlanFloor || (!newPlanSvg && !newPlanImageUrl)}>
            Salva planimetria
          </button>
        </div>
      </article>

      {plans.length === 0 || !planDetail ? (
        <EmptyState
          icon={FolderIcon}
          title="Nessuna planimetria disponibile"
          description="Carica almeno una planimetria a database per abilitare il posizionamento dei dispositivi."
        />
      ) : (
        <div className="grid gap-6 xl:grid-cols-[260px_1fr]">
          <article className="panel-card">
            <p className="section-title">Piani disponibili</p>
            <div className="mt-4 space-y-2">
              {plans.map((plan) => (
                <button
                  key={plan.id}
                  type="button"
                  onClick={() => setSelectedPlanId(plan.id)}
                  className={`w-full rounded-lg border px-3 py-2 text-left text-sm transition ${
                    plan.id === selectedPlanId
                      ? "border-[#1D4E35] bg-[#EAF3E8] text-[#1D4E35]"
                      : "border-gray-200 bg-white text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  <p className="font-medium">{plan.name}</p>
                  <p className="mt-1 text-xs text-gray-500">{plan.building || "Edificio non indicato"}</p>
                </button>
              ))}
            </div>
          </article>

          <article className="panel-card">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <p className="section-title">{planDetail.name}</p>
                <p className="section-copy">
                  {planDetail.building || "Edificio n/d"} · Piano {planDetail.floor_label}
                </p>
              </div>
              <p className="text-xs text-gray-400">Drag-and-drop con persistenza su database</p>
            </div>

            <div className="relative h-[540px] overflow-hidden rounded-xl border border-gray-100 bg-[linear-gradient(135deg,#F7FAF8_0%,#EDF3EE_100%)]">
              {planDetail.image_url ? (
                <div
                  aria-label={planDetail.name}
                  className="absolute inset-0 bg-contain bg-center bg-no-repeat opacity-45"
                  style={{ backgroundImage: `url(${planDetail.image_url})` }}
                />
              ) : null}
              {planDetail.svg_content ? (
                <div className="absolute inset-0 opacity-40" dangerouslySetInnerHTML={{ __html: planDetail.svg_content }} />
              ) : null}

              {planDetail.positions.map((position) => {
                const device = deviceMap.get(position.device_id);
                if (!device) {
                  return null;
                }

                return (
                  <Draggable
                    key={`${position.id}-${position.x}-${position.y}`}
                    defaultPosition={{ x: position.x, y: position.y }}
                    onStop={(_, data) => {
                      void handlePositionSave(position.device_id, data.x, data.y, position.label);
                    }}
                  >
                    <div className="absolute left-0 top-0 cursor-move">
                      <div
                        className={`group relative flex h-5 w-5 items-center justify-center rounded-full border-2 border-white shadow ${
                          device.status === "online" ? "bg-green-600" : "bg-red-600"
                        }`}
                      >
                        <span className="sr-only">{device.hostname || device.ip_address}</span>
                        <div className="pointer-events-none absolute left-7 top-1/2 hidden w-56 -translate-y-1/2 rounded-lg border border-gray-200 bg-white p-3 text-xs shadow-lg group-hover:block">
                          <p className="font-medium text-gray-900">{device.display_name || device.hostname || device.ip_address}</p>
                          <p className="mt-1 text-gray-500">{device.ip_address}</p>
                          <p className="mt-1 text-gray-500">{position.label || "Posizione non etichettata"}</p>
                          {isSavingPosition === position.device_id ? <p className="mt-2 text-[#1D4E35]">Salvataggio…</p> : null}
                        </div>
                      </div>
                    </div>
                  </Draggable>
                );
              })}
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {planDetail.positions.map((position) => {
                const device = deviceMap.get(position.device_id);
                if (!device) {
                  return null;
                }

                return (
                  <div key={position.id} className="rounded-lg border border-gray-100 px-4 py-3">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-medium text-gray-900">{device.display_name || device.hostname || device.ip_address}</p>
                      <NetworkStatusBadge status={device.status} />
                    </div>
                    <p className="mt-1 text-xs text-gray-500">{device.ip_address}</p>
                    <p className="mt-2 text-xs text-gray-500">{position.label || "Posizione non etichettata"}</p>
                  </div>
                );
              })}
            </div>

            <div className="mt-6">
              <p className="section-title">Dispositivi non posizionati</p>
              <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {unpositionedDevices.map((device) => (
                  <button
                    key={device.id}
                    type="button"
                    className="rounded-lg border border-dashed border-gray-200 px-4 py-3 text-left transition hover:bg-gray-50"
                    onClick={() => void handleAddDevice(device.id)}
                  >
                    <p className="text-sm font-medium text-gray-900">{device.display_name || device.hostname || device.ip_address}</p>
                    <p className="mt-1 text-xs text-gray-500">{device.ip_address}</p>
                  </button>
                ))}
                {unpositionedDevices.length === 0 ? (
                  <p className="text-sm text-gray-500">Tutti i dispositivi caricati risultano già posizionati su questa planimetria.</p>
                ) : null}
              </div>
            </div>
          </article>
        </div>
      )}
    </div>
  );
}

export default function NetworkFloorPlanPage() {
  return (
    <NetworkModulePage
      title="Planimetria"
      description="Mappa per piano con overlay SVG e posizionamento persistito dei dispositivi rilevati nella LAN."
      breadcrumb="Mappa"
    >
      {({ token }) => <FloorPlanContent token={token} />}
    </NetworkModulePage>
  );
}
