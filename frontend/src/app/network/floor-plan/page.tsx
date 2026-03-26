"use client";

import Draggable from "react-draggable";
import { useEffect, useMemo, useState } from "react";

import { NetworkModulePage } from "@/components/network/network-module-page";
import { NetworkStatusBadge } from "@/components/network/network-status-badge";
import { EmptyState } from "@/components/ui/empty-state";
import { FolderIcon } from "@/components/ui/icons";
import { getNetworkDevices, getNetworkFloorPlan, getNetworkFloorPlans } from "@/lib/api";
import type { NetworkDevice, NetworkFloorPlan, NetworkFloorPlanDetail } from "@/types/api";

function FloorPlanContent({ token }: { token: string }) {
  const [plans, setPlans] = useState<NetworkFloorPlan[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null);
  const [planDetail, setPlanDetail] = useState<NetworkFloorPlanDetail | null>(null);
  const [devices, setDevices] = useState<NetworkDevice[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    async function loadBaseData() {
      try {
        const [planItems, deviceResponse] = await Promise.all([getNetworkFloorPlans(token), getNetworkDevices(token, { pageSize: 200 })]);
        setPlans(planItems);
        setDevices(deviceResponse.items);
        setSelectedPlanId(planItems[0]?.id ?? null);
        setLoadError(null);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore nel caricamento planimetrie");
      }
    }

    void loadBaseData();
  }, [token]);

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

  if (loadError) {
    return (
      <article className="panel-card">
        <p className="text-sm font-medium text-red-700">Planimetria non disponibile</p>
        <p className="mt-2 text-sm text-gray-600">{loadError}</p>
      </article>
    );
  }

  if (plans.length === 0 || !planDetail) {
    return (
      <EmptyState
        icon={FolderIcon}
        title="Nessuna planimetria disponibile"
        description="Carica almeno una planimetria a database per abilitare il posizionamento dei dispositivi."
      />
    );
  }

  return (
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
          <p className="text-xs text-gray-400">Overlay SVG con marker draggable</p>
        </div>

        <div className="relative h-[540px] overflow-hidden rounded-xl border border-gray-100 bg-[linear-gradient(135deg,#F7FAF8_0%,#EDF3EE_100%)]">
          {planDetail.svg_content ? (
            <div className="absolute inset-0 opacity-40" dangerouslySetInnerHTML={{ __html: planDetail.svg_content }} />
          ) : null}

          {planDetail.positions.map((position) => {
            const device = deviceMap.get(position.device_id);
            if (!device) {
              return null;
            }

            return (
              <Draggable key={position.id} defaultPosition={{ x: position.x, y: position.y }} disabled>
                <div className="absolute left-0 top-0">
                  <div
                    className={`group relative flex h-5 w-5 items-center justify-center rounded-full border-2 border-white shadow ${
                      device.status === "online" ? "bg-green-600" : "bg-red-600"
                    }`}
                  >
                    <span className="sr-only">{device.hostname || device.ip_address}</span>
                    <div className="pointer-events-none absolute left-7 top-1/2 hidden w-56 -translate-y-1/2 rounded-lg border border-gray-200 bg-white p-3 text-xs shadow-lg group-hover:block">
                      <p className="font-medium text-gray-900">{device.hostname || device.ip_address}</p>
                      <p className="mt-1 text-gray-500">{device.ip_address}</p>
                      <p className="mt-1 text-gray-500">{position.label || "Posizione non etichettata"}</p>
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
                  <p className="text-sm font-medium text-gray-900">{device.hostname || device.ip_address}</p>
                  <NetworkStatusBadge status={device.status} />
                </div>
                <p className="mt-1 text-xs text-gray-500">{device.ip_address}</p>
                <p className="mt-2 text-xs text-gray-500">{position.label || "Posizione non etichettata"}</p>
              </div>
            );
          })}
        </div>
      </article>
    </div>
  );
}

export default function NetworkFloorPlanPage() {
  return (
    <NetworkModulePage
      title="Planimetria"
      description="Mappa per piano con overlay SVG e marker dei dispositivi rilevati nella LAN."
      breadcrumb="Mappa"
    >
      {({ token }) => <FloorPlanContent token={token} />}
    </NetworkModulePage>
  );
}
