
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
