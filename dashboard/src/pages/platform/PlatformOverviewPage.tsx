import React from 'react';
import { Link } from '@tanstack/react-router';
import {
  Building2,
  MessageSquare,
  Activity,
  Layers,
  CheckCircle2,
  ArrowUpRight,
  Plus,
} from 'lucide-react';
import { initialTenants, platformMetrics } from '../../mock/tenantsData';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';

export const PlatformOverviewPage: React.FC = () => {
  const activeTenants = initialTenants.filter((t) => t.status === 'active');

  const services = [
    { name: 'PostgreSQL 16', role: 'Multi-Tenant DB', status: 'Operational', latency: '2ms' },
    { name: 'Redis 7', role: 'ARQ & Rate Limit', status: 'Operational', latency: '1ms' },
    { name: 'Qdrant Vector DB', role: 'Vector Search', status: 'Operational', latency: '4ms' },
    { name: 'OpenRouter AI', role: 'Streaming LLM', status: 'Operational', latency: '310ms' },
  ];

  return (
    <div className="space-y-6 sm:space-y-8 max-w-7xl mx-auto">
      {/* Top Banner / Welcome */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-white/8">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight leading-tight">
            Platform Infrastructure
          </h2>
          <p className="text-xs text-zinc-400 mt-1">
            Real-time status, active agencies, and AI conversation volume.
          </p>
        </div>
        <Link to="/platform/tenants">
          <Button variant="primary" size="md">
            <Plus className="w-4 h-4 mr-1.5" />
            <span>Onboard Agency</span>
          </Button>
        </Link>
      </div>

      {/* 4 Focused KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        {/* Card 1: Active Tenants */}
        <div className="p-5 sm:p-6 rounded-xl bg-[#151517] border border-white/8 hover:border-white/15 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Active Agencies
            </span>
            <div className="w-8 h-8 rounded-lg bg-[#F97316]/10 flex items-center justify-center text-[#F97316]">
              <Building2 className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
              {activeTenants.length}
            </span>
            <span className="text-xs text-zinc-500">of {initialTenants.length} total</span>
          </div>
          <div className="mt-3 text-[11px] text-emerald-400 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Multi-tenant isolation verified</span>
          </div>
        </div>

        {/* Card 2: Live Embed Widgets */}
        <div className="p-5 sm:p-6 rounded-xl bg-[#151517] border border-white/8 hover:border-white/15 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Live Web Widgets
            </span>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400">
              <Layers className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
              {platformMetrics.activeWidgets}
            </span>
            <span className="text-xs text-zinc-500">whitelisted origins</span>
          </div>
          <div className="mt-3 text-[11px] text-zinc-400">
            <span>Domain whitelisting enforced</span>
          </div>
        </div>

        {/* Card 3: 24h AI Chat Traffic */}
        <div className="p-5 sm:p-6 rounded-xl bg-[#151517] border border-white/8 hover:border-white/15 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
              24h AI Messages
            </span>
            <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-400">
              <MessageSquare className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
              {platformMetrics.totalMessages24h.toLocaleString()}
            </span>
            <span className="text-xs text-emerald-400 font-medium">+18% today</span>
          </div>
          <div className="mt-3 text-[11px] text-zinc-400">
            <span>Grounded RAG stream active</span>
          </div>
        </div>

        {/* Card 4: AI Engine Latency */}
        <div className="p-5 sm:p-6 rounded-xl bg-[#151517] border border-white/8 hover:border-white/15 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Avg TTFT Latency
            </span>
            <div className="w-8 h-8 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-400">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
              {platformMetrics.avgResponseTimeMs}ms
            </span>
            <span className="text-xs text-zinc-500">to first token</span>
          </div>
          <div className="mt-3 text-[11px] text-emerald-400">
            <span>Fast token streaming</span>
          </div>
        </div>
      </div>

      {/* Two Column Layout: Core Services Status & Recent Tenant Volume */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Core Services Health (1 col) */}
        <div className="p-5 sm:p-6 rounded-xl bg-[#151517] border border-white/8 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">Cluster Telemetry</h3>
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          </div>
          <div className="space-y-3">
            {services.map((svc) => (
              <div
                key={svc.name}
                className="p-3 sm:p-3.5 rounded-lg bg-[#0B0B0D] border border-white/5 flex items-center justify-between text-xs"
              >
                <div>
                  <div className="font-semibold text-zinc-200">{svc.name}</div>
                  <div className="text-[11px] text-zinc-500">{svc.role}</div>
                </div>
                <div className="text-right">
                  <span className="text-emerald-400 font-medium block">{svc.status}</span>
                  <span className="text-[10px] text-zinc-600 font-mono">{svc.latency}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Active Tenants Snapshot (2 cols) */}
        <div className="lg:col-span-2 p-5 sm:p-6 rounded-xl bg-[#151517] border border-white/8 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">Top Active Agencies</h3>
            <Link
              to="/platform/tenants"
              className="text-xs text-[#F97316] hover:text-[#EA580C] flex items-center gap-1 font-medium"
            >
              <span>Manage All</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="w-full overflow-x-auto rounded-lg border border-white/5">
            <table className="w-full text-left text-xs min-w-[560px]">
              <thead>
                <tr className="border-b border-white/8 text-zinc-500 uppercase tracking-wider text-[11px] bg-white/[0.01]">
                  <th className="py-3 px-4 font-semibold whitespace-nowrap">Agency</th>
                  <th className="py-3 px-4 font-semibold whitespace-nowrap">Allowed Domain(s)</th>
                  <th className="py-3 px-4 font-semibold text-right whitespace-nowrap">Conversations</th>
                  <th className="py-3 px-4 font-semibold text-right whitespace-nowrap">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {initialTenants.map((tenant) => (
                  <tr key={tenant.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-3.5 px-4 font-medium text-white whitespace-nowrap">
                      <div>{tenant.name}</div>
                      <div className="text-[11px] text-zinc-500 font-mono">/{tenant.slug}</div>
                    </td>
                    <td className="py-3.5 px-4 text-zinc-400 font-mono text-[11px] whitespace-nowrap">
                      {tenant.allowed_domains[0] || 'Any'}
                      {tenant.allowed_domains.length > 1 && (
                        <span className="text-zinc-500 ml-1">+{tenant.allowed_domains.length - 1}</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right font-medium text-zinc-200 whitespace-nowrap">
                      {tenant.total_conversations}
                    </td>
                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      <Badge
                        variant={tenant.status === 'active' ? 'success' : 'danger'}
                        size="sm"
                      >
                        {tenant.status}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
