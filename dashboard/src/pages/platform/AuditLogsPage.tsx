import React, { useState } from 'react';
import { ShieldCheck, Search, Filter, Clock, CheckCircle2 } from 'lucide-react';
import { Badge } from '../../components/ui/Badge';

interface AuditLog {
  id: string;
  timestamp: string;
  action: 'TENANT_PROVISIONED' | 'KEY_ROTATED' | 'TENANT_SUSPENDED' | 'TENANT_ACTIVATED' | 'DOMAIN_WHITELIST_MODIFIED';
  actor: string;
  target_tenant: string;
  ip_address: string;
  status: 'SUCCESS' | 'FLAGGED';
  details: string;
}

const mockLogs: AuditLog[] = [
  {
    id: 'log-501',
    timestamp: '2026-10-18 20:34',
    action: 'TENANT_PROVISIONED',
    actor: 'superadmin@platform.internal',
    target_tenant: 'Elysium Palm Residences',
    ip_address: '192.168.1.104',
    status: 'SUCCESS',
    details: 'Enterprise plan initialized with dedicated vector scope',
  },
  {
    id: 'log-502',
    timestamp: '2026-10-18 18:22',
    action: 'DOMAIN_WHITELIST_MODIFIED',
    actor: 'superadmin@platform.internal',
    target_tenant: 'Apex Luxury Properties',
    ip_address: '192.168.1.104',
    status: 'SUCCESS',
    details: 'Added localhost:5173 to allowed origins',
  },
  {
    id: 'log-503',
    timestamp: '2026-10-18 14:15',
    action: 'TENANT_SUSPENDED',
    actor: 'superadmin@platform.internal',
    target_tenant: 'Skyline Capital Realty',
    ip_address: '192.168.1.104',
    status: 'SUCCESS',
    details: 'Suspension applied due to subscription review',
  },
  {
    id: 'log-504',
    timestamp: '2026-10-17 11:05',
    action: 'KEY_ROTATED',
    actor: 'superadmin@platform.internal',
    target_tenant: 'Belgravia Prime Estates',
    ip_address: '192.168.1.104',
    status: 'SUCCESS',
    details: 'Zero-downtime key rotation executed',
  },
  {
    id: 'log-505',
    timestamp: '2026-10-17 09:12',
    action: 'TENANT_PROVISIONED',
    actor: 'superadmin@platform.internal',
    target_tenant: 'Belgravia Prime Estates',
    ip_address: '192.168.1.104',
    status: 'SUCCESS',
    details: 'Growth plan initialized with 10k monthly messages',
  },
];

export const AuditLogsPage: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedAction, setSelectedAction] = useState<string>('ALL');

  const filteredLogs = mockLogs.filter((log) => {
    const matchesSearch =
      log.target_tenant.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.action.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.details.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesAction = selectedAction === 'ALL' || log.action === selectedAction;
    return matchesSearch && matchesAction;
  });

  const getActionBadge = (action: AuditLog['action']) => {
    switch (action) {
      case 'TENANT_PROVISIONED':
        return <Badge variant="brand" size="sm">PROVISIONED</Badge>;
      case 'KEY_ROTATED':
        return <Badge variant="warning" size="sm">KEY ROTATED</Badge>;
      case 'TENANT_SUSPENDED':
        return <Badge variant="danger" size="sm">SUSPENDED</Badge>;
      case 'TENANT_ACTIVATED':
        return <Badge variant="success" size="sm">ACTIVATED</Badge>;
      case 'DOMAIN_WHITELIST_MODIFIED':
        return <Badge variant="neutral" size="sm">WHITELIST</Badge>;
    }
  };

  return (
    <div className="space-y-6 sm:space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-white/8">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">Audit & Security Logs</h2>
          <p className="text-xs text-zinc-400 mt-1">
            Immutable log of administrative events, key rotations, and tenant mutations.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-lg shrink-0">
          <ShieldCheck className="w-4 h-4" />
          <span>Audit Logging Active</span>
        </div>
      </div>

      {/* Search & Action Filter */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3.5 sm:p-4 rounded-xl bg-[#151517] border border-white/8">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search audit records by tenant or action..."
            className="w-full pl-10 pr-4 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-[#F97316] transition-colors"
          />
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Filter className="w-3.5 h-3.5 text-zinc-500" />
          <select
            value={selectedAction}
            onChange={(e) => setSelectedAction(e.target.value)}
            className="px-3 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white focus:outline-none focus:border-[#F97316]"
          >
            <option value="ALL">All Event Types</option>
            <option value="TENANT_PROVISIONED">Tenant Provisioned</option>
            <option value="KEY_ROTATED">Key Rotated</option>
            <option value="TENANT_SUSPENDED">Tenant Suspended</option>
            <option value="DOMAIN_WHITELIST_MODIFIED">Domain Whitelist</option>
          </select>
        </div>
      </div>

      {/* Logs Table */}
      <div className="rounded-xl bg-[#151517] border border-white/8 overflow-hidden shadow-lg">
        <div className="w-full overflow-x-auto">
          <table className="w-full text-left text-xs min-w-[840px]">
            <thead>
              <tr className="border-b border-white/8 text-zinc-400 uppercase tracking-wider text-[11px] bg-white/[0.01]">
                <th className="py-3.5 px-4 sm:px-6 font-semibold whitespace-nowrap">Timestamp</th>
                <th className="py-3.5 px-4 sm:px-6 font-semibold whitespace-nowrap">Action</th>
                <th className="py-3.5 px-4 sm:px-6 font-semibold whitespace-nowrap">Target Tenant</th>
                <th className="py-3.5 px-4 sm:px-6 font-semibold">Details</th>
                <th className="py-3.5 px-4 sm:px-6 font-semibold whitespace-nowrap">Actor & IP</th>
                <th className="py-3.5 px-4 sm:px-6 font-semibold text-right whitespace-nowrap">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {filteredLogs.map((log) => (
                <tr key={log.id} className="hover:bg-white/[0.02] transition-colors">
                  <td className="py-4 px-4 sm:px-6 text-zinc-400 font-mono text-[11px] whitespace-nowrap">
                    <div className="flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 text-zinc-500" />
                      <span>{log.timestamp}</span>
                    </div>
                  </td>
                  <td className="py-4 px-4 sm:px-6 whitespace-nowrap">
                    {getActionBadge(log.action)}
                  </td>
                  <td className="py-4 px-4 sm:px-6 font-medium text-white whitespace-nowrap">
                    {log.target_tenant}
                  </td>
                  <td className="py-4 px-4 sm:px-6 text-zinc-300 max-w-xs leading-relaxed">
                    {log.details}
                  </td>
                  <td className="py-4 px-4 sm:px-6 text-zinc-400 text-[11px] font-mono whitespace-nowrap">
                    <div>{log.actor.split('@')[0]}</div>
                    <div className="text-zinc-600">{log.ip_address}</div>
                  </td>
                  <td className="py-4 px-4 sm:px-6 text-right whitespace-nowrap">
                    <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400 font-medium">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      {log.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
