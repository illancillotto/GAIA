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
  });

  test("WikiWidget resets the local thread when pathname changes", async () => {
    const clearMessages = vi.fn();
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

    rerender(<WikiWidget />);
    expect(clearMessages).not.toHaveBeenCalled();

    mocks.usePathname.mockReturnValue("/catasto/letture-contatori");
    rerender(<WikiWidget />);

    expect(clearMessages).toHaveBeenCalledTimes(1);
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
