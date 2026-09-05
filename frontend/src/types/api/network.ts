export type NetworkDashboardSummary = {
  total_devices: number;
  online_devices: number;
  offline_devices: number;
  open_alerts: number;
  firewalls_online: number;
  scans_last_24h: number;
  floor_plans: number;
  latest_scan_at: string | null;
};

export type NetworkStatisticsCountItem = {
  key: string;
  label: string;
  count: number;
};

export type NetworkStatisticsTrafficItem = {
  label: string;
  ip_address: string | null;
  device_id: number | null;
  events_count: number;
  bytes_in: number;
  bytes_out: number;
  bytes_total: number;
  tracked_subject_id: number | null;
};

export type NetworkStatisticsTimelinePoint = {
  bucket: string;
  events_count: number;
  bytes_in: number;
  bytes_out: number;
};

export type NetworkStatisticsSummary = {
  window_hours: number;
  generated_at: string;
  total_devices: number;
  active_devices: number;
  retired_devices: number;
  online_devices: number;
  offline_devices: number;
  known_devices: number;
  unknown_devices: number;
  monitored_devices: number;
  assigned_devices: number;
  unassigned_devices: number;
  placeholder_profiles: number;
  devices_with_traffic: number;
  firewall_count: number;
  open_alerts: number;
  total_events: number;
  allowed_events: number;
  blocked_events: number;
  bytes_in: number;
  bytes_out: number;
  unique_external_peers: number;
  unique_domains: number;
  top_device_types: NetworkStatisticsCountItem[];
  top_vendors: NetworkStatisticsCountItem[];
  top_offices: NetworkStatisticsCountItem[];
  top_assignees: NetworkStatisticsCountItem[];
  severity_breakdown: NetworkStatisticsCountItem[];
  protocol_breakdown: NetworkStatisticsCountItem[];
  top_event_types: NetworkStatisticsCountItem[];
  top_firewall_rules: NetworkStatisticsCountItem[];
  top_domains: NetworkStatisticsTrafficItem[];
  top_destinations: NetworkStatisticsTrafficItem[];
  top_source_devices: NetworkStatisticsTrafficItem[];
  hourly_timeline: NetworkStatisticsTimelinePoint[];
};

export type NetworkAssignedUserSummary = {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  full_name: string | null;
  office_location: string | null;
  phone_extension: string | null;
  is_placeholder_profile: boolean;
};

export type NetworkTrackedSubjectActivityEvent = {
  id: number;
  firewall_id: number;
  device_id: number | null;
  event_type: string;
  severity: string;
  protocol: string | null;
  src_ip: string | null;
  src_device_label: string | null;
  dst_ip: string | null;
  dst_device_label: string | null;
  domain: string | null;
  url: string | null;
  bytes_in: number;
  bytes_out: number;
  matched_on: string;
  matched_value: string;
  detection_tags: string[];
  observed_at: string;
};

export type NetworkTrackedSubjectActivitySummary = {
  window_hours: number;
  total_events: number;
  allowed_events: number;
  blocked_events: number;
  suspicious_events: number;
  vpn_suspected_events: number;
  proxy_suspected_events: number;
  tor_suspected_events: number;
  encrypted_dns_events: number;
  bytes_in: number;
  bytes_out: number;
  last_observed_at: string | null;
  top_detection_tags: string[];
  recent_events: NetworkTrackedSubjectActivityEvent[];
};

export type NetworkIpWhois = {
  ip_address: string;
  scope: string;
  is_private: boolean;
  is_loopback: boolean;
  is_link_local: boolean;
  rdap_status: "ok" | "unavailable" | "not_applicable";
  label: string | null;
  network_name: string | null;
  handle: string | null;
  country: string | null;
  start_address: string | null;
  end_address: string | null;
  cidr: string[];
  entities: string[];
  external_url: string | null;
  raw: Record<string, unknown> | null;
};

export type NetworkTrackedSubject = {
  id: number;
  entity_type: "device" | "ip" | "domain" | "url";
  normalized_value: string;
  value: string;
  label: string | null;
  resolved_label: string;
  notes: string | null;
  is_active: boolean;
  device_id: number | null;
  device_label: string | null;
  created_by_user_id: number | null;
  created_by_username: string | null;
  created_at: string;
  updated_at: string;
  activity_summary: NetworkTrackedSubjectActivitySummary | null;
  scan_history: {
    scan_id: number;
    observed_at: string;
    status: string;
    hostname: string | null;
    ip_address: string;
    mac_address: string | null;
    open_ports: string | null;
  }[];
};

