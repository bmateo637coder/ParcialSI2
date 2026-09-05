
import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { ApiService } from './api.service';
import { CommonModule } from '@angular/common';
@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, CommonModule],
  template: `
    <nav class="navbar">
      <a routerLink="/" class="navbar-brand">FASHION STORE</a>
      <div class="nav-links">
        <a routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{exact: true}" class="nav-item">Catálogo</a>
        <a routerLink="/branches" routerLinkActive="active" class="nav-item">Sucursales</a>
        <ng-container *ngIf="api.currentUser | async as user; else guest">
          <a routerLink="/profile" routerLinkActive="active" class="nav-item">Mi Perfil</a>
          <a *ngIf="user.role === 'Administrador'" routerLink="/admin" routerLinkActive="active" class="nav-item">Panel Admin</a>
          <button class="btn btn-outline" style="color:white; border-color:white; padding: 0.5rem 1rem;" (click)="logout()">Salir</button>
        </ng-container>
        <ng-template #guest>
            <a routerLink="/auth" class="btn btn-primary" style="background: white; color: var(--primary);">Ingresar</a>
        </ng-template>
      </div>
    </nav>
    <div class="container">
      <router-outlet></router-outlet>
    </div>
  `
})
export class App {
  constructor(public api: ApiService) {}
  logout() { this.api.logout(); }
}
