import type { RuoloAvvisoListItemResponse } from "@/types/ruolo";

export function formatRuoloAvvisoNotificationDate(value: string | null | undefined): string | null {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat("it-IT", { dateStyle: "short", timeStyle: "short" }).format(parsed);
}

export function buildRuoloAvvisoDigitalDeliveryLabel(avviso: RuoloAvvisoListItemResponse): string | null {
  const delivery = avviso.digital_delivery;
  if (!delivery) return null;
  const parts = ["Digitale/PEC"];
  if (delivery.delivery_status) parts.push(delivery.delivery_status);
  const acceptedAt = formatRuoloAvvisoNotificationDate(delivery.accepted_at);
  const deliveredAt = formatRuoloAvvisoNotificationDate(delivery.delivered_at);
  if (acceptedAt) parts.push(`accettata ${acceptedAt}`);
  if (deliveredAt) parts.push(`consegnata ${deliveredAt}`);
  if (delivery.pec_recipient) parts.push(delivery.pec_recipient);
  return parts.join(" · ");
}

export function buildRuoloAvvisoRegisteredMailLabel(avviso: RuoloAvvisoListItemResponse): string | null {
  const mail = avviso.registered_mail;
  if (!mail) return null;
  const parts = ["Raccomandata"];
  const sentAt = formatRuoloAvvisoNotificationDate(mail.sent_at);
  if (sentAt) parts.push(`inviata ${sentAt}`);
  if (mail.status_label) parts.push(mail.status_label);
  if (mail.tracking_number) parts.push(`tracking ${mail.tracking_number}`);
  return parts.join(" · ");
}
