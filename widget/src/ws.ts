// # 12b HITL - WebSocket Client Runtime for RealEstate AI Widget
import { ChatMessage } from './types';

export interface WidgetWSEventCallbacks {
  onToken: (token: string) => void;
  onMessage: (msg: ChatMessage) => void;
  onStatusChange: (status: 'ai' | 'handoff_requested' | 'human_active' | 'resolved', agentId?: string | null) => void;
  onError: (err: Error) => void;
  onConnected?: () => void;
  onDisconnected?: () => void;
}

export class WidgetWebSocketClient {
  private apiUrl: string;
  private token: string;
  private conversationId: string;
  private callbacks: WidgetWSEventCallbacks;
  private ws: WebSocket | null = null;
  private pingInterval: ReturnType<typeof setInterval> | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private isExplicitlyClosed = false;

  constructor(
    apiUrl: string,
    token: string,
    conversationId: string,
    callbacks: WidgetWSEventCallbacks
  ) {
    this.apiUrl = apiUrl.replace(/\/+$/, '');
    this.token = token;
    this.conversationId = conversationId;
    this.callbacks = callbacks;
  }

  /**
   * Translates HTTP/HTTPS URL into WS/WSS URL
   */
  private getWebSocketUrl(): string {
    const parsed = new URL(this.apiUrl);
    const protocol = parsed.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${parsed.host}/api/v1/chat/ws/${this.conversationId}?token=${encodeURIComponent(this.token)}`;
  }

  /**
   * Connects to the WebSocket gateway
   */
  public connect(): void {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.isExplicitlyClosed = false;
    const wsUrl = this.getWebSocketUrl();

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.startHeartbeat();
        this.callbacks.onConnected?.();
      };

      this.ws.onmessage = (event: MessageEvent) => {
        this.handleIncomingFrame(event.data);
      };

      this.ws.onerror = (event: Event) => {
        console.warn('[RealEstateAI WS] Socket error encountered:', event);
      };

      this.ws.onclose = (event: CloseEvent) => {
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
      this.callbacks.onError(err instanceof Error ? err : new Error(String(err)));
    }
  }

  /**
   * Handles incoming frames from the WebSocket
   */
  private handleIncomingFrame(data: string): void {
    try {
      const frame = JSON.parse(data);
      const eventType = frame.event;
      const payload = frame.payload || {};

      switch (eventType) {
        case 'token':
          if (payload.token) {
            this.callbacks.onToken(payload.token);
          }
          break;

        case 'message': {
          const role = payload.role || 'assistant';
          const senderType = payload.sender_type || (role === 'user' ? 'visitor' : 'ai');
          const chatMsg: ChatMessage = {
            id: payload.id || `msg_${Date.now()}`,
            role: role as 'user' | 'assistant' | 'system',
            sender_type: senderType,
            content: payload.content || '',
            created_at: payload.created_at,
          };
          this.callbacks.onMessage(chatMsg);
          break;
        }

        case 'status_change':
          if (payload.status) {
            this.callbacks.onStatusChange(payload.status, payload.assigned_agent_id);
          }
          break;

        case 'ping':
          this.send({ type: 'pong' });
          break;

        case 'pong':
          // Heartbeat received
          break;

        case 'error':
          this.callbacks.onError(new Error(payload.message || 'Real-time WebSocket error'));
          break;

        default:
          break;
      }
    } catch (err: unknown) {
      console.warn('[RealEstateAI WS] Frame parse error:', err);
    }
  }

  /**
   * Dispatches a message frame over WebSocket
   */
  public sendMessage(content: string): boolean {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return false;
    }

    this.send({
      type: 'message',
      content,
    });
    return true;
  }

  /**
   * Sends raw JSON payload
   */
  private send(data: Record<string, unknown>): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  /**
   * Starts periodic heartbeat ping
   */
  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.pingInterval = setInterval(() => {
      this.send({ type: 'ping' });
    }, 25000);
  }

  /**
   * Stops heartbeat
   */
  private stopHeartbeat(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  /**
   * Safely closes the WebSocket connection
   */
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
