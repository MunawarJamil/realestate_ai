import { useAuthStore } from '../store/useAuthStore';
import type { BackendMessage } from './client';

export interface AgentWSCallbacks {
  onHandoffAlert?: (alert: { conversation_id: string; title?: string; snippet: string }) => void;
  onStatusChange?: (data: { conversation_id: string; status: string; assigned_agent_id?: string | null }) => void;
  onMessage?: (msg: BackendMessage) => void;
  onError?: (err: Error) => void;
  onConnected?: () => void;
  onDisconnected?: () => void;
}

export class AgentWebSocketClient {
  private ws: WebSocket | null = null;
  private pingInterval: ReturnType<typeof setInterval> | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private isExplicitlyClosed = false;
  private callbacks: AgentWSCallbacks;

  constructor(callbacks: AgentWSCallbacks) {
    this.callbacks = callbacks;
  }

  private getUrl(): string | null {
    const token = useAuthStore.getState().agencyToken;
    if (!token) return null;

    const baseApi = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '');
    const parsed = new URL(baseApi);
    const protocol = parsed.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${parsed.host}/api/v1/chat/ws/agent?token=${encodeURIComponent(token)}`;
  }

  public connect(): void {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const wsUrl = this.getUrl();
    if (!wsUrl) {
      console.warn('[RealEstateAI Agent WS] Missing agency auth token, skipping connection.');
      return;
    }

    this.isExplicitlyClosed = false;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.startHeartbeat();
        this.callbacks.onConnected?.();
      };

      this.ws.onmessage = (event: MessageEvent) => {
        try {
          const frame = JSON.parse(event.data);
          const eventType = frame.event;
          const payload = frame.payload || {};

          switch (eventType) {
            case 'handoff_request':
              this.callbacks.onHandoffAlert?.({
                conversation_id: frame.conversation_id || payload.conversation_id,
                title: payload.title,
                snippet: payload.snippet || 'Visitor requested human assistance.',
              });
              break;

            case 'status_change':
              this.callbacks.onStatusChange?.({
                conversation_id: frame.conversation_id || payload.conversation_id,
                status: payload.status,
                assigned_agent_id: payload.assigned_agent_id,
              });
              break;

            case 'message': {
              const content = payload.content || payload.buyer_message || '';
              const role = payload.role || (payload.sender_type === 'visitor' ? 'user' : payload.sender_type === 'agent' ? 'agent' : 'user');
              const msg: BackendMessage = {
                id: payload.id || `msg_${Date.now()}`,
                conversation_id: frame.conversation_id || payload.conversation_id,
                role: role as 'user' | 'assistant' | 'system',
                sender_type: payload.sender_type || (role === 'user' ? 'visitor' : role === 'agent' ? 'agent' : undefined),
                agent_id: payload.agent_id,
                content,
                created_at: payload.created_at || new Date().toISOString(),
              };
              this.callbacks.onMessage?.(msg);
              break;
            }

            case 'ping':
              this.send({ type: 'pong' });
              break;

            case 'pong':
              // Heartbeat verified
              break;

            case 'error':
              this.callbacks.onError?.(new Error(payload.message || 'Agent WS error'));
              break;

            default:
              break;
          }
        } catch (err: unknown) {
          console.warn('[RealEstateAI Agent WS] Frame parse error:', err);
        }
      };

      this.ws.onerror = (e) => {
        console.warn('[RealEstateAI Agent WS] Socket error:', e);
      };

      this.ws.onclose = () => {
        this.stopHeartbeat();
        this.callbacks.onDisconnected?.();

        if (!this.isExplicitlyClosed && this.reconnectAttempts < this.maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 10000);
          this.reconnectAttempts++;
          setTimeout(() => {
            if (!this.isExplicitlyClosed) {
              this.connect();
            }
          }, delay);
        }
      };
    } catch (err: unknown) {
      this.callbacks.onError?.(err instanceof Error ? err : new Error(String(err)));
    }
  }

  public claim(conversationId: string): void {
    this.send({
      action: 'claim',
      conversation_id: conversationId,
    });
  }

  public release(conversationId: string): void {
    this.send({
      action: 'release',
      conversation_id: conversationId,
    });
  }

  public sendMessage(conversationId: string, content: string): boolean {
    if (!this.isConnected()) return false;
    this.send({
      action: 'send_message',
      conversation_id: conversationId,
      content,
    });
    return true;
  }

  private send(data: Record<string, unknown>): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.pingInterval = setInterval(() => {
      this.send({ type: 'ping' });
    }, 25000);
  }

  private stopHeartbeat(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  public disconnect(): void {
    this.isExplicitlyClosed = true;
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  public isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}
