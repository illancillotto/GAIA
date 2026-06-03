"use client";

import { useCallback, useEffect, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { createInazHoliday, createInazScheduleRule, createInazScheduleTemplate, bootstrapInazHolidays, deleteInazHoliday, deleteInazScheduleRule, deleteInazScheduleTemplate, listInazHolidays, listInazScheduleTemplates } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { InazHoliday, InazScheduleTemplate } from "@/types/api";

function currentYear(): string {
  return String(new Date().getFullYear());
}

export default function InazConfigurazionePage() {
  const [year, setYear] = useState(currentYear());
  const [holidays, setHolidays] = useState<InazHoliday[]>([]);
  const [templates, setTemplates] = useState<InazScheduleTemplate[]>([]);
  const [holidayDate, setHolidayDate] = useState("");
  const [holidayLabel, setHolidayLabel] = useState("");
  const [holidayCompanyCode, setHolidayCompanyCode] = useState("");
  const [holidayOverride, setHolidayOverride] = useState(false);
  const [templateCode, setTemplateCode] = useState("");
  const [templateLabel, setTemplateLabel] = useState("");
  const [templateCompanyCode, setTemplateCompanyCode] = useState("");
  const [ruleTemplateId, setRuleTemplateId] = useState("");
  const [ruleLabel, setRuleLabel] = useState("");
  const [ruleWeekday, setRuleWeekday] = useState("");
  const [ruleRecurrence, setRuleRecurrence] = useState("weekly");
  const [ruleWeekOfMonth, setRuleWeekOfMonth] = useState("");
  const [ruleIntervalWeeks, setRuleIntervalWeeks] = useState("");
  const [ruleAnchorDate, setRuleAnchorDate] = useState("");
  const [ruleStartTime, setRuleStartTime] = useState("07:00");
  const [ruleEndTime, setRuleEndTime] = useState("14:00");
  const [ruleSeasonStartMonth, setRuleSeasonStartMonth] = useState("");
  const [ruleSeasonStartDay, setRuleSeasonStartDay] = useState("");
  const [ruleSeasonEndMonth, setRuleSeasonEndMonth] = useState("");
  const [ruleSeasonEndDay, setRuleSeasonEndDay] = useState("");
  const [ruleHoliday, setRuleHoliday] = useState(false);
  const [ruleOrdinaryLabel, setRuleOrdinaryLabel] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const token = getStoredAccessToken();
    if (!token) return;
    const [holidayItems, templateItems] = await Promise.all([listInazHolidays(token, Number(year)), listInazScheduleTemplates(token)]);
    setHolidays(holidayItems);
    setTemplates(templateItems);
    setRuleTemplateId((current) => current || (templateItems[0] ? String(templateItems[0].id) : ""));
  }, [year]);

  useEffect(() => {
    void refresh().catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Errore caricamento configurazione Inaz"));
  }, [refresh]);

  return (
    <ProtectedPage
      title="Configurazione Inaz"
      description="Festivita, template orari e regole di classificazione."
      breadcrumb="Inaz"
      requiredModule="inaz"
      requiredRoles={["admin", "super_admin"]}
    >
      <div className="space-y-6">
        {error ? <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
        {success ? <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div> : null}

        <article className="panel-card space-y-4">
          <div className="flex flex-wrap items-end gap-3">
            <label className="block text-sm font-medium text-gray-700">
              Anno festivita
              <input className="form-control mt-1" value={year} onChange={(event) => setYear(event.target.value)} />
            </label>
            <button
              className="btn-secondary"
              type="button"
              onClick={() =>
                void (async () => {
                  const token = getStoredAccessToken();
                  if (!token) return;
                  try {
                    const result = await bootstrapInazHolidays(token, Number(year));
                    setSuccess(`Bootstrap festivita completato: ${result.created} voci.`);
                    await refresh();
                  } catch (bootstrapError) {
                    setError(bootstrapError instanceof Error ? bootstrapError.message : "Errore bootstrap festivita");
                  }
                })()
              }
            >
              Bootstrap anno
            </button>
          </div>
          <div className="grid gap-4 lg:grid-cols-4">
            <label className="block text-sm font-medium text-gray-700">
              Data
              <input className="form-control mt-1" type="date" value={holidayDate} onChange={(event) => setHolidayDate(event.target.value)} />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Etichetta
              <input className="form-control mt-1" value={holidayLabel} onChange={(event) => setHolidayLabel(event.target.value)} />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Company code
              <input className="form-control mt-1" value={holidayCompanyCode} onChange={(event) => setHolidayCompanyCode(event.target.value)} />
            </label>
            <label className="inline-flex items-center gap-2 pt-8 text-sm text-gray-700">
              <input checked={holidayOverride} onChange={(event) => setHolidayOverride(event.target.checked)} type="checkbox" />
              Workday override
            </label>
          </div>
          <button
            className="btn-primary"
            type="button"
            onClick={() =>
              void (async () => {
                const token = getStoredAccessToken();
                if (!token) return;
                try {
                  await createInazHoliday(token, {
                    holiday_date: holidayDate,
                    label: holidayLabel,
                    company_code: holidayCompanyCode || null,
                    is_workday_override: holidayOverride,
                  });
                  setHolidayDate("");
                  setHolidayLabel("");
                  setHolidayCompanyCode("");
                  setHolidayOverride(false);
                  setSuccess("Festivita aggiunta.");
                  await refresh();
                } catch (createError) {
                  setError(createError instanceof Error ? createError.message : "Errore creazione festivita");
                }
              })()
            }
          >
            Aggiungi festivita
          </button>
          <div className="space-y-3">
            {holidays.map((holiday) => (
              <div key={holiday.id} className="flex items-center justify-between gap-3 rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
                <div>
                  <p className="font-medium text-gray-900">{holiday.holiday_date} · {holiday.label}</p>
                  <p className="text-xs text-gray-500">{holiday.company_code ?? "Globale"}{holiday.is_workday_override ? " · workday override" : ""}</p>
                </div>
                <button
                  className="btn-secondary"
                  type="button"
                  onClick={() =>
                    void (async () => {
                      const token = getStoredAccessToken();
                      if (!token) return;
                      try {
                        await deleteInazHoliday(token, holiday.id);
                        await refresh();
                      } catch (deleteError) {
                        setError(deleteError instanceof Error ? deleteError.message : "Errore eliminazione festivita");
                      }
                    })()
                  }
                >
                  Elimina
                </button>
              </div>
            ))}
          </div>
        </article>

        <article className="panel-card space-y-4">
          <div className="grid gap-4 lg:grid-cols-3">
            <label className="block text-sm font-medium text-gray-700">
              Codice template
              <input className="form-control mt-1" value={templateCode} onChange={(event) => setTemplateCode(event.target.value)} />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Etichetta
              <input className="form-control mt-1" value={templateLabel} onChange={(event) => setTemplateLabel(event.target.value)} />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Company code
              <input className="form-control mt-1" value={templateCompanyCode} onChange={(event) => setTemplateCompanyCode(event.target.value)} />
            </label>
          </div>
          <button
            className="btn-primary"
            type="button"
            onClick={() =>
              void (async () => {
                const token = getStoredAccessToken();
                if (!token) return;
                try {
                  await createInazScheduleTemplate(token, {
                    code: templateCode,
                    label: templateLabel,
                    company_code: templateCompanyCode || null,
                    is_active: true,
                  });
                  setTemplateCode("");
                  setTemplateLabel("");
                  setTemplateCompanyCode("");
                  setSuccess("Template orario creato.");
                  await refresh();
                } catch (createError) {
                  setError(createError instanceof Error ? createError.message : "Errore creazione template");
                }
              })()
            }
          >
            Crea template
          </button>

          <div className="grid gap-4 lg:grid-cols-[1.2fr_repeat(2,140px)_repeat(4,120px)_auto]">
            <label className="block text-sm font-medium text-gray-700">
              Template
              <select className="form-control mt-1" value={ruleTemplateId} onChange={(event) => setRuleTemplateId(event.target.value)}>
                <option value="">Seleziona template</option>
                {templates.map((template) => (
                  <option key={template.id} value={template.id}>
                    {template.code} · {template.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Dalle
              <input className="form-control mt-1" type="time" value={ruleStartTime} onChange={(event) => setRuleStartTime(event.target.value)} />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Alle
              <input className="form-control mt-1" type="time" value={ruleEndTime} onChange={(event) => setRuleEndTime(event.target.value)} />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Weekday
              <input className="form-control mt-1" value={ruleWeekday} onChange={(event) => setRuleWeekday(event.target.value)} placeholder="0-6" />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Recurrence
              <select className="form-control mt-1" value={ruleRecurrence} onChange={(event) => setRuleRecurrence(event.target.value)}>
                <option value="weekly">weekly</option>
                <option value="first_weekday_of_month">first_weekday_of_month</option>
                <option value="nth_weekday_of_month">nth_weekday_of_month</option>
                <option value="alternating_weeks">alternating_weeks</option>
              </select>
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Week of month
              <input className="form-control mt-1" value={ruleWeekOfMonth} onChange={(event) => setRuleWeekOfMonth(event.target.value)} />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Interval weeks
              <input className="form-control mt-1" value={ruleIntervalWeeks} onChange={(event) => setRuleIntervalWeeks(event.target.value)} />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Anchor
              <input className="form-control mt-1" type="date" value={ruleAnchorDate} onChange={(event) => setRuleAnchorDate(event.target.value)} />
            </label>
          </div>
          <div className="grid gap-4 lg:grid-cols-4">
            <label className="block text-sm font-medium text-gray-700">
              Label regola
              <input className="form-control mt-1" value={ruleLabel} onChange={(event) => setRuleLabel(event.target.value)} />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Ordinary label
              <input className="form-control mt-1" value={ruleOrdinaryLabel} onChange={(event) => setRuleOrdinaryLabel(event.target.value)} />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Season start (mese/giorno)
              <div className="mt-1 flex gap-2">
                <input className="form-control" value={ruleSeasonStartMonth} onChange={(event) => setRuleSeasonStartMonth(event.target.value)} placeholder="MM" />
                <input className="form-control" value={ruleSeasonStartDay} onChange={(event) => setRuleSeasonStartDay(event.target.value)} placeholder="DD" />
              </div>
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Season end (mese/giorno)
              <div className="mt-1 flex gap-2">
                <input className="form-control" value={ruleSeasonEndMonth} onChange={(event) => setRuleSeasonEndMonth(event.target.value)} placeholder="MM" />
                <input className="form-control" value={ruleSeasonEndDay} onChange={(event) => setRuleSeasonEndDay(event.target.value)} placeholder="DD" />
              </div>
            </label>
          </div>
          <label className="inline-flex items-center gap-2 text-sm text-gray-700">
            <input checked={ruleHoliday} onChange={(event) => setRuleHoliday(event.target.checked)} type="checkbox" />
            Valida anche nei festivi
          </label>
          <button
            className="btn-primary"
            type="button"
            onClick={() =>
              void (async () => {
                const token = getStoredAccessToken();
                if (!token || !ruleTemplateId) return;
                try {
                  await createInazScheduleRule(token, Number(ruleTemplateId), {
                    label: ruleLabel || null,
                    weekday: ruleWeekday ? Number(ruleWeekday) : null,
                    recurrence_kind: ruleRecurrence,
                    week_of_month: ruleWeekOfMonth ? Number(ruleWeekOfMonth) : null,
                    interval_weeks: ruleIntervalWeeks ? Number(ruleIntervalWeeks) : null,
                    anchor_date: ruleAnchorDate || null,
                    start_time: ruleStartTime,
                    end_time: ruleEndTime,
                    season_start_month: ruleSeasonStartMonth ? Number(ruleSeasonStartMonth) : null,
                    season_start_day: ruleSeasonStartDay ? Number(ruleSeasonStartDay) : null,
                    season_end_month: ruleSeasonEndMonth ? Number(ruleSeasonEndMonth) : null,
                    season_end_day: ruleSeasonEndDay ? Number(ruleSeasonEndDay) : null,
                    applies_on_holiday: ruleHoliday,
                    ordinary_label: ruleOrdinaryLabel || null,
                  });
                  setSuccess("Regola oraria aggiunta.");
                  await refresh();
                } catch (createError) {
                  setError(createError instanceof Error ? createError.message : "Errore creazione regola");
                }
              })()
            }
          >
            Aggiungi regola
          </button>

          <div className="space-y-4">
            {templates.map((template) => (
              <div key={template.id} className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-medium text-gray-900">{template.code} · {template.label}</p>
                    <p className="text-xs text-gray-500">{template.company_code ?? "Globale"}{template.notes ? ` · ${template.notes}` : ""}</p>
                  </div>
                  <button
                    className="btn-secondary"
                    type="button"
                    onClick={() =>
                      void (async () => {
                        const token = getStoredAccessToken();
                        if (!token) return;
                        try {
                          await deleteInazScheduleTemplate(token, template.id);
                          await refresh();
                        } catch (deleteError) {
                          setError(deleteError instanceof Error ? deleteError.message : "Errore eliminazione template");
                        }
                      })()
                    }
                  >
                    Elimina template
                  </button>
                </div>
                <div className="mt-3 space-y-2">
                  {template.rules.map((rule) => (
                    <div key={rule.id} className="flex items-center justify-between gap-3 rounded-xl border border-white bg-white px-3 py-2 text-sm text-gray-700">
                      <div>
                        {rule.label ?? rule.recurrence_kind} · {rule.start_time} / {rule.end_time}
                        {rule.weekday != null ? ` · weekday ${rule.weekday}` : ""}
                      </div>
                      <button
                        className="btn-secondary"
                        type="button"
                        onClick={() =>
                          void (async () => {
                            const token = getStoredAccessToken();
                            if (!token) return;
                            try {
                              await deleteInazScheduleRule(token, rule.id);
                              await refresh();
                            } catch (deleteError) {
                              setError(deleteError instanceof Error ? deleteError.message : "Errore eliminazione regola");
                            }
                          })()
                        }
                      >
                        Elimina
                      </button>
                    </div>
                  ))}
                  {template.rules.length === 0 ? <p className="text-sm text-gray-500">Nessuna regola per questo template.</p> : null}
                </div>
              </div>
            ))}
          </div>
        </article>
      </div>
    </ProtectedPage>
  );
}
