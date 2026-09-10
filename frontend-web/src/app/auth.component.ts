import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { ApiService } from './api.service';

@Component({
  selector: 'app-auth',
  standalone: true,
  imports: [FormsModule, CommonModule],
  template: `
  <div class="auth-shell">
    <div class="page-head">
      <span class="eyebrow">FashionStore</span>
      <h1>Bienvenido de nuevo</h1>
      <p class="lead">Accede a tu cuenta o crea una nueva para descubrir nuestra colección.</p>
    </div>

    <div class="card">
      <div class="auth-tabs">
        <button class="auth-tab" [class.active]="mode === 'login'" (click)="mode = 'login'">Iniciar sesión</button>
        <button class="auth-tab" [class.active]="mode === 'register'" (click)="mode = 'register'">Crear cuenta</button>
      </div>

      <!-- LOGIN -->
      <form *ngIf="mode === 'login'" (ngSubmit)="login()" novalidate>
        <div class="form-group">
          <label class="form-label">Correo electrónico</label>
          <input class="form-control" type="email" [(ngModel)]="loginData.email" name="loginEmail" placeholder="ejemplo@correo.com" required>
        </div>
        <div class="form-group">
          <label class="form-label">Contraseña</label>
          <input class="form-control" type="password" [(ngModel)]="loginData.password" name="loginPassword" placeholder="Tu contraseña" required>
        </div>
        <button class="btn btn-accent btn-block" type="submit" [disabled]="loading">
          <span *ngIf="loading" class="spinner"></span>
          {{ loading ? 'Accediendo…' : 'Acceder a mi cuenta' }}
        </button>
      </form>

      <!-- REGISTER -->
      <form *ngIf="mode === 'register'" (ngSubmit)="register()" novalidate>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Nombre</label>
            <input class="form-control" [(ngModel)]="regData.first_name" name="firstName" placeholder="María">
          </div>
          <div class="form-group">
            <label class="form-label">Apellido</label>
            <input class="form-control" [(ngModel)]="regData.last_name" name="lastName" placeholder="Gonzales">
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Correo electrónico</label>
          <input class="form-control" type="email" [(ngModel)]="regData.email" name="regEmail" placeholder="ejemplo@correo.com">
        </div>
        <div class="form-group">
          <label class="form-label">Contraseña</label>
          <input class="form-control" type="password" [(ngModel)]="regData.password" name="regPassword" placeholder="Mínimo 6 caracteres">
          <div class="form-error" *ngIf="regData.password && regData.password.length < 6">La contraseña debe tener al menos 6 caracteres.</div>
        </div>
        <button class="btn btn-accent btn-block" type="submit" [disabled]="loading || !validRegistration">
          <span *ngIf="loading" class="spinner"></span>
          {{ loading ? 'Creando cuenta…' : 'Crear mi cuenta' }}
        </button>
      </form>

      <p class="auth-note">Cuenta demo admin: <strong>admin@fashionstore.com / admin123</strong></p>
    </div>
  </div>
  `,
})
export class AuthComponent {
  mode: 'login' | 'register' = 'login';
  loading = false;
  loginData = { email: '', password: '' };
  regData = { first_name: '', last_name: '', email: '', password: '' };

  constructor(private api: ApiService, private router: Router) {}

  get validRegistration(): boolean {
    return !!(
      this.regData.first_name.trim() &&
      this.regData.last_name.trim() &&
      /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.regData.email) &&
      this.regData.password.length >= 6
    );
  }

  login(): void {
    if (!this.loginData.email || !this.loginData.password) return;
    this.loading = true;
    this.api.login(this.loginData).subscribe({
      next: (res) => {
        this.api.establishSession(res).subscribe({
          next: () => {
            this.loading = false;
            this.router.navigate(['/']);
          },
          error: () => (this.loading = false),
        });
      },
      error: () => (this.loading = false),
    });
  }

  register(): void {
    if (!this.validRegistration) return;
    this.loading = true;
    this.api.register(this.regData).subscribe({
      next: (user) => {
        // Auto-login tras el registro
        this.api
          .login({ email: user.email, password: this.regData.password })
          .subscribe({
            next: (res) => {
              this.api.establishSession(res).subscribe({
                next: () => {
                  this.loading = false;
                  this.router.navigate(['/']);
                },
                error: () => (this.loading = false),
              });
            },
            error: () => {
              this.loading = false;
              this.mode = 'login';
              this.loginData.email = user.email;
            },
          });
      },
      error: () => (this.loading = false),
    });
  }
}