import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SyncOfflineService } from '../../../core/offline/sync-offline.service';

@Component({
  selector: 'app-sync-offline',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './sync.component.html'
})
export class SyncComponent implements OnInit {
  private syncService = inject(SyncOfflineService);
  pendientes: any[] = [];
  resultado: any = null;
  cargando = false;

  async ngOnInit() {
    this.pendientes = await this.syncService.obtenerPendientes();
  }

  async sincronizar() {
    this.cargando = true;
    this.resultado = null;
    try {
      this.resultado = await this.syncService.sincronizar();
      this.pendientes = await this.syncService.obtenerPendientes();
    } catch (e: any) {
      this.resultado = { error: e?.message || 'Error al sincronizar' };
    } finally {
      this.cargando = false;
    }
  }
}
