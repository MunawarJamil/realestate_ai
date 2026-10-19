export type TenantStatus = 'active' | 'suspended' | 'pending';

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  allowed_domains: string[];
  status: TenantStatus;
  plan: 'Starter' | 'Growth' | 'Enterprise';
  created_at: string;
  total_conversations: number;
  api_key_preview: string;
  widget_key_preview: string;
}

export interface PlatformMetrics {
  totalTenants: number;
  activeTenants: number;
  activeWidgets: number;
  totalMessages24h: number;
  avgResponseTimeMs: number;
}
