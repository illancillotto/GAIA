import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { WikiPage } from "@/features/wiki/WikiPage";
import { WikiWidget } from "@/features/wiki/WikiWidget";

const mocks = vi.hoisted(() => ({
  createWikiRequestWithArtifacts: vi.fn(),
  getStoredAccessToken: vi.fn(),
  captureWikiRequestArtifacts: vi.fn(),
  prepareWikiSupportHref: vi.fn(),
  usePathname: vi.fn(),
  useSearchParams: vi.fn(),
  useWikiChat: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", () => ({
  createWikiRequestWithArtifacts: mocks.createWikiRequestWithArtifacts,
  getMyWikiRequests: vi.fn().mockResolvedValue([]),
  getWikiArticles: vi.fn().mockResolvedValue([
    {
      source_file: "domain-docs/wiki/docs/IMPLEMENTATION_PLAN_wiki_live_agent.md",
      chunks: [{ source_file: "domain-docs/wiki/docs/IMPLEMENTATION_PLAN_wiki_live_agent.md", section_title: "Intro", excerpt: "..." }],
    },
  ]),
}));

vi.mock("next/navigation", () => ({
  usePathname: mocks.usePathname,
  useSearchParams: mocks.useSearchParams,
}));

vi.mock("@/features/wiki/request-support", async () => {
  const actual = await vi.importActual<typeof import("@/features/wiki/request-support")>("@/features/wiki/request-support");
  return {
    ...actual,
    captureWikiRequestArtifacts: mocks.captureWikiRequestArtifacts,
    prepareWikiSupportHref: mocks.prepareWikiSupportHref,
  };
});

vi.mock("@/features/wiki/useWikiChat", () => ({
  useWikiChat: mocks.useWikiChat,
}));

