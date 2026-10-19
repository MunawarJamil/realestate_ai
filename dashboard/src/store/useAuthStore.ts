import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { TenantRead } from '../types/tenant';

export interface AuthState {
  adminKey: string | null;
  apiKey: string | null;
  tenant: TenantRead | null;

  // Actions
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
      tenant: null,

      setAdminKey: (key: string) => set({ adminKey: key.trim() }),
      clearAdminKey: () => set({ adminKey: null }),

      setApiKey: (key: string, tenant: TenantRead | null = null) =>
        set((state) => ({
          apiKey: key.trim(),
          tenant: tenant !== undefined ? tenant : state.tenant,
        })),

      setTenant: (tenant: TenantRead | null) => set({ tenant }),
      clearApiKey: () => set({ apiKey: null, tenant: null }),

      logoutAll: () => set({ adminKey: null, apiKey: null, tenant: null }),
    }),
    {
      name: 'realestate_ai_auth_storage',
      partialize: (state) => ({
        adminKey: state.adminKey,
        apiKey: state.apiKey,
        tenant: state.tenant,
      }),
    }
  )
);
