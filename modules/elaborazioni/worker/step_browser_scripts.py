"""Browser-side readers for the STEP SmartClient UI.

Ported verbatim from the verified ``step-scraper`` (Node.js) used for the
first full extraction. They run through ``page.evaluate`` only: the portal
overrides ``window.Set``, which breaks ``locator.evaluate_all`` and
``page.wait_for_function``.
"""

from __future__ import annotations

READ_CONTRIBUENTI = r"""
() => {
  const grid = window.RicercaContribuente;
  if (!grid?.data) return null;
  const text = document.body.innerText;
  const counts = text.match(/Records trovati:\s*([\d.]+)[\s\S]*?Pagina\s+(\d+)\s+di\s+(\d+)/);
  if (!counts) return null;
  const data = Array.isArray(grid.data) ? grid.data : grid.data.localData;
  if (!data?.length) return null;
  const fields = grid.fields.map(field => {
    const element = document.createElement('span');
    element.innerHTML = field.title || field.name;
    return { name: field.name, title: element.textContent.trim() };
  });
  const rows = Array.from(data).filter(Boolean).map(record => {
    const result = {};
    for (const key of Object.keys(record)) {
      const value = record[key];
      if (!key.startsWith('_') && (value === null || ['string', 'number', 'boolean'].includes(typeof value))) result[key] = value;
    }
    return result;
  });
  return { total: Number(counts[1].replaceAll('.', '')), page: Number(counts[2]), pages: Number(counts[3]), fields, rows };
}
"""

READ_SHEET = r"""
() => {
  const widgets = [];
  for (const key of Object.keys(window)) {
    try {
      const widget = window[key];
      if (widget?.ID && typeof widget.getHandle === 'function' && widget.getHandle()) widgets.push(widget);
    } catch {}
  }
  const sheet = widgets.find(widget => window.isc.isA.Window(widget) && widget.title === 'Scheda Contribuente' && widget.isVisible());
  if (!sheet) return null;
  const root = sheet.getHandle();
  const clean = value => {
    const element = document.createElement('span');
    element.innerHTML = String(value ?? '');
    return element.textContent.trim();
  };
  const serializable = value => {
    if (value === undefined || value === null) return null;
    if (Object.prototype.toString.call(value) === '[object Date]') return Number.isNaN(value.getTime()) ? null : `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`;
    if (['string', 'number', 'boolean'].includes(typeof value)) return value;
    return null;
  };
  const forms = [];
  const grids = [];
  for (const widget of widgets) {
    if (!root.contains(widget.getHandle())) continue;
    if (window.isc.isA.DynamicForm(widget)) {
      const fields = [];
      let label;
      for (const item of widget.getItems()) {
        if (window.isc.isA.StaticTextItem(item)) {
          label = clean(item.getValue());
          continue;
        }
        const value = serializable(item.getValue());
        if (!label && value === 'Tipo persona') {
          label = value;
          continue;
        }
        fields.push({ name: item.name, label: label || clean(item.title) || item.name, value, displayValue: serializable(item.valueMap?.[value] ?? value) });
        label = undefined;
      }
      forms.push({ id: widget.ID, fields });
    }
    if (window.isc.isA.ListGrid(widget) && !widget.ID.endsWith('_summaryRow')) {
      let section;
      for (let parent = widget.parentElement; parent; parent = parent.parentElement) {
        if (window.isc.isA.Window(parent) && parent.title && parent !== sheet) { section = clean(parent.title); break; }
      }
      const data = Array.isArray(widget.data) ? widget.data : widget.data?.localData;
      grids.push({ id: widget.ID, section, fields: widget.fields.map(field => ({ name: field.name, title: clean(field.title || field.name) })), rows: Array.from(data || []).filter(Boolean).map(record => Object.fromEntries(Object.keys(record).filter(key => !key.startsWith('_') && (record[key] === null || ['string', 'number', 'boolean'].includes(typeof record[key]))).map(key => [key, record[key]]))), totalRows: widget.data?.getLength?.() ?? widget.data?.length ?? 0 });
    }
  }
  const personalForm = forms.find(form => form.fields.some(field => field.label === 'Indirizzo'));
  const accountingForm = forms.find(form => form.fields.some(field => field.label === 'Tot. Dovuto'));
  const documents = grids.find(grid => grid.fields.some(field => field.name === 'NUM_TRIB'));
  if (!personalForm || !accountingForm || !documents) return null;
  return { windowId: sheet.ID, handleId: root.id, closeId: sheet.closeButton?.getHandle()?.id, forms, anagrafica: Object.fromEntries(personalForm.fields.map(field => [field.label, field.value])), situazioneContabile: Object.fromEntries(accountingForm.fields.map(field => [field.label, field.value])), grids };
}
"""

READ_TRIBUTI = r"""
() => {
  const grid = window.ListaTributoRuolo;
  if (!grid?.getHandle?.()) return null;
  let modal = grid.parentElement;
  while (modal && !window.isc.isA.Window(modal)) modal = modal.parentElement;
  if (!modal?.isVisible()) return null;
  const counts = modal.getHandle().innerText.match(/Records trovati:\s*([\d.]+)[\s\S]*?Pagina\s+(\d+)\s+di\s+(\d+)/);
  if (!counts) return null;
  const data = Array.isArray(grid.data) ? grid.data : grid.data?.localData;
  const rows = Array.from(data || []).filter(Boolean).map(record => Object.fromEntries(Object.entries(record).filter(([key, value]) => !key.startsWith('_') && (value === null || ['string', 'number', 'boolean'].includes(typeof value)))));
  return { total: Number(counts[1].replaceAll('.', '')), page: Number(counts[2]), pages: Number(counts[3]), rows, fields: grid.fields.map(field => ({ name: field.name, title: field.title })), modalId: modal.ID, handleId: modal.getHandle().id, closeId: modal.closeButton?.getHandle()?.id };
}
"""
