import os

BASE_DIR = r"d:\A_tareas_u_MATEO\si2\p1\proyecto antigravity\frontend-web\src\app"

def write_file(filename, content):
    with open(os.path.join(BASE_DIR, filename), 'w', encoding='utf-8') as f:
        f.write(content)

# 3. Main App Component
write_file("app.ts", """
import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { ApiService } from './api.service';
import { CommonModule } from '@angular/common';
@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, CommonModule],
  template: `
    <nav class="navbar">
      <a routerLink="/" class="navbar-brand">FASHION STORE</a>
      <div class="nav-links">
        <a routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{exact: true}" class="nav-item">Catálogo</a>
        <a routerLink="/branches" routerLinkActive="active" class="nav-item">Sucursales</a>
        <ng-container *ngIf="api.currentUser | async as user; else guest">
          <a routerLink="/profile" routerLinkActive="active" class="nav-item">Mi Perfil</a>
          <a *ngIf="user.role === 'Administrador'" routerLink="/admin" routerLinkActive="active" class="nav-item">Panel Admin</a>
          <button class="btn btn-outline" style="color:white; border-color:white; padding: 0.5rem 1rem;" (click)="logout()">Salir</button>
        </ng-container>
        <ng-template #guest>
            <a routerLink="/auth" class="btn btn-primary" style="background: white; color: var(--primary);">Ingresar</a>
        </ng-template>
      </div>
    </nav>
    <div class="container">
      <router-outlet></router-outlet>
    </div>
  `
})
export class App {
  constructor(public api: ApiService) {}
  logout() { this.api.logout(); }
}
""")

# 4. Auth Component
write_file("auth.component.ts", """
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from './api.service';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
@Component({
  standalone: true, imports: [FormsModule, CommonModule],
  template: `
    <div class="grid" style="grid-template-columns: 1fr 1fr; align-items: start;">
      <div class="card">
        <h2>Iniciar Sesión</h2>
        <div class="alert alert-danger" *ngIf="loginError">{{loginError}}</div>
        <div class="form-group">
            <label class="form-label">Correo Electrónico</label>
            <input class="form-control" [(ngModel)]="loginData.email" placeholder="ejemplo@correo.com">
        </div>
        <div class="form-group">
            <label class="form-label">Contraseña</label>
            <input class="form-control" type="password" [(ngModel)]="loginData.password" placeholder="Tu contraseña">
        </div>
        <button class="btn btn-primary" style="width: 100%" (click)="login()">Acceder a mi cuenta</button>
      </div>

      <div class="card">
        <h2>Crear Cuenta Nueva</h2>
        <div class="form-group">
            <label class="form-label">Nombre</label>
            <input class="form-control" [(ngModel)]="regData.first_name">
        </div>
        <div class="form-group">
            <label class="form-label">Apellido</label>
            <input class="form-control" [(ngModel)]="regData.last_name">
        </div>
        <div class="form-group">
            <label class="form-label">Correo Electrónico</label>
            <input class="form-control" [(ngModel)]="regData.email">
        </div>
        <div class="form-group">
            <label class="form-label">Contraseña</label>
            <input class="form-control" type="password" [(ngModel)]="regData.password">
        </div>
        <button class="btn btn-outline" style="width: 100%" (click)="register()">Registrarme</button>
      </div>
    </div>
  `
})
export class AuthComponent {
  loginData = {email:'', password:''};
  regData = {first_name:'', last_name:'', email:'', password:''};
  loginError = '';
  constructor(private api: ApiService, private router: Router) {}
  login() {
    this.loginError = '';
    this.api.login(this.loginData).subscribe({
      next: (res: any) => {
        localStorage.setItem('token', res.access_token);
        localStorage.setItem('role', res.role);
        localStorage.setItem('email', this.loginData.email);
        this.api.currentUser.next({token: res.access_token, role: res.role, email: this.loginData.email});
        this.router.navigate(['/']);
      },
      error: (err) => {
        this.loginError = 'Credenciales incorrectas o error en el servidor.';
      }
    });
  }
  register() {
    this.api.register(this.regData).subscribe({
      next: () => alert('Cuenta creada con éxito. Por favor, inicia sesión.'),
      error: () => alert('Error al registrar la cuenta.')
    });
  }
}
""")

