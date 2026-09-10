import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService, User } from './api.service';
import { CommonModule } from '@angular/common';
import { ToastService } from './toast.service';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [FormsModule, CommonModule],
  template: `
  <div class="page-head">
    <span class="eyebrow">Tu cuenta</span>
    <h1>Mi perfil</h1>
  </div>

  <ng-container *ngIf="user; else loading">
    <div class="card profile-card">
      <div class="profile-avatar">{{ initials }}</div>
      <h2 style="margin-bottom:.25rem;">{{ user.first_name }} {{ user.last_name }}</h2>
      <p class="profile-email">{{ user.email }}</p>
      <span class="badge badge-accent">{{ user.role_name }}</span>

      <hr style="border:none; border-top:1px solid var(--line); margin:1.75rem 0;">

      <form (ngSubmit)="save()" novalidate>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Nombre</label>
            <input class="form-control" [(ngModel)]="edit.first_name" name="first" required>
          </div>
          <div class="form-group">
            <label class="form-label">Apellido</label>
            <input class="form-control" [(ngModel)]="edit.last_name" name="last" required>
          </div>
        </div>
        <p style="text-align:right;">
          <button class="btn btn-accent" type="submit" [disabled]="saving || !edit.first_name.trim() || !edit.last_name.trim()">
            <span *ngIf="saving" class="spinner"></span> Guardar cambios
          </button>
        </p>
      </form>
    </div>
  </ng-container>

  <ng-template #loading>
    <div class="text-center" style="padding: 3rem; color: var(--muted);">
      <p *ngIf="!errorMsg">Cargando tu perfil…</p>
      <p *ngIf="errorMsg" style="color: var(--danger);">{{ errorMsg }}</p>
    </div>
  </ng-template>
  `,
})
export class ProfileComponent implements OnInit {
  user: User | null = null;
  edit = { first_name: '', last_name: '' };
  saving = false;
  errorMsg = '';

  constructor(private api: ApiService, private toast: ToastService) {}

  ngOnInit(): void {
    this.api.getProfile().subscribe({
      next: (u) => {
        this.user = u;
        this.edit = { first_name: u.first_name, last_name: u.last_name };
      },
      error: () => {
        this.errorMsg = 'No se pudo cargar el perfil. Vuelve a iniciar sesión.';
      },
    });
  }

  get initials(): string {
    if (!this.user) return '';
    const a = this.user.first_name?.charAt(0) || '';
    const b = this.user.last_name?.charAt(0) || '';
    return (a + b).toUpperCase();
  }

  save(): void {
    this.saving = true;
    this.api
      .updateProfile({ first_name: this.edit.first_name.trim(), last_name: this.edit.last_name.trim() })
      .subscribe({
        next: () => {
          this.saving = false;
          this.toast.success('Perfil actualizado.');
        },
        error: () => (this.saving = false),
      });
  }
}