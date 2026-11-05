import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { ApiService } from './api.service';
import { environment } from '../environments/environment';

@Component({
  selector: 'app-platform', standalone: true, imports: [CommonModule, FormsModule],
  template: `
    <div class="page-head"><h1>Empresas y suscripciones</h1></div>
    <p role="alert" *ngIf="error">{{ error }}</p>
    <div *ngIf="membership" class="card" style="padding:1rem;">
      <h2>{{ membership.empresa }}</h2><p>Plan {{ membership.plan }} · {{ membership.estado }}</p>
      <p>Vigencia: {{ membership.fecha_inicio }} — {{ membership.fecha_vencimiento }}</p>
      <p>Hasta {{ membership.max_sucursales }} sucursales. Reportes IA: {{ membership.permite_reportes_ia ? 'habilitados' : 'no incluidos' }}.</p>
    </div>
    <ng-container *ngIf="isPlatform">
      <div class="card" style="padding:1rem;margin-bottom:1rem;">
        <h2>Registrar empresa</h2>
        <form (ngSubmit)="createCompany()" style="display:grid;gap:.75rem;max-width:640px;">
          <label>Razón social<input class="form-control" name="business" [(ngModel)]="company.razon_social" required></label>
          <label>NIT<input class="form-control" name="nit" [(ngModel)]="company.nit" required></label>
          <label>Nombre del administrador<input class="form-control" name="first" [(ngModel)]="company.admin_first_name" required></label>
          <label>Apellido<input class="form-control" name="last" [(ngModel)]="company.admin_last_name" required></label>
          <label>Correo del administrador<input class="form-control" name="email" type="email" [(ngModel)]="company.admin_email" required></label>
          <label>Contraseña inicial<input class="form-control" name="password" type="password" minlength="6" [(ngModel)]="company.admin_password" required></label>
          <label>Plan<select class="form-control" name="plan" [(ngModel)]="company.plan_id" required><option *ngFor="let p of plans" [ngValue]="p.id">{{ p.nombre }}</option></select></label>
          <button class="btn btn-primary" [disabled]="busy">Registrar empresa y administrador</button>
        </form>
      </div>
      <div class="card" style="padding:1rem;margin-bottom:1rem;">
        <h2>Empresas contratantes</h2>
        <button class="btn btn-outline" *ngFor="let e of companies" (click)="selectCompany(e)">{{ e.razon_social }}</button>
        <form *ngIf="subscription" (ngSubmit)="saveSubscription()" style="display:grid;gap:.75rem;max-width:600px;margin-top:1rem;">
          <h3>{{ selectedCompany.razon_social }}</h3>
          <label>Plan<select class="form-control" name="subPlan" [(ngModel)]="subscription.plan_id"><option *ngFor="let p of plans" [ngValue]="p.id">{{ p.nombre }}</option></select></label>
          <label>Estado<select class="form-control" name="state" [(ngModel)]="subscription.estado"><option *ngFor="let s of states">{{ s }}</option></select></label>
          <label>Inicio<input class="form-control" name="start" type="date" [(ngModel)]="subscription.fecha_inicio"></label>
          <label>Vencimiento<input class="form-control" name="end" type="date" [(ngModel)]="subscription.fecha_vencimiento"></label>
          <button class="btn btn-primary" [disabled]="busy">Guardar suscripción</button>
        </form>
      </div>
      <div class="card" style="padding:1rem;">
        <h2>Planes configurables</h2>
        <div *ngFor="let p of plans" style="display:flex;gap:.75rem;flex-wrap:wrap;align-items:end;margin:1rem 0;">
          <label>Nombre<input class="form-control" [(ngModel)]="p.nombre"></label>
          <label>Sucursales<input class="form-control" type="number" min="1" [(ngModel)]="p.max_sucursales"></label>
          <label>Precio mensual<input class="form-control" type="number" min="0" [(ngModel)]="p.precio_mensual"></label>
          <label><input type="checkbox" [(ngModel)]="p.permite_reportes_ia"> Reportes IA</label>
          <label><input type="checkbox" [(ngModel)]="p.permite_analitica_ml"> Analítica ML</label>
          <button class="btn btn-outline" (click)="savePlan(p)">Guardar plan</button>
        </div>
      </div>
    </ng-container>
  `
})
export class PlatformComponent implements OnInit {
  private http = inject(HttpClient);
  private api = inject(ApiService);
  isPlatform = this.api.currentUser.value?.role_name === 'Administrador de Plataforma';
  companies: any[] = []; plans: any[] = [];
  membership: any; selectedCompany: any; subscription: any;
  error = ''; busy = false;
  states = ['ACTIVA', 'SUSPENDIDA', 'VENCIDA', 'CANCELADA'];
  company = { razon_social: '', nit: '', admin_first_name: '', admin_last_name: '', admin_email: '', admin_password: '', plan_id: null as number | null };
  private base = `${environment.apiUrl}/plataforma`;
  ngOnInit() {
    if (this.isPlatform) this.load();
    else this.http.get(`${this.base}/mi-suscripcion`).subscribe({ next: r => this.membership = r, error: e => this.showError(e) });
  }
  load() {
    this.http.get<any[]>(`${this.base}/empresas`).subscribe({ next: r => this.companies = r, error: e => this.showError(e) });
    this.http.get<any[]>(`${this.base}/planes?solo_activos=false`).subscribe({ next: r => this.plans = r, error: e => this.showError(e) });
  }
  selectCompany(company: any) {
    this.selectedCompany = company;
    this.http.get(`${this.base}/empresas/${company.id}/suscripcion`).subscribe({ next: r => this.subscription = r, error: e => this.showError(e) });
  }
  createCompany() {
    this.busy = true; this.error = '';
    this.http.post(`${this.base}/empresas`, this.company).subscribe({ next: () => { this.busy = false; this.company.admin_password = ''; this.load(); }, error: e => this.showError(e) });
  }
  saveSubscription() {
    this.busy = true; this.error = '';
    const { plan_id, estado, fecha_inicio, fecha_vencimiento } = this.subscription;
    this.http.patch(`${this.base}/empresas/${this.selectedCompany.id}/suscripcion`, { plan_id, estado, fecha_inicio, fecha_vencimiento }).subscribe({ next: r => { this.subscription = r; this.busy = false; }, error: e => this.showError(e) });
  }
  savePlan(plan: any) {
    this.http.put(`${this.base}/planes/${plan.id}`, plan).subscribe({ next: () => { this.error = ''; }, error: e => this.showError(e) });
  }
  private showError(error: any) { this.busy = false; const detail = error?.error?.detail; this.error = typeof detail === 'string' ? detail : 'Revisa los datos y vuelve a intentar.'; }
}
