import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService, User, Order } from './api.service';
import { CommonModule } from '@angular/common';
import { ToastService } from './toast.service';

const ORDER_EMOJI: Record<string, string> = {
  PENDIENTE: '⏳',
  PAGADO: '💳',
  ENVIADO: '🚚',
  ENTREGADO: '✅',
  CANCELADO: '✖️',
};

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
        <h3 style="margin-bottom:1rem;">Datos personales</h3>
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
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Correo electrónico</label>
            <input class="form-control" type="email" [(ngModel)]="edit.email" name="email" required>
          </div>
          <div class="form-group">
            <label class="form-label">Teléfono</label>
            <input class="form-control" [(ngModel)]="edit.phone" name="phone" placeholder="+591 7 ...">
          </div>
        </div>
        <p style="text-align:right;">
          <button class="btn btn-accent" type="submit" [disabled]="saving || !validProfile">
            <span *ngIf="saving" class="spinner"></span> Guardar datos
          </button>
        </p>
      </form>

      <hr style="border:none; border-top:1px solid var(--line); margin:1.5rem 0;">

      <h3 style="margin-bottom:1rem;">Cambiar contraseña</h3>
      <form (ngSubmit)="changePassword()" novalidate>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Nueva contraseña</label>
            <input class="form-control" type="password" [(ngModel)]="pwd.new_password" name="newPwd" placeholder="Mínimo 6 caracteres">
            <div class="form-error" *ngIf="pwd.new_password && pwd.new_password.length < 6">La contraseña debe tener al menos 6 caracteres.</div>
          </div>
          <div class="form-group">
            <label class="form-label">Repetir contraseña</label>
            <input class="form-control" type="password" [(ngModel)]="pwd.confirm" name="confirmPwd" placeholder="Repite la contraseña">
            <div class="form-error" *ngIf="pwd.confirm && pwd.new_password !== pwd.confirm">Las contraseñas no coinciden.</div>
          </div>
        </div>
        <p style="text-align:right;">
          <button class="btn btn-outline" type="submit" [disabled]="changingPwd || !validPassword">
            <span *ngIf="changingPwd" class="spinner"></span> Actualizar contraseña
          </button>
        </p>
      </form>
    </div>

    <div class="card" style="margin-top:1.5rem;">
      <div class="toolbar">
        <div>
          <h2>Mis pedidos</h2>
          <p style="color:var(--muted); font-size:.9rem; margin-top:.25rem;">Historial de compras (CU26).</p>
        </div>
      </div>

      <div *ngIf="ordersLoading" class="skeleton" style="height:60px;"></div>
      <div class="empty-state" *ngIf="!ordersLoading && !orders.length">
        <h3>Aún no tienes pedidos</h3>
        <p>Cuando hagas una compra, este historial se mostrará aquí.</p>
      </div>

      <div class="order-list" *ngIf="!ordersLoading && orders.length">
        <div class="order-item" *ngFor="let o of orders">
          <div class="order-head">
            <span class="badge badge-accent">#{{ o.id }} · {{ o.order_type }}</span>
            <span class="badge"
              [class.badge-success]="o.status === 'ENTREGADO'"
              [class.badge-danger]="o.status === 'CANCELADO'"
              [class.badge-info]="o.status === 'ENVIADO'"
              [class.badge-warning]="o.status === 'PAGADO' || o.status === 'PENDIENTE'">
              {{ ORDER_EMOJI[o.status] || '' }} {{ o.status }}
            </span>
          </div>
          <div style="margin-top:.6rem; font-size:.9rem; color:var(--muted);">
            {{ o.created_at ? (o.created_at | date: 'd MMM yyyy, HH:mm') : '' }}
            <span *ngIf="o.branch_name"> · {{ o.branch_name }}</span>
            <span *ngIf="o.payment"> · Pago {{ o.payment.method }} ({{ o.payment.status }})</span>
            <div *ngIf="o.receipt_number" class="receipt-line">Comprobante: <strong>{{ o.receipt_number }}</strong></div>
            <div *ngIf="o.shipping_address" class="receipt-line">Envío a: {{ o.shipping_address }}</div>
          </div>
          <div *ngIf="o.status === 'PENDIENTE'" style="margin-top:.6rem;">
            <div class="form-row" style="gap:.4rem;">
              <select class="form-control" style="flex:1;" [ngModel]="payForm(o).method" (ngModelChange)="setPayMethod(o, $event)">
                <option value="TARJETA">Tarjeta</option>
                <option value="EFECTIVO">Efectivo</option>
                <option value="TRANSFERENCIA">Transferencia</option>
              </select>
              <input class="form-control" style="flex:2;" *ngIf="payForm(o).method === 'TARJETA'"
                [(ngModel)]="payForm(o).card" placeholder="Número de tarjeta…" maxlength="19">
              <button class="btn btn-accent btn-sm" (click)="pay(o)" [disabled]="paying === o.id">
                <span *ngIf="paying === o.id" class="spinner"></span> Pagar
              </button>
            </div>
          </div>
          <div class="order-items">
            <div class="order-item-row" *ngFor="let it of o.items">
              <img [src]="it.image_url || fallbackImg" width="36" height="46" style="object-fit:cover; border-radius:6px;" (error)="imgErr($event)">
              <span>{{ it.product_name }} <em style="color:var(--muted);">{{ it.size_name }} / {{ it.color_name }}</em></span>
              <span class="qty">×{{ it.quantity }}</span>
              <span class="amt">Bs. {{ it.subtotal | number: '1.2-2' }}</span>
            </div>
          </div>
          <div class="order-total">Total: <strong>Bs. {{ o.total | number: '1.2-2' }}</strong></div>
        </div>
      </div>
    </div>
  </ng-container>

  <ng-template #loading>
    <div class="text-center" style="padding: 3rem; color: var(--muted);">
      <p *ngIf="!errorMsg">Cargando tu perfil…</p>
      <p *ngIf="errorMsg" style="color: var(--danger);">{{ errorMsg }}</p>
    </div>
  </ng-template>
  `,
  styles: [`
    .receipt-line { margin-top: .25rem; font-size: .85rem; color: var(--muted); }
  `],
})
export class ProfileComponent implements OnInit {
  user: User | null = null;
  edit = { first_name: '', last_name: '', email: '', phone: '' };
  pwd = { new_password: '', confirm: '' };
  saving = false;
  changingPwd = false;
  errorMsg = '';
  orders: Order[] = [];
  ordersLoading = false;
  paying: number | null = null;
  payCache = new Map<number, { method: string; card: string }>();
  fallbackImg =
    'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&q=80&w=400';
  readonly ORDER_EMOJI = ORDER_EMOJI;

  constructor(private api: ApiService, private toast: ToastService) {}

  ngOnInit(): void {
    this.api.getProfile().subscribe({
      next: (u) => {
        this.user = u;
        this.edit = {
          first_name: u.first_name,
          last_name: u.last_name,
          email: u.email,
          phone: u.phone || '',
        };
      },
      error: () => {
        this.errorMsg = 'No se pudo cargar el perfil. Vuelve a iniciar sesión.';
      },
    });
    this.loadOrders();
  }

  loadOrders(): void {
    this.ordersLoading = true;
    this.api.getOrders().subscribe({
      next: (r) => {
        this.orders = r;
        this.ordersLoading = false;
      },
      error: () => (this.ordersLoading = false),
    });
  }

  get initials(): string {
    if (!this.user) return '';
    const a = this.user.first_name?.charAt(0) || '';
    const b = this.user.last_name?.charAt(0) || '';
    return (a + b).toUpperCase();
  }

  get validProfile(): boolean {
    return !!(this.edit.first_name.trim() && this.edit.last_name.trim() && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.edit.email));
  }

  get validPassword(): boolean {
    return this.pwd.new_password.length >= 6 && this.pwd.new_password === this.pwd.confirm;
  }

  save(): void {
    if (!this.validProfile) return;
    this.saving = true;
    this.api
      .updateProfileFull({
        first_name: this.edit.first_name.trim(),
        last_name: this.edit.last_name.trim(),
        email: this.edit.email.trim(),
        phone: this.edit.phone.trim() || undefined,
      })
      .subscribe({
        next: () => {
          this.saving = false;
          this.toast.success('Perfil actualizado.');
        },
        error: () => (this.saving = false),
      });
  }

  changePassword(): void {
    if (!this.validPassword) return;
    this.changingPwd = true;
    this.api
      .updateProfileFull({ password: this.pwd.new_password })
      .subscribe({
        next: () => {
          this.changingPwd = false;
          this.pwd = { new_password: '', confirm: '' };
          this.toast.success('Contraseña actualizada.');
        },
        error: () => (this.changingPwd = false),
      });
  }

  imgErr(e: Event): void {
    (e.target as HTMLImageElement).src = this.fallbackImg;
  }

  payForm(o: Order): { method: string; card: string } {
    if (!this.payCache.has(o.id)) {
      this.payCache.set(o.id, { method: 'TARJETA', card: '' });
    }
    return this.payCache.get(o.id)!;
  }

  setPayMethod(o: Order, m: string): void {
    this.payForm(o).method = m;
  }

  pay(o: Order): void {
    const f = this.payForm(o);
    this.paying = o.id;
    this.api
      .payOrder(o.id, {
        payment_method: f.method,
        card_number: f.method === 'TARJETA' ? f.card.trim() || null : null,
      })
      .subscribe({
        next: (updated) => {
          this.paying = null;
          this.payCache.delete(o.id);
          this.loadOrders();
          this.toast.success(updated.status === 'PAGADO' ? 'Pago registrado.' : 'Pago no confirmado.');
        },
        error: () => (this.paying = null),
      });
  }
}