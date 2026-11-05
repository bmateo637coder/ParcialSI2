import { Component, OnInit } from '@angular/core';
import { SyncOfflineService } from './core/offline/sync-offline.service';
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
    <p class="lead">Selecciona una sucursal, revisa los artículos y confirma el cobro.</p>
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
        <select class="form-control" [(ngModel)]="branchId" (ngModelChange)="changeBranch()" [disabled]="paying">
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

      <div class="form-group" *ngIf="paymentMethod === 'EFECTIVO'">
        <label class="form-label" for="cash-received">Efectivo recibido (Bs.)</label>
        <input id="cash-received" class="form-control" type="number" min="0" step="0.01" [(ngModel)]="cashReceived" [disabled]="paying" placeholder="Importe entregado por el cliente">
        <p>Cambio: <strong>Bs. {{ change | number:'1.2-2' }}</strong></p>
      </div>
      <p class="form-hint">Tarjetas y transferencias funcionan en modo de simulación.</p>
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
        <h3>{{ result.status === 'PAGADO' ? '¡Venta registrada!' : result.status === 'PENDIENTE' ? 'Pago pendiente' : 'Compra cancelada' }}</h3>
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
        <table class="table"><tbody><tr *ngFor="let item of result.items"><td>{{ item.product_name }} · {{ item.size_name }} / {{ item.color_name }} × {{ item.quantity }}</td><td>Bs. {{ item.subtotal | number:'1.2-2' }}</td></tr></tbody></table>
        <p *ngIf="result.payment?.method === 'EFECTIVO' && result.status === 'PAGADO'">Recibido: Bs. {{ result.payment?.cash_received | number:'1.2-2' }} · Cambio: <strong>Bs. {{ result.payment?.change_amount | number:'1.2-2' }}</strong></p>

        <p *ngIf="result.refunded_total">Se registró un reembolso de Bs. {{ result.refunded_total | number:'1.2-2' }} porque la compra no pudo completarse.</p>
        <p *ngIf="result.refund_pending">Hay Bs. {{ result.refund_pending | number:'1.2-2' }} pendientes de devolver. El encargado puede reintentar la operación desde Reembolsos.</p>
        <ng-container *ngIf="result.status === 'PENDIENTE'">
          <p style="margin-top:.5rem;">La tarjeta fue rechazada. Puedes completar el pago con efectivo o esperar al cliente.</p>
          <label class="form-label">Efectivo recibido (Bs.)</label>
          <input class="form-control" type="number" min="0" step="0.01" [(ngModel)]="pendingCash" [disabled]="paying">
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
  cashReceived: number | null = null;
  pendingCash: number | null = null;
  private requestId = '';
  private requestContent = '';
  private availabilityRequest = 0;
  private get retryKey(): string { return 'pos-pending-' + (this.api.currentUser.value?.id ?? 'none'); }

  get change(): number { return Math.max(0, Math.round(((this.cashReceived ?? 0) - this.total) * 100) / 100); }

  changeBranch(): void {
    this.lines = []; this.selectedAv = null; this.cashReceived = null;
    this.errorMsg = ''; this.loadAvailability();
  }

  constructor(private api: ApiService, private toast: ToastService, private offline: SyncOfflineService) {}

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
    const request = ++this.availabilityRequest;
    this.selectedAv = null;
    this.available = [];
    if (!this.branchId) {
      this.available = [];
      return;
    }
    this.loadingAv = true;
    this.api.getAvailability({ branch_id: this.branchId }).subscribe({
      next: (res) => {
        if (request !== this.availabilityRequest) return;
        this.available = res;
        this.loadingAv = false;
      },
      error: () => { if (request === this.availabilityRequest) { this.loadingAv = false; this.errorMsg = 'No se pudieron actualizar las existencias.'; } },
    });
  }

  addLine(): void {
    if (!this.selectedAv || this.paying) return;
    const qty = Number(this.addQty);
    if (!Number.isInteger(qty) || qty < 1) { this.toast.info('Ingresa una cantidad entera mayor que cero.'); return; }
    const existing = this.lines.find((l) => l.av.variant_id === this.selectedAv!.variant_id);
    if (qty + (existing?.quantity ?? 0) > this.selectedAv.available) {
      this.toast.info(`Solo hay ${this.selectedAv.available} disponibles.`);
      return;
    }
    if (existing) {
      existing.quantity += qty;
    } else {
      this.lines.push({ av: this.selectedAv, quantity: qty });
    }
    this.selectedAv = null;
    this.addQty = 1;
  }

  removeLine(line: PosLine): void {
    if (this.paying) return;
    this.lines = this.lines.filter((l) => l !== line);
  }

  lineSubtotal(line: PosLine): number {
    return Math.round((line.av.price || 0) * 100) * line.quantity / 100;
  }

  get total(): number {
    return this.lines.reduce((sum, l) => sum + Math.round(this.lineSubtotal(l) * 100), 0) / 100;
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

  async submit(): Promise<void> {
    if (this.paying || !this.branchId || !this.lines.length) return;
    this.errorMsg = '';
    if (this.paymentMethod === 'EFECTIVO' && (this.cashReceived == null || !Number.isFinite(this.cashReceived) || Math.round(this.cashReceived * 100) < Math.round(this.total * 100))) {
      this.errorMsg = 'El efectivo recibido debe cubrir el total de la venta.'; return;
    }
    this.paying = true;
    if (!navigator.onLine && this.paymentMethod === 'EFECTIVO' && this.api.currentUser.value?.empresa_id) {
      try {
        await this.offline.registrarVentaOffline({
          sucursalId: this.branchId,
          clienteId: this.clientId ?? undefined,
          items: this.lines.map(l => ({ variant_id: l.av.variant_id, quantity: l.quantity, precio: l.av.price, nombre: l.av.product_name })),
          total: this.total,
        });
        this.lines = [];
        this.cashReceived = null;
        this.toast.success('Efectivo registrado en este dispositivo. La venta queda sujeta a confirmación.');
        this.loadAvailability();
      } catch (error) {
        this.errorMsg = error instanceof Error ? error.message : 'No se pudo confirmar. Revisa Sincronización antes de repetir la venta.';
      } finally { this.paying = false; }
      return;
    }
    if (!navigator.onLine) {
      this.errorMsg = 'Sin conexión solo se pueden registrar ventas en efectivo de una empresa.';
      this.paying = false;
      return;
    }
    const sale = {
        branch_id: this.branchId,
        items: this.lines.map((l) => ({ variant_id: l.av.variant_id, quantity: l.quantity })),
        client_id: this.clientId,
        payment_method: this.paymentMethod,
        card_number: this.paymentMethod === 'TARJETA' ? this.cardNumber.trim() || null : null,
        cash_received: this.paymentMethod === 'EFECTIVO' ? this.cashReceived : null,
    };
    const content = JSON.stringify({ ...sale, card_number: null });
    if (content !== this.requestContent || !this.requestId) {
      let previous: {content?:string;id?:string} = {};
      try { previous = JSON.parse(sessionStorage.getItem(this.retryKey) || '{}'); } catch {}
      this.requestContent = content; this.requestId = previous.content === content && previous.id ? previous.id : crypto.randomUUID();
      try { sessionStorage.setItem(this.retryKey,JSON.stringify({content,id:this.requestId})); } catch {}
    }
    this.api.posSale({ ...sale, request_id: this.requestId })
      .subscribe({
        next: (order) => {
          this.paying = false;
          this.result = order;
          this.pendingCash = null;
          this.requestId = ''; this.requestContent = ''; this.cashReceived = null;
          try { sessionStorage.removeItem(this.retryKey); } catch {}
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
    if (!this.result || this.paying) return;
    if (this.pendingCash == null || !Number.isFinite(this.pendingCash) || Math.round(this.pendingCash * 100) < Math.round(this.result.total * 100)) {
      this.toast.info('El efectivo recibido debe cubrir el total pendiente.'); return;
    }
    this.paying = true;
    this.api.payOrder(this.result.id, { payment_method: 'EFECTIVO', cash_received: this.pendingCash }).subscribe({
      next: (updated) => {
        this.paying = false;
        this.loadAvailability();
        this.toast.success(updated.status === 'PAGADO' ? 'Pago completado con efectivo.' : 'Pago no confirmado.');
        this.result = updated;
      },
      error: (err) => { this.paying = false; this.toast.info(typeof err.error?.detail === 'string' ? err.error.detail : 'No se pudo completar el pago. Revisa el estado del pedido antes de reintentar.'); },
    });
  }
}
