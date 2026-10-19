import React, { useState } from 'react';
import { Link } from '@tanstack/react-router';
import {
  MessageSquare,
  FileText,
  Sparkles,
  ArrowUpRight,
  PhoneCall,
  Flame,
  CheckCircle2,
  Copy,
  Check,
  ChevronRight,
} from 'lucide-react';
import { initialConversations, initialLeads, initialDocuments } from '../../mock/agencyData';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';

export const AgencyDashboardPage: React.FC = () => {
  const [copied, setCopied] = useState(false);

  const hotLeads = initialLeads.filter((l) => l.qualification_score >= 85);
  const embedSnippet = `<script src="https://cdn.realestate-ai.com/widget.js" data-widget-key="wk_live_b21e..." async></script>`;

  const copyEmbed = () => {
    navigator.clipboard.writeText(embedSnippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6 sm:space-y-8 max-w-7xl mx-auto">
      {/* Top Banner */}
      <div className="overview-hero-card p-6 sm:p-7 rounded-2xl bg-gradient-to-r from-[#1A1A1D] via-[#151517] to-[#151517] border border-white/8 relative overflow-hidden">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#F97316]/10 text-[#F97316] text-xs font-semibold mb-2.5 border border-[#F97316]/20">
              <Sparkles className="w-3.5 h-3.5" />
              <span>AI Assistant Online</span>
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight leading-tight">
              Apex Luxury Properties
            </h2>
            <p className="text-xs text-zinc-400 mt-1">
              Active on whitelisted domain <code className="text-[#F97316] font-mono">apexproperties.ae</code>
            </p>
          </div>
          <Link to="/app/conversations" className="shrink-0">
            <Button variant="primary" size="md">
              <MessageSquare className="w-4 h-4 mr-1.5" />
              <span>Open Live Inbox</span>
            </Button>
          </Link>
        </div>
      </div>

      {/* 4 Focused KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        {/* KPI 1: Active Inquiries */}
        <div className="p-5 sm:p-6 rounded-xl bg-[#151517] border border-white/8 space-y-2">
          <div className="flex items-center justify-between text-zinc-400 text-xs font-semibold uppercase tracking-wider">
            <span>Conversations Today</span>
            <div className="w-8 h-8 rounded-lg bg-[#F97316]/10 flex items-center justify-center text-[#F97316]">
              <MessageSquare className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 text-2xl sm:text-3xl font-bold text-white tracking-tight">
            {initialConversations.length}
          </div>
          <div className="mt-2 text-[11px] text-emerald-400 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>2 active visitor sessions</span>
          </div>
        </div>

        {/* KPI 2: Hot Qualified Leads */}
        <div className="p-5 sm:p-6 rounded-xl bg-[#151517] border border-white/8 space-y-2">
          <div className="flex items-center justify-between text-zinc-400 text-xs font-semibold uppercase tracking-wider">
            <span>Hot CRM Leads</span>
            <div className="w-8 h-8 rounded-lg bg-rose-500/10 flex items-center justify-center text-rose-400">
              <Flame className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 text-2xl sm:text-3xl font-bold text-white tracking-tight">
            {hotLeads.length}
          </div>
          <div className="mt-2 text-[11px] text-zinc-400">
            <span>Score &ge; 85/100 (high intent)</span>
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
            {initialDocuments.length}
          </div>
          <div className="mt-2 text-[11px] text-zinc-400">
            <span>280 chunks indexed in Qdrant</span>
          </div>
        </div>

        {/* KPI 4: Grounded Accuracy */}
        <div className="p-5 sm:p-6 rounded-xl bg-[#151517] border border-white/8 space-y-2">
          <div className="flex items-center justify-between text-zinc-400 text-xs font-semibold uppercase tracking-wider">
            <span>AI Grounding Rate</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 text-2xl sm:text-3xl font-bold text-white tracking-tight">
            99.2%
          </div>
          <div className="mt-2 text-[11px] text-emerald-400">
            <span>Strict zero-hallucination</span>
          </div>
        </div>
      </div>

      {/* Main Split Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Hot Leads Table (2 Cols) */}
        <div className="lg:col-span-2 p-5 sm:p-6 rounded-xl bg-[#151517] border border-white/8 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Flame className="w-4 h-4 text-rose-400" />
              <h3 className="text-sm sm:text-base font-semibold text-white">
                Hot Prospective Buyers
              </h3>
            </div>
            <Link
              to="/app/leads"
              className="text-xs text-[#F97316] hover:text-[#EA580C] flex items-center gap-1 font-medium"
            >
              <span>View All Leads</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="space-y-3">
            {hotLeads.map((lead) => (
              <div
                key={lead.id}
                className="p-4 sm:p-4.5 rounded-xl bg-[#0B0B0D] border border-white/5 hover:border-white/10 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm text-white">{lead.name}</span>
                    <Badge variant="brand" size="sm">
                      Score: {lead.qualification_score}/100
                    </Badge>
                  </div>
                  <div className="text-xs text-zinc-400">
                    <strong className="text-zinc-200">{lead.property_type}</strong> • {lead.preferred_location}
                  </div>
                  <div className="text-[11px] text-zinc-500 flex items-center gap-2 flex-wrap">
                    <span className="flex items-center gap-1">
                      <PhoneCall className="w-3 h-3 text-zinc-400" />
                      {lead.phone}
                    </span>
                    <span>•</span>
                    <span className="font-mono text-emerald-400">{lead.budget}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <Link to="/app/conversations">
                    <Button variant="secondary" size="sm">
                      <span>Transcript</span>
                      <ChevronRight className="w-3.5 h-3.5 ml-1" />
                    </Button>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Assistant Status & Embed Helper (1 Col) */}
        <div className="p-5 sm:p-6 rounded-xl bg-[#151517] border border-white/8 space-y-5">
          <div>
            <h3 className="text-sm sm:text-base font-semibold text-white">Website Integration</h3>
            <p className="text-xs text-zinc-400 mt-1">Embed code for host website.</p>
          </div>

          <div className="p-3.5 bg-[#0B0B0D] border border-white/5 rounded-lg space-y-2">
            <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider block">
              HTML Embed Tag
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
              <span>{copied ? 'Copied' : 'Copy Embed Code'}</span>
            </Button>
          </div>

          <div className="pt-2 border-t border-white/5 space-y-2">
            <span className="text-xs font-semibold text-zinc-300 block">Shortcuts</span>
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
