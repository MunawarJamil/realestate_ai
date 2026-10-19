import React, { useState } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { KeyRound, ArrowRight, Building2, AlertCircle, CheckCircle2, Mail, Lock, Globe, Sparkles, HelpCircle, Copy, Check } from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { Modal } from '../../components/ui/Modal';
import { useAuthStore } from '../../store/useAuthStore';
import { apiClient, ApiError } from '../../api/client';

export const AgencyLoginPage: React.FC = () => {
  const navigate = useNavigate();
  const setAgencyAuth = useAuthStore((s) => s.setAgencyAuth);
  const setApiKey = useAuthStore((s) => s.setApiKey);
  const setTenant = useAuthStore((s) => s.setTenant);

  const [authMode, setAuthMode] = useState<'credentials' | 'apikey'>('credentials');

  // Credentials State (Clean initial state - no API key required for email/password login)
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [tenantSlug, setTenantSlug] = useState('');

  // API Key State (strictly empty by default - no hardcoded characters)
  const [apiKeyInput, setApiKeyInput] = useState('');

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successNotice, setSuccessNotice] = useState<string | null>(null);

  // Request Access Modal
  const [isRequestModalOpen, setIsRequestModalOpen] = useState(false);
  const [copiedContact, setCopiedContact] = useState(false);

  const fillAgencyAdminDemo = () => {
    setEmail('admin@prestige.com');
    setPassword('AgencyAdminPassword123!');
    setTenantSlug('prestige-prime');
    setErrorMessage(null);
  };

  const fillAgencyAgentDemo = () => {
    setEmail('agent@prestige.com');
    setPassword('AgentPassword123!');
    setTenantSlug('prestige-prime');
    setErrorMessage(null);
  };

  const fillApiKeyDemo = () => {
    setApiKeyInput('rk_live_demo_test_key');
    setErrorMessage(null);
  };

  const handleCredentialsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setErrorMessage('Please enter both your email address and password.');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const res = await apiClient.auth.login({
        email: email.trim(),
        password,
        tenant_slug: tenantSlug.trim() || undefined,
      });

      // Save tokens and user in store. All agency API requests automatically attach the Bearer JWT token.
      setAgencyAuth(res.tokens, res.user);

      // Fetch full tenant info for workspace header
      try {
        const tenantInfo = await apiClient.agency.getMe();
        setTenant(tenantInfo);
      } catch {
        if (res.user.tenant_id) {
          setTenant({
            id: res.user.tenant_id,
            name: res.tenant_name || 'Agency Workspace',
            slug: res.tenant_slug || 'agency',
            api_key_prefix: 'auth_jwt',
            widget_key: '',
            allowed_domains: [],
            is_active: true,
            created_at: res.user.created_at,
          });
        }
      }

      setSuccessNotice(`Welcome back, ${res.user.full_name}!`);
      setTimeout(() => {
        navigate({ to: '/app' });
      }, 350);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.status === 403) {
          setErrorMessage(err.message || 'Platform Super Admins cannot sign in via the Agency portal.');
        } else if (err.status === 401) {
          setErrorMessage('Invalid credentials or deactivated account. Please check your email and password.');
        } else {
          setErrorMessage(`Login failed (${err.status}): ${err.message}`);
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
    if (!apiKeyInput.trim()) {
      setErrorMessage('Please provide an Agency API Key (e.g., rk_live_...).');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    setApiKey(apiKeyInput.trim());

    try {
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
        setErrorMessage('Could not reach backend API at http://localhost:8000.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyContact = () => {
    navigator.clipboard.writeText('admin@platform.internal');
    setCopiedContact(true);
    setTimeout(() => setCopiedContact(false), 2000);
  };

  return (
    <div className="min-h-screen bg-[#0B0B0D] flex items-center justify-center p-4 relative font-sans">
      {/* Background radial luxury glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[550px] h-[350px] bg-gradient-to-b from-[#F97316]/10 via-[#1E1E22]/20 to-transparent blur-3xl pointer-events-none rounded-full" />

      <div className="w-full max-w-md relative z-10">
        {/* Header Branding */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br from-[#F97316] to-[#C2410C] text-white font-bold text-xl mb-4 shadow-lg shadow-[#F97316]/20 border border-white/10">
            <Building2 className="w-6 h-6" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Agency Workspace</h1>
          <p className="text-xs text-zinc-400 mt-1">
            Sign in to manage AI knowledge bases, properties, and conversations
          </p>
        </div>

        {/* Login Box */}
        <div className="bg-[#151517] border border-white/10 rounded-2xl p-7 shadow-2xl backdrop-blur-xl">
          {/* Mode Tabs */}
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
              Account Login
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
              Agency API Key
            </button>
          </div>

          {authMode === 'credentials' ? (
            <form onSubmit={handleCredentialsSubmit} autoComplete="off" className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400">
                    Work Email
                  </label>
                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      onClick={fillAgencyAdminDemo}
                      className="text-[10px] text-[#F97316] hover:underline flex items-center gap-0.5"
                    >
                      <Sparkles className="w-2.5 h-2.5" />
                      Demo Admin
                    </button>
                    <span className="text-zinc-600">·</span>
                    <button
                      type="button"
                      onClick={fillAgencyAgentDemo}
                      className="text-[10px] text-zinc-400 hover:text-white"
                    >
                      Demo Agent
                    </button>
                  </div>
                </div>
                <div className="relative">
                  <Mail className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    type="email"
                    name="agency_login_email_unique"
                    id="agency_login_email_unique"
                    autoComplete="new-password"
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value);
                      setErrorMessage(null);
                    }}
                    required
                    placeholder="admin@prestige.com"
                    className="w-full pl-10 pr-4 py-2.5 bg-[#0B0B0D] border border-white/10 rounded-lg text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-[#F97316] focus:ring-1 focus:ring-[#F97316] transition-colors"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    type="password"
                    name="agency_login_password_unique"
                    id="agency_login_password_unique"
                    autoComplete="new-password"
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value);
                      setErrorMessage(null);
                    }}
                    required
                    placeholder="Enter your account password..."
                    className="w-full pl-10 pr-4 py-2.5 bg-[#0B0B0D] border border-white/10 rounded-lg text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-[#F97316] focus:ring-1 focus:ring-[#F97316] transition-colors"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400">
                    Agency Slug <span className="text-zinc-600 font-normal lowercase">(optional)</span>
                  </label>
                  <span className="text-[11px] text-zinc-500">e.g. prestige-prime</span>
                </div>
                <div className="relative">
                  <Globe className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    type="text"
                    name="agency_login_slug_unique"
                    id="agency_login_slug_unique"
                    autoComplete="new-password"
                    value={tenantSlug}
                    onChange={(e) => {
                      setTenantSlug(e.target.value);
                      setErrorMessage(null);
                    }}
                    placeholder="prestige-prime"
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
                  <span>{successNotice}</span>
                </div>
              )}

              <Button
                type="submit"
                variant="primary"
                size="lg"
                className="w-full mt-2"
                disabled={isLoading || !!successNotice}
              >
                <span>{isLoading ? 'Signing in...' : 'Sign In to Workspace'}</span>
                <ArrowRight className="w-4 h-4 ml-1" />
              </Button>

              {/* Or Login with API Key Button */}
              <div className="pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setAuthMode('apikey');
                    setErrorMessage(null);
                  }}
                  className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg border border-white/10 bg-[#0B0B0D] hover:bg-white/[0.04] text-xs font-medium text-zinc-300 hover:text-white transition-all cursor-pointer"
                >
                  <KeyRound className="w-3.5 h-3.5 text-[#F97316]" />
                  <span>Or login with Agency API Key</span>
                </button>
              </div>
            </form>
          ) : (
            <form onSubmit={handleKeySubmit} autoComplete="off" className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400">
                    Agency API Key (X-API-Key)
                  </label>
                  <button
                    type="button"
                    onClick={fillApiKeyDemo}
                    className="text-[11px] text-[#F97316] hover:underline flex items-center gap-1"
                  >
                    <Sparkles className="w-3 h-3" />
                    Fill Demo Key
                  </button>
                </div>
                <div className="relative">
                  <KeyRound className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    type="text"
                    name="agency_direct_api_key_field"
                    id="agency_direct_api_key_field"
                    autoComplete="off"
                    value={apiKeyInput}
                    onChange={(e) => {
                      setApiKeyInput(e.target.value);
                      setErrorMessage(null);
                    }}
                    required
                    placeholder="rk_live_..."
                    className="w-full pl-10 pr-4 py-2.5 bg-[#0B0B0D] border border-white/10 rounded-lg text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-[#F97316] focus:ring-1 focus:ring-[#F97316] transition-colors font-mono text-xs"
                  />
                </div>
                <p className="text-[11px] text-zinc-500 mt-1.5">
                  Optional direct key access for developers and external integrations.
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
                disabled={isLoading || !!successNotice}
              >
                <span>{isLoading ? 'Connecting to Tenant...' : 'Connect to Workspace'}</span>
                <ArrowRight className="w-4 h-4 ml-1" />
              </Button>

              <div className="pt-1 text-center">
                <button
                  type="button"
                  onClick={() => {
                    setAuthMode('credentials');
                    setErrorMessage(null);
                  }}
                  className="text-xs text-zinc-400 hover:text-white transition-colors"
                >
                  ← Back to Email & Password Login
                </button>
              </div>
            </form>
          )}

          {/* Don't have credentials notice */}
          <div className="mt-5 pt-4 border-t border-white/5 text-center">
            <p className="text-xs text-zinc-400">
              Don&apos;t have credentials?{' '}
              <button
                type="button"
                onClick={() => setIsRequestModalOpen(true)}
                className="text-[#F97316] hover:underline font-medium cursor-pointer"
              >
                Request access from Platform Administrator / Owner
              </button>
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center mt-6">
          <p className="text-xs text-zinc-600">
            RealEstate AI Agency Portal • Multi-Tenant Isolated
          </p>
        </div>
      </div>

      {/* Request Access Info Modal */}
      <Modal
        isOpen={isRequestModalOpen}
        onClose={() => setIsRequestModalOpen(false)}
        title="Request Agency Workspace Access"
        description="New agency tenants and administrator credentials are provisioned exclusively by the platform infrastructure team or your agency owner."
      >
        <div className="space-y-4 text-xs text-zinc-300">
          <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/10 space-y-2">
            <div className="flex items-center gap-2 text-white font-medium">
              <HelpCircle className="w-4 h-4 text-[#F97316]" />
              <span>How are agency accounts created?</span>
            </div>
            <p className="text-zinc-400 text-[11px] leading-relaxed">
              RealEstate AI is a multi-tenant enterprise platform. The Platform Super Admin provisions your agency workspace and issues your initial agency admin login credentials along with your private API key and chat widget script.
            </p>
          </div>

          <div className="space-y-1.5">
            <label className="block text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
              Platform Support & Provisioning Desk
            </label>
            <div className="flex items-center gap-2">
              <input
                readOnly
                type="text"
                value="admin@platform.internal"
                className="flex-1 px-3 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs font-mono text-white select-all"
              />
              <Button
                variant="secondary"
                size="sm"
                onClick={handleCopyContact}
              >
                {copiedContact ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-zinc-400" />}
                <span>{copiedContact ? 'Copied' : 'Copy Email'}</span>
              </Button>
            </div>
          </div>

          <div className="pt-2 flex justify-end">
            <Button
              variant="primary"
              size="md"
              onClick={() => setIsRequestModalOpen(false)}
            >
              <span>Understood & Close</span>
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
