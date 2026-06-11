"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { getStoredAccessToken } from "@/lib/auth";
import { getApiBaseUrl, getWikiConversationDetail, getWikiConversations } from "@/lib/api";
import { generateUuid } from "@/lib/uuid";
import type {
  WikiChatMessage,
  WikiChatResponse,
  WikiChatResponsePhase,
  WikiChatStreamChunk,
  WikiConversation,
  WikiConversationSummary,
} from "./types";

class WikiStreamUnavailableError extends Error {
  constructor(message = "Streaming Wiki non disponibile") {
    super(message);
    this.name = "WikiStreamUnavailableError";
  }
}

function getWikiApiPath(path: string): string {
  return `${getApiBaseUrl()}${path}`;
}

function getWikiAuthHeaders(): HeadersInit {
  const token = getStoredAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function parseWikiErrorMessage(payload: unknown, fallback: string): string {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === "string") {
      return detail;
    }
  }
  return fallback;
}

export function parseWikiStreamEventBlock(block: string): WikiChatStreamChunk | null {
  const lines = block
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  if (lines.length === 0) {
    return null;
  }

  let declaredEvent: WikiChatStreamChunk["event"] | null = null;
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      const value = line.slice("event:".length).trim();
      if (value === "meta" || value === "delta" || value === "done" || value === "error") {
        declaredEvent = value;
      }
      continue;
    }
    if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trim());
    }
  }

  if (dataLines.length === 0) {
    return null;
  }

  const rawPayload = JSON.parse(dataLines.join("\n")) as Partial<WikiChatStreamChunk> | Record<string, unknown>;
  if (
    rawPayload &&
    typeof rawPayload === "object" &&
    "event" in rawPayload &&
    "data" in rawPayload &&
    (rawPayload.event === "meta" || rawPayload.event === "delta" || rawPayload.event === "done" || rawPayload.event === "error")
  ) {
    return rawPayload as WikiChatStreamChunk;
  }

  if (!declaredEvent) {
    return null;
  }

  return {
    event: declaredEvent,
    data: rawPayload as WikiChatStreamChunk["data"],
  };
}

