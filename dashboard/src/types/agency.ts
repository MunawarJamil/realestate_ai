export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  grounded_sources?: string[];
}

export type ConversationStatus = 'active' | 'qualified_lead' | 'closed';

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
  started_at: string;
  last_message_at: string;
  tags: string[];
  messages: Message[];
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
