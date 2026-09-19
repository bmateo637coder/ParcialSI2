import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { Observable } from 'rxjs';
import { ApiService, User } from './api.service';
import { CommonModule } from '@angular/common';
import { AssistantComponent } from './assistant.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, CommonModule, AssistantComponent],
  template: `
  <nav class="navbar">
    <a routerLink="/" class="navbar-brand">FASHION<span>STORE</span></a>
    <div class="nav-links">
      <a routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{ exact: true }" class="nav-item">Catálogo</a>
      <a routerLink="/disponibilidad" routerLinkActive="active" class="nav-item">Disponibilidad</a>
      <a routerLink="/branches" routerLinkActive="active" class="nav-item">Sucursales</a>

<ng-container *ngIf="currentUser$ | async as user; else guest">
          <span class="user-chip">
            <span class="avatar">{{ initials(user) }}</span>
            <span class="chip-text">{{ user.first_name }}</span>
          </span>
          <a routerLink="/pos" routerLinkActive="active" class="nav-item"
             *ngIf="user.role_name === 'Cajero' || user.role_name === 'Encargado de Sucursal'">
            Caja
          </a>
          <a routerLink="/reservas" routerLinkActive="active" class="nav-item">Reservas</a>
          <a routerLink="/carrito" routerLinkActive="active" class="nav-item">Mi carrito</a>
          <a routerLink="/profile" routerLinkActive="active" class="nav-item">Mi perfil</a>
          <a *ngIf="user.role_name === 'Administrador' || user.role_name === 'Encargado de Sucursal'"
             routerLink="/reports" routerLinkActive="active" class="nav-item">
            Reportes <span class="nav-badge">CU24-25</span>
          </a>
          <a *ngIf="user.role_name === 'Proveedor'" routerLink="/provider" routerLinkActive="active" class="nav-item">
            Portal proveedor
          </a>
          <a *ngIf="user.role_name === 'Administrador'" routerLink="/admin" routerLinkActive="active" class="nav-item">
            Panel admin <span class="nav-badge">Admin</span>
          </a>
          <a *ngIf="user.role_name === 'Administrador'" routerLink="/promos" routerLinkActive="active" class="nav-item">
            Promociones <span class="nav-badge">CU27</span>
          </a>
          <button class="link-plain" (click)="logout()">Salir</button>
        </ng-container>

      <ng-template #guest>
        <a routerLink="/auth" class="btn btn-accent btn-small-nav">Ingresar</a>
      </ng-template>
    </div>
  </nav>

  <div class="container">
    <router-outlet></router-outlet>
  </div>

  <app-assistant *ngIf="(currentUser$ | async) !== null"></app-assistant>
  `,
})
export class App {
  currentUser$!: Observable<User | null>;

  constructor(private api: ApiService) {
    this.currentUser$ = this.api.currentUser.asObservable();
  }

  logout(): void {
    this.api.logout();
  }

  initials(user: User | null): string {
    if (!user) return '';
    return ((user.first_name?.charAt(0) || '') + (user.last_name?.charAt(0) || '')).toUpperCase();
  }
}