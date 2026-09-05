
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
