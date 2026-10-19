import React, { useState } from 'react';
import {
  Server,
  ShieldAlert,
  RefreshCw,
  Sliders,
  CheckCircle2,
} from 'lucide-react';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';

export const SystemGatewayPage: React.FC = () => {
  const [globalKillSwitch, setGlobalKillSwitch] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => setIsRefreshing(false), 500);
  };

  const services = [
    {
      name: 'PostgreSQL 16 Engine',
      type: 'Database',
      status: 'healthy',
      metrics: 'Pool: 12/50 conns • 2.1ms',
      description: 'Tenants, conversations, and messages with foreign key isolation',
    },
    {
      name: 'Redis 7 (ARQ & Sliding Rate Limit)',
      type: 'Cache & Queue',
      status: 'healthy',
      metrics: 'Memory: 42MB • 0.9ms',
      description: 'Sliding-window IP rate limiter & async document chunk workers',
    },
    {
      name: 'Qdrant Vector Engine',
      type: 'Vector Database',
      status: 'healthy',
      metrics: 'Collections: 1 • 3.8ms',
      description: 'Cos-similarity RAG search for property brochures & floorplans',
    },
    {
      name: 'OpenRouter AI Provider',
      type: 'LLM Gateway',
      status: 'healthy',
      metrics: 'stepfun/step-3.5-flash:free • 310ms',
      description: 'Server-Sent Events streaming token generation pipeline',
    },
  ];

  return (
    <div className="space-y-6 sm:space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-white/8">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">System & AI Gateway</h2>
          <p className="text-xs text-zinc-400 mt-1">
            Cluster telemetry, rate limit controls, and emergency circuit breaker.
          </p>
        </div>
        <Button
          variant="secondary"
          size="md"
          onClick={handleRefresh}
          disabled={isRefreshing}
        >
          <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${isRefreshing ? 'animate-spin' : ''}`} />
          <span>{isRefreshing ? 'Pinging...' : 'Ping Cluster'}</span>
        </Button>
      </div>

      {/* EMERGENCY CIRCUIT BREAKER BANNER */}
      <div
        className={`p-5 sm:p-6 rounded-xl border transition-all ${
          globalKillSwitch
            ? 'bg-rose-950/30 border-rose-500/40'
            : 'bg-[#151517] border-white/8'
        }`}
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3.5">
            <div
              className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${
                globalKillSwitch
                  ? 'bg-rose-500/20 text-rose-400'
                  : 'bg-amber-500/10 text-amber-400'
              }`}
            >
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm sm:text-base font-semibold text-white">
                  Global AI Traffic Circuit Breaker
                </h3>
                <Badge variant={globalKillSwitch ? 'danger' : 'success'} size="sm">
                  {globalKillSwitch ? 'Traffic Suspended' : 'Live & Active'}
                </Badge>
              </div>
              <p className="text-xs text-zinc-400 mt-1">
                Emergency kill-switch to pause public widget streams and LLM completions.
              </p>
            </div>
          </div>
          <Button
            variant={globalKillSwitch ? 'primary' : 'danger'}
            size="md"
            onClick={() => setGlobalKillSwitch(!globalKillSwitch)}
            className="shrink-0"
          >
            {globalKillSwitch ? 'Deactivate Kill Switch' : 'Engage Emergency Pause'}
          </Button>
        </div>
      </div>

      {/* Core Services Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
        {services.map((svc) => (
          <div
            key={svc.name}
            className="p-5 sm:p-6 rounded-xl bg-[#151517] border border-white/8 space-y-3"
          >
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <Server className="w-4 h-4 text-[#F97316]" />
                  <h4 className="text-sm font-semibold text-white">{svc.name}</h4>
                </div>
                <span className="text-[11px] text-zinc-500 font-medium block mt-0.5">
                  {svc.type}
                </span>
              </div>
              <Badge variant="success" size="sm">
                <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                Operational
              </Badge>
            </div>

            <p className="text-xs text-zinc-400 leading-relaxed">{svc.description}</p>

            <div className="pt-2 border-t border-white/5 flex items-center justify-between text-xs font-mono text-zinc-300">
              <span className="text-zinc-500 text-[11px]">Telemetry:</span>
              <span className="bg-[#0B0B0D] px-2.5 py-1 rounded border border-white/5 text-[11px]">
                {svc.metrics}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Global Rate Limiting & Safety Parameters */}
      <div className="p-5 sm:p-6 rounded-xl bg-[#151517] border border-white/8 space-y-4">
        <div className="flex items-center gap-2">
          <Sliders className="w-4 h-4 text-[#F97316]" />
          <h3 className="text-sm font-semibold text-white">
            Sliding-Window Rate Limits & Quotas
          </h3>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6 text-xs">
          <div className="p-4 rounded-lg bg-[#0B0B0D] border border-white/5 space-y-1.5">
            <span className="text-zinc-500 font-semibold uppercase text-[10px] tracking-wider block">
              Public Client IP
            </span>
            <div className="text-base sm:text-lg font-bold text-white">60 req / min</div>
            <p className="text-[11px] text-zinc-500">
              Redis sliding-window rate limiting on embed endpoints.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-[#0B0B0D] border border-white/5 space-y-1.5">
            <span className="text-zinc-500 font-semibold uppercase text-[10px] tracking-wider block">
              Concurrent SSE Streams
            </span>
            <div className="text-base sm:text-lg font-bold text-white">20 per Tenant</div>
            <p className="text-[11px] text-zinc-500">
              Maximum active streaming conversations before queuing.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-[#0B0B0D] border border-white/5 space-y-1.5">
            <span className="text-zinc-500 font-semibold uppercase text-[10px] tracking-wider block">
              Context Chunk Budget
            </span>
            <div className="text-base sm:text-lg font-bold text-white">Top-5 Vectors</div>
            <p className="text-[11px] text-zinc-500">
              Cosine similarity threshold 0.72 for grounding.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
