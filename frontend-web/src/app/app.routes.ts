
import { Routes } from '@angular/router';
import { AuthComponent } from './auth.component';
import { AdminComponent } from './admin.component';
import { CatalogComponent } from './catalog.component';
import { BranchesComponent } from './branches.component';
import { ProfileComponent } from './profile.component';

export const routes: Routes = [
  { path: '', component: CatalogComponent },
  { path: 'auth', component: AuthComponent },
  { path: 'admin', component: AdminComponent },
  { path: 'branches', component: BranchesComponent },
  { path: 'profile', component: ProfileComponent }
];
