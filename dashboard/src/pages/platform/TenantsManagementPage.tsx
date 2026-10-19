import React, { useState, useEffect, useCallback } from 'react';
import {
  Plus,
  Search,
  Key,
  Globe,
  Copy,
  Check,
  PowerOff,
  Power,
  Code2,
  Settings2,
  Trash2,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';
import type { Tenant, TenantStatus, TenantRead, TenantCreated } from '../../types/tenant';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Modal } from '../../components/ui/Modal';
import { apiClient, ApiError } from '../../api/client';

function mapBackendTenant(t: TenantRead): Tenant {
  return {
    id: t.id,
    name: t.name,
    slug: t.slug,
    allowed_domains: t.allowed_domains || [],
    status: t.is_active ? 'active' : 'suspended',
    plan: 'Growth',
    created_at: new Date(t.created_at).toISOString().split('T')[0],
    total_conversations: 0,
    api_key_preview: `${t.api_key_prefix}••••••••••••••`,
    widget_key_preview: `${t.widget_key.slice(0, 12)}••••••••••••`,
    is_active: t.is_active,
  };
}

export const TenantsManagementPage: React.FC = () => {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | TenantStatus>('all');

  // Modal States
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Newly Provisioned Credentials Modal
  const [createdCredentials, setCreatedCredentials] = useState<TenantCreated | null>(null);

  // Manage Tenant Drawer / Modal
  const [selectedTenantKeys, setSelectedTenantKeys] = useState<Tenant | null>(null);
  const [manageTenant, setManageTenant] = useState<Tenant | null>(null);
  const [newDomainInput, setNewDomainInput] = useState('');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [updatingTenantId, setUpdatingTenantId] = useState<string | null>(null);

  // New Tenant Form State
  const [newAgencyName, setNewAgencyName] = useState('');
  const [newAllowedDomains, setNewAllowedDomains] = useState('');
  const [newPlan, setNewPlan] = useState<'Starter' | 'Growth' | 'Enterprise'>('Growth');

  const generatedSlug = newAgencyName
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)+/g, '');

  const fetchTenants = useCallback(async () => {
    setIsLoading(true);
    setErrorBanner(null);
    try {
      const data = await apiClient.admin.listTenants({ limit: 100 });
      setTenants(data.map(mapBackendTenant));
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setErrorBanner(`Failed to fetch tenants (${err.status}): ${err.message}`);
      } else {
        setErrorBanner(
          'Unable to reach FastAPI backend (http://localhost:8000). Ensure the backend server is running.'
        );
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTenants();
  }, [fetchTenants]);

  const filteredTenants = tenants.filter((tenant) => {
    const matchesSearch =
      tenant.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      tenant.slug.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || tenant.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const handleToggleStatus = async (tenantId: string) => {
    const target = tenants.find((t) => t.id === tenantId);
    if (!target) return;

    const nextActive = !target.is_active;
    setUpdatingTenantId(tenantId);

    try {
      const updated = await apiClient.admin.updateTenant(tenantId, {
        is_active: nextActive,
      });

      setTenants((prev) =>
        prev.map((t) => (t.id === tenantId ? mapBackendTenant(updated) : t))
      );
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : 'Failed to update tenant status';
      alert(`Error updating tenant: ${msg}`);
    } finally {
      setUpdatingTenantId(null);
    }
  };

  const handleCreateTenant = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAgencyName.trim()) return;

    const domains = newAllowedDomains
      .split(',')
      .map((d) => d.trim())
      .filter(Boolean);

    setIsSubmitting(true);
    setCreateError(null);

    try {
      const created = await apiClient.admin.createTenant({
        name: newAgencyName.trim(),
        slug: generatedSlug,
        allowed_domains: domains.length > 0 ? domains : ['*'],
      });

      // Add to list immediately
      setTenants((prev) => [mapBackendTenant(created), ...prev]);
      setIsCreateOpen(false);
      setNewAgencyName('');
      setNewAllowedDomains('');
      setNewPlan('Growth');

      // Present the credentials modal with raw API key
      setCreatedCredentials(created);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setCreateError(err.message);
      } else {
        setCreateError('Network error while provisioning agency tenant.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const copyToClipboard = (text: string, identifier: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(identifier);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleAddDomain = async (tenantId: string) => {
    if (!newDomainInput.trim()) return;
    const cleanDomain = newDomainInput.trim().toLowerCase();
    const target = tenants.find((t) => t.id === tenantId);
    if (!target) return;

    if (target.allowed_domains.includes(cleanDomain)) {
      setNewDomainInput('');
      return;
    }

    const updatedDomains = [...target.allowed_domains, cleanDomain];

    try {
      const updated = await apiClient.admin.updateTenant(tenantId, {
        allowed_domains: updatedDomains,
      });
      const mapped = mapBackendTenant(updated);
      setTenants((prev) => prev.map((t) => (t.id === tenantId ? mapped : t)));
      if (manageTenant?.id === tenantId) setManageTenant(mapped);
      setNewDomainInput('');
    } catch (err: unknown) {
      alert(`Failed to add domain: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  const handleRemoveDomain = async (tenantId: string, domainToRemove: string) => {
    const target = tenants.find((t) => t.id === tenantId);
    if (!target) return;

    const updatedDomains = target.allowed_domains.filter((d) => d !== domainToRemove);

    try {
      const updated = await apiClient.admin.updateTenant(tenantId, {
        allowed_domains: updatedDomains,
      });
      const mapped = mapBackendTenant(updated);
      setTenants((prev) => prev.map((t) => (t.id === tenantId ? mapped : t)));
      if (manageTenant?.id === tenantId) setManageTenant(mapped);
    } catch (err: unknown) {
      alert(`Failed to remove domain: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  return (
    <div className="space-y-6 sm:space-y-8 max-w-7xl mx-auto">
      {/* Header and Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-white/8">
        <div>
          <div className="flex items-center gap-2.5">
            <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
              Agency Tenants
            </h2>
            <button
              onClick={fetchTenants}
              disabled={isLoading}
              title="Refresh list"
              className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-zinc-400 hover:text-white transition-colors cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>
          <p className="text-xs text-zinc-400 mt-1">
            Provision keys, configure allowed domains, and monitor live status from PostgreSQL.
          </p>
        </div>
        <Button onClick={() => setIsCreateOpen(true)} variant="primary" size="md">
          <Plus className="w-4 h-4 mr-1.5" />
          <span>Provision Agency</span>
        </Button>
      </div>

      {/* Error banner if backend down */}
      {errorBanner && (
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-start justify-between gap-3 text-xs text-amber-300">
          <div className="flex items-start gap-2.5">
            <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Backend Communication Notice</p>
              <p className="text-amber-300/80 mt-0.5">{errorBanner}</p>
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={fetchTenants}>
            <span>Retry Connection</span>
          </Button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3.5 sm:p-4 rounded-xl bg-[#151517] border border-white/8">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search agencies by name or slug..."
            className="w-full pl-10 pr-4 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-[#F97316] transition-colors"
          />
        </div>
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          {(['all', 'active', 'suspended'] as const).map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-colors cursor-pointer shrink-0 ${
                statusFilter === status
                  ? 'bg-white/10 text-white font-semibold'
                  : 'text-zinc-400 hover:text-white hover:bg-white/5'
              }`}
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      {/* Tenants Table */}
      <div className="rounded-xl bg-[#151517] border border-white/8 overflow-hidden shadow-lg">
        <div className="w-full overflow-x-auto">
          <table className="w-full text-left text-xs min-w-[880px]">
            <thead>
              <tr className="border-b border-white/8 text-zinc-400 uppercase tracking-wider text-[11px] bg-white/[0.01]">
                <th className="py-3.5 px-6 font-semibold whitespace-nowrap">Agency Tenant</th>
                <th className="py-3.5 px-6 font-semibold whitespace-nowrap">Plan</th>
                <th className="py-3.5 px-6 font-semibold whitespace-nowrap">Allowed Domains</th>
                <th className="py-3.5 px-6 font-semibold text-right whitespace-nowrap">Created</th>
                <th className="py-3.5 px-6 font-semibold whitespace-nowrap">Status</th>
                <th className="py-3.5 px-6 font-semibold text-right whitespace-nowrap">Controls</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="py-16 text-center text-zinc-400">
                    <div className="flex flex-col items-center justify-center gap-2">
                      <RefreshCw className="w-5 h-5 text-[#F97316] animate-spin" />
                      <span className="text-xs">Loading agency tenants from backend...</span>
                    </div>
                  </td>
                </tr>
              ) : filteredTenants.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-16 text-center text-zinc-500 text-xs">
                    <div className="flex flex-col items-center justify-center gap-3">
                      <p>No agency tenants found in database.</p>
                      <Button variant="primary" size="sm" onClick={() => setIsCreateOpen(true)}>
                        <Plus className="w-3.5 h-3.5 mr-1" />
                        <span>Provision First Agency</span>
                      </Button>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredTenants.map((tenant) => (
                  <tr key={tenant.id} className="hover:bg-white/[0.02] transition-colors">
                    {/* Name & Slug */}
                    <td className="py-4 px-6 font-medium text-white whitespace-nowrap">
                      <div className="font-semibold text-sm">{tenant.name}</div>
                      <div className="text-[11px] text-zinc-500 font-mono mt-0.5">
                        id: {tenant.id.slice(0, 8)}... • slug: /{tenant.slug}
                      </div>
                    </td>

                    {/* Plan */}
                    <td className="py-4 px-6 whitespace-nowrap">
                      <span className="text-[11px] font-medium text-zinc-300 bg-white/5 px-2 py-0.5 rounded border border-white/5 whitespace-nowrap">
                        {tenant.plan}
                      </span>
                    </td>

                    {/* Domains */}
                    <td className="py-4 px-6 text-zinc-400 font-mono text-[11px] whitespace-nowrap">
                      <div className="flex items-center gap-1.5 flex-nowrap">
                        <Globe className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                        {tenant.allowed_domains.length === 0 ? (
                          <span className="text-zinc-600 italic">None (restricted)</span>
                        ) : (
                          tenant.allowed_domains.map((dom) => (
                            <span
                              key={dom}
                              className="bg-[#0B0B0D] px-2 py-0.5 rounded border border-white/5 whitespace-nowrap"
                            >
                              {dom}
                            </span>
                          ))
                        )}
                      </div>
                    </td>

                    {/* Created date */}
                    <td className="py-4 px-6 text-right font-medium text-zinc-400 whitespace-nowrap">
                      {tenant.created_at}
                    </td>

                    {/* Status */}
                    <td className="py-4 px-6 whitespace-nowrap">
                      <Badge
                        variant={tenant.status === 'active' ? 'success' : 'danger'}
                        className="capitalize"
                      >
                        {tenant.status}
                      </Badge>
                    </td>

                    {/* Action Buttons */}
                    <td className="py-4 px-6 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-2">
                        {/* Status Toggle Button */}
                        <button
                          onClick={() => handleToggleStatus(tenant.id)}
                          disabled={updatingTenantId === tenant.id}
                          className={`p-1.5 rounded-lg border transition-colors cursor-pointer ${
                            tenant.status === 'active'
                              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20'
                              : 'bg-zinc-800 border-white/10 text-zinc-400 hover:text-white'
                          }`}
                          title={tenant.status === 'active' ? 'Suspend Agency' : 'Activate Agency'}
                        >
                          {updatingTenantId === tenant.id ? (
                            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          ) : tenant.status === 'active' ? (
                            <Power className="w-3.5 h-3.5" />
                          ) : (
                            <PowerOff className="w-3.5 h-3.5" />
                          )}
                        </button>

                        {/* View Keys Button */}
                        <button
                          onClick={() => setSelectedTenantKeys(tenant)}
                          className="p-1.5 rounded-lg bg-white/5 border border-white/10 text-zinc-300 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
                          title="View API & Widget Keys"
                        >
                          <Key className="w-3.5 h-3.5" />
                        </button>

                        {/* Domain / Whitelist Config Drawer */}
                        <button
                          onClick={() => setManageTenant(tenant)}
                          className="p-1.5 rounded-lg bg-white/5 border border-white/10 text-zinc-300 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
                          title="Manage Domains Whitelist"
                        >
                          <Settings2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* MODAL 1: Create New Agency Form */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Provision Agency Tenant"
        description="Creates a new isolated multi-tenant agency workspace with API and public chat widget credentials."
      >
        <form onSubmit={handleCreateTenant} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5">
              Agency Name *
            </label>
            <input
              type="text"
              value={newAgencyName}
              onChange={(e) => setNewAgencyName(e.target.value)}
              required
              placeholder="e.g. Apex Luxury Properties"
              className="w-full px-3 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-[#F97316]"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5">
              Tenant Slug (Auto-derived)
            </label>
            <div className="flex items-center gap-2">
              <span className="text-xs text-zinc-500 font-mono">/</span>
              <input
                readOnly
                type="text"
                value={generatedSlug || 'agency-slug'}
                className="w-full px-3 py-2 bg-[#0B0B0D]/50 border border-white/5 rounded-lg text-xs font-mono text-zinc-400 focus:outline-none"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5">
              Allowed Domains (Comma separated)
            </label>
            <input
              type="text"
              value={newAllowedDomains}
              onChange={(e) => setNewAllowedDomains(e.target.value)}
              placeholder="e.g. apexluxury.com, localhost:3000, *"
              className="w-full px-3 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-[#F97316]"
            />
            <p className="text-[11px] text-zinc-500 mt-1">
              Limits chat widget execution to these exact web domains. Use * for testing.
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5">
              Service Tier Plan
            </label>
            <select
              value={newPlan}
              onChange={(e) =>
                setNewPlan(e.target.value as 'Starter' | 'Growth' | 'Enterprise')
              }
              className="w-full px-3 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white focus:outline-none focus:border-[#F97316]"
            >
              <option value="Starter">Starter Tier</option>
              <option value="Growth">Growth Tier</option>
              <option value="Enterprise">Enterprise Tier</option>
            </select>
          </div>

          {createError && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">
              {createError}
            </div>
          )}

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-white/8">
            <Button
              type="button"
              variant="secondary"
              size="md"
              onClick={() => setIsCreateOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="md" disabled={isSubmitting}>
              <span>{isSubmitting ? 'Provisioning...' : 'Create & Provision Agency'}</span>
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL 2: Newly Created Raw Credentials Banner (Crucial!) */}
      {createdCredentials && (
        <Modal
          isOpen={true}
          onClose={() => setCreatedCredentials(null)}
          title={`Agency Provisioned: ${createdCredentials.name}`}
          description="Save these credentials immediately. The private API key is displayed only once."
        >
          <div className="space-y-4">
            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-start gap-2 text-xs text-amber-300">
              <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <span>
                <strong>Important:</strong> The raw API key below will NEVER be shown again. Securely copy it and provide it to the agency admin.
              </span>
            </div>

            {/* Raw Private API Key */}
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Secret Private API Key (rk_live_...)
              </label>
              <div className="flex items-center gap-2">
                <input
                  readOnly
                  type="text"
                  value={createdCredentials.api_key}
                  className="flex-1 px-3 py-2 bg-[#0B0B0D] border border-[#F97316]/40 rounded-lg text-xs font-mono text-emerald-400 font-bold select-all"
                />
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => copyToClipboard(createdCredentials.api_key, 'new_rk')}
                >
                  {copiedKey === 'new_rk' ? (
                    <Check className="w-3.5 h-3.5 text-white" />
                  ) : (
                    <Copy className="w-3.5 h-3.5 text-white" />
                  )}
                  <span>{copiedKey === 'new_rk' ? 'Copied' : 'Copy Key'}</span>
                </Button>
              </div>
            </div>

            {/* Public Widget Key */}
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Public Web Chat Widget Key (wk_live_...)
              </label>
              <div className="flex items-center gap-2">
                <input
                  readOnly
                  type="text"
                  value={createdCredentials.widget_key}
                  className="flex-1 px-3 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs font-mono text-zinc-300 select-all"
                />
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => copyToClipboard(createdCredentials.widget_key, 'new_wk')}
                >
                  {copiedKey === 'new_wk' ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <Copy className="w-3.5 h-3.5 text-zinc-400" />
                  )}
                  <span>{copiedKey === 'new_wk' ? 'Copied' : 'Copy'}</span>
                </Button>
              </div>
            </div>

            <div className="pt-3 border-t border-white/8 flex justify-end">
              <Button
                variant="primary"
                size="md"
                onClick={() => setCreatedCredentials(null)}
              >
                <span>Done & Copied</span>
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* MODAL 3: View Keys & Embed Script for Existing Tenant */}
      {selectedTenantKeys && (
        <Modal
          isOpen={true}
          onClose={() => setSelectedTenantKeys(null)}
          title={`${selectedTenantKeys.name} — Credentials`}
          description="Tenant API credentials preview and client-side embed tag."
        >
          <div className="space-y-5">
            {/* Backend Key Preview */}
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Backend Private API Key Prefix
              </label>
              <div className="flex items-center gap-2">
                <input
                  readOnly
                  type="text"
                  value={selectedTenantKeys.api_key_preview}
                  className="flex-1 px-3 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs font-mono text-zinc-300"
                />
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => copyToClipboard(selectedTenantKeys.api_key_preview, 'rk')}
                >
                  {copiedKey === 'rk' ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <Copy className="w-3.5 h-3.5 text-zinc-400" />
                  )}
                  <span>{copiedKey === 'rk' ? 'Copied' : 'Copy'}</span>
                </Button>
              </div>
              <p className="text-[11px] text-zinc-500">
                Only the prefix is stored in the database for security (SHA-256 hashed).
              </p>
            </div>

            {/* Public Widget Key */}
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Public Web Chat Widget Key
              </label>
              <div className="flex items-center gap-2">
                <input
                  readOnly
                  type="text"
                  value={selectedTenantKeys.widget_key_preview}
                  className="flex-1 px-3 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs font-mono text-zinc-300"
                />
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => copyToClipboard(selectedTenantKeys.widget_key_preview, 'wk')}
                >
                  {copiedKey === 'wk' ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <Copy className="w-3.5 h-3.5 text-zinc-400" />
                  )}
                  <span>{copiedKey === 'wk' ? 'Copied' : 'Copy'}</span>
                </Button>
              </div>
            </div>

            {/* Embed Script Snippet */}
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-1.5">
                <Code2 className="w-3.5 h-3.5 text-[#F97316]" />
                <span>HTML Embed Script</span>
              </label>
              <div className="relative">
                <pre className="p-3 bg-[#0B0B0D] border border-white/10 rounded-lg text-[11px] font-mono text-zinc-300 overflow-x-auto">
{`<script
  src="http://localhost:5173/widget.js"
  data-widget-key="${selectedTenantKeys.widget_key_preview}"
  data-tenant-slug="${selectedTenantKeys.slug}"
  async>
</script>`}
                </pre>
              </div>
            </div>
          </div>
        </Modal>
      )}

      {/* DRAWER: Manage Allowed Domains */}
      {manageTenant && (
        <div className="fixed inset-0 z-50 overflow-hidden bg-black/60 backdrop-blur-xs flex justify-end">
          <div className="w-full max-w-md bg-[#151517] border-l border-white/10 h-full p-6 flex flex-col justify-between overflow-y-auto">
            <div className="space-y-6">
              <div className="flex items-center justify-between pb-4 border-b border-white/10">
                <div>
                  <h3 className="text-base font-bold text-white tracking-tight">
                    {manageTenant.name}
                  </h3>
                  <p className="text-xs text-zinc-400 mt-0.5">Origin Whitelist Configuration</p>
                </div>
                <button
                  onClick={() => setManageTenant(null)}
                  className="p-1 rounded text-zinc-400 hover:text-white cursor-pointer"
                >
                  ✕
                </button>
              </div>

              {/* Add Domain */}
              <div className="space-y-2">
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400">
                  Add Allowed Origin / Host
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newDomainInput}
                    onChange={(e) => setNewDomainInput(e.target.value)}
                    placeholder="e.g. subdomain.agency.com"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleAddDomain(manageTenant.id);
                      }
                    }}
                    className="flex-1 px-3 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-[#F97316]"
                  />
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => handleAddDomain(manageTenant.id)}
                  >
                    Add
                  </Button>
                </div>
                <p className="text-[11px] text-zinc-500">
                  Requests sent to <code className="text-zinc-400">/api/v1/widget/*</code> must have a matching Origin header.
                </p>
              </div>

              {/* Domains List */}
              <div className="space-y-2">
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400">
                  Active Allowed Origins ({manageTenant.allowed_domains.length})
                </label>
                <div className="space-y-2">
                  {manageTenant.allowed_domains.length === 0 ? (
                    <p className="text-xs text-zinc-500 italic">No origins whitelisted.</p>
                  ) : (
                    manageTenant.allowed_domains.map((dom) => (
                      <div
                        key={dom}
                        className="flex items-center justify-between p-2.5 rounded-lg bg-[#0B0B0D] border border-white/5 text-xs text-zinc-300"
                      >
                        <span className="font-mono">{dom}</span>
                        <button
                          onClick={() => handleRemoveDomain(manageTenant.id, dom)}
                          className="text-zinc-500 hover:text-red-400 transition-colors cursor-pointer p-1"
                          title="Remove domain"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>

            <div className="pt-6 border-t border-white/10 flex justify-end">
              <Button variant="secondary" size="md" onClick={() => setManageTenant(null)}>
                Close Drawer
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
