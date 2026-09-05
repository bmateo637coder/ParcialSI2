
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
