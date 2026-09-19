import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService, CategoryItem, Product, ProductVariant, RecommendedItem } from './api.service';
import { CommonModule } from '@angular/common';
import { ToastService } from './toast.service';

const FALLBACK_IMG =
  'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&q=80&w=600';
const REC_IMG =
  'https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&q=80&w=400';

@Component({
  selector: 'app-catalog',
  standalone: true,
  imports: [FormsModule, CommonModule],
  template: `
  <div class="page-head">
    <span class="eyebrow">Colección de temporada</span>
    <h1>Moda que inspira</h1>
    <p class="lead">Descubre las últimas tendencias. Filtra por categoría y encuentra tu estilo.</p>

    <div style="max-width: 520px; margin: 1.75rem auto 0; display: flex; gap: 0.5rem;">
      <input class="form-control" [(ngModel)]="q" placeholder="Buscar por nombre o descripción…" (keyup.enter)="search()">
      <button class="btn btn-accent" (click)="search()" [disabled]="loading">Buscar</button>
    </div>
  </div>

  <div class="chip-group">
    <button class="chip" [class.active]="activeCategory === null" (click)="filterCategory(null)">Todas</button>
    <button
      class="chip"
      *ngFor="let c of categories"
      [class.active]="activeCategory === c.id"
      (click)="filterCategory(c.id)">
      {{ c.name }}
      <span *ngIf="c.products_count">({{ c.products_count }})</span>
    </button>
  </div>

  <!-- Recomendaciones (CU22) -->
  <section *ngIf="recommended.length" style="margin-bottom: 2rem;">
    <div style="display:flex; align-items:baseline; justify-content:space-between; margin-bottom:.6rem;">
      <div>
        <span class="eyebrow">Para ti</span>
        <h2 style="margin-top:.1rem;">Recomendado para ti</h2>
      </div>
      <span class="badge badge-accent" *ngIf="recSource === 'ai'">Basado en tus compras</span>
      <span class="badge badge-info" *ngIf="recSource === 'featured'">Destacados</span>
    </div>
    <p style="color:var(--muted); font-size:.9rem; margin-bottom:1rem;" *ngIf="recommended.length">
      {{ recommended[0].reason }}
    </p>
    <div class="grid">
      <div class="product-card" *ngFor="let r of recommended">
        <div class="product-media">
          <div class="product-badge">{{ r.category }}</div>
          <img [src]="recImg" [alt]="r.name" loading="lazy">
        </div>
        <div class="product-body">
          <p class="product-cat">Sugerencia FashionStore</p>
          <h3>{{ r.name }}</h3>
          <p class="product-desc">{{ r.reason }}</p>
          <div class="product-price-row">
            <span class="product-price">Bs. {{ r.base_price | number: '1.2-2' }}</span>
            <button class="btn btn-outline btn-sm" (click)="goRecommended(r)">Ver prenda</button>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Loading -->
  <div *ngIf="loading && !products.length" class="grid">
    <div *ngFor="let s of [1,2,3,4,5,6]" class="product-card">
      <div class="skeleton skeleton-card"></div>
      <div class="product-body">
        <div class="skeleton" style="height:18px; width:70%;"></div>
        <div class="skeleton" style="height:12px; width:40%; margin-top:.6rem;"></div>
        <div class="skeleton" style="height:22px; width:35%; margin-top:1rem;"></div>
      </div>
    </div>
  </div>

  <!-- Empty -->
  <div *ngIf="!loading && !products.length && !error" class="empty-state">
    <div class="empty-icon">🕊</div>
    <h3>Sin resultados</h3>
    <p>No encontramos productos para esta búsqueda. Prueba con otros términos o categorías.</p>
  </div>

  <!-- Error -->
  <div *ngIf="!loading && error" class="empty-state">
    <div class="empty-icon">⚠️</div>
    <h3>No se pudo cargar el catálogo</h3>
    <p>Verifica que el servidor esté activo e inténtalo de nuevo.</p>
    <button class="btn btn-accent" style="margin-top:1rem;" (click)="search()">Reintentar</button>
  </div>

  <!-- Grid -->
  <div class="grid" *ngIf="products.length">
    <div class="product-card" *ngFor="let p of products">
      <div class="product-media">
        <div class="product-badge" *ngIf="p.category?.name">{{ p.category?.name }}</div>
        <img [src]="p.image_url || fallbackImg" [alt]="p.name" loading="lazy" (error)="onImgError($event)">
      </div>
      <div class="product-body">
        <p class="product-cat">{{ p.season?.name || 'Colección FashionStore' }}</p>
        <h3>{{ p.name }}</h3>
        <p *ngIf="p.description" class="product-desc">{{ p.description }}</p>
        <div class="product-price-row">
          <span class="product-price">Bs. {{ p.base_price | number: '1.2-2' }}</span>
          <button class="btn btn-outline btn-sm" (click)="openDetail(p)">Ver opciones</button>
        </div>
      </div>
    </div>
  </div>

  <!-- Modal detalle -->
  <div class="modal-backdrop" *ngIf="selected" (click.self)="closeDetail()">
    <div class="modal">
      <div class="modal-head">
        <h3>{{ selected.name }}</h3>
        <button class="modal-close" (click)="closeDetail()">&times;</button>
      </div>
      <div class="modal-body">
        <div class="modal-grid">
          <div class="product-media-full">
            <img [src]="selected.image_url || fallbackImg" [alt]="selected.name" (error)="onImgError($event)">
          </div>
          <div>
            <span class="badge badge-accent" *ngIf="selected.category?.name">{{ selected.category?.name }}</span>
            <span class="badge badge-info" *ngIf="selected.season?.name" style="margin-left:.4rem;">{{ selected.season?.name }}</span>
            <h2 style="margin:.75rem 0 .5rem;">Bs. {{ selected.base_price | number: '1.2-2' }}</h2>
            <p style="font-size:.95rem;">{{ selected.description || 'Descripción próxima.' }}</p>

            <div style="display:flex; gap:.5rem; margin-top:1rem; flex-wrap:wrap;">
              <button class="btn btn-outline" (click)="tryOn(selected)">
                Probar en vestidor virtual
              </button>
            </div>

            <h4 style="margin-top:1.25rem;">Elige talla y color</h4>
            <div *ngIf="variantsLoading" class="skeleton" style="height:40px; margin-top:.75rem;"></div>
            <div class="variant-list" *ngIf="!variantsLoading">
              <button
                *ngFor="let v of variants"
                class="variant-item"
                style="border:1px solid var(--line); background:var(--surface); cursor:pointer; text-align:left;"
                [class.variant-selected]="selectedVariant?.id === v.id"
                (click)="pickVariant(v)"
                [disabled]="v.stock === 0">
                <strong>{{ v.size_name }}</strong>
                <span class="v-tags">{{ v.color_name }}</span>
                <span class="v-tags" [class.stock-ok]="v.stock > 10" [class.stock-low]="v.stock > 0 && v.stock <= 10" [class.stock-out]="v.stock === 0">
                  {{ v.stock > 0 ? (v.stock + ' disponibles') : 'Agotado' }}
                </span>
              </button>
              <div class="empty-state" *ngIf="!variants.length" style="grid-column: 1 / -1; padding: 1.5rem;">
                <p>Este producto aún no tiene variantes configuradas.</p>
              </div>
            </div>

            <div *ngIf="selectedVariant && !variantsLoading" style="display:flex; gap:.5rem; margin-top:1rem;">
              <input class="form-control" type="number" min="1" [(ngModel)]="addQty" style="max-width:100px;" [disabled]="selectedVariant.stock === 0">
              <button class="btn btn-accent" (click)="addToCart()" [disabled]="adding || selectedVariant.stock === 0">
                <span *ngIf="adding" class="spinner"></span>
                {{ selectedVariant.stock === 0 ? 'Agotado' : 'Agregar al carrito' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  `,
})
export class CatalogComponent implements OnInit {
  q = '';
  products: Product[] = [];
  categories: CategoryItem[] = [];
  activeCategory: number | null = null;
  loading = false;
  error = false;
  fallbackImg = FALLBACK_IMG;