export type NetworkDevice = {
  id: number;
  last_scan_id: number | null;
  assigned_user_id: number | null;
  ip_address: string;
  mac_address: string | null;
  hostname: string | null;
  hostname_source: string | null;
  display_name: string | null;
  resolved_label: string;
  label_source: string;
  lifecycle_state: "active" | "retired";
  asset_label: string | null;
  vendor: string | null;
  model_name: string | null;
  device_type: string | null;
  operating_system: string | null;
  dns_name: string | null;
  location_hint: string | null;
  notes: string | null;
  is_known_device: boolean;
  metadata_sources: Record<string, string> | null;
  status: string;
  is_monitored: boolean;
  open_ports: string | null;
  retired_at: string | null;
  assigned_user: NetworkAssignedUserSummary | null;
  first_seen_at: string;
  last_seen_at: string;
  created_at: string;
  updated_at: string;
  positions: DevicePosition[];
  scan_history: {
    scan_id: number;
    observed_at: string;
    status: string;
    hostname: string | null;
    ip_address: string;
    mac_address: string | null;
    resolved_label: string | null;
    label_source: string | null;
    assigned_user_label: string | null;
    open_ports: string | null;
  }[];
  traffic_summary: {
    window_hours: number;
    total_events: number;
    allowed_events: number;
    blocked_events: number;
    bytes_in: number;
    bytes_out: number;
    last_observed_at: string | null;
    top_peers: {
      ip_address: string;
      label: string | null;
      events_count: number;
      bytes_in: number;
      bytes_out: number;
      tracked_subject_id: number | null;
    }[];
    recent_events: {
      id: number;
      event_type: string;
      severity: string;
      protocol: string | null;
      src_ip: string | null;
      dst_ip: string | null;
      peer_ip: string | null;
      peer_label: string | null;
      bytes_in: number;
      bytes_out: number;
      observed_at: string;
      tracked_peer_ip_subject_id: number | null;
      tracked_peer_label_subject_id: number | null;
      tracked_url_subject_id: number | null;
    }[];
  } | null;
};

export type NetworkDeviceUpdateInput = {
  display_name?: string | null;
  lifecycle_state?: "active" | "retired" | null;
  asset_label?: string | null;
  model_name?: string | null;
  device_type?: string | null;
  operating_system?: string | null;
  location_hint?: string | null;
  notes?: string | null;
  assigned_user_id?: number | null;
  is_known_device?: boolean;
  is_monitored?: boolean;
};

export type NetworkDeviceBulkUpdateInput = {
  device_ids: number[];
  is_known_device?: boolean | null;
  location_hint?: string | null;
  notes_append?: string | null;
};

export type NetworkDeviceBulkUpdateResponse = {
  updated_count: number;
  items: NetworkDevice[];
};

export type NetworkDeviceListResponse = {
  items: NetworkDevice[];
  total: number;
  page: number;
  page_size: number;
};

export type NetworkAlert = {
  id: number;
  device_id: number | null;
  scan_id: number | null;
  assigned_to_user_id: number | null;
  assigned_to_username: string | null;
  assigned_to_full_name: string | null;
  alert_type: string;
  severity: string;
  status: string;
  verification_status: "pending" | "investigating" | "confirmed" | "false_positive" | "tolerated";
  title: string;
  message: string | null;
  verification_notes: string | null;
  created_at: string;
  reviewed_at: string | null;
  acknowledged_at: string | null;
};

export type NetworkAlertUpdateInput = {
  status?: "open" | "resolved" | "ignored";
  assigned_to_user_id?: number | null;
  verification_status?: "pending" | "investigating" | "confirmed" | "false_positive" | "tolerated";
  verification_notes?: string | null;
};

export type NetworkFirewall = {
  id: number;
  vendor: string;
  name: string;
  model_name: string | null;
  serial_number: string | null;
  management_ip: string | null;
  status: string;
  metadata_sources: Record<string, string> | null;
  last_seen_at: string | null;
  created_at: string;
  updated_at: string;
};

export type NetworkFirewallLogFamilyStatus = {
  family_key: string;
  label: string;
  expected: boolean;
  observed_count: number;
  last_observed_at: string | null;
  status: "ok" | "missing" | "observed";
  examples: string[];
};

export type NetworkFirewallLogCoverageSummary = {
  firewall_id: number;
  window_hours: number;
  generated_at: string;
  total_events: number;
  expected_families: NetworkFirewallLogFamilyStatus[];
  additional_families: NetworkFirewallLogFamilyStatus[];
  missing_expected_families: string[];
  top_event_types: { key: string; label: string; count: number }[];
};

