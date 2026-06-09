export function getInazCompanyLabel(
  companyLabel: string | null | undefined,
  _companyCode: string | null | undefined,
  fallback = "",
): string {
  const normalized = companyLabel?.trim();
  return normalized && normalized.length > 0 ? normalized : fallback;
}
