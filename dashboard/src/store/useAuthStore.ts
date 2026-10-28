import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { TenantRead } from '../types/tenant';

export interface UserInfo {
  id: string;
  email: string;
  full_name: string;
  role: 'super_admin' | 'agency_admin' | 'agent';
  tenant_id?: string | null;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthState {
  // Legacy / Direct API Key fallback
  adminKey: string | null;
  apiKey: string | null;

  // Modern Multi-Tenant JWT Auth
  platformToken: string | null;
  platformRefreshToken: string | null;
  platformUser: UserInfo | null;

  agencyToken: string | null;
  agencyRefreshToken: string | null;
  agencyUser: UserInfo | null;

  tenant: TenantRead | null;

  // Actions
  setPlatformAuth: (tokens: AuthTokens, user: UserInfo) => void;
  clearPlatformAuth: () => void;

  setAgencyAuth: (tokens: AuthTokens, user: UserInfo, tenant?: TenantRead | null) => void;
  clearAgencyAuth: () => void;
  updateAgencyTokens: (tokens: { access_token: string; refresh_token: string }) => void;
  updatePlatformTokens: (tokens: { access_token: string; refresh_token: string }) => void;

  setAdminKey: (key: string) => void;
  clearAdminKey: () => void;

  setApiKey: (key: string, tenant?: TenantRead | null) => void;
  setTenant: (tenant: TenantRead | null) => void;
  clearApiKey: () => void;

  logoutAll: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      adminKey: null,
      apiKey: null,

      platformToken: null,
      platformRefreshToken: null,
      platformUser: null,

      agencyToken: null,
      agencyRefreshToken: null,
      agencyUser: null,

      tenant: null,

      setPlatformAuth: (tokens: AuthTokens, user: UserInfo) =>
        set({
          platformToken: tokens.access_token,
          platformRefreshToken: tokens.refresh_token,
          platformUser: user,
        }),

      clearPlatformAuth: () =>
        set({
          platformToken: null,
          platformRefreshToken: null,
          platformUser: null,
          adminKey: null,
        }),

      setAgencyAuth: (tokens: AuthTokens, user: UserInfo, tenant: TenantRead | null = null) =>
        set((state) => ({
          agencyToken: tokens.access_token,
          agencyRefreshToken: tokens.refresh_token,
          agencyUser: user,
          tenant: tenant !== undefined ? tenant : state.tenant,
        })),

      clearAgencyAuth: () =>
        set({
          agencyToken: null,
          agencyRefreshToken: null,
          agencyUser: null,
          apiKey: null,
          tenant: null,
        }),

      updateAgencyTokens: (tokens: { access_token: string; refresh_token: string }) =>
        set({
          agencyToken: tokens.access_token,
          agencyRefreshToken: tokens.refresh_token,
        }),

      updatePlatformTokens: (tokens: { access_token: string; refresh_token: string }) =>
        set({
          platformToken: tokens.access_token,
          platformRefreshToken: tokens.refresh_token,
        }),

      setAdminKey: (key: string) => set({ adminKey: key.trim() }),
      clearAdminKey: () => set({ adminKey: null }),

      setApiKey: (key: string, tenant: TenantRead | null = null) =>
        set((state) => ({
          apiKey: key.trim(),
          tenant: tenant !== undefined ? tenant : state.tenant,
        })),

      setTenant: (tenant: TenantRead | null) => set({ tenant }),
      clearApiKey: () => set({ apiKey: null, tenant: null }),

      logoutAll: () =>
        set({
          adminKey: null,
          apiKey: null,
          platformToken: null,
          platformRefreshToken: null,
          platformUser: null,
          agencyToken: null,
          agencyRefreshToken: null,
          agencyUser: null,
          tenant: null,
        }),
    }),
    {
      name: 'realestate_ai_auth_storage',
      partialize: (state) => ({
        adminKey: state.adminKey,
        apiKey: state.apiKey,
        platformToken: state.platformToken,
        platformRefreshToken: state.platformRefreshToken,
        platformUser: state.platformUser,
        agencyToken: state.agencyToken,
        agencyRefreshToken: state.agencyRefreshToken,
        agencyUser: state.agencyUser,
        tenant: state.tenant,
      }),
    }
  )
);
