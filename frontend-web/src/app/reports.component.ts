import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import {
  ApiService,
  Branch,
  CategoryItem,
  DashboardReport,
  SalesPoint,
  TopProductReport,
} from './api.service';

type PeriodKey = 'hoy' | '7dias' | '30dias' | 'mes' | 'custom';

declare global {
  interface Window {
    SpeechRecognition?: new () => SpeechRecognitionLike;
    webkitSpeechRecognition?: new () => SpeechRecognitionLike;
  }
}

export interface SpeechRecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((event: SpeechResultEventLike) => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
}

export interface SpeechResultEventLike {
  results?: ArrayLike<ArrayLike<{ transcript?: string }>>;
}

@Component({
  selector: 'app-reports',
  standalone: true,
  imports: [FormsModule, CommonModule],
  template: `
  <div class="page-head">
    <span class="eyebrow">CU24 · CU25</span>
    <h1>Reportes y dashboards</h1>
    <p class="lead">Ventas, inventario y reservas en un solo panel para la toma de decisiones.</p>
  </div>

  <!-- ============ FILTROS ============ -->
  <div class="card" style="margin-bottom: 1.5rem;">
    <div style="display:flex; flex-wrap:wrap; gap:1rem; align-items:flex-end;">
      <div>
        <label class="lbl">Periodo</label>
        <div style="display:flex; gap:.4rem; flex-wrap:wrap;">
          <button class="chip" [class.active]="period === 'hoy'" (click)="setPeriod('hoy')">Hoy</button>
          <button class="chip" [class.active]="period === '7dias'" (click)="setPeriod('7dias')">Últimos 7 días</button>
          <button class="chip" [class.active]="period === '30dias'" (click)="setPeriod('30dias')">Últimos 30 días</button>
          <button class="chip" [class.active]="period === 'mes'" (click)="setPeriod('mes')">Este mes</button>
          <button class="chip" [class.active]="period === 'custom'" (click)="setPeriod('custom')">Personalizado</button>
        </div>
        <div *ngIf="period === 'custom'" style="display:flex; gap:.5rem; margin-top:.5rem; flex-wrap:wrap;">
          <input type="date" [(ngModel)]="desde" class="form-control" style="max-width: 170px;" (change)="loadData()"/>
          <input type="date" [(ngModel)]="hasta" class="form-control" style="max-width: 170px;" (change)="loadData()"/>
        </div>
      </div>
      <div>
        <label class="lbl">Sucursal</label>
        <select class="form-control" [(ngModel)]="branchId" (change)="loadData()" style="min-width: 220px;">
          <option [ngValue]="null">Todas</option>
          <option *ngFor="let b of branches" [ngValue]="b.id">{{ b.name }}</option>
        </select>
      </div>
      <div>
        <label class="lbl">Categoría</label>
        <select class="form-control" [(ngModel)]="categoryId" (change)="loadData()" style="min-width: 220px;">
          <option [ngValue]="null">Todas</option>
          <option *ngFor="let c of categories" [ngValue]="c.id">{{ c.name }}</option>
        </select>
      </div>
      <button class="btn btn-accent" (click)="loadData()" [disabled]="loading">Actualizar</button>
      <button class="btn" (click)="downloadCsv()" [disabled]="!report || report.empty || loading" title="Exportar a CSV">
        ⤓ CSV
      </button>
      <button class="btn" (click)="printReport()" [disabled]="!report || report.empty || loading" title="Imprimir / guardar PDF">
        ⤓ PDF
      </button>
    </div>
  </div>

  <!-- ============ KPI ============ -->
  <div *ngIf="loading" class="empty-state"><span class="spinner"></span> Calculando indicadores…</div>

  <div *ngIf="!loading && report && !report.empty" class="kpi-grid">
    <div class="card kpi"><span class="kpi-label">Ventas del periodo</span>
      <span class="kpi-value">Bs. {{ report.kpis.total_sales | number: '1.2-2' }}</span>
      <span class="kpi-note">{{ report.kpis.total_orders }} pedido(s)</span></div>
    <div class="card kpi"><span class="kpi-label">Ticket promedio</span>
      <span class="kpi-value">Bs. {{ report.kpis.avg_order | number: '1.2-2' }}</span>
      <span class="kpi-note">por pedido</span></div>
    <div class="card kpi"><span class="kpi-label">Reservas</span>
      <span class="kpi-value">{{ report.kpis.reservations }}</span>
      <span class="kpi-note">en el periodo</span></div>
    <div class="card kpi"><span class="kpi-label">Unidades disponibles</span>
      <span class="kpi-value">{{ report.kpis.total_units_available }}</span>
      <span class="kpi-note">en inventario</span></div>
    <div class="card kpi" [class.kpi-warn]="report.kpis.low_stock_variants > 0">
      <span class="kpi-label">Con stock bajo</span>
      <span class="kpi-value">{{ report.kpis.low_stock_variants }}</span>
      <span class="kpi-note">≤ 5 unidades</span></div>
    <div class="card kpi"> <span class="kpi-label">Promociones activas</span>
      <span class="kpi-value">{{ report.kpis.active_promotions }}</span>
      <span class="kpi-note">en vigor</span></div>
    <div class="card kpi"> <span class="kpi-label">Descuento aplicado</span>
      <span class="kpi-value">Bs. {{ report.kpis.discount_amount | number: '1.2-2' }}</span>
      <span class="kpi-note">de promociones</span></div>
  </div>

  <!-- ============ NARRATIVA NLG / VOZ ============ -->
  <div *ngIf="!loading && report?.narrative" class="card narrative-card">
    <h3 style="margin-bottom:.5rem;">Resumen ejecutivo</h3>
    <p style="white-space:pre-line; color:var(--muted); line-height:1.6;">{{ report?.narrative }}</p>
  </div>

  <!-- ============ CUERPO ============ -->
  <div *ngIf="!loading && report" class="grid" style="align-items:stretch;">
    <div class="card" *ngIf="!report.empty && report.sales_series.length">
      <h3 style="margin-bottom:.5rem;">Ventas por día</h3>
      <div class="bart-chart">
        <div class="bar-col" *ngFor="let pt of report.sales_series" [title]="pt.date + ': Bs. ' + (pt.amount | number:'1.2-2') + ' (' + pt.orders + ' pedidos)'">
          <div class="bar" [style.height.%]="barHeight(pt)"><span class="bar-val">{{ pt.amount | number: '1.0-0' }}</span></div>
          <div class="bar-label">{{ pt.date.slice(5) }}</div>
        </div>
      </div>
    </div>

    <div class="card" *ngIf="!report.empty && report.by_category.length">
      <h3 style="margin-bottom:.5rem;">Ventas por categoría</h3>
      <table class="table">
        <thead><tr><th>Categoría</th><th class="tar">Unidades</th><th class="tar">Ventas</th></tr></thead>
        <tbody>
          <tr *ngFor="let c of report.by_category">
            <td>{{ c.category_name }}</td>
            <td class="tar">{{ c.units }}</td>
            <td class="tar">Bs. {{ c.sales | number: '1.2-2' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="card" *ngIf="!report.empty && report.top_products.length">
      <h3 style="margin-bottom:.5rem;">Productos más vendidos</h3>
      <table class="table">
        <thead><tr><th>Producto</th><th class="tar">Unid.</th><th class="tar">Ingresos</th></tr></thead>
        <tbody>
          <tr *ngFor="let tp of report.top_products">
            <td>{{ tp.name }}</td>
            <td class="tar">{{ tp.units }}</td>
            <td class="tar">Bs. {{ tp.revenue | number: '1.2-2' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  <div *ngIf="!loading && report && report.empty" class="empty-state">
    <div class="empty-icon">📊</div>
    <h3>Sin datos en el periodo</h3>
    <p>No hay ventas ni reservas en el rango seleccionado. Amplía el periodo o quita los filtros.</p>
  </div>

  <!-- ============ VOZ (CU24) ============ -->
  <div class="card voice-card">
    <h3 style="margin-bottom:.25rem;">Reporte por comando de voz <span class="badge badge-accent">CU24</span></h3>
    <p class="lead" style="margin-bottom:1rem;">
      Prueba con: <em>"generar reporte de ventas"</em>, <em>"inventario de la Sucursal ..."</em> o <em>"reservas de la semana"</em>.
    </p>
    <div style="display:flex; gap:.6rem; align-items:center; flex-wrap:wrap;">
      <button class="btn btn-accent" (click)="toggleListen()" [disabled]="listening || voiceBusy">
        <span *ngIf="listening" class="spinner spinner-inline"></span>
        {{ listening ? 'Escuchando…' : '🎤 Hablar' }}
      </button>
      <input class="form-control" [(ngModel)]="voiceText" placeholder="o escribe el comando aquí…"
             style="max-width: 360px;" (keyup.enter)="sendVoice()" [disabled]="voiceBusy"/>
      <button class="btn" (click)="sendVoice()" [disabled]="!voiceText.trim() || voiceBusy">Enviar</button>
    </div>
    <div *ngIf="voiceMessage" class="voice-result {{ voiceOk ? 'ok' : 'ko' }}">{{ voiceMessage }}</div>

    <div *ngIf="voiceOk && report && !report.empty" class="voice-preview">
      <strong style="display:block; margin-bottom:.5rem;">Vista previa</strong>
      <span class="preview-chip">Ventas: <b>Bs. {{ report.kpis.total_sales | number:'1.2-2' }}</b></span>
      <span class="preview-chip">Pedidos: <b>{{ report.kpis.total_orders }}</b></span>
      <span class="preview-chip">Ticket medio: <b>Bs. {{ report.kpis.avg_order | number:'1.2-2' }}</b></span>
      <span class="preview-chip">Reservas: <b>{{ report.kpis.reservations }}</b></span>
      <span class="preview-chip">Stock bajo: <b>{{ report.kpis.low_stock_variants }}</b></span>
      <span class="preview-chip">Promos activas: <b>{{ report.kpis.active_promotions }}</b></span>
      <div style="margin-top:.6rem; display:flex; gap:.5rem; flex-wrap:wrap;">
        <button class="btn btn-accent btn-sm" (click)="downloadCsv()">⤓ Descargar CSV</button>
        <button class="btn btn-accent btn-sm" (click)="printReport()">⤓ Descargar PDF</button>
        <button class="btn btn-outline btn-sm" (click)="sendVoice()" [disabled]="!voiceText.trim()">Repetir comando</button>
      </div>
    </div>
  </div>
  `,
  styles: [`
    .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
    .kpi { display: flex; flex-direction: column; gap: .15rem; margin: 0; }
    .kpi-label { font-size: .78rem; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); }
    .kpi-value { font-size: 1.5rem; font-weight: 800; color: var(--accent-dark); }
    .kpi-note { font-size: .8rem; color: var(--muted); }
    .kpi-warn { border-color: var(--danger); }
    .kpi-warn .kpi-value { color: var(--danger); }
    .bart-chart { display: flex; gap: .35rem; align-items: flex-end; height: 150px; padding-top: .5rem; }
    .bar-col { flex: 1; display: flex; flex-direction: column; justify-content: flex-end; height: 100%; min-width: 22px; }
    .bar { background: linear-gradient(180deg, var(--accent), var(--accent-dark)); border-radius: 6px 6px 0 0;
           min-height: 3px; position: relative; transition: height .3s ease; }
    .bar-val { position: absolute; top: -1.15rem; left: 0; right: 0; text-align: center; font-size: .68rem; color: var(--muted); }
    .bar-label { text-align: center; font-size: .68rem; color: var(--muted); margin-top: .3rem; }
    .table { width: 100%; border-collapse: collapse; font-size: .88rem; }
    .table th, .table td { padding: .45rem .35rem; border-bottom: 1px solid var(--border, rgba(0,0,0,.08)); }
    .table th { text-align: left; color: var(--muted); font-weight: 600; text-transform: uppercase; font-size: .72rem; }
    .table .tar, th.tar { text-align: right; }
    .lbl { display: block; font-size: .78rem; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); margin-bottom: .3rem; }
    .voice-card { margin-top: 1.5rem; border-left: 4px solid var(--accent); }
    .voice-result { margin-top: .8rem; padding: .6rem .9rem; border-radius: 8px; font-size: .9rem; }
    .voice-result.ok { background: rgba(76, 175, 80, .12); color: #2e7d32; }
    .voice-result.ko { background: rgba(244, 67, 54, .1); color: var(--danger); }
    .voice-preview { margin-top: .9rem; padding: .9rem 1rem; border: 1px solid rgba(230, 57, 70, .25);
      border-radius: 10px; background: rgba(230, 57, 70, .05); }
    .preview-chip { display: inline-block; margin: .15rem .35rem .15rem 0; padding: .28rem .65rem;
      background: #fff; border: 1px solid var(--line, rgba(0,0,0,.1)); border-radius: 999px; font-size: .82rem; }
    .spinner-inline { width: .8rem; height: .8rem; margin-right: .4rem; }
  `],
})
export class ReportsComponent implements OnInit {
  loading = true;
  report: DashboardReport | null = null;

