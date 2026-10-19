/**
 * Type definitions for the Embeddable RealEstate AI Chat Widget
 */

export interface WidgetConfig {
  widgetKey: string;
  apiUrl: string;
  title?: string;
  subtitle?: string;
  greeting?: string;
  placeholder?: string;
  position?: 'bottom-right' | 'bottom-left';
  primaryColor?: string;
}

export interface VisitorSession {
  visitor_token: string;
  visitor_id: string;
  tenant_id: string;
  tenant_name: string;
  expires_at: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sender_type?: 'visitor' | 'ai' | 'agent' | 'system'; // # 12b HITL
  created_at?: string;
}

export interface ConversationRead {
  id: string;
  tenant_id: string;
  title: string | null;
  status?: 'ai' | 'handoff_requested' | 'human_active' | 'resolved'; // # 12b HITL
  assigned_agent_id?: string | null; // # 12b HITL
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface WidgetState {
  isOpen: boolean;
  isLoading: boolean;
  isStreaming: boolean;
  status: 'ai' | 'handoff_requested' | 'human_active' | 'resolved'; // # 12b HITL
  session: VisitorSession | null;
  conversationId: string | null;
  messages: ChatMessage[];
  error: string | null;
}

export interface RealEstateAIWindowAPI {
  init: (config: Partial<WidgetConfig>) => void;
  open: () => void;
  close: () => void;
  toggle: () => void;
  getState: () => Readonly<WidgetState>;
}

declare global {
  interface Window {
    RealEstateAI?: RealEstateAIWindowAPI;
    RealEstateAIConfig?: Partial<WidgetConfig>;
  }
}
