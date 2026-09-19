import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { ApiService, CartItem, CartSummary, Order } from './api.service';

const FALLBACK_IMG =
  'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&q=80&w=300';

@Component({
  selector: 'app-cart',
  standalone: true,
  imports: [FormsModule, CommonModule],
  template: `
  <div class="page-head">
    <span class="eyebrow">Tu selección</span>
    <h1>Tu carrito</h1>
    <p class="lead">Revisa tus prendas, ajusta cantidades y finaliza tu compra. (CU16)</p>
  </div>

  <div *ngIf="loading" class="empty-state"><span class="spinner"></span> Cargando carrito…</div>

  <div *ngIf="!loading && cart && !cart.items.length" class="empty-state">
    <div class="empty-icon">🛍</div>
    <h3>Tu carrito está vacío</h3>
    <p>Explora el catálogo y agrega prendas que te gusten.</p>
    <a routerLink="/" class="btn btn-accent mt-2" style="display:inline-flex;">Ir al catálogo</a>
  </div>

  <div *ngIf="cart && cart.items.length" style="display:grid; grid-template-columns: 1fr 320px; gap: 1.5rem; align-items:start;" class="cart-layout">
    <div class="table-wrap card" style="padding: 0;">
      <table class="table">
        <thead>
          <tr>
            <th>Producto</th>
            <th>Precio unit.</th>
            <th>Descuento</th>
            <th>Cantidad</th>
            <th>Subtotal</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr *ngFor="let item of cart.items">
            <td>
              <div style="display:flex; align-items:center; gap:.75rem;">
                <img [src]="item.image_url || fallbackImg" alt="" style="width:40px; height:52px; object-fit:cover; border-radius:6px;">
                <div>
                  <strong>{{ item.product_name }}</strong>
                  <div style="font-size:.8rem; color:var(--muted);">
                    {{ item.size_name }} <span>·</span> {{ item.color_name }} <span>·</span> SKU {{ item.sku }}
                  </div>
                </div>
              </div>
            </td>
            <td>Bs. {{ item.unit_price | number: '1.2-2' }}</td>
            <td>
              <span *ngIf="item.discount" style="color:#27ae60; font-weight:600;">
                −Bs. {{ item.discount | number: '1.2-2' }}
              </span>
              <span *ngIf="!item.discount" style="color:var(--muted);">—</span>
            </td>
            <td>
              <div style="display:flex; align-items:center; gap:.4rem;">
                <button class="btn btn-outline btn-sm" (click)="changeQty(item, item.quantity - 1)">−</button>
                <span style="min-width:2rem; text-align:center; font-weight:600;">{{ item.quantity }}</span>
                <button class="btn btn-outline btn-sm" (click)="changeQty(item, item.quantity + 1)">+</button>
              </div>
            </td>
            <td style="font-weight:700; color:var(--accent-dark);">Bs. {{ item.subtotal | number: '1.2-2' }}</td>
            <td><button class="btn btn-danger btn-sm" (click)="remove(item)">&times;</button></td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="card">
      <h3 style="margin-bottom: 1rem;">Resumen</h3>
      <div style="display:flex; justify-content:space-between; margin-bottom:.5rem;">
        <span style="color:var(--muted);">Prendas</span><strong>{{ cart.total_items }}</strong>
      </div>
      <div style="display:flex; justify-content:space-between; margin-bottom:.5rem;">
        <span style="color:var(--muted);">Subtotal</span><span>Bs. {{ (cart.total_amount + (cart.total_discount || 0)) | number: '1.2-2' }}</span>
      </div>
      <div *ngIf="cart.total_discount" style="display:flex; justify-content:space-between; margin-bottom:.5rem; color:#27ae60;">
        <span>Descuento (promociones)</span><strong>−Bs. {{ cart.total_discount | number: '1.2-2' }}</strong>
      </div>
      <div style="display:flex; justify-content:space-between; margin-bottom:1.25rem;">
        <span style="color:var(--muted);">Total</span><strong>Bs. {{ cart.total_amount | number: '1.2-2' }}</strong>
      </div>

      <div class="form-group" style="margin-bottom: .75rem;">
        <label class="form-label">Método de pago</label>
        <select class="form-control" [(ngModel)]="paymentMethod">
          <option value="TARJETA">Tarjeta</option>
          <option value="TRANSFERENCIA">Transferencia</option>
          <option value="EFECTIVO">Efectivo</option>
        </select>
      </div>

      <div class="form-group" *ngIf="paymentMethod === 'TARJETA'" style="margin-bottom: .75rem;">
        <label class="form-label">Número de tarjeta (CU19)</label>
        <input class="form-control" [(ngModel)]="cardNumber" placeholder="4000000000000002 (rechazo de prueba…)" maxlength="19">
        <div class="form-hint">Sandbox: cualquier tarjeta válida se aprueba; <code>4000000000000002</code> / <code>4000000000009995</code> se rechazan.</div>
      </div>

      <div class="form-group" style="margin-bottom: .75rem;">
        <label class="form-label">Dirección de entrega (CU17)</label>
        <input class="form-control" [(ngModel)]="shippingAddress" placeholder="Calle, n.º, zona, ciudad…" maxlength="255">
        <div class="form-hint">La enviamos a la dirección que nos indiques.</div>
      </div>

      <div class="form-group" style="margin-bottom: 1.25rem;">
        <label class="form-label">Sucursal para retiro / envío (opcional)</label>
        <select class="form-control" [(ngModel)]="branchId">
          <option [ngValue]="null">Sin sucursal (envío digital)</option>
          <option *ngFor="let b of branches" [ngValue]="b.id">{{ b.name }} — {{ b.city }}</option>
        </select>
      </div>

      <div class="alert alert-danger" *ngIf="errorMsg">{{ errorMsg }}</div>

      <button class="btn btn-primary btn-block" (click)="checkout()" [disabled]="checkingOut">
        <span *ngIf="checkingOut" class="spinner"></span>
        {{ checkingOut ? 'Procesando…' : 'Confirmar y pagar' }}
      </button>
      <button class="btn btn-ghost btn-block" (click)="clear()" style="margin-top:.5rem;">Vaciar carrito</button>
    </div>
  </div>

  <!-- Confirmación de pedido -->
  <div class="modal-backdrop" *ngIf="confirmed" (click.self)="confirmed = null">
    <div class="modal">
      <div class="modal-head">
        <h3>{{ confirmed.status === 'CANCELADO' ? 'Pago rechazado' : '¡Pedido pagado!' }}</h3>
        <button class="modal-close" (click)="confirmed = null">&times;</button>
      </div>
      <div class="modal-body">
        <div class="badge" *ngIf="confirmed"
          [class.badge-danger]="confirmed.status === 'CANCELADO'"
          [class.badge-success]="confirmed.status === 'PAGADO'"
          [class.badge-warning]="confirmed.status === 'PENDIENTE'">
          {{ confirmed.status === 'CANCELADO' ? 'Pago ' + (confirmed.payment?.status) : 'Pago ' + (confirmed.payment?.status) }}
        </div>
        <h2 style="margin:.75rem 0 .5rem;">Pedido #{{ confirmed.id }}</h2>
        <p *ngIf="confirmed.receipt_number" style="font-size:.9rem; color:var(--muted);">
          Comprobante: <strong>{{ confirmed.receipt_number }}</strong>
        </p>
        <p *ngIf="confirmed.shipping_address" style="font-size:.9rem; color:var(--muted);">
          Envío a: {{ confirmed.shipping_address }}
        </p>
        <p>Total: <strong>Bs. {{ confirmed.total | number: '1.2-2' }}</strong> vía {{ confirmed.payment?.method }}.</p>

        <ng-container *ngIf="confirmed.status === 'CANCELADO'">
          <p>La pasarela rechazó el pago, así que el pedido se canceló sin descuento de stock ni cobro.</p>
          <p style="margin-top:.5rem;">Verifica tu tarjeta y vuelve a intentar la compra.</p>
        </ng-container>
        <ng-container *ngIf="confirmed.status !== 'CANCELADO'">
          <p style="margin-top:.5rem;">Recibirás una notificación con el estado de tu pedido. ¡Gracias por tu compra!</p>
        </ng-container>
      </div>
      <div class="modal-foot">
        <button class="btn btn-accent" routerLink="/profile">Ver mis pedidos</button>
        <button class="btn btn-outline" (click)="confirmed = null">Seguir comprando</button>
      </div>
    </div>
  </div>
  `,
  styles: [`
    .alert-danger {
      background: rgba(220,53,69,.08);
      border: 1px solid rgba(220,53,69,.35);
      color: #c0392b;
      padding: .7rem .9rem;
      border-radius: 10px;
      font-size: .85rem;
      margin-bottom: .9rem;
    }
    .form-hint { font-size:.78rem; color:var(--muted); margin-top:.3rem; }
    @media (max-width: 900px) {
      .cart-layout { grid-template-columns: 1fr !important; }
    }
  `],
})
export class CartComponent implements OnInit {
  cart: CartSummary | null = null;
  branches: { id: number; name: string; city: string }[] = [];
  loading = true;
  checkingOut = false;
  paymentMethod = 'TARJETA';
  branchId: number | null = null;
  shippingAddress = '';
  cardNumber = '';
  errorMsg = '';
  confirmed: Order | null = null;
  fallbackImg = FALLBACK_IMG;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getBranches().subscribe((bs) => (this.branches = bs));
    this.load();
  }

  load(): void {
    this.loading = true;
    this.api.getCart().subscribe({
      next: (cart) => {
        this.cart = cart;
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  changeQty(item: CartItem, qty: number): void {
    if (qty < 1) return;
    this.api.updateCartItem(item.id, qty).subscribe((cart) => (this.cart = cart));
  }

  remove(item: CartItem): void {
    this.api.removeCartItem(item.id).subscribe((cart) => (this.cart = cart));
  }

  clear(): void {
    this.api.clearCart().subscribe((cart) => (this.cart = cart));
  }

  checkout(): void {
    this.checkingOut = true;
    this.errorMsg = '';
    this.api
      .checkout({
        order_type: 'DIGITAL',
        branch_id: this.branchId,
        payment_method: this.paymentMethod,
        shipping_address: this.shippingAddress.trim() || null,
        card_number: this.paymentMethod === 'TARJETA' ? this.cardNumber.trim() || null : null,
      })
      .subscribe({
        next: (order) => {
          this.checkingOut = false;
          this.confirmed = order;
          this.load();
        },
        error: (err: unknown) => {
          this.checkingOut = false;
          const detail = (err as { error?: { detail?: string } })?.error?.detail as string | undefined;
          this.errorMsg =
            typeof detail === 'string'
              ? detail
              : 'No se pudo procesar el pedido. Verifica los datos e inténtalo nuevamente.';
        },
      });
  }
}