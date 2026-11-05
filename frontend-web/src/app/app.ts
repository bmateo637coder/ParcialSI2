import { Component, inject } from '@angular/core';
import { AutoSyncService } from './core/offline/auto-sync.service';
import { ConnectionService } from './core/offline/connection.service';
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
  <nav class="navbar" aria-label="Navegación principal" (keydown.escape)="menuOpen = false">
    <a routerLink="/" class="navbar-brand">FASHION<span>STORE</span></a>
    <button type="button" class="menu-toggle" [attr.aria-expanded]="menuOpen" aria-controls="main-navigation" (click)="menuOpen = !menuOpen">{{ menuOpen ? 'Cerrar menú' : 'Menú ☰' }}</button>
    <div id="main-navigation" class="nav-links" [class.menu-open]="menuOpen" (click)="closeMenu($event)">
      <a routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{ exact: true }" class="nav-item">Catálogo</a>
      <a routerLink="/disponibilidad" routerLinkActive="active" class="nav-item">Disponibilidad</a>
      <a routerLink="/branches" routerLinkActive="active" class="nav-item">Sucursales</a>

<ng-container *ngIf="currentUser$ | async as user; else guest">
          <span class="user-chip">
            <span class="avatar">{{ initials(user) }}</span>
            <span class="chip-text">{{ user.first_name }}</span>
          </span>
          <a routerLink="/pos" routerLinkActive="active" class="nav-item"
             *ngIf="['Administrador', 'Cajero', 'Encargado de Sucursal'].includes(user.role_name)">
            Caja
          </a>
          <a routerLink="/reservas" routerLinkActive="active" class="nav-item">Reservas</a>
          <a *ngIf="['Administrador','Encargado de Sucursal','Cliente'].includes(user.role_name)" routerLink="/reembolsos" routerLinkActive="active" class="nav-item">Reembolsos</a>
          <a *ngIf="['Administrador', 'Encargado de Sucursal', 'Administrador de Plataforma'].includes(user.role_name)" routerLink="/bitacora" routerLinkActive="active" class="nav-item">Bitácora</a>
          <a *ngIf="['Administrador', 'Encargado de Sucursal', 'Cajero'].includes(user.role_name)" routerLink="/cambios" routerLinkActive="active" class="nav-item">Cambios</a>
          <a routerLink="/carrito" routerLinkActive="active" class="nav-item">Mi carrito</a>
          <a routerLink="/profile" routerLinkActive="active" class="nav-item">Mi perfil</a>
          <a *ngIf="user.empresa_id || user.role_name === 'Administrador de Plataforma'" routerLink="/plataforma" routerLinkActive="active" class="nav-item">{{ user.role_name === 'Administrador de Plataforma' ? 'Empresas y planes' : 'Mi suscripción' }}</a>
          <a *ngIf="user.role_name === 'Administrador' || user.role_name === 'Encargado de Sucursal'"
             routerLink="/reports" routerLinkActive="active" class="nav-item">
            Reportes
          </a>
          <a *ngIf="user.role_name === 'Administrador' || user.role_name === 'Encargado de Sucursal'"
             routerLink="/reportes-ia" routerLinkActive="active" class="nav-item">
            Reportes IA
          </a>
          <a *ngIf="user.role_name === 'Administrador' || user.role_name === 'Encargado de Sucursal'" routerLink="/analitica" routerLinkActive="active" class="nav-item">Analítica</a>
          <a *ngIf="user.empresa_id"
             routerLink="/offline/sync" routerLinkActive="active" class="nav-item">
            Sincronización
          </a>
          <a *ngIf="user.role_name === 'Administrador' || user.role_name === 'Encargado de Sucursal'"
             routerLink="/conflictos-sync" routerLinkActive="active" class="nav-item">
            Conflictos sync
          </a>
          <a *ngIf="user.role_name === 'Proveedor'" routerLink="/provider" routerLinkActive="active" class="nav-item">
            Portal proveedor
          </a>
          <a *ngIf="user.role_name === 'Administrador'" routerLink="/admin" routerLinkActive="active" class="nav-item">
            Panel admin
          </a>
          <a *ngIf="user.role_name === 'Administrador'" routerLink="/promos" routerLinkActive="active" class="nav-item">
            Promociones
          </a>
          <button class="link-plain" (click)="logout()">Salir</button>
        </ng-container>

      <ng-template #guest>
        <a routerLink="/auth" class="btn btn-accent btn-small-nav">Ingresar</a>
      </ng-template>
    </div>
  </nav>

  <div class="container">
    <div *ngIf="!connection.online()" role="status" class="card" style="margin:1rem 0;padding:1rem;">
      Sin conexión. Se muestran los últimos datos guardados; las existencias pueden haber cambiado.
      Las ventas y reservas locales necesitan confirmación del servidor.
    </div>
    <router-outlet></router-outlet>
  </div>

  @defer (when (currentUser$ | async) !== null) {
    <app-assistant *ngIf="(currentUser$ | async) !== null"></app-assistant>
  }
  `,
  styles: [`.menu-toggle{display:none;color:#fff;background:transparent;border:1px solid #766d5c;padding:.5rem .8rem;border-radius:8px;cursor:pointer}.nav-links{flex:1;gap:.65rem 1rem}.navbar{column-gap:1.5rem;padding-top:.5rem;padding-bottom:.5rem}@media(max-width:900px){.menu-toggle{display:block}.nav-links{display:none;flex:1 0 100%;max-height:70vh;overflow:auto;padding:.8rem 0}.nav-links.menu-open{display:flex;justify-content:flex-start;gap:.6rem 1.1rem}.navbar{justify-content:space-between}}`],
})
export class App {
  menuOpen = false;
  private autoSync = inject(AutoSyncService);
  connection = inject(ConnectionService);
  currentUser$!: Observable<User | null>;

  constructor(private api: ApiService) {
    this.currentUser$ = this.api.currentUser.asObservable();
  }

  logout(): void {
    this.api.logout();
  }

  closeMenu(event: Event): void {
    if ((event.target as HTMLElement)?.closest('a,button')) this.menuOpen = false;
  }

  initials(user: User | null): string {
    if (!user) return '';
    return ((user.first_name?.charAt(0) || '') + (user.last_name?.charAt(0) || '')).toUpperCase();
  }
}
