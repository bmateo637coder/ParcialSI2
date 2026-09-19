import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, CategoryItem, Promotion, PromotionInput, Product } from './api.service';
import { ToastService } from './toast.service';

@Component({
  selector: 'app-promos',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
  <div class="page-head">
    <span class="eyebrow">Administración</span>
    <h1>Promociones</h1>
    <p class="lead">Crea ofertas globales o por categoría/producto. Los descuentos se aplican automáticamente al agregar productos al carrito.</p>
    <div style="max-width:420px; margin:1.5rem auto 0; display:flex; gap:.5rem;">
      <button class="btn btn-accent" (click)="startNew()">Nueva promoción</button>
    </div>
  </div>

  <div *ngIf="loading" class="grid">
    <div *ngFor="let s of [1,2,3]" class="skeleton" style="height:140px; border-radius:10px;"></div>
  </div>

  <div class="empty-state" *ngIf="!loading && !promotions.length">
    <div class="empty-icon">🏷️</div>
    <h3>Sin promociones</h3>
    <p>Crea tu primera promoción para empezar a descontar.</p>
  </div>

  <div class="grid" style="grid-template-columns:repeat(auto-fill,minmax(300px,1fr));">
    <div class="card branch-card" *ngFor="let p of promotions">
      <div style="display:flex; justify-content:space-between; align-items:flex-start;">
        <h3>{{ p.name }}</h3>
        <span class="badge" [class.badge-accent]="p.is_active" [class.badge-muted]="!p.is_active">
          {{ p.is_active ? 'Activa' : 'Desactivada' }}
        </span>
      </div>
      <p class="branch-meta">{{ p.description || 'Sin descripción' }}</p>
      <div class="branch-meta">
        <strong>{{ p.discount_type === 'PERCENTAGE' ? p.value + '%' : 'Bs ' + p.value }}</strong>
        <span> · {{ targetLabel(p) }}</span>
      </div>
      <div class="branch-meta" *ngIf="p.start_date || p.end_date">
        <span>{{ (p.start_date || '—') | slice:0:10 }} → {{ (p.end_date || '—') | slice:0:10 }}</span>
      </div>
      <div style="display:flex; gap:.5rem; margin-top:1rem; justify-content:flex-end;">
        <button class="btn btn-ghost btn-sm" (click)="editPromo(p)">Editar</button>
        <button *ngIf="p.is_active" class="btn btn-ghost btn-sm" (click)="deactivate(p)">Desactivar</button>
      </div>
    </div>
  </div>

  <!-- Modal nuevo/editar -->
  <div class="modal-overlay" *ngIf="editing">
    <div class="modal" style="max-width:520px;">
      <button class="modal-close" (click)="closeForm()">×</button>
      <h3>{{ promotionId ? 'Editar promoción' : 'Nueva promoción' }}</h3>
      <label class="form-label">Nombre</label>
      <input class="form-control" [(ngModel)]="form.name" placeholder="Ej: -20% en chaquetas">
      <label class="form-label">Descripción</label>
      <input class="form-control" [(ngModel)]="form.description" placeholder="Opcional">
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:.75rem;">
        <div>
          <label class="form-label">Tipo</label>
          <select class="form-control" [(ngModel)]="form.discount_type">
            <option value="PERCENTAGE">Porcentaje %</option>
            <option value="FIXED">Monto fijo (Bs)</option>
          </select>
        </div>
        <div>
          <label class="form-label">{{ form.discount_type === 'PERCENTAGE' ? 'Valor %' : 'Valor Bs' }}</label>
          <input class="form-control" type="number" [(ngModel)]="form.value" min="0">
        </div>
      </div>
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:.75rem;">
        <div>
          <label class="form-label">Aplicar a</label>
          <select class="form-control" [(ngModel)]="form.target_type" (change)="form.target_id = null">
            <option value="GLOBAL">Toda la tienda</option>
            <option value="CATEGORY">Categoría</option>
            <option value="PRODUCT">Producto</option>
          </select>
        </div>
        <div *ngIf="form.target_type === 'CATEGORY'">
          <label class="form-label">Categoría</label>
          <select class="form-control" [(ngModel)]="form.target_id">
            <option [ngValue]="null">— Elegir —</option>
            <option *ngFor="let c of categories" [ngValue]="c.id">{{ c.name }}</option>
          </select>
        </div>
        <div *ngIf="form.target_type === 'PRODUCT'">
          <label class="form-label">Producto</label>
          <select class="form-control" [(ngModel)]="form.target_id">
            <option [ngValue]="null">— Elegir —</option>
            <option *ngFor="let pr of products" [ngValue]="pr.id">{{ pr.name }}</option>
          </select>
        </div>
      </div>
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:.75rem;">
        <div>
          <label class="form-label">Inicio</label>
          <input class="form-control" type="date" [(ngModel)]="form.start_date">
        </div>
        <div>
          <label class="form-label">Fin</label>
          <input class="form-control" type="date" [(ngModel)]="form.end_date">
        </div>
      </div>
      <div style="display:flex; gap:.5rem; margin-top:1rem; justify-content:flex-end;">
        <button class="btn btn-ghost" (click)="closeForm()">Cancelar</button>
        <button class="btn btn-accent" (click)="save()" [disabled]="saving">Guardar</button>
      </div>
    </div>
  </div>
  `,
})
export class PromosComponent implements OnInit {
  promotions: Promotion[] = [];
  categories: CategoryItem[] = [];
  products: Product[] = [];
  loading = false;
  saving = false;
  editing = false;
  form: PromotionInput = this.emptyForm();

  constructor(private api: ApiService, private toast: ToastService) {}

  ngOnInit(): void {
    this.load();
    this.api.getCategories().subscribe({ next: (c) => (this.categories = c) });
    this.api.getProducts('', undefined, undefined).subscribe({ next: (p) => (this.products = p) });
  }

  load(): void {
    this.loading = true;
    this.api.getPromotions(true).subscribe({
      next: (p) => {
        this.promotions = p;
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.toast.error(this.errMsg(err));
      },
    });
  }

  startNew(): void {
    this.form = this.emptyForm();
    this.editing = true;
  }

  editPromo(p: Promotion): void {
    this.form = {
      name: p.name,
      description: p.description || '',
      discount_type: p.discount_type,
      value: p.value,
      target_type: p.target_type,
      target_id: p.target_id,
      start_date: p.start_date ? String(p.start_date).slice(0, 10) : '',
      end_date: p.end_date ? String(p.end_date).slice(0, 10) : '',
    };
    this.promotionId = p.id;
    this.editing = true;
  }

  closeForm(): void {
    this.editing = false;
    this.promotionId = null;
  }

  save(): void {
    if (!this.form.name.trim()) {
      this.toast.error('El nombre es obligatorio');
      return;
    }
    if (this.form.value <= 0) {
      this.toast.error('El valor debe ser mayor a 0');
      return;
    }
    if (this.form.target_type !== 'GLOBAL' && !this.form.target_id) {
      this.toast.error('Elige el producto o la categoría');
      return;
    }
    const payload: PromotionInput = {
      ...this.form,
      name: this.form.name.trim(),
      description: this.form.description?.trim() || null,
      start_date: this.form.start_date || null,
      end_date: this.form.end_date || null,
      target_id: this.form.target_type === 'GLOBAL' ? null : this.form.target_id,
    };
    this.saving = true;
    const op = this.promotionId
      ? this.api.updatePromotion(this.promotionId, payload)
      : this.api.createPromotion(payload);
    op.subscribe({
      next: () => {
        this.saving = false;
        this.closeForm();
        this.toast.success('Promoción guardada');
        this.load();
      },
      error: (err) => {
        this.saving = false;
        const serverMsg = this.errMsg(err);
        this.toast.error(serverMsg.includes('Error') ? 'Datos inválidos' : serverMsg);
      },
    });
  }

  deactivate(p: Promotion): void {
    this.api.deactivatePromotion(p.id).subscribe({
      next: () => {
        this.toast.success('Promoción desactivada');
        this.load();
      },
      error: (err) => this.toast.error(this.errMsg(err)),
    });
  }

  targetLabel(p: Promotion): string {
    if (p.target_type === 'GLOBAL') return 'Toda la tienda';
    if (p.target_type === 'CATEGORY') {
      const c = this.categories.find((x) => x.id === p.target_id);
      return c ? 'Categoría: ' + c.name : 'Categoría #' + p.target_id;
    }
    const pr = this.products.find((x) => x.id === p.target_id);
    return pr ? 'Producto: ' + pr.name : 'Producto #' + p.target_id;
  }

  promotionId: number | null = null;

  private emptyForm(): PromotionInput {
    return {
      name: '',
      description: '',
      discount_type: 'PERCENTAGE',
      value: 0,
      target_type: 'GLOBAL',
      target_id: null,
      start_date: '',
      end_date: '',
    };
  }

  private errMsg(err: any): string {
    return (err?.error?.detail as string) || (err?.message as string) || 'Error inesperado';
  }
}