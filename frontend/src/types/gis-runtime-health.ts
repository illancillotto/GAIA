export type GisRuntimeHealthStatus =
  | "ok"
  | "warning"
  | "critical"
  | "not_configured"
  | "disabled"
  | "unreachable";

export interface GisRuntimeComponentHealth {
  key: "postgis" | "martin" | "qgis" | "nas" | "external_sources";
  label: string;
  status: GisRuntimeHealthStatus;
  message: string;
  latency_ms?: number | null;
  checked_at: string;
  details: Record<string, unknown>;
}

export interface GisRuntimeHealthResponse {
  generated_at: string;
  status: "ok" | "warning" | "critical";
  export_scheduler_enabled: boolean;
  components: GisRuntimeComponentHealth[];
}
