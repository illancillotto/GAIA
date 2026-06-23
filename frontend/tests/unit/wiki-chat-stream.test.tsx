import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { parseWikiStreamEventBlock, useWikiChat } from "@/features/wiki/useWikiChat";

const mocks = vi.hoisted(() => ({
  clearStoredAccessToken: vi.fn(),
  getStoredAccessToken: vi.fn(),
  getApiBaseUrl: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  clearStoredAccessToken: mocks.clearStoredAccessToken,
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", () => ({
  getApiBaseUrl: mocks.getApiBaseUrl,
}));

function createStreamResponse(events: string[]) {
  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const event of events) {
        controller.enqueue(encoder.encode(event));
      }
      controller.close();
    },
  });

  return {
    ok: true,
    body,
    headers: { get: () => "text/event-stream" },
    json: async () => ({}),
  };
}

function WikiChatHarness() {
  const { messages, conversationId, loading, responsePhase, timeToFirstChunkMs, sendMessage } = useWikiChat();

  return (
    <div>
      <button type="button" onClick={() => void sendMessage("Cos'è GAIA?")}>
        send
      </button>
      <div data-testid="loading">{loading ? "loading" : "idle"}</div>
      <div data-testid="phase">{responsePhase}</div>
      <div data-testid="ttfc">{timeToFirstChunkMs == null ? "" : String(timeToFirstChunkMs)}</div>
      <div data-testid="conversation">{conversationId ?? ""}</div>
      <div data-testid="messages">
        {messages.map((message) => `${message.role}:${message.content}:${message.mode ?? ""}:${String(message.found)}`).join("|")}
      </div>
    </div>
  );
}

describe("useWikiChat streaming", () => {
  beforeEach(() => {
    mocks.clearStoredAccessToken.mockReset();
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.getApiBaseUrl.mockReturnValue("/api");
    vi.spyOn(performance, "now")
      .mockReturnValueOnce(100)
      .mockReturnValue(160);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  test("parses SSE event blocks produced by the backend", () => {
    const chunk = parseWikiStreamEventBlock(
      'event: meta\ndata: {"event":"meta","data":{"mode":"hybrid","found":true,"conversation_id":"conv-1"}}\n\n',
    );

    expect(chunk).toEqual({
      event: "meta",
      data: {
        mode: "hybrid",
        found: true,
        conversation_id: "conv-1",
      },
    });
  });

  test("streams assistant deltas and preserves conversation id", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url === "/api/wiki/conversations?limit=30") {
          return { ok: true, json: async () => [] };
        }
        if (url === "/api/wiki/chat/stream") {
          return createStreamResponse([
            'event: meta\ndata: {"event":"meta","data":{"mode":"hybrid","found":true,"conversation_id":"conv-stream","sources":[],"evidences":[],"tool_calls":[],"stream_mode":"provider"}}\n\n',
            'event: delta\ndata: {"event":"delta","data":{"text":"GAIA è"}}\n\n',
            'event: delta\ndata: {"event":"delta","data":{"text":"la piattaforma"}}\n\n',
            'event: done\ndata: {"event":"done","data":{"answer":"GAIA è la piattaforma","conversation_id":"conv-stream"}}\n\n',
          ]);
        }
        throw new Error(`Unexpected fetch: ${url}`);
      }),
    );

    render(<WikiChatHarness />);

    fireEvent.click(screen.getByText("send"));

    await waitFor(() => {
      expect(screen.getByTestId("conversation")).toHaveTextContent("conv-stream");
      expect(screen.getByTestId("messages")).toHaveTextContent("assistant:GAIA è la piattaforma:hybrid:true");
      expect(screen.getByTestId("loading")).toHaveTextContent("idle");
      expect(screen.getByTestId("phase")).toHaveTextContent("idle");
      expect(screen.getByTestId("ttfc")).not.toHaveTextContent("");
    });
  });

  test("falls back to synchronous chat when the stream body is unavailable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url === "/api/wiki/conversations?limit=30") {
          return { ok: true, json: async () => [] };
        }
        if (url === "/api/wiki/chat/stream") {
          return { ok: true, body: null, json: async () => ({}) };
        }
        if (url === "/api/wiki/chat") {
          return {
            ok: true,
            json: async () => ({
              answer: "Fallback sincrono",
              sources: [],
              evidences: [],
              tool_calls: [],
              mode: "docs_only",
              found: true,
              conversation_id: "conv-fallback",
            }),
          };
        }
        throw new Error(`Unexpected fetch: ${url}`);
      }),
    );

    render(<WikiChatHarness />);

    fireEvent.click(screen.getByText("send"));

    await waitFor(() => {
      expect(screen.getByTestId("conversation")).toHaveTextContent("conv-fallback");
      expect(screen.getByTestId("messages")).toHaveTextContent("assistant:Fallback sincrono:docs_only:true");
      expect(screen.getByTestId("loading")).toHaveTextContent("idle");
      expect(screen.getByTestId("phase")).toHaveTextContent("idle");
      expect(screen.getByTestId("ttfc")).not.toHaveTextContent("");
    });
  });

  test("clears stored token on wiki auth error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url === "/api/wiki/conversations?limit=30") {
          return { ok: true, json: async () => [] };
        }
        if (url === "/api/wiki/chat/stream") {
          return {
            ok: false,
            status: 401,
            body: null,
            json: async () => ({ detail: "Sessione scaduta o non valida. Effettua di nuovo l'accesso." }),
          };
        }
        throw new Error(`Unexpected fetch: ${url}`);
      }),
    );

    render(<WikiChatHarness />);

    fireEvent.click(screen.getByText("send"));

    await waitFor(() => {
      expect(screen.getByTestId("messages")).toHaveTextContent("assistant:Si è verificato un errore: Sessione scaduta o non valida. Effettua di nuovo l'accesso.");
    });

    expect(mocks.clearStoredAccessToken).toHaveBeenCalledTimes(1);
  });
});
