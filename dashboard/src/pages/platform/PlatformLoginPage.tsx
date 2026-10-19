import React, { useState } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { ShieldCheck, Lock, Mail, ArrowRight, AlertCircle } from 'lucide-react';
import { Button } from '../../components/ui/Button';

export const PlatformLoginPage: React.FC = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('superadmin@realestate-ai.internal');
  const [password, setPassword] = useState('••••••••••••');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
      navigate({ to: '/platform' });
    }, 400);
  };

  return (
    <div className="min-h-screen bg-[#0B0B0D] flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background warm luxury glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[350px] bg-gradient-to-b from-[#F97316]/10 via-[#3A1F10]/20 to-transparent blur-3xl pointer-events-none rounded-full" />

      <div className="w-full max-w-md relative z-10">
        {/* Header Branding */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br from-[#F97316] to-[#C2410C] text-white font-bold text-xl mb-4 shadow-lg shadow-[#F97316]/25 border border-white/10">
            R
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Platform Super Admin</h1>
          <p className="text-xs text-zinc-400 mt-1.5 flex items-center justify-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-[#F97316]" />
            Restricted Infrastructure Gateway
          </p>
        </div>

        {/* Login Box */}
        <div className="bg-[#151517] border border-white/10 rounded-2xl p-7 shadow-2xl backdrop-blur-xl">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-2">
                Platform Admin Email
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="admin@platform.internal"
                  className="w-full pl-10 pr-4 py-2.5 bg-[#0B0B0D] border border-white/10 rounded-lg text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-[#F97316] focus:ring-1 focus:ring-[#F97316] transition-colors"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400">
                  Password
                </label>
                <span className="text-[11px] text-zinc-500">MFA Enforced</span>
              </div>
              <div className="relative">
                <Lock className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="••••••••••••"
                  className="w-full pl-10 pr-4 py-2.5 bg-[#0B0B0D] border border-white/10 rounded-lg text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-[#F97316] focus:ring-1 focus:ring-[#F97316] transition-colors"
                />
              </div>
            </div>

            <div className="p-3 rounded-lg bg-white/[0.02] border border-white/5 flex items-start gap-2 text-xs text-zinc-400">
              <AlertCircle className="w-4 h-4 text-[#F97316] shrink-0 mt-0.5" />
              <span>
                Isolated login. Grants system-wide tenant control and API provisioning.
              </span>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="w-full mt-2"
              disabled={isLoading}
            >
              <span>{isLoading ? 'Authenticating...' : 'Sign In to Super Admin'}</span>
              <ArrowRight className="w-4 h-4 ml-1" />
            </Button>
          </form>
        </div>

        {/* Quick Footer hint */}
        <div className="text-center mt-6">
          <p className="text-xs text-zinc-600">
            RealEstate AI Platform Control • Multi-Tenant Core V1
          </p>
        </div>
      </div>
    </div>
  );
};
