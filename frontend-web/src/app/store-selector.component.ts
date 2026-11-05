import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from './api.service';

@Component({
  selector: 'app-store-selector',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <section *ngIf="!api.isAuthenticated" style="max-width:420px; margin:0 auto 1.5rem;">
      <div *ngIf="stores.length" class="form-group">
        <label for="public-store">Tienda</label>
        <select id="public-store" class="form-control" [ngModel]="api.storefrontId"
                (ngModelChange)="selectStore($event)">
          <option *ngFor="let store of stores" [ngValue]="store.id">{{ store.nombre }}</option>
        </select>
      </div>
      <p *ngIf="loading" role="status">Cargando tiendas…</p>
      <p *ngIf="!loading && !failed && !stores.length">No hay tiendas disponibles en este momento.</p>
      <div *ngIf="failed" role="alert">
        <p>No se pudieron cargar las tiendas.</p>
        <button class="btn btn-outline" (click)="load()">Reintentar</button>
      </div>
    </section>
  `,
})
export class StoreSelectorComponent implements OnInit {
  @Output() selected = new EventEmitter<void>();
  stores: { id: number; nombre: string }[] = [];
  loading = false;
  failed = false;

  constructor(public api: ApiService) {}

  ngOnInit(): void {
    if (!this.api.isAuthenticated) this.load();
  }

  load(): void {
    this.loading = true;
    this.failed = false;
    this.api.getTiendas().subscribe({
      next: stores => {
        this.stores = stores;
        this.loading = false;
        const previous = this.api.storefrontId;
        const id = stores.some(store => store.id === previous) ? previous : stores[0]?.id;
        if (id) this.selectStore(id);
        else this.api.storefrontId = null;
      },
      error: () => { this.loading = false; this.failed = true; },
    });
  }

  selectStore(id: number): void {
    if (!this.stores.some(store => store.id === id)) return;
    this.api.storefrontId = id;
    this.selected.emit();
  }
}
