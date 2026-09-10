import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { Observable } from 'rxjs';
import { ApiService, User } from './api.service';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, CommonModule],
  template: `
  <nav class="navbar">
    <a routerLink="/" class="navbar-brand">FASHION<span>STORE</span></a>
    <div class="nav-links">
      <a routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{ exact: true }" class="nav-item">Catálogo</a>
      <a routerLink="/branches" routerLinkActive="active" class="nav-item">Sucursales</a>

      <ng-container *ngIf="currentUser$ | async as user; else guest">
        <span class="user-chip">
          <span class="avatar">{{ initials(user) }}</span>
          <span class="chip-text">{{ user.first_name }}</span>
        </span>
        <a routerLink="/profile" routerLinkActive="active" class="nav-item">Mi perfil</a>
        <a *ngIf="user.role_name === 'Administrador'" routerLink="/admin" routerLinkActive="active" class="nav-item">
          Panel admin <span class="nav-badge">Admin</span>
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