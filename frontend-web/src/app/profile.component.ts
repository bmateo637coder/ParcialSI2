
import { Component, OnInit } from '@angular/core';
import { ApiService } from './api.service';
import { CommonModule } from '@angular/common';
@Component({
  standalone: true, imports: [CommonModule],
  template: `
    <h2>Mi Perfil Personal</h2>
    
    <div class="card" style="max-width: 600px; margin: 2rem auto; text-align: center;" *ngIf="user; else loading">
        <div style="width: 80px; height: 80px; background: var(--primary); color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 2rem; font-weight: bold; margin: 0 auto 1.5rem auto;">
            {{user.first_name.charAt(0)}}{{user.last_name.charAt(0)}}
        </div>
        <h3>{{user.first_name}} {{user.last_name}}</h3>
        <p style="color: var(--secondary); margin-bottom: 1rem;">{{user.email}}</p>
        <span class="alert alert-info" style="padding: 0.25rem 0.75rem; border-radius: 99px; font-size: 0.85rem;">
            Rol Asignado: {{role}}
        </span>
        
        <hr style="margin: 2rem 0; border: none; border-top: 1px solid var(--border);">
        <button class="btn btn-outline" style="width: 100%;">Editar Información</button>
    </div>
    
    <ng-template #loading>
        <div class="text-center" style="padding: 3rem; color: var(--secondary);">
            <p *ngIf="!errorMsg">Cargando información del perfil...</p>
            <p *ngIf="errorMsg" style="color: var(--danger);">{{errorMsg}}</p>
        </div>
    </ng-template>
  `
})
export class ProfileComponent implements OnInit {
  user: any;
  role: string = '';
  errorMsg = '';
  constructor(private api: ApiService) {}
  ngOnInit() {
    const email = localStorage.getItem('email');
    this.role = localStorage.getItem('role') || 'Cliente';
    if(email) {
        this.api.getProfile(email).subscribe({
            next: (res:any) => this.user = res,
            error: (err) => this.errorMsg = 'No se pudo cargar el perfil. Por favor vuelve a iniciar sesión.'
        });
    } else {
        this.errorMsg = 'No hay sesión activa.';
    }
  }
}