export type NetworkFirewallEvent = {
  id: number;
  firewall_id: number;
  device_id: number | null;
  source: string;
  event_type: string;
  severity: string;
  log_id: string | null;
  message: string | null;
  src_ip: string | null;
  src_device_label: string | null;
  dst_ip: string | null;
  dst_device_label: string | null;
  protocol: string | null;
  raw_payload: Record<string, unknown> | null;
  observed_at: string;
  tracked_src_ip_subject_id: number | null;
  tracked_dst_ip_subject_id: number | null;
  tracked_domain_subject_id: number | null;
  tracked_url_subject_id: number | null;
};

export type NetworkTrackedSubjectCreateInput = {
  entity_type: "device" | "ip" | "domain" | "url";
  value?: string | null;
  device_id?: number | null;
  label?: string | null;
  notes?: string | null;
};

export type NetworkTrackedSubjectUpdateInput = {
  label?: string | null;
  notes?: string | null;
  is_active?: boolean;
};

export type NetworkDetectionWatchlistRule = {
  id: number;
  category: "vpn" | "proxy" | "tor" | "encrypted_dns";
  rule_mode: "detect" | "allow";
  match_type: "keyword" | "domain" | "url" | "ip";
  pattern: string;
  label: string | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type NetworkDetectionWatchlistRuleCreateInput = {
  category: "vpn" | "proxy" | "tor" | "encrypted_dns";
  rule_mode?: "detect" | "allow";
  match_type: "keyword" | "domain" | "url" | "ip";
  pattern: string;
  label?: string | null;
  notes?: string | null;
  is_active?: boolean;
};

export type NetworkDetectionWatchlistRuleUpdateInput = {
  rule_mode?: "detect" | "allow";
  label?: string | null;
  notes?: string | null;
  is_active?: boolean;
};

export type NetworkVpnBypassSummary = {
  total_subjects: number;
  vpn_subjects: number;
  proxy_subjects: number;
  tor_subjects: number;
  encrypted_dns_subjects: number;
  total_suspicious_events: number;
  open_alerts: number;
  transient_device_alerts: number;
  arp_ephemeral_alerts: number;
  arp_identity_alerts: number;
  arp_spoofing_alerts: number;
  watchlist_rules: number;
};

export type NetworkVpnDeviceStatus = "active" | "blocked" | "revoked";

export type NetworkVpnAccessDevice = {
  id: number;
  user_id: number;
  device_fingerprint: string;
  client_device_id: string | null;
  display_name: string | null;
  status: NetworkVpnDeviceStatus;
  user_agent_hash: string | null;
  user_agent_sample: string | null;
  first_client_ip: string | null;
  last_client_ip: string | null;
  first_seen_at: string;
  last_seen_at: string;
  created_at: string;
  updated_at: string;
};

export type NetworkVpnAccessDeviceListResponse = {
  items: NetworkVpnAccessDevice[];
  total: number;
  skip: number;
  limit: number;
};

export type NetworkVpnAccessSession = {
  id: number;
  user_id: number | null;
  device_id: number | null;
  source: string;
  event_type: "login_allowed" | "login_blocked" | string;
  username: string | null;
  client_ip: string | null;
  vpn_ip: string | null;
  public_ip: string | null;
  device_fingerprint: string | null;
  user_agent_hash: string | null;
  user_agent_sample: string | null;
  blocked_reason: string | null;
  observed_at: string;
  created_at: string;
};

export type NetworkVpnAccessSessionListResponse = {
  items: NetworkVpnAccessSession[];
  total: number;
  skip: number;
  limit: number;
};

export type NetworkArpTimelineObservation = {
  observed_at: string;
  scan_id: number;
  device_id: number | null;
  ip_address: string;
  mac_address: string | null;
  status: string;
  resolved_label: string | null;
  hostname: string | null;
};

export type NetworkArpTimelineItem = {
  scope_key: string;
  scope_type: "device" | "ip";
  device_id: number | null;
  resolved_label: string | null;
  primary_ip_address: string | null;
  primary_mac_address: string | null;
  first_observed_at: string;
  last_observed_at: string;
  observations_count: number;
  online_appearances: number;
  offline_appearances: number;
  distinct_ip_addresses: string[];
  distinct_mac_addresses: string[];
  rapid_reappearances: number;
  suspicious_reasons: string[];
  observations: NetworkArpTimelineObservation[];
};

export type NetworkFirewallMetric = {
  id: number;
  firewall_id: number;
  metric_key: string;
  metric_value: number | null;
  metric_text: string | null;
  unit: string | null;
  severity: string;
  raw_payload: Record<string, unknown> | null;
  observed_at: string;
};

export type NetworkSophosConfig = {
  syslog_enabled: boolean;
  snmp_enabled: boolean;
  operation_window_enabled: boolean;
  operation_start_hour: number;
  operation_end_hour: number;
  operation_timezone: string;
  is_within_window: boolean;
  syslog_effective_enabled: boolean;
  snmp_effective_enabled: boolean;
  updated_at: string | null;
};

export type NetworkSophosConfigUpdateInput = {
  syslog_enabled?: boolean;
  snmp_enabled?: boolean;
  operation_window_enabled?: boolean;
  operation_start_hour?: number;
  operation_end_hour?: number;
  operation_timezone?: string;
};

export type NetworkScanDeltaSummary = {
  new_devices_count: number;
  missing_devices_count: number;
  changed_devices_count: number;
};

export type NetworkScan = {
  id: number;
  network_range: string;
  scan_type: string;
  status: string;
  hosts_scanned: number;
  active_hosts: number;
  discovered_devices: number;
  initiated_by: string | null;
  notes: string | null;
  started_at: string;
  completed_at: string;
  delta: NetworkScanDeltaSummary;
};

export type NetworkScanTriggerResponse = {
  scan: NetworkScan;
  devices_upserted: number;
  alerts_created: number;
};

export type NetworkScanTriggerInput = {
  scan_type?: "incremental" | "arp";
  network_range?: string;
};

export type BonificaUserStaging = {
  id: string;
  wc_id: number;
  username: string | null;
  email: string | null;
  user_type: string | null;
  business_name: string | null;
  first_name: string | null;
  last_name: string | null;
  tax: string | null;
  phone: string | null;
  mobile: string | null;
  role: string | null;
  enabled: boolean;
  wc_synced_at: string | null;
  review_status: string;
  matched_subject_id: string | null;
  matched_subject_display_name: string | null;
  mismatch_fields: Record<string, unknown> | null;
  reviewed_by: number | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type BonificaUserStagingListResponse = {
  items: BonificaUserStaging[];
  total: number;
  page: number;
  page_size: number;
};

export type BonificaUserStagingBulkApproveResponse = {
  approved: number;
  skipped: number;
  errors: string[];
};

export type NetworkScanDevice = {
  id: number;
  scan_id: number;
  device_id: number | null;
  ip_address: string;
  mac_address: string | null;
  hostname: string | null;
  hostname_source: string | null;
  display_name: string | null;
  resolved_label: string | null;
  label_source: string | null;
  assigned_user_label: string | null;
  asset_label: string | null;
  vendor: string | null;
  model_name: string | null;
  device_type: string | null;
  operating_system: string | null;
  dns_name: string | null;
  location_hint: string | null;
  metadata_sources: Record<string, string> | null;
  status: string;
  open_ports: string | null;
  observed_at: string;
};

export type NetworkScanDetail = NetworkScan & {
  devices: NetworkScanDevice[];
};

export type NetworkScanDiffEntry = {
  key: string;
  before: NetworkScanDevice | null;
  after: NetworkScanDevice | null;
  change_type: string;
};

export type NetworkScanDiff = {
  from_scan_id: number;
  to_scan_id: number;
  summary: NetworkScanDeltaSummary;
  changes: NetworkScanDiffEntry[];
};

export type NetworkFloorPlan = {
  id: number;
  name: string;
  building: string | null;
  floor_label: string;
  svg_content: string | null;
  image_url: string | null;
  width: number | null;
  height: number | null;
  created_at: string;
  updated_at: string;
};

export type DevicePosition = {
  id: number;
  device_id: number;
  floor_plan_id: number;
  x: number;
  y: number;
  label: string | null;
  created_at: string;
  updated_at: string;
};

export type NetworkFloorPlanDetail = NetworkFloorPlan & {
  positions: DevicePosition[];
};

export type NetworkFloorPlanCreateInput = {
  name: string;
  floor_label: string;
  building?: string | null;
  svg_content?: string | null;
  image_url?: string | null;
  width?: number | null;
  height?: number | null;
};

export type DevicePositionUpdateInput = {
  floor_plan_id: number;
  x: number;
  y: number;
  label?: string | null;
};

export type NetworkFloorPlanDevice = {
  position: DevicePosition;
  device: NetworkDevice;
};
