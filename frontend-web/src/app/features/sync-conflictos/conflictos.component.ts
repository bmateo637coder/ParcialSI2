import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-conflictos',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './conflictos.component.html'
})
export class ConflictosComponent implements OnInit {
  private http = inject(HttpClient);
  conflictos: any[] = [];
  cargando = false;

  ngOnInit(): void {
    this.cargar();
  }

  cargar() {
    this.cargando = true;
    this.http.get<any[]>(`${environment.apiUrl}/sync/conflictos?solo_pendientes=true`).subscribe({
      next: (res) => {
        this.conflictos = res.map((c) => ({
          ...c,
          cantidadAjuste: c.stock_disponible ?? c.cantidad_solicitada ?? 0
        }));
        this.cargando = false;
      },
      error: () => { this.cargando = false; }
    });
  }

  resolver(conflicto: any, accion: 'RECHAZAR' | 'AJUSTAR_CANTIDAD') {
    const cantidad = Number(conflicto.cantidadAjuste ?? 0);
    if (accion === 'AJUSTAR_CANTIDAD' && (!cantidad || cantidad <= 0)) {
      alert('Ingrese una cantidad mayor a cero');
      return;
    }

    this.http.post(
      `${environment.apiUrl}/sync/conflictos/${conflicto.id}/resolver`,
      { accion, cantidad_aceptada: accion === 'AJUSTAR_CANTIDAD' ? cantidad : null }
    ).subscribe({
      next: () => this.cargar(),
      error: (err) => alert(err?.error?.detail || 'Error al resolver')
    });
  }
}
