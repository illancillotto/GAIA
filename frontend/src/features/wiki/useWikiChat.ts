"use client";

import { useCallback, useEffect, useState } from "react";

import { getStoredAccessToken } from "@/lib/auth";
import { generateUuid } from "@/lib/uuid";
import type { WikiChatMessage, WikiChatResponse, WikiConversation, WikiConversationSummary } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

async function fetchWikiChat(
  question: string,
  context_article?: string,
  conversation_id?: string | null,
): Promise<WikiChatResponse> {
  const token = getStoredAccessToken();
  const res = await fetch(`${API_BASE}/api/wiki/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ question, context_article, conversation_id }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Errore ${res.status}`);
  }

  return res.json();
}

async function fetchWikiConversation(conversationId: string): Promise<WikiConversation> {
  const token = getStoredAccessToken();
  const res = await fetch(`${API_BASE}/api/wiki/conversations/${conversationId}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Errore ${res.status}`);
  }
  return res.json();
}

async function fetchWikiConversations(params: {
  limit?: number;
  search?: string | null;
  created_by?: string | null;
  context_article?: string | null;
} = {}): Promise<WikiConversationSummary[]> {
  const token = getStoredAccessToken();
  const query = new URLSearchParams();
  query.set("limit", String(params.limit ?? 30));
  if (params.search) {
    query.set("search", params.search);
  }
  if (params.created_by) {
    query.set("created_by", params.created_by);
  }
  if (params.context_article) {
    query.set("context_article", params.context_article);
  }
  const res = await fetch(`${API_BASE}/api/wiki/conversations?${query.toString()}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    return [];
  }
  return res.json();
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

  const reloadConversations = useCallback(async (params?: {
    search?: string | null;
    created_by?: string | null;
    context_article?: string | null;
    limit?: number;
  }) => {
    const items = await fetchWikiConversations(params);
    setConversations(items);
  }, []);

  const loadConversation = useCallback(async (targetConversationId: string) => {
    setLoading(true);
    setError(null);
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
  }, []);

  useEffect(() => {
    void reloadConversations();
  }, [reloadConversations]);

  useEffect(() => {
    if (initialConversationId) {
      void loadConversation(initialConversationId);
    }
  }, [initialConversationId, loadConversation]);

  const sendMessage = useCallback(
    async (question: string) => {
      if (!question.trim() || loading) return;

      const userMsg: WikiChatMessage = {
        id: generateUuid(),
        role: "user",
        content: question.trim(),
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMsg]);
      setLoading(true);
      setError(null);

      try {
        const response = await fetchWikiChat(question.trim(), contextArticle, conversationId);

        const assistantMsg: WikiChatMessage = {
          id: generateUuid(),
          role: "assistant",
          content: response.answer,
          sources: response.sources,
          evidences: response.evidences,
          tool_calls: response.tool_calls,
          mode: response.mode,
          found: response.found,
          conversationId: response.conversation_id ?? conversationId ?? null,
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, assistantMsg]);
        if (response.conversation_id) {
          setConversationId(response.conversation_id);
        }
        void reloadConversations();
      } catch (err) {
        const message = err instanceof Error ? err.message : "Errore sconosciuto";
        setError(message);
        setMessages((prev) => [
          ...prev,
          {
            id: generateUuid(),
            role: "assistant",
            content: `Si è verificato un errore: ${message}`,
            found: false,
            timestamp: new Date(),
          },
        ]);
      } finally {
        setLoading(false);
      }
    },
    [contextArticle, conversationId, loading, reloadConversations]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    setError(null);
  }, []);

  return {
    messages,
    conversationId,
    conversations,
    loading,
    error,
    sendMessage,
    clearMessages,
    loadConversation,
    reloadConversations,
  };
}
