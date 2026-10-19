import React, { useState } from 'react';
import { useNavigate, Link } from '@tanstack/react-router';
import { Lock, Mail, ArrowRight, Building2, ShieldAlert } from 'lucide-react';
import { Button } from '../../components/ui/Button';

export const AgencyLoginPage: React.FC = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('agent@apexproperties.ae');
  const [password, setPassword] = useState('••••••••••••');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
      navigate({ to: '/app' });
    }, 400);
  };

  return (
    <div className="min-h-screen bg-[#0B0B0D] flex items-center justify-center p-4 relative">
      <div className="w-full max-w-md relative z-10">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-zinc-800 text-white font-bold text-xl mb-4 border border-white/10">
            <Building2 className="w-6 h-6 text-[#F97316]" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Agency Portal</h1>
          <p className="text-xs text-zinc-400 mt-1.5">
            Sign in to manage your AI assistant, leads, and property knowledge base.
          </p>
        </div>

        {/* Card */}
        <div className="bg-[#151517] border border-white/10 rounded-2xl p-7 shadow-2xl">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-2">
                Work Email
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="agent@agency.com"
                  className="w-full pl-10 pr-4 py-2.5 bg-[#0B0B0D] border border-white/10 rounded-lg text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-zinc-500 transition-colors"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-2">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="••••••••••••"
                  className="w-full pl-10 pr-4 py-2.5 bg-[#0B0B0D] border border-white/10 rounded-lg text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-zinc-500 transition-colors"
                />
              </div>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="w-full mt-2"
              disabled={isLoading}
            >
              <span>{isLoading ? 'Signing in...' : 'Sign In to Workspace'}</span>
              <ArrowRight className="w-4 h-4 ml-1" />
            </Button>
          </form>
        </div>

        {/* Discrete Platform Switch */}
        <div className="text-center mt-6">
          <Link
            to="/platform/login"
            className="inline-flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            <ShieldAlert className="w-3.5 h-3.5 text-[#F97316]" />
            <span>Are you a Platform Super Admin?</span>
          </Link>
        </div>
      </div>
    </div>
  );
};
