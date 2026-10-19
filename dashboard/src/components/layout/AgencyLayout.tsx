import React, { useState, useEffect } from 'react';
import { Outlet, Link, useRouterState, useNavigate } from '@tanstack/react-router';
import {
  LayoutDashboard,
  MessageSquare,
  FileText,
  Users,
  Settings,
  LogOut,
  ShieldAlert,
  Menu,
  X,
} from 'lucide-react';
import { ThemeToggle } from '../ui/ThemeToggle';
import { useAuthStore } from '../../store/useAuthStore';

export const AgencyLayout: React.FC = () => {
  const routerState = useRouterState();
  const currentPath = routerState.location.pathname;
  const navigate = useNavigate();
  const tenant = useAuthStore((s) => s.tenant);
  const clearAgencyAuth = useAuthStore((s) => s.clearAgencyAuth);
  const agencyUser = useAuthStore((s) => s.agencyUser);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    setMobileMenuOpen(false);
  }, [currentPath]);

  const handleLogout = () => {
    clearAgencyAuth();
    navigate({ to: '/login' });
  };

  const navItems = [
    { label: 'Overview', path: '/app', icon: LayoutDashboard },
    { label: 'Conversations', path: '/app/conversations', icon: MessageSquare },
    { label: 'Leads & CRM', path: '/app/leads', icon: Users },
    { label: 'Knowledge Base', path: '/app/knowledge', icon: FileText },
    { label: 'Widget & Settings', path: '/app/settings', icon: Settings },
  ];

  const getPageTitle = (path: string) => {
    if (path === '/app') return 'Agency Workspace';
    if (path.startsWith('/app/conversations')) return 'Live Visitor Conversations';
    if (path.startsWith('/app/leads')) return 'CRM Qualified Leads';
    if (path.startsWith('/app/knowledge')) return 'Knowledge Base & Brochures';
    if (path.startsWith('/app/settings')) return 'Widget & Workspace Settings';
    return 'Agency Portal';
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
          {/* Logo & Agency Header */}
          <div className="p-5 sm:p-6 border-b border-white/8 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-zinc-800 border border-white/10 flex items-center justify-center font-bold text-white uppercase">
                {tenant?.name ? tenant.name.charAt(0) : 'A'}
              </div>
              <div className="overflow-hidden">
                <span className="font-bold text-sm tracking-tight text-white block truncate">
                  {tenant?.name || 'Agency Workspace'}
                </span>
                <span className="text-[11px] text-zinc-400">Agency Workspace</span>
              </div>
            </div>

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
              Agency Hub
            </div>
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentPath === item.path;

              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-white/10 text-white font-semibold'
                      : 'text-zinc-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  <Icon className="w-4 h-4 text-zinc-400" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Bottom Section */}
        <div className="p-4 border-t border-white/8 space-y-2">
          <Link
            to="/platform"
            className="flex items-center gap-2 text-xs text-[#F97316] hover:text-[#EA580C] px-3 py-2 rounded-lg bg-[#F97316]/10 hover:bg-[#F97316]/15 border border-[#F97316]/20 transition-colors"
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Switch to Platform Admin</span>
          </Link>

          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2.5 text-xs text-zinc-400 hover:text-zinc-200 px-3 py-2 rounded-lg hover:bg-white/5 transition-colors cursor-pointer"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Log out</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        {/* Top Bar - Fixed at top */}
        <header className="h-16 border-b border-white/8 px-4 sm:px-6 lg:px-8 flex items-center justify-between shrink-0 bg-[#0B0B0D]/90 backdrop-blur-md z-20">
          <div className="flex items-center gap-3">
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
            {agencyUser ? (
              <div className="flex items-center gap-2">
                <span className="hidden sm:inline-block text-[11px] font-medium px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 border border-white/5 capitalize">
                  {agencyUser.role.replace('_', ' ')}
                </span>
                <div className="w-8 h-8 rounded-full bg-[#F97316]/15 border border-[#F97316]/30 flex items-center justify-center text-xs font-semibold text-[#F97316]">
                  {agencyUser.full_name.slice(0, 2).toUpperCase()}
                </div>
                <div className="hidden md:flex flex-col text-left">
                  <span className="text-xs font-medium text-zinc-200 leading-tight">
                    {agencyUser.full_name}
                  </span>
                  <span className="text-[10px] text-zinc-500 leading-tight">
                    {agencyUser.email}
                  </span>
                </div>
              </div>
            ) : (
              <span className="text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-full font-medium whitespace-nowrap shrink-0">
                Live Widget Active
              </span>
            )}
          </div>
        </header>

        {/* Scrollable Content Body */}
        <main className="p-4 sm:p-6 lg:p-6 flex-1 overflow-y-auto min-h-0">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
