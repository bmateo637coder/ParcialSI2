import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService, CategoryItem, Product, ProductVariant } from './api.service';
import { CommonModule } from '@angular/common';

const FALLBACK_IMG =
  'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&q=80&w=600';

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
  <div *ngIf="!loading && !products.length" class="empty-state">
    <div class="empty-icon">🕊</div>
    <h3>Sin resultados</h3>
    <p>No encontramos productos para esta búsqueda. Prueba con otros términos o categorías.</p>
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

            <h4 style="margin-top:1.25rem;">Disponibilidad por variante</h4>
            <div *ngIf="variantsLoading" class="skeleton" style="height:40px; margin-top:.75rem;"></div>
            <div class="variant-list" *ngIf="!variantsLoading">
              <div class="variant-item" *ngFor="let v of variants">
                <strong>{{ v.size_name }}</strong>
                <span class="v-tags">{{ v.color_name }}</span>
                <span class="v-tags" [class.stock-ok]="v.stock > 10" [class.stock-low]="v.stock > 0 && v.stock <= 10" [class.stock-out]="v.stock === 0">
                  {{ v.stock > 0 ? (v.stock + ' disponibles') : 'Agotado' }}
                </span>
              </div>
              <div class="empty-state" *ngIf="!variants.length" style="grid-column: 1 / -1; padding: 1.5rem;">
                <p>Este producto aún no tiene variantes configuradas.</p>
              </div>
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
  fallbackImg = FALLBACK_IMG;

  selected: Product | null = null;
  variants: ProductVariant[] = [];
  variantsLoading = false;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.loading = true;
    this.api.getCategories().subscribe({
      next: (cats) => (this.categories = cats),
      error: () => {},
    });
    this.search();
  }

  search(): void {
    this.loading = true;
    this.api.getProducts(this.q, this.activeCategory ?? undefined).subscribe({
      next: (res) => {
        this.products = res;
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  filterCategory(id: number | null): void {
    this.activeCategory = id;
    this.search();
  }

  openDetail(p: Product): void {
    this.selected = p;
    this.variants = [];
    this.variantsLoading = true;
    this.api.getVariants(p.id).subscribe({
      next: (res) => {
        this.variants = res;
        this.variantsLoading = false;
      },
      error: () => (this.variantsLoading = false),
    });
  }

  closeDetail(): void {
    this.selected = null;
  }

  onImgError(event: Event): void {
    (event.target as HTMLImageElement).src = FALLBACK_IMG;
  }
}