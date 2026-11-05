import 'dart:convert';
import 'package:uuid/uuid.dart';
import '../../src/services.dart';
import '../../src/api_client.dart';
import 'offline_db.dart';

class SyncOfflineService {
  static Future<Map<String, dynamic>>? _inFlight;
  final _uuid = const Uuid();
  final ApiClient _api;
  final OfflineDb _db;
  SyncOfflineService({ApiClient? client, OfflineDb? database})
      : _api = client ?? api, _db = database ?? OfflineDb.instance;

  Future<String> registrarVentaOffline({required int sucursalId, required int usuarioId,
    required List items, double total = 0, String formaPago = 'EFECTIVO', int? clienteId}) {
    if (formaPago != 'EFECTIVO') throw StateError('Sin conexión solo se admite efectivo.');
    return _registrar('VENTA_CONTADO', sucursalId, usuarioId, items, total, clienteId, null);
  }

  Future<String> registrarReservaOffline({required int sucursalId, required List items, int expirationHours = 24}) {
    return _registrar('RESERVA', sucursalId, _api.currentUser?.id ?? 0, items, 0, _api.currentUser?.id,
      {'expiration_hours': expirationHours});
  }

  Future<String> _registrar(String tipo, int branch, int userId, List items, double total,
    int? clientId, Map<String, dynamic>? extra) async {
    final user = _api.currentUser;
    if (user?.empresaId == null || user!.id != userId || items.isEmpty) {
      throw StateError('Se requiere una sesión de empresa y prendas para operar sin conexión.');
    }
    final uuid = _uuid.v4();
    await _db.agregarOperacion({
      'uuid': uuid, 'tipo_operacion': tipo, 'sucursal_id': branch, 'usuario_id': userId,
      'empresa_id': user.empresaId, 'fecha_local': DateTime.now().toUtc().toIso8601String(),
      'cliente_id': clientId, 'items_json': jsonEncode(items), 'total': total,
      'forma_pago': 'EFECTIVO', 'estado': 'REGISTRADA_LOCAL', 'intentos': 0, 'payload_json': jsonEncode(extra),
    });
    return uuid;
  }

  Future<List<Map<String, dynamic>>> operaciones() async {
    final user = _api.currentUser;
    if (user?.empresaId == null) return [];
    return _db.obtenerOperaciones(user!.empresaId!, user.id);
  }

  Future<int> pendientes() async {
    final user = _api.currentUser;
    if (user?.empresaId == null) return 0;
    return (await _db.obtenerPendientes(user!.empresaId!, user.id)).length;
  }

  Future<Map<String, dynamic>> sincronizar() {
    return _inFlight ??= _enviar().whenComplete(() => _inFlight = null);
  }

  Future<Map<String, dynamic>> _enviar() async {
    final user = _api.currentUser;
    if (user?.empresaId == null) throw StateError('Inicia sesión en tu empresa.');
    final pending = await _db.obtenerPendientes(user!.empresaId!, user.id);
    final batch = pending.take(200).toList();
    if (batch.isEmpty) return {'mensaje': 'Sin operaciones pendientes', 'resultados': <dynamic>[]};
    final operations = batch.map((p) => {
      'uuid': p['uuid'], 'tipo_operacion': p['tipo_operacion'], 'sucursal_id': p['sucursal_id'],
      'usuario_id': p['usuario_id'], 'fecha_local': p['fecha_local'], 'cliente_id': p['cliente_id'],
      'items': jsonDecode(p['items_json'] as String), 'total': p['total'], 'forma_pago': p['forma_pago'],
      'origen': 'OFFLINE', 'payload_extra': jsonDecode(p['payload_json'] as String? ?? 'null'),
    }).toList();
    for (final p in batch) {
      await _db.registrarIntento(p['uuid'] as String);
    }
    if (_api.currentUser?.id != user.id || _api.currentUser?.empresaId != user.empresaId) {
      throw StateError('La sesión cambió. Vuelve a sincronizar.');
    }
    final response = await _api.request('POST', '/sync', body: {'operaciones': operations});
    final data = (response as Map).cast<String, dynamic>();
    for (final raw in (data['resultados'] as List?) ?? const []) {
      if (raw is! Map || !batch.any((p) => p['uuid'] == raw['uuid'])) continue;
      if (!{'CONFIRMADA', 'EN_CONFLICTO', 'RECHAZADA'}.contains(raw['estado'])) continue;
      await _db.actualizarEstado(raw['uuid'] as String, raw['estado'] as String,
        mensaje: raw['mensaje'] as String?, resultado: raw);
    }
    return data;
  }
}
