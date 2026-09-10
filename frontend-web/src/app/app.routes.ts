import { Routes } from '@angular/router';
import { AuthComponent } from './auth.component';
import { AdminComponent } from './admin.component';
import { CatalogComponent } from './catalog.component';
import { BranchesComponent } from './branches.component';
import { ProfileComponent } from './profile.component';
import { AuthGuard } from './auth.guard';
import { AdminGuard } from './admin.guard';

export const routes: Routes = [
  { path: '', component: CatalogComponent },
  { path: 'auth', component: AuthComponent },
  { path: 'branches', component: BranchesComponent },
  { path: 'admin', component: AdminComponent, canActivate: [AdminGuard] },
  { path: 'profile', component: ProfileComponent, canActivate: [AuthGuard] },
  { path: '**', redirectTo: '' },
];