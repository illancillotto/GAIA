export type Custody = {
  id: string;
  holder_user_id: number;
  holder_name: string;
  taken_at: string;
  returned_at: string | null;
  handover_from_user_id: number | null;
  handover_from_name?: string | null;
  notes: string | null;
  return_notes: string | null;
};

export type Asset = {
  id: string;
  asset_code: string;
  asset_type: string;
  name: string;
  description: string | null;
  brand: string | null;
  model: string | null;
  serial_number: string | null;
  imei: string | null;
  phone_number: string | null;
  mac_address: string | null;
  notes: string | null;
  status: string;
  effective_status: string;
  is_active: boolean;
  assigned_org_unit_id: string | null;
  assigned_org_unit_name: string | null;
  network_device_id: number | null;
  vehicle_id: string | null;
  plate_number: string | null;
  vehicle_status: string | null;
  current_custody: Custody | null;
};

export type AssetInput = Pick<Asset, "asset_code" | "asset_type" | "name"> & Partial<Omit<Asset, "id" | "effective_status" | "assigned_org_unit_name" | "plate_number" | "vehicle_status" | "current_custody">>;
export type Capabilities = { view: boolean; manage: boolean; assign: boolean; custody: boolean; history: boolean };
export type Lookup = { id: string | number; name: string };
export type Lookups = { users: Lookup[]; org_units: Lookup[]; network_devices: Lookup[]; vehicles: Lookup[]; permissions: string[] };
export type PageResult<T> = { items: T[]; total: number };