# 5. Admin Component
write_file("admin.component.ts", """
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from './api.service';
import { CommonModule } from '@angular/common';
@Component({
  standalone: true, imports: [FormsModule, CommonModule],
  template: `
    <div style="display: flex; justify-content: space-between; align-items:center;">
        <h2>Panel de Administración Global</h2>
        <span class="alert alert-info" style="margin:0; padding:0.5rem;">Modo: Administrador</span>
    </div>
    
    <div class="grid mt-2">
        <!-- Sucursales Admin -->
        <div class="card">
            <h3>Gestión de Sucursales</h3>
            <div class="form-group">
                <label class="form-label">Nombre de la Sucursal</label>
                <input class="form-control" [(ngModel)]="branch.name" placeholder="Ej: Sucursal Equipetrol">
            </div>
            <div class="form-group">
                <label class="form-label">Ciudad</label>
                <input class="form-control" [(ngModel)]="branch.city" placeholder="Ej: Santa Cruz">
            </div>
            <button class="btn btn-primary" (click)="addBranch()">Registrar Sucursal</button>
            
            <table class="table mt-2">
                <thead><tr><th>Nombre</th><th>Ciudad</th></tr></thead>
                <tbody>
                    <tr *ngFor="let b of branches"><td>{{b.name}}</td><td>{{b.city}}</td></tr>
                </tbody>
            </table>
        </div>

        <!-- Productos Admin -->
        <div class="card">
            <h3>Gestión de Productos</h3>
            <div class="form-group">
                <label class="form-label">Nombre del Producto</label>
                <input class="form-control" [(ngModel)]="product.name" placeholder="Ej: Vestido Floral">
            </div>
            <div class="form-group">
                <label class="form-label">Precio Base (Bs.)</label>
                <input class="form-control" [(ngModel)]="product.base_price" type="number">
            </div>
            <button class="btn btn-primary" (click)="addProduct()">Publicar Producto</button>
            
            <table class="table mt-2">
                <thead><tr><th>Producto</th><th>Precio</th></tr></thead>
                <tbody>
                    <tr *ngFor="let p of products"><td>{{p.name}}</td><td>Bs. {{p.base_price}}</td></tr>
                </tbody>
            </table>
        </div>
    </div>
  `
})
export class AdminComponent implements OnInit {
  branch = {name:'', city:''};
  product = {name:'', base_price:0};
  branches: any[] = [];
  products: any[] = [];
  
  constructor(private api: ApiService) {}
  
  ngOnInit() { this.loadData(); }
  
  loadData() {
      this.api.getBranches('').subscribe((res:any) => this.branches = res);
      this.api.getProducts('').subscribe((res:any) => this.products = res);
  }

  addBranch() { 
      this.api.createBranch(this.branch).subscribe(() => { 
          alert('Sucursal registrada correctamente'); 
          this.branch={name:'',city:''};
          this.loadData();
      }); 
  }
  
  addProduct() { 
      this.api.createProduct(this.product).subscribe(() => { 
          alert('Producto publicado en el catálogo'); 
          this.product={name:'',base_price:0};
          this.loadData();
      }); 
  }
}
""")

# 6. Catalog Component
write_file("catalog.component.ts", """
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from './api.service';
import { CommonModule } from '@angular/common';
@Component({
  standalone: true, imports: [FormsModule, CommonModule],
  template: `
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1>Colección de Temporada</h1>
        <p style="color: var(--secondary);">Descubre las últimas tendencias en moda diseñadas para ti.</p>
        
        <div style="max-width: 500px; margin: 1.5rem auto; display:flex; gap:0.5rem;">
            <input class="form-control" [(ngModel)]="q" placeholder="Buscar por nombre, categoría o estilo..." (keyup.enter)="search()">
            <button class="btn btn-primary" (click)="search()">Explorar</button>
        </div>
    </div>

    <div *ngIf="products.length===0" class="text-center" style="padding: 3rem; color: var(--secondary);">
        <i>El catálogo está vacío actualmente. El administrador debe publicar productos.</i>
    </div>

    <div class="grid">
        <div class="product-card" *ngFor="let p of products">
            <!-- Imagen simulada profesional -->
            <img class="product-img" src="https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&q=80&w=400" alt="Prenda">
            <div class="product-details">
                <h3 style="margin-bottom:0.25rem;">{{p.name}}</h3>
                <p style="color:var(--secondary); font-size:0.9rem;">Colección FashionStore</p>
                <div class="product-price">Bs. {{p.base_price.toFixed(2)}}</div>
                <button class="btn btn-outline" style="width:100%; margin-top:1rem;">Ver Disponibilidad</button>
            </div>
        </div>
    </div>
  `
})
export class CatalogComponent implements OnInit {
  q = ''; products: any[] = [];
  constructor(private api: ApiService) {}
  ngOnInit() { this.search(); }
  search() { this.api.getProducts(this.q).subscribe((res:any) => this.products = res); }
}
""")

