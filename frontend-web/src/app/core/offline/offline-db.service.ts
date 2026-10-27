import Dexie, { Table } from 'dexie';
import { v4 as uuidv4 } from 'uuid';

export interface OperacionLocal {
  id?: number;
  uuid: string;
  tipoOperacion: 'VENTA_CONTADO' | 'RESERVA';
  sucursalId: number;
  usuarioId: number;
  empresaId: number;
  fechaLocal: string;
  clienteId?: number;
  items: any[];
  total?: number;
  formaPago?: string;
  estado: 'REGISTRADA_LOCAL' | 'ENVIADA' | 'CONFIRMADA' | 'RECHAZADA' | 'EN_CONFLICTO';
  intentos: number;
  payload?: any;
}

export interface CatalogoLocal {
  id?: number;
  productoId: number;
  varianteId: number;
  sku: string;
  nombreProducto: string;
  precio: number;
  sucursalId: number;
  stockConocido?: number;
  fechaDescarga: string;
}

export class FashionStoreOfflineDB extends Dexie {
  operaciones!: Table<OperacionLocal, number>;
  catalogo!: Table<CatalogoLocal, number>;

  constructor() {
    super('FashionStoreOffline');
    this.version(1).stores({
      operaciones: '++id, uuid, estado, tipoOperacion, sucursalId, fechaLocal',
      catalogo: '++id, [productoId+varianteId+sucursalId], sku, sucursalId'
    });
  }

  async agregarOperacion(op: Partial<OperacionLocal>): Promise<string> {
    const uuid = op.uuid || uuidv4();
    await this.operaciones.add({
      uuid,
      tipoOperacion: op.tipoOperacion || 'VENTA_CONTADO',
      sucursalId: op.sucursalId || 0,
      usuarioId: op.usuarioId || 0,
      empresaId: op.empresaId || 0,
      fechaLocal: op.fechaLocal || new Date().toISOString(),
      clienteId: op.clienteId,
      items: op.items || [],
      total: op.total || 0,
      formaPago: op.formaPago || 'EFECTIVO',
      estado: 'REGISTRADA_LOCAL',
      intentos: 0,
      payload: op
    });
    return uuid;
  }

  async obtenerPendientes(): Promise<OperacionLocal[]> {
    return this.operaciones.where('estado').equals('REGISTRADA_LOCAL').toArray();
  }

  async marcarEnviada(uuid: string): Promise<void> {
    await this.operaciones.where('uuid').equals(uuid).modify({ estado: 'ENVIADA' });
  }

  async actualizarEstado(uuid: string, estado: OperacionLocal['estado']): Promise<void> {
    await this.operaciones.where('uuid').equals(uuid).modify({ estado });
  }
}

export const dbOffline = new FashionStoreOfflineDB();
