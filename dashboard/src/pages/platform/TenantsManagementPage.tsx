import React, { useState } from 'react';
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
  RotateCcw,
} from 'lucide-react';
import { initialTenants } from '../../mock/tenantsData';
import type { Tenant, TenantStatus } from '../../types/tenant';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Modal } from '../../components/ui/Modal';

export const TenantsManagementPage: React.FC = () => {
  const [tenants, setTenants] = useState<Tenant[]>(initialTenants);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | TenantStatus>('all');

  // Modal States
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedTenantKeys, setSelectedTenantKeys] = useState<Tenant | null>(null);
  const [manageTenant, setManageTenant] = useState<Tenant | null>(null);
  const [newDomainInput, setNewDomainInput] = useState('');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [keyRotatedNotice, setKeyRotatedNotice] = useState(false);


  // New Tenant Form State
  const [newAgencyName, setNewAgencyName] = useState('');
  const [newAllowedDomains, setNewAllowedDomains] = useState('');
  const [newPlan, setNewPlan] = useState<'Starter' | 'Growth' | 'Enterprise'>('Growth');

  const generatedSlug = newAgencyName
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)+/g, '');

  const filteredTenants = tenants.filter((tenant) => {
    const matchesSearch =
      tenant.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      tenant.slug.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || tenant.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const handleToggleStatus = (tenantId: string) => {
    setTenants((prev) =>
      prev.map((t) => {
        if (t.id === tenantId) {
          const nextStatus: TenantStatus = t.status === 'active' ? 'suspended' : 'active';
          return { ...t, status: nextStatus };
        }
        return t;
      })
    );
  };

  const handleCreateTenant = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAgencyName.trim()) return;

    const domains = newAllowedDomains
      .split(',')
      .map((d) => d.trim())
      .filter(Boolean);

    const randomSuffix = Math.random().toString(36).substring(2, 8);
    const newTenant: Tenant = {
      id: `t-${Date.now().toString().slice(-4)}`,
      name: newAgencyName.trim(),
      slug: generatedSlug || `agency-${randomSuffix}`,
      allowed_domains: domains.length > 0 ? domains : ['localhost'],
      status: 'active',
      plan: newPlan,
      created_at: new Date().toISOString().split('T')[0],
      total_conversations: 0,
      api_key_preview: `rk_live_${randomSuffix}••••••••••••••`,
      widget_key_preview: `wk_live_${randomSuffix}••••••••••••••`,
    };

    setTenants([newTenant, ...tenants]);
    setIsCreateOpen(false);
    setNewAgencyName('');
    setNewAllowedDomains('');
  };

  const copyToClipboard = (text: string, identifier: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(identifier);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleAddDomain = (tenantId: string) => {
    if (!newDomainInput.trim()) return;
    const cleanDomain = newDomainInput.trim().toLowerCase();
    setTenants((prev) =>
      prev.map((t) => {
        if (t.id === tenantId && !t.allowed_domains.includes(cleanDomain)) {
          const updated = { ...t, allowed_domains: [...t.allowed_domains, cleanDomain] };
          if (manageTenant?.id === tenantId) setManageTenant(updated);
          return updated;
        }
        return t;
      })
    );
    setNewDomainInput('');
  };

  const handleRemoveDomain = (tenantId: string, domainToRemove: string) => {
    setTenants((prev) =>
      prev.map((t) => {
        if (t.id === tenantId) {
          const updated = {
            ...t,
            allowed_domains: t.allowed_domains.filter((d) => d !== domainToRemove),
          };
          if (manageTenant?.id === tenantId) setManageTenant(updated);
          return updated;
        }
        return t;
      })
    );
  };

  const handleRotateKeys = (tenantId: string) => {
    const randomSuffix = Math.random().toString(36).substring(2, 8);
    setTenants((prev) =>
      prev.map((t) => {
        if (t.id === tenantId) {
          const updated: Tenant = {
            ...t,
            api_key_preview: `rk_live_${randomSuffix}••••••••••••••`,
            widget_key_preview: `wk_live_${randomSuffix}••••••••••••••`,
          };
          if (manageTenant?.id === tenantId) setManageTenant(updated);
          return updated;
        }
        return t;
      })
    );
    setKeyRotatedNotice(true);
    setTimeout(() => setKeyRotatedNotice(false), 3000);
  };


  return (
    <div className="space-y-6 sm:space-y-8 max-w-7xl mx-auto">
      {/* Header and Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-white/8">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">Agency Tenants</h2>
          <p className="text-xs text-zinc-400 mt-1">
            Provision keys, configure allowed domains, and monitor live status.
          </p>
        </div>
        <Button onClick={() => setIsCreateOpen(true)} variant="primary" size="md">
          <Plus className="w-4 h-4 mr-1.5" />
          <span>Provision Agency</span>
        </Button>
      </div>

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
                <th className="py-3.5 px-6 font-semibold text-right whitespace-nowrap">Conversations</th>
                <th className="py-3.5 px-6 font-semibold whitespace-nowrap">Status</th>
                <th className="py-3.5 px-6 font-semibold text-right whitespace-nowrap">Controls</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {filteredTenants.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-zinc-500 text-xs">
                    No agency tenants found matching filters.
                  </td>
                </tr>
              ) : (
                filteredTenants.map((tenant) => (
                  <tr key={tenant.id} className="hover:bg-white/[0.02] transition-colors">
                    {/* Name & Slug */}
                    <td className="py-4 px-6 font-medium text-white whitespace-nowrap">
                      <div className="font-semibold text-sm">{tenant.name}</div>
                      <div className="text-[11px] text-zinc-500 font-mono mt-0.5">
                        id: {tenant.id} • slug: /{tenant.slug}
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
                        {tenant.allowed_domains.map((dom) => (
                          <span
                            key={dom}
                            className="bg-[#0B0B0D] px-2 py-0.5 rounded border border-white/5 whitespace-nowrap"
                          >
                            {dom}
                          </span>
                        ))}
                      </div>
                    </td>

                    {/* Conversations */}
                    <td className="py-4 px-6 text-right font-medium text-zinc-200 whitespace-nowrap">
                      {tenant.total_conversations}
                    </td>

                    {/* Status */}
                    <td className="py-4 px-6 whitespace-nowrap">
                      <Badge
                        variant={tenant.status === 'active' ? 'success' : 'danger'}
                        size="sm"
                      >
                        {tenant.status}
                      </Badge>
                    </td>

                    {/* Controls */}
                    <td className="py-4 px-6 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-2">
                        {/* Manage Tenant Drawer */}
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => setManageTenant(tenant)}
                          title="Manage Domains & Key Rotation"
                        >
                          <Settings2 className="w-3.5 h-3.5 text-zinc-400" />
                          <span>Manage</span>
                        </Button>

                        {/* View Keys Modal trigger */}
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => setSelectedTenantKeys(tenant)}
                          title="View API & Widget Keys"
                        >
                          <Key className="w-3.5 h-3.5 text-zinc-400" />
                          <span>Keys</span>
                        </Button>

                        {/* Suspend / Reactivate Switch */}
                        <Button
                          variant={tenant.status === 'active' ? 'danger' : 'secondary'}
                          size="sm"
                          onClick={() => handleToggleStatus(tenant.id)}
                          title={tenant.status === 'active' ? 'Suspend Tenant' : 'Activate Tenant'}
                        >
                          {tenant.status === 'active' ? (
                            <>
                              <PowerOff className="w-3.5 h-3.5 text-rose-400" />
                              <span>Suspend</span>
                            </>
                          ) : (
                            <>
                              <Power className="w-3.5 h-3.5 text-emerald-400" />
                              <span>Activate</span>
                            </>
                          )}
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* MODAL 1: Provision New Agency */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Provision New Agency Tenant"
        description="Creates a strictly isolated tenant with unique DB schema scope, backend API key, and embeddable widget key."
      >
        <form onSubmit={handleCreateTenant} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5">
              Agency Business Name
            </label>
            <input
              type="text"
              required
              value={newAgencyName}
              onChange={(e) => setNewAgencyName(e.target.value)}
              placeholder="e.g. Mayfair Luxury Properties"
              className="w-full px-3.5 py-2.5 bg-[#0B0B0D] border border-white/10 rounded-lg text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-[#F97316] transition-colors"
            />
            {generatedSlug && (
              <p className="text-[11px] text-zinc-500 mt-1 font-mono">
                Assigned slug: <strong className="text-zinc-300">{generatedSlug}</strong>
              </p>
            )}
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5">
              Allowed Domain(s) (Whitelist)
            </label>
            <input
              type="text"
              value={newAllowedDomains}
              onChange={(e) => setNewAllowedDomains(e.target.value)}
              placeholder="e.g. mayfairproperties.co.uk, localhost:5173"
              className="w-full px-3.5 py-2.5 bg-[#0B0B0D] border border-white/10 rounded-lg text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-[#F97316] transition-colors"
            />
            <p className="text-[11px] text-zinc-500 mt-1">
              Comma-separated. Web chat widget will strictly reject visitor connections from unlisted origins.
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5">
              Platform Plan
            </label>
            <select
              value={newPlan}
              onChange={(e) => setNewPlan(e.target.value as any)}
              className="w-full px-3.5 py-2.5 bg-[#0B0B0D] border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-[#F97316] transition-colors"
            >
              <option value="Starter">Starter (1,000 monthly messages)</option>
              <option value="Growth">Growth (10,000 monthly messages)</option>
              <option value="Enterprise">Enterprise (Unlimited + Dedicated Vector Scope)</option>
            </select>
          </div>

          <div className="p-3 rounded-lg bg-[#0B0B0D] border border-white/5 space-y-2">
            <span className="text-[11px] font-semibold text-zinc-400 block uppercase">
              Auto-Generated Keys Preview
            </span>
            <div className="text-xs font-mono text-zinc-400 flex items-center justify-between">
              <span>Backend API Key:</span>
              <span className="text-emerald-400">rk_live_auto_generated</span>
            </div>
            <div className="text-xs font-mono text-zinc-400 flex items-center justify-between">
              <span>Public Widget Key:</span>
              <span className="text-[#F97316]">wk_live_auto_generated</span>
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-3">
            <Button
              type="button"
              variant="ghost"
              size="md"
              onClick={() => setIsCreateOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="md">
              Create & Provision Agency
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL 2: View Keys & Embed Script */}
      {selectedTenantKeys && (
        <Modal
          isOpen={true}
          onClose={() => setSelectedTenantKeys(null)}
          title={`${selectedTenantKeys.name} — Credentials`}
          description="Tenant API credentials and client-side embed tag."
        >
          <div className="space-y-5">
            {/* Backend Key */}
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Backend Private API Key (rk_live_...)
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
                  onClick={() =>
                    copyToClipboard(selectedTenantKeys.api_key_preview, 'rk')
                  }
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
                Used by agency backend servers to ingest knowledge docs & manage CRM leads.
              </p>
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
                  value={selectedTenantKeys.widget_key_preview}
                  className="flex-1 px-3 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs font-mono text-zinc-300"
                />
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() =>
                    copyToClipboard(selectedTenantKeys.widget_key_preview, 'wk')
                  }
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
  src="https://cdn.realestate-ai.com/widget.js"
  data-widget-key="${selectedTenantKeys.widget_key_preview.replace('••••••••••••••', 'demo_secret')}"
  data-tenant-slug="${selectedTenantKeys.slug}"
  async>
</script>`}
                </pre>
                <div className="absolute top-2 right-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() =>
                      copyToClipboard(
                        `<script src="https://cdn.realestate-ai.com/widget.js" data-widget-key="${selectedTenantKeys.widget_key_preview}" async></script>`,
                        'embed'
                      )
                    }
                  >
                    {copiedKey === 'embed' ? (
                      <Check className="w-3 h-3 text-emerald-400" />
                    ) : (
                      <Copy className="w-3 h-3 text-zinc-400" />
                    )}
                  </Button>
                </div>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <Button
                variant="secondary"
                size="md"
                onClick={() => setSelectedTenantKeys(null)}
              >
                Close
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* MODAL 3: Manage Agency (Domains & Keys Rotation) */}
      {manageTenant && (
        <Modal
          isOpen={true}
          onClose={() => setManageTenant(null)}
          title={`Manage ${manageTenant.name}`}
          description={`ID: ${manageTenant.id} • Slug: /${manageTenant.slug}`}
          maxWidth="lg"
        >
          <div className="space-y-6">
            {/* Success notification for key rotation */}
            {keyRotatedNotice && (
              <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center gap-2">
                <Check className="w-4 h-4" />
                <span>Keys successfully rotated! New credentials are now active.</span>
              </div>
            )}

            {/* Allowed Domains Editor */}
            <div className="space-y-3">
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Allowed Origin Domains (Whitelist)
              </label>
              <div className="space-y-2">
                {manageTenant.allowed_domains.map((domain) => (
                  <div
                    key={domain}
                    className="flex items-center justify-between p-2.5 bg-[#0B0B0D] border border-white/5 rounded-lg text-xs"
                  >
                    <span className="font-mono text-zinc-300">{domain}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveDomain(manageTenant.id, domain)}
                      className="text-zinc-500 hover:text-rose-400 p-1 transition-colors cursor-pointer"
                      title="Remove domain"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>

              {/* Add new domain */}
              <div className="flex items-center gap-2 pt-1">
                <input
                  type="text"
                  value={newDomainInput}
                  onChange={(e) => setNewDomainInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddDomain(manageTenant.id);
                    }
                  }}
                  placeholder="e.g. portal.apexproperties.ae"
                  className="flex-1 px-3 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-[#F97316]"
                />
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handleAddDomain(manageTenant.id)}
                >
                  <Plus className="w-3.5 h-3.5 mr-1" />
                  <span>Add Domain</span>
                </Button>
              </div>
            </div>

            {/* Plan Quotas & Usage */}
            <div className="space-y-2 pt-3 border-t border-white/5">
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Subscription Plan Tier
              </label>
              <select
                value={manageTenant.plan}
                onChange={(e) => {
                  const newPlan = e.target.value as any;
                  setTenants((prev) =>
                    prev.map((t) => (t.id === manageTenant.id ? { ...t, plan: newPlan } : t))
                  );
                  setManageTenant({ ...manageTenant, plan: newPlan });
                }}
                className="w-full px-3 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white focus:outline-none focus:border-[#F97316]"
              >
                <option value="Starter">Starter (1,000 monthly messages)</option>
                <option value="Growth">Growth (10,000 monthly messages)</option>
                <option value="Enterprise">Enterprise (Unlimited + Dedicated Vectors)</option>
              </select>
            </div>

            {/* Key Rotation Section */}
            <div className="p-4 rounded-xl bg-[#0B0B0D] border border-white/5 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-semibold text-white">Security Key Rotation</h4>
                  <p className="text-[11px] text-zinc-400 mt-0.5">
                    Generate brand new API key and Widget key if credentials were exposed.
                  </p>
                </div>
                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => handleRotateKeys(manageTenant.id)}
                >
                  <RotateCcw className="w-3.5 h-3.5 mr-1.5" />
                  <span>Rotate Keys</span>
                </Button>
              </div>
              <div className="text-[11px] text-zinc-500 font-mono">
                Current API: {manageTenant.api_key_preview} • Widget: {manageTenant.widget_key_preview}
              </div>
            </div>

            {/* Close Button */}
            <div className="flex justify-end pt-2">
              <Button
                variant="primary"
                size="md"
                onClick={() => setManageTenant(null)}
              >
                Save & Close
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

