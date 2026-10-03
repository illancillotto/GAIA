const statusLabels: Record<string, string> = {
  available: "Disponibile", in_use: "In custodia", maintenance: "In manutenzione",
  lost: "Smarrito", damaged: "Danneggiato", retired: "Dismesso",
};

const typeLabels: Record<string, string> = {
  phone: "Telefono", tablet: "Tablet", notebook: "Notebook", desktop: "Computer fisso",
  radio: "Radio", vehicle: "Veicolo", tool: "Strumento", key: "Chiave",
  network_device: "Dispositivo di rete", printer: "Stampante", other: "Altro",
};

export function statusLabel(status: string): string {
  return Object.hasOwn(statusLabels, status) ? statusLabels[status] : status;
}

export function typeLabel(type: string): string {
  return Object.hasOwn(typeLabels, type) ? typeLabels[type] : type;
}

const dateFormatter = new Intl.DateTimeFormat("it-IT", {
  timeZone: "Europe/Rome", day: "2-digit", month: "2-digit", year: "numeric",
  hour: "2-digit", minute: "2-digit",
});

export function custodyDate(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Data non disponibile";
  return dateFormatter.format(date);
}
