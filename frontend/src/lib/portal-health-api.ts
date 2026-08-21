import { request } from "@/lib/api";
import type { SisterPortalEventList, SisterPortalHealth } from "@/types/api";


function authorization(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` };
}


export function getSisterPortalHealth(token: string, hours = 24): Promise<SisterPortalHealth> {
  return request<SisterPortalHealth>(`/elaborazioni/portal-health?hours=${hours}`, {
    headers: authorization(token),
  });
}


export function getSisterPortalEvents(
  token: string,
  hours = 24,
  limit = 100,
): Promise<SisterPortalEventList> {
  return request<SisterPortalEventList>(
    `/elaborazioni/portal-health/events?hours=${hours}&limit=${limit}`,
    { headers: authorization(token) },
  );
}
