import { useAuthStore } from '../store/useAuthStore';
import type {
  TenantRead,
  TenantCreated,
  TenantCreatePayload,
  TenantUpdatePayload,
} from '../types/tenant';

export class ApiError extends Error {
  status: number;
  details?: unknown;

  constructor(status: number, message: string, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

export interface BackendKnowledgeDoc {
  id: string;
  tenant_id: string;
  filename: string;
  title: string | null;
  content_type: string;
  file_size_bytes: number;
  status: 'pending' | 'processing' | 'ready' | 'failed';
  error_message?: string | null;
  chunk_count: number;
  created_at: string;
  updated_at: string;
}

export interface BackendKnowledgeList {
  items: BackendKnowledgeDoc[];
  total: number;
  limit: number;
  offset: number;
}

export interface BackendSearchResult {
  id: string;
  document_id: string;
  content: string;
  score: number;
  metadata: Record<string, unknown>;
}

export interface BackendConversation {
  id: string;
  tenant_id: string;
  title: string;
  status: 'ai' | 'handoff_requested' | 'human_active' | 'resolved'; // # 12b HITL
  assigned_agent_id?: string | null; // # 12b HITL
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface BackendConversationList {
  items: BackendConversation[];
  total: number;
}

export interface BackendMessage {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  sender_type?: 'visitor' | 'ai' | 'agent' | 'system'; // # 12b HITL
  agent_id?: string | null; // # 12b HITL
  content: string;
  created_at: string;
}

export interface BackendConversationSummary {
  conversation_id: string;
  summary: string;
  key_intent?: string | null;
  budget?: string | null;
  preferred_location?: string | null;
}

export interface UserRead {
  id: string;
  email: string;
  full_name: string;
  role: 'super_admin' | 'agency_admin' | 'agent';
  tenant_id?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthResponse {
  tokens: TokenResponse;
  user: UserRead;
  tenant_name?: string | null;
  tenant_slug?: string | null;
}

export interface LoginPayload {
  email: string;
  password: string;
  tenant_slug?: string;
}

export interface PlatformLoginPayload {
  email: string;
  password: string;
}

export interface UserCreatePayload {
  email: string;
  password: string;
  full_name: string;
  role: 'agency_admin' | 'agent';
}

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '');

type AuthType = 'admin' | 'agency' | 'bearer' | 'none';

interface RequestOptions extends RequestInit {
  auth?: AuthType;
  params?: Record<string, string | number | boolean | undefined | null>;
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { auth = 'none', params, headers = {}, ...customConfig } = options;

  let url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  if (params) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null) {
        query.append(key, String(val));
      }
    });
    const queryString = query.toString();
    if (queryString) {
      url += (url.includes('?') ? '&' : '?') + queryString;
    }
  }

  const reqHeaders: Record<string, string> = {
    ...(headers as Record<string, string>),
  };

  if (!(customConfig.body instanceof FormData) && !reqHeaders['Content-Type']) {
    reqHeaders['Content-Type'] = 'application/json';
  }

  // Dynamic Auth Header Injection (supports JWT Bearer and API Key fallbacks)
  const authState = useAuthStore.getState();
  if (auth === 'admin') {
    if (authState.platformToken) {
      reqHeaders['Authorization'] = `Bearer ${authState.platformToken}`;
    } else if (authState.adminKey) {
      reqHeaders['X-Admin-Key'] = authState.adminKey;
    }
  } else if (auth === 'agency') {
    if (authState.agencyToken) {
      reqHeaders['Authorization'] = `Bearer ${authState.agencyToken}`;
    } else if (authState.apiKey) {
      reqHeaders['X-API-Key'] = authState.apiKey;
    }
  } else if (auth === 'bearer') {
    const token = authState.platformToken || authState.agencyToken;
    if (token) {
      reqHeaders['Authorization'] = `Bearer ${token}`;
    }
  }

  const response = await fetch(url, {
    ...customConfig,
    headers: reqHeaders,
  });

  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    let rawError: unknown = null;
    try {
      const errJson = await response.json();
      rawError = errJson;
      if (typeof errJson.detail === 'string') {
        errorDetail = errJson.detail;
      } else if (Array.isArray(errJson.detail)) {
        errorDetail = errJson.detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join('; ');
      } else if (errJson.detail?.message) {
        errorDetail = errJson.detail.message;
      } else if (errJson.message) {
        errorDetail = errJson.message;
      }
    } catch {
      // Non-JSON error body fallback
    }

    throw new ApiError(response.status, errorDetail, rawError);
  }

  if (response.status === 204) {
    return null as T;
  }

  return response.json() as Promise<T>;
}

