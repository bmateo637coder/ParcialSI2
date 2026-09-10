import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService, Branch, Product, ProductVariant, MetadataItem } from './api.service';
import { CommonModule } from '@angular/common';
import { ToastService } from './toast.service';

type Tab = 'products' | 'branches' | 'catalog';

interface ProductForm {
  id: number | null;
  name: string;
  description: string;
  base_price: number;
  image_url: string;
  category_id: number | null;
  season_id: number | null;
  provider_id: number | null;
}

interface BranchForm {
  id: number | null;
  name: string;
  city: string;
  address: string;
  phone: string;
}

interface VariantForm {
  size_id: number | null;
  color_id: number | null;
  sku: string;
  stock: number;
}

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [FormsModule, CommonModule],
  template: `
  <div class="page-head">
    <span class="eyebrow">Zona restringida</span>
    <h1>Panel de administración</h1>
    <p class="lead">Gestiona productos, sucursales y el catálogo de la tienda.</p>
  </div>

  <div class="card">
    <div class="admin-tabs">
      <button class="admin-tab" [class.active]="tab === 'products'" (click)="tab = 'products'">Productos</button>
      <button class="admin-tab" [class.active]="tab === 'branches'" (click)="tab = 'branches'">Sucursales</button>
      <button class="admin-tab" [class.active]="tab === 'catalog'" (click)="tab = 'catalog'">Catálogo</button>
    </div>

    <!-- ============ PRODUCTOS ============ -->
    <section *ngIf="tab === 'products'">
      <div class="toolbar">
        <h2>Productos del catálogo</h2>
        <button class="btn btn-accent" (click)="openProduct()">+ Nuevo producto</button>
      </div>
      <div *ngIf="productsLoading" class="skeleton" style="height:60px;"></div>
      <div class="empty-state" *ngIf="!productsLoading && !products.length">Aún no hay productos.</div>
      <div class="table-wrap" *ngIf="!productsLoading && products.length">
        <table class="table">
          <thead>
            <tr><th></th><th>Producto</th><th>Categoría</th><th>Precio</th><th>Stock total</th><th class="text-right">Acciones</th></tr>
          </thead>
          <tbody>
            <tr *ngFor="let p of products">
              <td><img class="product-img-thumb" [src]="p.image_url || imgFallback" width="44" height="56" style="object-fit:cover; border-radius:6px;" (error)="imgFallbackError($event)"></td>
              <td><strong>{{ p.name }}</strong></td>
              <td>{{ p.category?.name || '—' }}</td>
              <td>Bs. {{ p.base_price | number: '1.2-2' }}</td>
              <td>{{ stockByProduct(p.id) }}</td>
              <td>
                <div class="actions">
                  <button class="btn btn-outline btn-sm" (click)="openProduct(p)">Editar</button>
                  <button class="btn btn-danger btn-sm" (click)="deleteProduct(p)">Eliminar</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- ============ SUCURSALES ============ -->
    <section *ngIf="tab === 'branches'">
      <div class="toolbar">
        <h2>Sucursales</h2>
        <button class="btn btn-accent" (click)="openBranch()">+ Nueva sucursal</button>
      </div>
      <div class="empty-state" *ngIf="!branches.length">No hay sucursales registradas.</div>
      <div class="table-wrap" *ngIf="branches.length">
        <table class="table">
          <thead>
            <tr><th>Nombre</th><th>Ciudad</th><th>Dirección</th><th>Teléfono</th><th>Estado</th><th class="text-right">Acciones</th></tr>
          </thead>
          <tbody>
            <tr *ngFor="let b of branches">
              <td><strong>{{ b.name }}</strong></td>
              <td>{{ b.city }}</td>
              <td>{{ b.address || '—' }}</td>
              <td>{{ b.phone || '—' }}</td>
              <td><span class="badge badge-success" *ngIf="b.is_active !== false">Activa</span><span class="badge badge-danger" *ngIf="b.is_active === false">Inactiva</span></td>
              <td>
                <div class="actions">
                  <button class="btn btn-outline btn-sm" (click)="openBranch(b)">Editar</button>
                  <button class="btn btn-danger btn-sm" (click)="deleteBranch(b)">Eliminar</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- ============ CATÁLOGO ============ -->
    <section *ngIf="tab === 'catalog'">
      <h2>Datos de referencia</h2>
      <p style="color:var(--muted); margin-bottom:1.5rem;">Agrega categorías, temporadas, tallas, colores y proveedores que luego se usan en el formulario de productos.</p>
      <div class="grid" style="grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));">
        <div class="card" *ngFor="let ref of refForms">
          <h3 style="margin-bottom:1rem;">{{ ref.label }}</h3>
          <div class="form-group" style="margin-bottom:.75rem;">
            <input class="form-control" [(ngModel)]="ref.input" (keyup.enter)="addRef(ref)" [placeholder]="ref.placeholder">
          </div>
          <button class="btn btn-outline btn-sm btn-block" (click)="addRef(ref)">Agregar</button>
          <div style="margin-top:1rem; display:flex; flex-wrap:wrap; gap:.35rem;">
            <span class="badge badge-accent" *ngFor="let item of ref.items">{{ item.name }}</span>
          </div>
        </div>
      </div>
    </section>
  </div>

  <!-- MODAL PRODUCTO -->
  <div class="modal-backdrop" *ngIf="prodModalOpen" (click.self)="closeProduct()">
    <div class="modal" style="max-width: 720px;">
      <div class="modal-head">
        <h3>{{ productForm.id ? 'Editar producto' : 'Nuevo producto' }}</h3>
        <button class="modal-close" (click)="closeProduct()">&times;</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label class="form-label">Nombre *</label>
          <input class="form-control" [(ngModel)]="productForm.name" placeholder="Ej: Vestido Floral Verano">
        </div>
        <div class="form-group">
          <label class="form-label">Descripción</label>
          <textarea class="form-control" [(ngModel)]="productForm.description" placeholder="Describe el producto…"></textarea>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Precio base (Bs.) *</label>
            <input class="form-control" type="number" min="0" step="0.01" [(ngModel)]="productForm.base_price">
          </div>
          <div class="form-group">
            <label class="form-label">URL de imagen</label>
            <input class="form-control" [(ngModel)]="productForm.image_url" placeholder="https://…">
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Categoría</label>
            <select class="form-control" [(ngModel)]="productForm.category_id">
              <option [ngValue]="null">— Sin categoría —</option>
              <option *ngFor="let c of categories" [ngValue]="c.id">{{ c.name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Temporada</label>
            <select class="form-control" [(ngModel)]="productForm.season_id">
              <option [ngValue]="null">— Sin temporada —</option>
              <option *ngFor="let s of seasons" [ngValue]="s.id">{{ s.name }}</option>
            </select>
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Proveedor</label>
          <select class="form-control" [(ngModel)]="productForm.provider_id">
            <option [ngValue]="null">— Sin proveedor —</option>
            <option *ngFor="let p of providers" [ngValue]="p.id">{{ p.name }}</option>
          </select>
        </div>

        <hr style="border:none; border-top:1px solid var(--line); margin:1.25rem 0;">
        <div style="display:flex; justify-content:space-between; align-items:center;" *ngIf="productForm.id">
          <h4 style="margin:0;">Variantes (talla / color / stock)</h4>
        </div>

        <div *ngIf="productForm.id" style="margin-top:1rem;">
          <div class="variant-list">
            <div class="variant-item" *ngFor="let v of variants">
              <strong>{{ v.size_name }} / {{ v.color_name }}</strong>
              <span class="v-tags">SKU: {{ v.sku }}</span>
              <span class="v-tags" [class.stock-ok]="v.stock > 10" [class.stock-low]="v.stock > 0 && v.stock <= 10" [class.stock-out]="v.stock === 0">Stock: {{ v.stock }}</span>
              <button class="btn btn-danger btn-sm" style="align-self:flex-start; margin-top:.4rem;" (click)="deleteVariant(v)">Quitar</button>
            </div>
          </div>

          <div class="form-row" style="margin-top:1.25rem; align-items:end;">
            <div class="form-group">
              <label class="form-label">Talla</label>
              <select class="form-control" [(ngModel)]="variantForm.size_id">
                <option [ngValue]="null">—</option>
                <option *ngFor="let s of sizes" [ngValue]="s.id">{{ s.name }}</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Color</label>
              <select class="form-control" [(ngModel)]="variantForm.color_id">
                <option [ngValue]="null">—</option>
                <option *ngFor="let c of colors" [ngValue]="c.id">{{ c.name }}</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">SKU</label>
              <input class="form-control" [(ngModel)]="variantForm.sku" placeholder="ABC-M-BL">
            </div>
            <div class="form-group">
              <label class="form-label">Stock</label>
              <input class="form-control" type="number" min="0" [(ngModel)]="variantForm.stock">
            </div>
            <div class="form-group">
              <button class="btn btn-outline" (click)="addVariant()">+ Agregar</button>
            </div>
          </div>
        </div>
      </div>
      <div class="modal-foot">
        <button class="btn btn-outline" (click)="closeProduct()">Cancelar</button>
        <button class="btn btn-accent" (click)="saveProduct()" [disabled]="!productForm.name.trim()">Guardar producto</button>
      </div>
    </div>
  </div>

  <!-- MODAL SUCURSAL -->
  <div class="modal-backdrop" *ngIf="branchModalOpen" (click.self)="closeBranch()">
    <div class="modal">
      <div class="modal-head">
        <h3>{{ branchForm.id ? 'Editar sucursal' : 'Nueva sucursal' }}</h3>
        <button class="modal-close" (click)="closeBranch()">&times;</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label class="form-label">Nombre *</label>
          <input class="form-control" [(ngModel)]="branchForm.name" placeholder="Ej: Sucursal Equipetrol">
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Ciudad *</label>
            <input class="form-control" [(ngModel)]="branchForm.city" placeholder="Santa Cruz">
          </div>
          <div class="form-group">
            <label class="form-label">Teléfono</label>
            <input class="form-control" [(ngModel)]="branchForm.phone" placeholder="+591 3 345 2233">
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Dirección</label>
          <input class="form-control" [(ngModel)]="branchForm.address" placeholder="Av. San Martín 320">
        </div>
      </div>
      <div class="modal-foot">
        <button class="btn btn-outline" (click)="closeBranch()">Cancelar</button>
        <button class="btn btn-accent" (click)="saveBranch()" [disabled]="!branchForm.name.trim() || !branchForm.city.trim()">Guardar sucursal</button>
      </div>
    </div>
  </div>
  `,
  styles: ['.text-right { text-align: right; }'],
})
export class AdminComponent implements OnInit {
  tab: Tab = 'products';
  imgFallback =
    'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&q=80&w=600';

