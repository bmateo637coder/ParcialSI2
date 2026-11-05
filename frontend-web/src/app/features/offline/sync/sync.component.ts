import { Component, OnInit, OnDestroy, inject, NgZone } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SyncOfflineService } from '../../../core/offline/sync-offline.service';
import { ConnectionService } from '../../../core/offline/connection.service';
import { OperacionLocal } from '../../../core/offline/offline-db.service';
import { ApiService } from '../../../api.service';
import { liveQuery } from 'dexie';

@Component({
  selector: 'app-sync',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './sync.component.html',
})
export class SyncComponent implements OnInit, OnDestroy {
  private sync = inject(SyncOfflineService);
  private conn = inject(ConnectionService);
  private api = inject(ApiService);
  private zone = inject(NgZone);
  private changes?: { unsubscribe(): void };

  pendientes: OperacionLocal[] = [];
  resultado: any = null;
  cargando = false;

  get online() {
    return this.conn.online();
  }

  ngOnInit(): void {
    this.changes = liveQuery(() => this.sync.obtenerOperaciones()).subscribe(rows => {
      this.zone.run(() => { this.pendientes = rows; });
    });
  }

  ngOnDestroy(): void { this.changes?.unsubscribe(); }

  async cargar() {
    this.pendientes = await this.sync.obtenerOperaciones();
  }

  async descargar() {
    this.cargando = true;
    try { await this.api.prepararOffline(); this.resultado = { mensaje: 'Catálogo, variantes y sucursales guardados para trabajar sin conexión.' }; }
    catch { this.resultado = { error: 'No se pudo descargar. Comprueba la conexión y vuelve a intentar.' }; }
    finally { this.cargando = false; }
  }

  async sincronizar() {
    this.cargando = true;
    this.resultado = null;
    try {
      this.resultado = await this.sync.sincronizarSiConectado();
      await this.cargar();
    } catch (e: any) {
      this.resultado = { error: e?.message || 'Error al sincronizar' };
    } finally {
      this.cargando = false;
    }
  }
}