export const apiClient = {
  // --- Platform / Super Admin Endpoints ---
  admin: {
    async listTenants(params?: {
      limit?: number;
      offset?: number;
      is_active?: boolean;
    }): Promise<TenantRead[]> {
      return request<TenantRead[]>('/api/v1/tenants', {
        auth: 'admin',
        params,
      });
    },

    async createTenant(payload: TenantCreatePayload): Promise<TenantCreated> {
      return request<TenantCreated>('/api/v1/tenants', {
        method: 'POST',
        auth: 'admin',
        body: JSON.stringify(payload),
      });
    },

    async updateTenant(
      tenantId: string,
      payload: TenantUpdatePayload
    ): Promise<TenantRead> {
      return request<TenantRead>(`/api/v1/tenants/${tenantId}`, {
        method: 'PATCH',
        auth: 'admin',
        body: JSON.stringify(payload),
      });
    },

    async getHealth(): Promise<{ status: string }> {
      return request<{ status: string }>('/health', {
        auth: 'none',
      });
    },
  },

  // --- Agency Workspace Endpoints ---
  agency: {
    async getMe(): Promise<TenantRead> {
      return request<TenantRead>('/api/v1/tenants/me', {
        auth: 'agency',
      });
    },

    // Knowledge base
    async listDocuments(params?: {
      limit?: number;
      offset?: number;
      status?: string;
    }): Promise<BackendKnowledgeList> {
      return request<BackendKnowledgeList>('/api/v1/knowledge/documents', {
        auth: 'agency',
        params,
      });
    },

    async uploadDocument(file: File, title?: string): Promise<BackendKnowledgeDoc> {
      const formData = new FormData();
      formData.append('file', file);
      if (title) {
        formData.append('title', title);
      }

      return request<BackendKnowledgeDoc>('/api/v1/knowledge/documents', {
        method: 'POST',
        auth: 'agency',
        body: formData,
      });
    },

    async deleteDocument(documentId: string): Promise<null> {
      return request<null>(`/api/v1/knowledge/documents/${documentId}`, {
        method: 'DELETE',
        auth: 'agency',
      });
    },

    async searchKnowledge(
      query: string,
      limit = 5
    ): Promise<{ results: BackendSearchResult[] }> {
      return request<{ results: BackendSearchResult[] }>('/api/v1/knowledge/search', {
        method: 'POST',
        auth: 'agency',
        body: JSON.stringify({ query, limit }),
      });
    },

    // Conversations & Chat
    async listConversations(params?: {
      limit?: number;
      offset?: number;
    }): Promise<BackendConversationList> {
      return request<BackendConversationList>('/api/v1/chat/conversations', {
        auth: 'agency',
        params,
      });
    },

    async getConversation(id: string): Promise<BackendConversation> {
      return request<BackendConversation>(`/api/v1/chat/conversations/${id}`, {
        auth: 'agency',
      });
    },

    async createConversation(payload: {
      title?: string;
      metadata?: Record<string, unknown>;
    }): Promise<BackendConversation> {
      return request<BackendConversation>('/api/v1/chat/conversations', {
        method: 'POST',
        auth: 'agency',
        body: JSON.stringify(payload),
      });
    },

    async listMessages(
      conversationId: string,
      params?: { limit?: number; offset?: number }
    ): Promise<BackendMessage[]> {
      return request<BackendMessage[]>(
        `/api/v1/chat/conversations/${conversationId}/messages`,
        {
          auth: 'agency',
          params,
        }
      );
    },

    async sendMessage(
      conversationId: string,
      content: string
    ): Promise<BackendMessage> {
      return request<BackendMessage>(
        `/api/v1/chat/conversations/${conversationId}/messages`,
        {
          method: 'POST',
          auth: 'agency',
          body: JSON.stringify({ content }),
        }
      );
    },

    // # 12b HITL - Agent Claim, Release, Resolve & AI Summary
    async claimConversation(conversationId: string): Promise<BackendConversation> {
      return request<BackendConversation>(
        `/api/v1/chat/conversations/${conversationId}/claim`,
        {
          method: 'POST',
          auth: 'agency',
        }
      );
    },

    async releaseConversation(conversationId: string): Promise<BackendConversation> {
      return request<BackendConversation>(
        `/api/v1/chat/conversations/${conversationId}/release`,
        {
          method: 'POST',
          auth: 'agency',
        }
      );
    },

    async resolveConversation(conversationId: string): Promise<BackendConversation> {
      return request<BackendConversation>(
        `/api/v1/chat/conversations/${conversationId}/resolve`,
        {
          method: 'POST',
          auth: 'agency',
        }
      );
    },

    async getConversationSummary(conversationId: string): Promise<BackendConversationSummary> {
      return request<BackendConversationSummary>(
        `/api/v1/chat/conversations/${conversationId}/summary`,
        {
          auth: 'agency',
        }
      );
    },

    // Real-time SSE Stream Reader
    async streamMessage(
      conversationId: string,
      content: string,
      callbacks: {
        onToken: (token: string) => void;
        onDone?: () => void;
        onError?: (error: Error) => void;
        signal?: AbortSignal;
      }
    ): Promise<void> {
      const authState = useAuthStore.getState();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (authState.agencyToken) {
        headers['Authorization'] = `Bearer ${authState.agencyToken}`;
      } else if (authState.apiKey) {
        headers['X-API-Key'] = authState.apiKey;
      }

      const response = await fetch(
        `${API_BASE_URL}/api/v1/chat/conversations/${conversationId}/stream`,
        {
          method: 'POST',
          headers,
          body: JSON.stringify({ content }),
          signal: callbacks.signal,
        }
      );

      if (!response.ok) {
        let errMessage = `Streaming failed (${response.status})`;
        try {
          const errJson = await response.json();
          if (errJson.detail) errMessage = errJson.detail;
        } catch {
          // ignore
        }
        const err = new ApiError(response.status, errMessage);
        callbacks.onError?.(err);
        throw err;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        const err = new Error('No readable stream available in response');
        callbacks.onError?.(err);
        throw err;
      }

      const decoder = new TextDecoder();
      let buffer = '';

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() ?? '';

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || trimmed.startsWith(':')) continue;

            if (trimmed.startsWith('data: ')) {
              const dataStr = trimmed.slice(6);
              if (dataStr === '[DONE]') {
                callbacks.onDone?.();
                return;
              }

              try {
                const parsed = JSON.parse(dataStr);
                if (parsed.token) {
                  callbacks.onToken(parsed.token);
                } else if (parsed.error) {
                  callbacks.onError?.(new Error(parsed.error));
                }
              } catch {
                // partial or unparseable line
              }
            } else if (trimmed.startsWith('event: error')) {
              // Next data line will contain the error payload
            }
          }
        }
        callbacks.onDone?.();
      } catch (err: unknown) {
        if ((err as Error).name !== 'AbortError') {
          callbacks.onError?.(err as Error);
        }
      } finally {
        reader.releaseLock();
      }
    },
  },

  auth: {
    login: (payload: LoginPayload) =>
      request<AuthResponse>('/api/v1/auth/login', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),

    platformLogin: (payload: PlatformLoginPayload) =>
      request<AuthResponse>('/api/v1/auth/platform/login', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),

    refreshToken: (refreshToken: string, audience: 'platform' | 'agency' = 'agency') =>
      request<TokenResponse>(`/api/v1/auth/refresh?audience=${audience}`, {
        method: 'POST',
        body: JSON.stringify({ refresh_token: refreshToken }),
      }),

    getMe: () =>
      request<UserRead>('/api/v1/auth/me', {
        method: 'GET',
        auth: 'bearer',
      }),

    getAgencyUsers: (params?: { limit?: number; offset?: number }) =>
      request<UserRead[]>('/api/v1/auth/users', {
        method: 'GET',
        auth: 'agency',
        params,
      }),

    createAgencyUser: (payload: UserCreatePayload) =>
      request<UserRead>('/api/v1/auth/users', {
        method: 'POST',
        auth: 'agency',
        body: JSON.stringify(payload),
      }),
  },
};
