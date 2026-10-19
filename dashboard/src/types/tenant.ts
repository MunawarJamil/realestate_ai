export type TenantStatus = 'active' | 'suspended' | 'pending';

export interface TenantRead {
  id: string;
  name: string;
  slug: string;
  api_key_prefix: string;
  widget_key: string;
  allowed_domains: string[];
  is_active: boolean;
  created_at: string;
}

export interface TenantCreated extends TenantRead {
  api_key: string;
  admin_email?: string;
  admin_password?: string;
}

export interface TenantCreatePayload {
  name: string;
  slug: string;
  allowed_domains?: string[];
  admin_email?: string;
  admin_full_name?: string;
  admin_password?: string;
}

export interface TenantUpdatePayload {
  name?: string;
  allowed_domains?: string[];
  is_active?: boolean;
}

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
  is_active?: boolean;
}

export interface PlatformMetrics {
  totalTenants: number;
  activeTenants: number;
  activeWidgets: number;
  totalMessages24h: number;
  avgResponseTimeMs: number;
}
