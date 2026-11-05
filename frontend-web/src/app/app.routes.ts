import { Routes } from '@angular/router';
import { AuthGuard } from './auth.guard';
import { AdminGuard } from './admin.guard';
import { StaffGuard } from './staff.guard';
import { ReportsGuard } from './reports.guard';
import { ProviderGuard } from './provider.guard';

export const routes: Routes = [
  { path: '', loadComponent: () => import('./catalog.component').then(m => m.CatalogComponent) },
  { path: 'auth', loadComponent: () => import('./auth.component').then(m => m.AuthComponent) },
  { path: 'branches', loadComponent: () => import('./branches.component').then(m => m.BranchesComponent) },
  { path: 'disponibilidad', loadComponent: () => import('./availability.component').then(m => m.AvailabilityComponent) },
  { path: 'carrito', loadComponent: () => import('./cart.component').then(m => m.CartComponent), canActivate: [AuthGuard] },
  { path: 'pos', loadComponent: () => import('./pos.component').then(m => m.PosComponent), canActivate: [StaffGuard] },
  { path: 'bitacora', loadComponent: () => import('./audit.component').then(m => m.AuditComponent), canActivate: [AuthGuard] },
  { path: 'reembolsos', loadComponent: () => import('./refunds.component').then(m => m.RefundsComponent), canActivate: [AuthGuard] },
  { path: 'vestidor', loadComponent: () => import('./vestidor.component').then(m => m.VestidorComponent) },
  { path: 'reservas', loadComponent: () => import('./reservations.component').then(m => m.ReservationsComponent), canActivate: [AuthGuard] },
  { path: 'admin', loadComponent: () => import('./admin.component').then(m => m.AdminComponent), canActivate: [AdminGuard] },
  { path: 'promos', loadComponent: () => import('./promos.component').then(m => m.PromosComponent), canActivate: [AdminGuard] },
  { path: 'provider', loadComponent: () => import('./provider.component').then(m => m.ProviderComponent), canActivate: [ProviderGuard] },
  { path: 'reports', loadComponent: () => import('./reports.component').then(m => m.ReportsComponent), canActivate: [ReportsGuard] },
  { path: 'reportes-ia', loadComponent: () => import('./features/reportes-ia/reportes-ia.component').then(m => m.ReportesIaComponent), canActivate: [ReportsGuard] },
  { path: 'offline/sync', loadComponent: () => import('./features/offline/sync/sync.component').then(m => m.SyncComponent), canActivate: [AuthGuard] },
  { path: 'profile', loadComponent: () => import('./profile.component').then(m => m.ProfileComponent), canActivate: [AuthGuard] },
  { path: 'plataforma', loadComponent: () => import('./platform.component').then(m => m.PlatformComponent), canActivate: [AuthGuard] },
  { path: 'analitica', loadComponent: () => import('./analytics.component').then(m => m.AnalyticsComponent), canActivate: [ReportsGuard] },
  { path: 'cambios', loadComponent: () => import('./exchanges.component').then(m => m.ExchangesComponent), canActivate: [StaffGuard] },
  { path: 'conflictos-sync', loadComponent: () => import('./features/sync-conflictos/conflictos.component').then(m => m.ConflictosComponent), canActivate: [ReportsGuard] },
  { path: '**', redirectTo: '' },
];
