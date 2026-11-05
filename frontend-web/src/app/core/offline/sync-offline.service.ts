import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { dbOffline, OperacionLocal, offlineUser, offlineScope } from './offline-db.service';
import { environment } from '../../../environments/environment';

interface SyncItemResult {
  uuid: string;
  estado: 'CONFIRMADA' | 'RECHAZADA' | 'EN_CONFLICTO';
  mensaje?: string;
}

interface SyncResponse {
  mensaje?: string;
  resultados?: SyncItemResult[];
}

@Injectable({
  providedIn: 'root'
})
export class SyncOfflineService {
  private http = inject(HttpClient);
  private enCurso: Promise<SyncResponse> | null = null;

  private contexto(operacion: Partial<OperacionLocal>): Partial<OperacionLocal> {
    const user = offlineUser();
    return { ...operacion, usuarioId: user?.id, empresaId: user?.empresa_id, formaPago: 'EFECTIVO' };
  }

  async registrarVentaOffline(venta: Partial<OperacionLocal>): Promise<string> {
    return dbOffline.agregarOperacion({
      ...this.contexto(venta),
      tipoOperacion: 'VENTA_CONTADO'
    });
  }

  async registrarReservaOffline(reserva: Partial<OperacionLocal>): Promise<string> {
    return dbOffline.agregarOperacion({
      ...this.contexto(reserva),
      tipoOperacion: 'RESERVA'
    });
  }

  sincronizar(): Promise<SyncResponse> {
    if (!this.enCurso) this.enCurso = this.enviar().finally(() => { this.enCurso = null; });
    return this.enCurso;
  }

  private async enviar(): Promise<SyncResponse> {
    const scope = offlineScope();
    const token = localStorage.getItem('token');
    if (!token || !offlineUser()?.empresa_id) return { mensaje: 'Inicia sesión en tu empresa para sincronizar.' };
    const pendientes = await dbOffline.obtenerPendientes();
    if (pendientes.length === 0) {
      return { mensaje: 'Sin operaciones pendientes' };
    }

    const operaciones = pendientes.slice(0, 200).map((p) => ({
      uuid: p.uuid,
      tipo_operacion: p.tipoOperacion,
      sucursal_id: p.sucursalId,
      usuario_id: p.usuarioId,
      fecha_local: p.fechaLocal,
      cliente_id: p.clienteId,
      items: p.items,
      total: p.total,
      forma_pago: p.formaPago,
      payload_extra: p.payload?.payload ?? {},
      origen: 'OFFLINE'
    }));

    if (scope !== offlineScope()) throw new Error('La sesión cambió. Vuelve a sincronizar.');
    await dbOffline.marcarEnviadas(operaciones.map(op => op.uuid));
    const resp = await firstValueFrom(
      this.http.post<SyncResponse>(`${environment.apiUrl}/sync`, { operaciones }, { headers: { Authorization: `Bearer ${token}` } })
    );

    for (const resultado of resp.resultados ?? []) {
      if (operaciones.some(op => op.uuid === resultado.uuid)) {
        await dbOffline.actualizarEstado(resultado.uuid, resultado.estado, resultado.mensaje, resultado);
      }
    }

    return resp;
  }

  async obtenerPendientes(): Promise<OperacionLocal[]> {
    return dbOffline.obtenerPendientes();
  }

  async obtenerOperaciones(): Promise<OperacionLocal[]> { return dbOffline.obtenerOperaciones(); }

  async sincronizarSiConectado(): Promise<SyncResponse> {
    if (!navigator.onLine) {
      return { mensaje: 'Sin conexión. Se sincronizará al recuperar internet.' };
    }
    return this.sincronizar();
  }
}
