import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService, Branch, Product, ProductVariant, MetadataItem, User, Proposal } from './api.service';
import { CommonModule } from '@angular/common';
import { ToastService } from './toast.service';

type Tab = 'products' | 'branches' | 'catalog' | 'users' | 'inventory' | 'providers';

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

interface UserForm {
  id: number | null;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  password: string;
  role_id: number | null;
  is_active: boolean;
}

interface InventoryRow {
  id: number;
  variant_id: number;
  branch_id: number;
  available: number;
  product_id: number;
  product_name: string;
  image_url?: string | null;
  sku: string;
  size_name?: string | null;
  color_name?: string | null;
  branch_name?: string | null;
  city?: string | null;
}

interface InventoryMovementRow {
  id: number;
  inventory_id: number;
  movement_type: string;
  quantity: number;
  reason?: string | null;
  user_name?: string | null;
  created_at?: string | null;
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
      <button class="admin-tab" [class.active]="tab === 'users'" (click)="tab = 'users'">Usuarios</button>
      <button class="admin-tab" [class.active]="tab === 'inventory'" (click)="tab = 'inventory'">Inventario</button>
      <button class="admin-tab" [class.active]="tab === 'providers'" (click)="tab = 'providers'; loadProviderTab()">Proveedores</button>
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

    <!-- ============ USUARIOS (CU4) ============ -->
    <section *ngIf="tab === 'users'">
      <div class="toolbar">
        <div>
          <h2>Usuarios y roles</h2>
          <p style="color:var(--muted); font-size:.9rem; margin-top:.25rem;">Gestiona cuentas del sistema: crea, edita roles y desactiva usuarios.</p>
        </div>
        <button class="btn btn-accent" (click)="openUser()">+ Nuevo usuario</button>
      </div>

      <div style="display:flex; gap:.5rem; margin-bottom:1rem; flex-wrap:wrap;">
        <input class="form-control" [(ngModel)]="userSearch" (keyup.enter)="loadUsers()" placeholder="Buscar por nombre o correo…" style="max-width:300px;">
        <select class="form-control" [(ngModel)]="userRoleFilter" (change)="loadUsers()" style="max-width:200px;">
          <option [ngValue]="null">Todos los roles</option>
          <option *ngFor="let r of roles" [ngValue]="r.id">{{ r.name }}</option>
        </select>
        <button class="btn btn-outline" (click)="loadUsers()">Filtrar</button>
      </div>

      <div *ngIf="usersLoading" class="skeleton" style="height:60px;"></div>
      <div class="empty-state" *ngIf="!usersLoading && !users.length">No hay usuarios que coincidan.</div>
      <div class="table-wrap" *ngIf="!usersLoading && users.length">
        <table class="table">
          <thead>
            <tr><th>Usuario</th><th>Correo</th><th>Teléfono</th><th>Rol</th><th>Estado</th><th class="text-right">Acciones</th></tr>
          </thead>
          <tbody>
            <tr *ngFor="let u of users">
              <td><strong>{{ u.first_name }} {{ u.last_name }}</strong></td>
              <td>{{ u.email }}</td>
              <td>{{ u.phone || '—' }}</td>
              <td><span class="badge badge-info">{{ u.role_name }}</span></td>
              <td>
                <span class="badge badge-success" *ngIf="u.is_active">Activo</span>
                <span class="badge badge-danger" *ngIf="!u.is_active">Inactivo</span>
              </td>
              <td>
                <div class="actions">
                  <button class="btn btn-outline btn-sm" (click)="openUser(u)">Editar</button>
                  <button class="btn btn-danger btn-sm" *ngIf="u.is_active" (click)="deactivateUser(u)" [disabled]="u.id === currentUserId">Desactivar</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- ============ INVENTARIO (CU21) ============ -->
    <section *ngIf="tab === 'inventory'">
      <div class="toolbar">
        <div>
          <h2>Inventario por sucursal</h2>
          <p style="color:var(--muted); font-size:.9rem; margin-top:.25rem;">Ajusta stock y registra movimientos (INGRESO, SALIDA, AJUSTE, DEVOLUCION).</p>
        </div>
        <label class="checkbox-inline" style="align-items:center; gap:.5rem;">
          <input type="checkbox" [(ngModel)]="lowStockOnly" (change)="loadInventory()"> Solo stock bajo
        </label>
      </div>

