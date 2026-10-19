import React, { useState, useEffect } from 'react';
import { Outlet, Link, useRouterState, useNavigate } from '@tanstack/react-router';
import {
  LayoutDashboard,
  Building2,
  ShieldAlert,
  Server,
  LogOut,
  ExternalLink,
  Cpu,
  ScrollText,
  Menu,
  X,
} from 'lucide-react';
import { ThemeToggle } from '../ui/ThemeToggle';
import { useAuthStore } from '../../store/useAuthStore';

export const SuperAdminLayout: React.FC = () => {
  const routerState = useRouterState();
  const currentPath = routerState.location.pathname;
  const navigate = useNavigate();
  const clearPlatformAuth = useAuthStore((s) => s.clearPlatformAuth);
  const platformUser = useAuthStore((s) => s.platformUser);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Auto-close mobile drawer on route change
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [currentPath]);

  const handleLogout = () => {
    clearPlatformAuth();
    navigate({ to: '/platform/login' });
  };

  const navItems = [
    {
      label: 'Overview',
      path: '/platform',
      icon: LayoutDashboard,
      exact: true,
    },
    {
      label: 'Tenants & Agencies',
      path: '/platform/tenants',
      icon: Building2,
      exact: false,
    },
    {
      label: 'System & AI Gateway',
      path: '/platform/system',
      icon: Cpu,
      exact: false,
    },
    {
      label: 'Audit & Security Logs',
      path: '/platform/audit',
      icon: ScrollText,
      exact: false,
    },
  ];

  const getPageTitle = (path: string) => {
    if (path === '/platform') return 'Platform Overview';
    if (path.startsWith('/platform/tenants')) return 'Tenants & Agency Management';
    if (path.startsWith('/platform/system')) return 'System & AI Gateway';
    if (path.startsWith('/platform/audit')) return 'Platform Audit & Security Logs';
    return 'Platform Super Admin';
  };

  return (
    <div className="h-screen overflow-hidden bg-[#0B0B0D] text-white flex relative">
      {/* Mobile Backdrop */}
      {mobileMenuOpen && (
        <div
          onClick={() => setMobileMenuOpen(false)}
          className="fixed inset-0 bg-black/80 z-40 lg:hidden backdrop-blur-sm"
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 border-r border-white/8 bg-[#0F0F12] flex flex-col justify-between shrink-0 transition-transform duration-200 lg:static lg:translate-x-0 h-full overflow-y-auto ${
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div>
          {/* Logo & Portal Badge */}
          <div className="p-5 sm:p-6 border-b border-white/8 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#F97316] to-[#C2410C] flex items-center justify-center font-bold text-white shadow-md shadow-[#F97316]/20">
                R
              </div>
              <div>
                <span className="font-bold text-sm tracking-tight text-white block">
                  RealEstate AI
                </span>
                <span className="inline-flex items-center gap-1 text-[10px] font-semibold tracking-wider uppercase text-[#F97316] bg-[#F97316]/10 px-1.5 py-0.5 rounded">
                  <ShieldAlert className="w-2.5 h-2.5" />
                  Platform Admin
                </span>
              </div>
            </div>

            {/* Mobile Close Button */}
            <button
              onClick={() => setMobileMenuOpen(false)}
              className="lg:hidden text-zinc-400 hover:text-white p-1 rounded-lg"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-1.5">
            <div className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider px-3 mb-2">
              Platform Controls
            </div>
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = item.exact
                ? currentPath === item.path
                : currentPath.startsWith(item.path);

              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-[#F97316]/10 text-[#F97316] border border-[#F97316]/20'
                      : 'text-zinc-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-[#F97316]' : 'text-zinc-400'}`} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Bottom Section */}
        <div className="p-4 border-t border-white/8 space-y-3">
          <div className="p-3 rounded-lg bg-[#151517] border border-white/5 text-xs">
            <div className="flex items-center justify-between mb-1">
              <span className="text-zinc-400 flex items-center gap-1.5">
                <Server className="w-3.5 h-3.5 text-emerald-400" /> Core Cluster
              </span>
              <span className="text-emerald-400 font-medium text-[11px]">Healthy</span>
            </div>
            <div className="text-[11px] text-zinc-500">
              Qdrant • Redis • Postgres
            </div>
          </div>

          <Link
            to="/app"
            className="flex items-center justify-between text-xs text-zinc-400 hover:text-zinc-200 px-3 py-2 rounded-lg hover:bg-white/5 transition-colors"
          >
            <span>View Agency Portal</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </Link>

          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2.5 text-xs text-rose-400/90 hover:text-rose-300 px-3 py-2 rounded-lg hover:bg-rose-500/10 transition-colors cursor-pointer"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Exit Platform Admin</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        {/* Top Bar - Fixed at top */}
        <header className="h-16 border-b border-white/8 px-4 sm:px-6 lg:px-8 flex items-center justify-between shrink-0 bg-[#0B0B0D]/90 backdrop-blur-md z-20">
          <div className="flex items-center gap-3">
            {/* Hamburger Button for Mobile */}
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="lg:hidden text-zinc-400 hover:text-white p-1.5 rounded-lg bg-zinc-900 border border-white/10"
              title="Open Navigation"
            >
              <Menu className="w-5 h-5" />
            </button>
            <h1 className="text-sm sm:text-base font-semibold text-zinc-200 truncate">
              {getPageTitle(currentPath)}
            </h1>
          </div>

          <div className="flex items-center gap-3">
            <ThemeToggle />
            <span className="hidden sm:inline-block text-xs text-zinc-400 bg-zinc-900 border border-white/5 px-2.5 py-1 rounded-md">
              Env: <strong className="text-white">Production V1</strong>
            </span>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-[#F97316]/20 border border-[#F97316]/40 flex items-center justify-center text-xs font-semibold text-[#F97316]">
                {platformUser ? platformUser.full_name.slice(0, 2).toUpperCase() : 'SA'}
              </div>
              {platformUser && (
                <div className="hidden md:flex flex-col text-left">
                  <span className="text-xs font-medium text-zinc-200 leading-tight">
                    {platformUser.full_name}
                  </span>
                  <span className="text-[10px] text-zinc-500 leading-tight">
                    {platformUser.email}
                  </span>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Dynamic Route Content */}
        <main className="p-4 sm:p-6 lg:p-8 flex-1 overflow-y-auto min-h-0">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
