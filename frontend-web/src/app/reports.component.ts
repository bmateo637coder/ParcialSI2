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
  onresult: (() => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
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
    rec.lang = 'es-BO';
    rec.continuous = false;
    rec.interimResults = false;
    rec.onresult = () => {
      const results = (this.recognition as unknown as { results?: Array<Array<{ transcript: string }>> }).results;
      const transcript = results && results.length > 0 ? results[0][0].transcript : '';
      if (transcript.trim()) {
        this.voiceText = transcript;
        this.sendVoice();
      }
    };
    rec.onerror = (ev) => {
      this.listening = false;
      this.voiceMessage = `No pude escucharte (${ev.error || 'error'}). Intenta de nuevo.`;
      this.voiceOk = false;
    };
    rec.onend = () => (this.listening = false);
    this.recognition = rec;
    this.voiceMessage = '';
    this.listening = true;
    rec.start();
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
}