async function fetchWikiChat(
  question: string,
  context_article?: string,
  conversation_id?: string | null,
  signal?: AbortSignal,
): Promise<WikiChatResponse> {
  const res = await fetch(getWikiApiPath("/wiki/chat"), {
    method: "POST",
    signal,
    headers: {
      "Content-Type": "application/json",
      ...getWikiAuthHeaders(),
    },
    body: JSON.stringify({ question, context_article, conversation_id }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(parseWikiErrorMessage(err, `Errore ${res.status}`));
  }

  return res.json();
}

async function streamWikiChat(
  question: string,
  context_article: string | undefined,
  conversation_id: string | null | undefined,
  onChunk: (chunk: WikiChatStreamChunk) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(getWikiApiPath("/wiki/chat/stream"), {
    method: "POST",
    signal,
    headers: {
      "Content-Type": "application/json",
      ...getWikiAuthHeaders(),
    },
    body: JSON.stringify({ question, context_article, conversation_id }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(parseWikiErrorMessage(err, `Errore ${res.status}`));
  }

  if (!res.body) {
    throw new WikiStreamUnavailableError();
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let hasChunks = false;

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split(/\n\n/);
    buffer = events.pop() ?? "";

    for (const eventBlock of events) {
      const chunk = parseWikiStreamEventBlock(eventBlock);
      if (!chunk) {
        continue;
      }
      hasChunks = true;
      onChunk(chunk);
      if (chunk.event === "error") {
        throw new Error(chunk.data.detail ?? "Errore stream Wiki");
      }
    }
  }

  buffer += decoder.decode();
  const trailingChunk = parseWikiStreamEventBlock(buffer);
  if (trailingChunk) {
    hasChunks = true;
    onChunk(trailingChunk);
    if (trailingChunk.event === "error") {
      throw new Error(trailingChunk.data.detail ?? "Errore stream Wiki");
    }
  }

  if (!hasChunks) {
    throw new WikiStreamUnavailableError();
  }
}

async function fetchWikiConversation(conversationId: string): Promise<WikiConversation> {
  const token = getStoredAccessToken();
  if (!token) {
    throw new Error("Sessione non disponibile.");
  }
  return getWikiConversationDetail(token, conversationId);
}

async function fetchWikiConversations(params: {
  limit?: number;
  search?: string | null;
  created_by?: string | null;
  context_article?: string | null;
} = {}): Promise<WikiConversationSummary[]> {
  const token = getStoredAccessToken();
  if (!token) {
    throw new Error("Sessione non disponibile.");
  }
  return getWikiConversations(token, {
    limit: params.limit ?? 30,
    search: params.search ?? null,
    createdBy: params.created_by ?? null,
    contextArticle: params.context_article ?? null,
  });
}

function toUiMessage(message: WikiConversation["messages"][number]): WikiChatMessage {
  return {
    id: message.id,
    role: message.role,
    content: message.content,
    sources: message.sources,
    evidences: message.evidences,
    tool_calls: message.tool_calls,
    mode: message.mode ?? undefined,
    found: message.found ?? undefined,
    timestamp: new Date(message.created_at),
  };
}

export function useWikiChat(contextArticle?: string, initialConversationId?: string | null) {
  const [messages, setMessages] = useState<WikiChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(initialConversationId ?? null);
  const [conversations, setConversations] = useState<WikiConversationSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [responsePhase, setResponsePhase] = useState<WikiChatResponsePhase>("idle");
  const [timeToFirstChunkMs, setTimeToFirstChunkMs] = useState<number | null>(null);
  const activeStreamControllerRef = useRef<AbortController | null>(null);

  const measureFirstChunk = useCallback((startedAt: number) => {
    const endedAt = performance.now();
    setTimeToFirstChunkMs(Math.max(Math.round(endedAt - startedAt), 0));
    try {
      performance.measure("wiki-chat:first-chunk", { start: startedAt, end: endedAt });
    } catch {
      // Ignore unsupported measure signatures in older environments.
    }
  }, []);

  const cancelActiveStream = useCallback(() => {
    activeStreamControllerRef.current?.abort();
    activeStreamControllerRef.current = null;
  }, []);

  const reloadConversations = useCallback(async (params?: {
    search?: string | null;
    created_by?: string | null;
    context_article?: string | null;
    limit?: number;
  }) => {
    try {
      const items = await fetchWikiConversations(params);
      setConversations(items);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Errore caricamento conversazioni Wiki";
      setError(message);
    }
  }, []);

  const loadConversation = useCallback(async (targetConversationId: string) => {
    cancelActiveStream();
    setLoading(true);
    setError(null);
    setResponsePhase("idle");
    try {
      const conversation = await fetchWikiConversation(targetConversationId);
      setConversationId(conversation.id);
      setMessages(conversation.messages.map(toUiMessage));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Errore sconosciuto";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [cancelActiveStream]);

  useEffect(() => {
    void reloadConversations();
  }, [reloadConversations]);

  useEffect(() => {
    return () => {
      cancelActiveStream();
    };
  }, [cancelActiveStream]);

  useEffect(() => {
    if (initialConversationId) {
      void loadConversation(initialConversationId);
    }
  }, [initialConversationId, loadConversation]);

  const sendMessage = useCallback(
    async (question: string) => {
      if (!question.trim() || loading) return;
      cancelActiveStream();

      const userMsg: WikiChatMessage = {
        id: generateUuid(),
        role: "user",
        content: question.trim(),
        timestamp: new Date(),
      };
      const assistantMessageId = generateUuid();
      const assistantTimestamp = new Date();

      setMessages((prev) => [
        ...prev,
        userMsg,
        {
          id: assistantMessageId,
          role: "assistant",
          content: "",
          conversationId: conversationId ?? null,
          timestamp: assistantTimestamp,
        },
      ]);
      setLoading(true);
      setError(null);
      setResponsePhase("routing");
      setTimeToFirstChunkMs(null);

      try {
        const streamController = new AbortController();
        const startedAt = performance.now();
        let firstChunkCaptured = false;
        activeStreamControllerRef.current = streamController;

        const patchAssistant = (patch: Partial<WikiChatMessage> | ((message: WikiChatMessage) => WikiChatMessage)) => {
          setMessages((prev) =>
            prev.map((message) => {
              if (message.id !== assistantMessageId) {
                return message;
              }
              if (typeof patch === "function") {
                return patch(message);
              }
              return { ...message, ...patch };
            }),
          );
        };

        try {
          await streamWikiChat(question.trim(), contextArticle, conversationId, (chunk) => {
            if (streamController.signal.aborted) {
              return;
            }
            if (!firstChunkCaptured && (chunk.event === "meta" || chunk.event === "delta")) {
              firstChunkCaptured = true;
              measureFirstChunk(startedAt);
            }
            if (chunk.event === "meta") {
              if (chunk.data.stream_mode === "provider") {
                setResponsePhase("streaming");
              } else if (chunk.data.mode === "docs_only") {
                setResponsePhase("retrieving_docs");
              } else if (chunk.data.mode === "live_data" || chunk.data.mode === "logic" || chunk.data.mode === "hybrid") {
                setResponsePhase("retrieving_live_data");
              }
              patchAssistant({
                mode: chunk.data.mode,
                found: chunk.data.found,
                sources: chunk.data.sources,
                evidences: chunk.data.evidences,
                tool_calls: chunk.data.tool_calls,
                conversationId: chunk.data.conversation_id ?? conversationId ?? null,
              });
              if (chunk.data.conversation_id) {
                setConversationId(chunk.data.conversation_id);
              }
              return;
            }

            if (chunk.event === "delta") {
              setResponsePhase("streaming");
              patchAssistant((message) => ({
                ...message,
                content: message.content ? `${message.content} ${chunk.data.text ?? ""}`.trim() : (chunk.data.text ?? ""),
              }));
              return;
            }

            if (chunk.event === "done") {
              setResponsePhase("idle");
              patchAssistant((message) => ({
                ...message,
                content: chunk.data.answer ?? message.content,
                conversationId: chunk.data.conversation_id ?? message.conversationId ?? conversationId ?? null,
              }));
              if (chunk.data.conversation_id) {
                setConversationId(chunk.data.conversation_id);
              }
            }
          }, streamController.signal);
        } catch (streamError) {
          if (streamController.signal.aborted) {
            return;
          }
          if (!(streamError instanceof WikiStreamUnavailableError)) {
            throw streamError;
          }

          setResponsePhase("retrieving_docs");
          const response = await fetchWikiChat(question.trim(), contextArticle, conversationId, streamController.signal);
          if (streamController.signal.aborted) {
            return;
          }
          if (!firstChunkCaptured) {
            firstChunkCaptured = true;
            measureFirstChunk(startedAt);
          }
          patchAssistant({
            content: response.answer,
            sources: response.sources,
            evidences: response.evidences,
            tool_calls: response.tool_calls,
            mode: response.mode,
            found: response.found,
            conversationId: response.conversation_id ?? conversationId ?? null,
          });
          if (response.conversation_id) {
            setConversationId(response.conversation_id);
          }
          setResponsePhase("idle");
        }
        void reloadConversations();
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          return;
        }
        const message = err instanceof Error ? err.message : "Errore sconosciuto";
        setError(message);
        setMessages((prev) =>
          prev.map((chatMessage) =>
            chatMessage.id === assistantMessageId
              ? {
                  ...chatMessage,
                  content: `Si è verificato un errore: ${message}`,
                  found: false,
                }
              : chatMessage,
          ),
        );
        setResponsePhase("idle");
      } finally {
        activeStreamControllerRef.current = null;
        setLoading(false);
      }
    },
    [cancelActiveStream, contextArticle, conversationId, loading, reloadConversations]
  );

  const clearMessages = useCallback(() => {
    cancelActiveStream();
    setMessages([]);
    setConversationId(null);
    setError(null);
    setResponsePhase("idle");
    setTimeToFirstChunkMs(null);
  }, [cancelActiveStream]);

  return {
    messages,
    conversationId,
    conversations,
    loading,
    error,
    responsePhase,
    timeToFirstChunkMs,
    sendMessage,
    clearMessages,
    loadConversation,
    reloadConversations,
  };
}
