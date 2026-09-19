import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { ApiService } from './api.service';
import { ToastService } from './toast.service';

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
        <div style="display:flex; justify-content:flex-end;">
          <button type="button" class="link-btn" (click)="mode = 'forgot'">¿Olvidaste tu contraseña?</button>
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

      <!-- OLVIDÉ MI CONTRASEÑA -->
      <div *ngIf="mode === 'forgot'">
        <div class="form-group" *ngIf="!resetToken">
          <p style="color:var(--muted); font-size:.9rem; margin-bottom:1rem;">
            Escribe tu correo y te enviaremos un enlace para restablecer tu contraseña.
            <em>Modo demo: el código se muestra en pantalla.</em>
          </p>
          <label class="form-label">Correo electrónico</label>
          <input class="form-control" type="email" [(ngModel)]="forgotEmail" name="forgotEmail" placeholder="ejemplo@correo.com">
          <button class="btn btn-accent btn-block" style="margin-top:1rem;" (click)="requestReset()" [disabled]="loading || !forgotEmail">
            <span *ngIf="loading" class="spinner"></span>
            Enviar enlace de recuperación
          </button>
        </div>

        <div *ngIf="resetToken">
          <p style="color:var(--muted); font-size:.9rem; margin-bottom:1rem;">
            Ingresa el código de recuperación y tu nueva contraseña.
          </p>
          <div class="form-group">
            <label class="form-label">Código de recuperación</label>
            <textarea class="form-control" [(ngModel)]="resetToken" name="resetToken" rows="3" readonly></textarea>
          </div>
          <div class="form-group">
            <label class="form-label">Nueva contraseña</label>
            <input class="form-control" type="password" [(ngModel)]="newPassword" name="newPassword" placeholder="Mínimo 6 caracteres">
            <div class="form-error" *ngIf="newPassword && newPassword.length < 6">La contraseña debe tener al menos 6 caracteres.</div>
          </div>
          <div class="form-group" *ngIf="resetMessage">
            <p class="success-note">{{ resetMessage }}</p>
          </div>
          <button class="btn btn-accent btn-block" (click)="confirmReset()" [disabled]="loading || !resetToken || newPassword.length < 6">
            <span *ngIf="loading" class="spinner"></span>
            Restablecer contraseña
          </button>
          <button class="btn btn-outline btn-block" style="margin-top:.75rem;" (click)="backToLogin()">Volver a iniciar sesión</button>
        </div>

        <div *ngIf="!resetToken" style="margin-top:.75rem;">
          <button class="btn btn-outline btn-block" (click)="mode = 'login'">Volver a iniciar sesión</button>
        </div>
      </div>

      <p class="auth-note">Cuenta demo admin: <strong>admin@fashionstore.com / admin123</strong></p>
    </div>
  </div>
  `,
})
export class AuthComponent {
  mode: 'login' | 'register' | 'forgot' = 'login';
  loading = false;
  loginData = { email: '', password: '' };
  regData = { first_name: '', last_name: '', email: '', password: '' };
  forgotEmail = '';
  resetToken = '';
  newPassword = '';
  resetMessage = '';

  constructor(private api: ApiService, private router: Router, private toast: ToastService) {}

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

  requestReset(): void {
    if (!this.forgotEmail) return;
    this.loading = true;
    this.resetMessage = '';
    this.api.forgotPassword(this.forgotEmail).subscribe({
      next: (res) => {
        this.loading = false;
        this.resetToken = res.reset_token || '';
        if (!this.resetToken) {
          this.resetMessage = res.message;
        }
      },
      error: () => (this.loading = false),
    });
  }

  confirmReset(): void {
    if (!this.resetToken || this.newPassword.length < 6) return;
    this.loading = true;
    this.api.resetPassword(this.resetToken.trim(), this.newPassword).subscribe({
      next: (res) => {
        this.loading = false;
        this.resetMessage = res.message;
        this.resetToken = '';
        this.newPassword = '';
        this.mode = 'login';
        this.toast.success(res.message);
      },
      error: () => (this.loading = false),
    });
  }

  backToLogin(): void {
    this.resetToken = '';
    this.newPassword = '';
    this.resetMessage = '';
    this.forgotEmail = '';
    this.mode = 'login';
  }
}