describe("Wiki surfaces", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/catasto");
    mocks.createWikiRequestWithArtifacts.mockReset();
    mocks.getStoredAccessToken.mockReset();
    mocks.captureWikiRequestArtifacts.mockReset();
    mocks.prepareWikiSupportHref.mockReset();
    mocks.usePathname.mockReset();
    mocks.useSearchParams.mockReset();
    mocks.useWikiChat.mockReset();
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
      configurable: true,
      value: vi.fn(),
    });
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.captureWikiRequestArtifacts.mockResolvedValue({ uiSnapshot: { module_snapshot: { module: "catasto" } } });
    mocks.prepareWikiSupportHref.mockResolvedValue("/wiki/support?draft_id=abc");
    mocks.createWikiRequestWithArtifacts.mockResolvedValue({ id: "req-1" });
    mocks.usePathname.mockReturnValue("/catasto");
    mocks.useSearchParams.mockReturnValue(new URLSearchParams());
    mocks.useWikiChat.mockReturnValue({
      messages: [
        {
          id: "assistant-1",
          role: "assistant",
          content: "Risposta denied",
          mode: "live_data",
          found: false,
          tool_calls: [{ tool_name: "find_share_by_name", success: false, redacted: true }],
          evidences: [],
          timestamp: new Date(),
        },
      ],
      conversationId: "conv-1",
      conversations: [],
      loading: false,
      error: null,
      sendMessage: vi.fn(),
      clearMessages: vi.fn(),
      loadConversation: vi.fn(),
      reloadConversations: vi.fn(),
    });
  });

  test("WikiWidget renders denied tool call state", async () => {
    render(<WikiWidget />);

    fireEvent.click(screen.getByLabelText("Apri assistente GAIA"));

    await waitFor(() => {
      expect(screen.getByText("Risposta denied")).toBeInTheDocument();
      expect(screen.getByText("Apri supporto completo")).toBeInTheDocument();
    });
    expect(screen.getByTitle("Apri Wiki completa")).toHaveAttribute("href", "/wiki?conversation=conv-1");
  });

  test("WikiWidget quick request uses createWikiRequestWithArtifacts", async () => {
    render(<WikiWidget />);

    fireEvent.click(screen.getByLabelText("Apri assistente GAIA"));

    await waitFor(() => {
      expect(screen.getByText("Chiedi supporto")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Chiedi supporto"));

    await waitFor(() => {
      expect(mocks.createWikiRequestWithArtifacts).toHaveBeenCalledTimes(1);
    });

    expect(mocks.captureWikiRequestArtifacts).toHaveBeenCalledTimes(1);
    expect(mocks.createWikiRequestWithArtifacts.mock.calls[0]?.[2]).toEqual({
      uiSnapshot: { module_snapshot: { module: "catasto" } },
    });
    expect(screen.getByText("Richiesta registrata. Grazie!")).toBeInTheDocument();
  });

  test("WikiWidget handles quick action variants and full support handoff", async () => {
    const clearMessages = vi.fn();
    mocks.useWikiChat.mockReturnValue({
      messages: [
        {
          id: "assistant-1",
          role: "assistant",
          content: "Risposta da inoltrare",
          mode: "live_data",
          found: false,
          tool_calls: [],
          evidences: [],
          timestamp: new Date(),
        },
      ],
      conversationId: "conv-1",
      conversations: [],
      loading: false,
      error: null,
      sendMessage: vi.fn(),
      clearMessages,
      loadConversation: vi.fn(),
      reloadConversations: vi.fn(),
    });
    mocks.getStoredAccessToken.mockReturnValueOnce(null);
    mocks.prepareWikiSupportHref.mockResolvedValue("#support");

    render(<WikiWidget />);

    fireEvent.click(screen.getByLabelText("Apri assistente GAIA"));
    fireEvent.click(screen.getByText("Chiedi supporto"));
    expect(mocks.createWikiRequestWithArtifacts).not.toHaveBeenCalled();

    fireEvent.click(screen.getByText("Segnala problema"));
    fireEvent.click(screen.getByText("Richiedi funzionalità"));
    fireEvent.click(screen.getByTitle("Nuova conversazione"));
    fireEvent.click(screen.getByText("Apri supporto completo"));

    await waitFor(() => {
      expect(mocks.createWikiRequestWithArtifacts).toHaveBeenCalledTimes(2);
      expect(mocks.prepareWikiSupportHref).toHaveBeenCalledWith(
        expect.objectContaining({
          intent: "help_request",
          assistantAnswer: "Risposta da inoltrare",
        }),
      );
    });
    expect(clearMessages).toHaveBeenCalledTimes(1);
  });

  test("WikiWidget submits user questions and renders loading phases", () => {
    const sendMessage = vi.fn();
    mocks.useWikiChat.mockReturnValue({
      messages: [],
      conversationId: null,
      conversations: [],
      loading: false,
      error: null,
      responsePhase: "idle",
      timeToFirstChunkMs: null,
      sendMessage,
      clearMessages: vi.fn(),
      loadConversation: vi.fn(),
      reloadConversations: vi.fn(),
    });

    render(<WikiWidget />);

    fireEvent.click(screen.getByLabelText("Apri assistente GAIA"));
    expect(screen.getByText("Ciao! Sono l'assistente GAIA.")).toBeInTheDocument();
    expect(screen.getByTitle("Apri Wiki completa")).toHaveAttribute("href", "/wiki");

    const input = screen.getByPlaceholderText("Scrivi una domanda...");
    const form = input.closest("form");
    expect(form).not.toBeNull();

    fireEvent.submit(form as HTMLFormElement);
    expect(sendMessage).not.toHaveBeenCalled();

    fireEvent.change(input, { target: { value: "Come funziona GAIA?" } });
    fireEvent.submit(form as HTMLFormElement);

    expect(sendMessage).toHaveBeenCalledWith("Come funziona GAIA?");
    expect(input).toHaveValue("");
  });

  test.each([
    ["routing", "Instradamento richiesta"],
    ["retrieving_docs", "Ricerca documentazione"],
    ["retrieving_live_data", "Verifica dati live"],
    ["streaming", "Composizione risposta"],
    ["unknown", ""],
  ])("WikiWidget renders loading phase %s", (responsePhase, expectedLabel) => {
    mocks.useWikiChat.mockReturnValue({
      messages: [],
      conversationId: null,
      conversations: [],
      loading: true,
      error: null,
      responsePhase,
      timeToFirstChunkMs: 42,
      sendMessage: vi.fn(),
      clearMessages: vi.fn(),
      loadConversation: vi.fn(),
      reloadConversations: vi.fn(),
    });

    render(<WikiWidget />);

    fireEvent.click(screen.getByLabelText("Apri assistente GAIA"));
    if (expectedLabel) {
      expect(screen.getByText(expectedLabel)).toBeInTheDocument();
    }
    expect(screen.getByText("Primo chunk: 42 ms")).toBeInTheDocument();
  });

  test("WikiWidget renders loading without phase details when no phase is active", () => {
    mocks.useWikiChat.mockReturnValue({
      messages: [],
      conversationId: null,
      conversations: [],
      loading: true,
      error: null,
      responsePhase: "idle",
      timeToFirstChunkMs: null,
      sendMessage: vi.fn(),
      clearMessages: vi.fn(),
      loadConversation: vi.fn(),
      reloadConversations: vi.fn(),
    });

    render(<WikiWidget />);

    fireEvent.click(screen.getByLabelText("Apri assistente GAIA"));
    expect(screen.queryByText(/Primo chunk:/)).not.toBeInTheDocument();
  });

  test("WikiWidget renders user messages, sources and evidences without quick support actions", async () => {
    mocks.useWikiChat.mockReturnValue({
      messages: [
        {
          id: "user-1",
          role: "user",
          content: "Domanda utente",
          timestamp: new Date(),
        },
        {
          id: "assistant-1",
          role: "assistant",
          content: "Risposta con fonti",
          mode: "hybrid",
          found: true,
          sources: [
            {
              source_file: "domain-docs/wiki/docs/RUOLO.md",
              section_title: "Ruolo",
              excerpt: "Estratto",
            },
          ],
          evidences: [
            {
              type: "live_data",
              label: "Cruscotto ruolo",
              source_key: "ruolo.dashboard",
              excerpt: "Totali annuali",
              payload_kind: "ruolo_dashboard_summary",
              payload: { total_importo: 1234.5 },
            },
          ],
          tool_calls: [{ tool_name: "get_ruolo_stats", success: true, redacted: false }],
          timestamp: new Date(),
        },
      ],
      conversationId: "conv-1",
      conversations: [],
      loading: false,
      error: null,
      sendMessage: vi.fn(),
      clearMessages: vi.fn(),
      loadConversation: vi.fn(),
      reloadConversations: vi.fn(),
    });

    render(<WikiWidget />);

    fireEvent.click(screen.getByLabelText("Apri assistente GAIA"));

    expect(screen.getByText("Domanda utente")).toBeInTheDocument();
    expect(screen.getByText("Risposta con fonti")).toBeInTheDocument();
    expect(screen.getByText("Hybrid")).toBeInTheDocument();
    expect(screen.getByText("RUOLO.md")).toBeInTheDocument();
    expect(screen.getByText("Cruscotto ruolo")).toBeInTheDocument();
    expect(screen.getByText("get_ruolo_stats")).toBeInTheDocument();
    expect(screen.queryByText("Apri supporto completo")).not.toBeInTheDocument();
  });

  test("WikiWidget resets the local thread when pathname changes", async () => {
    const clearMessages = vi.fn();
    const unchangedPathClearMessages = vi.fn();
    mocks.useWikiChat.mockReturnValue({
      messages: [
        {
          id: "assistant-1",
          role: "assistant",
          content: "Risposta precedente",
          mode: "docs_only",
          found: true,
          tool_calls: [],
          evidences: [],
          timestamp: new Date(),
        },
      ],
      conversationId: "conv-old",
      conversations: [],
      loading: false,
      error: null,
      sendMessage: vi.fn(),
      clearMessages,
      loadConversation: vi.fn(),
      reloadConversations: vi.fn(),
    });

    const { rerender } = render(<WikiWidget />);

    mocks.useWikiChat.mockReturnValue({
      messages: [
        {
          id: "assistant-1",
          role: "assistant",
          content: "Risposta precedente",
          mode: "docs_only",
          found: true,
          tool_calls: [],
          evidences: [],
          timestamp: new Date(),
        },
      ],
      conversationId: "conv-old",
      conversations: [],
      loading: false,
      error: null,
      sendMessage: vi.fn(),
      clearMessages: unchangedPathClearMessages,
      loadConversation: vi.fn(),
      reloadConversations: vi.fn(),
    });
    rerender(<WikiWidget />);
    expect(clearMessages).not.toHaveBeenCalled();
    expect(unchangedPathClearMessages).not.toHaveBeenCalled();

    mocks.usePathname.mockReturnValue("/catasto/letture-contatori");
    rerender(<WikiWidget />);

    expect(unchangedPathClearMessages).toHaveBeenCalledTimes(1);
  });

  test("WikiWidget stays hidden inside embedded workspaces", () => {
    window.history.replaceState({}, "", "/catasto?embedded=1");

    render(<WikiWidget />);

    expect(screen.queryByLabelText("Apri assistente GAIA")).not.toBeInTheDocument();
  });

  test("WikiPage renders chat shell and assistant metadata", async () => {
    render(<WikiPage />);

    await waitFor(() => {
      expect(screen.getByText("Chat documentale")).toBeInTheDocument();
      expect(screen.getByText("Risposta denied")).toBeInTheDocument();
      expect(screen.getByText("find_share_by_name")).toBeInTheDocument();
      expect(screen.getByText("Apri supporto completo")).toBeInTheDocument();
      expect(screen.getByText("Nessuna conversazione salvata.")).toBeInTheDocument();
    });
  });
});
