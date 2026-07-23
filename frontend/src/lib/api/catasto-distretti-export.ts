import { requestBlob } from "@/lib/api";

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

export async function catastoDownloadDistrettoParticelleExport(
  token: string,
  id: string,
  format: "csv" | "xlsx" | "geojson",
): Promise<Blob> {
  return requestBlob(`/catasto/distretti/${id}/particelle/export?format=${format}`, {
    headers: authHeaders(token),
  });
}
