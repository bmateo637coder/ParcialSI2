import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { ApiService, AvailabilityItem, Order } from './api.service';
import { ToastService } from './toast.service';

interface PosLine {
  av: AvailabilityItem;
  quantity: number;
}

@Component({
  selector: 'app-pos',
  standalone: true,
  imports: [FormsModule, CommonModule],
  template: `
  <div class="page-head">
    <span class="eyebrow">Registro de ventas en sucursal</span>
    <h1>Caja (POS)</h1>
    <p class="lead">Registra una venta presencial por parte del cajero. (CU18)</p>
  </div>

  <div style="display:grid; grid-template-columns: 1fr 320px; gap: 1.5rem; align-items:start;" class="pos-layout">
    <div class="card">
      <h3 style="margin-bottom: 1rem;">Artículos de la venta</h3>

      <div class="form-row">
        <div class="form-group" style="flex:2;">
          <label class="form-label">Artículo (variante con stock)</label>
          <select class="form-control" [(ngModel)]="selectedAv" [disabled]="!available.length">
            <option [ngValue]="null">
              {{ available.length ? 'Elige una prenda…' : 'Sin prendas con stock en la sucursal' }}
            </option>
            <option *ngFor="let av of available" [ngValue]="av">
              {{ av.product_name }} · {{ av.size_name || '-' }} / {{ av.color_name || '-' }} —
              Bs. {{ av.price || 0 | number: '1.2-2' }} ({{ av.available }} disp.)
            </option>
          </select>
        </div>
        <div class="form-group" style="flex:1;">
          <label class="form-label">Cantidad</label>
          <input class="form-control" type="number" min="1" [(ngModel)]="addQty">
        </div>
        <div class="form-group" style="flex:0 0 auto; align-self:flex-end; padding-bottom:.25rem;">
          <button class="btn btn-accent" (click)="addLine()" [disabled]="!selectedAv || addingLine">Agregar</button>
        </div>
      </div>

      <table class="table" *ngIf="lines.length" style="margin-top:1rem;">
        <thead>
          <tr>
            <th>Producto</th>
            <th>Precio</th>
            <th>Cant.</th>
            <th>Subtotal</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr *ngFor="let line of lines">
            <td>{{ line.av.product_name }} <em style="color:var(--muted);">{{ line.av.size_name }} / {{ line.av.color_name }}</em></td>
            <td>Bs. {{ line.av.price || 0 | number: '1.2-2' }}</td>
            <td>{{ line.quantity }}</td>
            <td><strong>Bs. {{ lineSubtotal(line) | number: '1.2-2' }}</strong></td>
            <td><button class="btn btn-danger btn-sm" (click)="removeLine(line)">&times;</button></td>
          </tr>
        </tbody>
      </table>

      <div *ngIf="!lines.length && !loadingAv" class="empty-state" style="padding:1.5rem;">
        <p>Agrega al menos un artículo para registrar la venta.</p>
      </div>
    </div>

    <div class="card">
      <h3 style="margin-bottom: 1rem;">Resumen y pago</h3>

      <div class="form-group" style="margin-bottom:.75rem;">
        <label class="form-label">Sucursal</label>
        <select class="form-control" [(ngModel)]="branchId" (ngModelChange)="loadAvailability()">
          <option [ngValue]="null">Elige la sucursal</option>
          <option *ngFor="let b of branches" [ngValue]="b.id">{{ b.name }} — {{ b.city }}</option>
        </select>
      </div>

      <div class="form-group" *ngIf="isAdmin">
        <label class="form-label">Cliente (opcional, por defecto "Mostrador")</label>
        <input class="form-control" [(ngModel)]="clientQuery" placeholder="Buscar por correo…" (keyup.enter)="searchClients()">
        <select class="form-control" [(ngModel)]="clientId" style="margin-top:.4rem;">
          <option [ngValue]="null">Cliente de mostrador</option>
          <option *ngFor="let u of clients" [ngValue]="u.id">{{ u.first_name }} {{ u.last_name }} ({{ u.email }})</option>
        </select>
      </div>

      <div class="form-group" style="margin-bottom:.75rem;">
        <label class="form-label">Método de pago</label>
        <select class="form-control" [(ngModel)]="paymentMethod">
          <option value="EFECTIVO">Efectivo</option>
          <option value="TARJETA">Tarjeta</option>
          <option value="TRANSFERENCIA">Transferencia</option>
        </select>
      </div>

      <div class="form-group" *ngIf="paymentMethod === 'TARJETA'" style="margin-bottom:.75rem;">
        <label class="form-label">Número de tarjeta</label>
        <input class="form-control" [(ngModel)]="cardNumber" placeholder="4000000000000002 (rechazo de prueba…)" maxlength="19">
        <div class="form-hint">En sandbox, <code>4000000000000002</code> / <code>4000000000009995</code> se rechazan.</div>
      </div>

      <div style="display:flex; justify-content:space-between; margin:1rem 0;">
        <span style="color:var(--muted);">Total a cobrar</span>
        <strong style="font-size:1.15rem; color:var(--accent-dark);">Bs. {{ total | number: '1.2-2' }}</strong>
      </div>

      <div class="alert alert-danger" *ngIf="errorMsg">{{ errorMsg }}</div>

      <button class="btn btn-primary btn-block" (click)="submit()" [disabled]="paying || !lines.length || !branchId">
        <span *ngIf="paying" class="spinner"></span>
        {{ paying ? 'Registrando venta…' : 'Cobrar y registrar venta' }}
      </button>
    </div>
  </div>

  <!-- Resultado -->
  <div class="modal-backdrop" *ngIf="result" (click.self)="result = null">
    <div class="modal">
      <div class="modal-head">
        <h3>{{ result.status === 'PAGADO' ? '¡Venta registrada!' : 'Pago pendiente' }}</h3>
        <button class="modal-close" (click)="result = null">&times;</button>
      </div>
      <div class="modal-body">
        <span class="badge"
          [class.badge-success]="result.status === 'PAGADO'"
          [class.badge-warning]="result.status === 'PENDIENTE'">
          {{ result.status }}
        </span>
        <h2 style="margin:.75rem 0 .5rem;">Pedido #{{ result.id }}</h2>
        <p *ngIf="result.receipt_number" style="font-size:.9rem; color:var(--muted);">
          Comprobante: <strong>{{ result.receipt_number }}</strong>
        </p>
        <p>Total: <strong>Bs. {{ result.total | number: '1.2-2' }}</strong> vía {{ result.payment?.method }}
          ({{ result.payment?.status }}).</p>

        <ng-container *ngIf="result.status !== 'PAGADO'">
          <p style="margin-top:.5rem;">La tarjeta fue rechazada. Puedes completar el pago con efectivo o esperar al cliente.</p>
          <button class="btn btn-accent btn-block" (click)="payPendingCash()" [disabled]="paying">
            <span *ngIf="paying" class="spinner"></span> Completar con efectivo
          </button>
        </ng-container>
      </div>
      <div class="modal-foot">
        <button class="btn btn-outline" (click)="result = null">Cerrar</button>
      </div>
    </div>
  </div>
  `,
  styles: [`
    @media (max-width: 900px) { .pos-layout { grid-template-columns: 1fr !important; } }
    .form-hint { font-size:.78rem; color:var(--muted); margin-top:.3rem; }
    .alert-danger {
      background: rgba(220,53,69,.08); border: 1px solid rgba(220,53,69,.35);
      color:#c0392b; padding:.7rem .9rem; border-radius:10px; font-size:.85rem; margin-bottom:.9rem;
    }
  `],
})
export class PosComponent implements OnInit {
  branches: { id: number; name: string; city: string }[] = [];
  branchId: number | null = null;
  available: AvailabilityItem[] = [];
  loadingAv = false;
  selectedAv: AvailabilityItem | null = null;
  addQty = 1;
  addingLine = false;
  lines: PosLine[] = [];
  clients: { id: number; first_name: string; last_name: string; email: string }[] = [];
  clientQuery = '';
  clientId: number | null = null;
  paymentMethod = 'EFECTIVO';
  cardNumber = '';
  errorMsg = '';
  paying = false;
  result: Order | null = null;

