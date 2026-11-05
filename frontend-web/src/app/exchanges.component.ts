import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { environment } from '../environments/environment';

@Component({
  selector: 'app-exchanges', standalone: true, imports: [CommonModule, FormsModule],
  template: `
    <div class="page-head"><h1>Cambios de prendas</h1><p>Selecciona la compra original y la prenda de reemplazo disponible en su sucursal.</p></div>
    <p role="alert" *ngIf="error">{{ error }}</p><p role="status" *ngIf="message">{{ message }}</p>
    <div class="card" style="padding:1.5rem;max-width:760px;margin:auto;display:grid;gap:1rem;">
      <label>Compra original<select class="form-control" [(ngModel)]="order" (ngModelChange)="selectOrder()">
        <option [ngValue]="null">Selecciona una compra</option><option *ngFor="let o of orders" [ngValue]="o">{{ o.receipt_number }} · {{ o.client_name }} · {{ o.created_at | date:'dd/MM/yyyy' }} · {{ o.total | currency:'BOB' }}</option>
      </select></label>
      <label *ngIf="order">Prenda que devuelve el cliente<select class="form-control" [(ngModel)]="original">
        <option [ngValue]="null">Selecciona una prenda</option><option *ngFor="let i of order.items" [ngValue]="i">{{ i.product_name }} · {{ i.size_name }} / {{ i.color_name }} · {{ i.quantity }} unidades</option>
      </select></label>
      <label *ngIf="order">Prenda de reemplazo<select class="form-control" [(ngModel)]="replacement">
        <option [ngValue]="null">Selecciona una prenda</option><option *ngFor="let a of availability" [ngValue]="a">{{ a.product_name }} · {{ a.size_name }} / {{ a.color_name }} · {{ a.price | currency:'BOB' }} · {{ a.available }} disponibles</option>
      </select></label>
      <label>Cantidad<input class="form-control" type="number" min="1" [max]="original?.quantity || 1" [(ngModel)]="quantity"></label>
      <p *ngIf="original && replacement">Diferencia aproximada: {{ difference | currency:'BOB' }}. El servidor valida el precio final y las promociones vigentes.</p>
      <label>Efectivo por la diferencia<input class="form-control" type="number" step="0.01" [(ngModel)]="cash"></label>
      <p>Usa un monto positivo si recibes efectivo del cliente, o negativo si le devuelves efectivo.</p>
      <button class="btn btn-primary" [disabled]="busy || !original || !replacement || quantity < 1" (click)="submit()">Confirmar cambio y movimiento de efectivo</button>
      <div *ngFor="let e of history" class="card" style="padding:1rem;">Cambio #{{ e.id }} · {{ e.estado }} · {{ e.fecha_solicitud | date:'dd/MM/yyyy HH:mm' }} · Diferencia: {{ e.monto_diferencia | currency:'BOB' }}</div>
    </div>
  `
})
export class ExchangesComponent implements OnInit {
  private http = inject(HttpClient);
  orders: any[] = []; availability: any[] = []; history: any[] = [];
  order: any; original: any; replacement: any;
  quantity = 1; cash = 0; busy = false; error = ''; message = '';
  get difference() { return this.original && this.replacement ? Math.round((this.replacement.price - this.original.subtotal / this.original.quantity) * this.quantity * 100) / 100 : 0; }
  ngOnInit() { this.http.get<any[]>(`${environment.apiUrl}/orders`).subscribe({ next: orders => this.orders = orders.filter(o => ['PAGADO', 'ENVIADO', 'ENTREGADO'].includes(o.status)), error: e => this.error = e?.error?.detail || 'No se pudieron cargar las compras.' }); }
  selectOrder() {
    this.original = null; this.replacement = null; this.availability = []; this.history = []; this.error = ''; this.message = '';
    if (!this.order) return;
    this.http.get<any[]>(`${environment.apiUrl}/inventory/availability?branch_id=${this.order.branch_id}`).subscribe({ next: rows => this.availability = rows.filter(r => r.available > 0), error: e => this.error = e?.error?.detail || 'No se pudo cargar la disponibilidad.' });
    this.http.get<any[]>(`${environment.apiUrl}/orders/${this.order.id}/exchanges`).subscribe({ next: rows => this.history = rows, error: () => {} });
  }
  submit() {
    this.busy = true; this.error = '';
    this.http.post(`${environment.apiUrl}/orders/${this.order.id}/exchanges`, { order_item_id: this.original.id,
      replacement_variant_id: this.replacement.variant_id, quantity: this.quantity, cash_difference: this.cash }).subscribe({
      next: () => { this.busy = false; this.selectOrder(); this.message = 'Cambio registrado. Se actualizó el inventario de ambas prendas.'; },
      error: e => { this.busy = false; this.error = e?.error?.detail || 'No se pudo registrar el cambio.'; }
    });
  }
}