# 7. Branches Component
write_file("branches.component.ts", """
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from './api.service';
import { CommonModule } from '@angular/common';
@Component({
  standalone: true, imports: [FormsModule, CommonModule],
  template: `
    <h2>Nuestras Sucursales</h2>
    <div style="margin-bottom: 2rem; display:flex; gap: 0.5rem; max-width: 400px;">
        <input class="form-control" [(ngModel)]="city" placeholder="Filtrar por ciudad (Ej: Santa Cruz)" (keyup.enter)="search()">
        <button class="btn btn-primary" (click)="search()">Filtrar</button>
    </div>

    <div *ngIf="branches.length===0" class="alert alert-info">
        No se encontraron sucursales para esta búsqueda.
    </div>

    <div class="grid">
        <div class="card" *ngFor="let b of branches" style="border-top: 4px solid var(--primary);">
            <h3 style="margin-bottom: 0.5rem;">{{b.name}}</h3>
            <p style="color: var(--secondary); margin-bottom: 1rem;">
                <svg style="width:16px; height:16px; vertical-align:middle; margin-right:4px;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
                {{b.city}}
            </p>
            <button class="btn btn-outline" style="width: 100%;">Ver inventario local</button>
        </div>
    </div>
  `
})
export class BranchesComponent implements OnInit {
  city = ''; branches: any[] = [];
  constructor(private api: ApiService) {}
  ngOnInit() { this.search(); }
  search() { this.api.getBranches(this.city).subscribe((res:any) => this.branches = res); }
}
""")

# 8. Profile Component
write_file("profile.component.ts", """
import { Component, OnInit } from '@angular/core';
import { ApiService } from './api.service';
import { CommonModule } from '@angular/common';
@Component({
  standalone: true, imports: [CommonModule],
  template: `
    <h2>Mi Perfil Personal</h2>
    
    <div class="card" style="max-width: 600px; margin: 2rem auto; text-align: center;" *ngIf="user; else loading">
        <div style="width: 80px; height: 80px; background: var(--primary); color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 2rem; font-weight: bold; margin: 0 auto 1.5rem auto;">
            {{user.first_name.charAt(0)}}{{user.last_name.charAt(0)}}
        </div>
        <h3>{{user.first_name}} {{user.last_name}}</h3>
        <p style="color: var(--secondary); margin-bottom: 1rem;">{{user.email}}</p>
        <span class="alert alert-info" style="padding: 0.25rem 0.75rem; border-radius: 99px; font-size: 0.85rem;">
            Rol Asignado: {{role}}
        </span>
        
        <hr style="margin: 2rem 0; border: none; border-top: 1px solid var(--border);">
        <button class="btn btn-outline" style="width: 100%;">Editar Información</button>
    </div>
    
    <ng-template #loading>
        <div class="text-center" style="padding: 3rem; color: var(--secondary);">
            <p *ngIf="!errorMsg">Cargando información del perfil...</p>
            <p *ngIf="errorMsg" style="color: var(--danger);">{{errorMsg}}</p>
        </div>
    </ng-template>
  `
})
export class ProfileComponent implements OnInit {
  user: any;
  role: string = '';
  errorMsg = '';
  constructor(private api: ApiService) {}
  ngOnInit() {
    const email = localStorage.getItem('email');
    this.role = localStorage.getItem('role') || 'Cliente';
    if(email) {
        this.api.getProfile(email).subscribe({
            next: (res:any) => this.user = res,
            error: (err) => this.errorMsg = 'No se pudo cargar el perfil. Por favor vuelve a iniciar sesión.'
        });
    } else {
        this.errorMsg = 'No hay sesión activa.';
    }
  }
}
""")

print("Frontend elegantly styled and scaffolded!")
