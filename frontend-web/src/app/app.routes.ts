import { Routes } from '@angular/router';
import { AuthComponent } from './auth.component';
import { AdminComponent } from './admin.component';
import { CatalogComponent } from './catalog.component';
import { BranchesComponent } from './branches.component';
import { ProfileComponent } from './profile.component';
import { AvailabilityComponent } from './availability.component';
import { CartComponent } from './cart.component';
import { ReservationsComponent } from './reservations.component';
import { PosComponent } from './pos.component';
import { VestidorComponent } from './vestidor.component';
import { ReportsComponent } from './reports.component';
import { AuthGuard } from './auth.guard';
import { AdminGuard } from './admin.guard';
import { StaffGuard } from './staff.guard';
import { ReportsGuard } from './reports.guard';
import { ProviderGuard } from './provider.guard';
import { PromosComponent } from './promos.component';
import { ProviderComponent } from './provider.component';
import { SyncComponent } from './features/offline/sync/sync.component';
import { ReportesIaComponent } from './features/reportes-ia/reportes-ia.component';

export const routes: Routes = [
  { path: '', component: CatalogComponent },
  { path: 'auth', component: AuthComponent },
  { path: 'branches', component: BranchesComponent },
  { path: 'disponibilidad', component: AvailabilityComponent },
  { path: 'carrito', component: CartComponent, canActivate: [AuthGuard] },
  { path: 'pos', component: PosComponent, canActivate: [StaffGuard] },
  { path: 'vestidor', component: VestidorComponent },
  { path: 'reservas', component: ReservationsComponent, canActivate: [AuthGuard] },
  { path: 'admin', component: AdminComponent, canActivate: [AdminGuard] },
  { path: 'promos', component: PromosComponent, canActivate: [AdminGuard] },
  { path: 'provider', component: ProviderComponent, canActivate: [ProviderGuard] },
  { path: 'reports', component: ReportsComponent, canActivate: [ReportsGuard] },
  { path: 'reportes-ia', component: ReportesIaComponent, canActivate: [ReportsGuard] },
  { path: 'offline/sync', component: SyncComponent, canActivate: [StaffGuard] },
  { path: 'profile', component: ProfileComponent, canActivate: [AuthGuard] },
  { path: '**', redirectTo: '' },
];