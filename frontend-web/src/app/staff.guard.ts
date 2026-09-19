import { Injectable } from '@angular/core';
import { CanActivate, Router } from '@angular/router';
import { ApiService } from './api.service';

@Injectable({ providedIn: 'root' })
export class StaffGuard implements CanActivate {
  constructor(private api: ApiService, private router: Router) {}

  canActivate(): boolean {
    const user = this.api.currentUser.value;
    if (user && (user.role_name === 'Cajero' || user.role_name === 'Encargado de Sucursal')) {
      return true;
    }
    this.router.navigate(['/']);
    return false;
  }
}