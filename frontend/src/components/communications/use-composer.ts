"use client";
import { useCallback, useState } from "react";
import { communications, uploadAttachment } from "@/lib/communications-api";
import type { Communication } from "@/types/communications";

type Props = { token: string; message: Communication; canEdit: boolean; onChange: (message: Communication) => void };
export function useComposer({ token, message, canEdit, onChange }: Props) {
  const [form, setForm] = useState({ account_id: message.account_id, recipient: message.recipient, subject: message.subject, body: message.body });
  const [checks, setChecks] = useState<string[]>([]);
  const [rendered, setRendered] = useState<Record<string, boolean>>({});
  const [status, setStatus] = useState({ busy: false, error: "" });
  const dirty = Object.entries(form).some(([key, value]) => value !== message[key as keyof typeof form]);
  const editable = canEdit && ["draft", "ready", "approved"].includes(message.state);
  const ready = !dirty && message.attachments.length > 0 && message.attachments.every((part) => rendered[part.id]);
  const onRender = useCallback((id: string, ok: boolean) => setRendered((current) => ({ ...current, [id]: ok })), []);
  function change(key: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [key]: value })); setChecks([]);
  }
  async function action(name: string) {
    setStatus({ busy: true, error: "" });
    try {
      const path = `/messages/${message.id}`;
      const payload = commandPayload(name, message.version, form, checks);
      await communications(token, name === "save" ? path : `${path}/${name}`, payload, name === "save" ? "PATCH" : "POST");
      const next = await communications<Communication>(token, path);
      setChecks([]); onChange(next); setStatus({ busy: false, error: "" });
    } catch (error) { setStatus({ busy: false, error: error instanceof Error ? error.message : "Operazione fallita" }); }
  }
  async function upload(file: File) {
    setStatus({ busy: true, error: "" });
    try {
      onChange(await uploadAttachment(token, message.id, message.version, file));
      setChecks([]); setStatus({ busy: false, error: "" });
    } catch (error) { setStatus({ busy: false, error: error instanceof Error ? error.message : "Caricamento fallito" }); }
  }
  return { form, checks, setChecks, status, dirty, editable, ready, onRender, change, action, upload };
}

function commandPayload(name: string, version: number, form: Record<string, string>, checks: string[]) {
  if (name === "save") return { ...form, expected_version: version };
  if (name === "approve") return { expected_version: version, checklist: Object.fromEntries(checks.map((key) => [key, true])), confirmed: true };
  return { expected_version: version };
}
