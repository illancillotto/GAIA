function normalizeIssueText(value: string | null): string {
  return (value ?? "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

export function buildCapacitasDiagnosis(detail: string | null, statusCode: number | null): string | null {
  const normalized = normalizeIssueText(detail);

  if (normalized.includes("token non trovato")) {
    return "Il login HTTP risponde 200 ma il backend non riesce a estrarre il token di sessione. Di solito significa login rifiutato senza redirect, markup del form cambiato, oppure cookie AUTH_COOKIE non impostato dal portale.";
  }
  if (normalized.includes("viewstate")) {
    return "La pagina SSO sembra aver cambiato i campi ASP.NET richiesti. Va verificato il parsing di __VIEWSTATE / __EVENTVALIDATION nel backend.";
  }
  if (statusCode === 502) {
    return "Il frontend raggiunge correttamente il backend, ma il backend non completa la negoziazione con il portale esterno. Il punto da verificare e il parser di login Capacitas o la risposta HTML reale post-login.";
  }
  return null;
}

export function buildBonificaDiagnosis(detail: string | null, statusCode: number | null): string | null {
  const normalized = normalizeIssueText(detail);

  if (normalized.includes("csrf") || normalized.includes("_token")) {
    return "Il login page parser non ha trovato il token CSRF Laravel. Verificare markup del form /login o selettori nel backend.";
  }
  if (normalized.includes("credenziali non valide")) {
    return "Il portale ha risposto con form di login ancora attivo. Le credenziali salvate non sono accettate oppure il provider ha cambiato i campi di autenticazione.";
  }
  if (statusCode === 502) {
    return "Il frontend raggiunge correttamente il backend, ma il backend non completa l'autenticazione Laravel. Controllare redirect finale, cookie `laravel_session` e `XSRF-TOKEN`.";
  }
  return null;
}