  constructor(private api: ApiService, private toast: ToastService) {}

  get isAdmin(): boolean {
    return this.api.isAdmin;
  }

  ngOnInit(): void {
    this.api.getBranches().subscribe({
      next: (bs) => {
        this.branches = bs;
        if (bs.length) {
          this.branchId = bs[0].id;
          this.loadAvailability();
        }
      },
      error: () => {},
    });
  }

  loadAvailability(): void {
    if (!this.branchId) {
      this.available = [];
      return;
    }
    this.loadingAv = true;
    this.api.getAvailability({ branch_id: this.branchId }).subscribe({
      next: (res) => {
        this.available = res;
        this.loadingAv = false;
      },
      error: () => (this.loadingAv = false),
    });
  }

  addLine(): void {
    if (!this.selectedAv) return;
    const qty = Math.max(1, Math.floor(this.addQty || 1));
    if (qty > this.selectedAv.available) {
      this.toast.info(`Solo hay ${this.selectedAv.available} disponibles.`);
      return;
    }
    const existing = this.lines.find((l) => l.av.variant_id === this.selectedAv!.variant_id);
    if (existing) {
      existing.quantity = Math.min(existing.quantity + qty, this.selectedAv.available);
    } else {
      this.lines.push({ av: this.selectedAv, quantity: qty });
    }
    this.selectedAv = null;
    this.addQty = 1;
  }

