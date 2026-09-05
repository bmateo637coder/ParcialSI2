
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from './api.service';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
@Component({
  standalone: true, imports: [FormsModule, CommonModule],
  template: `
    <div class="grid" style="grid-template-columns: 1fr 1fr; align-items: start;">
      <div class="card">
        <h2>Iniciar Sesión</h2>
        <div class="alert alert-danger" *ngIf="loginError">{{loginError}}</div>
        <div class="form-group">
            <label class="form-label">Correo Electrónico</label>
            <input class="form-control" [(ngModel)]="loginData.email" placeholder="ejemplo@correo.com">
        </div>
        <div class="form-group">
            <label class="form-label">Contraseña</label>
            <input class="form-control" type="password" [(ngModel)]="loginData.password" placeholder="Tu contraseña">
        </div>
        <button class="btn btn-primary" style="width: 100%" (click)="login()">Acceder a mi cuenta</button>
      </div>

      <div class="card">
        <h2>Crear Cuenta Nueva</h2>
        <div class="form-group">
            <label class="form-label">Nombre</label>
            <input class="form-control" [(ngModel)]="regData.first_name">
        </div>
        <div class="form-group">
            <label class="form-label">Apellido</label>
            <input class="form-control" [(ngModel)]="regData.last_name">
        </div>
        <div class="form-group">
            <label class="form-label">Correo Electrónico</label>
            <input class="form-control" [(ngModel)]="regData.email">
        </div>
        <div class="form-group">
            <label class="form-label">Contraseña</label>
            <input class="form-control" type="password" [(ngModel)]="regData.password">
        </div>
        <button class="btn btn-outline" style="width: 100%" (click)="register()">Registrarme</button>
      </div>
    </div>
  `
})
export class AuthComponent {
  loginData = {email:'', password:''};
  regData = {first_name:'', last_name:'', email:'', password:''};
  loginError = '';
  constructor(private api: ApiService, private router: Router) {}
  login() {
    this.loginError = '';
    this.api.login(this.loginData).subscribe({
      next: (res: any) => {
        localStorage.setItem('token', res.access_token);
        localStorage.setItem('role', res.role);
        localStorage.setItem('email', this.loginData.email);
        this.api.currentUser.next({token: res.access_token, role: res.role, email: this.loginData.email});
        this.router.navigate(['/']);
      },
      error: (err) => {
        this.loginError = 'Credenciales incorrectas o error en el servidor.';
      }
    });
  }
  register() {
    this.api.register(this.regData).subscribe({
      next: () => alert('Cuenta creada con éxito. Por favor, inicia sesión.'),
      error: () => alert('Error al registrar la cuenta.')
    });
  }
}
