import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ApiService, AvailabilityItem } from './api.service';
import { ToastService } from './toast.service';

const FALLBACK_IMG =
  'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&q=80&w=300';

@Component({
  selector: 'app-availability',
  standalone: true,
  imports: [FormsModule, CommonModule],
  template: `
  <div class="page-head">
    <span class="eyebrow">Disponibilidad en tiendas</span>
    <h1>¿Dónde está disponible?</h1>
    <p class="lead">Consulta en tiempo real el stock de cada prenda en nuestras sucursales. (CU11)</p>

    <div style="max-width: 560px; margin: 1.75rem auto 0; display: flex; gap: 0.5rem;">
      <input class="form-control" [(ngModel)]="q" placeholder="Buscar por prenda o color…" (keyup.enter)="search()">
      <button class="btn btn-accent" (click)="search()" [disabled]="loading">Buscar</button>
    </div>
  </div>

  <!-- Filtro por sucursal -->
  <div style="text-align: center; margin-bottom: 2rem;">
    <label class="form-label" style="display:inline-block; margin-right: .75rem;">Sucursal:</label>
    <select class="form-control" style="max-width: 320px; display: inline-block;" [(ngModel)]="branchId" (change)="search()">
      <option [ngValue]="null">Todas las sucursales</option>
      <option *ngFor="let b of branches" [ngValue]="b.id">{{ b.name }} — {{ b.city }}</option>
    </select>
  </div>

  <div *ngIf="loading" class="empty-state"><span class="spinner"></span> Consultando inventario…</div>

  <div *ngIf="!loading && !rows.length" class="empty-state">
    <div class="empty-icon">🔍</div>
    <h3>Sin disponibilidad</h3>
    <p>No encontramos stock para esta búsqueda. Prueba con otros términos o sucursales.</p>
  </div>

  <div *ngIf="rows.length" class="table-wrap card" style="padding: 0;">
    <table class="table">
      <thead>
        <tr>
          <th>Prenda</th>
          <th>Variante</th>
          <th>Sucursal</th>
          <th>Stock</th>
          <th>Precio</th>
          <th>Acción</th>
        </tr>
      </thead>
      <tbody>
        <tr *ngFor="let r of rows">
          <td>
            <div style="display:flex; align-items:center; gap:.75rem;">
              <img [src]="r.image_url || fallbackImg" alt="" style="width:40px; height:52px; object-fit:cover; border-radius:6px;">
              <div>
                <strong>{{ r.product_name }}</strong>
                <div style="font-size:.8rem; color:var(--muted);">SKU {{ r.sku }}</div>
              </div>
            </div>
          </td>
          <td>{{ r.size_name }} <span style="color:var(--muted);">·</span> {{ r.color_name }}</td>
          <td>{{ r.branch_name }}<div style="font-size:.8rem; color:var(--muted);">{{ r.city }}</div></td>
          <td>
            <span [class.stock-ok]="r.available > 10" [class.stock-low]="r.available <= 10" [class.stock-out]="r.available === 0">
              {{ r.available }} unidades
            </span>
          </td>
          <td>Bs. {{ r.price | number: '1.2-2' }}</td>
          <td>
            <button class="btn btn-accent btn-sm" (click)="addToCart(r)" [disabled]="addingId === r.variant_id || r.available === 0">
              <span *ngIf="addingId === r.variant_id" class="spinner"></span>
              {{ r.available === 0 ? 'Sin stock' : (addingId === r.variant_id ? 'Agregando…' : 'Agregar al carrito') }}
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
  `,
})
export class AvailabilityComponent implements OnInit {
  q = '';
  rows: AvailabilityItem[] = [];
  branches: { id: number; name: string; city: string }[] = [];
  branchId: number | null = null;
  loading = false;
  addingId: number | null = null;
  fallbackImg = FALLBACK_IMG;

  constructor(private api: ApiService, private router: Router, private toast: ToastService) {}

  ngOnInit(): void {
    this.api.getBranches().subscribe((bs) => (this.branches = bs));
    this.search();
  }

  search(): void {
    this.loading = true;
    this.api
      .getAvailability({ q: this.q, branch_id: this.branchId ?? undefined })
      .subscribe({
        next: (res) => {
          this.rows = res;
          this.loading = false;
        },
        error: () => (this.loading = false),
      });
  }

  addToCart(r: AvailabilityItem): void {
    if (this.addingId !== null) return;
    if (!this.api.isAuthenticated) {
      this.toast.info('Inicia sesión para agregar productos al carrito.');
      this.router.navigate(['/auth']);
      return;
    }
    if (r.available <= 0) return;
    this.addingId = r.variant_id;
    this.api.addToCart(r.variant_id, 1).subscribe({
      next: () => {
        this.addingId = null;
        this.toast.success('Agregado al carrito.');
      },
      error: () => (this.addingId = null),
    });
  }
}