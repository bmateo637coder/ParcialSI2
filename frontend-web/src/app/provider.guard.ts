import { Injectable } from '@angular/core';
import { CanActivate, Router } from '@angular/router';
import { ApiService } from './api.service';

@Injectable({ providedIn: 'root' })
export class ProviderGuard implements CanActivate {
  constructor(private api: ApiService, private router: Router) {}

  canActivate(): boolean {
    const user = this.api.currentUser.value;
    if (user && user.role_name === 'Proveedor') {
      return true;
    }
    this.router.navigate(['/']);
    return false;
  }
}