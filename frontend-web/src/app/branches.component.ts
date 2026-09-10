import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService, Branch } from './api.service';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-branches',
  standalone: true,
  imports: [FormsModule, CommonModule],
  template: `
  <div class="page-head">
    <span class="eyebrow">Dónde encontrarnos</span>
    <h1>Nuestras sucursales</h1>
    <p class="lead">Visítanos en cualquiera de nuestras tiendas. Encuentra la más cercana a ti.</p>
    <div style="max-width: 420px; margin: 1.5rem auto 0; display: flex; gap: 0.5rem;">
      <input class="form-control" [(ngModel)]="city" placeholder="Filtrar por ciudad…" (keyup.enter)="search()">
      <button class="btn btn-accent" (click)="search()">Filtrar</button>
    </div>
  </div>

  <div *ngIf="loading && !branches.length" class="grid">
    <div *ngFor="let s of [1,2,3]" class="skeleton" style="height:180px; border-radius:10px;"></div>
  </div>

  <div class="empty-state" *ngIf="!loading && !branches.length">
    <div class="empty-icon">📍</div>
    <h3>Sin resultados</h3>
    <p>No encontramos sucursales en "{{ city }}". Prueba con otra ciudad.</p>
  </div>

  <div class="grid" *ngIf="branches.length">
    <div class="card branch-card" *ngFor="let b of branches">
      <h3>{{ b.name }}</h3>
      <span class="badge badge-accent" style="align-self:flex-start;">{{ b.city }}</span>
      <div class="branch-meta">
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
        <span>{{ b.address || 'Dirección por confirmar' }}</span>
      </div>
      <div class="branch-meta">
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"/></svg>
        <span>{{ b.phone || 'Teléfono no disponible' }}</span>
      </div>
    </div>
  </div>
  `,
})
export class BranchesComponent implements OnInit {
  city = '';
  branches: Branch[] = [];
  loading = false;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.search();
  }

  search(): void {
    this.loading = true;
    this.api.getBranches(this.city).subscribe({
      next: (res) => {
        this.branches = res;
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }
}