  period: PeriodKey = '30dias';
  desde = '';
  hasta = '';
  branchId: number | null = null;
  categoryId: number | null = null;

  branches: Branch[] = [];
  categories: CategoryItem[] = [];

  listening = false;
  voiceBusy = false;
  voiceText = '';
  voiceMessage = '';
  voiceOk = false;
  private recognition: SpeechRecognitionLike | null = null;
  private listenTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.applyPeriod();
    this.api.getBranches().subscribe({ next: (b) => (this.branches = b) });
    this.api.getCategories().subscribe({ next: (c) => (this.categories = c) });
    this.loadData();
  }

  private todayIso(): string {
    return new Date().toISOString().slice(0, 10);
  }

  setPeriod(key: PeriodKey): void {
    this.period = key;
    this.applyPeriod();
    this.loadData();
  }

  applyPeriod(): void {
    const today = this.todayIso();
    const d = new Date(today + 'T00:00:00Z');
    if (this.period === 'hoy') {
      this.desde = this.hasta = today;
    } else if (this.period === '7dias') {
      this.hasta = today;
      d.setUTCDate(d.getUTCDate() - 6);
      this.desde = d.toISOString().slice(0, 10);
    } else if (this.period === '30dias') {
      this.hasta = today;
      d.setUTCDate(d.getUTCDate() - 29);
      this.desde = d.toISOString().slice(0, 10);
    } else if (this.period === 'mes') {
      this.hasta = today;
      this.desde = today.slice(0, 8) + '01';
    } else {
      this.desde = this.hasta = '';
    }
  }

  loadData(): void {
    this.loading = true;
    const params: { desde?: string; hasta?: string; branch_id?: number; category_id?: number } = {};
    if (this.period === 'custom') {
      if (this.desde) params.desde = this.desde;
      if (this.hasta) params.hasta = this.hasta;
    } else {
      params.desde = this.desde;
      params.hasta = this.hasta;
    }
    if (this.branchId) params.branch_id = this.branchId;
    if (this.categoryId) params.category_id = this.categoryId;
    this.api.getDashboardReport(params).subscribe({
      next: (r) => {
        this.report = r;
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  barHeight(pt: SalesPoint): number {
    const max = Math.max(...this.report!.sales_series.map((p) => p.amount), 1);
    return Math.max(2, Math.round((pt.amount / max) * 100));
  }

  // ------------------------------------------------------------------
  // VOZ (CU24)
  // ------------------------------------------------------------------
  get speechAvailable(): boolean {
    return !!(window.SpeechRecognition || window.webkitSpeechRecognition);
  }

  toggleListen(): void {
    if (this.listening) {
      this.recognition?.stop();
      return;
    }
    const Ctor = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Ctor) {
      this.voiceMessage = 'Este navegador no soporta reconocimiento de voz. Escribe el comando.';
      this.voiceOk = false;
      return;
    }
    const rec = new Ctor();
    rec.lang = this.pickLang();
    rec.continuous = false;
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.onresult = (event) => {
      const results = event?.results;
      const transcript =
        results && results.length > 0 && results[0].length > 0 ? results[0][0].transcript ?? '' : '';
      if (transcript.trim()) {
        this.stopWatchdog();
        this.voiceText = transcript;
        this.sendVoice();
      }
    };
    rec.onerror = (ev) => {
      this.stopWatchdog();
      this.listening = false;
      this.voiceMessage = `No pude escucharte (${ev.error || 'error'}). Revisa que el micrófono esté permitido e intenta de nuevo.`;
      this.voiceOk = false;
    };
    rec.onend = () => {
      this.stopWatchdog();
      this.listening = false;
    };
    this.recognition = rec;
    this.voiceMessage = '';
    this.listening = true;
    try {
      rec.start();
    } catch (err) {
      this.stopWatchdog();
      this.listening = false;
      this.voiceMessage = 'No pude iniciar el micrófono. Intenta tocar el botón nuevamente.';
      this.voiceOk = false;
      return;
    }
    // Si en ~10s no llega audio, cortamos solos y damos una pista clara.
    this.listenTimer = setTimeout(() => {
      if (this.listening) {
        this.stopWatchdog();
        try {
          this.recognition?.stop();
        } catch { /* ya detenido */ }
        this.listening = false;
        this.voiceMessage = 'No se detectó voz. Verifica el permiso del micrófono y habla claro.';
        this.voiceOk = false;
      }
    }, 10000);
  }

  private pickLang(): string {
    const navLang = (navigator.language || '').toLowerCase();
    if (navLang.startsWith('es')) return navLang.length <= 5 ? navLang : 'es-ES';
    return 'es-ES';
  }

  private stopWatchdog(): void {
    if (this.listenTimer != null) {
      clearTimeout(this.listenTimer);
      this.listenTimer = null;
    }
  }

  sendVoice(): void {
    const command = this.voiceText.trim();
    if (!command || this.voiceBusy) return;
    this.voiceBusy = true;
    this.voiceMessage = '';
    this.api.voiceReport(command).subscribe({
      next: (res) => {
        this.voiceBusy = false;
        this.voiceMessage = res.message;
        this.voiceOk = res.recognized;
        if (res.recognized && res.data) {
          const intent = res.intent;
          this.period = 'custom';
          this.desde = intent.date_from || '';
          this.hasta = intent.date_to || '';
          this.branchId = intent.branch_id ?? null;
          this.categoryId = intent.category_id ?? null;
          this.report = res.data;
          this.loading = false;
        }
      },
      error: () => (this.voiceBusy = false),
    });
  }

  // ------------------------------------------------------------------
  // Exportación: CSV y PDF
  // ------------------------------------------------------------------
  downloadCsv(): void {
    const r = this.report;
    if (!r || r.empty) return;
    const rows: string[][] = [];

    rows.push(['Reporte FashionStore']);
    rows.push(['Periodo', r.date_from, 'al', r.date_to]);
    rows.push([]);
    rows.push(['Indicador', 'Valor']);
    rows.push(['Ventas (Bs.)', r.kpis.total_sales.toFixed(2)]);
    rows.push(['Pedidos', String(r.kpis.total_orders)]);
    rows.push(['Ticket promedio (Bs.)', r.kpis.avg_order.toFixed(2)]);
    rows.push(['Reservas', String(r.kpis.reservations)]);
    rows.push(['Unidades disponibles', String(r.kpis.total_units_available)]);
    rows.push(['Variantes con stock bajo', String(r.kpis.low_stock_variants)]);
    rows.push(['Promociones activas', String(r.kpis.active_promotions)]);
    rows.push(['Descuento aplicado (Bs.)', r.kpis.discount_amount.toFixed(2)]);
    rows.push([]);
    rows.push(['Ventas por dia']);
    rows.push(['Fecha', 'Monto (Bs.)', 'Pedidos']);
    for (const p of r.sales_series) {
      rows.push([p.date, p.amount.toFixed(2), String(p.orders)]);
    }
    rows.push([]);
    rows.push(['Ventas por categoria']);
    rows.push(['Categoria', 'Unidades', 'Ventas (Bs.)']);
    for (const c of r.by_category) {
      rows.push([c.category_name, String(c.units), c.sales.toFixed(2)]);
    }
    rows.push([]);
    rows.push(['Top productos']);
    rows.push(['Producto', 'Unidades', 'Ingresos (Bs.)']);
    for (const t of r.top_products) {
      rows.push([t.name, String(t.units), t.revenue.toFixed(2)]);
    }

    const csv = '\uFEFF' + rows.map((row) => row.map(this.csvCell).join(';')).join('\r\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `reporte-fasionstore-${this.desde || 'sin-fechas'}-${this.hasta || 'hoy'}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  private csvCell(value: string): string {
    return '"' + value.replace(/"/g, '""') + '"';
  }

  printReport(): void {
    const r = this.report;
    if (!r || r.empty) return;
    const w = window.open('', '_blank', 'width=900,height=680');
    if (!w) {
      this.voiceMessage = 'Permite las ventanas emergentes para descargar el PDF desde el diálogo de impresión.';
      this.voiceOk = false;
      return;
    }

    const kpis: Array<[string, string]> = [
      ['Ventas del periodo', 'Bs. ' + r.kpis.total_sales.toFixed(2) + ' (' + r.kpis.total_orders + ' pedidos)'],
      ['Ticket promedio', 'Bs. ' + r.kpis.avg_order.toFixed(2)],
      ['Reservas', String(r.kpis.reservations)],
      ['Unidades disponibles', String(r.kpis.total_units_available)],
      ['Stock bajo', String(r.kpis.low_stock_variants)],
      ['Promociones activas', String(r.kpis.active_promotions)],
      ['Descuento aplicado', 'Bs. ' + r.kpis.discount_amount.toFixed(2)],
    ];
    const kpiHtml = kpis.map(([k, v]) => `<div class="kpi"><span>${k}</span><b>${v}</b></div>`).join('');

    const table = (title: string, head: string[], rows2: Array<string[]>): string =>
      rows2.length
        ? `<h3>${title}</h3><table><thead><tr>${head.map((c) => `<th>${c}</th>`).join('')}</tr></thead>
           <tbody>${rows2
             .map((row) => `<tr>${row.map((c) => `<td>${c}</td>`).join('')}</tr>`)
             .join('')}</tbody></table>`
        : '';

    const daily = table(
      'Ventas por día',
      ['Fecha', 'Monto (Bs.)', 'Pedidos'],
      r.sales_series.map((p) => [p.date, p.amount.toFixed(2), String(p.orders)]),
    );
    const cats = table(
      'Ventas por categoría',
      ['Categoría', 'Unidades', 'Ventas (Bs.)'],
      r.by_category.map((c) => [c.category_name, String(c.units), c.sales.toFixed(2)]),
    );
    const tops = table(
      'Top productos',
      ['Producto', 'Unidades', 'Ingresos (Bs.)'],
      r.top_products.map((t) => [t.name, String(t.units), t.revenue.toFixed(2)]),
    );
    const narrative = r.narrative ? `<p class="narrative">${r.narrative}</p>` : '';

    w.document.write(`<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><title>Reporte FashionStore</title>
    <style>
      body { font-family: Arial, Helvetica, sans-serif; color: #222; padding: 24px; max-width: 800px; margin: 0 auto; }
      h1 { color: #5b2333; font-size: 22px; margin-bottom: 2px; }
      h3 { color: #5b2333; font-size: 15px; margin: 18px 0 6px; }
      .meta { color: #777; font-size: 12px; margin-bottom: 18px; }
      .kpis { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 14px; }
      .kpi { border: 1px solid #e2d9d0; border-radius: 8px; padding: 8px 12px; font-size: 12px; min-width: 140px; }
      .kpi span { display: block; color: #777; margin-bottom: 2px; }
      .kpi b { font-size: 15px; color: #5b2333; }
      table { width: 100%; border-collapse: collapse; font-size: 12px; }
      th, td { border: 1px solid #ddd; padding: 5px 8px; text-align: left; }
      th { background: #f6f1eb; text-transform: uppercase; font-size: 11px; color: #5b2333; }
      .narrative { background: #faf4ef; border-left: 3px solid #5b2333; padding: 10px 12px; font-size: 12px; }
      @media print { body { padding: 0; } }
    </style></head><body>
      <h1>Reporte FashionStore</h1>
      <div class="meta">Período: ${r.date_from || '-'} al ${r.date_to || '-'} &middot; Generado: ${new Date().toLocaleString('es-BO')}</div>
      ${narrative}
      <div class="kpis">${kpiHtml}</div>
      ${daily}${cats}${tops}
    </body></html>`);
    w.document.close();
    w.focus();
    setTimeout(() => {
      try {
        w.print();
      } catch {
        /* el usuario puede imprimir desde el menú */
      }
    }, 400);
  }
}