import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { ApiService, Branch, Product, ProductVariant, Reservation } from './api.service';

@Component({
  selector: 'app-reservations',
  standalone: true,
  imports: [FormsModule, CommonModule],
  template: `
  <div class="page-head">
    <span class="eyebrow">Aparta tu prenda</span>
    <h1>Reservas</h1>
    <p class="lead">Aparta prendas en tu sucursal favorita y recógelas cuando quieras. (CU13-15)</p>
  </div>

  <div class="admin-tabs" style="justify-content:center;">
    <button class="admin-tab" [class.active]="tab === 'list'" (click)="tab = 'list'">Mis reservas</button>
    <button class="admin-tab" [class.active]="tab === 'create'" (click)="tab = 'create'; loadCatalog()">Nueva reserva (CU13)</button>
    <button *ngIf="isStaff" class="admin-tab" [class.active]="tab === 'all'" (click)="tab = 'all'; loadAll()">Todas (sucursal)</button>
  </div>

  <!-- ============================ LISTA ============================ -->
  <div *ngIf="tab === 'list'">
    <div style="display:flex; gap:.5rem; justify-content:center; margin-bottom:1.5rem; flex-wrap:wrap;">
      <button class="chip" [class.active]="statusFilter === ''" (click)="statusFilter = ''; load()">Todas</button>
      <button class="chip" [class.active]="statusFilter === 'PENDIENTE'" (click)="statusFilter = 'PENDIENTE'; load()">Pendientes</button>
      <button class="chip" [class.active]="statusFilter === 'ATENDIDA'" (click)="statusFilter = 'ATENDIDA'; load()">Atendidas</button>
      <button class="chip" [class.active]="statusFilter === 'CANCELADA'" (click)="statusFilter = 'CANCELADA'; load()">Canceladas</button>
    </div>

    <div *ngIf="reservationsLoading" class="empty-state"><span class="spinner"></span> Cargando reservas…</div>
    <div *ngIf="!reservationsLoading && !reservations.length" class="empty-state">
      <div class="empty-icon">🗓</div>
      <h3>Sin reservas</h3>
      <p>No tienes reservas en este estado. Crea una para apartar tus prendas.</p>
    </div>

    <div class="grid grid-sm" *ngIf="reservations.length">
      <div class="card branch-card" *ngFor="let r of reservations">
        <span class="badge" [ngClass]="statusClass(r.status)">{{ statusLabel(r.status) }}</span>
        <div>
          <h3 style="margin-bottom:.25rem;">{{ r.code }}</h3>
          <div style="font-size:.85rem; color:var(--muted);">
            Sucursal: <strong>{{ r.branch_name }}</strong><br>
            Vence: <strong>{{ r.expiration_date | date: 'dd/MM/yyyy HH:mm' }}</strong>
          </div>
        </div>
        <table style="width:100%; font-size:.85rem;">
          <tr *ngFor="let it of r.items">
            <td>{{ it.product_name }} ({{ it.size_name }} / {{ it.color_name }})</td>
            <td style="text-align:right;">x{{ it.quantity }}</td>
            <td style="text-align:right; color:var(--accent-dark); font-weight:600;">Bs. {{ it.subtotal | number: '1.2-2' }}</td>
          </tr>
        </table>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:.5rem;">
          <span style="font-weight:700; color:var(--accent-dark);">Total: Bs. {{ r.total | number: '1.2-2' }}</span>
          <div style="display:flex; gap:.4rem;">
            <button *ngIf="r.status === 'PENDIENTE'" class="btn btn-danger btn-sm" (click)="cancel(r)">Cancelar</button>
            <button *ngIf="r.status === 'PENDIENTE' && canManage" class="btn btn-accent btn-sm" (click)="attend(r)">Atender</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ============================ CREAR ============================ -->
  <div *ngIf="tab === 'create'" class="card" style="max-width: 720px; margin: 0 auto;">
    <h3 style="margin-bottom:1rem;">Nueva reserva</h3>

    <div class="form-group">
      <label class="form-label">Sucursal donde recogerás</label>
      <select class="form-control" [(ngModel)]="form.branch_id">
        <option [ngValue]="null" disabled>Selecciona una sucursal</option>
        <option *ngFor="let b of branches" [ngValue]="b.id">{{ b.name }} — {{ b.city }}</option>
      </select>
    </div>

    <div class="form-row" style="margin-bottom:1rem;">
      <div class="form-group" style="margin-bottom:0;">
        <label class="form-label">Producto</label>
        <select class="form-control" [(ngModel)]="pick.product_id" (change)="onProductPick()">
          <option [ngValue]="null" disabled>Elige un producto</option>
          <option *ngFor="let p of products" [ngValue]="p.id">{{ p.name }}</option>
        </select>
      </div>
      <div class="form-group" style="margin-bottom:0;">
        <label class="form-label">Variante</label>
        <select class="form-control" [(ngModel)]="pick.variant_id" [disabled]="!pick.product_id">
          <option [ngValue]="null" disabled>Elige talla/color</option>
          <option *ngFor="let v of pickVariants" [ngValue]="v.id">{{ v.size_name }} / {{ v.color_name }} <ng-container *ngIf="v.stock !== undefined">({{ v.stock }})</ng-container></option>
        </select>
      </div>
    </div>
    <div style="display:flex; gap:.5rem; margin-bottom:1.25rem;">
      <input class="form-control" type="number" min="1" [(ngModel)]="pick.quantity" style="max-width:120px;" (keyup.enter)="addLine()">
      <button class="btn btn-outline" (click)="addLine()" [disabled]="!pick.variant_id || !pick.quantity">Agregar prenda</button>
    </div>

    <div class="form-group">
      <label class="form-label">Prendas a reservar</label>
      <div *ngIf="!lines.length" class="empty-state" style="padding:1.25rem;">Aún no has agregado prendas.</div>
      <div *ngFor="let line of lines" style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--line); padding:.5rem 0;">
        <span>{{ line.label }} <strong>x{{ line.quantity }}</strong></span>
        <button class="btn btn-danger btn-sm" (click)="removeLine(line)">&times;</button>
      </div>
    </div>

    <div class="form-group">
      <label class="form-label">Duración de la reserva (horas)</label>
      <input class="form-control" type="number" min="1" max="720" [(ngModel)]="form.expiration_hours" style="max-width:160px;">
    </div>

    <button class="btn btn-primary btn-block" (click)="submitReservation()" [disabled]="submitting || !lines.length || !form.branch_id">
      <span *ngIf="submitting" class="spinner"></span>
      {{ submitting ? 'Reservando…' : 'Confirmar reserva' }}
    </button>
  </div>

  <!-- ============================ TODAS (STAFF) ============================ -->
  <div *ngIf="tab === 'all'">
    <div style="text-align:center; margin-bottom:1rem;">
      <button class="btn btn-outline btn-sm" (click)="expireStale()">Expirar pendientes vencidas</button>
    </div>
    <div *ngIf="allReservationsLoading" class="empty-state"><span class="spinner"></span> Cargando…</div>
    <div *ngIf="!allReservationsLoading && !allReservations.length" class="empty-state"><p>No hay reservas registradas.</p></div>
    <div class="table-wrap card" style="padding:0;" *ngIf="allReservations.length">
      <table class="table">
        <thead>
          <tr><th>Código</th><th>Cliente</th><th>Sucursal</th><th>Estado</th><th>Vence</th><th>Prendas</th><th>Total</th><th>Acciones</th></tr>
        </thead>
        <tbody>
          <tr *ngFor="let r of allReservations">
            <td><strong>{{ r.code }}</strong></td>
            <td>{{ r.client_name }}</td>
            <td>{{ r.branch_name }}</td>
            <td><span class="badge" [ngClass]="statusClass(r.status)">{{ statusLabel(r.status) }}</span></td>
            <td>{{ r.expiration_date | date: 'dd/MM/yyyy HH:mm' }}</td>
            <td>{{ r.item_count }}</td>
            <td>Bs. {{ r.total | number: '1.2-2' }}</td>
            <td>
              <div class="actions">
                <button *ngIf="r.status === 'PENDIENTE' && canManage" class="btn btn-accent btn-sm" (click)="attend(r)">Atender</button>
                <button *ngIf="r.status === 'PENDIENTE'" class="btn btn-danger btn-sm" (click)="cancel(r)">Cancelar</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
  `,
})
export class ReservationsComponent implements OnInit {
  tab: 'list' | 'create' | 'all' = 'list';
  reservations: Reservation[] = [];
  allReservations: Reservation[] = [];
  reservationsLoading = false;
  allReservationsLoading = false;
  statusFilter = '';
  submitting = false;
  isStaff = false;
  canManage = false;

