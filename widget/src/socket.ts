// # 12c HITL - Socket.IO Client for RealEstate AI Embeddable Widget
import { io, Socket } from 'socket.io-client';
import { ChatMessage } from './types';

export interface WidgetSocketCallbacks {
  onMessage: (msg: ChatMessage) => void;
  onTyping?: (data: { is_typing: boolean; sender: string }) => void;
  onConnected?: () => void;
  onDisconnected?: () => void;
  onError?: (err: Error) => void;
}

export class WidgetSocketClient {
  private socket: Socket | null = null;
  private apiUrl: string;
  private token: string;
  private conversationId: string;
  private callbacks: WidgetSocketCallbacks;

  constructor(
    apiUrl: string,
    token: string,
    conversationId: string,
    callbacks: WidgetSocketCallbacks
  ) {
    this.apiUrl = apiUrl.replace(/\/+$/, '');
    this.token = token;
    this.conversationId = conversationId;
    this.callbacks = callbacks;
  }

  public connect(): void {
    if (this.socket && this.socket.connected) return;

    this.socket = io(this.apiUrl, {
      path: '/socket.io',
      auth: { token: this.token },
      transports: ['websocket', 'polling'],
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });

    this.socket.on('connect', () => {
      console.log('[Widget Socket.IO] Connected. Joining conversation room:', this.conversationId);
      this.socket?.emit('join_conversation', { conversation_id: this.conversationId });
      this.callbacks.onConnected?.();
    });

    this.socket.on('new_message', (payload: any) => {
      const role = payload.role === 'user' ? 'user' : 'assistant';
      const msg: ChatMessage = {
        id: payload.id || `msg_${Date.now()}`,
        role: role,
        sender_type: payload.sender_type,
        content: payload.content || '',
        created_at: payload.created_at,
      };
      this.callbacks.onMessage(msg);
    });

    this.socket.on('user_typing', (data: any) => {
      this.callbacks.onTyping?.(data);
    });

    this.socket.on('disconnect', () => {
      console.log('[Widget Socket.IO] Disconnected');
      this.callbacks.onDisconnected?.();
    });

    this.socket.on('connect_error', (err: Error) => {
      console.warn('[Widget Socket.IO] Connection error:', err.message);
      this.callbacks.onError?.(err);
    });
  }

  public sendMessage(content: string): boolean {
    if (!this.socket || !this.socket.connected) return false;
    this.socket.emit('send_message', {
      conversation_id: this.conversationId,
      content,
    });
    return true;
  }

  public isConnected(): boolean {
    return !!(this.socket && this.socket.connected);
  }

  public disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }
}
