import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from './api.service';

interface AuditRow {
  id: number; actor_name: string; actor_role: string; action: string; entity: string;
  entity_id: string; description: string; created_at: string;
  changes: Record<string, { antes: unknown; despues: unknown }>;
}

@Component({
  selector: 'app-audit', standalone: true, imports: [CommonModule, FormsModule],
  template: `
    <div class="page-head"><span class="eyebrow">Trazabilidad de operaciones</span><h1>Bitácora</h1>
    <p class="lead">Consulta quién realizó cada cambio y los valores anteriores y posteriores.</p></div>
    <form class="card filters" (ngSubmit)="search()">
      <label>Buscar<input class="form-control" name="query" [(ngModel)]="query" placeholder="Usuario o entidad"></label>
      <label>Acción<select class="form-control" name="action" [(ngModel)]="action"><option value="">Todas</option><option>CREAR</option><option>ACTUALIZAR</option><option>ELIMINAR</option><option>ACCESO</option></select></label>
      <label>Desde<input class="form-control" name="from" type="date" [(ngModel)]="from"></label>
      <label>Hasta<input class="form-control" name="to" type="date" [(ngModel)]="to"></label>
      <button class="btn btn-primary" [disabled]="loading">{{ loading ? 'Consultando…' : 'Consultar' }}</button>
    </form>
    <p role="alert" *ngIf="error">{{ error }}</p>
    <div class="card" style="overflow:auto">
      <p>{{ total }} registros · Página {{ page }} de {{ pages }}</p>
      <table class="table"><thead><tr><th>Fecha</th><th>Usuario</th><th>Acción</th><th>Registro</th><th>Cambios</th></tr></thead>
      <tbody><tr *ngFor="let row of rows"><td>{{ row.created_at | date:'dd/MM/yyyy HH:mm:ss' }}</td><td>{{ row.actor_name }}<small>{{ row.actor_role }}</small></td><td><span class="badge">{{ row.action }}</span></td><td>{{ label(row.entity) }} #{{ row.entity_id }}</td>
      <td><details *ngIf="fields(row).length"><summary>Ver detalle</summary><table class="table"><thead><tr><th>Campo</th><th>Antes</th><th>Después</th></tr></thead><tbody><tr *ngFor="let field of fields(row)"><td>{{ field }}</td><td>{{ display(row.changes[field].antes) }}</td><td>{{ display(row.changes[field].despues) }}</td></tr></tbody></table></details><span *ngIf="!fields(row).length">{{ row.description }}</span></td></tr>
      <tr *ngIf="!loading && !rows.length"><td colspan="5">No hay registros para estos filtros.</td></tr></tbody></table>
      <div class="pagination"><button class="btn btn-outline" (click)="load(page - 1)" [disabled]="page <= 1 || loading">Anterior</button><button class="btn btn-outline" (click)="load(page + 1)" [disabled]="page >= pages || loading">Siguiente</button></div>
    </div>`,
  styles: [`.filters{display:flex;gap:1rem;align-items:end;flex-wrap:wrap;margin-bottom:1rem}.filters label{flex:1;min-width:130px}small{display:block;color:var(--muted)}details{min-width:150px}details table{font-size:.8rem}td{vertical-align:top;max-width:350px;overflow-wrap:anywhere}.pagination{display:flex;justify-content:end;gap:.5rem}`]
})
export class AuditComponent implements OnInit {
  rows: AuditRow[] = []; query = ''; action = ''; from = ''; to = '';
  page = 1; total = 0; loading = false; error = '';
  get pages(): number { return Math.max(1, Math.ceil(this.total / 25)); }
  constructor(private api: ApiService) {}
  ngOnInit(): void { this.load(1); }
  search(): void { this.load(1); }
  load(page: number): void {
    if (this.loading) return;
    if (this.from && this.to && this.from > this.to) { this.error = 'Revisa el rango de fechas.'; return; }
    this.loading = true; this.error = '';
    const params: Record<string, string | number> = { page, page_size: 25, q: this.query, action: this.action };
    if (this.from) params['desde'] = new Date(this.from + 'T00:00:00').toISOString();
    if (this.to) params['hasta'] = new Date(this.to + 'T23:59:59.999').toISOString();
    this.api.getAudit(params).subscribe({ next: data => { this.rows = data.items; this.total = data.total; this.page = data.page; this.loading = false; },
      error: err => { this.loading = false; this.error = typeof err.error?.detail === 'string' ? err.error.detail : 'No se pudo consultar la bitácora.'; } });
  }
  fields(row: AuditRow): string[] { return Object.keys(row.changes); }
  display(value: unknown): string { return value == null ? '—' : typeof value === 'object' ? JSON.stringify(value) : String(value); }
  label(entity: string): string { return ({inventory:'Inventario',inventory_movements:'Movimiento',orders:'Venta / pedido',payments:'Pago',order_items:'Detalle de venta',users:'Usuario',products:'Producto',product_variants:'Variante',reservations:'Reserva',branches:'Sucursal'} as Record<string,string>)[entity] ?? entity; }
}
