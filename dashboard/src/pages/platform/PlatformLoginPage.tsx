import React, { useState } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { ShieldCheck, KeyRound, ArrowRight, AlertCircle, CheckCircle2 } from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { useAuthStore } from '../../store/useAuthStore';
import { apiClient, ApiError } from '../../api/client';

export const PlatformLoginPage: React.FC = () => {
  const navigate = useNavigate();
  const setAdminKey = useAuthStore((s) => s.setAdminKey);
  const existingKey = useAuthStore((s) => s.adminKey);

  const [adminKey, setKeyInput] = useState(
    existingKey || '57a6447506728bbbcdb81e1493cc04229a4947d1b55d77beb686a507e7781dca'
  );
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successNotice, setSuccessNotice] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!adminKey.trim()) {
      setErrorMessage('Please provide a valid Admin API Key.');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    // Save key in store first so apiClient attaches it as X-Admin-Key
    setAdminKey(adminKey.trim());

    try {
      // Validate key against live backend endpoint
      await apiClient.admin.listTenants({ limit: 1 });
      setSuccessNotice(true);
      setTimeout(() => {
        navigate({ to: '/platform' });
      }, 300);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.status === 403) {
          setErrorMessage('Invalid Admin Key (403 Forbidden). Verification failed.');
        } else {
          setErrorMessage(`Authentication failed (${err.status}): ${err.message}`);
        }
      } else {
        setErrorMessage(
          'Could not reach backend API server at http://localhost:8000. Ensure FastAPI is running.'
        );
      }
    } finally {
      setIsLoading(false);
    }
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
              <div className="flex items-center justify-between mb-2">
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400">
                  Master Admin Key (X-Admin-Key)
                </label>
                <span className="text-[11px] text-[#F97316]">Hardware / Root Safe</span>
              </div>
              <div className="relative">
                <KeyRound className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  value={adminKey}
                  onChange={(e) => {
                    setKeyInput(e.target.value);
                    setErrorMessage(null);
                  }}
                  required
                  placeholder="Paste 64-char hex admin key..."
                  className="w-full pl-10 pr-4 py-2.5 bg-[#0B0B0D] border border-white/10 rounded-lg text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-[#F97316] focus:ring-1 focus:ring-[#F97316] transition-colors font-mono text-xs"
                />
              </div>
              <p className="text-[11px] text-zinc-500 mt-1.5">
                Configured via <code className="text-zinc-400">ADMIN_API_KEY</code> in root <code className="text-zinc-400">.env</code>.
              </p>
            </div>

            {errorMessage && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 flex items-start gap-2 text-xs text-red-400">
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                <span>{errorMessage}</span>
              </div>
            )}

            {successNotice && (
              <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center gap-2 text-xs text-emerald-400">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>Authentication verified. Redirecting to platform control...</span>
              </div>
            )}

            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="w-full mt-2"
              disabled={isLoading || successNotice}
            >
              <span>{isLoading ? 'Verifying with Backend...' : 'Authenticate Super Admin'}</span>
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
