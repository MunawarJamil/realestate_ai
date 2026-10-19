import React, { useState } from 'react';
import { useNavigate, Link } from '@tanstack/react-router';
import { KeyRound, ArrowRight, Building2, ShieldAlert, AlertCircle, CheckCircle2 } from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { useAuthStore } from '../../store/useAuthStore';
import { apiClient, ApiError } from '../../api/client';

export const AgencyLoginPage: React.FC = () => {
  const navigate = useNavigate();
  const setApiKey = useAuthStore((s) => s.setApiKey);
  const setTenant = useAuthStore((s) => s.setTenant);
  const existingKey = useAuthStore((s) => s.apiKey);

  const [apiKeyInput, setApiKeyInput] = useState(
    existingKey || ''
  );
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successNotice, setSuccessNotice] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKeyInput.trim()) {
      setErrorMessage('Please provide an Agency API Key (e.g., rk_live_...).');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    // Save in Zustand store first so apiClient attaches it as X-API-Key
    setApiKey(apiKeyInput.trim());

    try {
      // Validate by querying the authenticated tenant profile
      const tenant = await apiClient.agency.getMe();
      setTenant(tenant);
      setSuccessNotice(`Welcome back, ${tenant.name}!`);
      setTimeout(() => {
        navigate({ to: '/app' });
      }, 350);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.status === 401) {
          setErrorMessage('Invalid Agency API Key (401 Unauthorized). Verify your key from Super Admin.');
        } else {
          setErrorMessage(`Authentication failed (${err.status}): ${err.message}`);
        }
      } else {
        setErrorMessage(
          'Could not reach backend API at http://localhost:8000. Ensure FastAPI server is running.'
        );
      }
    } finally {
      setIsLoading(false);
    }
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
              <div className="flex items-center justify-between mb-2">
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400">
                  Agency API Key (X-API-Key)
                </label>
                <span className="text-[11px] text-zinc-500 font-mono">rk_live_...</span>
              </div>
              <div className="relative">
                <KeyRound className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  value={apiKeyInput}
                  onChange={(e) => {
                    setApiKeyInput(e.target.value);
                    setErrorMessage(null);
                  }}
                  required
                  placeholder="Paste your agency API key..."
                  className="w-full pl-10 pr-4 py-2.5 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs font-mono text-white placeholder-zinc-600 focus:outline-none focus:border-[#F97316] transition-colors"
                />
              </div>
              <p className="text-[11px] text-zinc-500 mt-1.5">
                Generated during agency onboarding in the Super Admin platform.
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
                <span>{successNotice}</span>
              </div>
            )}

            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="w-full mt-2"
              disabled={isLoading || Boolean(successNotice)}
            >
              <span>{isLoading ? 'Verifying Agency...' : 'Sign In to Workspace'}</span>
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