      <div style="display:flex; gap:.5rem; margin-bottom:1rem; flex-wrap:wrap;">
        <select class="form-control" [(ngModel)]="inventoryBranchFilter" (change)="loadInventory()" style="max-width:280px;">
          <option [ngValue]="null">Todas las sucursales</option>
          <option *ngFor="let b of branches" [ngValue]="b.id">{{ b.name }}</option>
        </select>
        <span class="badge badge-info" *ngIf="inventory.length"> {{ inventory.length }} registros </span>
      </div>

      <div *ngIf="inventoryLoading" class="skeleton" style="height:60px;"></div>
      <div class="empty-state" *ngIf="!inventoryLoading && !inventory.length">No hay registros de inventario. Agrega stock desde un producto.</div>
      <div class="table-wrap" *ngIf="!inventoryLoading && inventory.length">
        <table class="table">
          <thead>
            <tr><th>Producto</th><th>Variante</th><th>Sucursal</th><th>Stock</th><th class="text-right">Acciones</th></tr>
          </thead>
          <tbody>
            <tr *ngFor="let inv of inventory">
              <td><img class="product-img-thumb" [src]="inv.image_url || imgFallback" width="36" height="46" style="object-fit:cover; border-radius:6px;" (error)="imgFallbackError($event)"> {{ inv.product_name }}</td>
              <td>{{ inv.size_name }} / {{ inv.color_name }} <span style="color:var(--muted);">({{ inv.sku }})</span></td>
              <td>{{ inv.branch_name }} <span style="color:var(--muted);">— {{ inv.city }}</span></td>
              <td>
                <span class="v-tags" [class.stock-ok]="inv.available > 10" [class.stock-low]="inv.available > 0 && inv.available <= 10" [class.stock-out]="inv.available === 0">{{ inv.available }}</span>
              </td>
              <td>
                <div class="actions">
                  <button class="btn btn-outline btn-sm" (click)="openAdjust(inv)">Ajustar stock</button>
                  <button class="btn btn-outline btn-sm" (click)="openMovementFor(inv)">+ Movimiento</button>
                  <button class="btn btn-outline btn-sm" (click)="showMovementsFor(inv)">Historial</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="card" style="margin-top:1.5rem;" *ngIf="selectedInventory">
        <h3 style="margin-bottom:.5rem;">Movimientos — {{ selectedInventory.product_name }} ({{ selectedInventory.size_name }} / {{ selectedInventory.color_name }})</h3>
        <div class="table-wrap" *ngIf="movements.length">
          <table class="table">
            <thead>
              <tr><th>Fecha</th><th>Tipo</th><th>Cantidad</th><th>Motivo</th><th>Autor</th></tr>
            </thead>
            <tbody>
              <tr *ngFor="let m of movements">
                <td>{{ m.created_at ? (m.created_at | date: 'd MMM yyyy HH:mm') : '—' }}</td>
                <td><span class="badge" [class.badge-success]="m.quantity > 0" [class.badge-danger]="m.quantity < 0">{{ m.movement_type }}</span></td>
                <td><strong [class]="m.quantity >= 0 ? 'stock-ok' : 'stock-out'">{{ m.quantity > 0 ? '+' : '' }}{{ m.quantity }}</strong></td>
                <td>{{ m.reason || '—' }}</td>
                <td>{{ m.user_name || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="empty-state" *ngIf="!movements.length" style="padding:1.5rem;">Sin movimientos registrados aún.</div>
        <div style="margin-top:1rem;">
          <button class="btn btn-outline btn-sm" (click)="openMovementFor(selectedInventory)">+ Registrar movimiento</button>
        </div>
      </div>
    </section>

    <!-- ============ PROVEEDORES (CU28/CU29) ============ -->
    <section *ngIf="tab === 'providers'">
      <div class="toolbar">
        <h2>Vincular cuenta de proveedor</h2>
      </div>
      <div class="form-group" style="max-width:420px;">
        <label class="form-label">Usuario con rol Proveedor</label>
        <select class="form-control" [(ngModel)]="providerLinkUserId">
          <option [ngValue]="null">— Elegir usuario —</option>
          <option *ngFor="let u of providerUsers" [ngValue]="u.id">{{ u.first_name }} {{ u.last_name }} ({{ u.email }})</option>
        </select>
      </div>
      <div class="form-group" style="max-width:420px;">
        <label class="form-label">Empresa proveedora</label>
        <select class="form-control" [(ngModel)]="providerLinkId">
          <option [ngValue]="null">— Elegir empresa —</option>
          <option *ngFor="let pv of providers" [ngValue]="pv.id">{{ pv.name }}</option>
        </select>
      </div>
      <button class="btn btn-accent" (click)="linkProviderAccount()" [disabled]="!providerLinkUserId || !providerLinkId">Vincular</button>

      <div class="toolbar" style="margin-top:2rem;">
        <h2>Propuestas de productos (CU28)</h2>
      </div>
      <div class="empty-state" *ngIf="!proposals.length">Sin propuestas pendientes ni procesadas.</div>
      <div class="table-wrap" *ngIf="proposals.length">
        <table class="table">
          <thead>
            <tr><th>Propuesta</th><th>Proveedor</th><th>Precio base</th><th>Estado</th><th class="text-right">Acciones</th></tr>
          </thead>
          <tbody>
            <tr *ngFor="let pr of proposals">
              <td>
                <strong>{{ pr.name }}</strong>
                <div style="font-size:.8rem; color:var(--muted);">{{ pr.description || 'Sin descripción' }}</div>
                <div *ngIf="pr.admin_comment" style="font-size:.8rem; color:var(--muted); font-style:italic;">{{ pr.admin_comment }}</div>
              </td>
              <td>{{ pr.provider_name || '#' + pr.provider_id }}</td>
              <td>Bs. {{ pr.base_price | number: '1.2-2' }}</td>
              <td>
                <span class="badge"
                      [class.badge-warn]="pr.status === 'PENDIENTE'"
                      [class.badge-accent]="pr.status === 'APROBADA'"
                      [class.badge-muted]="pr.status === 'RECHAZADA'">
                  {{ pr.status }}
                </span>
              </td>
              <td>
                <div class="actions" *ngIf="pr.status === 'PENDIENTE'">
                  <button class="btn btn-accent btn-sm" (click)="reviewProposal(pr, 'approve')">Aprobar</button>
                  <button class="btn btn-danger btn-sm" (click)="reviewProposal(pr, 'reject')">Rechazar</button>
                </div>
                <span class="text-right" style="color:var(--muted);" *ngIf="pr.status !== 'PENDIENTE'">—</span>
              </td>
            </tr>
          </tbody>
        </table>
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

  <!-- MODAL USUARIO -->
  <div class="modal-backdrop" *ngIf="userModalOpen" (click.self)="closeUser()">
    <div class="modal">
      <div class="modal-head">
        <h3>{{ userForm.id ? 'Editar usuario' : 'Nuevo usuario' }}</h3>
        <button class="modal-close" (click)="closeUser()">&times;</button>
      </div>
      <div class="modal-body">
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Nombre *</label>
            <input class="form-control" [(ngModel)]="userForm.first_name" placeholder="María">
          </div>
          <div class="form-group">
            <label class="form-label">Apellido *</label>
            <input class="form-control" [(ngModel)]="userForm.last_name" placeholder="Gonzales">
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Correo electrónico *</label>
          <input class="form-control" type="email" [(ngModel)]="userForm.email" placeholder="ejemplo@correo.com">
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Rol *</label>
            <select class="form-control" [(ngModel)]="userForm.role_id">
              <option *ngFor="let r of roles" [ngValue]="r.id">{{ r.name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Teléfono</label>
            <input class="form-control" [(ngModel)]="userForm.phone" placeholder="+591 ...">
          </div>
        </div>
        <div class="form-group" *ngIf="!userForm.id">
          <label class="form-label">Contraseña *</label>
          <input class="form-control" type="password" [(ngModel)]="userForm.password" placeholder="Mínimo 6 caracteres">
        </div>
        <div class="form-group" *ngIf="userForm.id">
          <label class="form-label">Nueva contraseña (opcional)</label>
          <input class="form-control" type="password" [(ngModel)]="userForm.password" placeholder="Déjalo vacío para no cambiarla">
        </div>
        <div class="form-group checkbox-inline" *ngIf="userForm.id && userForm.id !== currentUserId">
          <label style="display:flex; align-items:center; gap:.5rem; cursor:pointer;">
            <input type="checkbox" [(ngModel)]="userForm.is_active"> Usuario activo
          </label>
        </div>
      </div>
      <div class="modal-foot">
        <button class="btn btn-outline" (click)="closeUser()">Cancelar</button>
        <button class="btn btn-accent" (click)="saveUser()" [disabled]="!userForm.first_name.trim() || !userForm.last_name.trim() || !userForm.email || !userForm.role_id || (!userForm.id && (userForm.password || '').length < 6)">
          Guardar usuario
        </button>
      </div>
    </div>
  </div>

  <!-- MODAL AJUSTAR STOCK -->
  <div class="modal-backdrop" *ngIf="adjustModalOpen" (click.self)="closeAdjust()">
    <div class="modal">
      <div class="modal-head">
        <h3>Ajustar stock</h3>
        <button class="modal-close" (click)="closeAdjust()">&times;</button>
      </div>
      <div class="modal-body">
        <p style="color:var(--muted); font-size:.9rem;" *ngIf="adjustTarget">
          {{ adjustTarget.product_name }} — {{ adjustTarget.size_name }} / {{ adjustTarget.color_name }} ·
          {{ adjustTarget.branch_name }} · Actual: <strong>{{ adjustTarget.available }}</strong>
        </p>
        <div class="form-group">
          <label class="form-label">Nuevo stock</label>
          <input class="form-control" type="number" min="0" [(ngModel)]="adjustValue">
        </div>
      </div>
      <div class="modal-foot">
        <button class="btn btn-outline" (click)="closeAdjust()">Cancelar</button>
        <button class="btn btn-accent" (click)="saveAdjust()" [disabled]="adjustValue === null || adjustValue === undefined || adjustValue < 0">Guardar</button>
      </div>
    </div>
  </div>

  <!-- MODAL MOVIMIENTO -->
  <div class="modal-backdrop" *ngIf="movementModalOpen" (click.self)="closeMovement()">
    <div class="modal">
      <div class="modal-head">
        <h3>Registrar movimiento</h3>
        <button class="modal-close" (click)="closeMovement()">&times;</button>
      </div>
      <div class="modal-body">
        <p style="color:var(--muted); font-size:.9rem;" *ngIf="movementTarget">
          {{ movementTarget.product_name }} — {{ movementTarget.size_name }} / {{ movementTarget.color_name }} ·
          {{ movementTarget.branch_name }} · Stock: <strong>{{ movementTarget.available }}</strong>
        </p>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Tipo</label>
            <select class="form-control" [(ngModel)]="movementForm.type">
              <option value="INGRESO">INGRESO (entrada)</option>
              <option value="SALIDA">SALIDA (salida)</option>
              <option value="AJUSTE">AJUSTE (corrección)</option>
              <option value="DEVOLUCION">DEVOLUCION (entrada)</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Cantidad</label>
            <input class="form-control" type="number" min="1" [(ngModel)]="movementForm.qty" placeholder="1">
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Motivo</label>
          <input class="form-control" [(ngModel)]="movementForm.reason" placeholder="Ej: Llegada de proveedor">
        </div>
        <p class="form-error" *ngIf="movementError">{{ movementError }}</p>
      </div>
      <div class="modal-foot">
        <button class="btn btn-outline" (click)="closeMovement()">Cancelar</button>
        <button class="btn btn-accent" (click)="saveMovement()" [disabled]="!movementForm.qty || movementForm.qty < 1">Guardar movimiento</button>
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

  // --- Usuarios (CU4) ---
  users: User[] = [];
  usersLoading = false;
  roles: { id: number; name: string; description?: string }[] = [];
  userSearch = '';
  userRoleFilter: number | null = null;
  userModalOpen = false;
  userForm: UserForm = this.emptyUserForm();

  // --- Inventario (CU21) ---
  inventory: InventoryRow[] = [];
  inventoryLoading = false;
  lowStockOnly = false;
  inventoryBranchFilter: number | null = null;
  selectedInventory: InventoryRow | null = null;
  movements: InventoryMovementRow[] = [];
  adjustModalOpen = false;
  adjustTarget: InventoryRow | null = null;
  adjustValue = 0;
  movementModalOpen = false;
  movementTarget: InventoryRow | null = null;
  movementForm = { type: 'INGRESO', qty: 1, reason: '' };
  movementError = '';

  // --- Proveedores (CU28/CU29) ---
  providerUsers: User[] = [];
  providerLinkUserId: number | null = null;
  providerLinkId: number | null = null;
  proposals: Proposal[] = [];

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

  get currentUserId(): number {
    return this.api.currentUser.value?.id ?? 0;
  }

  private loadAll(): void {
    this.loadProducts();
    this.loadBranches();
    this.loadUsers();
    this.loadRoles();
    this.loadInventory();
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
  // Usuarios y roles (CU4)
  // ----------------------------------------------------------------
  private emptyUserForm(): UserForm {
    return { id: null, first_name: '', last_name: '', email: '', phone: '', password: '', role_id: null, is_active: true };
  }

  loadRoles(): void {
    this.api.getRoles().subscribe({ next: (r) => (this.roles = r) });
  }

  loadUsers(): void {
    this.usersLoading = true;
    this.api
      .getUsers({
        q: this.userSearch,
        role_id: this.userRoleFilter ?? undefined,
      })
      .subscribe({
        next: (r) => {
          this.users = r;
          this.usersLoading = false;
        },
        error: () => (this.usersLoading = false),
      });
  }

  openUser(u?: User): void {
    this.userForm = u
      ? {
          id: u.id,
          first_name: u.first_name,
          last_name: u.last_name,
          email: u.email,
          phone: u.phone || '',
          password: '',
          role_id: this.roles.find((r) => r.name === u.role_name)?.id ?? null,
          is_active: u.is_active,
        }
      : this.emptyUserForm();
    this.userModalOpen = true;
  }

  closeUser(): void {
    this.userModalOpen = false;
  }

  saveUser(): void {
    const form = this.userForm;
    if (!form.first_name.trim() || !form.last_name.trim() || !form.email.trim() || !form.role_id) return;
    if (!form.id && (form.password || '').length < 6) return;

    const base = {
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      email: form.email.trim(),
      phone: form.phone.trim() || undefined,
      role_id: form.role_id,
    };
    const op = form.id
      ? this.api.updateUser(form.id, {
          ...base,
          ...(form.password ? { password: form.password } : {}),
          is_active: form.id !== this.currentUserId ? form.is_active : undefined,
        } as any)
      : this.api.createUser({ ...base, password: form.password });

    op.subscribe({
      next: () => {
        this.toast.success(form.id ? 'Usuario actualizado.' : 'Usuario creado.');
        this.closeUser();
        this.loadUsers();
      },
    });
  }

  deactivateUser(u: User): void {
    if (!confirm(`¿Desactivar a ${u.first_name} ${u.last_name}? No podrá iniciar sesión.`)) return;
    this.api.deactivateUser(u.id).subscribe({
      next: () => {
        this.toast.success('Usuario desactivado.');
        this.loadUsers();
      },
    });
  }

  // ----------------------------------------------------------------
  // Inventario y movimientos (CU21)
  // ----------------------------------------------------------------
  loadInventory(): void {
    this.inventoryLoading = true;
    this.api
      .getInventory({
        branch_id: this.inventoryBranchFilter ?? undefined,
        low_stock_only: this.lowStockOnly,
      })
      .subscribe({
        next: (r) => {
          this.inventory = r as InventoryRow[];
          this.inventoryLoading = false;
        },
        error: () => (this.inventoryLoading = false),
      });
  }

  openAdjust(inv: InventoryRow): void {
    this.adjustTarget = inv;
    this.adjustValue = inv.available;
    this.adjustModalOpen = true;
  }

  closeAdjust(): void {
    this.adjustModalOpen = false;
    this.adjustTarget = null;
  }

  saveAdjust(): void {
    if (!this.adjustTarget || this.adjustValue < 0) return;
    const targetId = this.adjustTarget.id;
    const targetRef = this.adjustTarget;
    this.api.updateInventory(targetId, { available: this.adjustValue }).subscribe({
      next: () => {
        this.toast.success('Stock ajustado.');
        this.closeAdjust();
        this.loadInventory();
        if (this.selectedInventory?.id === targetId) this.showMovementsFor(targetRef);
      },
    });
  }

  openMovementFor(inv: InventoryRow): void {
    this.movementTarget = inv;
    this.movementForm = { type: 'INGRESO', qty: 1, reason: '' };
    this.movementError = '';
    this.movementModalOpen = true;
  }

  closeMovement(): void {
    this.movementModalOpen = false;
    this.movementTarget = null;
  }

  saveMovement(): void {
    if (!this.movementTarget || !this.movementForm.qty || this.movementForm.qty < 1) return;
    const targetId = this.movementTarget.id;
    const qty = Math.floor(this.movementForm.qty);
    const type = this.movementForm.type;
    // Los tipos de salida se envían como delta negativo.
    const delta = type === 'SALIDA' || type === 'RESERVA' ? -qty : qty;
    this.api
      .createInventoryMovement({
        inventory_id: targetId,
        movement_type: type,
        quantity: delta,
        reason: this.movementForm.reason.trim() || undefined,
      })
      .subscribe({
        next: () => {
          this.toast.success('Movimiento registrado.');
          this.closeMovement();
          this.loadInventory();
          if (this.selectedInventory?.id === targetId) this.showMovementsFor(this.selectedInventory);
        },
        error: (err) => {
          this.movementError = err?.error?.detail || 'No se pudo registrar el movimiento.';
        },
      });
  }

  showMovementsFor(inv: InventoryRow): void {
    this.selectedInventory = inv;
    this.movements = [];
    this.api.getInventoryMovements({ inventory_id: inv.id }).subscribe({
      next: (r) => (this.movements = r as InventoryMovementRow[]),
    });
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

  // ----------------------------------------------------------------
  // Proveedores (CU28/CU29)
  // ----------------------------------------------------------------
  loadProviderTab(): void {
    this.loadProviderUsers();
    this.loadProposals();
  }

  loadProviderUsers(): void {
    this.api.getUsers({ q: '' }).subscribe({
      next: (us) => {
        this.providerUsers = us.filter((u) => u.role_name === 'Proveedor');
      },
    });
  }

  loadProposals(): void {
    this.api.getProposals().subscribe({
      next: (pr) => (this.proposals = pr),
      error: () => this.toast.error('No se pudieron cargar las propuestas.'),
    });
  }

  linkProviderAccount(): void {
    if (!this.providerLinkUserId || !this.providerLinkId) return;
    this.api
      .linkProviderAccount({ user_id: this.providerLinkUserId, provider_id: this.providerLinkId })
      .subscribe({
        next: () => {
          this.toast.success('Cuenta de proveedor vinculada.');
          this.providerLinkUserId = null;
          this.providerLinkId = null;
        },
        error: (err) =>
          this.toast.error(
            (err?.error?.detail as string) || 'No se pudo vincular. Verifica que el usuario no esté ya vinculado.'
          ),
      });
  }

  reviewProposal(pr: Proposal, action: 'approve' | 'reject'): void {
    const comment = prompt(
      action === 'approve' ? 'Comentario (opcional):' : 'Motivo del rechazo (opcional):'
    );
    if (comment === null) return;
    const trimmed = comment.trim() || undefined;
    const op = action === 'approve' ? this.api.approveProposal(pr.id, trimmed) : this.api.rejectProposal(pr.id, trimmed);
    op.subscribe({
      next: (updated) => {
        this.toast.success(action === 'approve' ? 'Propuesta aprobada.' : 'Propuesta rechazada.');
        this.proposals = this.proposals.map((x) => (x.id === updated.id ? updated : x));
      },
      error: (err) => this.toast.error((err?.error?.detail as string) || 'Error al procesar la propuesta.'),
    });
  }
}