  branches: Branch[] = [];
  products: Product[] = [];
  pickVariants: ProductVariant[] = [];

  form = {
    branch_id: null as number | null,
    expiration_hours: 48,
  };

  pick = {
    product_id: null as number | null,
    variant_id: null as number | null,
    quantity: 1,
  };

  lines: { variant: ProductVariant; quantity: number; label: string }[] = [];

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    const user = this.api.currentUser.value;
    this.isStaff = !!user && ['Administrador', 'Encargado de Sucursal', 'Cajero'].includes(user.role_name);
    this.canManage = !!user && ['Administrador', 'Encargado de Sucursal'].includes(user.role_name);
    this.api.getBranches().subscribe((bs) => (this.branches = bs));
    this.load();
  }

  load(): void {
    this.reservationsLoading = true;
    this.api.getReservations(this.statusFilter).subscribe({
      next: (res) => {
        this.reservations = res;
        this.reservationsLoading = false;
      },
      error: () => (this.reservationsLoading = false),
    });
  }

  loadAll(): void {
    this.allReservationsLoading = true;
    this.api.getReservations('', true).subscribe({
      next: (res) => {
        this.allReservations = res;
        this.allReservationsLoading = false;
      },
      error: () => (this.allReservationsLoading = false),
    });
  }

  loadCatalog(): void {
    if (!this.products.length) {
      this.api.getProducts().subscribe((p) => (this.products = p));
    }
  }

  onProductPick(): void {
    this.pick.variant_id = null;
    this.pickVariants = [];
    if (this.pick.product_id) {
      this.api.getVariants(this.pick.product_id).subscribe((v) => (this.pickVariants = v));
    }
  }

  addLine(): void {
    const variant = this.pickVariants.find((v) => v.id === this.pick.variant_id);
    if (!variant) return;
    const qty = Math.max(1, Math.floor(this.pick.quantity || 1));
    this.lines = [...this.lines, { variant, quantity: qty, label: `${variant.size_name} / ${variant.color_name}` }];
    this.pick.quantity = 1;
  }

  removeLine(line: { variant: ProductVariant }): void {
    this.lines = this.lines.filter((l) => l.variant.id !== line.variant.id);
  }

  submitReservation(): void {
    if (!this.form.branch_id || !this.lines.length) return;
    this.submitting = true;
    this.api
      .createReservation({
        branch_id: this.form.branch_id,
        expiration_hours: this.form.expiration_hours || 48,
        items: this.lines.map((l) => ({ variant_id: l.variant.id, quantity: l.quantity })),
      })
      .subscribe({
        next: () => {
          this.submitting = false;
          this.lines = [];
          this.tab = 'list';
          this.load();
        },
        error: () => (this.submitting = false),
      });
  }

  cancel(r: Reservation): void {
    this.api.cancelReservation(r.id).subscribe(() => this.reloadAll());
  }

  attend(r: Reservation): void {
    this.api.attendReservation(r.id).subscribe(() => this.reloadAll());
  }

  expireStale(): void {
    this.api.reserveExpireStale().subscribe(() => this.loadAll());
  }

  private reloadAll(): void {
    if (this.tab === 'all') this.loadAll();
    else this.load();
  }

  statusClass(s: string): string {
    return (
      {
        PENDIENTE: 'badge-info',
        ATENDIDA: 'badge-success',
        CANCELADA: 'badge-danger',
        VENCIDA: 'badge-danger',
      }[s] || 'badge-info'
    );
  }

  statusLabel(s: string): string {
    return (
      {
        PENDIENTE: 'Pendiente',
        ATENDIDA: 'Atendida',
        CANCELADA: 'Cancelada',
        VENCIDA: 'Vencida',
      }[s] || s
    );
  }
}