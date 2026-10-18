/**
 * Safe local storage manager for widget visitor identity and active conversations.
 */

import { VisitorSession } from './types';

interface StoredWidgetData {
  session: VisitorSession;
  conversationId: string | null;
}

export class WidgetStorage {
  private storageKey: string;

  constructor(widgetKey: string) {
    this.storageKey = `re_ai_widget_${widgetKey}`;
  }

  public getSession(): VisitorSession | null {
    try {
      const raw = localStorage.getItem(this.storageKey);
      if (!raw) return null;

      const data: StoredWidgetData = JSON.parse(raw);
      if (!data.session || !data.session.visitor_token) {
        return null;
      }

      // Check token expiration
      const expireTime = new Date(data.session.expires_at).getTime();
      if (Date.now() >= expireTime) {
        this.clear();
        return null;
      }

      return data.session;
    } catch {
      return null;
    }
  }

  public getConversationId(): string | null {
    try {
      const raw = localStorage.getItem(this.storageKey);
      if (!raw) return null;
      const data: StoredWidgetData = JSON.parse(raw);
      return data.conversationId || null;
    } catch {
      return null;
    }
  }

  public saveSession(session: VisitorSession, conversationId?: string | null): void {
    try {
      const currentConv = conversationId !== undefined ? conversationId : this.getConversationId();
      const payload: StoredWidgetData = {
        session,
        conversationId: currentConv || null,
      };
      localStorage.setItem(this.storageKey, JSON.stringify(payload));
    } catch (e) {
      console.warn('[RealEstateAI Widget] Failed to save session to localStorage', e);
    }
  }

  public saveConversationId(conversationId: string | null): void {
    const session = this.getSession();
    if (!session) return;
    this.saveSession(session, conversationId);
  }

  public clear(): void {
    try {
      localStorage.removeItem(this.storageKey);
    } catch {
      // Ignore
    }
  }
}
