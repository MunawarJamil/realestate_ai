import React, { useState } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { ShieldCheck, KeyRound, ArrowRight, AlertCircle, CheckCircle2, Mail, Lock, Sparkles } from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { useAuthStore } from '../../store/useAuthStore';
import { apiClient, ApiError } from '../../api/client';

export const PlatformLoginPage: React.FC = () => {
  const navigate = useNavigate();
  const setPlatformAuth = useAuthStore((s) => s.setPlatformAuth);
  const setAdminKey = useAuthStore((s) => s.setAdminKey);

  const [authMode, setAuthMode] = useState<'credentials' | 'apikey'>('credentials');

  // Credentials mode (clean initial state to prevent browser key autofill collision)
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  // Key mode
  const [adminKey, setKeyInput] = useState('');

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successNotice, setSuccessNotice] = useState(false);

  const fillSuperAdminDemo = () => {
    setEmail('admin@platform.internal');
    setPassword('SuperAdminPassword123!');
    setErrorMessage(null);
  };

  const fillMasterKeyDemo = () => {
    setKeyInput('57a6447506728bbbcdb81e1493cc04229a4947d1b55d77beb686a507e7781dca');
    setErrorMessage(null);
  };

  const handleCredentialsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setErrorMessage('Please enter both platform email and password.');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const res = await apiClient.auth.platformLogin({
        email: email.trim(),
        password,
      });

      setPlatformAuth(res.tokens, res.user);
      setSuccessNotice(true);
      setTimeout(() => {
        navigate({ to: '/platform' });
      }, 350);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.status === 403) {
          setErrorMessage(err.message || 'Access Denied: Agency accounts cannot access the Platform portal.');
        } else if (err.status === 401) {
          setErrorMessage('Invalid platform credentials. Please verify your email and password.');
        } else {
          setErrorMessage(`Authentication failed (${err.status}): ${err.message}`);
        }
      } else {
        setErrorMessage('Could not connect to FastAPI server at http://localhost:8000.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!adminKey.trim()) {
      setErrorMessage('Please provide a valid Admin API Key.');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    setAdminKey(adminKey.trim());

    try {
      await apiClient.admin.listTenants({ limit: 1 });
      setSuccessNotice(true);
      setTimeout(() => {
        navigate({ to: '/platform' });
      }, 350);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.status === 403) {
          setErrorMessage('Invalid Admin Key (403 Forbidden). Verification failed.');
        } else {
          setErrorMessage(`Authentication failed (${err.status}): ${err.message}`);
        }
      } else {
        setErrorMessage('Could not reach backend API server at http://localhost:8000.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0B0B0D] flex items-center justify-center p-4 relative overflow-hidden font-sans">
      {/* Background warm luxury glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[550px] h-[350px] bg-gradient-to-b from-[#F97316]/12 via-[#3A1F10]/20 to-transparent blur-3xl pointer-events-none rounded-full" />

      <div className="w-full max-w-md relative z-10">
        {/* Header Branding */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br from-[#F97316] to-[#C2410C] text-white font-bold text-xl mb-4 shadow-lg shadow-[#F97316]/25 border border-white/10">
            R
          </div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[#F97316]/15 border border-[#F97316]/30 text-[#F97316] text-[11px] font-semibold mb-2">
            <ShieldCheck className="w-3 h-3" />
            SUPER ADMIN ONLY
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Platform Infrastructure</h1>
          <p className="text-xs text-zinc-400 mt-1">
            Restricted access gateway for platform administrators
          </p>
        </div>

        {/* Login Box */}
        <div className="bg-[#151517] border border-white/10 rounded-2xl p-7 shadow-2xl backdrop-blur-xl">
          {/* Mode Switcher Tabs */}
          <div className="flex rounded-lg bg-[#0B0B0D] p-1 mb-5 border border-white/5">
            <button
              type="button"
              onClick={() => {
                setAuthMode('credentials');
                setErrorMessage(null);
              }}
              className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-all ${
                authMode === 'credentials'
                  ? 'bg-[#1E1E22] text-white shadow-sm'
                  : 'text-zinc-400 hover:text-white'
              }`}
            >
              JWT Login (Email)
            </button>
            <button
              type="button"
              onClick={() => {
                setAuthMode('apikey');
                setErrorMessage(null);
              }}
              className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-all ${
                authMode === 'apikey'
                  ? 'bg-[#1E1E22] text-white shadow-sm'
                  : 'text-zinc-400 hover:text-white'
              }`}
            >
              Master API Key
            </button>
          </div>

          {authMode === 'credentials' ? (
            <form onSubmit={handleCredentialsSubmit} autoComplete="off" className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400">
                    Platform Admin Email
                  </label>
                  <button
                    type="button"
                    onClick={fillSuperAdminDemo}
                    className="text-[11px] text-[#F97316] hover:underline flex items-center gap-1"
                  >
                    <Sparkles className="w-3 h-3" />
                    Fill Demo Credentials
                  </button>
                </div>
                <div className="relative">
                  <Mail className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    type="email"
                    name="platform_login_email_field"
                    id="platform_login_email_field"
                    autoComplete="new-password"
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value);
                      setErrorMessage(null);
                    }}
                    required
                    placeholder="admin@platform.internal"
                    className="w-full pl-10 pr-4 py-2.5 bg-[#0B0B0D] border border-white/10 rounded-lg text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-[#F97316] focus:ring-1 focus:ring-[#F97316] transition-colors"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5">
                  Master Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    type="password"
                    name="platform_login_password_field"
                    id="platform_login_password_field"
                    autoComplete="new-password"
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value);
                      setErrorMessage(null);
                    }}
                    required
                    placeholder="Enter platform admin password..."
                    className="w-full pl-10 pr-4 py-2.5 bg-[#0B0B0D] border border-white/10 rounded-lg text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-[#F97316] focus:ring-1 focus:ring-[#F97316] transition-colors"
                  />
                </div>
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
                  <span>Platform Super Admin verified. Redirecting...</span>
                </div>
              )}

              <Button
                type="submit"
                variant="primary"
                size="lg"
                className="w-full mt-2"
                disabled={isLoading || successNotice}
              >
                <span>{isLoading ? 'Authenticating...' : 'Sign In as Super Admin'}</span>
                <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </form>
          ) : (
            <form onSubmit={handleKeySubmit} autoComplete="off" className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400">
                    Master Admin Key (X-Admin-Key)
                  </label>
                  <button
                    type="button"
                    onClick={fillMasterKeyDemo}
                    className="text-[11px] text-[#F97316] hover:underline flex items-center gap-1"
                  >
                    <Sparkles className="w-3 h-3" />
                    Fill Demo Key
                  </button>
                </div>
                <div className="relative">
                  <KeyRound className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    type="password"
                    name="platform_master_admin_key_field"
                    id="platform_master_admin_key_field"
                    autoComplete="new-password"
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
                  Matches <code className="text-zinc-400">ADMIN_API_KEY</code> in root <code className="text-zinc-400">.env</code>.
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
                  <span>Admin Key verified. Redirecting...</span>
                </div>
              )}

              <Button
                type="submit"
                variant="primary"
                size="lg"
                className="w-full mt-2"
                disabled={isLoading || successNotice}
              >
                <span>{isLoading ? 'Verifying Key...' : 'Authenticate Master Key'}</span>
                <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </form>
          )}
        </div>

        {/* Quick Footer */}
        <div className="text-center mt-6">
          <p className="text-xs text-zinc-600">
            RealEstate AI Platform Core • Multi-Tenant RBAC v1.0
          </p>
        </div>
      </div>
    </div>
  );
};
