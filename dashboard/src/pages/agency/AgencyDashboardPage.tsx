import React, { useState, useEffect } from 'react';
import { Link } from '@tanstack/react-router';
import {
  MessageSquare,
  FileText,
  Sparkles,
  ArrowRight,
  Flame,
  CheckCircle2,
  Copy,
  Check,
  Users,
  Settings,
  Layers,
  ShieldCheck,
  RefreshCw,
} from 'lucide-react';
import { useAuthStore } from '../../store/useAuthStore';
import { apiClient } from '../../api/client';
import { Button } from '../../components/ui/Button';

export const AgencyDashboardPage: React.FC = () => {
  const tenant = useAuthStore((s) => s.tenant);
  const setTenant = useAuthStore((s) => s.setTenant);
  const agencyUser = useAuthStore((s) => s.agencyUser);

  const [copied, setCopied] = useState(false);
  const [docCount, setDocCount] = useState<number | null>(null);
  const [convCount, setConvCount] = useState<number | null>(null);
  const [isLoadingStats, setIsLoadingStats] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function loadWorkspaceData() {
      setIsLoadingStats(true);

      // 1. Ensure fresh tenant details
      if (!tenant) {
        try {
          const freshTenant = await apiClient.agency.getMe();
          if (isMounted) setTenant(freshTenant);
        } catch {
          // Keep current state
        }
      }

      // 2. Fetch live counts from backend
      try {
        const [docsRes, convsRes] = await Promise.allSettled([
          apiClient.agency.listDocuments({ limit: 1 }),
          apiClient.agency.listConversations({ limit: 1 }),
        ]);

        if (isMounted) {
          if (docsRes.status === 'fulfilled') {
            setDocCount(docsRes.value.total);
          } else {
            setDocCount(0);
          }

          if (convsRes.status === 'fulfilled') {
            setConvCount(convsRes.value.items.length);
          } else {
            setConvCount(0);
          }
        }
      } finally {
        if (isMounted) setIsLoadingStats(false);
      }
    }

    loadWorkspaceData();

    return () => {
      isMounted = false;
    };
  }, [tenant, setTenant]);

  const widgetKey = tenant?.widget_key || 'wk_live_...';
  const tenantSlug = tenant?.slug || 'agency';
  const agencyName = tenant?.name || 'Agency Workspace';
  const allowedDomainsText =
    tenant?.allowed_domains && tenant.allowed_domains.length > 0
      ? tenant.allowed_domains.join(', ')
      : '* (All domains permitted)';

  const embedSnippet = `<script
  src="http://localhost:5173/widget.js"
  data-widget-key="${widgetKey}"
  data-tenant-slug="${tenantSlug}"
  async>
</script>`;

  const copyEmbed = () => {
    navigator.clipboard.writeText(embedSnippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const featureTabs = [
    {
      title: 'Conversations',
      path: '/app/conversations',
      icon: MessageSquare,
      color: 'text-[#F97316]',
      bg: 'bg-[#F97316]/10',
      border: 'border-[#F97316]/20',
      description:
        'Live visitor chat inbox with real-time SSE streaming, message history, intent classification, and human agent takeover.',
      status: convCount !== null && convCount > 0 ? `${convCount} Active Threads` : 'Ready for visitors',
    },
    {
      title: 'Leads & CRM',
      path: '/app/leads',
      icon: Users,
      color: 'text-rose-400',
      bg: 'bg-rose-500/10',
      border: 'border-rose-500/20',
      description:
        'AI-qualified buyer leads extracted automatically from conversations with contact details, budgets, and property preferences.',
      status: '0 Qualified Leads',
    },
    {
      title: 'Knowledge Base',
      path: '/app/knowledge',
      icon: FileText,
      color: 'text-blue-400',
      bg: 'bg-blue-500/10',
      border: 'border-blue-500/20',
      description:
        'Upload brochures, floorplans, price lists, and payment schedules. Qdrant vector database indexes chunks for zero-hallucination AI.',
      status: docCount !== null && docCount > 0 ? `${docCount} Documents Indexed` : 'Upload First Document',
    },
    {
      title: 'Widget & Settings',
      path: '/app/settings',
      icon: Settings,
      color: 'text-emerald-400',
      bg: 'bg-emerald-500/10',
      border: 'border-emerald-500/20',
      description:
        'Customize chat launcher colors, concierge greetings, quick suggested questions, and copy your embed snippet.',
      status: 'Customization Active',
    },
  ];

  return (
    <div className="space-y-6 sm:space-y-8 max-w-7xl mx-auto font-sans">
      {/* Top Banner */}
      <div className="overview-hero-card p-6 sm:p-7 rounded-2xl bg-gradient-to-r from-[#1A1A1D] via-[#151517] to-[#151517] border border-white/8 relative overflow-hidden">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 relative z-10">
          <div>
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#F97316]/10 text-[#F97316] text-xs font-semibold mb-2.5 border border-[#F97316]/20">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Multi-Tenant Workspace Isolated</span>
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight leading-tight">
              {agencyName}
            </h2>
            <p className="text-xs text-zinc-400 mt-1 flex items-center gap-1.5">
              <span>Active on whitelisted domains:</span>
              <code className="text-[#F97316] font-mono bg-[#0B0B0D] px-1.5 py-0.5 rounded border border-white/5">
                {allowedDomainsText}
              </code>
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <Link to="/app/knowledge">
              <Button variant="secondary" size="md">
                <FileText className="w-4 h-4 mr-1.5" />
                <span>Upload Documents</span>
              </Button>
            </Link>
            <Link to="/app/conversations">
              <Button variant="primary" size="md">
                <MessageSquare className="w-4 h-4 mr-1.5" />
                <span>Open Live Inbox</span>
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* 4 Focused KPI Cards (Live Real-Time Data) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        {/* KPI 1: Active Inquiries */}
        <div className="p-5 sm:p-6 rounded-xl bg-[#151517] border border-white/8 space-y-2">
          <div className="flex items-center justify-between text-zinc-400 text-xs font-semibold uppercase tracking-wider">
            <span>Conversations</span>
            <div className="w-8 h-8 rounded-lg bg-[#F97316]/10 flex items-center justify-center text-[#F97316]">
              <MessageSquare className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 text-2xl sm:text-3xl font-bold text-white tracking-tight">
            {isLoadingStats ? (
              <RefreshCw className="w-6 h-6 animate-spin text-zinc-500" />
            ) : (
              convCount ?? 0
            )}
          </div>
          <div className="mt-2 text-[11px] text-zinc-400">
            <span>Live visitor threads</span>
          </div>
        </div>

        {/* KPI 2: Hot Qualified Leads */}
        <div className="p-5 sm:p-6 rounded-xl bg-[#151517] border border-white/8 space-y-2">
          <div className="flex items-center justify-between text-zinc-400 text-xs font-semibold uppercase tracking-wider">
            <span>Qualified Leads</span>
            <div className="w-8 h-8 rounded-lg bg-rose-500/10 flex items-center justify-center text-rose-400">
              <Flame className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 text-2xl sm:text-3xl font-bold text-white tracking-tight">
            0
          </div>
          <div className="mt-2 text-[11px] text-zinc-400">
            <span>High intent CRM prospects</span>
          </div>
        </div>

        {/* KPI 3: Indexed Knowledge Docs */}
        <div className="p-5 sm:p-6 rounded-xl bg-[#151517] border border-white/8 space-y-2">
          <div className="flex items-center justify-between text-zinc-400 text-xs font-semibold uppercase tracking-wider">
            <span>Knowledge Base</span>
            <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-400">
              <FileText className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 text-2xl sm:text-3xl font-bold text-white tracking-tight">
            {isLoadingStats ? (
              <RefreshCw className="w-6 h-6 animate-spin text-zinc-500" />
            ) : (
              docCount ?? 0
            )}
          </div>
          <div className="mt-2 text-[11px] text-zinc-400">
            <span>Indexed property brochures</span>
          </div>
        </div>

        {/* KPI 4: Grounded Accuracy */}
        <div className="p-5 sm:p-6 rounded-xl bg-[#151517] border border-white/8 space-y-2">
          <div className="flex items-center justify-between text-zinc-400 text-xs font-semibold uppercase tracking-wider">
            <span>AI Grounding</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 text-2xl sm:text-3xl font-bold text-white tracking-tight">
            100%
          </div>
          <div className="mt-2 text-[11px] text-emerald-400">
            <span>RAG strict vector retrieval</span>
          </div>
        </div>
      </div>

      {/* Workspace Feature Guide & Onboarding Roadmap */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-white flex items-center gap-2">
              <Layers className="w-4 h-4 text-[#F97316]" />
              <span>Workspace Modules & Tab Directory</span>
            </h3>
            <p className="text-xs text-zinc-400 mt-0.5">
              Your isolated agency environment. Data in each section is strictly partitioned to your tenant.
            </p>
          </div>
          {agencyUser && (
            <span className="text-xs text-zinc-400 bg-white/5 border border-white/10 px-2.5 py-1 rounded-full">
              Logged in as: <strong className="text-white capitalize">{agencyUser.role.replace('_', ' ')}</strong>
            </span>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {featureTabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <Link
                key={tab.path}
                to={tab.path}
                className="p-5 rounded-xl bg-[#151517] border border-white/8 hover:border-white/20 transition-all hover:bg-white/[0.02] flex flex-col justify-between group"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2.5">
                      <div className={`w-9 h-9 rounded-lg ${tab.bg} flex items-center justify-center ${tab.color}`}>
                        <Icon className="w-5 h-5" />
                      </div>
                      <h4 className="font-semibold text-sm text-white group-hover:text-[#F97316] transition-colors">
                        {tab.title}
                      </h4>
                    </div>
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-white/5 text-zinc-300 border border-white/5">
                      {tab.status}
                    </span>
                  </div>
                  <p className="text-xs text-zinc-400 leading-relaxed">
                    {tab.description}
                  </p>
                </div>
                <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between text-xs text-[#F97316] font-medium">
                  <span>Open {tab.title}</span>
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </div>
              </Link>
            );
          })}
        </div>
      </div>

      {/* Main Split Section: Integration Code & Setup */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick Setup Guide (2 Cols) */}
        <div className="lg:col-span-2 p-5 sm:p-6 rounded-xl bg-[#151517] border border-white/8 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <h3 className="text-sm sm:text-base font-semibold text-white">
                Getting Started with Your Agency Workspace
              </h3>
            </div>
            <span className="text-xs text-zinc-500 font-mono">Tenant ID: {tenant?.id ? `${tenant.id.slice(0, 8)}...` : 'Active'}</span>
          </div>

          <div className="space-y-3">
            <div className="p-4 rounded-xl bg-[#0B0B0D] border border-white/5 flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-[#F97316]/10 text-[#F97316] flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
                1
              </div>
              <div>
                <h4 className="text-xs font-semibold text-white">Upload Your Property Brochures & Pricing</h4>
                <p className="text-xs text-zinc-400 mt-0.5">
                  Visit the <Link to="/app/knowledge" className="text-[#F97316] hover:underline">Knowledge Base</Link> and upload project PDFs, floorplans, or payment plans. The AI extracts and chunks them automatically.
                </p>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-[#0B0B0D] border border-white/5 flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-[#F97316]/10 text-[#F97316] flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
                2
              </div>
              <div>
                <h4 className="text-xs font-semibold text-white">Embed AI Chat Widget on Your Website</h4>
                <p className="text-xs text-zinc-400 mt-0.5">
                  Copy the snippet on the right into your website&apos;s HTML footer before the closing <code className="text-zinc-300 font-mono text-[11px]">&lt;/body&gt;</code> tag.
                </p>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-[#0B0B0D] border border-white/5 flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-[#F97316]/10 text-[#F97316] flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
                3
              </div>
              <div>
                <h4 className="text-xs font-semibold text-white">Monitor Conversations & Capture Leads</h4>
                <p className="text-xs text-zinc-400 mt-0.5">
                  Incoming chats will stream live into <Link to="/app/conversations" className="text-[#F97316] hover:underline">Conversations</Link>, and buyer contact info will automatically appear in <Link to="/app/leads" className="text-[#F97316] hover:underline">Leads & CRM</Link>.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Website Integration & Embed Helper (1 Col) */}
        <div className="p-5 sm:p-6 rounded-xl bg-[#151517] border border-white/8 space-y-4">
          <div>
            <h3 className="text-sm sm:text-base font-semibold text-white">Website Integration Tag</h3>
            <p className="text-xs text-zinc-400 mt-1">Embed code unique to your agency.</p>
          </div>

          <div className="p-3.5 bg-[#0B0B0D] border border-white/5 rounded-lg space-y-2">
            <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider block">
              HTML Embed Snippet
            </span>
            <pre className="text-[11px] font-mono text-zinc-300 overflow-x-auto whitespace-pre-wrap break-all leading-relaxed">
              {embedSnippet}
            </pre>
            <Button
              variant="secondary"
              size="sm"
              className="w-full mt-2"
              onClick={copyEmbed}
            >
              {copied ? (
                <Check className="w-3.5 h-3.5 text-emerald-400 mr-1.5" />
              ) : (
                <Copy className="w-3.5 h-3.5 text-zinc-400 mr-1.5" />
              )}
              <span>{copied ? 'Copied' : 'Copy Embed Snippet'}</span>
            </Button>
          </div>

          <div className="pt-2 border-t border-white/5 space-y-2">
            <span className="text-xs font-semibold text-zinc-300 block">Workspace Actions</span>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <Link
                to="/app/knowledge"
                className="p-2.5 rounded-lg bg-[#0B0B0D] hover:bg-white/5 border border-white/5 text-zinc-300 transition-colors block text-center"
              >
                Upload Brochure
              </Link>
              <Link
                to="/app/settings"
                className="p-2.5 rounded-lg bg-[#0B0B0D] hover:bg-white/5 border border-white/5 text-zinc-300 transition-colors block text-center"
              >
                Widget Styling
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
