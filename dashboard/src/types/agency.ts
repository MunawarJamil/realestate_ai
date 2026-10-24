// # 12b HITL - Enhanced Message Contract
export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  sender_type?: 'visitor' | 'ai' | 'agent' | 'system'; // # 12b HITL
  content: string;
  created_at: string;
  grounded_sources?: string[];
}

// # 12b HITL - Conversation Status with Multi-tier States
export type ConversationStatus =
  | 'ai'
  | 'handoff_requested'
  | 'human_active'
  | 'resolved'
  | 'active'
  | 'qualified_lead'
  | 'closed';

// # 12b HITL - AI Executive Brief Interface
export interface BackendConversationSummary {
  conversation_id: string;
  summary: string;
  key_intent?: string | null;
  budget?: string | null;
  preferred_location?: string | null;
}

export interface Conversation {
  id: string;
  visitor_name: string;
  visitor_avatar?: string;
  visitor_location: string;
  visitor_email?: string;
  visitor_phone?: string;
  intent: string;
  budget: string;
  property_interest: string;
  status: ConversationStatus;
  assigned_agent_id?: string | null;
  summary?: BackendConversationSummary | null;
  started_at: string;
  last_message_at: string;
  last_message_preview?: string; // Persists last snippet
  last_message_sender?: string;  // 'visitor' | 'agent' | 'ai'
  tags: string[];
  messages: Message[];
  unread_count?: number;
}



export type LeadStatus = 'new' | 'contacted' | 'viewing_scheduled' | 'closed';

export interface Lead {
  id: string;
  name: string;
  email: string;
  phone: string;
  budget: string;
  property_type: string;
  preferred_location: string;
  qualification_score: number;
  status: LeadStatus;
  created_at: string;
  notes: string;
  conversation_id?: string;
}

export type DocumentCategory = 'Brochure' | 'Floorplan' | 'Pricing' | 'Payment Plan';
export type DocumentStatus = 'indexed' | 'processing' | 'failed';

export interface KnowledgeDoc {
  id: string;
  title: string;
  category: DocumentCategory;
  file_name: string;
  file_size: string;
  chunk_count: number;
  status: DocumentStatus;
  uploaded_at: string;
}
