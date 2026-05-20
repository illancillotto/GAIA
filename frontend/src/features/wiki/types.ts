export interface WikiChunkSource {
  source_file: string;
  section_title: string | null;
  excerpt: string;
}

export interface WikiChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: WikiChunkSource[];
  found?: boolean;
  timestamp: Date;
}

export interface WikiChatRequest {
  question: string;
  context_article?: string;
}

export interface WikiChatResponse {
  answer: string;
  sources: WikiChunkSource[];
  found: boolean;
}

export interface WikiArticleSummary {
  source_file: string;
  section_title: string | null;
  excerpt: string;
  chunk_index: number;
}

export interface WikiArticleGroup {
  source_file: string;
  chunks: WikiArticleSummary[];
}

export interface WikiRequestCreate {
  user_question: string;
  agent_response?: string;
  category: "feature_request" | "bug_report" | "question";
}

export interface WikiRequest {
  id: string;
  user_question: string;
  agent_response: string | null;
  category: string;
  status: "pending" | "reviewed" | "planned" | "done";
  created_by: string | null;
  admin_notes: string | null;
  created_at: string;
  updated_at: string;
}