  products: Product[] = [];
  branches: Branch[] = [];
  productsLoading = false;

  categories: MetadataItem[] = [];
  seasons: MetadataItem[] = [];
  sizes: MetadataItem[] = [];
  colors: MetadataItem[] = [];
  providers: MetadataItem[] = [];

  prodModalOpen = false;
  productForm: ProductForm = this.emptyProductForm();
  variants: ProductVariant[] = [];
  variantForm: VariantForm = { size_id: null, color_id: null, sku: '', stock: 0 };

  branchModalOpen = false;
  branchForm: BranchForm = this.emptyBranchForm();

  refForms = [
    { key: 'categories' as const, label: 'Categorías', placeholder: 'Ej: Mujer', input: '', items: [] as MetadataItem[] },
    { key: 'seasons' as const, label: 'Temporadas', placeholder: 'Ej: Otoño-Invierno 2026', input: '', items: [] as MetadataItem[] },
    { key: 'sizes' as const, label: 'Tallas', placeholder: 'Ej: S', input: '', items: [] as MetadataItem[] },
    { key: 'colors' as const, label: 'Colores', placeholder: 'Ej: Negro', input: '', items: [] as MetadataItem[] },
    { key: 'providers' as const, label: 'Proveedores', placeholder: 'Ej: Confex S.R.L.', input: '', items: [] as MetadataItem[] },
  ];

