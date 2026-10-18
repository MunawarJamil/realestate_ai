/**
 * HTTP and SSE Client for the RealEstate AI Public Widget API
 */

import { ChatMessage, ConversationRead, VisitorSession } from './types';

export class WidgetApiClient {
  private apiUrl: string;
  private widgetKey: string;

  constructor(apiUrl: string, widgetKey: string) {
    this.apiUrl = apiUrl.replace(/\/+$/, '');
    this.widgetKey = widgetKey;
  }

  /**
   * Initializes or resumes a visitor session with public widget key
   */
  public async initSession(requestedVisitorId?: string | null): Promise<VisitorSession> {
    const res = await fetch(`${this.apiUrl}/api/v1/widget/session`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Widget-Key': this.widgetKey,
      },
      body: JSON.stringify(requestedVisitorId ? { visitor_id: requestedVisitorId } : {}),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to initialize session' }));
      throw new Error(err.detail || `Session init failed with status ${res.status}`);
    }

    return res.json();
  }

  /**
   * Creates a new conversation for this visitor
   */
  public async createConversation(token: string, title?: string): Promise<ConversationRead> {
    const res = await fetch(`${this.apiUrl}/api/v1/widget/conversations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ title: title || 'Website Inquiry' }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to create conversation' }));
      throw new Error(err.detail || `Create conversation failed with status ${res.status}`);
    }

    return res.json();
  }

  /**
   * Fetches message history for an existing conversation
   */
  public async listMessages(token: string, conversationId: string): Promise<ChatMessage[]> {
    const res = await fetch(
      `${this.apiUrl}/api/v1/widget/conversations/${conversationId}/messages`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    if (!res.ok) {
      return [];
    }

    return res.json();
  }

  /**
   * Streams chat completion tokens via Server-Sent Events (SSE)
   */
  public streamChat(
    token: string,
    conversationId: string,
    message: string,
    onToken: (token: string) => void,
    onDone: () => void,
    onError: (err: Error) => void
  ): AbortController {
    const controller = new AbortController();

    (async () => {
      try {
        const response = await fetch(
          `${this.apiUrl}/api/v1/widget/conversations/${conversationId}/stream`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ content: message }),
            signal: controller.signal,
          }
        );

        if (!response.ok) {
          const errData = await response.json().catch(() => ({ detail: 'Stream request failed' }));
          throw new Error(errData.detail || `Stream failed with HTTP ${response.status}`);
        }

        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error('Response body stream is not available');
        }

        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split('\n\n');
          buffer = parts.pop() || '';

          for (const part of parts) {
            const trimmed = part.trim();
            if (!trimmed) continue;

            const lines = trimmed.split('\n');
            let eventType = 'message';
            let data = '';

            for (const line of lines) {
              if (line.startsWith('event: ')) {
                eventType = line.substring(7).trim();
              } else if (line.startsWith('data: ')) {
                data = line.substring(6).trim();
              }
            }

            if (eventType === 'error') {
              throw new Error(data || 'Stream error occurred');
            }

            if (data === '[DONE]') {
              onDone();
              return;
            }

            if (data) {
              try {
                const parsed = JSON.parse(data);
                if (parsed.token) {
                  onToken(parsed.token);
                }
              } catch {
                // Raw string token
                onToken(data);
              }
            }
          }
        }

        onDone();
      } catch (err: unknown) {
        if (controller.signal.aborted) {
          return;
        }
        onError(err instanceof Error ? err : new Error(String(err)));
      }
    })();

    return controller;
  }
}
