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
  mensaje?: string;
  resultado?: unknown;
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
  cache!: Table<{ key: string; scope: string; url: string; data: any; downloadedAt: string }, string>;

  constructor() {
    super('FashionStoreOffline');
    this.version(1).stores({
      operaciones: '++id, uuid, estado, tipoOperacion, sucursalId, fechaLocal',
      catalogo: '++id, [productoId+varianteId+sucursalId], sku, sucursalId'
    });
    this.version(2).stores({
      operaciones: '++id, uuid, estado, tipoOperacion, sucursalId, fechaLocal, [empresaId+usuarioId]',
      cache: 'key, scope, url'
    });
  }

  async agregarOperacion(op: Partial<OperacionLocal>): Promise<string> {
    if (!op.empresaId || !op.usuarioId || !op.sucursalId || !op.items?.length) {
      throw new Error('Se requiere una sesión de empresa, sucursal y prendas para operar sin conexión.');
    }
    const uuid = op.uuid || uuidv4();
    await this.transaction('rw', this.operaciones, this.cache, async () => {
    const scope = offlineScope();
    const cacheRows = await this.cache.where('scope').equals(scope).toArray();
    const quantities = new Map<number, number>();
    for (const item of op.items!) {
      if (!Number.isInteger(item.quantity) || item.quantity <= 0 || !Number.isFinite(item.precio) || item.precio < 0) {
        throw new Error('Las cantidades deben ser positivas y los precios no pueden ser negativos.');
      }
      quantities.set(item.variant_id, (quantities.get(item.variant_id) || 0) + item.quantity);
    }
    const knownStock = cacheRows.filter(r => r.url.startsWith('/inventory/availability')).flatMap(r => r.data);
    for (const [variantId, quantity] of quantities) {
      const row = knownStock.find((r: any) => r.variant_id === variantId && r.branch_id === op.sucursalId);
      if (!row || row.available < quantity) throw new Error('La cantidad supera las existencias locales conocidas de la sucursal.');
    }
    for (const row of cacheRows.filter(r => r.url.startsWith('/inventory/availability'))) {
      for (const item of row.data) {
        if (item.branch_id === op.sucursalId) item.available -= quantities.get(item.variant_id) || 0;
      }
      await this.cache.put(row);
    }
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
    });
    return uuid;
  }

  async obtenerOperaciones(): Promise<OperacionLocal[]> {
    const user = offlineUser();
    if (!user?.empresa_id || !user.id) return [];
    return this.operaciones.where('[empresaId+usuarioId]').equals([user.empresa_id, user.id]).reverse().toArray();
  }

  async obtenerPendientes(): Promise<OperacionLocal[]> {
    return (await this.obtenerOperaciones()).filter(op => ['REGISTRADA_LOCAL', 'ENVIADA', 'EN_CONFLICTO'].includes(op.estado));
  }

  async marcarEnviada(uuid: string): Promise<void> {
    await this.marcarEnviadas([uuid]);
  }

  async marcarEnviadas(uuids: string[]): Promise<void> {
    await this.transaction('rw', this.operaciones, async () => {
      await this.operaciones.where('uuid').anyOf(uuids)
        .filter(op => ['REGISTRADA_LOCAL', 'ENVIADA', 'EN_CONFLICTO'].includes(op.estado))
        .modify(op => {
          op.estado = 'ENVIADA';
          op.intentos += 1;
          op.mensaje = 'Enviada. Aún falta la confirmación del servidor; puedes reintentar sin duplicar la operación.';
        });
    });
  }

  async actualizarEstado(uuid: string, estado: OperacionLocal['estado'], mensaje?: string, resultado?: unknown): Promise<void> {
    await this.operaciones.where('uuid').equals(uuid).modify({ estado, mensaje, resultado });
  }
}

export function offlineUser(): { id: number; empresa_id?: number; role_name: string } | null {
  try { return JSON.parse(localStorage.getItem('user') || 'null'); } catch { return null; }
}

export function offlineScope(): string {
  const user = offlineUser();
  return `${user?.empresa_id ?? 'public'}:${user?.id ?? 'guest'}`;
}

export async function cacheOfflineResponse(scope: string, url: string, value: any): Promise<void> {
  await dbOffline.transaction('rw', dbOffline.operaciones, dbOffline.cache, async () => {
  const data = structuredClone(value);
  if (url.startsWith('/inventory/availability') && Array.isArray(data)) {
    const user = offlineUser();
    if (user?.empresa_id && scope === offlineScope()) {
      const pending = await dbOffline.obtenerPendientes();
      for (const op of pending) for (const item of op.items) {
        const row = data.find(r => r.branch_id === op.sucursalId && r.variant_id === (item.variant_id ?? item.variante_id));
        if (row) row.available = Math.max(0, row.available - (item.quantity ?? item.cantidad));
      }
    }
  }
  await dbOffline.cache.put({ key: `${scope}:${url}`, scope, url, data, downloadedAt: new Date().toISOString() });
  });
}

export async function readOfflineResponse(scope: string, url: string): Promise<any | undefined> {
  const exact = await dbOffline.cache.get(`${scope}:${url}`);
  if (exact) return exact.data;
  const [base, query] = url.split('?');
  if (!query || !['/products/', '/inventory/availability'].includes(base)) return undefined;
  const cached = await dbOffline.cache.get(`${scope}:${base}`);
  if (!cached || !Array.isArray(cached.data)) return undefined;
  const params = new URLSearchParams(query);
  const q = (params.get('q') || '').toLowerCase();
  return cached.data.filter((row: any) => {
    if (q && !`${row.name || row.product_name} ${row.description || ''} ${row.sku || ''}`.toLowerCase().includes(q)) return false;
    for (const key of ['category_id', 'season_id', 'product_id', 'branch_id']) {
      if (params.has(key) && Number(params.get(key)) !== (row[key] ?? row[key.replace('_id', '')]?.id)) return false;
    }
    return true;
  });
}

export const dbOffline = new FashionStoreOfflineDB();