  private stockMap = new Map<number, number>();

  constructor(private api: ApiService, private toast: ToastService) {}

  ngOnInit(): void {
    this.loadAll();
  }

  private loadAll(): void {
    this.loadProducts();
    this.loadBranches();
    this.api.getCategories().subscribe({ next: (r) => (this.categories = r) });
    this.api.getSeasons().subscribe({ next: (r) => (this.seasons = r) });
    this.api.getSizes().subscribe({ next: (r) => (this.sizes = r) });
    this.api.getColors().subscribe({ next: (r) => (this.colors = r) });
    this.api.getProviders().subscribe({ next: (r) => (this.providers = r) });

    this.refForms.forEach((ref) => {
      this.api[`get${this.cap(ref.key)}` as 'getCategories']().subscribe({
        next: (r) => (ref.items = r as MetadataItem[]),
      });
    });
  }

  private cap(s: string): string {
    return s.charAt(0).toUpperCase() + s.slice(1);
  }

  loadProducts(): void {
    this.productsLoading = true;
    this.stockMap.clear();
    this.api.getProducts().subscribe({
      next: (res) => {
        this.products = res;
        res.forEach((p) => {
          this.api.getVariants(p.id).subscribe({
            next: (vs) => this.stockMap.set(p.id, vs.reduce((acc, v) => acc + v.stock, 0)),
          });
        });
        this.productsLoading = false;
      },
      error: () => (this.productsLoading = false),
    });
  }

  loadBranches(): void {
    this.api.getBranches().subscribe({ next: (res) => (this.branches = res) });
  }

  stockByProduct(id: number): number {
    return this.stockMap.get(id) ?? 0;
  }

  imgFallbackError(e: Event): void {
    (e.target as HTMLImageElement).src = this.imgFallback;
  }

  // ----------------------------------------------------------------
  // Productos
  // ----------------------------------------------------------------
  private emptyProductForm(): ProductForm {
    return { id: null, name: '', description: '', base_price: 0, image_url: '', category_id: null, season_id: null, provider_id: null };
  }

