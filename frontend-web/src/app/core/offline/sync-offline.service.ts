import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { dbOffline, OperacionLocal } from './offline-db.service';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class SyncOfflineService {
  private http = inject(HttpClient);

  async registrarVentaOffline(venta: Partial<OperacionLocal>): Promise<string> {
    const uuid = await dbOffline.agregarOperacion({
      ...venta,
      tipoOperacion: 'VENTA_CONTADO'
    });
    return uuid;
  }

  async registrarReservaOffline(reserva: Partial<OperacionLocal>): Promise<string> {
    const uuid = await dbOffline.agregarOperacion({
      ...reserva,
      tipoOperacion: 'RESERVA'
    });
    return uuid;
  }

  async sincronizar(): Promise<any> {
    const pendientes = await dbOffline.obtenerPendientes();
    if (pendientes.length === 0) {
      return { mensaje: 'Sin operaciones pendientes' };
    }

    const operaciones = pendientes.map((p) => ({
      uuid: p.uuid,
      tipo_operacion: p.tipoOperacion,
      sucursal_id: p.sucursalId,
      usuario_id: p.usuarioId,
      fecha_local: p.fechaLocal,
      cliente_id: p.clienteId,
      items: p.items,
      total: p.total,
      forma_pago: p.formaPago,
      origen: 'OFFLINE'
    }));

    for (const p of pendientes) {
      await dbOffline.marcarEnviada(p.uuid);
    }

    const resp = await this.http.post(`${environment.apiUrl}/sync`, { operaciones }).toPromise();
    return resp;
  }

  async obtenerPendientes(): Promise<OperacionLocal[]> {
    return dbOffline.obtenerPendientes();
  }
}
