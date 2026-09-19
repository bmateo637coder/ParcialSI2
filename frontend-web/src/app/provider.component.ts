import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, Proposal, ProposalInput, ProviderMe, Product } from './api.service';
import { ToastService } from './toast.service';

@Component({
  selector: 'app-provider',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
  <div class="page-head">
    <span class="eyebrow">Portal proveedor</span>
    <h1>{{ provider?.provider?.name || 'Mi negocio' }}</h1>
    <p class="lead">Gestiona el catálogo que ofreces a la tienda y propón nuevos productos para la próxima temporada.</p>
  </div>

  <div class="tabs" style="max-width:720px; margin:1rem auto 2rem;">
    <button class="tab" [class.active]="tab==='products'" (click)="tab='products'">Mis productos</button>
    <button class="tab" [class.active]="tab==='proposals'" (click)="tab='proposals'">Propuestas</button>
    <button class="tab" [class.active]="tab==='new'" (click)="tab='new'">Nueva propuesta</button>
  </div>

  <!-- Mis productos -->
  <section *ngIf="tab==='products'">
    <div *ngIf="loading" class="grid">
      <div *ngFor="let s of [1,2,3]" class="skeleton" style="height:120px; border-radius:10px;"></div>
    </div>
    <div class="empty-state" *ngIf="!loading && !products.length">
      <div class="empty-icon">📦</div>
      <h3>Aún no tienes productos</h3>
      <p>Propón tu primer producto para que el administrador lo apruebe.</p>
    </div>
    <div class="card product-card" *ngFor="let p of products">
      <div class="product-info">
        <h3>{{ p.name }}</h3>
        <p class="product-desc">{{ p.description || 'Sin descripción' }}</p>
        <span class="badge" [class.badge-accent]="p.is_active" [class.badge-muted]="!p.is_active">
          {{ p.is_active ? 'Disponible' : 'Pausado' }}
        </span>
      </div>
      <div class="product-actions">
        <span class="price">Bs {{ p.base_price | number:'1.2-2' }}</span>
        <button class="btn btn-ghost btn-sm" (click)="toggleProduct(p)">
          {{ p.is_active ? 'Pausar' : 'Publicar' }}
        </button>
      </div>
    </div>
  </section>

  <!-- Propuestas -->
  <section *ngIf="tab==='proposals'">
    <div class="empty-state" *ngIf="!loading && !proposals.length">
      <div class="empty-icon">📋</div>
      <h3>Sin propuestas</h3>
      <p>Propón un producto nuevo; un administrador lo revisará.</p>
    </div>
    <div class="card product-card" *ngFor="let pr of proposals">
      <div class="product-info">
        <h3>{{ pr.name }}</h3>
        <p class="product-desc">{{ pr.description || 'Sin descripción' }}</p>
        <span class="badge"
              [class.badge-warn]="pr.status==='PENDIENTE'"
              [class.badge-accent]="pr.status==='APROBADA'"
              [class.badge-muted]="pr.status==='RECHAZADA'">
          {{ pr.status }}
        </span>
        <p *ngIf="pr.admin_comment" class="product-desc"><em>{{ pr.admin_comment }}</em></p>
      </div>
      <div class="product-actions">
        <span class="price">Bs {{ pr.base_price | number:'1.2-2' }}</span>
      </div>
    </div>
  </section>

  <!-- Nueva propuesta -->
  <section *ngIf="tab==='new'" style="max-width:480px; margin:0 auto;">
    <div class="card" style="padding:1.5rem;">
      <h3>Propón un producto</h3>
      <label class="form-label">Nombre</label>
      <input class="form-control" [(ngModel)]="newProposal.name" placeholder="Ej: Chaqueta biker">
      <label class="form-label">Descripción</label>
      <textarea class="form-control" [(ngModel)]="newProposal.description" rows="3" placeholder="Material, temporada, público…"></textarea>
      <label class="form-label">Precio base (Bs)</label>
      <input class="form-control" type="number" [(ngModel)]="newProposal.base_price" placeholder="0.00">
      <div style="display:flex; gap:.5rem; margin-top:1rem; justify-content:flex-end;">
        <button class="btn btn-ghost" (click)="resetProposal()">Limpiar</button>
        <button class="btn btn-accent" (click)="submitProposal()" [disabled]="saving">Enviar propuesta</button>
      </div>
    </div>
  </section>
  `,
})
export class ProviderComponent implements OnInit {
  tab: 'products' | 'proposals' | 'new' = 'products';
  provider: ProviderMe | null = null;
  products: Product[] = [];
  proposals: Proposal[] = [];
  newProposal: ProposalInput = { name: '', description: '', base_price: 0 };
  loading = false;
  saving = false;

  constructor(private api: ApiService, private toast: ToastService) {}

  ngOnInit(): void {
    this.api.getProviderMe().subscribe({
      next: (me) => {
        this.provider = me;
        this.loadProducts();
        this.loadProposals();
      },
      error: (err) => this.toast.error(this.errMsg(err)),
    });
  }

  loadProducts(): void {
    this.loading = true;
    this.api.getProviderProducts().subscribe({
      next: (p) => {
        this.products = p;
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.toast.error(this.errMsg(err));
      },
    });
  }

  loadProposals(): void {
    this.api.getProposals().subscribe({
      next: (pr) => (this.proposals = pr),
      error: (err) => this.toast.error(this.errMsg(err)),
    });
  }

  toggleProduct(p: Product): void {
    this.api.updateProviderProduct(p.id, !p.is_active).subscribe({
      next: (updated) => {
        const idx = this.products.findIndex((x) => x.id === updated.id);
        if (idx >= 0) this.products[idx] = updated;
        this.toast.success(updated.is_active ? 'Producto publicado' : 'Producto pausado');
      },
      error: (err) => this.toast.error(this.errMsg(err)),
    });
  }

  submitProposal(): void {
    if (!this.newProposal.name.trim()) {
      this.toast.error('El nombre es obligatorio');
      return;
    }
    if (this.newProposal.base_price <= 0) {
      this.toast.error('El precio base debe ser mayor a 0');
      return;
    }
    this.saving = true;
    this.api.proposeProduct({
      name: this.newProposal.name.trim(),
      description: this.newProposal.description?.trim() || null,
      base_price: this.newProposal.base_price,
    }).subscribe({
      next: (pr) => {
        this.saving = false;
        this.toast.success('Propuesta enviada. Un administrador la revisará.');
        this.proposals = [pr, ...this.proposals];
        this.resetProposal();
        this.tab = 'proposals';
      },
      error: (err) => {
        this.saving = false;
        this.toast.error(this.errMsg(err));
      },
    });
  }

  resetProposal(): void {
    this.newProposal = { name: '', description: '', base_price: 0 };
  }

  private errMsg(err: any): string {
    return (err?.error?.detail as string) || (err?.message as string) || 'Error inesperado';
  }
}