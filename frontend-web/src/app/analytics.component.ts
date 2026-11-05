import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { environment } from '../environments/environment';

@Component({
  selector: 'app-analytics', standalone: true, imports: [CommonModule, FormsModule],
  template: `
    <div class="page-head"><h1>Analítica de la tienda</h1><p>Predicción de demanda y agrupación de prendas.</p></div>
    <p role="alert" *ngIf="error">{{ error }}</p>
    <button class="btn btn-primary" (click)="train()" [disabled]="busy">{{ busy ? 'Entrenando y evaluando…' : 'Entrenar modelos y actualizar análisis' }}</button>
    <div *ngIf="data" style="margin-top:1rem;">
      <div class="grid">
        <div class="card" style="padding:1rem;"><h3>Ventas del mes</h3><strong>{{ data.kpi.ventas_mes | currency:'BOB' }}</strong></div>
        <div class="card" style="padding:1rem;"><h3>Prendas vendidas</h3><strong>{{ data.kpi.productos_vendidos }}</strong></div>
        <div class="card" style="padding:1rem;"><h3>Compra promedio</h3><strong>{{ data.kpi.ticket_promedio | currency:'BOB' }}</strong></div>
      </div>
      <p *ngIf="!data.entrenado">Entrena los modelos para obtener estimaciones y grupos de productos.</p>
      <ng-container *ngIf="data.entrenado">
        <p>{{ data.advertencia }}</p>
        <div class="card" style="padding:1rem;margin:1rem 0;">
          <h2>Validación de los modelos</h2>
          <p>{{ data.metricas.muestras_entrenamiento }} muestras de entrenamiento y {{ data.metricas.muestras_validacion }} de validación.</p>
          <p>Error absoluto medio: <strong>{{ data.metricas.mae }}</strong> unidades · R²: <strong>{{ data.metricas.r2 }}</strong> · Silueta de los grupos: <strong>{{ data.metricas.silhouette }}</strong></p>
          <p>El error se mide sobre datos separados del entrenamiento. Una silueta más cercana a 1 indica grupos mejor separados.</p>
        </div>
        <div class="chart-filters">
          <label>Sucursal del análisis
            <select class="form-control" [(ngModel)]="branch" (ngModelChange)="selected = null" aria-label="Sucursal del análisis">
              <option value="">Todas las sucursales</option>
              <option *ngFor="let b of branches" [value]="b.id">{{ b.name }}</option>
            </select>
          </label>
          <label>Prendas en los gráficos
            <select class="form-control" [(ngModel)]="chartLimit" aria-label="Prendas en los gráficos">
              <option [ngValue]="10">10</option><option [ngValue]="25">25</option><option [ngValue]="50">50</option>
            </select>
          </label>
        </div>
        <p *ngIf="!predictions.length">No hay prendas para esta selección.</p>
        <figure class="chart-card" *ngIf="chartRows.length" aria-labelledby="demand-chart-title">
          <figcaption id="demand-chart-title"><h2>Existencias y demanda estimada</h2></figcaption>
          <p>Existencias actuales frente a unidades estimadas para un día. Elige una prenda para ver su detalle.</p>
          <div class="legend"><span><i class="stock-key"></i>Existencias</span><span><i class="demand-key"></i>Demanda diaria estimada</span></div>
          <div *ngFor="let p of chartRows" class="demand-row">
            <button class="chart-label" (click)="selected = p">{{ p.producto }} · {{ p.sucursal }} · {{ p.sku }}</button>
            <div role="img" [attr.aria-label]="p.sku + ': ' + p.stock + ' existencias y ' + p.demanda_diaria_estimada + ' unidades estimadas por día'">
              <div class="bar stock" [style.width.%]="barWidth(p.stock)"></div>
              <div class="bar demand" [style.width.%]="barWidth(p.demanda_diaria_estimada)"></div>
            </div>
            <small>{{ p.stock }} disponibles · {{ p.demanda_diaria_estimada }} estimadas/día</small>
          </div>
        </figure>
        <figure class="chart-card" *ngIf="chartRows.length" aria-labelledby="clusters-chart-title">
          <figcaption id="clusters-chart-title"><h2>Distribución de prendas por grupo</h2></figcaption>
          <p>Precio y existencias de las prendas analizadas. Cada color representa un grupo identificado por el modelo. Selecciona un punto para inspeccionarlo.</p>
          <svg viewBox="0 0 720 320" role="group" aria-labelledby="scatter-title" aria-describedby="scatter-desc">
            <title id="scatter-title">Grupos de prendas por precio y existencias</title>
            <desc id="scatter-desc">El eje horizontal representa el precio en bolivianos y el vertical las existencias. Los puntos se pueden seleccionar con el teclado.</desc>
            <line x1="60" y1="260" x2="680" y2="260" stroke="currentColor" />
            <line x1="60" y1="35" x2="60" y2="260" stroke="currentColor" />
            <text x="60" y="282" text-anchor="middle">0</text>
            <text x="680" y="282" text-anchor="middle">{{ maxPrice | number:'1.0-2' }}</text>
            <text x="48" y="40" text-anchor="end">{{ maxStock }}</text>
            <text x="370" y="310" text-anchor="middle">Precio (Bs.)</text>
            <text transform="translate(18 155) rotate(-90)" text-anchor="middle">Existencias</text>
            <circle *ngFor="let p of chartRows" [attr.cx]="60 + 620 * p.precio / maxPrice"
              [attr.cy]="260 - 220 * p.stock / maxStock" r="7" [attr.fill]="groupColor(p.grupo)"
              stroke="white" stroke-width="2" tabindex="0" role="button"
              [attr.aria-label]="p.sku + ', grupo ' + p.grupo + ', precio ' + p.precio + ', existencias ' + p.stock"
              (click)="selected = p" (keydown.enter)="selected = p" (keydown.space)="$event.preventDefault(); selected = p">
              <title>{{ p.producto }} · {{ p.sucursal }} · {{ p.sku }} · Grupo {{ p.grupo }}</title>
            </circle>
          </svg>
          <div class="legend"><span *ngFor="let g of data.segmentacion"><i [style.background]="groupColor(g.grupo)"></i>Grupo {{ g.grupo }}</span></div>
        </figure>
        <aside *ngIf="selected" class="chart-card" aria-live="polite">
          <h3>{{ selected.producto }} · {{ selected.sku }}</h3>
          <p>{{ selected.sucursal }} · Grupo {{ selected.grupo }} · Bs. {{ selected.precio | number:'1.2-2' }}</p>
          <p>{{ selected.stock }} unidades disponibles y {{ selected.demanda_diaria_estimada }} unidades estimadas para un día.</p>
          <button class="btn btn-outline" (click)="selected = null">Cerrar detalle</button>
        </aside>
        <h2>Demanda estimada por día</h2>
        <div style="overflow-x:auto;"><table style="width:100%;">
          <thead><tr><th>Prenda</th><th>Sucursal</th><th>SKU</th><th>Existencias</th><th>Estimación</th><th>Grupo</th></tr></thead>
          <tbody><tr *ngFor="let p of predictions"><td>{{ p.producto }}</td><td>{{ p.sucursal }}</td><td>{{ p.sku }}</td><td>{{ p.stock }}</td><td>{{ p.demanda_diaria_estimada }}</td><td>{{ p.grupo }}</td></tr></tbody>
        </table></div>
        <h2 style="margin-top:1rem;">Grupos de prendas</h2>
        <div class="grid"><div class="card" style="padding:1rem;" *ngFor="let g of data.segmentacion"><h3>Grupo {{ g.grupo }}</h3><p>{{ g.variantes }} variantes.</p><p>Precio medio de referencia: {{ g.perfil.precio | number:'1.0-2' }} · Stock de referencia: {{ g.perfil.stock | number:'1.0-0' }}</p></div></div>
        <h2>Recomendaciones de reposición</h2><p *ngIf="!data.recomendaciones.length">No se detectaron necesidades de reposición con este modelo.</p>
        <p *ngFor="let r of data.recomendaciones">{{ r.sucursal }} · {{ r.sku }}: {{ r.mensaje }}</p>
        <h2>Prendas con características atípicas</h2><p *ngFor="let a of data.anomalias">{{ a.sucursal }} · {{ a.sku }} (distancia al grupo: {{ a.distancia }})</p>
      </ng-container>
    </div>
  `,
  styles: [`
    .chart-card { margin:1.5rem 0; padding:1rem; border:1px solid var(--line); border-radius:12px; }
    .chart-card svg { width:100%; max-height:420px; }
    .chart-card text { fill:currentColor; font-size:12px; }
    .chart-filters,.legend { display:flex; gap:1.5rem; flex-wrap:wrap; margin:1rem 0; }
    .legend span { display:flex; align-items:center; gap:.4rem; }
    .legend i { width:14px; height:14px; border-radius:3px; display:inline-block; }
    .stock-key,.stock { background:#315e91; } .demand-key,.demand { background:#ae4934; }
    .demand-row { margin:1rem 0; } .bar { height:12px; margin:4px 0; border-radius:3px; }
    .chart-label { background:none; border:0; color:inherit; cursor:pointer; text-align:left; padding:0; font:inherit; }
    circle { cursor:pointer; } circle:focus { outline:2px solid currentColor; }
  `]
})
export class AnalyticsComponent implements OnInit {
  private http = inject(HttpClient);
  data: any; busy = false; error = '';
  branch = ''; chartLimit = 10; selected: any = null;
  get predictions(): any[] { return (this.data?.prediccion_demanda ?? []).filter((p: any) => !this.branch || String(p.sucursal_id) === this.branch); }
  get chartRows(): any[] { return this.predictions.slice(0, this.chartLimit); }
  get branches(): {id: number; name: string}[] {
    return [...new Map<number, string>((this.data?.prediccion_demanda ?? []).map((p: any) => [p.sucursal_id, p.sucursal] as [number, string]))]
      .map(([id, name]) => ({ id, name }));
  }
  get maxPrice(): number { return Math.max(1, ...this.chartRows.map(p => p.precio)); }
  get maxStock(): number { return Math.max(1, ...this.chartRows.map(p => p.stock)); }
  barWidth(value: number): number { return 100 * value / Math.max(1, ...this.chartRows.flatMap(p => [p.stock, p.demanda_diaria_estimada])); }
  groupColor(group: number): string { return ['#315e91', '#ae4934', '#39836c'][(group - 1) % 3]; }
  ngOnInit() { this.load(); }
  load() {
    this.http.get(`${environment.apiUrl}/analitica/dashboard`).subscribe({ next: r => { this.data = r; this.selected = null; }, error: e => this.error = e?.error?.detail || 'No se pudo cargar el análisis.' });
  }
  train() {
    this.busy = true; this.error = '';
    this.http.post(`${environment.apiUrl}/analitica/entrenar`, {}).subscribe({ next: () => { this.busy = false; this.load(); }, error: e => { this.busy = false; this.error = e?.error?.detail || 'No se pudo entrenar.'; } });
  }
}