  openProduct(p?: Product): void {
    this.variants = [];
    this.variantForm = { size_id: null, color_id: null, sku: '', stock: 0 };
    if (p) {
      this.productForm = {
        id: p.id,
        name: p.name,
        description: p.description || '',
        base_price: p.base_price,
        image_url: p.image_url || '',
        category_id: p.category?.id ?? null,
        season_id: p.season?.id ?? null,
        provider_id: null,
      };
      this.api.getVariants(p.id).subscribe({ next: (r) => (this.variants = r) });
    } else {
      this.productForm = this.emptyProductForm();
    }
    this.prodModalOpen = true;
  }

  closeProduct(): void {
    this.prodModalOpen = false;
  }

  saveProduct(): void {
    const data = {
      name: this.productForm.name.trim(),
      description: this.productForm.description || null,
      base_price: this.productForm.base_price,
      image_url: this.productForm.image_url.trim() || null,
      category_id: this.productForm.category_id,
      season_id: this.productForm.season_id,
      provider_id: this.productForm.provider_id,
    };
    const op = this.productForm.id
      ? this.api.updateProduct(this.productForm.id, data)
      : this.api.createProduct(data);
    op.subscribe({
      next: () => {
        this.toast.success(this.productForm.id ? 'Producto actualizado.' : 'Producto creado.');
        this.closeProduct();
        this.loadProducts();
      },
    });
  }

  deleteProduct(p: Product): void {
    if (!confirm(`¿Eliminar "${p.name}"? Esto quitará el producto del catálogo.`)) return;
    this.api.deleteProduct(p.id).subscribe({
      next: () => {
        this.toast.success('Producto eliminado.');
        this.loadProducts();
      },
    });
  }

  addVariant(): void {
    if (!this.productForm.id || !this.variantForm.size_id || !this.variantForm.color_id || !this.variantForm.sku.trim()) return;
    this.api
      .createVariant(this.productForm.id, {
        size_id: this.variantForm.size_id,
        color_id: this.variantForm.color_id,
        sku: this.variantForm.sku.trim().toUpperCase(),
        stock: this.variantForm.stock,
      })
      .subscribe({
        next: (v) => {
          this.variants = [...this.variants, v];
          this.variantForm = { size_id: null, color_id: null, sku: '', stock: 0 };
          this.toast.success('Variante agregada.');
        },
      });
  }

  deleteVariant(v: ProductVariant): void {
    if (!confirm('¿Quitar esta variante?')) return;
    this.api.deleteVariant(v.id).subscribe({
      next: () => {
        this.variants = this.variants.filter((x) => x.id !== v.id);
        this.toast.success('Variante eliminada.');
      },
    });
  }

  // ----------------------------------------------------------------
  // Sucursales
  // ----------------------------------------------------------------
  private emptyBranchForm(): BranchForm {
    return { id: null, name: '', city: '', address: '', phone: '' };
  }

  openBranch(b?: Branch): void {
    this.branchForm = b
      ? { id: b.id, name: b.name, city: b.city, address: b.address || '', phone: b.phone || '' }
      : this.emptyBranchForm();
    this.branchModalOpen = true;
  }

  closeBranch(): void {
    this.branchModalOpen = false;
  }

  saveBranch(): void {
    const data = {
      name: this.branchForm.name.trim(),
      city: this.branchForm.city.trim(),
      address: this.branchForm.address.trim() || undefined,
      phone: this.branchForm.phone.trim() || undefined,
    };
    const op = this.branchForm.id
      ? this.api.updateBranch(this.branchForm.id, data)
      : this.api.createBranch(data);
    op.subscribe({
      next: () => {
        this.toast.success(this.branchForm.id ? 'Sucursal actualizada.' : 'Sucursal creada.');
        this.closeBranch();
        this.loadBranches();
      },
    });
  }

  deleteBranch(b: Branch): void {
    if (!confirm(`¿Eliminar "${b.name}"?`)) return;
    this.api.deleteBranch(b.id).subscribe({
      next: () => {
        this.toast.success('Sucursal eliminada.');
        this.loadBranches();
      },
    });
  }

  // ----------------------------------------------------------------
  // Catálogo
  // ----------------------------------------------------------------
  addRef(ref: (typeof this.refForms)[number]): void {
    const name = ref.input.trim();
    if (!name) return;
    let op: import('rxjs').Observable<MetadataItem>;
    switch (ref.key) {
      case 'categories':
        op = this.api.createCategory(name);
        break;
      case 'seasons':
        op = this.api.createSeason(name);
        break;
      case 'sizes':
        op = this.api.createSize(name);
        break;
      case 'colors':
        op = this.api.createColor(name);
        break;
      case 'providers':
        op = this.api.createProvider(name);
        break;
    }
    op.subscribe({
      next: (item) => {
        ref.items = [...ref.items, item];
        ref.input = '';
        this.toast.success(`${ref.label.slice(0, -1)} "${name}" agregado.`);
      },
    });
  }
}