  recommended: RecommendedItem[] = [];
  recSource = '';
  recImg = REC_IMG;

  selected: Product | null = null;
  variants: ProductVariant[] = [];
  variantsLoading = false;
  selectedVariant: ProductVariant | null = null;
  addQty = 1;
  adding = false;

  constructor(private api: ApiService, private router: Router, private toast: ToastService) {}

  ngOnInit(): void {
    this.loading = true;
    this.api.getCategories().subscribe({
      next: (cats) => (this.categories = cats),
      error: () => {},
    });
    if (this.api.isAuthenticated) {
      this.api.getRecommendations().subscribe({
        next: (rec) => {
          this.recommended = rec.items || [];
          this.recSource = rec.source;
        },
        error: () => {},
      });
    }
    this.search();

    const st = history.state as { openProductId?: number } | null;
    if (st?.openProductId) {
      this.api.getProduct(st.openProductId).subscribe({
        next: (p) => {
          this.openDetail(p);
          window.scrollTo({ top: 0, behavior: 'smooth' });
        },
        error: () => this.toast.info('La prenda ya no está disponible.'),
      });
    }
  }

  goRecommended(r: RecommendedItem): void {
    this.api.getProduct(r.product_id).subscribe({
      next: (p) => {
        this.openDetail(p);
        window.scrollTo({ top: 0, behavior: 'smooth' });
      },
      error: () => this.toast.info('La prenda ya no está disponible.'),
    });
  }

  tryOn(p: Product): void {
    this.router.navigate(['/vestidor'], { state: { product: p } });
  }

  search(): void {
    this.loading = true;
    this.error = false;
    this.api.getProducts(this.q, this.activeCategory ?? undefined).subscribe({
      next: (res) => {
        this.products = res;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.error = true;
      },
    });
  }

  filterCategory(id: number | null): void {
    this.activeCategory = id;
    this.search();
  }

  openDetail(p: Product): void {
    this.selected = p;
    this.variants = [];
    this.selectedVariant = null;
    this.addQty = 1;
    this.variantsLoading = true;
    this.api.getVariants(p.id).subscribe({
      next: (res) => {
        this.variants = res;
        this.variantsLoading = false;
      },
      error: () => (this.variantsLoading = false),
    });
  }

  pickVariant(v: ProductVariant): void {
    this.selectedVariant = v;
    this.addQty = 1;
  }

  addToCart(): void {
    if (!this.selectedVariant) return;
    if (!this.api.isAuthenticated) {
      this.toast.info('Inicia sesión para agregar productos al carrito.');
      this.router.navigate(['/auth']);
      return;
    }
    const qty = Math.max(1, Math.floor(this.addQty || 1));
    this.adding = true;
    this.api.addToCart(this.selectedVariant.id, qty).subscribe({
      next: () => {
        this.adding = false;
        this.toast.success('Agregado al carrito.');
        this.closeDetail();
      },
      error: () => (this.adding = false),
    });
  }

  closeDetail(): void {
    this.selected = null;
  }

  onImgError(event: Event): void {
    (event.target as HTMLImageElement).src = FALLBACK_IMG;
  }
}