  removeLine(line: PosLine): void {
    this.lines = this.lines.filter((l) => l !== line);
  }

  lineSubtotal(line: PosLine): number {
    return (line.av.price || 0) * line.quantity;
  }

  get total(): number {
    return this.lines.reduce((sum, l) => sum + this.lineSubtotal(l), 0);
  }

  searchClients(): void {
    if (!this.clientQuery.trim()) return;
    this.api.getUsers({ q: this.clientQuery.trim() }).subscribe({
      next: (u) => {
        this.clients = u;
        this.clientId = null;
      },
      error: () => {},
    });
  }

  submit(): void {
    if (!this.branchId || !this.lines.length) return;
    this.errorMsg = '';
    this.paying = true;
    this.api
      .posSale({
        branch_id: this.branchId,
        items: this.lines.map((l) => ({ variant_id: l.av.variant_id, quantity: l.quantity })),
        client_id: this.clientId,
        payment_method: this.paymentMethod,
        card_number: this.paymentMethod === 'TARJETA' ? this.cardNumber.trim() || null : null,
      })
      .subscribe({
        next: (order) => {
          this.paying = false;
          this.result = order;
          this.lines = [];
          this.clientId = null;
          this.cardNumber = '';
          this.loadAvailability();
        },
        error: (err: unknown) => {
          this.paying = false;
          const detail = (err as { error?: { detail?: string } })?.error?.detail as string | undefined;
          this.errorMsg =
            typeof detail === 'string' ? detail : 'No se pudo registrar la venta. Verifica el stock.';
        },
      });
  }

  payPendingCash(): void {
    if (!this.result) return;
    this.paying = true;
    this.api.payOrder(this.result.id, { payment_method: 'EFECTIVO' }).subscribe({
      next: (updated) => {
        this.paying = false;
        this.loadAvailability();
        this.toast.success(updated.status === 'PAGADO' ? 'Pago completado con efectivo.' : 'Pago no confirmado.');
        this.result = updated;
        setTimeout(() => (this.result = null), 1200);
      },
      error: () => (this.paying = false),
    });
  }
}