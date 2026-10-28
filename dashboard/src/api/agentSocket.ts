// # 12c HITL - Socket.IO Client for Agency Dashboard
import { io, Socket } from 'socket.io-client';
import { useAuthStore } from '../store/useAuthStore';
import type { BackendMessage } from './client';

export interface AgentSocketCallbacks {
  onMessage?: (msg: BackendMessage) => void;
  onVisitorActivity?: (msg: BackendMessage) => void;
  onTyping?: (data: { conversation_id: string; is_typing: boolean; sender: string }) => void;
  onConnected?: () => void;
  onDisconnected?: () => void;
  onError?: (err: Error) => void;
  onLeadCreated?: (lead: any) => void;
  onLeadUpdated?: (lead: any) => void;
  onHotLeadAlert?: (lead: any) => void;

}

export class AgentSocketClient {
  private socket: Socket | null = null;
  private callbacks: AgentSocketCallbacks;
  private currentJoinedConvId: string | null = null;

  constructor(callbacks: AgentSocketCallbacks) {
    this.callbacks = callbacks;
  }

  private getBaseUrl(): string {
    const baseApi = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '');
    return baseApi;
  }

  public connect(): void {
    if (this.socket && this.socket.connected) return;

    const token = useAuthStore.getState().agencyToken;
    if (!token) {
      console.warn('[Agency Socket.IO] Missing agency JWT token, skipping connection.');
      return;
    }

    this.socket = io(this.getBaseUrl(), {
      path: '/socket.io',
      auth: { token },
      transports: ['websocket', 'polling'],
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });

    this.socket.on('connect', () => {
      console.log('[Agency Socket.IO] Connected to server.');
      this.callbacks.onConnected?.();
      if (this.currentJoinedConvId) {
        this.joinConversation(this.currentJoinedConvId);
      }
    });

    this.socket.on('new_message', (payload: any) => {
      const msg: BackendMessage = {
        id: payload.id || `msg_${Date.now()}`,
        conversation_id: payload.conversation_id,
        role: payload.role || 'user',
        sender_type: payload.sender_type,
        agent_id: payload.agent_id,
        content: payload.content || '',
        created_at: payload.created_at || new Date().toISOString(),
      };
      this.callbacks.onMessage?.(msg);
    });

    this.socket.on('visitor_activity', (payload: any) => {
      const msg: BackendMessage = {
        id: payload.id || `msg_${Date.now()}`,
        conversation_id: payload.conversation_id,
        role: payload.role || 'user',
        sender_type: payload.sender_type,
        agent_id: payload.agent_id,
        content: payload.content || '',
        created_at: payload.created_at || new Date().toISOString(),
      };
      this.callbacks.onVisitorActivity?.(msg);
    });

    this.socket.on('user_typing', (data: any) => {
      this.callbacks.onTyping?.(data);
    });

    this.socket.on('disconnect', () => {
      console.log('[Agency Socket.IO] Disconnected.');
      this.callbacks.onDisconnected?.();
    });

    this.socket.on('connect_error', (err: Error) => {
      console.warn('[Agency Socket.IO] Connection error:', err.message);
      this.callbacks.onError?.(err);
    });

    // Lead events
    this.socket.on('lead_created', (data: any) => {
    this.callbacks.onLeadCreated?.(data);
    });

    this.socket.on('lead_updated', (data: any) => {
    this.callbacks.onLeadUpdated?.(data);
    });

    this.socket.on('hot_lead_alert', (data: any) => {
    this.callbacks.onHotLeadAlert?.(data);
    });







  }

  public joinConversation(conversationId: string): void {
    this.currentJoinedConvId = conversationId;
    if (this.socket && this.socket.connected) {
      this.socket.emit('join_conversation', { conversation_id: conversationId });
    }
  }

  public sendMessage(conversationId: string, content: string): boolean {
    if (!this.socket || !this.socket.connected) return false;
    this.socket.emit('send_message', {
      conversation_id: conversationId,
      content,
    });
    return true;
  }

  public sendTyping(conversationId: string, isTyping: boolean): boolean {
    if (!this.socket || !this.socket.connected) return false;
    this.socket.emit('typing', {
      conversation_id: conversationId,
      is_typing: isTyping,
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
