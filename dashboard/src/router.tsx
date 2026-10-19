import {
  createRouter,
  createRoute,
  createRootRoute,
  Outlet,
  redirect,
} from '@tanstack/react-router';

// Layouts
import { SuperAdminLayout } from './components/layout/SuperAdminLayout';
import { AgencyLayout } from './components/layout/AgencyLayout';

// Pages
import { PlatformLoginPage } from './pages/platform/PlatformLoginPage';
import { PlatformOverviewPage } from './pages/platform/PlatformOverviewPage';
import { TenantsManagementPage } from './pages/platform/TenantsManagementPage';
import { SystemGatewayPage } from './pages/platform/SystemGatewayPage';
import { AuditLogsPage } from './pages/platform/AuditLogsPage';
import { AgencyLoginPage } from './pages/agency/AgencyLoginPage';
import { AgencyDashboardPage } from './pages/agency/AgencyDashboardPage';
import { AgencyConversationsPage } from './pages/agency/AgencyConversationsPage';
import { AgencyLeadsPage } from './pages/agency/AgencyLeadsPage';
import { AgencyKnowledgePage } from './pages/agency/AgencyKnowledgePage';
import { AgencySettingsPage } from './pages/agency/AgencySettingsPage';



// 1. Root Route
const rootRoute = createRootRoute({
  component: () => <Outlet />,
});

// 2. Index redirect to /platform/login
const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  beforeLoad: () => {
    throw redirect({ to: '/platform/login' });
  },
});

// 3. Super Admin Routes
const platformLoginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/platform/login',
  component: PlatformLoginPage,
});

const platformLayoutRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/platform',
  component: SuperAdminLayout,
});

const platformOverviewRoute = createRoute({
  getParentRoute: () => platformLayoutRoute,
  path: '/',
  component: PlatformOverviewPage,
});

const platformTenantsRoute = createRoute({
  getParentRoute: () => platformLayoutRoute,
  path: '/tenants',
  component: TenantsManagementPage,
});

const platformSystemRoute = createRoute({
  getParentRoute: () => platformLayoutRoute,
  path: '/system',
  component: SystemGatewayPage,
});

const platformAuditRoute = createRoute({
  getParentRoute: () => platformLayoutRoute,
  path: '/audit',
  component: AuditLogsPage,
});


// 4. Agency Admin Routes
const agencyLoginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/login',
  component: AgencyLoginPage,
});

const agencyLayoutRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/app',
  component: AgencyLayout,
});

const agencyDashboardRoute = createRoute({
  getParentRoute: () => agencyLayoutRoute,
  path: '/',
  component: AgencyDashboardPage,
});

// Placeholder sub-routes for agency portal
const agencyConversationsRoute = createRoute({
  getParentRoute: () => agencyLayoutRoute,
  path: '/conversations',
  component: AgencyConversationsPage,
});


const agencyLeadsRoute = createRoute({
  getParentRoute: () => agencyLayoutRoute,
  path: '/leads',
  component: AgencyLeadsPage,
});

const agencyKnowledgeRoute = createRoute({
  getParentRoute: () => agencyLayoutRoute,
  path: '/knowledge',
  component: AgencyKnowledgePage,
});


const agencySettingsRoute = createRoute({
  getParentRoute: () => agencyLayoutRoute,
  path: '/settings',
  component: AgencySettingsPage,
});


// Construct the Route Tree
const routeTree = rootRoute.addChildren([
  indexRoute,
  platformLoginRoute,
  platformLayoutRoute.addChildren([
    platformOverviewRoute,
    platformTenantsRoute,
    platformSystemRoute,
    platformAuditRoute,
  ]),
  agencyLoginRoute,
  agencyLayoutRoute.addChildren([
    agencyDashboardRoute,
    agencyConversationsRoute,
    agencyLeadsRoute,
    agencyKnowledgeRoute,
    agencySettingsRoute,
  ]),
]);

export const router = createRouter({
  routeTree,
  defaultPreload: 'intent',
});

// Register router for type safety
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}
